// Run with: node --test explainer/tests/explainer.test.js
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const root = path.join(__dirname, "..");
const fs = require("node:fs");
globalThis.DPC = {};
require(path.join(root, "js", "i18n.js"));
const LOCALE_FILES = fs.readdirSync(path.join(root, "js", "locales")).filter((name) => name.endsWith(".js"));
for (const name of LOCALE_FILES) require(path.join(root, "js", "locales", name));

for (const file of ["data/explainer-data.js", "js/core.js", "js/model.js", "js/network.js", "js/simulation.js", "js/drug.js", "js/results.js", "js/plant.js", "js/charts.js", "js/fly.js"]) {
  require(path.join(root, file));
}

const {
  PlantTissue, FaultKind, erf, ModelFactory, Network, IntegrationCycles, CycleOutcome, ConnectionOutcome, CycleConditions,
  SweepPlan, SweepDirection, transitionPoints, OutcomeIndex, Verdict, DrugCloud, mirroredLayout,
} = globalThis.DPC;
const data = globalThis.DPC_EXPLAINER_DATA;
const factory = new ModelFactory(data);
const models = Object.fromEntries(Object.values(FaultKind).map((kind) => [kind, factory.create(kind)]));
const TOLERANCE = 1e-6;

// The Python model's values at the same inputs, written by simulator/explainer_export.py (CoherenceModel on
// REFERENCE_SCENARIO), so the check follows any recalibration of the Python model.
const PYTHON_REFERENCE = data.modelChecks;

test("browser model reproduces the Python model's effective jitter and coherence probability", () => {
  assert.ok(PYTHON_REFERENCE.length > 0, "explainer-data.js carries no model checks; re-run simulator/explainer_export.py");
  for (const reference of PYTHON_REFERENCE) {
    const model = models[reference.kind];
    assert.ok(Math.abs(model.effectiveJitterMs(reference.concentration, reference.giant) - reference.jitterMs) < TOLERANCE, JSON.stringify(reference));
    assert.ok(Math.abs(model.coherenceProbability(reference.concentration, reference.giant) - reference.coherence) < TOLERANCE, JSON.stringify(reference));
  }
});

test("erf approximation stays within its published error bound", () => {
  const known = [[0, 0], [0.5, 0.5204998778130465], [1, 0.8427007929497149], [-1, -0.8427007929497149], [2, 0.9953222650189527]];
  for (const [x, value] of known) assert.ok(Math.abs(erf(x) - value) < 1.5e-7, `erf(${x})`);
});

function smallNetwork() {
  // 0→1→2 forward from sensory cell 0, 2→1 feedback; 3-4 a separate pair; 5 isolated.
  return new Network({
    name: "test", nodeCount: 6, connections: [0, 1, 1, 2, 3, 4], directedConnections: [0, 1, 1, 2, 2, 1, 3, 4],
    sensoryNodes: [0], sensoryDescription: "",
  });
}


test("analysis finds the giant component and the cells a sensory stimulus reaches", () => {
  const network = smallNetwork();
  const analysis = new CycleOutcome(network);
  assert.equal(network.analyse(Uint8Array.from([1, 1, 1]), analysis), 3 / 6);
  assert.deepEqual(Array.from(analysis.inGiant), [1, 1, 1, 0, 0, 0]);
  assert.deepEqual(Array.from(analysis.inReach), [1, 1, 1, 0, 0, 0]);
  assert.equal(analysis.reachShare, 2 / 5);
  network.analyse(Uint8Array.from([0, 0, 1]), analysis);
  assert.equal(analysis.reachShare, 0);
});

test("a connection is feedback when it runs back towards the sensory cells", () => {
  const network = smallNetwork();
  assert.deepEqual([0, 1, 2, 3].map((k) => network.isFeedback(k)), [false, false, true, false]);
});

test("glial settings follow glial_regulation.py", () => {
  const model = factory.create(FaultKind.OMISSION, { myelinIntegrity: 0.5 });
  assert.equal(model.baselineJitterMs(), data.model.baselineJitterMs * (1 + data.glia.demyelinationJitterGain * 0.5));
  const microglial = factory.create(FaultKind.OMISSION, { microglialGain: 0.5 });
  assert.equal(microglial.arousalAt(0, 1), microglial.arousal(0));
  assert.equal(microglial.arousalAt(0, 0), microglial.arousal(0) * 0.5);
});

test("silenced populations keep none of their connections", () => {
  const network = new Network(data.network);
  const cycles = new IntegrationCycles(network, 3);
  const outcome = cycles.run(factory.withoutAgent(), 0, new CycleConditions({ silencedShare: 0.3 }));
  for (let k = 0; k < network.connectionCount; k++) {
    if (outcome.silenced[network.sources[k]] || outcome.silenced[network.targets[k]]) assert.equal(outcome.kept[k], 0);
  }
});

test("transition points read the sweep's crossings of the quorum", () => {
  const points = [
    { direction: SweepDirection.INDUCTION, concentration: 0, share: 0.9 },
    { direction: SweepDirection.INDUCTION, concentration: 1, share: 0.2 },
    { direction: SweepDirection.EMERGENCE, concentration: 1, share: 0.2 },
    { direction: SweepDirection.EMERGENCE, concentration: 0.5, share: 0.3 },
    { direction: SweepDirection.EMERGENCE, concentration: 0, share: 0.9 },
  ];
  assert.deepEqual(transitionPoints(points, (share) => share >= 0.5), { lostAt: 1, regainedAt: 0 });
});

test("outcome index groups runs and gives a verdict", () => {
  const base = { report: "validation_full_x.json", study: "validation", label: "full", identifier: "C1", statement: "s", kind: "test" };
  const index = new OutcomeIndex([
    { ...base, group: "N = 302", holding: 20, applicable: 20 },
    { ...base, group: "N = 1000", holding: 19, applicable: 20 },
    { ...base, label: "confirmatory", group: "N = 302", holding: 0, applicable: 20 },
  ]);
  const entry = index.find("validation:C1");
  assert.equal(entry.groups.length, 2);
  assert.equal(entry.holding, 39);
  assert.equal(entry.verdict, Verdict.SOME);
  assert.equal(index.find("validation:confirmatory:C1").verdict, Verdict.NONE);
  assert.equal(index.find("validation:C9"), null);
});

test("exported connectome matches the percolation report's worm network", () => {
  const network = new Network(data.network);
  const worm = data.thresholds.organisms.find((row) => row.organism === network.name);
  assert.equal(network.nodeCount, worm.node_count);
  assert.equal(network.connectionCount, worm.undirected_edge_count);
});

test("awake worm holds quorum and a saturating GABAergic-like dose loses it", () => {
  const network = new Network(data.network);
  const cycles = new IntegrationCycles(network, 1);
  const model = models[FaultKind.OMISSION];
  assert.ok(model.holdsQuorum(cycles.run(model, 0).giantShare));
  cycles.restart();
  const deep = 2.5;
  for (let n = 0; n < 5; n++) cycles.run(model, deep);
  assert.ok(!model.holdsQuorum(cycles.outcome.giantShare));
});

test("only on-time connections are kept", () => {
  const network = new Network(data.network);
  const cycles = new IntegrationCycles(network, 7);
  const outcome = cycles.run(models[FaultKind.TIMING], 1.0);
  for (let k = 0; k < network.connectionCount; k++) {
    assert.equal(outcome.kept[k], outcome.connections[k] === ConnectionOutcome.ON_TIME ? 1 : 0);
  }
});

test("a sweep rises to the maximum and comes back to zero", () => {
  const plan = new SweepPlan({ maxConcentration: 1, step: 0.5, cyclesPerStep: 1 });
  const steps = Array.from(plan.steps());
  assert.deepEqual(steps.map((s) => s.concentration), [0, 0.5, 1, 1, 0.5, 0]);
  assert.deepEqual(steps.map((s) => s.direction), [...Array(3).fill(SweepDirection.INDUCTION), ...Array(3).fill(SweepDirection.EMERGENCE)]);
});

// Values printed by simulator/plant_tissue.py (ExcitableTissue._step) on a 3 × 3 sheet, all junctions open, 10 steps.
const PYTHON_PLANT_VOLTAGE = [1.580924333573, -0.608089441684, -1.134245226912];
const PYTHON_PLANT_RECOVERY = [-0.507801286653, -0.612592747435, -0.623533024054];

test("browser plant tissue reproduces the Python FitzHugh-Nagumo steps", () => {
  const spec = { ...data.plant, rows: 3, columns: 3 };
  const tissue = new PlantTissue(spec, 1);
  tissue.start({ concentration: 0, conductance: data.plant.junctionConductances[0] });
  for (let n = 0; n < 10; n++) tissue.step();
  for (let column = 0; column < 3; column++) {
    for (let row = 0; row < 3; row++) {
      assert.ok(Math.abs(tissue.voltage[row * 3 + column] - PYTHON_PLANT_VOLTAGE[column]) < 1e-9);
      assert.ok(Math.abs(tissue.recovery[row * 3 + column] - PYTHON_PLANT_RECOVERY[column]) < 1e-9);
    }
  }
});

test("closing every junction stops the wave at the stimulated edge", () => {
  const tissue = new PlantTissue({ ...data.plant, rows: 10, columns: 10, durationSteps: 400 }, 1);
  tissue.start({ concentration: 1e6, conductance: 1 });
  while (!tissue.finished) tissue.step();
  assert.equal(tissue.openFraction < 0.1, true);
  assert.ok(tissue.reachedFraction <= 0.2);
});

// Every locale must carry the same keys, the same HTML tags in the same order, and the same message placeholders.
const tagsOf = (html) => (html.match(/<[^>]+>/g) ?? []).join("|");
const placeholdersOf = (message) => (message.match(/\{\w+\}/g) ?? []).sort().join();

test("every locale matches the English source in keys, tags and placeholders", () => {
  const { registry, DEFAULT_LOCALE } = globalThis.DPC;
  const source = registry.get(DEFAULT_LOCALE);
  for (const [code, locale] of registry) {
    assert.deepEqual(Object.keys(locale.content).sort(), Object.keys(source.content).sort(), `${code} content keys`);
    assert.deepEqual(Object.keys(locale.messages).sort(), Object.keys(source.messages).sort(), `${code} message keys`);
    for (const key of Object.keys(source.content)) assert.equal(tagsOf(locale.content[key]), tagsOf(source.content[key]), `${code} tags in ${key}`);
    for (const key of Object.keys(source.messages)) assert.equal(placeholdersOf(locale.messages[key]), placeholdersOf(source.messages[key]), `${code} placeholders in ${key}`);
    if (locale.predictions) assert.equal(locale.predictions.length, data.predictions[DEFAULT_LOCALE].length, `${code} predictions`);
  }
});

test("the page and the English locale use exactly the same text keys", () => {
  const page = fs.readFileSync(path.join(root, "index.html"), "utf8");
  const used = new Set([...page.matchAll(/data-i18n(?:-[a-z-]+)?="([^"]+)"/g)].map((match) => match[1]));
  const defined = new Set(Object.keys(globalThis.DPC.registry.get(globalThis.DPC.DEFAULT_LOCALE).content));
  assert.deepEqual([...used].filter((key) => !defined.has(key)), [], "keys the page needs but the locale lacks");
  assert.deepEqual([...defined].filter((key) => !used.has(key)), [], "locale text the page never shows");
});

test("on the first cycle every cell starts from its own state, so nothing fades in from empty", () => {
  const network = new Network(data.network);
  const outcome = new IntegrationCycles(network, 5).run(factory.withoutAgent(), 0);
  assert.deepEqual(Array.from(outcome.wasInGiant), Array.from(outcome.inGiant));
});

const DOSE_RANGE = 2.5;
const LONG_ENOUGH_MS = 100000;

test("anaesthetic molecules: the number follows the dose and the bound share follows the dose-response curve", () => {
  const cloud = new DrugCloud(1);
  const agent = models[FaultKind.OMISSION].agent;
  const dose = (concentration) => cloud.setDose({ concentration, maxConcentration: DOSE_RANGE, effect: agent.effectFraction(concentration) });
  dose(DOSE_RANGE);
  const full = cloud.molecules.length;
  assert.ok(full > 0);
  const bound = cloud.molecules.filter((molecule) => molecule.bound).length;
  assert.equal(bound, Math.round(full * agent.effectFraction(DOSE_RANGE)));
  dose(DOSE_RANGE / 2);
  cloud.settle();
  assert.equal(cloud.molecules.length, Math.round(full / 2));
  dose(0);
  assert.equal(cloud.molecules.filter((molecule) => molecule.bound).length, 0, "nothing stays bound once the drug is gone");
});

test("anaesthetic molecules wash out: leaving molecules reach the edge and are dropped", () => {
  const cloud = new DrugCloud(2);
  cloud.setDose({ concentration: DOSE_RANGE, maxConcentration: DOSE_RANGE, effect: 0.5 });
  cloud.setDose({ concentration: 0, maxConcentration: DOSE_RANGE, effect: 0 });
  assert.ok(cloud.molecules.every((molecule) => molecule.leaving));
  cloud.advance(LONG_ENOUGH_MS);
  assert.equal(cloud.molecules.length, 0);
});

test("fly map: left and right neuropils mirror each other and midline neuropils sit in the centre", () => {
  const { neuropils } = data.fly;
  const layout = mirroredLayout(neuropils);
  const at = (name) => layout[neuropils.indexOf(name)];
  for (const name of neuropils.filter((n) => n.endsWith("_L"))) {
    const [left, right] = [at(name), at(name.replace(/_L$/, "_R"))];
    assert.ok(right, `${name} has a right-hand partner`);
    assert.equal(left.y, right.y);
    assert.ok(Math.abs(left.x - 0.5 - (0.5 - right.x)) < 1e-12, `${name} mirrors its partner`);
  }
  for (const name of neuropils.filter((n) => !/_[LR]$/.test(n))) assert.equal(at(name).x, 0.5);
});

test("fly data: connections are (source, target, synapses) triples between neuropils, and the antennal lobes are the senses", () => {
  const { fly } = data;
  assert.equal(fly.connections.length % 3, 0);
  for (let k = 0; k < fly.connections.length; k += 3) {
    assert.notEqual(fly.connections[k], fly.connections[k + 1], "connections within a neuropil are dropped");
    assert.ok(fly.connections[k + 2] >= 5, "every neuron-level connection has at least five synapses");
  }
  assert.deepEqual(fly.sensoryNeuropils.map((index) => fly.neuropils[index]).sort(), ["AL_L", "AL_R"]);
  assert.equal(fly.neuronCounts.reduce((sum, n) => sum + n, 0), fly.neuronCount);
});

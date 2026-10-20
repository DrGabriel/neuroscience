// One scene per figure of the article, each built from the shared blocks in scenes.js.
(function (root) {
  "use strict";

  const {
    FaultKind, Network, OrbitProjector, Turn, QuorumPainter, BroadcastPainter, FaultPlacementPainter, PlantTissue, PlantView,
    CycleConditions, FaultPlacement, agentJitterMasks,
    ArrivalView, PhaseDialView, RasterView, StripView, ThresholdView, describeThresholds, FlyMapView, SpeciesCurvesView, namedNeuropils, RandomSource, RangeControl, ChoiceGroup,
    Scene, NetworkPane, NetworkScene, DosedScene, DoseInstrument, DrugLayer, SweepPanel, NetworkViewKind, alternativeViews, conditionsWith,
    DECIMALS, withinWindow, wrapPhase, phaseOf, percent, fixed, formatConcentration, speakConcentration, prefillStrip, make, t, count, quorumState, ThresholdBar,
    OrientationMarkers, SensoryRings, REGION_WORDS, organismName,
  } = root.DPC;

  const quorumWord = (holds) => t(quorumState(holds));
  const ms = (value) => `${fixed(value, DECIMALS.ms)} ms`;
  const speakMs = (value) => t("speakMs", { value: fixed(value, DECIMALS.ms) });

  // The waking worm, holding quorum.
  class HeroScene extends NetworkScene {
    describe() {
      return t("describeHero", { giant: percent(this.pane.outcome.giantShare) });
    }
  }

  // P1, P2: arrivals scattered by timing error around the integration window.
  class WindowScene extends Scene {
    static ARRIVALS = 180;

    constructor(scope, context) {
      super(scope, context);
      this.random = new RandomSource(context.seed);
      this.view = new ArrivalView(this.element("canvas"));
      this.jitter = this.track(new RangeControl(scope, "jitter", { owner: this.owner, format: ms, speak: speakMs, onChange: () => this.step() }));
    }

    legend() {
      return this.view.legend();
    }

    get windowMs() {
      return this.context.data.model.integrationWindowMs;
    }

    tick() {
      this.arrivalsMs = Array.from({ length: WindowScene.ARRIVALS }, () => this.random.standardNormal() * this.jitter.value);
    }

    render() {
      this.view.draw({ arrivalsMs: this.arrivalsMs, halfWindowMs: this.windowMs / 2 });
    }

    readings() {
      return { onTime: percent(withinWindow(this.windowMs, this.jitter.value)) };
    }

    describe() {
      return t("describeWindow", { jitter: fixed(this.jitter.value, DECIMALS.ms), onTime: this.readings().onTime, window: fixed(this.windowMs, 0) });
    }
  }

  // P8: the same timing error in ms costs less phase on a slower rhythm.
  class RhythmScene extends Scene {
    static ARRIVALS = 90;
    static REFERENCE_HZ = 40;
    static FREQUENCIES = Object.freeze({ GAMMA: 40, BETA: 20, ALPHA: 10 });

    constructor(scope, context) {
      super(scope, context);
      this.random = new RandomSource(context.seed + 1);
      this.view = new PhaseDialView(this.element("canvas"));
      this.frequency = this.track(new ChoiceGroup(scope, "frequency", { owner: this.owner, values: RhythmScene.FREQUENCIES, onChange: () => this.step() }));
      this.jitter = this.track(new RangeControl(scope, "jitter", { owner: this.owner, format: ms, speak: speakMs, onChange: () => this.step() }));
      // The window is held at the share of the cycle that half of 3 ms takes at 40 Hz.
      this.windowHalfPhase = phaseOf(context.data.model.integrationWindowMs / 2, RhythmScene.REFERENCE_HZ);
    }

    tick() {
      this.phases = Array.from({ length: RhythmScene.ARRIVALS }, () => phaseOf(this.random.standardNormal() * this.jitter.value, this.frequency.value));
      this.onTime = this.phases.filter((phase) => Math.abs(wrapPhase(phase)) <= this.windowHalfPhase).length / this.phases.length;
    }

    render() {
      this.view.draw({ phases: this.phases, windowHalfPhase: this.windowHalfPhase });
    }

    legend() {
      return this.view.legend();
    }

    readings() {
      return { phaseError: `${Math.round((phaseOf(this.jitter.value, this.frequency.value) * 180) / Math.PI)}°`, onTime: percent(this.onTime) };
    }

    describe() {
      return t("describeRhythm", { frequency: this.frequency.value, jitter: fixed(this.jitter.value, DECIMALS.ms), onTime: percent(this.onTime) });
    }
  }

  // P8, schematic only: streaming, then polling, then exponential backoff.
  class StreamingScene extends Scene {
    static POLLING_FROM = 0.25;
    static BACKOFF_FROM = 0.5;
    static STAGE_MESSAGE = Object.freeze(["stageStreaming", "stagePolling", "stageBackoff"]);

    constructor(scope, context) {
      super(scope, context);
      this.random = new RandomSource(context.seed + 2);
      this.view = new RasterView(this.element("canvas"));
      this.depth = this.track(new RangeControl(scope, "depth", { owner: this.owner, speak: (depth) => t(StreamingScene.stageMessage(depth)), onChange: () => this.step() }));
      // The named stops under the slider sit where each stage begins.
      this.element("[data-stops]").style.setProperty("--polling-from", String(StreamingScene.POLLING_FROM));
      this.element("[data-stops]").style.setProperty("--backoff-from", String(StreamingScene.BACKOFF_FROM));
    }

    static stageMessage(depth) {
      if (depth < StreamingScene.POLLING_FROM) return StreamingScene.STAGE_MESSAGE[0];
      return StreamingScene.STAGE_MESSAGE[depth <= StreamingScene.BACKOFF_FROM ? 1 : 2];
    }

    legend() {
      return this.view.legend();
    }

    tick() {
      this.raster = this.view.sample(this.random, this.depth.value);
    }

    render() {
      this.view.draw(this.raster);
    }

    describe() {
      if (this.depth.value < StreamingScene.POLLING_FROM) return t("describeStreaming");
      return t(this.depth.value <= StreamingScene.BACKOFF_FROM ? "describePolling" : "describeBackoff");
    }
  }

  // P4: the same dose, two kinds of fault, side by side.
  class FaultsScene extends Scene {
    static ANIMATED = true;

    constructor(scope, context) {
      super(scope, context);
      this.panes = Object.values(FaultKind).map((kind) => ({
        kind,
        pane: new NetworkPane({ canvas: this.element(`[data-pane="${kind}"] canvas`), network: context.network, seed: context.seed }),
      }));
      this.dose = this.track(new RangeControl(scope, "dose", { owner: this.owner, format: formatConcentration, speak: speakConcentration, onChange: () => this.step() }));
      this.instrument = new DoseInstrument(scope, this.dose.input);
      this.drug = new DrugLayer(this.panes.map(({ pane }) => pane.view), context);
    }

    legend() {
      return this.panes[0].pane.painter.legend();
    }

    sharedReadings() {
      const agents = this.panes.map(({ kind }) => ({ kind, agent: this.context.models.create(kind).agent }));
      this.instrument.draw(agents[0].agent, this.dose.value);
      return { doseEffect: agents.map(({ kind, agent }) => DoseInstrument.effectText(agent, this.dose.value, kind)).join(" · ") };
    }

    tick() {
      for (const { kind, pane } of this.panes) pane.run(this.context.models.create(kind), this.dose.value);
      this.drug.show(this.context.models.create(FaultKind.OMISSION).agent, this.dose);
    }

    render() {
      for (const { pane } of this.panes) pane.draw(this.progress);
    }

    showReadings() {
      super.showReadings();
      for (const { pane } of this.panes) pane.showVerdict();
    }

    // One reading per pane, the same in both so they compare: the share of connections that count.
    readings() {
      return Object.fromEntries(this.panes.map(({ kind, pane }) => [`counting-${kind}`, percent(pane.outcome.expectedCoherence)]));
    }

    describe() {
      const [omission, timing] = this.panes.map(({ pane }) => percent(pane.outcome.giantShare));
      return t("describeFaults", { dose: formatConcentration(this.dose.value), omission, timing });
    }
  }

  // P3: the giant component against the quorum, seen as a network, as islands or as a matrix.
  class QuorumScene extends DosedScene {
    constructor(scope, context) {
      super(scope, context);
      this.alternatives = alternativeViews(this.element("[data-network]"), context.network);
      this.view = this.track(new ChoiceGroup(scope, "view", { owner: this.owner, values: NetworkViewKind, onChange: () => {
        this.render();
        this.showLegend();
      } }));
      this.measuredThreshold = context.data.thresholds.organisms.find((row) => row.organism === context.network.name).quorum_threshold_measured_mean;
      // Why quorum holds or fails: the connections that count against the share the measured threshold needs.
      this.connections = new ThresholdBar({ label: "connectionsThatCount", mark: "connectionsNeeded" });
      this.element("[data-connection-bar]").append(this.connections.element);
    }

    render() {
      if (this.view.value === NetworkViewKind.NETWORK) super.render();
      else this.alternatives[this.view.value].draw(this.pane.painter);
    }

    legend() {
      return this.view.value === NetworkViewKind.NETWORK ? super.legend() : this.alternatives[this.view.value].legend(this.pane.painter);
    }

    showsDrug() {
      return this.view.value === NetworkViewKind.NETWORK;
    }

    showReadings() {
      super.showReadings();
      this.connections.show({ share: this.pane.outcome.expectedCoherence, threshold: this.measuredThreshold });
    }

    describe() {
      const outcome = this.pane.outcome;
      return t("describeQuorum", { dose: formatConcentration(this.dose.value), giant: percent(outcome.giantShare), state: quorumWord(this.holdsQuorum()), coherence: percent(outcome.expectedCoherence), threshold: percent(this.measuredThreshold) });
    }
  }

  // P5, P7: going under and coming back, with the reference feedback calibrated to measured ratios.
  class InertiaScene extends NetworkScene {
    constructor(scope, context) {
      super(scope, context);
      this.feedback = this.element("[data-feedback]");
      for (const target of context.data.inertia.targets) {
        this.feedback.append(new Option(t("feedbackOption", { ms: fixed(target.feedbackMs, DECIMALS.ratio), ratio: fixed(target.ratio, DECIMALS.ratio), source: target.source }), String(target.feedbackMs)));
      }
      this.feedback.append(new Option(t("noFeedback"), "0"));
      const reference = context.models.reference.feedbackJitterMs;
      this.feedback.value = String(context.data.inertia.targets.reduce((best, target) => (Math.abs(target.feedbackMs - reference) < Math.abs(best - reference) ? target.feedbackMs : best), 0));
      this.feedback.selectedOptions[0].defaultSelected = true;
      this.sweep = new SweepPanel(this, { model: () => this.model(), comparison: () => this.model(0), controls: [this.feedback], cycles: this.pane.cycles });
      // A sweep's readings belong to the setting it ran with.
      this.feedback.addEventListener("change", () => {
        this.sweep.clear();
        this.step();
      });
    }

    model(feedbackJitterMs = Number(this.feedback.value)) {
      return this.context.models.create(FaultKind.OMISSION, { feedbackJitterMs });
    }

    // While a sweep runs, it advances the pane's cycles itself, so the network shows the dose being swept.
    tick() {
      if (!this.sweep.runner.running) super.tick();
    }

    render() {
      super.render();
      if (!this.sweep.runner.running) this.sweep.draw();
    }

    legend() {
      return [...super.legend(), ...this.sweep.legend()];
    }

    clear() {
      this.sweep.clear();
    }

    readings() {
      return { ...this.sweep.readings(), ratio: this.sweep.ratioReading(), ratioMean: this.sweep.spreadReading("chosen"), ratioNoFeedback: this.sweep.spreadReading("comparison") };
    }

    describe() {
      return this.sweep.summary();
    }
  }

  // P3 with a stimulus, P6: the sensory cells keep their signal while its spread through the network collapses.
  class BroadcastScene extends DosedScene {
    constructor(scope, context) {
      super(scope, context, { painterFor: (outcome) => new BroadcastPainter(outcome, context.network) });
    }

    readings() {
      return { reach: percent(this.pane.outcome.reachShare) };
    }

    describe() {
      return t("describeBroadcast", { dose: formatConcentration(this.dose.value), reach: percent(this.pane.outcome.reachShare) });
    }
  }

  const PLACEMENT_MESSAGE = Object.freeze({ FEEDBACK: "placementFeedback", MATCHED_RANDOM: "placementRandom", EVERYWHERE: "placementEverywhere" });

  // Ketamine and K2, live: the ketamine-like agent's timing error on feedback connections only, on as many random
  // connections (the control), or on every connection, while baseline error and transmission failure act everywhere.
  class FeedbackScene extends DosedScene {
    constructor(scope, context) {
      const exposure = { mask: null };
      super(scope, context, { painterFor: (outcome) => new FaultPlacementPainter(outcome, context.network, () => exposure.mask) });
      this.fault = { value: FaultKind.TIMING };
      this.exposure = exposure;
      this.masks = agentJitterMasks(context.network, context.seed);
      this.conditionsFor = Object.freeze(Object.fromEntries(Object.entries(this.masks).map(([placement, mask]) => [placement, new CycleConditions({ agentJitterMask: mask })])));
      this.placement = this.track(new ChoiceGroup(scope, "placement", { owner: this.owner, values: FaultPlacement, onChange: () => this.place() }));
      this.place();
    }

    place() {
      this.exposure.mask = this.masks[this.placement.value];
      this.step();
    }

    conditions() {
      return this.conditionsFor[this.placement.value];
    }

    exposedCount() {
      const mask = this.exposure.mask;
      return mask ? mask.reduce((sum, value) => sum + value, 0) : this.context.network.connectionCount;
    }

    readings() {
      const exposed = this.exposedCount();
      return { exposed: t("countAndShare", { count: count(exposed), share: percent(exposed / this.context.network.connectionCount) }) };
    }

    describe() {
      return t("describeFeedback", { dose: formatConcentration(this.dose.value), placement: t(PLACEMENT_MESSAGE[this.placement.value]), giant: percent(this.pane.outcome.giantShare) });
    }
  }

  // P7 in sleep: no agent, no arousal drive, whole populations falling silent.
  class SleepScene extends NetworkScene {
    static STRIP_CAPACITY = 90;
    static Preset = Object.freeze({ RAT: "ratDownStateShare", HUMAN: "humanDownStateShareUpper", GLOBAL: "globalDownStateShare" });

    constructor(scope, context) {
      super(scope, context, { painterFor: (outcome) => new QuorumPainter(outcome, context.network, { showLate: false, showSilenced: true }) });
      this.silenced = this.track(new RangeControl(scope, "silenced", { owner: this.owner, format: percent, speak: (share) => t("speakSilenced", { share: percent(share) }), onChange: () => this.restartStrip() }));
      this.strip = new StripView(this.element("[data-strip]"), { capacity: SleepScene.STRIP_CAPACITY, threshold: context.models.reference.quorumFraction });
      for (const button of scope.querySelectorAll("[data-preset]")) {
        button.addEventListener("click", () => {
          this.silenced.value = context.data.sleep[SleepScene.Preset[button.dataset.preset]];
          this.restartStrip();
        });
      }
      prefillStrip(this, this.strip);
    }

    // A new setting starts a new history: the strip is refilled at that setting, then the figure moves on.
    restartStrip() {
      prefillStrip(this, this.strip);
      this.step();
    }

    model() {
      return this.context.models.withoutAgent({ arousalLevel: this.context.data.sleep.arousalLevel });
    }

    conditions() {
      return conditionsWith(this.silenced.value);
    }

    legend() {
      return [...super.legend(), ...this.strip.legend()];
    }

    clear() {
      prefillStrip(this, this.strip);
    }

    tick() {
      super.tick();
      this.strip.push(this.pane.outcome.giantShare);
      this.strip.draw();
    }

    describe() {
      return t("describeSleep", { silenced: percent(this.silenced.value), giant: percent(this.pane.outcome.giantShare), state: quorumWord(this.holdsQuorum()) });
    }
  }

  // P9: myelin sets the baseline jitter; the microglial loop weakens arousal as the giant component shrinks.
  class GliaScene extends Scene {
    constructor(scope, context) {
      super(scope, context);
      const onChange = () => {
        this.sweep?.clear();
        this.showReadings();
      };
      this.myelin = this.track(new RangeControl(scope, "myelin", { owner: this.owner, format: percent, speak: (share) => t("speakMyelin", { share: percent(share) }), onChange }));
      this.microglia = this.track(new RangeControl(scope, "microglia", { owner: this.owner, format: (value) => fixed(value, DECIMALS.share), onChange }));
      this.sweep = new SweepPanel(this, { model: () => this.model(), controls: [this.myelin.input, this.microglia.input] });
    }

    model() {
      return this.context.models.create(FaultKind.OMISSION, { myelinIntegrity: this.myelin.value, microglialGain: this.microglia.value });
    }

    render() {
      if (!this.sweep.runner.running) this.sweep.draw();
    }

    legend() {
      return this.sweep.legend();
    }

    clear() {
      this.sweep.clear();
    }

    readings() {
      return { baseline: ms(this.model().baselineJitterMs()), ...this.sweep.readings() };
    }

    describe() {
      return t("describeGlia", { myelin: percent(this.myelin.value), microglia: fixed(this.microglia.value, DECIMALS.share), sweep: this.sweep.summary() });
    }
  }

  // Near the threshold the giant component swings from cycle to cycle: the fluctuations of P1b.
  class EdgeScene extends DosedScene {
    static STRIP_CAPACITY = 120;

    constructor(scope, context) {
      super(scope, context);
      this.strip = new StripView(this.element("[data-strip]"), { capacity: EdgeScene.STRIP_CAPACITY, threshold: context.models.reference.quorumFraction });
      // After the slider's own step: the history is replaced by one run wholly at the new dose.
      this.dose.input.addEventListener("input", () => prefillStrip(this, this.strip));
      prefillStrip(this, this.strip);
    }

    tick() {
      super.tick();
      this.strip.push(this.pane.outcome.giantShare);
      this.strip.draw();
    }

    legend() {
      return [...super.legend(), ...this.strip.legend()];
    }

    clear() {
      prefillStrip(this, this.strip);
    }

    // Over every cycle the strip shows, so the reading and the chart describe the same window.
    readings() {
      return { spread: fixed(this.strip.spread(EdgeScene.STRIP_CAPACITY), DECIMALS.threshold) };
    }

    describe() {
      return t("describeEdge", { dose: formatConcentration(this.dose.value), spread: this.readings().spread });
    }
  }

  // The reports name organisms in English; the page shows them in the reader's language.
  const ORGANISM_KEY = Object.freeze({ "C. elegans": "celegans", Drosophila: "drosophila", Human: "human" });
  const localOrganism = (name) => (name in ORGANISM_KEY ? organismName(ORGANISM_KEY[name]) : name);
  // Diffusion imaging records no direction, so a directed threshold on the human map is not a result (paper, Section 6).
  const WITHOUT_DIRECTION = Object.freeze(new Set(["Human"]));
  const directedOf = (row) => (WITHOUT_DIRECTION.has(row.organism) ? null : row.quorum_threshold_directed_mean);

  // Quorum thresholds across species: the generating-function formula against measurement.
  class SpeciesScene extends Scene {
    constructor(scope, context) {
      super(scope, context);
      this.view = new ThresholdView(this.element("canvas"));
      const organisms = context.data.thresholds.organisms;
      this.rows = organisms.map((row) => ({ label: localOrganism(row.organism), formula: row.quorum_threshold_formula, measured: row.quorum_threshold_measured_mean, directed: directedOf(row) }));
      const cells = (row) => [
        localOrganism(row.organism), count(row.node_count), fixed(row.mean_degree, 1), fixed(row.quorum_threshold_formula, DECIMALS.threshold),
        fixed(row.quorum_threshold_measured_mean, DECIMALS.threshold), directedOf(row) === null ? t("notMeasured") : fixed(row.quorum_threshold_directed_mean, DECIMALS.threshold), ms(row.critical_jitter_ms_measured),
      ];
      this.element("tbody").append(...organisms.map((row) => make("tr", {}, cells(row).map((value) => make("td", { textContent: value })))));
      // The source report is fixed: written once and marked for the results archive to turn into a link.
      const source = this.element("[data-reading='source']");
      source.textContent = source.dataset.report = context.data.thresholds.report;
    }

    render() {
      this.view.draw(this.rows);
    }

    legend() {
      return this.view.legend();
    }

    describe() {
      return describeThresholds(this.rows);
    }
  }

  // The study's own induction curves for worm, fly and human: a reported result, nothing is simulated here.
  class SpeciesCurvesScene extends Scene {
    constructor(scope, context) {
      super(scope, context);
      this.view = new SpeciesCurvesView(this.element("canvas"), context.data.speciesCurves);
    }

    render() {
      this.view.draw();
    }

    legend() {
      return this.view.legend();
    }

    describe() {
      return t("describeSpeciesCurves");
    }
  }

  // The fly's wiring by neuropil: a drawing of the data, nothing is simulated here.
  class FlyMapScene extends Scene {
    constructor(scope, context) {
      super(scope, context);
      this.view = new FlyMapView(this.element("canvas"), context.data.fly);
    }

    render() {
      this.view.draw();
    }

    legend() {
      return this.view.legend();
    }

    describe() {
      return t("describeFlyMap", { neuropils: count(namedNeuropils(this.context.data.fly.neuropils).length) });
    }
  }

  // The same rule on a human brain in 3D: regions at their anatomical positions, a sound at auditory cortex.
  class BrainScene extends DosedScene {
    static AUTO_TURN_RADIANS_PER_MS = 0.00015;

    constructor(scope, context) {
      const network = new Network(context.data.human);
      const projector = new OrbitProjector(context.data.human.coordinates);
      super(scope, { ...context, network }, { projector, painterFor: (outcome) => new QuorumPainter(outcome, network, { words: REGION_WORDS }) });
      this.projector = projector;
      projector.attach(this.element("[data-network]"), () => this.render());
      this.painters = { quorum: this.pane.painter, broadcast: new BroadcastPainter(this.pane.outcome, network, { words: REGION_WORDS }) };
      // Drawn over the regions: the hearing areas ringed, and Front, Back, Left and Right turning with the brain.
      this.pane.view.overlays.push(new SensoryRings(network), new OrientationMarkers(projector));
      this.stimulus = this.element("[data-stimulus]");
      this.stimulus.addEventListener("change", () => {
        this.render();
        this.showLegend();
      });
      this.autoTurn = this.element("[data-auto-turn]");
      for (const button of scope.querySelectorAll("[data-turn]")) {
        button.addEventListener("click", () => {
          this.projector.turn(Turn[button.dataset.turn]);
          this.render();
        });
      }
      this.element("[data-reset-view]").addEventListener("click", () => {
        this.projector.reset();
        this.render();
      });
    }

    legend() {
      return [...(this.stimulus.checked ? this.painters.broadcast : this.painters.quorum).legend(), ...SensoryRings.legend()];
    }

    clear() {
      this.projector.reset();
    }

    advance(dtMs, cycleMs) {
      if (this.autoTurn.checked) this.projector.rotate(BrainScene.AUTO_TURN_RADIANS_PER_MS * dtMs, 0);
      super.advance(dtMs, cycleMs);
    }

    render() {
      this.pane.painter = this.stimulus.checked ? this.painters.broadcast : this.painters.quorum;
      super.render();
    }

    readings() {
      return { reach: percent(this.pane.outcome.reachShare) };
    }

    describe() {
      return t("describeBrain", { dose: formatConcentration(this.dose.value), giant: percent(this.pane.outcome.giantShare), reach: percent(this.pane.outcome.reachShare) });
    }
  }

  // P4 in plants: an action potential crossing excitable tissue until the agent closes enough junctions.
  class PlantScene extends Scene {
    static ANIMATED = true;
    // One full run of the study's tissue plays over this many integration cycles of playback time, and once it is
    // over the stimulus repeats after this many more, while the figure is on screen.
    static RUN_IN_CYCLES = 4;
    static REPEAT_AFTER_CYCLES = 3;

    constructor(scope, context) {
      super(scope, context);
      const { plant } = context.data;
      this.tissue = new PlantTissue(plant, context.seed);
      this.view = new PlantView(this.element("canvas"));
      this.conductance = this.element("[data-conductance]");
      for (const value of plant.junctionConductances) this.conductance.append(new Option(String(value), String(value)));
      this.dose = this.track(new RangeControl(scope, "dose", { owner: this.owner, format: formatConcentration, speak: speakConcentration, onChange: () => this.restart() }));
      this.reducedMotion = root.matchMedia?.("(prefers-reduced-motion: reduce)") ?? { matches: false };
      this.instrument = new DoseInstrument(scope, this.dose.input);
      this.drug = new DrugLayer([this.view], context);
      this.conductance.addEventListener("change", () => this.restart());
      this.element("[data-restart]").addEventListener("click", () => this.restart());
      this.pendingSteps = 0;
      this.restart();
    }

    sharedReadings() {
      this.instrument.draw(this.tissue.agent, this.dose.value);
      return { doseEffect: t("doseEffectJunctions", { share: percent(this.tissue.agent.transmissionFailure(this.dose.value)) }) };
    }

    restart() {
      this.finishedForMs = 0;
      this.tissue.start({ concentration: this.dose.value, conductance: Number(this.conductance.value) });
      this.drug.show(this.tissue.agent, this.dose);
      this.showReadings();
      this.render();
    }

    advanceModel(dtMs, cycleMs) {
      if (this.tissue.finished) {
        this.repeatWhenDue(dtMs, cycleMs);
        return;
      }
      this.pendingSteps += (dtMs * this.tissue.spec.durationSteps) / (PlantScene.RUN_IN_CYCLES * cycleMs);
      for (; this.pendingSteps >= 1 && !this.tissue.finished; this.pendingSteps -= 1) this.tissue.step();
      this.showReadings();
      this.render();
    }

    // Playback only advances figures on screen, so the stimulus repeats only while the reader can see it.
    repeatWhenDue(dtMs, cycleMs) {
      this.finishedForMs += dtMs;
      if (!this.reducedMotion.matches && this.finishedForMs >= PlantScene.REPEAT_AFTER_CYCLES * cycleMs) this.restart();
      else this.render();
    }

    render() {
      this.view.draw(this.tissue);
    }

    legend() {
      return this.view.legend();
    }

    clear() {
      this.restart();
    }

    readings() {
      return { open: percent(this.tissue.openFraction), reached: percent(this.tissue.reachedFraction) };
    }

    describe() {
      return t("describePlant", { dose: formatConcentration(this.dose.value), open: percent(this.tissue.openFraction), reached: percent(this.tissue.reachedFraction) });
    }
  }

  root.DPC = Object.assign(root.DPC || {}, {
    Figures: Object.freeze({
      HeroScene, WindowScene, RhythmScene, StreamingScene, FaultsScene, QuorumScene, InertiaScene, BroadcastScene,
      FeedbackScene, SleepScene, GliaScene, EdgeScene, SpeciesScene, SpeciesCurvesScene, FlyMapScene, BrainScene, PlantScene,
    }),
  });
})(globalThis);

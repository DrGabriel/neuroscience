// Scene building blocks. A scene owns one <figure>: its controls, its views and the readings it shows.
(function (root) {
  "use strict";

  const {
    FaultKind, IntegrationCycles, CycleConditions, transitionPoints, NetworkView, IslandsView, MatrixView, CycleBar, RingProjector,
    QuorumPainter, RangeControl, ChoiceGroup, SweepRunner, SweepPlan, TraceView, DoseCurveView, DrugCloud, required, fixed, percent, t, make, renderLegend,
  } = root.DPC;

  const DECIMALS = Object.freeze({ share: 2, concentration: 2, ms: 1, ratio: 2, threshold: 3 });
  const SWEEP_PLAN = new SweepPlan({ maxConcentration: 2.5, step: 0.05, cyclesPerStep: 6 });
  const formatConcentration = (value) => fixed(value, DECIMALS.concentration);

  class Scene {
    // Scenes whose figure changes between cycles (signals in flight) set this, and are redrawn every frame.
    static ANIMATED = false;

    constructor(scope, context) {
      Object.assign(this, { scope, context, progress: 1, elapsedMs: 0 });
      this.owner = this.constructor.name;
      this.shown = new Map();
      this.controls = [];
      // The anaesthetic's molecules, for scenes with a dose (see DrugLayer).
      this.drug = null;
      this.legendList = make("ul", { className: "figure-legend", ariaLabel: t("legendTitle") });
      scope.insertBefore(this.legendList, scope.querySelector("figcaption"));
    }

    element(selector) {
      return required(this.scope, selector, this.owner);
    }

    // Registers a control so that Reset can put it back to its starting value.
    track(control) {
      this.controls.push(control);
      return control;
    }

    // Adds the figure's Reset button when it has anything the reader can change.
    offerReset() {
      const interactive = this.controls.length || this.scope.querySelector("select, input[type='checkbox']");
      if (!interactive) return;
      const button = make("button", { type: "button", className: "key reset", textContent: t("resetFigure") });
      button.addEventListener("click", () => this.reset());
      this.resetButton = button;
      this.scope.prepend(button);
    }

    // Puts every control back to its starting value, clears what the figure has accumulated, and runs a fresh cycle.
    reset() {
      this.controls.forEach((control) => control.reset());
      for (const select of this.scope.querySelectorAll("select")) {
        const initial = [...select.options].findIndex((option) => option.defaultSelected);
        select.selectedIndex = Math.max(0, initial);
        select.dispatchEvent(new Event("change", { bubbles: true }));
      }
      for (const box of this.scope.querySelectorAll("input[type='checkbox']")) box.checked = box.defaultChecked;
      this.clear();
      this.step();
      this.showLegend();
      this.context.announce(this);
    }

    // Forgets anything accumulated while the reader played with the figure (histories, sweeps, views).
    clear() {}

    legend() {
      return [];
    }

    // Whether the anaesthetic's molecules are on screen, so the key lists them.
    showsDrug() {
      return this.drug !== null;
    }

    showLegend() {
      const items = [...(this.showsDrug() ? DrugCloud.legend() : []), ...this.legend()];
      this.legendList.hidden = items.length === 0;
      renderLegend(this.legendList, items);
    }

    // Runs one integration cycle (or redraws a sample) and shows its readings.
    step() {
      this.tick();
      this.elapsedMs = 0;
      this.progress = this.constructor.ANIMATED ? 0 : 1;
      this.showReadings();
      this.render();
    }

    // Moves the scene on by dtMs of playback time: its overlays always, then its model (advanceModel).
    advance(dtMs, cycleMs) {
      this.drug?.advance(dtMs);
      this.advanceModel(dtMs, cycleMs);
    }

    // A new cycle starts every cycleMs; animated scenes redraw in between, and so do scenes whose molecules move.
    advanceModel(dtMs, cycleMs) {
      this.elapsedMs += dtMs;
      if (this.elapsedMs >= cycleMs) {
        this.step();
        return;
      }
      if (this.constructor.ANIMATED) this.progress = this.elapsedMs / cycleMs;
      if (this.constructor.ANIMATED || this.drug) this.render();
    }

    // Shows the end of the current cycle, for a paused figure.
    settle() {
      this.drug?.settle();
      this.progress = 1;
      this.render();
    }

    tick() {}

    render() {}

    readings() {
      return {};
    }

    describe() {
      return "";
    }

    // Readings every scene of a kind shares (for example the dose instrument), added to the scene's own.
    sharedReadings() {
      return {};
    }

    // Writes each reading into its [data-reading] element, touching the page only when the text changed.
    showReadings() {
      for (const [key, value] of Object.entries({ ...this.sharedReadings(), ...this.readings() })) {
        if (this.shown.get(key) === value) continue;
        this.shown.set(key, value);
        for (const node of this.scope.querySelectorAll(`[data-reading="${key}"]`)) node.textContent = value;
      }
    }
  }

  // The dose's molecules over one or more views, kept in step with the dose slider. A paused page settles every
  // scene the reader changes (app.js), so the molecules then jump to where they are going instead of moving.
  class DrugLayer {
    constructor(views, { seed }) {
      this.clouds = views.map((view) => {
        const cloud = new DrugCloud(seed);
        view.overlays.push(cloud);
        return cloud;
      });
    }

    show(agent, dose) {
      const dosing = { concentration: dose.value, maxConcentration: Number(dose.input.max), effect: agent.effectFraction(dose.value) };
      for (const cloud of this.clouds) cloud.setDose(dosing);
    }

    advance(dtMs) {
      for (const cloud of this.clouds) cloud.advance(dtMs);
    }

    settle() {
      for (const cloud of this.clouds) cloud.settle();
    }
  }

  // One network drawn by one view, running its own integration cycles.
  class NetworkPane {
    constructor({ canvas, network, seed, painterFor = (outcome) => new QuorumPainter(outcome, network), projector = new RingProjector(network) }) {
      this.network = network;
      this.cycles = new IntegrationCycles(network, seed);
      this.view = new NetworkView(canvas, network, projector);
      this.painter = painterFor(this.cycles.outcome);
    }

    get outcome() {
      return this.cycles.outcome;
    }

    run(model, concentration, conditions) {
      return this.cycles.run(model, concentration, conditions);
    }

    draw(progress) {
      this.view.draw(this.painter, progress);
    }
  }

  // A scene showing one network with a cycle bar underneath. Subclasses supply model(), concentration(), conditions().
  class NetworkScene extends Scene {
    static ANIMATED = true;

    constructor(scope, context, paneOptions = {}) {
      super(scope, context);
      this.pane = new NetworkPane({ canvas: this.element("[data-network]"), network: context.network, seed: context.seed, ...paneOptions });
      const bar = scope.querySelector("[data-cycle-bar]");
      this.cycleBar = bar ? new CycleBar(bar) : null;
    }

    model() {
      return this.context.models.withoutAgent();
    }

    concentration() {
      return 0;
    }

    conditions() {
      return undefined;
    }

    tick() {
      this.pane.run(this.model(), this.concentration(), this.conditions());
    }

    render() {
      this.pane.draw(this.progress);
      this.cycleBar?.show(this.progress);
    }

    showReadings() {
      super.showReadings();
      this.cycleBar?.showStrength(this.pane.outcome.referenceStrength);
    }

    holdsQuorum() {
      return this.model().holdsQuorum(this.pane.outcome.giantShare);
    }

    legend() {
      return this.pane.painter.legend();
    }
  }

  // A network scene with a dose slider and, where the figure offers one, a choice of fault.
  class DosedScene extends NetworkScene {
    constructor(scope, context, paneOptions) {
      super(scope, context, paneOptions);
      this.dose = this.track(new RangeControl(scope, "dose", { owner: this.owner, format: formatConcentration, onChange: () => this.step() }));
      this.fault = scope.querySelector('[data-choice="fault"]')
        ? this.track(new ChoiceGroup(scope, "fault", { owner: this.owner, values: FaultKind, onChange: () => this.step() }))
        : { value: FaultKind.OMISSION };
      this.instrument = new DoseInstrument(scope, this.dose.input);
      this.drug = new DrugLayer([this.pane.view], context);
    }

    tick() {
      super.tick();
      this.drug.show(this.model().agent, this.dose);
    }

    sharedReadings() {
      const { agent } = this.model();
      this.instrument.draw(agent, this.dose.value);
      return { doseEffect: DoseInstrument.effectText(agent, this.dose.value, this.fault.value) };
    }

    model() {
      return this.context.models.create(this.fault.value);
    }

    concentration() {
      return this.dose.value;
    }
  }

  // The dose slider's instrument: the agent's dose-response curve with the current dose, and what the drug is doing.
  class DoseInstrument {
    constructor(scope, input) {
      const canvas = scope.querySelector("[data-dose-curve]");
      this.view = canvas ? new DoseCurveView(canvas, { maxConcentration: Number(input.max) }) : null;
    }

    draw(agent, concentration) {
      this.view?.draw({ agent, concentration, halfEffectLabel: t("halfEffect") });
    }

    static effectText(agent, concentration, faultKind) {
      if (faultKind === FaultKind.TIMING) return t("doseEffectJitter", { ms: `${fixed(agent.addedJitterMs(concentration), DECIMALS.ms)} ms` });
      return t("doseEffectFailure", { share: percent(agent.transmissionFailure(concentration)) });
    }
  }

  // Where a sweep stands: not started, under way, or over. Readings show each transition the moment it is found.
  const SweepState = Object.freeze({ IDLE: "IDLE", RUNNING: "RUNNING", DONE: "DONE" });

  // A dose sweep with its trace and readings, for any scene that supplies a model.
  class SweepPanel {
    // cycles: pass a pane's own cycles so that the pane shows the network at each dose as the sweep reaches it.
    constructor(scene, { model, controls = [], cycles = null }) {
      Object.assign(this, { scene, model, controls });
      this.runner = new SweepRunner(scene.element("[data-sweep]"), SWEEP_PLAN);
      this.trace = new TraceView(scene.element("[data-trace]"), { maxConcentration: SWEEP_PLAN.maxConcentration, quorumFraction: scene.context.models.reference.quorumFraction });
      this.cycles = cycles ?? new IntegrationCycles(scene.context.network, scene.context.seed);
      this.clear();
      this.runner.button.addEventListener("click", () => this.run());
    }

    async run() {
      this.clear();
      this.state = SweepState.RUNNING;
      const result = await this.runner.run({
        cycles: this.cycles,
        model: this.model,
        controls: [...this.controls, this.scene.resetButton].filter(Boolean),
        onStep: (points, concentration) => {
          this.points = points.slice();
          this.result = { points: this.points, ...transitionPoints(this.points, (share) => this.model().holdsQuorum(share)) };
          this.trace.draw(this.points, { concentration, share: this.cycles.outcome.giantShare });
          this.scene.showReadings();
        },
      });
      if (!result) return;
      this.result = result;
      this.state = SweepState.DONE;
      this.scene.showReadings();
      this.scene.context.announce(this.scene);
    }

    draw() {
      this.trace.draw(this.points, null);
    }

    clear() {
      this.points = [];
      this.result = null;
      this.state = SweepState.IDLE;
    }

    legend() {
      return this.trace.legend();
    }

    // A transition's reading: its concentration once found; before that, what the sweep can still show.
    _reading(value, { pending, missing, decimals = DECIMALS.concentration }) {
      if (value !== null) return fixed(value, decimals);
      if (this.state === SweepState.IDLE) return t("runTheSweep");
      return t(this.state === SweepState.DONE ? missing : pending);
    }

    readings() {
      const { lostAt = null, regainedAt = null } = this.result ?? {};
      return {
        lost: this._reading(lostAt, { pending: "notYet", missing: "quorumNeverLost" }),
        regained: this._reading(regainedAt, { pending: "notYet", missing: lostAt === null ? "quorumNeverLost" : "quorumNeverRegained" }),
      };
    }

    // The loss-to-recovery ratio once both transitions are known, read the same way as the transitions.
    ratioReading() {
      const { lostAt = null, regainedAt = null } = this.result ?? {};
      const ratio = lostAt !== null && regainedAt !== null ? lostAt / regainedAt : null;
      return this._reading(ratio, { pending: "notYet", missing: "ratioUndefined", decimals: DECIMALS.ratio });
    }

    summary() {
      if (this.state !== SweepState.DONE) return t("sweepNotRun");
      const { lostAt = null, regainedAt = null } = this.result;
      if (lostAt === null) return t("sweepNoLoss");
      return t(regainedAt === null ? "sweepNoReturn" : "sweepSummary", this.readings());
    }
  }

  // The same moment as a network, as islands, or as a matrix.
  const NetworkViewKind = Object.freeze({ NETWORK: "NETWORK", ISLANDS: "ISLANDS", MATRIX: "MATRIX" });

  function alternativeViews(canvas, network) {
    return { [NetworkViewKind.ISLANDS]: new IslandsView(canvas, network), [NetworkViewKind.MATRIX]: new MatrixView(canvas, network) };
  }

  const conditionsWith = (silencedShare) => new CycleConditions({ silencedShare });

  root.DPC = Object.assign(root.DPC || {}, {
    DECIMALS, Scene, NetworkPane, NetworkScene, DosedScene, DoseInstrument, DrugLayer, SweepPanel, NetworkViewKind, alternativeViews, conditionsWith, formatConcentration,
  });
})(globalThis);

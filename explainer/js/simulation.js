// Integration cycles and dose sweeps on a network, using the percolation model's rule for each connection.
(function (root) {
  "use strict";

  const ConnectionOutcome = Object.freeze({ FAILED: 0, ON_TIME: 1, LATE: 2, SILENCED: 3 });
  const SweepDirection = Object.freeze({ INDUCTION: "INDUCTION", EMERGENCE: "EMERGENCE" });
  const UINT32_RANGE = 4294967296;

  class RandomSource {
    constructor(seed) {
      this._state = seed >>> 0;
    }

    // mulberry32
    uniform() {
      this._state = (this._state + 0x6d2b79f5) >>> 0;
      let t = this._state;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / UINT32_RANGE;
    }

    // Box-Muller
    standardNormal() {
      let u = 0;
      while (u === 0) u = this.uniform();
      return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * this.uniform());
    }
  }

  // What a cycle runs under, beyond the model and the dose: the share of populations in a down-state, and which
  // connections the agent's timing error reaches (a mask over connections; null means every connection).
  class CycleConditions {
    constructor({ silencedShare = 0, agentJitterMask = null } = {}) {
      this.silencedShare = silencedShare;
      this.agentJitterMask = agentJitterMask;
      Object.freeze(this);
    }
  }

  // Where the agent's timing error acts: test K2, its matched-random control, and the whole network.
  const FaultPlacement = Object.freeze({ FEEDBACK: "FEEDBACK", MATCHED_RANDOM: "MATCHED_RANDOM", EVERYWHERE: "EVERYWHERE" });

  // As many connections as the mask marks, drawn at random with a partial Fisher-Yates shuffle.
  function matchedRandomMask(mask, seed) {
    const random = new RandomSource(seed);
    const order = Int32Array.from({ length: mask.length }, (_, k) => k);
    const chosen = new Uint8Array(mask.length);
    const count = mask.reduce((sum, value) => sum + value, 0);
    for (let k = 0; k < count; k++) {
      const pick = k + Math.floor(random.uniform() * (mask.length - k));
      [order[k], order[pick]] = [order[pick], order[k]];
      chosen[order[k]] = 1;
    }
    return chosen;
  }

  function agentJitterMasks(network, seed) {
    const feedback = network.feedbackConnectionMask();
    return Object.freeze({
      [FaultPlacement.FEEDBACK]: feedback,
      [FaultPlacement.MATCHED_RANDOM]: matchedRandomMask(feedback, seed),
      [FaultPlacement.EVERYWHERE]: null,
    });
  }
  const AWAKE = new CycleConditions();

  // Everything one cycle produced, held in reusable typed arrays.
  class CycleOutcome {
    constructor(network) {
      this.connections = new Uint8Array(network.connectionCount);
      this.kept = new Uint8Array(network.connectionCount);
      this.errorsMs = new Float32Array(network.connectionCount);
      this.silenced = new Uint8Array(network.nodeCount);
      this.inGiant = new Uint8Array(network.nodeCount);
      this.wasInGiant = new Uint8Array(network.nodeCount);
      this.inReach = new Uint8Array(network.nodeCount);
      this.componentOf = new Int32Array(network.nodeCount);
      this.componentSize = new Int32Array(network.nodeCount);
      this.halfWindowMs = 0;
      this.failureProbability = 0;
      this.jitterMs = 0;
      this.expectedCoherence = 0;
      this.referenceStrength = 1;
      this.giantShare = 1;
      this.reachShare = 1;
      this.cycle = 0;
    }
  }

  // One cycle: down-states silence whole populations; every other connection independently transmits or fails, and
  // a transmitted signal counts when its timing error lies within half the window. The shared rhythm's error uses
  // the previous cycle's giant component: the reference feedback of P5, one cycle at a time.
  class IntegrationCycles {
    constructor(network, seed) {
      this.network = network;
      this.random = new RandomSource(seed);
      this.outcome = new CycleOutcome(network);
    }

    restart() {
      this.outcome.giantShare = 1;
    }

    run(model, concentration, conditions = AWAKE) {
      const { network, outcome } = this;
      const previousGiant = outcome.giantShare;
      outcome.wasInGiant.set(outcome.inGiant);
      outcome.failureProbability = model.agent.transmissionFailure(concentration);
      outcome.jitterMs = model.effectiveJitterMs(concentration, previousGiant);
      this._mask = conditions.agentJitterMask;
      this._unexposedJitterMs = this._mask ? model.unexposedJitterMs(concentration, previousGiant) : outcome.jitterMs;
      outcome.halfWindowMs = model.halfWindowMs();
      outcome.expectedCoherence = model.coherenceProbability(concentration, previousGiant);
      outcome.referenceStrength = model.referenceStrength(concentration, previousGiant);
      this._silence(conditions.silencedShare);
      for (let k = 0; k < network.connectionCount; k++) this._transmit(k);
      outcome.giantShare = network.analyse(outcome.kept, outcome);
      // The first cycle has no previous one to change from.
      if (outcome.cycle === 0) outcome.wasInGiant.set(outcome.inGiant);
      outcome.cycle += 1;
      return outcome;
    }

    _silence(share) {
      const { silenced } = this.outcome;
      for (let node = 0; node < silenced.length; node++) silenced[node] = this.random.uniform() < share ? 1 : 0;
    }

    _transmit(k) {
      const { network, outcome } = this;
      let result;
      if (outcome.silenced[network.sources[k]] || outcome.silenced[network.targets[k]]) result = ConnectionOutcome.SILENCED;
      else if (this.random.uniform() < outcome.failureProbability) result = ConnectionOutcome.FAILED;
      else {
        const jitterMs = this._mask && !this._mask[k] ? this._unexposedJitterMs : outcome.jitterMs;
        outcome.errorsMs[k] = this.random.standardNormal() * jitterMs;
        result = Math.abs(outcome.errorsMs[k]) <= outcome.halfWindowMs ? ConnectionOutcome.ON_TIME : ConnectionOutcome.LATE;
      }
      outcome.connections[k] = result;
      outcome.kept[k] = result === ConnectionOutcome.ON_TIME ? 1 : 0;
    }
  }

  class SweepPlan {
    constructor({ maxConcentration, step, cyclesPerStep }) {
      Object.assign(this, { maxConcentration, step, cyclesPerStep });
      Object.freeze(this);
    }

    *steps() {
      const count = Math.round(this.maxConcentration / this.step);
      for (let k = 0; k <= count; k++) yield { direction: SweepDirection.INDUCTION, concentration: k * this.step };
      for (let k = 0; k <= count; k++) yield { direction: SweepDirection.EMERGENCE, concentration: this.maxConcentration - k * this.step };
    }
  }

  // Where quorum was lost on the way up and regained on the way down, from averaged sweep points.
  function transitionPoints(points, holdsQuorum) {
    const crossing = (direction, fromHeld) => {
      const series = points.filter((point) => point.direction === direction);
      for (let k = 1; k < series.length; k++) {
        if (holdsQuorum(series[k - 1].share) === fromHeld && holdsQuorum(series[k].share) !== fromHeld) return series[k].concentration;
      }
      return null;
    };
    return { lostAt: crossing(SweepDirection.INDUCTION, true), regainedAt: crossing(SweepDirection.EMERGENCE, false) };
  }

  root.DPC = Object.assign(root.DPC || {}, { ConnectionOutcome, SweepDirection, RandomSource, CycleConditions, FaultPlacement, agentJitterMasks, CycleOutcome, IntegrationCycles, SweepPlan, transitionPoints });
})(globalThis);

// Percolation model of Section 4, mirroring simulator/dpc_simulator.py (CoherenceModel, AnaestheticAgent)
// and simulator/glial_regulation.py (demyelinated, MicroglialCoherenceModel).
(function (root) {
  "use strict";

  const FaultKind = Object.freeze({ OMISSION: "OMISSION", TIMING: "TIMING" });

  // Abramowitz and Stegun 7.1.26; absolute error below 1.5e-7.
  const ERF_COEFFICIENTS = Object.freeze({ p: 0.3275911, a: Object.freeze([0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429]) });

  function erf(x) {
    const t = 1 / (1 + ERF_COEFFICIENTS.p * Math.abs(x));
    const polynomial = ERF_COEFFICIENTS.a.reduceRight((sum, coefficient) => sum * t + coefficient, 0) * t;
    const value = 1 - polynomial * Math.exp(-x * x);
    return x >= 0 ? value : -value;
  }

  // Probability that a Gaussian timing error of SD jitterMs falls within ±windowMs / 2.
  function withinWindow(windowMs, jitterMs) {
    return erf(windowMs / (2 * Math.SQRT2 * jitterMs));
  }

  class AnaestheticAgent {
    constructor(spec) {
      Object.assign(this, spec);
      Object.freeze(this);
    }

    effectFraction(concentration) {
      if (concentration <= 0) return 0;
      const scaled = Math.pow(concentration / this.halfEffectConcentration, this.hillCoefficient);
      return scaled / (1 + scaled);
    }

    transmissionFailure(concentration) {
      return this.maxTransmissionFailure * this.effectFraction(concentration);
    }

    addedJitterMs(concentration) {
      return this.maxAddedJitterMs * this.effectFraction(concentration);
    }
  }

  // Every setting a scene can vary, with the reference values as defaults; `with` returns a changed copy.
  class ModelSettings {
    constructor(values) {
      Object.assign(this, values);
      Object.freeze(this);
    }

    static reference(data) {
      const { model, glia } = data;
      return new ModelSettings({
        integrationWindowMs: model.integrationWindowMs,
        baselineJitterMs: model.baselineJitterMs,
        feedbackJitterMs: model.feedbackJitterMs,
        arousalLevel: model.arousalLevel,
        quorumFraction: model.quorumFraction,
        myelinIntegrity: 1,
        demyelinationJitterGain: glia.demyelinationJitterGain,
        microglialGain: 0,
      });
    }

    with(changes) {
      return new ModelSettings({ ...this, ...changes });
    }
  }

  class CoherenceModel {
    constructor(settings, agent) {
      this.settings = settings;
      this.agent = agent;
      Object.freeze(this);
    }

    baselineJitterMs() {
      const { baselineJitterMs, demyelinationJitterGain, myelinIntegrity } = this.settings;
      return baselineJitterMs * (1 + demyelinationJitterGain * (1 - myelinIntegrity));
    }

    arousal(concentration) {
      return this.settings.arousalLevel * (1 - this.agent.arousalSuppression * this.agent.effectFraction(concentration));
    }

    arousalAt(concentration, giantShare) {
      return this.arousal(concentration) * (1 - this.settings.microglialGain * (1 - giantShare));
    }

    // How intact the shared rhythm is (P5): 1 when the network agrees fully or arousal holds it up, 0 when neither does.
    referenceStrength(concentration, giantShare) {
      return 1 - (1 - giantShare) * (1 - this.arousalAt(concentration, giantShare));
    }

    referenceErrorMs(concentration, giantShare) {
      return this.settings.feedbackJitterMs * (1 - this.referenceStrength(concentration, giantShare));
    }

    effectiveJitterMs(concentration, giantShare) {
      return Math.hypot(this.baselineJitterMs(), this.agent.addedJitterMs(concentration), this.referenceErrorMs(concentration, giantShare));
    }

    // The error on a connection that the agent's own timing error does not reach (test K2 and its control).
    unexposedJitterMs(concentration, giantShare) {
      return Math.hypot(this.baselineJitterMs(), this.referenceErrorMs(concentration, giantShare));
    }

    halfWindowMs() {
      return this.settings.integrationWindowMs / 2;
    }

    coherenceProbability(concentration, giantShare) {
      const transmits = 1 - this.agent.transmissionFailure(concentration);
      return transmits * withinWindow(this.settings.integrationWindowMs, this.effectiveJitterMs(concentration, giantShare));
    }

    holdsQuorum(giantShare) {
      return giantShare >= this.settings.quorumFraction;
    }
  }

  class ModelFactory {
    constructor(data) {
      this.reference = ModelSettings.reference(data);
      this.agents = Object.freeze(Object.fromEntries(Object.values(FaultKind).map((kind) => [kind, new AnaestheticAgent(data.model.agents[kind])])));
      // No agent at all: natural sleep and the waking baseline.
      this.noAgent = new AnaestheticAgent({ ...data.model.agents[FaultKind.OMISSION], maxTransmissionFailure: 0, maxAddedJitterMs: 0 });
      Object.freeze(this);
    }

    create(kind, changes = {}) {
      return new CoherenceModel(this.reference.with(changes), this.agents[kind]);
    }

    withoutAgent(changes = {}) {
      return new CoherenceModel(this.reference.with(changes), this.noAgent);
    }
  }

  root.DPC = Object.assign(root.DPC || {}, { FaultKind, erf, withinWindow, AnaestheticAgent, ModelFactory });
})(globalThis);

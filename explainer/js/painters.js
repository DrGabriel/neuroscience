// Painters say how one cycle's outcome is drawn: which connections in which layer, and how each cell looks.
(function (root) {
  "use strict";

  const { Token, Swatch, LegendGroup, ConnectionOutcome, labelled } = root.DPC;

  const LINE = Object.freeze({ thin: 0.7, normal: 0.9, bold: 1.2 });
  const CellStyle = Object.freeze({
    IN_GIANT: Object.freeze({ token: Token.HELD, radius: 3.4 }),
    CUT_OFF: Object.freeze({ token: Token.STRAY, radius: 2.9 }),
    SILENCED: Object.freeze({ token: Token.SILENCED, radius: 2.9, hollow: true }),
    SENSORY: Object.freeze({ token: Token.INK, radius: 3.4 }),
    REACHED: Object.freeze({ token: Token.REACH, radius: 3.4 }),
  });

  let nextVersion = 1;

  // Key entries shared by every painter whose figure shows signals in flight.
  const PULSE_LEGEND = Object.freeze([
    { group: LegendGroup.SIGNALS, swatch: Swatch.DIAMOND, token: Token.HELD, message: "legendPulseOnTime" },
    { group: LegendGroup.SIGNALS, swatch: Swatch.DIAMOND, token: Token.LATE, message: "legendPulseLate" },
    { group: LegendGroup.SIGNALS, swatch: Swatch.CROSS, token: Token.STRAY, message: "legendPulseFailed" },
  ]);

  class Painter {
    constructor(outcome, network) {
      Object.assign(this, { outcome, network, version: nextVersion++ });
    }

    carriesPulse() {
      return true;
    }
  }

  // Who is in the agreeing group: green on time inside it, grey cut off, faint vermilion late, hollow when silenced.
  class QuorumPainter extends Painter {
    constructor(outcome, network, { showLate = true, showSilenced = false } = {}) {
      super(outcome, network);
      this.options = { showLate, showSilenced };
      const inGiant = (k) => outcome.inGiant[network.sources[k]] === 1;
      this.connectionLayers = [
        ...(showLate ? [{ token: Token.LATE_SOFT, width: LINE.thin, includes: (k) => outcome.connections[k] === ConnectionOutcome.LATE }] : []),
        { token: Token.STRAY_SOFT, width: LINE.normal, includes: (k) => outcome.kept[k] === 1 && !inGiant(k) },
        { token: Token.HELD_SOFT, width: LINE.bold, includes: (k) => outcome.kept[k] === 1 && inGiant(k) },
      ];
    }

    cellStyle(node) {
      return QuorumPainter.styleOf(this.outcome.silenced[node], this.outcome.inGiant[node]);
    }

    previousCellStyle(node) {
      return QuorumPainter.styleOf(this.outcome.silenced[node], this.outcome.wasInGiant[node]);
    }

    legend() {
      return labelled([
        { group: LegendGroup.CELLS, swatch: Swatch.DOT, token: Token.HELD, message: "legendInGiant" },
        { group: LegendGroup.CELLS, swatch: Swatch.DOT, token: Token.STRAY, message: "legendCutOff" },
        ...(this.options.showSilenced ? [{ group: LegendGroup.CELLS, swatch: Swatch.RING, token: Token.SILENCED, message: "legendSilenced" }] : []),
        { group: LegendGroup.CONNECTIONS, swatch: Swatch.LINE, token: Token.HELD, message: "legendLinkCounted" },
        ...(this.options.showLate ? [{ group: LegendGroup.CONNECTIONS, swatch: Swatch.LINE, token: Token.LATE, message: "legendLinkLate" }] : []),
        ...PULSE_LEGEND,
      ]);
    }

    static styleOf(silenced, inGiant) {
      if (silenced) return CellStyle.SILENCED;
      return inGiant ? CellStyle.IN_GIANT : CellStyle.CUT_OFF;
    }
  }

  // How far a stimulus at the sensory cells reaches: senses in the text colour, blue reached, grey not reached.
  class BroadcastPainter extends Painter {
    constructor(outcome, network) {
      super(outcome, network);
      const reached = (k) => outcome.inReach[network.sources[k]] === 1;
      this.connectionLayers = [
        { token: Token.STRAY_SOFT, width: LINE.normal, includes: (k) => outcome.kept[k] === 1 && !reached(k) },
        { token: Token.REACH_SOFT, width: LINE.bold, includes: (k) => outcome.kept[k] === 1 && reached(k) },
      ];
    }

    carriesPulse(k) {
      return this.outcome.inReach[this.network.sources[k]] === 1;
    }

    cellStyle(node) {
      if (this.network.isSensory[node]) return CellStyle.SENSORY;
      return this.outcome.inReach[node] ? CellStyle.REACHED : CellStyle.CUT_OFF;
    }

    legend() {
      return labelled([
        { group: LegendGroup.CELLS, swatch: Swatch.DOT, token: Token.INK, message: "legendSensory" },
        { group: LegendGroup.CELLS, swatch: Swatch.DOT, token: Token.REACH, message: "legendReached" },
        { group: LegendGroup.CELLS, swatch: Swatch.DOT, token: Token.STRAY, message: "legendNotReached" },
        { group: LegendGroup.CONNECTIONS, swatch: Swatch.LINE, token: Token.REACH, message: "legendLinkCarries" },
        { group: LegendGroup.CONNECTIONS, swatch: Swatch.LINE, token: Token.STRAY, message: "legendLinkNotReached" },
        ...PULSE_LEGEND,
      ]);
    }
  }

  // Test K2 live: the agreeing group as in QuorumPainter, over a purple layer marking the connections that receive the
  // agent's timing error. exposedMask() returns the current mask, or null when every connection receives it.
  class FaultPlacementPainter extends QuorumPainter {
    constructor(outcome, network, exposedMask) {
      super(outcome, network);
      const exposed = (k) => {
        const mask = exposedMask();
        return mask === null || mask[k] === 1;
      };
      this.connectionLayers = [{ token: Token.FEEDBACK, width: LINE.thin, includes: exposed }, ...this.connectionLayers];
    }

    legend() {
      const entries = super.legend();
      return [...entries, ...labelled([{ group: LegendGroup.CONNECTIONS, swatch: Swatch.LINE, token: Token.FEEDBACK, message: "legendLinkExposed" }])];
    }
  }

  root.DPC = Object.assign(root.DPC || {}, { QuorumPainter, BroadcastPainter, FaultPlacementPainter });
})(globalThis);

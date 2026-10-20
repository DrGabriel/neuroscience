// Painters say how one cycle's outcome is drawn: which connections in which layer, and how each cell looks.
(function (root) {
  "use strict";

  const { Token, Swatch, LegendGroup, ConnectionOutcome, CellGroup, labelled } = root.DPC;

  const LINE = Object.freeze({ thin: 0.7, normal: 0.9, bold: 1.2 });
  const CellStyle = Object.freeze({
    IN_GIANT: Object.freeze({ token: Token.HELD, radius: 3.4 }),
    CUT_OFF: Object.freeze({ token: Token.STRAY, radius: 2.9 }),
    SILENCED: Object.freeze({ token: Token.SILENCED, radius: 2.9, hollow: true }),
    SENSORY: Object.freeze({ token: Token.INK, radius: 3.4 }),
    REACHED: Object.freeze({ token: Token.REACH, radius: 3.4 }),
    ISLAND_1: Object.freeze({ token: Token.ISLAND_1, radius: 3.4 }),
    ISLAND_2: Object.freeze({ token: Token.ISLAND_2, radius: 3.4 }),
  });
  // Each island group with its cell style, its connection colour and its key entry, largest first.
  const ISLANDS = Object.freeze([
    Object.freeze({ group: CellGroup.ISLAND_1, style: CellStyle.ISLAND_1, soft: Token.ISLAND_1_SOFT, message: "legendIsland1" }),
    Object.freeze({ group: CellGroup.ISLAND_2, style: CellStyle.ISLAND_2, soft: Token.ISLAND_2_SOFT, message: "legendIsland2" }),
  ]);

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

  // Who agrees with whom: green the agreeing group while it holds quorum; once quorum is lost, the two largest islands
  // in their own colours; grey a cell in no group; faint vermilion late; hollow when silenced. colouredIslands limits
  // how many islands get a colour, for figures that already use an island colour for something else.
  class QuorumPainter extends Painter {
    constructor(outcome, network, { showLate = true, showSilenced = false, colouredIslands = ISLANDS.length } = {}) {
      super(outcome, network);
      this.options = { showLate, showSilenced };
      this.islands = ISLANDS.slice(0, colouredIslands);
      this.styleOfGroup = new Map([[CellGroup.AGREEING, CellStyle.IN_GIANT], ...this.islands.map((island) => [island.group, island.style])]);
      const groupOf = (k) => outcome.group[network.sources[k]];
      const counted = (k) => outcome.kept[k] === 1;
      const coloured = (k) => this.styleOfGroup.has(groupOf(k));
      this.connectionLayers = [
        ...(showLate ? [{ token: Token.LATE_SOFT, width: LINE.thin, includes: (k) => outcome.connections[k] === ConnectionOutcome.LATE }] : []),
        { token: Token.STRAY_SOFT, width: LINE.normal, includes: (k) => counted(k) && !coloured(k) },
        ...this.islands.map((island) => ({ token: island.soft, width: LINE.bold, includes: (k) => counted(k) && groupOf(k) === island.group })),
        { token: Token.HELD_SOFT, width: LINE.bold, includes: (k) => counted(k) && groupOf(k) === CellGroup.AGREEING },
      ];
    }

    cellStyle(node) {
      return this.styleOf(this.outcome.silenced[node], this.outcome.group[node]);
    }

    previousCellStyle(node) {
      return this.styleOf(this.outcome.silenced[node], this.outcome.wasGroup[node]);
    }

    styleOf(silenced, group) {
      if (silenced) return CellStyle.SILENCED;
      return this.styleOfGroup.get(group) ?? CellStyle.CUT_OFF;
    }

    legend() {
      return labelled([
        { group: LegendGroup.CELLS, swatch: Swatch.DOT, token: Token.HELD, message: "legendInGiant" },
        ...this.islands.map((island) => ({ group: LegendGroup.CELLS, swatch: Swatch.DOT, token: island.style.token, message: island.message })),
        { group: LegendGroup.CELLS, swatch: Swatch.DOT, token: Token.STRAY, message: "legendCutOff" },
        ...(this.options.showSilenced ? [{ group: LegendGroup.CELLS, swatch: Swatch.RING, token: Token.SILENCED, message: "legendSilenced" }] : []),
        { group: LegendGroup.CONNECTIONS, swatch: Swatch.LINE, token: Token.HELD, message: "legendLinkCounted" },
        ...(this.options.showLate ? [{ group: LegendGroup.CONNECTIONS, swatch: Swatch.LINE, token: Token.LATE, message: "legendLinkLate" }] : []),
        ...PULSE_LEGEND,
      ]);
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
      // The second island's purple is the colour of the exposed connections here.
      super(outcome, network, { colouredIslands: 1 });
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

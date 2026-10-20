// Painters say how one cycle's outcome is drawn: which connections in which layer, and how each cell looks.
(function (root) {
  "use strict";

  const { Token, Swatch, LegendGroup, ConnectionOutcome, CellGroup, labelled, palette, t, clamp } = root.DPC;

  // The words a key uses for what a node is: a cell in the worm, a brain region in the human map.
  const CELL_WORDS = Object.freeze({
    group: LegendGroup.CELLS, inGiant: "legendInGiant", cutOff: "legendCutOff", sensory: "legendSensory", reached: "legendReached", notReached: "legendNotReached",
  });
  const REGION_WORDS = Object.freeze({
    group: LegendGroup.REGIONS, inGiant: "legendInGiantRegion", cutOff: "legendCutOffRegion", sensory: "legendSensoryRegion", reached: "legendReachedRegion", notReached: "legendNotReachedRegion",
  });

  const LINE = Object.freeze({ thin: 0.7, normal: 0.9, bold: 1.2 });
  // The radius every cell style below is drawn at, before a projector's size factor.
  const CELL_RING_RADIUS_PX = 3.4;
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
    constructor(outcome, network, { showLate = true, showSilenced = false, colouredIslands = ISLANDS.length, words = CELL_WORDS } = {}) {
      super(outcome, network);
      this.options = { showLate, showSilenced };
      this.words = words;
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
      const { group, inGiant, cutOff } = this.words;
      return labelled([
        { group, swatch: Swatch.DOT, token: Token.HELD, message: inGiant },
        ...this.islands.map((island) => ({ group, swatch: Swatch.DOT, token: island.style.token, message: island.message })),
        { group, swatch: Swatch.DOT, token: Token.STRAY, message: cutOff },
        ...(this.options.showSilenced ? [{ group, swatch: Swatch.RING, token: Token.SILENCED, message: "legendSilenced" }] : []),
        { group: LegendGroup.CONNECTIONS, swatch: Swatch.LINE, token: Token.HELD, message: "legendLinkCounted" },
        ...(this.options.showLate ? [{ group: LegendGroup.CONNECTIONS, swatch: Swatch.LINE, token: Token.LATE, message: "legendLinkLate" }] : []),
        ...PULSE_LEGEND,
      ]);
    }
  }

  // How far a stimulus at the sensory cells reaches: senses in the text colour, blue reached, grey not reached.
  class BroadcastPainter extends Painter {
    constructor(outcome, network, { words = CELL_WORDS } = {}) {
      super(outcome, network);
      this.words = words;
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
      const { group, sensory, reached, notReached } = this.words;
      return labelled([
        { group, swatch: Swatch.DOT, token: Token.INK, message: sensory },
        { group, swatch: Swatch.DOT, token: Token.REACH, message: reached },
        { group, swatch: Swatch.DOT, token: Token.STRAY, message: notReached },
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

  // A ring around each sensory node, drawn over whatever colour the painter gives it: the hearing areas of the brain.
  class SensoryRings {
    static GAP_PX = 3.5;
    static WIDTH_PX = 1.6;

    constructor(network) {
      this.nodes = network.sensoryNodes;
    }

    static legend() {
      return labelled([{ group: LegendGroup.REGIONS, swatch: Swatch.RING, token: Token.INK, message: "legendAuditoryRing" }]);
    }

    draw(context, { anchors }) {
      context.strokeStyle = palette.get(Token.INK);
      context.lineWidth = SensoryRings.WIDTH_PX;
      for (const node of this.nodes) {
        const point = anchors[node];
        context.beginPath();
        context.arc(point.x, point.y, CELL_RING_RADIUS_PX * point.size + SensoryRings.GAP_PX, 0, 2 * Math.PI);
        context.stroke();
      }
    }
  }

  // Front, Back, Left and Right of the head, placed just outside the brain along its own axes, so they turn with it.
  // Nearer markers are drawn stronger; a marker pointing straight at or away from the reader is faded out.
  class OrientationMarkers {
    static REACH = 1.05;
    static FONT_PX = 13;
    // As NetworkView.PADDING, so the markers sit on the same scale as the regions.
    static PADDING_PX = 14;
    static HIDDEN_DEPTH = 0.12;
    static MARKERS = Object.freeze([
      Object.freeze({ message: "brainFront", axis: Object.freeze([-1, 0, 0]) }),
      Object.freeze({ message: "brainBack", axis: Object.freeze([1, 0, 0]) }),
      Object.freeze({ message: "brainLeft", axis: Object.freeze([0, 1, 0]) }),
      Object.freeze({ message: "brainRight", axis: Object.freeze([0, -1, 0]) }),
    ]);

    constructor(projector) {
      this.projector = projector;
    }

    draw(context, { width, height }) {
      context.save();
      context.font = `600 ${OrientationMarkers.FONT_PX}px ${palette.get(Token.FONT_LABEL)}`;
      context.textAlign = "center";
      context.textBaseline = "middle";
      context.fillStyle = palette.get(Token.INK);
      for (const { message, axis } of OrientationMarkers.MARKERS) {
        const point = this.projector.projectPoint(axis.map((value) => value * OrientationMarkers.REACH), { width, height, padding: OrientationMarkers.PADDING_PX });
        const sideways = 1 - Math.abs(2 * point.depth - 1);
        if (sideways < OrientationMarkers.HIDDEN_DEPTH) continue;
        const inset = OrientationMarkers.FONT_PX * 2;
        context.globalAlpha = Math.min(1, sideways + point.depth / 2);
        context.fillText(t(message), clamp(point.x, inset, width - inset), clamp(point.y, inset / 2, height - inset / 2));
      }
      context.restore();
    }
  }

  root.DPC = Object.assign(root.DPC || {}, { QuorumPainter, BroadcastPainter, FaultPlacementPainter, SensoryRings, OrientationMarkers, CELL_WORDS, REGION_WORDS });
})(globalThis);

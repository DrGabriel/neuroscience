// The fly: its wiring summarised by neuropil (a drawing of the data, not a simulation), and the study's own curves
// for worm, fly and human side by side (a reported result, read from the cross-species report).
(function (root) {
  "use strict";

  const { Token, Swatch, LegendGroup, labelled, palette, Surface, scale, polyline, make, t, count, organismName, drawShareAxes, AxisTitle, dashedRule, DASH, fixed } = root.DPC;

  const SIDE = Object.freeze({ LEFT: "_L", RIGHT: "_R" });
  const UNASSIGNED = "UNASGD";
  // Drawing rule, stated in the caption: a connection is drawn when it carries at least this share of its source
  // neuropil's output to other neuropils.
  const DRAWN_OUTPUT_SHARE = 0.02;
  // Schematic layout, as shares of the figure: paired neuropils on two mirrored arcs, midline ones down the centre.
  const LAYOUT = Object.freeze({ midline: 0.5, arcFromMidline: 0.18, arcBulge: 0.24 });
  const EDGE_ALPHA = Object.freeze({ fromSenses: 0.9, other: 0.35, faded: 0.05 });
  const EDGE_WIDTH = Object.freeze({ thinnest: 0.4, range: 2.2 });

  // Left neuropils on the left, their right-hand partners mirrored on the right, midline neuropils down the middle.
  // The layout is schematic: FlyWire's connectivity table has no coordinates.
  function mirroredLayout(names) {
    const base = (name) => name.replace(/_[LR]$/, "");
    const paired = [...new Set(names.filter((name) => name.endsWith(SIDE.LEFT)).map(base))].sort();
    const midline = names.filter((name) => !name.endsWith(SIDE.LEFT) && !name.endsWith(SIDE.RIGHT)).sort();
    const position = new Map();
    paired.forEach((name, k) => {
      const y = (k + 0.5) / paired.length;
      const offset = LAYOUT.arcFromMidline + LAYOUT.arcBulge * Math.sin(Math.PI * y);
      position.set(`${name}${SIDE.LEFT}`, { x: LAYOUT.midline - offset, y });
      position.set(`${name}${SIDE.RIGHT}`, { x: LAYOUT.midline + offset, y });
    });
    midline.forEach((name, k) => position.set(name, { x: LAYOUT.midline, y: (k + 0.5) / midline.length }));
    return names.map((name) => position.get(name));
  }

  // The connections drawn, each with its fixed look, lightest first so that heavy ones lie on top.
  function drawnEdges(fly) {
    const { connections, neuropils, sensoryNeuropils } = fly;
    const output = new Float64Array(neuropils.length);
    for (let k = 0; k < connections.length; k += 3) output[connections[k]] += connections[k + 2];
    const edges = [];
    for (let k = 0; k < connections.length; k += 3) {
      const [from, to, synapses] = [connections[k], connections[k + 1], connections[k + 2]];
      if (synapses >= DRAWN_OUTPUT_SHARE * output[from]) edges.push({ from, to, synapses, fromSenses: sensoryNeuropils.includes(from) });
    }
    edges.sort((a, b) => a.synapses - b.synapses);
    const heaviest = Math.log(edges[edges.length - 1]?.synapses ?? Math.E);
    for (const edge of edges) edge.width = EDGE_WIDTH.thinnest + EDGE_WIDTH.range * (Math.log(edge.synapses) / heaviest) ** 2;
    return edges;
  }

  class FlyMapView {
    static INSET = 18;
    static MAX_RADIUS = 13;
    static MIN_RADIUS = 2.5;
    static HIT_SLACK_PX = 4;
    static LABEL_GAP_PX = 3;
    static FONT_PX = 12;
    static HOVER_RING_PX = 3;
    // The key under the map lists this many neuropils, largest first, so their names need no pointer.
    static KEY_SIZE = 10;
    // On a canvas narrower than this, only the largest neuropils are labelled, so labels do not run into each other.
    static NARROW_PX = 520;
    static NARROW_LABELS = 16;

    constructor(canvas, fly) {
      this.surface = new Surface(canvas);
      this.fly = fly;
      this.layout = mirroredLayout(fly.neuropils);
      this.edges = drawnEdges(fly);
      const largest = Math.max(...fly.neuronCounts);
      this.radii = fly.neuronCounts.map((n) => Math.max(FlyMapView.MIN_RADIUS, FlyMapView.MAX_RADIUS * Math.sqrt(n / largest)));
      this.strongestTarget = fly.neuropils.map((_, node) => this.edges.filter((edge) => edge.from === node).pop()?.to ?? null);
      this.hovered = null;
      this.points = [];
      canvas.addEventListener("pointermove", (event) => this._hover(event.offsetX, event.offsetY));
      canvas.addEventListener("pointerleave", () => this._hover(null, null));
      this.readout = make("p", { className: "fly-readout mono", textContent: t("flyHoverHint") });
      this.bySize = fly.neuropils.map((_, node) => node).filter((node) => fly.neuropils[node] !== UNASSIGNED).sort((a, b) => fly.neuronCounts[b] - fly.neuronCounts[a]);
      canvas.after(this.readout, this._key());
    }

    // The largest neuropils in words: name, size and strongest output, readable without pointing at the map.
    _key() {
      const items = this.bySize.slice(0, FlyMapView.KEY_SIZE).map((node) => make("li", { textContent: this._describe(node) }));
      return make("div", { className: "fly-key" }, [make("p", { className: "fly-key-title", textContent: t("flyKeyTitle", { count: FlyMapView.KEY_SIZE }) }), make("ol", {}, items)]);
    }

    legend() {
      return labelled([
        { group: LegendGroup.REGIONS, swatch: Swatch.DOT, token: Token.INK, message: "flySensoryNeuropil" },
        { group: LegendGroup.REGIONS, swatch: Swatch.DOT, token: Token.MUTED, message: "flyNeuropil" },
        { group: LegendGroup.CONNECTIONS, swatch: Swatch.LINE, token: Token.REACH, message: "flyFromSenses" },
        { group: LegendGroup.CONNECTIONS, swatch: Swatch.LINE, token: Token.STRAY, message: "flyOtherConnection" },
      ]);
    }

    draw() {
      const { context, width, height } = this.surface.begin();
      const inset = FlyMapView.INSET;
      this.points = this.layout.map(({ x, y }) => ({ x: inset + x * (width - 2 * inset), y: inset + y * (height - 2 * inset) }));
      this._drawEdges(context);
      this._drawNeuropils(context, width);
    }

    _drawEdges(context) {
      const colours = { senses: palette.get(Token.REACH), other: palette.get(Token.STRAY) };
      const identity = (value) => value;
      for (const edge of this.edges) {
        const touched = this.hovered === null || edge.from === this.hovered || edge.to === this.hovered;
        context.globalAlpha = touched ? (edge.fromSenses ? EDGE_ALPHA.fromSenses : EDGE_ALPHA.other) : EDGE_ALPHA.faded;
        context.strokeStyle = edge.fromSenses ? colours.senses : colours.other;
        context.lineWidth = edge.width;
        polyline(context, [this.points[edge.from], this.points[edge.to]], identity, identity);
      }
      context.globalAlpha = 1;
    }

    _drawNeuropils(context, width) {
      const colours = { sensory: palette.get(Token.INK), other: palette.get(Token.MUTED), ring: palette.get(Token.PAPER) };
      const labelled = new Set(width < FlyMapView.NARROW_PX ? this.bySize.slice(0, FlyMapView.NARROW_LABELS) : this.bySize);
      context.font = `${FlyMapView.FONT_PX}px ${palette.get(Token.FONT_DATA)}`;
      context.textBaseline = "middle";
      this.fly.neuropils.forEach((name, node) => {
        const { x, y } = this.points[node];
        const radius = this.radii[node];
        const onLeft = x < width / 2;
        context.beginPath();
        context.arc(x, y, radius, 0, 2 * Math.PI);
        context.fillStyle = this.fly.sensoryNeuropils.includes(node) ? colours.sensory : colours.other;
        context.fill();
        context.strokeStyle = colours.ring;
        context.lineWidth = node === this.hovered ? FlyMapView.HOVER_RING_PX : 1;
        context.stroke();
        if (!labelled.has(node) && node !== this.hovered) return;
        context.fillStyle = colours.other;
        context.textAlign = onLeft ? "right" : "left";
        context.fillText(name, x + (radius + FlyMapView.LABEL_GAP_PX) * (onLeft ? -1 : 1), y);
      });
    }

    // Redraws only when the neuropil under the pointer changes.
    _hover(x, y) {
      const hit = x === null ? -1 : this.points.findIndex((point, node) => Math.hypot(point.x - x, point.y - y) <= this.radii[node] + FlyMapView.HIT_SLACK_PX);
      const hovered = hit >= 0 ? hit : null;
      if (hovered === this.hovered) return;
      this.hovered = hovered;
      this.readout.textContent = hovered === null ? t("flyHoverHint") : this._describe(hovered);
      this.draw();
    }

    _describe(node) {
      const { neuropils, neuronCounts } = this.fly;
      const name = neuropils[node] === UNASSIGNED ? t("flyUnassigned") : neuropils[node];
      const target = this.strongestTarget[node];
      return t("flyHover", { name, neurons: count(neuronCounts[node]), target: target === null ? t("none") : neuropils[target] });
    }
  }

  // Mean global coherence relative to awake (each run divided by its own awake value, as in the paper's Figure 3),
  // against concentration, for each organism; told apart by line pattern and a label at the line's end, never by colour.
  // Dashed and dotted already mean "dose falling" and "quorum line" on this page, so the organisms use other patterns.
  const LINE_PATTERN = Object.freeze({
    SOLID: Object.freeze([]),
    DASH_DOT: Object.freeze([9, 3, 2, 3]),
    DASH_DOT_DOT: Object.freeze([9, 3, 2, 3, 2, 3]),
  });
  const CURVE_STYLE = Object.freeze({
    celegans: Object.freeze({ dash: LINE_PATTERN.SOLID, swatch: Swatch.LINE }),
    drosophila: Object.freeze({ dash: LINE_PATTERN.DASH_DOT, swatch: Swatch.DASH_DOT }),
    human: Object.freeze({ dash: LINE_PATTERN.DASH_DOT_DOT, swatch: Swatch.DASH_DOT_DOT }),
  });

  class SpeciesCurvesView {
    static MARGIN = Object.freeze({ left: 60, right: 96, top: 12, bottom: 46 });
    static LABEL_GAP_PX = 18;
    static LABEL_OFFSET_PX = 6;

    // Coherence relative to awake, so half the awake coherence is a fixed line: the phase model's quorum line.
    static HALF_AWAKE = 0.5;

    constructor(canvas, speciesCurves) {
      this.surface = new Surface(canvas);
      this.curves = speciesCurves.curves;
    }

    legend() {
      return labelled([
        ...this.curves.map((curve) => ({
          group: LegendGroup.CHART,
          swatch: CURVE_STYLE[curve.organism].swatch,
          token: Token.INK,
          message: "speciesCurveEntry",
          params: { organism: organismName(curve.organism), seeds: curve.seeds },
        })),
        { group: LegendGroup.CHART, swatch: Swatch.DOTTED, token: Token.QUORUM, message: "legendHalfAwake", params: { share: fixed(SpeciesCurvesView.HALF_AWAKE, 1) } },
      ]);
    }

    draw() {
      const { context, width, height } = this.surface.begin();
      const margin = SpeciesCurvesView.MARGIN;
      const maxConcentration = Math.max(...this.curves.map((curve) => curve.concentrations[curve.concentrations.length - 1]));
      const px = scale([0, maxConcentration], [margin.left, width - margin.right]);
      const py = scale([0, 1], [height - margin.bottom, margin.top]);
      drawShareAxes(context, { px, py, margin, width, height, maxConcentration, shareTitle: AxisTitle.COHERENCE });
      dashedRule(context, { x0: margin.left, x1: width - margin.right, y: py(SpeciesCurvesView.HALF_AWAKE), colour: palette.get(Token.QUORUM), dash: DASH.threshold });
      context.strokeStyle = context.fillStyle = palette.get(Token.INK);
      context.lineWidth = 2;
      const ends = this.curves.map((curve) => {
        const series = curve.induction.map((y, k) => ({ x: curve.concentrations[k], y }));
        context.setLineDash(CURVE_STYLE[curve.organism].dash);
        polyline(context, series, px, py);
        context.setLineDash([]);
        const end = series[series.length - 1];
        return { text: organismName(curve.organism), x: px(end.x) + SpeciesCurvesView.LABEL_OFFSET_PX, y: py(end.y) };
      });
      this._labelEnds(context, ends, height - margin.bottom - SpeciesCurvesView.LABEL_GAP_PX / 2);
    }

    // Labels at the line ends, pushed apart vertically so that they never overlap, and lifted together if the
    // lowest would fall below lowestY, into the axis labels.
    _labelEnds(context, ends, lowestY) {
      context.textAlign = "left";
      context.textBaseline = "middle";
      ends.sort((a, b) => a.y - b.y);
      ends.forEach((end, k) => {
        if (k > 0) end.y = Math.max(end.y, ends[k - 1].y + SpeciesCurvesView.LABEL_GAP_PX);
      });
      const lift = Math.max(0, ends[ends.length - 1].y - lowestY);
      for (const end of ends) context.fillText(end.text, end.x, end.y - lift);
    }
  }

  // The named neuropils, leaving out the group of neurons that FlyWire assigns to none.
  const namedNeuropils = (neuropils) => neuropils.filter((name) => name !== UNASSIGNED);

  root.DPC = Object.assign(root.DPC || {}, { FlyMapView, SpeciesCurvesView, mirroredLayout, namedNeuropils, DRAWN_OUTPUT_SHARE });
})(globalThis);

// Chart views: each owns a Surface and draws one kind of figure from plain data.
(function (root) {
  "use strict";

  const { Token, Swatch, LegendGroup, labelled, palette, Surface, SweepDirection, scale, polyline, dot, diamond, hexagon, triangle, square, arrowhead, dashedRule, wrapPhase, fixed, make, t, percent } = root.DPC;

  const quorumLineEntry = (quorumFraction) => ({ group: LegendGroup.CHART, swatch: Swatch.DOTTED, token: Token.QUORUM, message: "legendQuorumLine", params: { quorum: fixed(quorumFraction, 1) } });
  const TIMING_LEGEND = Object.freeze([
    { group: LegendGroup.CHART, swatch: Swatch.BAND, token: Token.HELD_SOFT, message: "legendWindow" },
    { group: LegendGroup.SIGNALS, swatch: Swatch.DIAMOND, token: Token.HELD, message: "legendOnTime" },
    { group: LegendGroup.SIGNALS, swatch: Swatch.DIAMOND, token: Token.LATE, message: "legendOffTime" },
  ]);

  const AXIS = Object.freeze({ fontSizePx: 12, labelGapPx: 6, titleSizePx: 13, titleInsetPx: 2 });
  const DASH = Object.freeze({ threshold: Object.freeze([1.5, 3]), emergence: Object.freeze([6, 3]), halfEffect: Object.freeze([4, 4]) });
  // Where along a sweep line its direction arrow sits, and its size.
  const ARROW = Object.freeze({ along: 0.55, sizePx: 7 });
  const LINE_WIDTH = Object.freeze({ series: 2, strip: 1.6, rule: 1, raster: 1.4 });
  const MARKER_RADIUS = 4;

  // A readout that follows the pointer over a chart: a guide line and a label for the nearest data point. The view
  // supplies nearest(x, y) in CSS pixels, returning {x, y, text} or null; nothing is redrawn on the canvas.
  // The host is positioned by CSS (.chart-host) so that the readout can sit over the canvas.
  class ChartHover {
    constructor(canvas, nearest) {
      Object.assign(this, { canvas, nearest, shown: null });
      canvas.parentElement.classList.add("chart-host");
      this.guide = make("span", { className: "chart-guide", hidden: true });
      this.label = make("span", { className: "chart-readout", hidden: true });
      this.label.setAttribute("aria-hidden", "true");
      canvas.parentElement.append(this.guide, this.label);
      canvas.addEventListener("pointermove", (event) => this._show(event.offsetX, event.offsetY));
      canvas.addEventListener("pointerleave", () => this.hide());
    }

    _show(x, y) {
      const point = this.nearest(x, y);
      if (!point) {
        this.hide();
        return;
      }
      if (point.text === this.shown) return;
      const { canvas } = this;
      Object.assign(this.guide.style, { left: `${canvas.offsetLeft + point.x}px`, top: `${canvas.offsetTop}px`, height: `${canvas.offsetHeight}px` });
      Object.assign(this.label.style, { left: `${canvas.offsetLeft + point.x}px`, top: `${canvas.offsetTop + point.y}px` });
      this.label.classList.toggle("flip", point.x > canvas.offsetWidth / 2);
      this.label.textContent = this.shown = point.text;
      this.guide.hidden = this.label.hidden = false;
    }

    hide() {
      this.shown = null;
      this.guide.hidden = this.label.hidden = true;
    }
  }

  function closest(candidates, x, y) {
    let best = null, bestDistance = Infinity;
    for (const candidate of candidates) {
      const distance = Math.hypot(candidate.x - x, candidate.y - y);
      if (distance < bestDistance) [best, bestDistance] = [candidate, distance];
    }
    return best;
  }

  function nearestInX(candidates, x) {
    let best = null;
    for (const candidate of candidates) if (!best || Math.abs(candidate.x - x) < Math.abs(best.x - x)) best = candidate;
    return best;
  }

  function useAxisFont(context) {
    context.font = `${AXIS.fontSizePx}px ${palette.get(Token.FONT_DATA)}`;
    context.fillStyle = palette.get(Token.MUTED);
  }

  // Axis titles drawn on the chart, so a reader never needs the caption to know what an axis measures.
  // titles: { x, y } message keys, either optional; frame: { margin, width, height }.
  function axisTitles(context, frame, titles) {
    const { margin, width, height } = frame;
    context.save();
    context.font = `${AXIS.titleSizePx}px ${palette.get(Token.FONT_LABEL)}`;
    context.fillStyle = palette.get(Token.INK);
    context.textAlign = "center";
    if (titles.x) {
      context.textBaseline = "bottom";
      context.fillText(t(titles.x), margin.left + (width - margin.left - margin.right) / 2, height - AXIS.titleInsetPx);
    }
    if (titles.y) {
      context.translate(AXIS.titleInsetPx, margin.top + (height - margin.top - margin.bottom) / 2);
      context.rotate(-Math.PI / 2);
      context.textBaseline = "top";
      context.fillText(t(titles.y), 0, 0);
    }
    context.restore();
  }

  // The titles of every chart, as message keys.
  const AxisTitle = Object.freeze({
    CONCENTRATION: "axisConcentration", AGREEING_GROUP: "axisAgreeingGroup", AGREEING_SHORT: "axisAgreeingShort", COHERENCE: "axisCoherence", RECENT_CYCLES: "axisRecentCycles",
    ARRIVAL_MS: "axisArrivalMs", QUORUM_THRESHOLD: "axisQuorumThreshold", DOSE: "axisDose",
  });

  function shareLabels(context, { shares, x, py }) {
    context.textAlign = "right";
    context.textBaseline = "middle";
    for (const share of shares) context.fillText(fixed(share, 1), x - AXIS.labelGapPx, py(share));
  }

  const SHARE_TICKS = Object.freeze([0, 0.5, 1]);
  const CONCENTRATION_TICK = 0.5;

  // Ruled share axis (0, 0.5, 1) and concentration labels every half unit, shared by every dose chart.
  // frame: { px, py, margin, width, height, maxConcentration, shareTitle }; shareTitle names the vertical axis.
  function drawShareAxes(context, frame) {
    const { px, py, margin, width, height, maxConcentration, shareTitle } = frame;
    context.strokeStyle = palette.get(Token.RULE);
    context.lineWidth = LINE_WIDTH.rule;
    context.beginPath();
    for (const share of SHARE_TICKS) {
      context.moveTo(margin.left, py(share));
      context.lineTo(width - margin.right, py(share));
    }
    context.stroke();
    useAxisFont(context);
    shareLabels(context, { shares: SHARE_TICKS, x: margin.left, py });
    context.textAlign = "center";
    context.textBaseline = "top";
    const ticks = Math.round(maxConcentration / CONCENTRATION_TICK);
    for (let k = 0; k <= ticks; k++) context.fillText(fixed(k * CONCENTRATION_TICK, 1), px(k * CONCENTRATION_TICK), height - margin.bottom + AXIS.labelGapPx);
    axisTitles(context, frame, { x: AxisTitle.CONCENTRATION, y: shareTitle });
  }

  // The agreeing group (vertical) against concentration, rising then falling.
  class TraceView {
    static MARGIN = Object.freeze({ left: 58, right: 10, top: 10, bottom: 44 });

    constructor(canvas, { maxConcentration, quorumFraction }) {
      Object.assign(this, { surface: new Surface(canvas), maxConcentration, quorumFraction, plotted: [] });
      new ChartHover(canvas, (x, y) => this._nearest(x, y));
    }

    _nearest(x, y) {
      const point = closest(this.plotted, x, y);
      if (!point) return null;
      const { direction, concentration, share } = point.data;
      const message = direction === SweepDirection.INDUCTION ? "legendRising" : "legendFalling";
      return { x: point.x, y: point.y, text: t("hoverSweep", { direction: t(message), dose: fixed(concentration, 2), share: percent(share) }) };
    }

    legend() {
      return labelled([
        { group: LegendGroup.CHART, swatch: Swatch.ARROW_FORWARD, token: Token.INK, message: "legendRising" },
        { group: LegendGroup.CHART, swatch: Swatch.ARROW_BACK, token: Token.EMERGENCE, message: "legendFalling" },
        quorumLineEntry(this.quorumFraction),
      ]);
    }

    draw(points, current) {
      const { context, width, height } = this.surface.begin();
      const margin = TraceView.MARGIN;
      const px = scale([0, this.maxConcentration], [margin.left, width - margin.right]);
      const py = scale([0, 1], [height - margin.bottom, margin.top]);
      this.plotted = points.map((data) => ({ x: px(data.concentration), y: py(data.share), data }));
      drawShareAxes(context, { px, py, margin, width, height, maxConcentration: this.maxConcentration, shareTitle: AxisTitle.AGREEING_GROUP });
      dashedRule(context, { x0: margin.left, x1: width - margin.right, y: py(this.quorumFraction), colour: palette.get(Token.QUORUM), dash: DASH.threshold });
      for (const direction of Object.values(SweepDirection)) this._drawSeries(context, { direction, points, px, py });
      if (current) dot(context, px(current.concentration), py(current.share), MARKER_RADIUS, palette.get(Token.INK));
    }

    _drawSeries(context, { direction, points, px, py }) {
      const series = points.filter((point) => point.direction === direction).map((point) => ({ x: point.concentration, y: point.share }));
      if (!series.length) return;
      const induction = direction === SweepDirection.INDUCTION;
      context.strokeStyle = palette.get(induction ? Token.INK : Token.EMERGENCE);
      context.lineWidth = LINE_WIDTH.series;
      context.setLineDash(induction ? [] : DASH.emergence);
      polyline(context, series, px, py);
      context.setLineDash([]);
      this._drawArrow(context, series.map((point) => ({ x: px(point.x), y: py(point.y) })));
    }

    // Points the way the dose was moving: right while it rose, left while it fell.
    _drawArrow(context, points) {
      if (points.length < 2) return;
      const k = Math.max(1, Math.round((points.length - 1) * ARROW.along));
      const [from, to] = [points[k - 1], points[k]];
      arrowhead(context, { x: to.x, y: to.y, angle: Math.atan2(to.y - from.y, to.x - from.x), size: ARROW.sizePx });
    }
  }

  // A value over the most recent cycles, against a threshold.
  class StripView {
    static MARGIN = Object.freeze({ left: 58, right: 10, top: 8, bottom: 24 });

    constructor(canvas, { capacity, threshold }) {
      Object.assign(this, { surface: new Surface(canvas), capacity, threshold, values: [], plotted: [] });
      new ChartHover(canvas, (x) => this._nearest(x));
    }

    _nearest(x) {
      const nearest = nearestInX(this.plotted, x);
      if (!nearest) return null;
      const ago = this.values.length - 1 - nearest.index;
      return { x: nearest.x, y: nearest.y, text: t("hoverStrip", { ago: String(ago), share: percent(nearest.value) }) };
    }

    push(value) {
      this.values.push(value);
      if (this.values.length > this.capacity) this.values.shift();
    }

    clear() {
      this.values = [];
    }

    legend() {
      return labelled([{ group: LegendGroup.CHART, swatch: Swatch.LINE, token: Token.INK, message: "legendStripSeries" }, quorumLineEntry(this.threshold)]);
    }

    spread(window) {
      const recent = this.values.slice(-window);
      const mean = recent.reduce((sum, value) => sum + value, 0) / recent.length;
      return Math.sqrt(recent.reduce((sum, value) => sum + (value - mean) ** 2, 0) / recent.length);
    }

    draw() {
      const { context, width, height } = this.surface.begin();
      const margin = StripView.MARGIN;
      const px = scale([0, this.capacity - 1], [margin.left, width - margin.right]);
      const py = scale([0, 1], [height - margin.bottom, margin.top]);
      useAxisFont(context);
      shareLabels(context, { shares: [0, 1], x: margin.left, py });
      axisTitles(context, { margin, width, height }, { x: AxisTitle.RECENT_CYCLES, y: AxisTitle.AGREEING_SHORT });
      dashedRule(context, { x0: margin.left, x1: width - margin.right, y: py(this.threshold), colour: palette.get(Token.QUORUM), dash: DASH.threshold });
      context.strokeStyle = palette.get(Token.INK);
      context.lineWidth = LINE_WIDTH.strip;
      polyline(context, this.values.map((value, k) => ({ x: k, y: value })), px, py);
      this.plotted = this.values.map((value, index) => ({ x: px(index), y: py(value), value, index }));
    }
  }

  // Signal arrival times scattered around the integration window.
  class ArrivalView {
    static SPAN_MS = 20;
    static TICK_MS = 5;
    static INSET = 16;
    static AXIS_BOTTOM = 44;
    static ROW_PX = 7;
    static DOT_RADIUS = 2.6;

    constructor(canvas) {
      this.surface = new Surface(canvas);
    }

    legend() {
      return labelled(TIMING_LEGEND);
    }

    draw({ arrivalsMs, halfWindowMs }) {
      const { context, width, height } = this.surface.begin();
      const span = ArrivalView.SPAN_MS;
      const px = scale([-span, span], [ArrivalView.INSET, width - ArrivalView.INSET]);
      const axisY = height - ArrivalView.AXIS_BOTTOM;
      context.fillStyle = palette.get(Token.HELD_SOFT);
      context.fillRect(px(-halfWindowMs), 0, px(halfWindowMs) - px(-halfWindowMs), axisY);
      useAxisFont(context);
      context.textAlign = "center";
      context.textBaseline = "top";
      for (let ms = -span; ms <= span; ms += ArrivalView.TICK_MS) context.fillText(String(ms), px(ms), axisY + AXIS.labelGapPx);
      axisTitles(context, { margin: { left: ArrivalView.INSET, right: ArrivalView.INSET, top: 0, bottom: ArrivalView.AXIS_BOTTOM }, width, height }, { x: AxisTitle.ARRIVAL_MS });
      const rows = Math.max(1, Math.floor(axisY / ArrivalView.ROW_PX) - 1);
      const colours = { held: palette.get(Token.HELD), late: palette.get(Token.LATE) };
      arrivalsMs.forEach((ms, k) => {
        if (Math.abs(ms) > span) return;
        diamond(context, px(ms), axisY - ArrivalView.ROW_PX * (1 + (k % rows)), ArrivalView.DOT_RADIUS + 0.6, Math.abs(ms) <= halfWindowMs ? colours.held : colours.late);
      });
    }
  }

  // One cycle of the rhythm as a clock face, with the window as a wedge at the beat.
  class PhaseDialView {
    static INSET = 14;
    static RINGS = 5;
    static RING_GAP = 6;
    static DOT_RADIUS = 2.6;
    static BEAT_RADIUS = 4;

    constructor(canvas) {
      this.surface = new Surface(canvas);
    }

    legend() {
      return labelled([...TIMING_LEGEND, { group: LegendGroup.CHART, swatch: Swatch.TRIANGLE, token: Token.INK, message: "legendBeat" }]);
    }

    draw({ phases, windowHalfPhase }) {
      const { context, width, height } = this.surface.begin();
      const cx = width / 2, cy = height / 2, radius = Math.min(width, height) / 2 - PhaseDialView.INSET;
      const toCanvas = (phase) => phase - Math.PI / 2;
      context.fillStyle = palette.get(Token.HELD_SOFT);
      context.beginPath();
      context.moveTo(cx, cy);
      context.arc(cx, cy, radius, toCanvas(-windowHalfPhase), toCanvas(windowHalfPhase));
      context.closePath();
      context.fill();
      context.strokeStyle = palette.get(Token.RULE);
      context.beginPath();
      context.arc(cx, cy, radius, 0, 2 * Math.PI);
      context.stroke();
      const colours = { held: palette.get(Token.HELD), late: palette.get(Token.LATE) };
      phases.forEach((phase, k) => {
        const wrapped = wrapPhase(phase);
        const r = radius - PhaseDialView.RING_GAP * (1 + (k % PhaseDialView.RINGS));
        diamond(context, cx + r * Math.cos(toCanvas(wrapped)), cy + r * Math.sin(toCanvas(wrapped)), PhaseDialView.DOT_RADIUS + 0.6, Math.abs(wrapped) <= windowHalfPhase ? colours.held : colours.late);
      });
      const ink = palette.get(Token.INK);
      triangle(context, { x: cx, y: cy - radius, radius: PhaseDialView.BEAT_RADIUS + 1, fill: ink, edge: ink });
    }
  }

  // Formula against measurement, per organism: hollow formula, filled measured, and the stricter directed value.
  class ThresholdView {
    static MARGIN = Object.freeze({ left: 96, right: 16, top: 10, bottom: 44 });
    static HEADROOM = 1.15;
    static TICK = 0.02;
    static MARK_RADIUS = 5;

    constructor(canvas) {
      this.surface = new Surface(canvas);
    }

    legend() {
      return labelled([
        { group: LegendGroup.CHART, swatch: Swatch.TRIANGLE_OPEN, token: Token.MUTED, message: "legendFormula" },
        { group: LegendGroup.CHART, swatch: Swatch.SQUARE, token: Token.INK, message: "legendMeasured" },
        { group: LegendGroup.CHART, swatch: Swatch.SQUARE_OPEN, token: Token.INK, message: "legendDirected" },
      ]);
    }

    draw(rows) {
      const { context, width, height } = this.surface.begin();
      const margin = ThresholdView.MARGIN;
      const maximum = Math.max(...rows.flatMap((row) => [row.formula, row.measured, row.directed])) * ThresholdView.HEADROOM;
      const px = scale([0, maximum], [margin.left, width - margin.right]);
      const band = (height - margin.top - margin.bottom) / rows.length;
      // Told apart by shape: hollow triangle for the formula, filled square measured, hollow square directed.
      const marks = [
        { key: "formula", token: Token.MUTED, hollow: true, draw: triangle },
        { key: "measured", token: Token.INK, hollow: false, draw: square },
        { key: "directed", token: Token.INK, hollow: true, draw: square },
      ];
      useAxisFont(context);
      context.textBaseline = "middle";
      rows.forEach((row, k) => {
        const y = margin.top + band * (k + 0.5);
        context.textAlign = "right";
        context.fillStyle = palette.get(Token.INK);
        context.fillText(row.label, margin.left - 10, y);
        context.strokeStyle = palette.get(Token.RULE);
        context.beginPath();
        context.moveTo(margin.left, y);
        context.lineTo(width - margin.right, y);
        context.stroke();
        for (const mark of marks) this._drawMark(context, { x: px(row[mark.key]), y, mark });
      });
      useAxisFont(context);
      context.textAlign = "center";
      context.textBaseline = "top";
      for (let value = 0; value <= maximum; value += ThresholdView.TICK) context.fillText(fixed(value, 2), px(value), height - margin.bottom + AXIS.labelGapPx);
      axisTitles(context, { margin, width, height }, { x: AxisTitle.QUORUM_THRESHOLD });
    }

    _drawMark(context, { x, y, mark }) {
      const colour = palette.get(mark.token);
      context.lineWidth = 2;
      mark.draw(context, { x, y, radius: ThresholdView.MARK_RADIUS, fill: mark.hollow ? palette.get(Token.PAPER) : colour, edge: colour });
    }
  }

  // Schematic only, with round numbers chosen for legibility: depth 0 to 0.5 moves from independent firing (streaming)
  // to regular bursts (polling); 0.5 to 1 lengthens the silences between bursts, each longer than the last
  // (exponential backoff), as in burst suppression.
  const RASTER = Object.freeze({
    cells: 24, spikesPerBurst: 3, streamingSpikesPerCell: 14, pollingBursts: 4, burstWidth: 0.012,
    firstGap: 0.12, firstGapGrowth: 3, backoffFactor: 2, pollingDepth: 0.5, insetPx: 10, topPx: 8,
  });

  function burstTimes(depth) {
    if (depth <= RASTER.pollingDepth) return Array.from({ length: RASTER.pollingBursts }, (_, k) => (k + 0.5) / RASTER.pollingBursts);
    const backoff = (depth - RASTER.pollingDepth) / (1 - RASTER.pollingDepth);
    const times = [];
    let time = RASTER.firstGap / 2;
    let gap = RASTER.firstGap * (1 + RASTER.firstGapGrowth * backoff);
    while (time < 1) {
      times.push(time);
      time += gap;
      gap *= 1 + (RASTER.backoffFactor - 1) * backoff;
    }
    return times;
  }

  class RasterView {
    constructor(canvas) {
      this.surface = new Surface(canvas);
    }

    legend() {
      return labelled([{ group: LegendGroup.CHART, swatch: Swatch.TICK, token: Token.INK, message: "legendSpike" }]);
    }

    sample(random, depth) {
      const bursts = burstTimes(depth);
      const burstiness = Math.min(1, depth / RASTER.pollingDepth);
      return Array.from({ length: RASTER.cells }, () => [
        ...Array.from({ length: Math.round(RASTER.streamingSpikesPerCell * (1 - burstiness)) }, () => random.uniform()),
        ...bursts.flatMap((time) => Array.from({ length: Math.round(RASTER.spikesPerBurst * burstiness) }, () => time + random.standardNormal() * RASTER.burstWidth)),
      ]);
    }

    draw(raster) {
      const { context, width, height } = this.surface.begin();
      const left = RASTER.insetPx, right = width - RASTER.insetPx;
      const rowHeight = (height - 2 * RASTER.topPx) / raster.length;
      context.strokeStyle = palette.get(Token.INK);
      context.lineWidth = LINE_WIDTH.raster;
      context.beginPath();
      raster.forEach((spikes, row) => {
        for (const time of spikes) {
          if (time < 0 || time > 1) continue;
          const x = left + time * (right - left);
          context.moveTo(x, RASTER.topPx + row * rowHeight + 1);
          context.lineTo(x, RASTER.topPx + (row + 1) * rowHeight - 1);
        }
      });
      context.stroke();
    }
  }

  // The anaesthetic's dose-response: the model's Hill curve of drug effect against concentration, with the current
  // dose marked and the half-effect concentration dashed. Drawn from the agent's own parameters.
  class DoseCurveView {
    static MARGIN = Object.freeze({ left: 4, right: 4, top: 14, bottom: 20 });
    static SAMPLES = 120;
    static MARKER_RADIUS = 4;

    constructor(canvas, { maxConcentration }) {
      Object.assign(this, { surface: new Surface(canvas), maxConcentration, plotted: [] });
      new ChartHover(canvas, (x) => this._nearest(x));
    }

    _nearest(x) {
      const nearest = nearestInX(this.plotted, x);
      if (!nearest) return null;
      return { x: nearest.x, y: nearest.y, text: t("hoverDose", { dose: fixed(nearest.concentration, 2), effect: percent(nearest.effect) }) };
    }

    draw({ agent, concentration, halfEffectLabel }) {
      const { context, width, height } = this.surface.begin();
      const margin = DoseCurveView.MARGIN;
      const px = scale([0, this.maxConcentration], [margin.left, width - margin.right]);
      const py = scale([0, 1], [height - margin.bottom, margin.top]);
      const curve = Array.from({ length: DoseCurveView.SAMPLES + 1 }, (_, k) => {
        const c = (k / DoseCurveView.SAMPLES) * this.maxConcentration;
        return { x: c, y: agent.effectFraction(c) };
      });
      this.plotted = curve.map((point) => ({ x: px(point.x), y: py(point.y), concentration: point.x, effect: point.y }));
      context.fillStyle = palette.get(Token.DRUG_SOFT);
      context.beginPath();
      context.moveTo(px(0), py(0));
      for (const point of curve.filter((point) => point.x <= concentration)) context.lineTo(px(point.x), py(point.y));
      context.lineTo(px(concentration), py(0));
      context.closePath();
      context.fill();
      context.strokeStyle = palette.get(Token.INK);
      context.lineWidth = LINE_WIDTH.series;
      polyline(context, curve, px, py);
      const half = agent.halfEffectConcentration;
      context.lineWidth = LINE_WIDTH.rule;
      context.strokeStyle = palette.get(Token.MUTED);
      context.setLineDash(DASH.halfEffect);
      context.beginPath();
      context.moveTo(px(half), py(0));
      context.lineTo(px(half), py(1));
      context.stroke();
      context.setLineDash([]);
      useAxisFont(context);
      context.textAlign = "left";
      context.textBaseline = "top";
      context.fillText(halfEffectLabel, px(half) + AXIS.labelGapPx, 0);
      axisTitles(context, { margin, width, height }, { x: AxisTitle.DOSE });
      context.lineWidth = LINE_WIDTH.rule;
      hexagon(context, { x: px(concentration), y: py(agent.effectFraction(concentration)), radius: DoseCurveView.MARKER_RADIUS + 1, fill: palette.get(Token.DRUG), edge: palette.get(Token.DRUG_EDGE) });
    }
  }

  root.DPC = Object.assign(root.DPC || {}, { DASH, ChartHover, closest, drawShareAxes, AxisTitle, DoseCurveView, TraceView, StripView, ArrivalView, PhaseDialView, ThresholdView, RasterView });
})(globalThis);

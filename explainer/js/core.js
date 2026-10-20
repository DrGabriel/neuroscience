// Shared building blocks: colour tokens, canvas surfaces, number formatting and checked DOM lookups.
(function (root) {
  "use strict";

  const Token = Object.freeze({
    PAPER: "--paper", INK: "--ink", MUTED: "--muted", RULE: "--rule", GRID: "--grid",
    HELD: "--held", HELD_SOFT: "--held-soft", LATE: "--late", LATE_SOFT: "--late-soft",
    STRAY: "--stray", STRAY_SOFT: "--stray-soft",
    ISLAND_1: "--island-1", ISLAND_1_SOFT: "--island-1-soft", ISLAND_2: "--island-2", ISLAND_2_SOFT: "--island-2-soft", WASH: "--wash", SILENCED: "--silenced", REACH: "--reach", REACH_SOFT: "--reach-soft",
    FEEDBACK: "--feedback", EMERGENCE: "--emergence", QUORUM: "--quorum", FONT_DATA: "--font-data", FONT_LABEL: "--font-label",
    DRUG: "--drug", DRUG_SOFT: "--drug-soft", DRUG_EDGE: "--drug-edge",
  });

  // Resolved CSS custom properties, cached until the theme changes.
  class Palette {
    constructor() {
      this.cache = new Map();
      this.version = 0;
    }

    get(name) {
      if (!this.cache.has(name)) this.cache.set(name, getComputedStyle(document.documentElement).getPropertyValue(name).trim());
      return this.cache.get(name);
    }

    invalidate() {
      this.cache.clear();
      this.version += 1;
    }
  }
  const palette = new Palette();

  // A canvas sized to its box at the device's pixel ratio, resized only when its box changes. onResize lets the owner
  // redraw when the box changes on its own, for example when a hidden panel is shown.
  class Surface {
    constructor(canvas, { onResize = null } = {}) {
      Object.assign(this, { canvas, onResize, width: 0, height: 0, version: 0 });
      this.context = canvas.getContext("2d");
      this._measure();
      if (typeof ResizeObserver !== "undefined") new ResizeObserver(() => this._measure() && this.onResize?.()).observe(canvas);
    }

    // Matches the backing store to the box; true when the box changed.
    _measure() {
      const ratio = root.devicePixelRatio || 1;
      const { width, height } = this.canvas.getBoundingClientRect();
      if (width === this.width && height === this.height) return false;
      Object.assign(this, { width, height });
      this.canvas.width = Math.max(1, Math.round(width * ratio));
      this.canvas.height = Math.max(1, Math.round(height * ratio));
      this.context.setTransform(ratio, 0, 0, ratio, 0, 0);
      this.version += 1;
      return true;
    }

    // Clears to transparent, so the recording paper behind the canvas shows, and returns the box size in CSS pixels.
    begin() {
      this.context.clearRect(0, 0, this.width, this.height);
      return { context: this.context, width: this.width, height: this.height };
    }
  }

  const clamp = (value, low = 0, high = 1) => Math.max(low, Math.min(high, value));
  const wrapPhase = (phase) => Math.atan2(Math.sin(phase), Math.cos(phase));
  const MS_PER_SECOND = 1000;
  const phaseOf = (ms, frequencyHz) => (2 * Math.PI * frequencyHz * ms) / MS_PER_SECOND;

  function make(tag, properties = {}, children = []) {
    const node = Object.assign(document.createElement(tag), properties);
    node.append(...children);
    return node;
  }

  // A lookup that names what is missing instead of failing later on null.
  function required(scope, selector, owner) {
    const node = scope.querySelector(selector);
    if (!node) throw new Error(`${owner}: missing ${selector}`);
    return node;
  }

  // Plots a series of {x, y} points as one path through a scale.
  function polyline(context, points, px, py) {
    context.beginPath();
    points.forEach((point, k) => (k ? context.lineTo(px(point.x), py(point.y)) : context.moveTo(px(point.x), py(point.y))));
    context.stroke();
  }

  function dot(context, x, y, radius, colour) {
    context.beginPath();
    context.arc(x, y, radius, 0, 2 * Math.PI);
    context.fillStyle = colour;
    context.fill();
  }

  // A signal in flight: a small diamond.
  function diamond(context, x, y, radius, colour) {
    context.beginPath();
    context.moveTo(x, y - radius);
    context.lineTo(x + radius, y);
    context.lineTo(x, y + radius);
    context.lineTo(x - radius, y);
    context.closePath();
    context.fillStyle = colour;
    context.fill();
  }

  // A signal that fails: a small cross.
  function cross(context, x, y, radius, colour) {
    context.beginPath();
    context.moveTo(x - radius, y - radius);
    context.lineTo(x + radius, y + radius);
    context.moveTo(x + radius, y - radius);
    context.lineTo(x - radius, y + radius);
    context.strokeStyle = colour;
    context.stroke();
  }

  // An anaesthetic molecule: an outlined hexagon, filled when bound and hollow when free.
  function hexagon(context, { x, y, radius, fill, edge }) {
    context.beginPath();
    for (let k = 0; k < 6; k++) {
      const angle = (Math.PI / 3) * k;
      context[k ? "lineTo" : "moveTo"](x + radius * Math.cos(angle), y + radius * Math.sin(angle));
    }
    context.closePath();
    context.fillStyle = fill;
    context.fill();
    context.strokeStyle = edge;
    context.stroke();
  }

  // A chart mark: an upward triangle, or a square, filled or hollow.
  function triangle(context, { x, y, radius, fill, edge }) {
    context.beginPath();
    context.moveTo(x, y - radius);
    context.lineTo(x + radius, y + radius * 0.8);
    context.lineTo(x - radius, y + radius * 0.8);
    context.closePath();
    context.fillStyle = fill;
    context.fill();
    context.strokeStyle = edge;
    context.stroke();
  }

  function square(context, { x, y, radius, fill, edge }) {
    context.beginPath();
    context.rect(x - radius, y - radius, 2 * radius, 2 * radius);
    context.fillStyle = fill;
    context.fill();
    context.strokeStyle = edge;
    context.stroke();
  }

  // An arrowhead at (x, y) pointing along angle, for direction on a line.
  function arrowhead(context, { x, y, angle, size }) {
    context.beginPath();
    context.moveTo(x - size * Math.cos(angle - 0.5), y - size * Math.sin(angle - 0.5));
    context.lineTo(x, y);
    context.lineTo(x - size * Math.cos(angle + 0.5), y - size * Math.sin(angle + 0.5));
    context.stroke();
  }

  function dashedRule(context, { x0, x1, y, colour, dash }) {
    context.strokeStyle = colour;
    context.setLineDash(dash);
    context.beginPath();
    context.moveTo(x0, y);
    context.lineTo(x1, y);
    context.stroke();
    context.setLineDash([]);
  }

  // Legend swatch shapes; each draws in the colour of its token.
  const Swatch = Object.freeze({
    DOT: "dot", RING: "ring", LINE: "line", DASHED: "dashed", DOTTED: "dotted", DASH_DOT: "dash-dot", DASH_DOT_DOT: "dash-dot-dot", DIAMOND: "diamond", CROSS: "cross", BAND: "band",
    SQUARE: "square", SQUARE_OPEN: "square-open", TRIANGLE: "triangle", TRIANGLE_OPEN: "triangle-open", TICK: "tick", HEXAGON: "hexagon", HEXAGON_OPEN: "hexagon-open", ARROW_FORWARD: "arrow-forward", ARROW_BACK: "arrow-back",
  });
  // What kind of thing a legend entry describes; the key shows one labelled row per group, in this order.
  const LegendGroup = Object.freeze({ DRUG: "legendGroupDrug", REGIONS: "legendGroupRegions", CELLS: "legendGroupCells", CONNECTIONS: "legendGroupConnections", SIGNALS: "legendGroupSignals", CHART: "legendGroupChart" });

  // Legend entries written with message keys become entries with labels in the reader's language.
  const labelled = (entries) => entries.map(({ message, params, ...entry }) => ({ ...entry, label: root.DPC.t(message, params) }));

  function legendEntry({ swatch, token, label }) {
    const mark = make("i", { className: `swatch ${swatch}` });
    mark.style.setProperty("--swatch", `var(${token})`);
    return make("li", {}, [mark, make("span", { textContent: label })]);
  }

  // Replaces a legend with one labelled row per group of {group, swatch, token, label} entries.
  function renderLegend(list, items) {
    const rows = Object.values(LegendGroup)
      .map((group) => ({ group, entries: items.filter((item) => item.group === group) }))
      .filter(({ entries }) => entries.length);
    list.replaceChildren(...rows.map(({ group, entries }) =>
      make("li", { className: "legend-row" }, [make("span", { className: "legend-group", textContent: root.DPC.t(group) }), make("ul", {}, entries.map(legendEntry))]),
    ));
  }

  // A linear map from a data domain to pixels.
  const scale = ([d0, d1], [p0, p1]) => (value) => p0 + ((value - d0) / (d1 - d0)) * (p1 - p0);

  root.DPC = Object.assign(root.DPC || {}, { Token, Swatch, LegendGroup, labelled, legendEntry, renderLegend, palette, Surface, clamp, wrapPhase, phaseOf, make, required, polyline, dot, diamond, cross, hexagon, triangle, square, arrowhead, dashedRule, scale });
})(globalThis);

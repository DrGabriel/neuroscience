// Three ways to see one integration cycle: the network with signals in flight, its islands, and its matrix.
// Every view takes the same draw(painter, progress), where the painter carries the cycle's outcome.
(function (root) {
  "use strict";

  const { ConnectionOutcome, Token, Swatch, LegendGroup, labelled, palette, Surface, clamp, percent, diamond, cross, t } = root.DPC;

  // A single cell agrees with nobody, so islands start at two cells (as in simulation.js).
  const MIN_ISLAND_CELLS = 2;
  const VIEW_TEXT = Object.freeze({ fontSizePx: 13, insetPx: 3 });

  // A short label with a paper-coloured box behind it, so it stays legible over bubbles and links.
  function boxedLabel(context, { text, x, y }) {
    context.font = `${VIEW_TEXT.fontSizePx}px ${palette.get(Token.FONT_LABEL)}`;
    context.textAlign = "center";
    context.textBaseline = "middle";
    const width = context.measureText(text).width + 2 * VIEW_TEXT.insetPx;
    context.fillStyle = palette.get(Token.PAPER);
    context.fillRect(x - width / 2, y - VIEW_TEXT.fontSizePx / 2 - VIEW_TEXT.insetPx, width, VIEW_TEXT.fontSizePx + 2 * VIEW_TEXT.insetPx);
    context.fillStyle = palette.get(Token.INK);
    context.fillText(text, x, y);
  }

  // Timing of one cycle as drawn, in fractions of the cycle: signals leave at 0 and the window opens around ARRIVAL.
  // A timing error of half the window moves an arrival by WINDOW_HALF_WIDTH. Failed signals fade out mid-flight.
  // Cells take their new state as the window closes.
  const CYCLE = Object.freeze({
    ARRIVAL: 0.6, WINDOW_HALF_WIDTH: 0.07, EARLIEST: 0.25, LATEST: 1.25,
    FAIL_FADE_START: 0.2, FAIL_FADE_END: 0.38, SETTLE_START: 0.62, SETTLE_END: 0.8,
  });
  // Even awake, most signals miss the window (about 62% at 3 ms of scatter), yet the network agrees because only a small
  // share needs to count. Late signals are therefore drawn smaller and fainter, so the eye follows the ones that count.
  const PULSE_STYLES = Object.freeze([
    Object.freeze({ kind: ConnectionOutcome.LATE, token: Token.LATE, sizePx: 1.6, alpha: 0.55 }),
    Object.freeze({ kind: ConnectionOutcome.ON_TIME, token: Token.HELD, sizePx: 2.4, alpha: 1 }),
  ]);
  const FAILED_PULSE_SIZE_PX = 2.2;
  const DEPTH_SHADING = Object.freeze({ floor: 0.45, range: 0.55 });

  const smooth = (value) => value * value * (3 - 2 * value);
  const settled = (progress) => smooth(clamp((progress - CYCLE.SETTLE_START) / (CYCLE.SETTLE_END - CYCLE.SETTLE_START)));

  // Per cycle: where each transmitted signal arrives (fraction of the cycle) and which connections carry which outcome.
  class PulsePlan {
    constructor(network) {
      this.arrival = new Float32Array(network.connectionCount);
      this.byOutcome = new Map(Object.values(ConnectionOutcome).map((kind) => [kind, []]));
      this.key = "";
    }

    update(painter) {
      const { outcome } = painter;
      const key = `${outcome.cycle}:${painter.version}`;
      if (key === this.key) return;
      for (const list of this.byOutcome.values()) list.length = 0;
      for (let k = 0; k < outcome.connections.length; k++) {
        if (!painter.carriesPulse(k)) continue;
        this.byOutcome.get(outcome.connections[k]).push(k);
        const shift = (outcome.errorsMs[k] / outcome.halfWindowMs) * CYCLE.WINDOW_HALF_WIDTH;
        this.arrival[k] = clamp(CYCLE.ARRIVAL + shift, CYCLE.EARLIEST, CYCLE.LATEST);
      }
      this.key = key;
    }
  }

  class NetworkView {
    static PADDING = 14;

    constructor(canvas, network, projector) {
      Object.assign(this, { surface: new Surface(canvas), network, projector });
      this.pulses = new PulsePlan(network);
      this.edges = { canvas: document.createElement("canvas"), key: "" };
      // Layers drawn over the cells, given the cells' positions (for example the anaesthetic's molecules).
      this.overlays = [];
    }

    draw(painter, progress = 1) {
      const { context, width, height } = this.surface.begin();
      const points = this.projector.project(width, height, NetworkView.PADDING);
      this._drawEdges(context, points, painter);
      if (progress < 1) {
        this.pulses.update(painter);
        this._drawPulses(context, points, progress);
      }
      this._drawCells(context, points, painter, settled(progress));
      for (const overlay of this.overlays) overlay.draw(context, { width, height, anchors: points });
    }

    // Edges change once per cycle; with a fixed layout they are drawn once and copied every frame.
    _drawEdges(context, points, painter) {
      if (!this.projector.isFixed) {
        this._strokeEdges(context, points, painter);
        return;
      }
      const key = `${painter.outcome.cycle}:${painter.version}:${this.surface.version}:${palette.version}`;
      const cache = this.edges.canvas;
      if (this.edges.key !== key) {
        cache.width = this.surface.canvas.width;
        cache.height = this.surface.canvas.height;
        const cached = cache.getContext("2d");
        cached.setTransform(this.surface.context.getTransform());
        this._strokeEdges(cached, points, painter);
        this.edges.key = key;
      }
      context.save();
      context.setTransform(1, 0, 0, 1, 0, 0);
      context.drawImage(cache, 0, 0);
      context.restore();
    }

    _strokeEdges(context, points, painter) {
      for (const layer of painter.connectionLayers) {
        const pairs = layer.directed ? this.network.directed : this.network.undirected;
        context.strokeStyle = palette.get(layer.token);
        context.lineWidth = layer.width;
        context.beginPath();
        for (let k = 0; k < pairs.count; k++) {
          if (!layer.includes(k)) continue;
          const a = points[pairs.sources[k]], b = points[pairs.targets[k]];
          context.moveTo(a.x, a.y);
          context.lineTo(b.x, b.y);
        }
        context.stroke();
      }
    }

    _drawPulses(context, points, progress) {
      const { sources, targets } = this.network;
      // Draws a pulse part-way along connection k; called thousands of times a frame, so it allocates nothing.
      const drawAt = (shape, k, along, { colour, sizePx }) => {
        const a = points[sources[k]], b = points[targets[k]];
        shape(context, a.x + (b.x - a.x) * along, a.y + (b.y - a.y) * along, sizePx, colour);
      };
      const fade = 1 - clamp((progress - CYCLE.FAIL_FADE_START) / (CYCLE.FAIL_FADE_END - CYCLE.FAIL_FADE_START));
      if (fade > 0) {
        context.globalAlpha = fade;
        context.lineWidth = 1;
        const failed = { colour: palette.get(Token.STRAY), sizePx: FAILED_PULSE_SIZE_PX };
        for (const k of this.pulses.byOutcome.get(ConnectionOutcome.FAILED)) drawAt(cross, k, progress / CYCLE.ARRIVAL, failed);
      }
      for (const style of PULSE_STYLES) {
        const look = { colour: palette.get(style.token), sizePx: style.sizePx };
        context.globalAlpha = style.alpha;
        for (const k of this.pulses.byOutcome.get(style.kind)) {
          if (progress < this.pulses.arrival[k]) drawAt(diamond, k, progress / this.pulses.arrival[k], look);
        }
      }
      context.globalAlpha = 1;
    }

    _drawCells(context, points, painter, settledShare) {
      const ring = palette.get(Token.PAPER);
      const paint = (point, style, alpha) => {
        if (alpha <= 0) return;
        context.globalAlpha = alpha * (DEPTH_SHADING.floor + DEPTH_SHADING.range * point.depth);
        context.beginPath();
        context.arc(point.x, point.y, style.radius * point.size, 0, 2 * Math.PI);
        if (style.hollow) {
          context.strokeStyle = palette.get(style.token);
          context.stroke();
          return;
        }
        context.fillStyle = palette.get(style.token);
        context.fill();
        context.strokeStyle = ring;
        context.stroke();
      };
      context.lineWidth = 1;
      for (const node of this.projector.drawingOrder(points)) {
        const current = painter.cellStyle(node);
        const previous = painter.previousCellStyle?.(node);
        if (!previous || previous === current || settledShare >= 1) {
          paint(points[node], current, 1);
          continue;
        }
        paint(points[node], previous, 1 - settledShare);
        paint(points[node], current, settledShare);
      }
      context.globalAlpha = 1;
    }
  }

  // Island sizes this cycle, largest first, counting only cells that are not silenced.
  function islandSizes(outcome) {
    const sizes = new Map();
    outcome.componentOf.forEach((rootOfNode, node) => {
      if (!outcome.silenced[node]) sizes.set(rootOfNode, (sizes.get(rootOfNode) ?? 0) + 1);
    });
    return [...sizes.entries()].sort((a, b) => b[1] - a[1]);
  }

  // Each island of agreeing cells as a bubble whose area is its share of the network, largest first. The largest sits
  // inside a dashed circle the size quorum needs, so whether it reaches quorum is seen, not read.
  class IslandsView {
    static AREA_SHARE = 0.32;
    static INSET = 12;
    static GAP = 4;
    static ROW_GAP = 6;
    static MIN_RADIUS = 1.5;
    static LABEL_MIN_RADIUS = 22;
    static FONT_SIZE_PX = 12;
    static DASH = Object.freeze([5, 4]);
    static QUORUM_LINE_PX = 1.5;
    static QUORUM_LABEL_INSET_PX = 12;

    constructor(canvas, network) {
      Object.assign(this, { surface: new Surface(canvas), network });
    }

    // The same colours as the network view: the painter decides which group gets which.
    legend(painter) {
      return labelled([
        { group: LegendGroup.CELLS, swatch: Swatch.DOT, token: Token.HELD, message: "legendGiantIsland" },
        ...painter.islands.map((island) => ({ group: LegendGroup.CELLS, swatch: Swatch.DOT, token: island.style.token, message: island.message })),
        { group: LegendGroup.CELLS, swatch: Swatch.DOT, token: Token.STRAY, message: "legendIsland" },
        { group: LegendGroup.CHART, swatch: Swatch.DASHED, token: Token.INK, message: "legendQuorumCircle", params: { share: percent(painter.outcome.quorumFraction) } },
      ]);
    }

    draw(painter) {
      const { context, width, height } = this.surface.begin();
      const { outcome } = painter;
      const unit = Math.sqrt((width * height * IslandsView.AREA_SHARE) / this.network.nodeCount / Math.PI);
      const quorumRadius = unit * Math.sqrt(outcome.quorumFraction * this.network.nodeCount);
      const islands = islandSizes(outcome);
      const radiusOf = (size) => Math.max(IslandsView.MIN_RADIUS, unit * Math.sqrt(size));
      // The first slot is wide enough for the dashed circle as well as the largest island.
      const first = Math.max(quorumRadius, radiusOf(islands[0]?.[1] ?? 0));
      const centre = { x: IslandsView.INSET + first, y: IslandsView.INSET + first };
      let x = IslandsView.INSET + 2 * first + IslandsView.GAP, y = IslandsView.INSET, rowHeight = 2 * first;
      context.font = `${IslandsView.FONT_SIZE_PX}px ${palette.get(Token.FONT_DATA)}`;
      islands.forEach(([rootOfNode, size], index) => {
        const radius = radiusOf(size);
        const token = painter.styleOf(0, outcome.group[rootOfNode]).token;
        if (index === 0) {
          this._bubble(context, { ...centre, radius, token, share: size / this.network.nodeCount });
          return;
        }
        if (x + 2 * radius > width - IslandsView.INSET) {
          x = IslandsView.INSET;
          y += rowHeight + IslandsView.ROW_GAP;
          rowHeight = 0;
        }
        if (y + 2 * radius > height) return;
        this._bubble(context, { x: x + radius, y: y + radius, radius, token, share: size / this.network.nodeCount });
        x += 2 * radius + IslandsView.GAP;
        rowHeight = Math.max(rowHeight, 2 * radius);
      });
      this._quorumCircle(context, { ...centre, radius: quorumRadius, share: outcome.quorumFraction });
    }

    _quorumCircle(context, { x, y, radius, share }) {
      context.strokeStyle = palette.get(Token.INK);
      context.lineWidth = IslandsView.QUORUM_LINE_PX;
      context.setLineDash(IslandsView.DASH);
      context.beginPath();
      context.arc(x, y, radius, 0, 2 * Math.PI);
      context.stroke();
      context.setLineDash([]);
      boxedLabel(context, { text: t("islandsQuorumCircle", { share: percent(share) }), x, y: y + radius - IslandsView.QUORUM_LABEL_INSET_PX });
    }

    _bubble(context, { x, y, radius, token, share }) {
      context.beginPath();
      context.arc(x, y, radius, 0, 2 * Math.PI);
      context.fillStyle = palette.get(token);
      context.fill();
      if (radius <= IslandsView.LABEL_MIN_RADIUS) return;
      context.textAlign = "center";
      context.textBaseline = "middle";
      context.fillStyle = palette.get(Token.PAPER);
      context.fillText(percent(share), x, y);
    }
  }

  // Connection matrix with cells ordered by island (largest first): islands appear as blocks on the diagonal, each
  // outlined. Once quorum is lost, the view zooms in on the cells that belong to an island, since the rest have no
  // link that counts and would only shrink the blocks to dots.
  class MatrixView {
    static MARGIN = Object.freeze({ left: 22, right: 4, top: 4, bottom: 22 });
    static TITLE_INSET_PX = 4;

    constructor(canvas, network) {
      Object.assign(this, { surface: new Surface(canvas), network });
    }

    legend(painter) {
      return labelled([
        { group: LegendGroup.CONNECTIONS, swatch: Swatch.SQUARE, token: Token.HELD, message: "legendMatrixGiant" },
        ...painter.islands.map((island) => ({ group: LegendGroup.CONNECTIONS, swatch: Swatch.SQUARE, token: island.style.token, message: island.message })),
        { group: LegendGroup.CONNECTIONS, swatch: Swatch.SQUARE, token: Token.STRAY, message: "legendMatrixOther" },
        { group: LegendGroup.CONNECTIONS, swatch: Swatch.SQUARE, token: Token.LATE, message: "legendMatrixLate" },
        { group: LegendGroup.CHART, swatch: Swatch.SQUARE_OPEN, token: Token.MUTED, message: "legendMatrixBlock" },
      ]);
    }

    draw(painter) {
      const { context, width, height } = this.surface.begin();
      const { outcome } = painter;
      const { position, order, shown } = this._positions(outcome);
      const margin = MatrixView.MARGIN;
      const side = Math.min(width - margin.left - margin.right, height - margin.top - margin.bottom);
      const frame = { left: margin.left + (width - margin.left - margin.right - side) / 2, top: margin.top, side, cell: side / shown };
      context.strokeStyle = palette.get(Token.RULE);
      context.strokeRect(frame.left, frame.top, side, side);
      this._drawLinks(context, { painter, position, shown, frame });
      this._outlineBlocks(context, { outcome, order, shown, frame });
      this._titles(context, frame);
    }

    _drawLinks(context, { painter, position, shown, frame }) {
      const { outcome } = painter;
      const late = palette.get(Token.LATE_SOFT);
      const colourOf = (node) => palette.get(painter.styleOf(0, outcome.group[node]).token);
      const pixel = Math.max(1, frame.cell);
      for (let k = 0; k < this.network.connectionCount; k++) {
        const kind = outcome.connections[k];
        if (kind !== ConnectionOutcome.ON_TIME && kind !== ConnectionOutcome.LATE) continue;
        const a = position[this.network.sources[k]], b = position[this.network.targets[k]];
        if (a >= shown || b >= shown) continue;
        context.fillStyle = kind === ConnectionOutcome.LATE ? late : colourOf(this.network.sources[k]);
        context.fillRect(frame.left + a * frame.cell, frame.top + b * frame.cell, pixel, pixel);
        context.fillRect(frame.left + b * frame.cell, frame.top + a * frame.cell, pixel, pixel);
      }
    }

    // One outline per island on the diagonal.
    _outlineBlocks(context, { outcome, order, shown, frame }) {
      context.strokeStyle = palette.get(Token.MUTED);
      context.lineWidth = 1;
      for (let start = 0; start < shown;) {
        const size = outcome.componentSize[outcome.componentOf[order[start]]];
        if (size >= MIN_ISLAND_CELLS) context.strokeRect(frame.left + start * frame.cell, frame.top + start * frame.cell, size * frame.cell, size * frame.cell);
        start += Math.max(1, size);
      }
    }

    _titles(context, frame) {
      const text = t("axisCellsByIsland");
      context.save();
      context.font = `${VIEW_TEXT.fontSizePx}px ${palette.get(Token.FONT_LABEL)}`;
      context.fillStyle = palette.get(Token.INK);
      context.textAlign = "center";
      context.textBaseline = "top";
      context.fillText(text, frame.left + frame.side / 2, frame.top + frame.side + MatrixView.TITLE_INSET_PX);
      context.translate(frame.left - MatrixView.TITLE_INSET_PX, frame.top + frame.side / 2);
      context.rotate(-Math.PI / 2);
      context.textBaseline = "bottom";
      context.fillText(text, 0, 0);
      context.restore();
    }

    // Cells in order of island size, largest first; shown counts the cells in islands, or every cell when none is.
    _positions(outcome) {
      const size = (node) => outcome.componentSize[outcome.componentOf[node]];
      const order = Array.from({ length: this.network.nodeCount }, (_, node) => node);
      order.sort((a, b) => size(b) - size(a) || outcome.componentOf[a] - outcome.componentOf[b] || a - b);
      const position = new Int32Array(order.length);
      order.forEach((node, index) => { position[node] = index; });
      const inIslands = order.filter((node) => size(node) >= MIN_ISLAND_CELLS).length;
      return { position, order, shown: inIslands || order.length };
    }
  }

  // The bar under a network figure: where in the cycle the animation is, with the window marked, and how intact the
  // shared rhythm (P5) is. Only a transform changes per frame, so it never forces layout.
  class CycleBar {
    constructor(element) {
      this.marker = element.querySelector("[data-cycle-marker]");
      this.strength = element.querySelector("[data-rhythm-strength]");
      element.style.setProperty("--window-start", String(CYCLE.ARRIVAL - CYCLE.WINDOW_HALF_WIDTH));
      element.style.setProperty("--window-width", String(2 * CYCLE.WINDOW_HALF_WIDTH));
    }

    show(progress) {
      this.marker.style.setProperty("--progress", progress.toFixed(3));
    }

    showStrength(referenceStrength) {
      if (this.strength) this.strength.textContent = percent(referenceStrength);
    }
  }

  root.DPC = Object.assign(root.DPC || {}, { NetworkView, IslandsView, MatrixView, CycleBar });
})(globalThis);

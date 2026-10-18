// Three ways to see one integration cycle: the network with signals in flight, its islands, and its matrix.
// Every view takes the same draw(painter, progress), where the painter carries the cycle's outcome.
(function (root) {
  "use strict";

  const { ConnectionOutcome, Token, Swatch, LegendGroup, labelled, palette, Surface, clamp, percent, diamond, cross } = root.DPC;

  // Timing of one cycle as drawn, in fractions of the cycle: signals leave at 0 and the window opens around ARRIVAL.
  // A timing error of half the window moves an arrival by WINDOW_HALF_WIDTH. Failed signals fade out mid-flight.
  // Cells take their new state as the window closes.
  const CYCLE = Object.freeze({
    ARRIVAL: 0.6, WINDOW_HALF_WIDTH: 0.07, EARLIEST: 0.25, LATEST: 1.25,
    FAIL_FADE_START: 0.2, FAIL_FADE_END: 0.38, SETTLE_START: 0.62, SETTLE_END: 0.8,
  });
  const PULSE_SIZE_PX = 2.2;
  const PULSE_COLOURS = Object.freeze([[ConnectionOutcome.ON_TIME, Token.HELD], [ConnectionOutcome.LATE, Token.LATE]]);
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
      const drawAt = (shape, k, along, colour) => {
        const a = points[sources[k]], b = points[targets[k]];
        shape(context, a.x + (b.x - a.x) * along, a.y + (b.y - a.y) * along, PULSE_SIZE_PX, colour);
      };
      const fade = 1 - clamp((progress - CYCLE.FAIL_FADE_START) / (CYCLE.FAIL_FADE_END - CYCLE.FAIL_FADE_START));
      if (fade > 0) {
        context.globalAlpha = fade;
        context.lineWidth = 1;
        const failed = palette.get(Token.STRAY);
        for (const k of this.pulses.byOutcome.get(ConnectionOutcome.FAILED)) drawAt(cross, k, progress / CYCLE.ARRIVAL, failed);
        context.globalAlpha = 1;
      }
      for (const [kind, token] of PULSE_COLOURS) {
        const colour = palette.get(token);
        for (const k of this.pulses.byOutcome.get(kind)) {
          if (progress < this.pulses.arrival[k]) drawAt(diamond, k, progress / this.pulses.arrival[k], colour);
        }
      }
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

  // Each island of agreeing cells as a bubble whose area is its share of the network, largest first.
  class IslandsView {
    static AREA_SHARE = 0.32;
    static INSET = 12;
    static GAP = 4;
    static ROW_GAP = 6;
    static MIN_RADIUS = 1.5;
    static LABEL_MIN_RADIUS = 22;
    static FONT_SIZE_PX = 12;

    constructor(canvas, network) {
      Object.assign(this, { surface: new Surface(canvas), network });
    }

    legend() {
      return labelled([
        { group: LegendGroup.CELLS, swatch: Swatch.DOT, token: Token.HELD, message: "legendGiantIsland" },
        { group: LegendGroup.CELLS, swatch: Swatch.DOT, token: Token.STRAY, message: "legendIsland" },
      ]);
    }

    draw(painter) {
      const { context, width, height } = this.surface.begin();
      const { outcome } = painter;
      const unit = Math.sqrt((width * height * IslandsView.AREA_SHARE) / this.network.nodeCount / Math.PI);
      let x = IslandsView.INSET, y = IslandsView.INSET, rowHeight = 0;
      context.textBaseline = "middle";
      context.textAlign = "center";
      context.font = `${IslandsView.FONT_SIZE_PX}px ${palette.get(Token.FONT_DATA)}`;
      for (const [rootOfNode, size] of islandSizes(outcome)) {
        const radius = Math.max(IslandsView.MIN_RADIUS, unit * Math.sqrt(size));
        if (x + 2 * radius > width - IslandsView.INSET) {
          x = IslandsView.INSET;
          y += rowHeight + IslandsView.ROW_GAP;
          rowHeight = 0;
        }
        if (y + 2 * radius > height) break;
        this._bubble(context, { x: x + radius, y: y + radius, radius, isGiant: outcome.inGiant[rootOfNode] === 1 && size > 1, share: size / this.network.nodeCount });
        x += 2 * radius + IslandsView.GAP;
        rowHeight = Math.max(rowHeight, 2 * radius);
      }
    }

    _bubble(context, { x, y, radius, isGiant, share }) {
      context.beginPath();
      context.arc(x, y, radius, 0, 2 * Math.PI);
      context.fillStyle = palette.get(isGiant ? Token.HELD : Token.STRAY);
      context.fill();
      if (radius <= IslandsView.LABEL_MIN_RADIUS) return;
      context.fillStyle = palette.get(Token.PAPER);
      context.fillText(percent(share), x, y);
    }
  }

  // Connection matrix with cells ordered by island (largest first): islands appear as blocks on the diagonal.
  class MatrixView {
    static INSET = 4;

    constructor(canvas, network) {
      Object.assign(this, { surface: new Surface(canvas), network });
    }

    legend() {
      return labelled([
        { group: LegendGroup.CONNECTIONS, swatch: Swatch.SQUARE, token: Token.HELD, message: "legendMatrixGiant" },
        { group: LegendGroup.CONNECTIONS, swatch: Swatch.SQUARE, token: Token.STRAY, message: "legendMatrixOther" },
        { group: LegendGroup.CONNECTIONS, swatch: Swatch.SQUARE, token: Token.LATE, message: "legendMatrixLate" },
      ]);
    }

    draw(painter) {
      const { context, width, height } = this.surface.begin();
      const { outcome } = painter;
      const position = this._positions(outcome);
      const side = Math.min(width, height) - 2 * MatrixView.INSET;
      const cell = side / this.network.nodeCount;
      const left = (width - side) / 2, top = (height - side) / 2;
      const pixel = Math.max(1, cell);
      context.strokeStyle = palette.get(Token.RULE);
      context.strokeRect(left, top, side, side);
      const fill = { held: palette.get(Token.HELD), stray: palette.get(Token.STRAY), late: palette.get(Token.LATE_SOFT) };
      for (let k = 0; k < this.network.connectionCount; k++) {
        const kind = outcome.connections[k];
        if (kind !== ConnectionOutcome.ON_TIME && kind !== ConnectionOutcome.LATE) continue;
        const a = position[this.network.sources[k]], b = position[this.network.targets[k]];
        context.fillStyle = kind === ConnectionOutcome.LATE ? fill.late : outcome.inGiant[this.network.sources[k]] ? fill.held : fill.stray;
        context.fillRect(left + a * cell, top + b * cell, pixel, pixel);
        context.fillRect(left + b * cell, top + a * cell, pixel, pixel);
      }
    }

    _positions(outcome) {
      const size = (node) => outcome.componentSize[outcome.componentOf[node]];
      const order = Array.from({ length: this.network.nodeCount }, (_, node) => node);
      order.sort((a, b) => size(b) - size(a) || outcome.componentOf[a] - outcome.componentOf[b] || a - b);
      const position = new Int32Array(order.length);
      order.forEach((node, index) => { position[node] = index; });
      return position;
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

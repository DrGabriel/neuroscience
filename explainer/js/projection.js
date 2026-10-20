// Where each cell is drawn: flat rings from the network's own layout, or a rotating 3D brain from real coordinates.
(function (root) {
  "use strict";

  const { clamp } = root.DPC;

  // Every projector returns screen x, y, a depth in [0, 1] (1 nearest the viewer) and a size factor,
  // says whether its layout isFixed, and gives the order to draw cells in.

  // The network's own ring layout. It never moves, so its points and drawing order are computed once per size.
  class RingProjector {
    constructor(network) {
      this.network = network;
      this.isFixed = true;
      this.cache = { key: "", points: [] };
      this.order = Array.from({ length: network.nodeCount }, (_, node) => node);
    }

    project(width, height, padding) {
      const key = `${width}x${height}:${padding}`;
      if (this.cache.key === key) return this.cache.points;
      const half = Math.min(width, height) / 2 - padding;
      const { x, y, nodeCount } = this.network;
      this.cache = { key, points: Array.from({ length: nodeCount }, (_, node) => ({ x: width / 2 + x[node] * half, y: height / 2 + y[node] * half, depth: 1, size: 1 })) };
      return this.cache.points;
    }

    drawingOrder() {
      return this.order;
    }
  }

  const ORBIT = Object.freeze({ perspective: 3.2, nearSize: 1.35, farSize: 0.6, pitchLimit: 1.3, initialPitch: -0.25, dragRadiansPerPixel: 0.01, keyStep: 0.12 });

  // One step of turning, named so buttons and keys share it.
  const Turn = Object.freeze({ LEFT: "LEFT", RIGHT: "RIGHT", UP: "UP", DOWN: "DOWN" });
  const TURNS = Object.freeze({
    [Turn.LEFT]: [-ORBIT.keyStep, 0], [Turn.RIGHT]: [ORBIT.keyStep, 0], [Turn.UP]: [0, -ORBIT.keyStep], [Turn.DOWN]: [0, ORBIT.keyStep],
  });
  const KEY_TURN = Object.freeze({ ArrowLeft: Turn.LEFT, ArrowRight: Turn.RIGHT, ArrowUp: Turn.UP, ArrowDown: Turn.DOWN });

  // Orthographic-with-mild-perspective view of 3D coordinates, rotated by yaw and pitch. In the Lausanne coordinates
  // the first axis runs from front to back, the second from right to left and the third upwards (checked against the
  // regions' names and hemispheres), so the starting view shows the left hemisphere from the side, front to the left.
  class OrbitProjector {
    constructor(coordinates) {
      const count = coordinates.length / 3;
      const centre = [0, 1, 2].map((axis) => Array.from({ length: count }, (_, k) => coordinates[3 * k + axis]).reduce((a, b) => a + b, 0) / count);
      const points = Array.from({ length: count }, (_, k) => [0, 1, 2].map((axis) => coordinates[3 * k + axis] - centre[axis]));
      const extent = Math.max(...points.map((p) => Math.hypot(...p)));
      this.points = points.map((p) => p.map((value) => value / extent));
      this.yaw = 0;
      this.pitch = ORBIT.initialPitch;
      this.isFixed = false;
      this.order = this.points.map((_, node) => node);
    }

    reset() {
      this.yaw = 0;
      this.pitch = ORBIT.initialPitch;
    }

    // Farthest first, so nearer regions are drawn over farther ones.
    drawingOrder(points) {
      return this.order.sort((a, b) => points[a].depth - points[b].depth);
    }

    turn(direction) {
      this.rotate(...TURNS[direction]);
    }

    rotate(deltaYaw, deltaPitch) {
      this.yaw += deltaYaw;
      this.pitch = clamp(this.pitch + deltaPitch, -ORBIT.pitchLimit, ORBIT.pitchLimit);
    }

    project(width, height, padding) {
      return this.points.map((point) => this.projectPoint(point, { width, height, padding }));
    }

    // Any point in the brain's own normalised frame (for example the end of an axis), seen from the current angle.
    projectPoint([x, y, z], { width, height, padding }) {
      const half = Math.min(width, height) / 2 - padding;
      const [cy, sy, cp, sp] = [Math.cos(this.yaw), Math.sin(this.yaw), Math.cos(this.pitch), Math.sin(this.pitch)];
      const x1 = cy * x + sy * y;
      const y1 = -sy * x + cy * y;
      const y2 = cp * y1 - sp * z;
      const z2 = sp * y1 + cp * z;
      const scale = ORBIT.perspective / (ORBIT.perspective - y2);
      const depth = (y2 + 1) / 2;
      return { x: width / 2 + x1 * half * scale, y: height / 2 - z2 * half * scale, depth, size: ORBIT.farSize + (ORBIT.nearSize - ORBIT.farSize) * depth };
    }

    // Drag with a pointer or use the arrow keys to turn the brain.
    attach(canvas, onChange) {
      let last = null;
      canvas.addEventListener("pointerdown", (event) => {
        last = { x: event.clientX, y: event.clientY };
        canvas.setPointerCapture(event.pointerId);
      });
      canvas.addEventListener("pointermove", (event) => {
        if (!last) return;
        this.rotate((event.clientX - last.x) * ORBIT.dragRadiansPerPixel, (event.clientY - last.y) * ORBIT.dragRadiansPerPixel);
        last = { x: event.clientX, y: event.clientY };
        onChange();
      });
      canvas.addEventListener("pointerup", () => { last = null; });
      canvas.addEventListener("keydown", (event) => {
        const turn = TURNS[KEY_TURN[event.key]];
        if (!turn) return;
        event.preventDefault();
        this.rotate(...turn);
        onChange();
      });
    }
  }

  root.DPC = Object.assign(root.DPC || {}, { RingProjector, OrbitProjector, Turn });
})(globalThis);

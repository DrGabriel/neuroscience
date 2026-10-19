// Connectome graph: components in O(E α(N)) per integration cycle, and processing depth from the sensory cells.
(function (root) {
  "use strict";

  const UNREACHED = -1;

  class UnionFind {
    constructor(size) {
      this.parent = new Int32Array(size);
      this.size = new Int32Array(size);
    }

    reset() {
      for (let node = 0; node < this.parent.length; node++) {
        this.parent[node] = node;
        this.size[node] = 1;
      }
    }

    find(node) {
      const parent = this.parent;
      while (parent[node] !== node) {
        parent[node] = parent[parent[node]];
        node = parent[node];
      }
      return node;
    }

    union(a, b) {
      let rootA = this.find(a);
      let rootB = this.find(b);
      if (rootA === rootB) return;
      if (this.size[rootA] < this.size[rootB]) [rootA, rootB] = [rootB, rootA];
      this.parent[rootB] = rootA;
      this.size[rootA] += this.size[rootB];
    }
  }

  function pairsFrom(flat) {
    const count = flat.length / 2;
    return Object.freeze({
      count,
      sources: Int32Array.from({ length: count }, (_, k) => flat[2 * k]),
      targets: Int32Array.from({ length: count }, (_, k) => flat[2 * k + 1]),
    });
  }

  // Shortest directed path length from any sensory cell; UNREACHED where none exists.
  function depthsFromSensory(nodeCount, directed, sensoryNodes) {
    const outgoing = Array.from({ length: nodeCount }, () => []);
    for (let k = 0; k < directed.count; k++) outgoing[directed.sources[k]].push(directed.targets[k]);
    const depth = new Int32Array(nodeCount).fill(UNREACHED);
    const queue = [...sensoryNodes];
    for (const node of queue) depth[node] = 0;
    for (let head = 0; head < queue.length; head++) {
      for (const next of outgoing[queue[head]]) {
        if (depth[next] !== UNREACHED) continue;
        depth[next] = depth[queue[head]] + 1;
        queue.push(next);
      }
    }
    return depth;
  }

  function preferredAngle(innerNeighbours, angle, fallback) {
    if (!innerNeighbours.length) return fallback;
    const sin = innerNeighbours.reduce((sum, other) => sum + Math.sin(angle[other]), 0);
    const cos = innerNeighbours.reduce((sum, other) => sum + Math.cos(angle[other]), 0);
    return Math.atan2(sin, cos);
  }

  // Concentric rings, one per step from the sensory cells (cells no sensory path reaches go outermost). Ring radii
  // enclose equal area per cell; within a ring, cells are ordered by the mean angle of their inner neighbours,
  // the barycentre heuristic of layered graph drawing, so that connected cells sit near one another.
  function ringLayout(nodeCount, undirected, depth) {
    const outermost = Math.max(...depth) + 1;
    const ringOf = Array.from(depth, (d) => (d === UNREACHED ? outermost : d));
    const neighbours = Array.from({ length: nodeCount }, () => []);
    for (let k = 0; k < undirected.count; k++) {
      neighbours[undirected.sources[k]].push(undirected.targets[k]);
      neighbours[undirected.targets[k]].push(undirected.sources[k]);
    }
    const angle = new Float64Array(nodeCount);
    const layout = { x: new Float64Array(nodeCount), y: new Float64Array(nodeCount) };
    let placed = 0;
    for (let ring = 0; ring <= outermost; ring++) {
      const members = [];
      for (let node = 0; node < nodeCount; node++) if (ringOf[node] === ring) members.push(node);
      if (!members.length) continue;
      const evenly = (index) => (2 * Math.PI * index) / members.length;
      const preferred = new Map(members.map((node, index) => [node, preferredAngle(neighbours[node].filter((other) => ringOf[other] < ring), angle, evenly(index))]));
      members.sort((a, b) => preferred.get(a) - preferred.get(b));
      const radius = Math.sqrt((placed + members.length / 2) / nodeCount);
      const offset = preferred.get(members[0]);
      members.forEach((node, index) => {
        angle[node] = offset + evenly(index);
        layout.x[node] = radius * Math.cos(angle[node]);
        layout.y[node] = radius * Math.sin(angle[node]);
      });
      placed += members.length;
    }
    return layout;
  }

  class Network {
    constructor(record) {
      this.name = record.name;
      this.nodeCount = record.nodeCount;
      this.undirected = pairsFrom(record.connections);
      this.directed = pairsFrom(record.directedConnections);
      this.connectionCount = this.undirected.count;
      this.sources = this.undirected.sources;
      this.targets = this.undirected.targets;
      this.sensoryNodes = Int32Array.from(record.sensoryNodes);
      this.isSensory = new Uint8Array(this.nodeCount);
      for (const node of this.sensoryNodes) this.isSensory[node] = 1;
      this.depth = depthsFromSensory(this.nodeCount, this.directed, this.sensoryNodes);
      const layout = ringLayout(this.nodeCount, this.undirected, this.depth);
      this.x = layout.x;
      this.y = layout.y;
      this._components = new UnionFind(this.nodeCount);
      Object.freeze(this);
    }

    // A directed connection runs back towards the sensory cells when its target is fewer steps from them than its source.
    isFeedback(k) {
      const from = this.depth[this.directed.sources[k]];
      const to = this.depth[this.directed.targets[k]];
      return from !== UNREACHED && to !== UNREACHED && to < from;
    }

    // Per undirected connection, 1 when either of its directions is a feedback connection.
    feedbackConnectionMask() {
      const key = (a, b) => (a < b ? a * this.nodeCount + b : b * this.nodeCount + a);
      const feedback = new Set();
      for (let k = 0; k < this.directed.count; k++) {
        if (this.isFeedback(k)) feedback.add(key(this.directed.sources[k], this.directed.targets[k]));
      }
      return Uint8Array.from({ length: this.connectionCount }, (_, k) => (feedback.has(key(this.sources[k], this.targets[k])) ? 1 : 0));
    }

    feedbackCount() {
      let count = 0;
      for (let k = 0; k < this.directed.count; k++) count += this.isFeedback(k) ? 1 : 0;
      return count;
    }

    // Fills the analysis (inGiant, componentOf, componentSize, inReach, reachShare) from the connections marked in
    // `kept`, and returns the giant component's share of all cells.
    analyse(kept, analysis) {
      const components = this._components;
      components.reset();
      for (let k = 0; k < this.connectionCount; k++) if (kept[k]) components.union(this.sources[k], this.targets[k]);
      let largestRoot = 0;
      for (let node = 0; node < this.nodeCount; node++) {
        analysis.componentOf[node] = components.find(node);
        if (analysis.componentOf[node] === node && components.size[node] > components.size[largestRoot]) largestRoot = node;
      }
      analysis.componentSize.set(components.size);
      const sensoryRoots = new Set(Array.from(this.sensoryNodes, (node) => analysis.componentOf[node]));
      let reached = 0;
      for (let node = 0; node < this.nodeCount; node++) {
        const rootOfNode = analysis.componentOf[node];
        analysis.inGiant[node] = rootOfNode === largestRoot ? 1 : 0;
        analysis.inReach[node] = sensoryRoots.has(rootOfNode) && components.size[rootOfNode] > 1 ? 1 : 0;
        if (analysis.inReach[node] && !this.isSensory[node]) reached += 1;
      }
      analysis.reachShare = reached / (this.nodeCount - this.sensoryNodes.length);
      return components.size[largestRoot] / this.nodeCount;
    }
  }

  root.DPC = Object.assign(root.DPC || {}, { Network });
})(globalThis);

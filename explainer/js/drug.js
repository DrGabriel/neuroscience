// The anaesthetic in the figures, drawn as a schematic: molecules drift in from the edges as the dose rises and out
// as it falls. How many are drawn follows the concentration; the share that sits bound on a cell follows the agent's
// dose-response (the Hill curve under the slider). Where each molecule goes is illustrative, not simulated.
(function (root) {
  "use strict";

  const { Token, Swatch, LegendGroup, labelled, palette, hexagon, RandomSource } = root.DPC;

  const CLOUD = Object.freeze({
    maxMolecules: 60,
    radiusPx: 5,
    // A soft disc behind each molecule lifts it off a dense network.
    haloPx: 9,
    // Share of the figure a molecule crosses per millisecond of playback, entering and wandering.
    speedPerMs: 0.0009,
    wanderSpeedPerMs: 0.00012,
    arrivalDistance: 0.004,
    // Without cells to visit (the plant sheet), free molecules wander inside this margin of the figure.
    inset: 0.06,
    // Free molecules drift from cell to cell, this far to one side of the cell (share of the figure).
    besideCell: 0.02,
    edgeWidthPx: 1.6,
  });
  const Edge = Object.freeze({ LEFT: 0, RIGHT: 1, TOP: 2, BOTTOM: 3 });

  const randomCell = (random) => Math.floor(random.uniform() * Number.MAX_SAFE_INTEGER);
  const insideSpot = (random) => ({ x: CLOUD.inset + random.uniform() * (1 - 2 * CLOUD.inset), y: CLOUD.inset + random.uniform() * (1 - 2 * CLOUD.inset) });

  // anchorNode is the cell it binds to; visitNode the cell it is drifting towards while free. Both are taken modulo
  // the number of cells, so one molecule works for any network.
  class Molecule {
    constructor(random) {
      Object.assign(this, { anchorNode: randomCell(random), visitNode: randomCell(random), bound: false, leaving: false, settled: false, gone: false, exit: null });
      const angle = 2 * Math.PI * random.uniform();
      this.offset = { x: CLOUD.besideCell * Math.cos(angle), y: CLOUD.besideCell * Math.sin(angle) };
      this.spot = insideSpot(random);
      Object.assign(this, DrugCloud.edgePoint(random));
    }
  }

  class DrugCloud {
    constructor(seed) {
      this.random = new RandomSource(seed);
      this.molecules = [];
      // The cells' positions in pixels and the figure's size, from the last frame drawn.
      this.frame = { anchors: null, width: 1, height: 1 };
      this.target = { x: 0, y: 0 };
    }

    static edgePoint(random) {
      const along = random.uniform();
      const edge = Math.floor(random.uniform() * Object.keys(Edge).length);
      if (edge === Edge.LEFT) return { x: 0, y: along };
      if (edge === Edge.RIGHT) return { x: 1, y: along };
      return { x: along, y: edge === Edge.TOP ? 0 : 1 };
    }

    // Matches the cloud to a dose: molecules in proportion to concentration, bound in proportion to the drug's effect.
    setDose({ concentration, maxConcentration, effect }) {
      const wanted = Math.round((CLOUD.maxMolecules * concentration) / maxConcentration);
      const staying = this.molecules.filter((molecule) => !molecule.leaving);
      for (let k = staying.length; k < wanted; k++) {
        const molecule = new Molecule(this.random);
        this.molecules.push(molecule);
        staying.push(molecule);
      }
      staying.slice(wanted).forEach((molecule) => this._leave(molecule));
      const boundCount = Math.round(wanted * effect);
      staying.slice(0, wanted).forEach((molecule, k) => { molecule.bound = k < boundCount; });
    }

    _leave(molecule) {
      Object.assign(molecule, { leaving: true, bound: false, exit: DrugCloud.edgePoint(this.random) });
    }

    // Moves every molecule towards where it is going; molecules that have left are dropped.
    advance(dtMs) {
      let anyGone = false;
      for (const molecule of this.molecules) {
        const target = this._target(molecule);
        const speed = molecule.bound || molecule.leaving || !molecule.settled ? CLOUD.speedPerMs : CLOUD.wanderSpeedPerMs;
        const dx = target.x - molecule.x, dy = target.y - molecule.y;
        const distance = Math.hypot(dx, dy);
        const travel = Math.min(distance, speed * dtMs);
        if (distance > 0) {
          molecule.x += (dx / distance) * travel;
          molecule.y += (dy / distance) * travel;
        }
        if (distance - travel <= CLOUD.arrivalDistance) anyGone = this._arrive(molecule) || anyGone;
      }
      if (anyGone) this.molecules = this.molecules.filter((molecule) => !molecule.gone);
    }

    // Returns true when the molecule has left the figure.
    _arrive(molecule) {
      if (molecule.leaving) return (molecule.gone = true);
      molecule.settled = true;
      if (molecule.bound) return false;
      molecule.visitNode = randomCell(this.random);
      molecule.spot = insideSpot(this.random);
      return false;
    }

    // A paused figure shows where the molecules end up, without the motion (WCAG 2.2.2).
    settle() {
      this.molecules = this.molecules.filter((molecule) => !molecule.leaving);
      for (const molecule of this.molecules) {
        const { x, y } = this._target(molecule);
        Object.assign(molecule, { x, y, settled: true });
      }
    }

    // Where a molecule is heading, as shares of the figure; written into one reused object to avoid garbage per frame.
    _target(molecule) {
      if (molecule.leaving) return molecule.exit;
      const { anchors, width, height } = this.frame;
      if (!anchors?.length) return molecule.spot;
      const cell = anchors[(molecule.bound ? molecule.anchorNode : molecule.visitNode) % anchors.length];
      const offset = molecule.bound ? 0 : 1;
      this.target.x = cell.x / width + offset * molecule.offset.x;
      this.target.y = cell.y / height + offset * molecule.offset.y;
      return this.target;
    }

    // anchors: the cells' positions in pixels. Bound molecules sit on a cell and free ones drift between cells;
    // without cells (the plant sheet) both stay inside the figure's margin.
    draw(context, { width, height, anchors = null }) {
      Object.assign(this.frame, { anchors, width, height });
      const colours = { drug: palette.get(Token.DRUG), edge: palette.get(Token.DRUG_EDGE), paper: palette.get(Token.PAPER), halo: palette.get(Token.DRUG_SOFT) };
      context.lineWidth = CLOUD.edgeWidthPx;
      for (const molecule of this.molecules) {
        const x = molecule.x * width, y = molecule.y * height;
        context.beginPath();
        context.arc(x, y, CLOUD.haloPx, 0, 2 * Math.PI);
        context.fillStyle = colours.halo;
        context.fill();
        hexagon(context, { x, y, radius: CLOUD.radiusPx, fill: molecule.bound ? colours.drug : colours.paper, edge: molecule.bound ? colours.edge : colours.drug });
      }
    }

    static legend() {
      return labelled([
        { group: LegendGroup.DRUG, swatch: Swatch.HEXAGON_OPEN, token: Token.DRUG, message: "legendDrugFree" },
        { group: LegendGroup.DRUG, swatch: Swatch.HEXAGON, token: Token.DRUG, message: "legendDrugBound" },
      ]);
    }
  }

  root.DPC = Object.assign(root.DPC || {}, { DrugCloud });
})(globalThis);

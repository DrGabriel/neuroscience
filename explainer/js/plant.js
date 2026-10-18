// Excitable plant tissue, mirroring simulator/plant_tissue.py: a sheet of FitzHugh-Nagumo cells coupled through
// junctions that the anaesthetic closes. The left column is stimulated and the action potential spreads (or not).
(function (root) {
  "use strict";

  const { AnaestheticAgent, RandomSource, Token, Swatch, LegendGroup, labelled, palette, Surface, clamp, make } = root.DPC;

  function squareSheetJunctions(rows, columns) {
    const first = [], second = [];
    for (let r = 0; r < rows; r++) for (let c = 0; c + 1 < columns; c++) { first.push(r * columns + c); second.push(r * columns + c + 1); }
    for (let r = 0; r + 1 < rows; r++) for (let c = 0; c < columns; c++) { first.push(r * columns + c); second.push((r + 1) * columns + c); }
    return { first: Int32Array.from(first), second: Int32Array.from(second) };
  }

  class PlantTissue {
    // Junction draws are fixed per tissue, as in the study, so a dose change only re-opens or closes junctions.
    constructor(spec, seed) {
      this.spec = spec;
      Object.assign(this, squareSheetJunctions(spec.rows, spec.columns));
      const random = new RandomSource(seed);
      this.failureDraws = Float64Array.from(this.first, () => random.uniform());
      this.agent = new AnaestheticAgent(spec.agent);
      this.cellCount = spec.rows * spec.columns;
      this.voltage = new Float64Array(this.cellCount);
      this.recovery = new Float64Array(this.cellCount);
      this.hasFired = new Uint8Array(this.cellCount);
      this.isOpen = new Uint8Array(this.first.length);
      this.coupling = new Float64Array(this.cellCount);
      this.conductance = spec.junctionConductances[0];
    }

    // Opens or closes junctions for this concentration and restarts the action potential from the left edge.
    start({ concentration, conductance }) {
      this.conductance = conductance;
      const failure = this.agent.transmissionFailure(concentration);
      let open = 0;
      for (let j = 0; j < this.first.length; j++) {
        this.isOpen[j] = this.failureDraws[j] >= failure ? 1 : 0;
        open += this.isOpen[j];
      }
      this.openFraction = open / this.first.length;
      this.voltage.fill(this.spec.restingVoltage);
      this.recovery.fill(this.spec.restingRecovery);
      this.hasFired.fill(0);
      this.firedCount = 0;
      for (let r = 0; r < this.spec.rows; r++) this.voltage[r * this.spec.columns] = this.spec.stimulusVoltage;
      this._markFired();
      this.stepsTaken = 0;
    }

    step() {
      const { voltage, recovery, coupling, first, second, isOpen } = this;
      const { a, b, epsilon } = this.spec.fitzHugh;
      const dt = this.spec.timeStep;
      coupling.fill(0);
      for (let j = 0; j < first.length; j++) {
        if (!isOpen[j]) continue;
        const current = voltage[second[j]] - voltage[first[j]];
        coupling[first[j]] += current;
        coupling[second[j]] -= current;
      }
      for (let i = 0; i < this.cellCount; i++) {
        const v = voltage[i], w = recovery[i];
        voltage[i] = v + dt * (v - (v * v * v) / 3 - w + this.conductance * coupling[i]);
        recovery[i] = w + dt * epsilon * (v + a - b * w);
      }
      this._markFired();
      this.stepsTaken += 1;
    }

    get finished() {
      return this.stepsTaken >= this.spec.durationSteps;
    }

    get reachedFraction() {
      return this.firedCount / this.cellCount;
    }

    _markFired() {
      for (let i = 0; i < this.cellCount; i++) {
        if (this.hasFired[i] || this.voltage[i] <= this.spec.firingVoltage) continue;
        this.hasFired[i] = 1;
        this.firedCount += 1;
      }
    }
  }

  const VOLTAGE_RANGE = Object.freeze({ low: -2.1, high: 2.1 });
  const CLOSED_JUNCTION_GAP = 0.25;
  const RGB_CHANNELS = 4;

  function rgb(hex) {
    const value = parseInt(hex.replace("#", ""), 16);
    return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
  }

  // One pixel per cell (shaded from paper to blue by voltage, tinted pale blue where the wave has already passed),
  // scaled up without smoothing; closed junctions drawn on top in grey, the colour of a failed connection.
  const PASSED_TINT = 0.22;
  class PlantView {
    constructor(canvas) {
      this.surface = new Surface(canvas);
      this.pixels = make("canvas");
      this.overlays = [];
    }

    legend() {
      return labelled([
        { group: LegendGroup.CELLS, swatch: Swatch.SQUARE, token: Token.REACH, message: "legendFiring" },
        { group: LegendGroup.CELLS, swatch: Swatch.SQUARE, token: Token.REACH_SOFT, message: "legendPassed" },
        { group: LegendGroup.CONNECTIONS, swatch: Swatch.LINE, token: Token.STRAY, message: "legendClosed" },
      ]);
    }

    draw(tissue) {
      const { context, width, height } = this.surface.begin();
      const { rows, columns } = tissue.spec;
      const cell = Math.min(width / columns, height / rows);
      const left = (width - cell * columns) / 2, top = (height - cell * rows) / 2;
      this._paintCells(tissue);
      context.imageSmoothingEnabled = false;
      context.drawImage(this.pixels, left, top, cell * columns, cell * rows);
      this._drawClosedJunctions(context, tissue, { cell, left, top });
      for (const overlay of this.overlays) overlay.draw(context, { width, height });
    }

    _paintCells(tissue) {
      const { rows, columns } = tissue.spec;
      this.pixels.width = columns;
      this.pixels.height = rows;
      const pixelContext = this.pixels.getContext("2d");
      const image = pixelContext.createImageData(columns, rows);
      const [paper, firing] = [Token.PAPER, Token.REACH].map((name) => rgb(palette.get(name)));
      const passed = paper.map((channel, k) => channel + (firing[k] - channel) * PASSED_TINT);
      for (let i = 0; i < tissue.cellCount; i++) {
        const level = clamp((tissue.voltage[i] - VOLTAGE_RANGE.low) / (VOLTAGE_RANGE.high - VOLTAGE_RANGE.low)) ** 2;
        const base = tissue.hasFired[i] ? passed : paper;
        for (let channel = 0; channel < 3; channel++) image.data[i * RGB_CHANNELS + channel] = base[channel] + (firing[channel] - base[channel]) * level;
        image.data[i * RGB_CHANNELS + 3] = 255;
      }
      pixelContext.putImageData(image, 0, 0);
    }

    _drawClosedJunctions(context, tissue, { cell, left, top }) {
      const { columns } = tissue.spec;
      context.strokeStyle = palette.get(Token.STRAY);
      context.lineWidth = Math.max(1, cell * CLOSED_JUNCTION_GAP);
      context.beginPath();
      for (let j = 0; j < tissue.first.length; j++) {
        if (tissue.isOpen[j]) continue;
        const a = tissue.first[j], b = tissue.second[j];
        const [row, column] = [Math.floor(b / columns), b % columns];
        const horizontal = Math.floor(a / columns) === row;
        context.moveTo(left + column * cell, top + row * cell);
        context.lineTo(left + (column + (horizontal ? 0 : 1)) * cell, top + (row + (horizontal ? 1 : 0)) * cell);
      }
      context.stroke();
    }
  }

  root.DPC = Object.assign(root.DPC || {}, { PlantTissue, PlantView });
})(globalThis);

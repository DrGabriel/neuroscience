// One playback clock for every figure: play, pause, step one cycle, and a choice of speed.
(function (root) {
  "use strict";

  const { ChoiceGroup, required, t, fixed } = root.DPC;

  // The model has no cycle length of its own; one cycle of a 40 Hz rhythm lasts 25 ms, far too fast to watch.
  // Each speed shows that cycle this many times slower.
  const REFERENCE_CYCLE_MS = 25;
  const MS_PER_SECOND = 1000;
  const Speed = Object.freeze({ SLOW: 100, MEDIUM: 40, FAST: 16 });

  class Playback {
    constructor(scope, { startPlaying }) {
      this.playing = startPlaying;
      this.toggle = required(scope, "[data-play]", "Playback");
      this.stepButton = required(scope, "[data-step]", "Playback");
      this.timebase = required(scope, "[data-timebase]", "Playback");
      this.speed = new ChoiceGroup(scope, "speed", { owner: "Playback", values: Speed, onChange: () => this._show() });
      this.listeners = { pause: [], step: [] };
      this.toggle.addEventListener("click", () => {
        this.playing = !this.playing;
        this._show();
        if (!this.playing) this.listeners.pause.forEach((listener) => listener());
      });
      this.stepButton.addEventListener("click", () => this.listeners.step.forEach((listener) => listener()));
      this._show();
    }

    get cycleMs() {
      return REFERENCE_CYCLE_MS * this.speed.value;
    }

    on(event, listener) {
      this.listeners[event].push(listener);
    }

    _show() {
      this.toggle.textContent = t(this.playing ? "pause" : "play");
      this.toggle.setAttribute("aria-pressed", String(!this.playing));
      this.stepButton.disabled = this.playing;
      this.timebase.textContent = t("cycleLength", { seconds: fixed(this.cycleMs / MS_PER_SECOND, 1) });
      this.timebase.title = t("cycleLengthTitle", { ms: REFERENCE_CYCLE_MS, factor: this.speed.value });
      // The readout hides on narrower screens, so each speed button carries the same information.
      for (const button of this.speed.buttons) {
        const factor = this.speed.values[button.dataset.value];
        button.title = `${t("cycleLength", { seconds: fixed((REFERENCE_CYCLE_MS * factor) / MS_PER_SECOND, 1) })}. ${t("cycleLengthTitle", { ms: REFERENCE_CYCLE_MS, factor })}`;
      }
    }
  }

  root.DPC = Object.assign(root.DPC || {}, { Playback });
})(globalThis);

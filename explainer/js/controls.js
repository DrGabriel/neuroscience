// Shared controls. A scene names its controls in the markup (data-control, data-choice); these classes do the rest.
(function (root) {
  "use strict";

  const { required, transitionPoints, t, make, clamp } = root.DPC;

  // <input type="range" data-control="name"> with an optional <span data-control-value="name"> showing its value.
  class RangeControl {
    constructor(scope, name, { owner, format = String, onChange }) {
      this.input = required(scope, `[data-control="${name}"]`, owner);
      this.label = scope.querySelector(`[data-control-value="${name}"]`);
      this.format = format;
      this.input.addEventListener("input", () => {
        this.show();
        onChange(this.value);
      });
      this.show();
    }

    get value() {
      return Number(this.input.value);
    }

    reset() {
      this.value = this.input.defaultValue;
    }

    set value(value) {
      this.input.value = String(value);
      this.show();
    }

    // Shows the value, and fills the track up to it (in the drug's colour on dose sliders, see styles.css).
    show() {
      if (this.label) this.label.textContent = this.format(this.value);
      const [min, max] = [Number(this.input.min), Number(this.input.max)];
      this.input.style.setProperty("--range-fill", String((this.value - min) / (max - min)));
    }
  }

  // Buttons <button data-choice="name" data-value="KEY"> acting as one pressed-button group over an enum.
  class ChoiceGroup {
    constructor(scope, name, { owner, values, onChange }) {
      this.buttons = [...scope.querySelectorAll(`[data-choice="${name}"]`)];
      if (!this.buttons.length) throw new Error(`${owner}: missing [data-choice="${name}"]`);
      this.values = values;
      this.value = values[this.buttons.find((button) => button.getAttribute("aria-pressed") === "true")?.dataset.value ?? this.buttons[0].dataset.value];
      this.initial = this.value;
      for (const button of this.buttons) {
        button.addEventListener("click", () => {
          this.value = values[button.dataset.value];
          this.show();
          onChange(this.value);
        });
      }
      this.show();
    }

    show() {
      for (const button of this.buttons) button.setAttribute("aria-pressed", String(this.values[button.dataset.value] === this.value));
    }

    reset() {
      this.value = this.initial;
      this.show();
    }
  }

  // Runs a rise-then-fall dose sweep in fast-forward, holding its button busy until it is over.
  class SweepRunner {
    static CYCLE_MS = 35;

    constructor(button, plan) {
      Object.assign(this, { button, plan, idleLabel: button.textContent, running: false });
    }

    // Returns {points, lostAt, regainedAt}, or null when a sweep is already running.
    async run({ cycles, model, conditions, onStep, controls = [] }) {
      if (this.running) return null;
      this._setBusy(true, controls);
      const points = [];
      cycles.restart();
      try {
        for (const { direction, concentration } of this.plan.steps()) {
          let total = 0;
          for (let n = 0; n < this.plan.cyclesPerStep; n++) {
            total += cycles.run(model(), concentration, conditions).giantShare;
            await new Promise((resolve) => root.setTimeout(resolve, SweepRunner.CYCLE_MS));
          }
          points.push({ direction, concentration, share: total / this.plan.cyclesPerStep });
          onStep(points, concentration);
        }
      } finally {
        this._setBusy(false, controls);
      }
      return { points, ...transitionPoints(points, (share) => model().holdsQuorum(share)) };
    }

    _setBusy(busy, controls) {
      this.running = busy;
      this.button.disabled = busy;
      this.button.textContent = busy ? t("sweepBusy") : this.idleLabel;
      for (const control of controls) control.disabled = busy;
    }
  }

  const Key = Object.freeze({ DOWN: "ArrowDown", UP: "ArrowUp", HOME: "Home", END: "End", ENTER: "Enter", SPACE: " ", ESCAPE: "Escape", TAB: "Tab" });
  let pickerCount = 0;

  // A dropdown drawn in the page's own style, matching the section menu. It enhances a native <select>, which stays
  // the source of truth: choosing an option sets the select and fires its "change" event, so code that reads the
  // select is unchanged. A caption marked data-picker-caption in the label moves inside the button, as in the section menu.
  // Keyboard and screen readers follow the WAI-ARIA listbox pattern; the pointer highlights the option under it.
  class Picker {
    constructor(select) {
      this.select = select;
      const id = `picker-${++pickerCount}`;
      this.button = make("button", { type: "button", className: "picker-button" });
      this.button.setAttribute("aria-haspopup", "listbox");
      this.button.setAttribute("aria-expanded", "false");
      this.list = make("ul", { className: "picker-list", id, hidden: true, tabIndex: -1 });
      this.list.setAttribute("role", "listbox");
      this.button.setAttribute("aria-controls", id);
      const label = select.closest("label");
      if (label) this.button.setAttribute("aria-label", label.textContent.trim());
      this.value = make("span", { className: "picker-value" });
      const caption = label?.querySelector("[data-picker-caption]");
      this.button.append(...(caption ? [caption] : []), this.value);
      select.classList.add("visually-hidden");
      select.tabIndex = -1;
      select.setAttribute("aria-hidden", "true");
      select.after(this.button, this.list);
      this.button.addEventListener("click", () => (this.list.hidden ? this.open() : this.close()));
      this.button.addEventListener("keydown", (event) => this._onButtonKey(event));
      this.list.addEventListener("keydown", (event) => this._onListKey(event));
      this.list.addEventListener("click", (event) => this._choose(event.target.closest("[role='option']")));
      this.list.addEventListener("pointermove", (event) => {
        const item = event.target.closest("[role='option']");
        if (item && Number(item.dataset.index) !== this.active) this._highlight(Number(item.dataset.index), { scroll: false });
      });
      document.addEventListener("click", (event) => {
        if (!this.button.parentElement.contains(event.target)) this.close();
      });
      select.addEventListener("change", () => this.sync());
      this.sync();
    }

    // Rebuilds the options and the button label from the select (after options change or a reset).
    sync() {
      const options = [...this.select.options];
      this.list.replaceChildren(...options.map((option, index) => {
        const item = make("li", { textContent: option.textContent, id: `${this.list.id}-${index}` });
        item.setAttribute("role", "option");
        item.setAttribute("aria-selected", String(index === this.select.selectedIndex));
        item.dataset.index = String(index);
        return item;
      }));
      this.value.textContent = this.select.selectedOptions[0]?.textContent ?? "";
      this.button.disabled = this.select.disabled;
    }

    open() {
      if (this.select.disabled) return;
      this.sync();
      this.list.hidden = false;
      this.button.setAttribute("aria-expanded", "true");
      this._highlight(this.select.selectedIndex);
      this.list.focus();
    }

    close() {
      if (this.list.hidden) return;
      this.list.hidden = true;
      this.button.setAttribute("aria-expanded", "false");
    }

    _highlight(index, { scroll = true } = {}) {
      const items = [...this.list.children];
      const bounded = clamp(index, 0, items.length - 1);
      items.forEach((item, k) => item.classList.toggle("active", k === bounded));
      this.list.setAttribute("aria-activedescendant", items[bounded]?.id ?? "");
      if (scroll) items[bounded]?.scrollIntoView({ block: "nearest" });
      this.active = bounded;
    }

    _choose(item) {
      if (!item) return;
      this.select.selectedIndex = Number(item.dataset.index);
      this.select.dispatchEvent(new Event("change", { bubbles: true }));
      this.close();
      this.button.focus();
    }

    _onButtonKey(event) {
      if (![Key.DOWN, Key.UP, Key.ENTER, Key.SPACE].includes(event.key)) return;
      event.preventDefault();
      this.open();
    }

    _onListKey(event) {
      const moves = { [Key.DOWN]: this.active + 1, [Key.UP]: this.active - 1, [Key.HOME]: 0, [Key.END]: this.list.children.length - 1 };
      if (event.key in moves) {
        event.preventDefault();
        this._highlight(moves[event.key]);
      } else if (event.key === Key.ENTER || event.key === Key.SPACE) {
        event.preventDefault();
        this._choose(this.list.children[this.active]);
      } else if (event.key === Key.ESCAPE || event.key === Key.TAB) {
        this.close();
        this.button.focus();
      }
    }
  }

  root.DPC = Object.assign(root.DPC || {}, { RangeControl, ChoiceGroup, SweepRunner, Picker });
})(globalThis);

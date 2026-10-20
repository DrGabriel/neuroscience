// The model's verdict under a network figure: is there quorum, and how far the largest agreeing group is from the
// quorum line. One bar, one line drawn on it, so the threshold is something the reader sees rather than a number.
(function (root) {
  "use strict";

  const { make, t, percent } = root.DPC;

  const QuorumState = Object.freeze({ HELD: "held", LOST: "lost" });
  const quorumState = (holds) => (holds ? QuorumState.HELD : QuorumState.LOST);
  const PERCENT_SCALE = 100;

  // A share between 0 and 1 drawn as a bar, with a marked line the reader can compare it against.
  class ThresholdBar {
    // label: what the bar measures; mark: what the line is, both message keys.
    constructor({ label, mark }) {
      Object.assign(this, { labelKey: label, markKey: mark });
      this.label = make("span", { className: "threshold-label" });
      this.value = make("b", { className: "threshold-value" });
      this.fill = make("span", { className: "threshold-fill" });
      this.markLabel = make("span", { className: "threshold-mark-label" });
      this.mark = make("span", { className: "threshold-mark" }, [this.markLabel]);
      this.track = make("span", { className: "threshold-track" }, [this.fill, this.mark]);
      this.track.setAttribute("role", "meter");
      this.track.setAttribute("aria-valuemin", "0");
      this.track.setAttribute("aria-valuemax", String(PERCENT_SCALE));
      const scale = make("span", { className: "threshold-scale", ariaHidden: "true" }, [make("span", { textContent: percent(0) }), make("span", { textContent: percent(1) })]);
      this.element = make("div", { className: "threshold-bar" }, [make("span", { className: "threshold-head" }, [this.label, this.value]), this.track, scale]);
    }

    show({ share, threshold }) {
      const label = t(this.labelKey);
      const mark = t(this.markKey, { threshold: percent(threshold) });
      this.label.innerHTML = label;
      this.value.textContent = percent(share);
      this.markLabel.innerHTML = mark;
      this.element.style.setProperty("--share", String(share));
      this.element.style.setProperty("--threshold", String(threshold));
      this.track.setAttribute("aria-valuenow", String(Math.round(share * PERCENT_SCALE)));
      this.track.setAttribute("aria-label", `${this.label.textContent}; ${this.markLabel.textContent}`);
    }
  }

  // The verdict: a word with its own icon (a tick or a cross, so it never depends on colour) and the bar of the
  // largest agreeing group against the quorum line.
  class QuorumVerdict {
    constructor(host) {
      this.word = make("strong", { className: "verdict-word" });
      this.reason = make("span", { className: "verdict-reason" });
      this.bar = new ThresholdBar({ label: "verdictLargestGroup", mark: "verdictQuorumLine" });
      const heading = make("span", { className: "verdict-heading" });
      this.heading = heading;
      this.element = make("div", { className: "verdict" }, [
        heading,
        make("p", { className: "verdict-line" }, [make("span", { className: "verdict-icon", ariaHidden: "true" }), this.word, this.reason]),
        this.bar.element,
      ]);
      host.after(this.element);
    }

    show({ share, quorum, holds }) {
      const state = quorumState(holds);
      this.element.dataset.quorum = state;
      this.heading.textContent = t("verdictHeading");
      this.word.textContent = t(holds ? "verdictConscious" : "verdictUnconscious");
      this.reason.textContent = t(holds ? "verdictHeldReason" : "verdictLostReason");
      this.bar.show({ share, threshold: quorum });
    }
  }

  root.DPC = Object.assign(root.DPC || {}, { QuorumState, quorumState, ThresholdBar, QuorumVerdict });
})(globalThis);

// Test outcomes, statistics and predictions exported from the result reports and the paper, rendered as HTML.
(function (root) {
  "use strict";

  const { make, percent, fixed, t, count, translator, DEFAULT_LOCALE } = root.DPC;

  const Verdict = Object.freeze({ ALL: "all", SOME: "some", NONE: "none", NOT_APPLICABLE: "not-applicable", PENDING: "pending" });
  const VERDICT_MESSAGE = Object.freeze({
    [Verdict.ALL]: "verdictAll",
    [Verdict.SOME]: "verdictSome",
    [Verdict.NONE]: "verdictNone",
    [Verdict.NOT_APPLICABLE]: "verdictNotApplicable",
  });
  const KIND_MESSAGE = Object.freeze({ test: "kindTest", "consistency check": "kindConsistency" });
  const DEFAULT_LABEL = "full";
  const STUDY_MESSAGE = Object.freeze({
    "validation:full": "studyValidation",
    "glia:full": "studyGlia",
    "congestion:full": "studyCongestionFull",
    "congestion:confirmatory": "studyCongestionConfirmatory",
    "species:full": "studySpecies",
    "prespecified:full": "studyPrespecified",
  });
  const verdictLabel = (verdict) => t(VERDICT_MESSAGE[verdict]);

  function verdictOf(holding, applicable) {
    if (applicable === 0) return Verdict.NOT_APPLICABLE;
    if (holding === applicable) return Verdict.ALL;
    return holding === 0 ? Verdict.NONE : Verdict.SOME;
  }

  // Outcomes keyed by study, run label and identifier, each with its groups (sizes, organisms or settings). Reports keep
  // their identifiers; publicLabels maps those that reuse a postulate's name to the label the paper shows (test P3 -> T3).
  class OutcomeIndex {
    constructor(outcomes, publicLabels = {}) {
      this.publicLabels = publicLabels;
      this.entries = new Map();
      for (const outcome of outcomes) {
        const key = OutcomeIndex.key(outcome.study, outcome.label, outcome.identifier);
        if (!this.entries.has(key)) this.entries.set(key, { ...outcome, groups: [], holding: 0, applicable: 0 });
        const entry = this.entries.get(key);
        entry.groups.push({ group: outcome.group, holding: outcome.holding, applicable: outcome.applicable });
        entry.holding += outcome.holding;
        entry.applicable += outcome.applicable;
      }
      for (const entry of this.entries.values()) entry.verdict = verdictOf(entry.holding, entry.applicable);
    }

    label(identifier) {
      return this.publicLabels[identifier] ?? identifier;
    }

    static key(study, label, identifier) {
      return `${study}:${label}:${identifier}`;
    }

    // "study:ID" or "study:label:ID".
    find(reference) {
      const parts = reference.split(":");
      const [study, label, identifier] = parts.length === 2 ? [parts[0], DEFAULT_LABEL, parts[1]] : parts;
      return this.entries.get(OutcomeIndex.key(study, label, identifier)) ?? null;
    }

    byStudy() {
      const studies = new Map();
      for (const entry of this.entries.values()) {
        const key = `${entry.study}:${entry.label}`;
        if (!studies.has(key)) studies.set(key, { report: entry.report, entries: [] });
        studies.get(key).entries.push(entry);
      }
      return studies;
    }
  }

  function markPending(node, text) {
    node.classList.add("outcome");
    node.dataset.verdict = Verdict.PENDING;
    node.textContent = text;
  }

  function markVerdict(node, { text, verdict, detail }) {
    node.classList.add("outcome");
    node.dataset.verdict = verdict;
    node.textContent = text;
    node.title = detail;
  }

  function groupCell({ group, holding, applicable }) {
    const bar = make("span", { className: "group-bar" });
    bar.style.setProperty("--fill", String(applicable ? holding / applicable : 0));
    return make("span", { className: "group", title: t("groupRuns", { group, holding, applicable }) }, [
      make("span", { className: "group-label", textContent: group }), bar, make("span", { className: "count", textContent: `${holding}/${applicable}` }),
    ]);
  }

  function renderLedger(container, index) {
    if (translator().code !== DEFAULT_LOCALE) container.append(make("p", { className: "ledger-note", textContent: t("ledgerNote") }));
    for (const [key, { report, entries }] of index.byStudy()) {
      const rows = entries.map((entry) =>
        make("tr", { className: `verdict-${entry.verdict}` }, [
          make("th", { scope: "row", textContent: index.label(entry.identifier) }),
          make("td", {}, [make("span", { textContent: entry.statement }), make("span", { className: "check-kind", textContent: ` ${t("checkKind", { kind: t(KIND_MESSAGE[entry.kind]), verdict: verdictLabel(entry.verdict) })}` })]),
          make("td", { className: "groups" }, entry.groups.map(groupCell)),
        ]),
      );
      container.append(
        make("section", { className: "ledger-report" }, [
          make("h3", { textContent: STUDY_MESSAGE[key] ? t(STUDY_MESSAGE[key]) : key }),
          reportReference(report),
          make("div", { className: "table-scroll" }, [make("table", { className: "ledger" }, [make("tbody", {}, rows)])]),
        ]),
      );
    }
  }

  // <span data-outcome="species:K1"> becomes "K1 held in no run, 2/20 runs", or says the run is pending.
  function renderInlineOutcomes(scope, index) {
    for (const node of scope.querySelectorAll("[data-outcome]")) {
      const entry = index.find(node.dataset.outcome);
      const identifier = index.label(node.dataset.outcome.split(":").pop());
      if (!entry) {
        markPending(node, t("outcomePending", { identifier }));
        continue;
      }
      markVerdict(node, {
        text: t("outcome", { identifier, verdict: verdictLabel(entry.verdict), holding: entry.holding, applicable: entry.applicable }),
        verdict: entry.verdict,
        detail: `${entry.statement}. ${entry.groups.map((group) => `${group.group}: ${group.holding}/${group.applicable}`).join("; ")}`,
      });
    }
  }

  function renderPlantClaims(scope, plantClaims) {
    for (const node of scope.querySelectorAll("[data-plant-claims]")) {
      if (!plantClaims) {
        markPending(node, t("resultPending"));
        continue;
      }
      const held = plantClaims.claims.filter((claim) => claim.holds).length;
      markVerdict(node, {
        text: t("plantClaims", { held, total: plantClaims.claims.length }),
        verdict: verdictOf(held, plantClaims.claims.length),
        detail: plantClaims.claims.map((claim) => `${claim.statement}: ${t(claim.holds ? "claimHeld" : "claimNotHeld")}`).join("; "),
      });
    }
  }

  // Predictions in the reader's language: from the locale file, else from that language's paper, else English.
  function renderPredictions(container, exported) {
    const { code, locale } = translator();
    const predictions = locale.predictions ?? exported[code] ?? exported[DEFAULT_LOCALE];
    for (const prediction of predictions) {
      const statement = make("p", { className: "prediction" });
      statement.innerHTML = prediction.prediction;
      const how = make("p", { className: "how" });
      how.innerHTML = `<span class="label">${t("howToTest")}</span> ${prediction.test}`;
      const falsified = make("p", { className: "how" });
      falsified.innerHTML = `<span class="label">${t("wrongIf")}</span> ${prediction.falsifiedIf}`;
      container.append(make("li", { value: Number(prediction.number) }, [statement, how, falsified]));
    }
  }

  // <span data-stat="c_off, GABAergic-like" data-format="percent|ms|number"> shows the mean at the largest network size.
  const STAT_FORMATS = Object.freeze({ percent, ms: (value) => `${fixed(value, 1)} ms`, number: (value) => fixed(value, 2) });

  function renderStatistics(scope, statistics) {
    for (const node of scope.querySelectorAll("[data-stat]")) {
      const bySize = statistics[node.dataset.stat];
      if (!bySize) throw new Error(`No statistic named "${node.dataset.stat}" in the validation report`);
      const largest = Math.max(...Object.keys(bySize).map(Number));
      node.textContent = STAT_FORMATS[node.dataset.format ?? "number"](bySize[String(largest)].mean);
      node.title = t("statTitle", { size: count(largest) });
    }
  }

  // A report's file name, marked so that the results archive can turn it into a link to its viewer.
  function reportReference(report) {
    const node = make("p", { className: "source", textContent: report });
    node.dataset.report = report;
    return node;
  }

  // Reports keep the study name they were written under; a renamed study points at its current message.
  const STUDY_ALIASES = Object.freeze({ preregistered: "prespecified" });
  const studyMessage = (kind) => `study_${STUDY_ALIASES[kind] ?? kind}`;

  root.DPC = Object.assign(root.DPC || {}, { studyMessage, Verdict, OutcomeIndex, renderLedger, renderInlineOutcomes, renderPlantClaims, renderPredictions, renderStatistics });
})(globalThis);

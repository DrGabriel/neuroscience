// Test outcomes, statistics and predictions exported from the result reports and the paper, rendered as HTML.
(function (root) {
  "use strict";

  const { make, percent, fixed, t, count, translator, DEFAULT_LOCALE } = root.DPC;

  // Share of runs in which a statement held: what the counts say, before any pass rule is applied.
  const Verdict = Object.freeze({ ALL: "all", SOME: "some", NONE: "none", NOT_APPLICABLE: "not-applicable", PENDING: "pending" });
  const CONSISTENCY_KIND = "consistency check";
  const DEFAULT_LABEL = "full";
  const STUDY_MESSAGE = Object.freeze({
    "validation:full": "studyValidation",
    "glia:full": "studyGlia",
    "congestion:full": "studyCongestionFull",
    "congestion:confirmatory": "studyCongestionConfirmatory",
    "species:full": "studySpecies",
    "prespecified:full": "studyPrespecified",
    "learned_timing:full": "studyLearnedTiming",
    "disconnection:full": "studyDisconnection",
    "dpc_readout:full": "studyDpcReadout",
  });

  function verdictOf(holding, applicable) {
    if (applicable === 0) return Verdict.NOT_APPLICABLE;
    if (holding === applicable) return Verdict.ALL;
    return holding === 0 ? Verdict.NONE : Verdict.SOME;
  }

  // The paper's verdict, shown before the counts. Each kind has a label, a plain tooltip and a mark (styles.css).
  const PaperVerdict = Object.freeze({
    PASSED: "passed", FAILED: "failed", NOT_EVALUABLE: "not-evaluable", MIXED: "mixed", COULD_NOT_FAIL: "could-not-fail",
    CONSISTENCY: "consistency", OBSERVATION: "observation", EXTENSION: "extension", COUNTS: "counts", NOT_APPLICABLE: "not-applicable",
  });
  const PAPER_VERDICT_MESSAGE = Object.freeze({
    [PaperVerdict.PASSED]: { label: "paperPassed", tip: "tipPassed" },
    [PaperVerdict.FAILED]: { label: "paperFailed", tip: "tipFailed" },
    [PaperVerdict.NOT_EVALUABLE]: { label: "paperNotEvaluable", tip: "tipNotEvaluable" },
    [PaperVerdict.MIXED]: { label: "paperMixed", tip: "tipMixed" },
    [PaperVerdict.COULD_NOT_FAIL]: { label: "paperCouldNotFail", tip: "tipCouldNotFail" },
    [PaperVerdict.CONSISTENCY]: { label: "paperConsistency", tip: "tipConsistency" },
    [PaperVerdict.OBSERVATION]: { label: "paperObservation", tip: "tipObservation" },
    [PaperVerdict.EXTENSION]: { label: "paperExtension", tip: "tipExtension" },
    [PaperVerdict.COUNTS]: { label: "paperCounts", tip: "tipCounts" },
    [PaperVerdict.NOT_APPLICABLE]: { label: "verdictNotApplicable", tip: "tipNotApplicable" },
  });

  // How a study's results are judged (paper, Section 6 and Section 10, item 28): percolation checks hold only in every
  // run at every network size; pre-specified tests pass at 80% of an organism's runs, as their reports record per
  // group; phase-model and Wilson-Cowan results have no pass rule and are reported as counts.
  const PassRule = Object.freeze({ EVERY_RUN: "ruleEveryRun", REPORTED: "ruleReported", COUNTS: "ruleCounts", OBSERVATION: "ruleObservation", EXTENSION: "ruleExtension" });
  const STUDY_RULE = Object.freeze({ validation: PassRule.EVERY_RUN, glia: PassRule.EVERY_RUN, prespecified: PassRule.REPORTED, learned_timing: PassRule.REPORTED, disconnection: PassRule.REPORTED });
  // Report sections that the paper keeps out of the verdict (Appendix B.4).
  const SECTION_RULE = Object.freeze({ "validation:observations": PassRule.OBSERVATION, "validation:extension_tests": PassRule.EXTENSION });
  const ruleFor = ({ study, section }) => SECTION_RULE[`${study}:${section}`] ?? STUDY_RULE[study] ?? PassRule.COUNTS;

  // Verdicts the paper states in words where the counts alone do not give one, keyed by study and report identifier,
  // with an optional note (a message key) that qualifies them.
  const PAPER_STATED = Object.freeze({
    // Limitation 25: with failure up to 95% and added timing error up to 40 ms, quorum loss could not fail.
    "validation:C1": { verdict: PaperVerdict.COULD_NOT_FAIL, note: "noteMaxima" },
    "species:P2a": { verdict: PaperVerdict.COULD_NOT_FAIL, note: "noteMaxima" },
    "species:P2b": { verdict: PaperVerdict.COULD_NOT_FAIL, note: "noteMaxima" },
    // Section 6: C4, C5 and C6 follow from the model's equations; C4 also missed the every-seed rule by one seed, and
    // C5 depends on the calibration (limitation 29).
    "validation:C4": { verdict: PaperVerdict.CONSISTENCY, note: "noteOneRun" },
    "validation:C5": { verdict: PaperVerdict.CONSISTENCY, note: "noteCalibration" },
    "validation:C6": { verdict: PaperVerdict.CONSISTENCY },
    // Section 6: the rat share keeps quorum, so the model implies rats keep quorum in NREM sleep (limitation 27); deep
    // anaesthesia has no conscious state to return to without arousal drive (E3; Section 5.4, prediction 15).
    "validation:O3": { note: "noteRatSleep" },
    "validation:E3": { note: "noteArousalDrive" },
    // Section 6: T1b passed on fresh seeds as T1c, but the rise may reflect the low awake baseline (Appendix C.12).
    "species:P1b": { note: "noteBaseline" },
    "prespecified:P1c": { note: "noteBaseline" },
    // Section 6 and Section 5.6: A1 failed in every seed but could not have passed.
    "glia:A1": { verdict: PaperVerdict.FAILED, note: "noteCouldNotPass" },
    // Limitation 11: the pre-specified surge at the collapse (T1) failed.
    "species:P1": { verdict: PaperVerdict.FAILED },
    // Limitation 5 and Section 7.2: K1 failed as first tested.
    "species:K1": { verdict: PaperVerdict.FAILED },
    // Section 6 and Appendix D: no local islands (S1, S2); Section 5.4 and the conclusion: no robust inertia in the phase model (S3).
    "species:S1": { verdict: PaperVerdict.FAILED },
    "species:S2": { verdict: PaperVerdict.FAILED },
    "species:S3": { verdict: PaperVerdict.FAILED },
    // Section 6: the distinctive prediction of P8 failed in every seed.
    "species:F3": { verdict: PaperVerdict.FAILED },
    // Section 6 and Section 5.1: congestion failed, in the exploratory and the confirmatory run.
    "congestion:W1": { verdict: PaperVerdict.FAILED },
    "congestion:W2": { verdict: PaperVerdict.FAILED },
    "congestion:W3": { verdict: PaperVerdict.FAILED },
    "congestion:W4": { verdict: PaperVerdict.FAILED },
    // Section 6: L2 held in every seed only because quorum was lost earlier, not later.
    "learned_timing:L2": { note: "noteEarlierLoss" },
  });

  // What the hypothesis expects of each observation, for the ones where "in no run" is the desired outcome: patients
  // are not trapped unconscious (limitation 8, O1 and O2); the rat share of sleep keeps quorum and the human share
  // loses it (Section 6, O3 to O5).
  const Expected = Object.freeze({ EVERY_RUN: "expectedEvery", NO_RUN: "expectedNone" });
  const EXPECTED = Object.freeze({
    "validation:O1": Expected.NO_RUN, "validation:O2": Expected.NO_RUN, "validation:O3": Expected.NO_RUN,
    "validation:O4": Expected.EVERY_RUN, "validation:O5": Expected.EVERY_RUN,
  });

  function metExpectation(expected, entry) {
    if (expected === Expected.EVERY_RUN) return entry.holding === entry.applicable;
    return entry.holding === 0;
  }

  const GROUP_VERDICT = Object.freeze({ passes: PaperVerdict.PASSED, fails: PaperVerdict.FAILED, "not evaluable": PaperVerdict.NOT_EVALUABLE });

  // A pre-specified study's verdict from its groups': one verdict when they agree, MIXED (named per group) when not.
  function reportedVerdict(groups) {
    const verdicts = new Set(groups.map((group) => GROUP_VERDICT[group.groupVerdict]));
    return verdicts.size === 1 ? [...verdicts][0] : PaperVerdict.MIXED;
  }

  const RULE_VERDICT = Object.freeze({
    [PassRule.EVERY_RUN]: (entry) => (entry.holding === entry.applicable ? PaperVerdict.PASSED : PaperVerdict.FAILED),
    [PassRule.REPORTED]: (entry) => reportedVerdict(entry.groups),
    [PassRule.COUNTS]: () => PaperVerdict.COUNTS,
    [PassRule.OBSERVATION]: () => PaperVerdict.OBSERVATION,
    [PassRule.EXTENSION]: () => PaperVerdict.EXTENSION,
  });

  // The paper's verdict on one entry: stated in the paper, a consistency check, or read by the study's pass rule.
  function paperVerdictOf(entry) {
    const stated = PAPER_STATED[`${entry.study}:${entry.identifier}`] ?? {};
    const expected = EXPECTED[`${entry.study}:${entry.identifier}`] ?? null;
    const base = { note: stated.note ?? null, expected, metExpectation: expected ? metExpectation(expected, entry) : null };
    if (entry.applicable === 0) return { ...base, verdict: PaperVerdict.NOT_APPLICABLE };
    if (stated.verdict) return { ...base, verdict: stated.verdict };
    if (entry.kind === CONSISTENCY_KIND) return { ...base, verdict: PaperVerdict.CONSISTENCY };
    return { ...base, verdict: RULE_VERDICT[ruleFor(entry)](entry) };
  }

  // Outcomes keyed by study, run label and identifier, each with its groups (sizes, organisms or settings). Reports keep
  // their identifiers; publicLabels maps those that clash with another name to the label the paper shows: shared ones
  // in every study (test P3 -> T3), byStudy ones in one study only (congestion G1 -> B1).
  class OutcomeIndex {
    constructor(outcomes, publicLabels = { shared: {}, byStudy: {} }) {
      this.publicLabels = publicLabels;
      this.entries = new Map();
      for (const outcome of outcomes) {
        const key = OutcomeIndex.key(outcome.study, outcome.label, outcome.identifier);
        if (!this.entries.has(key)) this.entries.set(key, { ...outcome, groups: [], holding: 0, applicable: 0 });
        const entry = this.entries.get(key);
        entry.groups.push({ group: outcome.group, holding: outcome.holding, applicable: outcome.applicable, groupVerdict: outcome.groupVerdict ?? null });
        entry.holding += outcome.holding;
        entry.applicable += outcome.applicable;
      }
      for (const entry of this.entries.values()) {
        entry.verdict = verdictOf(entry.holding, entry.applicable);
        entry.paper = paperVerdictOf(entry);
      }
    }

    label(study, identifier) {
      return this.publicLabels.byStudy?.[study]?.[identifier] ?? this.publicLabels.shared?.[identifier] ?? identifier;
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
        if (!studies.has(key)) studies.set(key, { report: entry.report, study: entry.study, entries: [] });
        studies.get(key).entries.push(entry);
      }
      return studies;
    }
  }

  const groupVerdictLabel = (group) => t(PAPER_VERDICT_MESSAGE[GROUP_VERDICT[group.groupVerdict]].label);

  // The verdict in words: "passed", "failed on C. elegans; not evaluable on Human", "observation; expected in no run".
  function verdictText(entry) {
    const { verdict, expected, metExpectation: met } = entry.paper;
    if (verdict === PaperVerdict.MIXED) return entry.groups.map((group) => t("groupVerdict", { group: group.group, verdict: groupVerdictLabel(group) })).join("; ");
    const label = t(PAPER_VERDICT_MESSAGE[verdict].label);
    if (!expected) return label;
    return t("verdictWithExpectation", { verdict: label, expected: t(expected), met: t(met ? "expectationMet" : "expectationMissed") });
  }

  // The plain tooltip: what this kind of verdict means, the note that qualifies it, the statement and each group's count.
  function verdictDetail(entry) {
    const groups = entry.groups.map((group) => `${group.group}: ${group.holding}/${group.applicable}`).join("; ");
    const note = entry.paper.note ? ` ${t(entry.paper.note)}.` : "";
    return `${t(PAPER_VERDICT_MESSAGE[entry.paper.verdict].tip)}${note} ${entry.statement}. ${groups}`;
  }

  function markPending(node, text) {
    node.classList.add("outcome");
    node.dataset.paperVerdict = Verdict.PENDING;
    node.textContent = text;
    node.title = t("tipPending");
  }

  function markVerdict(node, { text, verdict, detail }) {
    node.classList.add("outcome");
    node.dataset.paperVerdict = verdict;
    node.textContent = text;
    node.title = detail;
  }

  function groupCell({ group, holding, applicable, groupVerdict }) {
    const bar = make("span", { className: "group-bar" });
    bar.style.setProperty("--fill", String(applicable ? holding / applicable : 0));
    // Always four cells, so that every group lines up in the ledger's grid.
    const verdict = [make("span", { className: "group-verdict", textContent: groupVerdict ? groupVerdictLabel({ groupVerdict }) : "" })];
    return make("span", { className: "group", title: t("groupRuns", { group, holding, applicable }) }, [
      make("span", { className: "group-label", textContent: group }), bar, make("span", { className: "count", textContent: `${holding}/${applicable}` }), ...verdict,
    ]);
  }

  function ledgerRow(entry, index) {
    const note = entry.paper.note ? [make("span", { className: "verdict-note", textContent: t(entry.paper.note) })] : [];
    const verdict = make("span", { className: "outcome" });
    markVerdict(verdict, { text: verdictText(entry), verdict: entry.paper.verdict, detail: verdictDetail(entry) });
    return make("tr", { className: "ledger-row" }, [
      make("th", { scope: "row", textContent: index.label(entry.study, entry.identifier) }),
      make("td", { className: "ledger-verdict" }, [verdict, ...note]),
      make("td", { textContent: entry.statement }),
      make("td", { className: "groups" }, entry.groups.map(groupCell)),
    ]);
  }

  function renderLedger(container, index) {
    if (translator().code !== DEFAULT_LOCALE) container.append(make("p", { className: "ledger-note", textContent: t("ledgerNote") }));
    for (const [key, { report, study, entries }] of index.byStudy()) {
      const rows = entries.map((entry) => ledgerRow(entry, index));
      const head = make("tr", {}, ["ledgerTest", "ledgerVerdict", "ledgerStatement", "ledgerRuns"].map((message) => make("th", { scope: "col", textContent: t(message) })));
      container.append(
        make("section", { className: "ledger-report" }, [
          make("h3", { textContent: STUDY_MESSAGE[key] ? t(STUDY_MESSAGE[key]) : key }),
          make("p", { className: "ledger-rule", textContent: t(STUDY_RULE[study] ?? PassRule.COUNTS) }),
          reportReference(report),
          make("div", { className: "table-scroll" }, [make("table", { className: "ledger" }, [make("thead", {}, [head]), make("tbody", {}, rows)])]),
        ]),
      );
    }
  }

  // <span data-outcome="species:K1"> becomes "K1: failed, 24/46 runs", or says the run is pending.
  function renderInlineOutcomes(scope, index) {
    for (const node of scope.querySelectorAll("[data-outcome]")) {
      const entry = index.find(node.dataset.outcome);
      const parts = node.dataset.outcome.split(":");
      const identifier = index.label(parts[0], parts.at(-1));
      if (!entry) {
        markPending(node, t("outcomePending", { identifier }));
        continue;
      }
      markVerdict(node, {
        text: t("outcome", { identifier, verdict: verdictText(entry), holding: entry.holding, applicable: entry.applicable }),
        verdict: entry.paper.verdict,
        detail: verdictDetail(entry),
      });
    }
  }

  const PLANT_VERDICT = Object.freeze({ [Verdict.ALL]: PaperVerdict.PASSED, [Verdict.NONE]: PaperVerdict.FAILED, [Verdict.SOME]: PaperVerdict.MIXED, [Verdict.NOT_APPLICABLE]: PaperVerdict.NOT_APPLICABLE });

  function renderPlantClaims(scope, plantClaims) {
    for (const node of scope.querySelectorAll("[data-plant-claims]")) {
      if (!plantClaims) {
        markPending(node, t("resultPending"));
        continue;
      }
      const held = plantClaims.claims.filter((claim) => claim.holds).length;
      markVerdict(node, {
        text: t("plantClaims", { held, total: plantClaims.claims.length }),
        verdict: PLANT_VERDICT[verdictOf(held, plantClaims.claims.length)],
        detail: plantClaims.claims.map((claim) => `${claim.statement}: ${t(claim.holds ? "claimHeld" : "claimNotHeld")}`).join("; "),
      });
    }
  }

  // Predictions in the reader's language: from the locale file, else from that language's paper, else English.
  function renderPredictions(container, exported) {
    const { code, locale } = translator();
    const predictions = locale.predictions ?? exported[code] ?? exported[DEFAULT_LOCALE];
    for (const prediction of predictions) {
      const lead = make("p", { className: "prediction-lead", textContent: t(`predictionLead${prediction.number}`) });
      const statement = make("p", { className: "prediction" });
      statement.innerHTML = prediction.prediction;
      const how = make("p", { className: "how" });
      how.innerHTML = `<span class="label">${t("howToTest")}</span> ${prediction.test}`;
      const falsified = make("p", { className: "how" });
      falsified.innerHTML = `<span class="label">${t("wrongIf")}</span> ${prediction.falsifiedIf}`;
      container.append(make("li", { value: Number(prediction.number) }, [lead, statement, how, falsified]));
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

  root.DPC = Object.assign(root.DPC || {}, { studyMessage, Verdict, PaperVerdict, PassRule, verdictText, verdictDetail, OutcomeIndex, renderLedger, renderInlineOutcomes, renderPlantClaims, renderPredictions, renderStatistics });
})(globalThis);

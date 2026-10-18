// The results archive: every study report, current and superseded, with a viewer for its report, its full data
// and, for sweep studies, the curve of every seed. Reports load on demand as scripts, because a page opened from
// file:// cannot fetch files. Everything shown is read from the reports; nothing is computed here but means.
(function (root) {
  "use strict";

  const { Token, Swatch, LegendGroup, labelled, legendEntry, palette, Surface, scale, polyline, make, t, organismName, Picker, drawShareAxes, DASH } = root.DPC;
  const CURRENT_SET = "current";
  const JSON_CHUNK = 100;
  // Reports can be tens of megabytes once parsed, so only the most recently opened few are kept.
  const KEPT_REPORTS = 2;
  const ViewerTab = Object.freeze({ REPORT: "REPORT", DATA: "DATA", CURVES: "CURVES" });

  // ---- Loading ---------------------------------------------------------------------------------------------------

  class ReportLoader {
    constructor() {
      this.loaded = new Map();
      this.waiting = new Map();
      root.DPC_RESULT_LOADED = (identifier, payload) => this._arrived(identifier, payload);
    }

    load(entry) {
      if (this.loaded.has(entry.identifier)) return Promise.resolve(this.loaded.get(entry.identifier));
      if (!this.waiting.has(entry.identifier)) this.waiting.set(entry.identifier, this._inject(entry));
      return this.waiting.get(entry.identifier).promise;
    }

    _arrived(identifier, payload) {
      const pending = this.waiting.get(identifier);
      this.waiting.delete(identifier);
      pending?.script.remove();
      this.loaded.set(identifier, payload);
      if (this.loaded.size > KEPT_REPORTS) this.loaded.delete(this.loaded.keys().next().value);
      pending?.resolve(payload);
    }

    _inject(entry) {
      const pending = { script: make("script", { src: entry.script }) };
      pending.promise = new Promise((resolve, reject) => Object.assign(pending, { resolve, reject }));
      pending.script.addEventListener("error", () => {
        this.waiting.delete(entry.identifier);
        pending.script.remove();
        pending.reject(new Error(`Could not load ${entry.script}`));
      });
      document.head.append(pending.script);
      return pending;
    }
  }

  // ---- Markdown (the reports use headings, tables, paragraphs, lists and inline code/bold only) ------------------

  const INLINE = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g;

  function inline(text) {
    return text.split(INLINE).filter(Boolean).map((part) => {
      if (part.startsWith("`")) return make("code", { textContent: part.slice(1, -1) });
      if (part.startsWith("**")) return make("b", { textContent: part.slice(2, -2) });
      if (part.startsWith("*") && part.length > 2) return make("i", { textContent: part.slice(1, -1) });
      return document.createTextNode(part);
    });
  }

  const cells = (line) => line.trim().replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim());

  function table(lines) {
    const [header, , ...rows] = lines;
    const head = make("thead", {}, [make("tr", {}, cells(header).map((cell) => make("th", {}, inline(cell))))]);
    const body = make("tbody", {}, rows.map((row) => make("tr", {}, cells(row).map((cell) => make("td", {}, inline(cell))))));
    return make("div", { className: "table-scroll" }, [make("table", { className: "report-table" }, [head, body])]);
  }

  function block(lines) {
    const first = lines[0];
    const heading = first.match(/^(#{1,6})\s+(.*)$/);
    if (heading) return make(`h${Math.min(6, heading[1].length + 2)}`, {}, inline(heading[2]));
    if (first.startsWith("|")) return table(lines);
    if (first.startsWith("- ")) return make("ul", {}, lines.map((line) => make("li", {}, inline(line.slice(2)))));
    if (first.startsWith("```")) return make("pre", {}, [make("code", { textContent: lines.slice(1, -1).join("\n") })]);
    return make("p", {}, inline(lines.join(" ")));
  }

  // Splits on blank lines, keeping headings on their own, and builds DOM nodes (never HTML strings).
  function renderMarkdown(text) {
    const blocks = [];
    let current = [];
    const flush = () => {
      if (current.length) blocks.push(current);
      current = [];
    };
    for (const line of text.split("\n")) {
      if (!line.trim()) flush();
      else if (/^#{1,6}\s/.test(line)) {
        flush();
        blocks.push([line]);
      } else current.push(line);
    }
    flush();
    return make("div", { className: "report-body" }, blocks.map(block));
  }

  // ---- JSON tree: each object or array opens on demand; long arrays open in chunks -------------------------------

  function scalar(value) {
    const kind = value === null ? "null" : typeof value;
    return make("span", { className: `json-${kind}`, textContent: kind === "string" ? JSON.stringify(value) : String(value) });
  }

  function jsonNode(key, value) {
    const label = key === null ? [] : [make("span", { className: "json-key", textContent: `${key}: ` })];
    if (value === null || typeof value !== "object") return make("div", { className: "json-leaf" }, [...label, scalar(value)]);
    const isArray = Array.isArray(value);
    const size = isArray ? value.length : Object.keys(value).length;
    const summary = make("summary", {}, [...label, make("span", { className: "json-size", textContent: t(isArray ? "jsonItems" : "jsonFields", { count: size }) })]);
    const node = make("details", { className: "json-node" }, [summary]);
    node.addEventListener("toggle", () => {
      if (node.open && node.childElementCount === 1) node.append(...jsonChildren(value));
    });
    return node;
  }

  // A run of a long array, opened on its own; its items are only built when it is opened.
  function jsonChunk(array, start) {
    const end = Math.min(array.length, start + JSON_CHUNK);
    const node = make("details", { className: "json-node" }, [make("summary", {}, [make("span", { className: "json-key", textContent: `[${start}–${end - 1}]` })])]);
    node.addEventListener("toggle", () => {
      if (!node.open || node.childElementCount > 1) return;
      for (let index = start; index < end; index++) node.append(jsonNode(index, array[index]));
    });
    return node;
  }

  function jsonChildren(value) {
    if (!Array.isArray(value)) return Object.entries(value).map(([key, child]) => jsonNode(key, child));
    if (value.length <= JSON_CHUNK) return value.map((child, index) => jsonNode(index, child));
    const chunks = [];
    for (let start = 0; start < value.length; start += JSON_CHUNK) chunks.push(jsonChunk(value, start));
    return chunks;
  }

  // ---- Curves of every seed (cross-species and pre-registered studies) -----------------------------------------

  const mean = (rows) => rows[0].map((_, k) => rows.reduce((sum, row) => sum + row[k], 0) / rows.length);
  const CURVE_LINE = Object.freeze({ seed: 1, mean: 2.2 });
  const CURVES_LEGEND = Object.freeze([
    { group: LegendGroup.CHART, swatch: Swatch.LINE, token: Token.STRAY, message: "curvesSeed" },
    { group: LegendGroup.CHART, swatch: Swatch.LINE, token: Token.INK, message: "curvesMean" },
    { group: LegendGroup.CHART, swatch: Swatch.DASHED, token: Token.INK, message: "curvesEmergence" },
  ]);

  // Global coherence of every seed, as recorded in the report, with the mean going under and coming back.
  class CurveView {
    static MARGIN = Object.freeze({ left: 44, right: 12, top: 12, bottom: 30 });

    constructor(canvas) {
      this.runs = [];
      this.surface = new Surface(canvas, { onResize: () => this.draw(this.runs) });
    }

    draw(runs) {
      this.runs = runs;
      const { context, width, height } = this.surface.begin();
      if (!runs.length) return;
      const margin = CurveView.MARGIN;
      const concentrations = runs[0].concentrations;
      const maxConcentration = concentrations[concentrations.length - 1];
      const px = scale([0, maxConcentration], [margin.left, width - margin.right]);
      const py = scale([0, 1], [height - margin.bottom, margin.top]);
      drawShareAxes(context, { px, py, margin, width, height, maxConcentration });
      const series = (values) => values.map((y, k) => ({ x: concentrations[k], y }));
      context.lineWidth = CURVE_LINE.seed;
      context.strokeStyle = palette.get(Token.STRAY);
      for (const run of runs) polyline(context, series(run.induction_coherence), px, py);
      context.strokeStyle = palette.get(Token.INK);
      context.lineWidth = CURVE_LINE.mean;
      polyline(context, series(mean(runs.map((run) => run.induction_coherence))), px, py);
      context.setLineDash(DASH.emergence);
      polyline(context, series(mean(runs.map((run) => run.emergence_coherence))), px, py);
      context.setLineDash([]);
    }
  }

  // Built once with the viewer; each report with curves is loaded into it.
  class CurveExplorer {
    constructor(panel) {
      this.runs = [];
      this.organism = this._select(t("curvesOrganism"));
      this.condition = this._select(t("curvesCondition"));
      const canvas = make("canvas", { className: "curves" });
      this.caption = make("p", { className: "curves-caption" });
      const legend = make("ul", { className: "curves-legend" }, labelled(CURVES_LEGEND).map(legendEntry));
      panel.append(make("div", { className: "curves-controls" }, [this.organism.label, this.condition.label]), canvas, legend, this.caption);
      this.view = new CurveView(canvas);
      this.organism.select.addEventListener("change", () => this._fillConditions());
      this.condition.select.addEventListener("change", () => this.draw());
      for (const { select } of [this.organism, this.condition]) new Picker(select);
    }

    _select(caption) {
      const select = make("select");
      return { select, label: make("label", { className: "control" }, [make("span", { textContent: caption }), select]) };
    }

    load(document) {
      this.runs = document.runs.filter((run) => Array.isArray(run.induction_coherence));
      const organisms = [...new Set(this.runs.map((run) => run.organism))];
      this.organism.select.replaceChildren(...organisms.map((key) => new Option(organismName(key), key)));
      this.organism.select.dispatchEvent(new Event("change"));
    }

    // Condition names are the study's own labels, kept as written in the report.
    _fillConditions() {
      const conditions = [...new Set(this.runs.filter((run) => run.organism === this.organism.select.value).map((run) => run.condition))];
      this.condition.select.replaceChildren(...conditions.map((value) => new Option(value, value)));
      this.condition.select.dispatchEvent(new Event("change"));
    }

    draw() {
      const shown = this.runs.filter((run) => run.organism === this.organism.select.value && run.condition === this.condition.select.value);
      this.view.draw(shown);
      this.caption.textContent = t("curvesCaption", { seeds: shown.length });
    }
  }

  // ---- Viewer --------------------------------------------------------------------------------------------------

  class ReportViewer {
    constructor(dialog, loader) {
      Object.assign(this, { dialog, loader });
      this.title = dialog.querySelector("[data-viewer-title]");
      this.meta = dialog.querySelector("[data-viewer-meta]");
      this.links = dialog.querySelector("[data-viewer-links]");
      this.tabs = [...dialog.querySelectorAll("[role='tab']")];
      this.panels = Object.fromEntries(Object.values(ViewerTab).map((tab) => [tab, dialog.querySelector(`[data-panel="${tab}"]`)]));
      this.status = Object.fromEntries(Object.values(ViewerTab).map((tab) => [tab, make("p", { className: "muted" })]));
      Object.entries(this.status).forEach(([tab, status]) => this.panels[tab].before(status));
      this.content = { [ViewerTab.REPORT]: make("div"), [ViewerTab.DATA]: make("div") };
      this.panels[ViewerTab.REPORT].append(this.content[ViewerTab.REPORT]);
      this.panels[ViewerTab.DATA].append(this.content[ViewerTab.DATA]);
      this.curves = new CurveExplorer(this.panels[ViewerTab.CURVES]);
      this.tabs.forEach((tab) => tab.addEventListener("click", () => this.show(tab.dataset.tab)));
      dialog.querySelector("[role='tablist']").addEventListener("keydown", (event) => this._onTabKey(event));
      dialog.querySelector("[data-viewer-close]").addEventListener("click", () => dialog.close());
      dialog.addEventListener("click", (event) => event.target === dialog && dialog.close());
    }

    async open(entry, tab = ViewerTab.REPORT) {
      this.title.textContent = describeEntry(entry);
      this.meta.textContent = provenanceLine(entry);
      this.links.replaceChildren(...rawLinks(entry));
      this.tabs.find((button) => button.dataset.tab === ViewerTab.CURVES).hidden = !entry.has_curves;
      this._setStatus(t("viewerLoading"));
      Object.values(this.content).forEach((node) => node.replaceChildren());
      this.show(tab);
      if (!this.dialog.open) this.dialog.showModal();
      try {
        this._fill(entry, await this.loader.load(entry));
        this._setStatus("");
      } catch {
        this._setStatus(t("viewerLoadFailed"));
      }
    }

    _setStatus(text) {
      for (const status of Object.values(this.status)) Object.assign(status, { textContent: text, hidden: !text });
    }

    _fill(entry, { markdown, document }) {
      this.content[ViewerTab.REPORT].replaceChildren(renderMarkdown(markdown));
      const tree = jsonNode(null, document);
      tree.open = true;
      this.content[ViewerTab.DATA].replaceChildren(tree);
      if (entry.has_curves) this.curves.load(document);
    }

    // Left and right arrows move between the visible tabs (WAI-ARIA tabs pattern).
    _onTabKey(event) {
      const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
      if (!step) return;
      event.preventDefault();
      const visible = this.tabs.filter((tab) => !tab.hidden);
      const next = visible[(visible.findIndex((tab) => tab.dataset.tab === this.tab) + step + visible.length) % visible.length];
      this.show(next.dataset.tab);
      next.focus();
    }

    show(tab) {
      this.tab = tab;
      for (const button of this.tabs) button.setAttribute("aria-selected", String(button.dataset.tab === tab));
      for (const [name, panel] of Object.entries(this.panels)) panel.hidden = name !== tab;
    }
  }

  const studyName = (entry) => t(`study_${entry.kind}`);
  // ISO time to the minute: "2026-10-18 13:54 UTC".
  const startedText = (entry) => `${entry.started_utc.slice(0, "YYYY-MM-DDTHH:MM".length).replace("T", " ")} UTC`;
  const describeEntry = (entry) => `${studyName(entry)} · ${t(`run_${entry.label}`)} · ${startedText(entry)}`;

  function provenanceLine(entry) {
    const commit = entry.git_commit ? entry.git_commit.slice(0, 7) : "?";
    const dirty = entry.working_tree_dirty ? ` (${t("archiveDirty")})` : "";
    return `${entry.machine} · ${t("archiveCommit")} ${commit}${dirty}`;
  }

  function rawLinks(entry) {
    const links = [make("a", { href: entry.json_link, textContent: t("viewerRawJson"), target: "_blank", rel: "noopener" })];
    if (entry.markdown_link) links.push(make("a", { href: entry.markdown_link, textContent: t("viewerRawMarkdown"), target: "_blank", rel: "noopener" }));
    return links;
  }

  // ---- The list --------------------------------------------------------------------------------------------------

  function checksText(checks) {
    if (!checks.checks) return t("archiveNoChecks");
    return t("archiveChecksSummary", { every: checks.holding_in_every_run, none: checks.holding_in_none, checks: checks.checks });
  }

  class ResultsArchive {
    constructor({ list, dialog, catalogue }) {
      Object.assign(this, { list, catalogue });
      this.viewer = new ReportViewer(dialog, new ReportLoader());
      this.byFile = new Map(catalogue.filter((entry) => entry.report_set === CURRENT_SET).map((entry) => [entry.identifier.split("/").pop(), entry]));
      this.render();
    }

    render() {
      const sets = [...new Set(this.catalogue.map((entry) => entry.report_set))];
      const ordered = [CURRENT_SET, ...sets.filter((set) => set !== CURRENT_SET).reverse()];
      this.list.replaceChildren(...ordered.map((set) => this._setSection(set)));
    }

    _setSection(set) {
      const entries = this.catalogue.filter((entry) => entry.report_set === set);
      const current = set === CURRENT_SET;
      const heading = make("h3", { textContent: current ? t("archiveCurrent") : t("archiveSuperseded", { set }) });
      const note = entries[0]?.set_note ? [make("p", { className: "muted", textContent: entries[0].set_note })] : [];
      const head = make("tr", {}, ["archiveStudy", "archiveStarted", "archiveChecks", "archiveMachine", ""].map((key) => make("th", { textContent: key ? t(key) : "" })));
      const rows = entries.map((entry) => this._row(entry));
      const tableNode = make("div", { className: "table-scroll" }, [make("table", { className: "archive-table" }, [make("thead", {}, [head]), make("tbody", {}, rows)])]);
      const section = make("section", { className: `archive-set${current ? "" : " superseded"}` }, [heading, ...note, tableNode]);
      return current ? section : make("details", { className: "archive-older" }, [make("summary", { textContent: t("archiveShowOlder", { set, count: entries.length }) }), section]);
    }

    _row(entry) {
      const open = make("button", { type: "button", className: "key", textContent: t("archiveOpen") });
      open.addEventListener("click", () => this.viewer.open(entry));
      return make("tr", {}, [
        make("td", {}, [make("b", { textContent: studyName(entry) }), make("br"), make("span", { className: "muted", textContent: t(`run_${entry.label}`) })]),
        make("td", { className: "mono", textContent: startedText(entry) }),
        make("td", { textContent: checksText(entry.checks) }),
        make("td", { className: "mono", textContent: provenanceLine(entry) }),
        make("td", {}, [open]),
      ]);
    }

    // Every element marked data-report="<report file name>" becomes a button that opens that report.
    linkify(scope) {
      for (const node of scope.querySelectorAll("[data-report]")) {
        const entry = this.byFile.get(node.dataset.report.replace(/\.(json|md)$/, ""));
        if (!entry) continue;
        const button = make("button", { type: "button", className: "report-link", textContent: node.dataset.report });
        button.addEventListener("click", () => this.viewer.open(entry));
        node.replaceChildren(button);
      }
    }
  }

  root.DPC = Object.assign(root.DPC || {}, { ResultsArchive, renderMarkdown, ViewerTab });
})(globalThis);

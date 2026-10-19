// Bootstraps the article: shared context, scenes, playback, navigation, figure numbers and reported results.
(function (root) {
  "use strict";

  const {
    ModelFactory, Network, Figures, Playback, Picker, palette, make, t, count, clamp, translator, registry, remember,
    OutcomeIndex, namedNeuropils, renderLedger, renderInlineOutcomes, renderPlantClaims, renderPredictions, renderStatistics, ResultsArchive,
  } = root.DPC;
  const data = root.DPC_EXPLAINER_DATA;
  const SEED = 2026;
  const MAX_FRAME_MS = 100;
  const TRANSLATED_ATTRIBUTES = Object.freeze(["aria-label", "title", "data-channel"]);
  const PLACE_KEY = "dpc-explainer-reading-place";

  // Where the reader is: the section at the top of the window and how far through it, as a share of its height.
  // Text length differs between languages, so a pixel offset would land somewhere else after a language change.
  // The sticky bar covers the top of the window; reading starts below it.
  const barHeight = () => document.querySelector(".topbar").offsetHeight;

  function readingPlace() {
    const top = barHeight();
    const sections = [...document.querySelectorAll("#top, section.part")];
    const current = sections.filter((section) => section.getBoundingClientRect().top <= top + 1).pop() ?? sections[0];
    const box = current.getBoundingClientRect();
    return { id: current.id, share: clamp((top - box.top) / box.height) };
  }

  function rememberPlace(place) {
    try {
      root.sessionStorage.setItem(PLACE_KEY, JSON.stringify(place));
    } catch {
      // Storage can be blocked; the reader then lands at the start of the section named in the address.
    }
  }

  // Returns the reader to the same point of the same section, once, after a language change.
  function restorePlace() {
    let place = null;
    try {
      place = JSON.parse(root.sessionStorage.getItem(PLACE_KEY));
      root.sessionStorage.removeItem(PLACE_KEY);
    } catch {
      return;
    }
    const section = place && document.getElementById(place.id);
    if (!section || location.hash !== `#${place.id}`) return;
    const scrollTo = () => root.scrollTo({ top: section.getBoundingClientRect().top + root.scrollY + place.share * section.offsetHeight - barHeight(), behavior: "instant" });
    scrollTo();
    document.fonts?.ready.then(scrollTo);
  }

  // The page's text in the reader's language: element content, translated attributes, title and notice.
  function applyLanguage() {
    const reader = translator();
    const { code, locale } = reader;
    document.documentElement.lang = code;
    for (const node of document.querySelectorAll("[data-i18n]")) node.innerHTML = reader.content(node.dataset.i18n);
    for (const node of document.querySelectorAll("[data-message]")) node.textContent = t(node.dataset.message);
    for (const name of TRANSLATED_ATTRIBUTES) {
      for (const node of document.querySelectorAll(`[data-i18n-${name}]`)) node.setAttribute(name, reader.content(node.getAttribute(`data-i18n-${name}`)));
    }
    document.querySelector("[data-current-section]").textContent = t("contents");
    const notice = document.querySelector("[data-locale-notice]");
    notice.hidden = !locale.notice;
    notice.textContent = locale.notice ?? "";
    const picker = document.querySelector("[data-language]");
    for (const [option, { name }] of registry) picker.append(new Option(name, option, false, option === code));
    picker.addEventListener("change", () => {
      remember(picker.value);
      const place = readingPlace();
      rememberPlace(place);
      const url = new URL(location.href);
      url.searchParams.set("lang", picker.value);
      url.hash = place.id;
      location.assign(url);
    });
  }

  // Numbers quoted in the running text, computed once from the data.
  function factsFrom(network) {
    return Object.freeze({
      wormSize: t("wormSize", { cells: count(network.nodeCount), connections: count(network.connectionCount) }),
      humanSize: t("humanSize", { regions: count(data.human.nodeCount), connections: count(data.human.connections.length / 2) }),
      sensoryCount: count(network.sensoryNodes.length),
      feedbackCount: count(network.feedbackCount()),
      directedCount: count(network.directed.count),
      flyNeurons: count(data.fly.neuronCount),
      flyConnections: count(data.fly.connectionCount),
      flyNeuropils: count(namedNeuropils(data.fly.neuropils).length),
    });
  }

  applyLanguage();

  // Each figure gets a polite live region that speaks its description after the reader changes a control.
  const descriptions = new Map();
  function announce(scene) {
    const text = scene.describe();
    if (text) descriptions.get(scene).textContent = text;
  }

  const network = new Network(data.network);
  const facts = factsFrom(network);
  const context = Object.freeze({ data, seed: SEED, network, models: new ModelFactory(data), facts, announce });
  const scenes = [...document.querySelectorAll("[data-scene]")].map((scope) => new Figures[scope.dataset.scene](scope, context));
  const visible = new Set();
  const awaitingAnnouncement = new Set();

  for (const scene of scenes) {
    scene.showLegend();
    scene.offerReset();
  }
  // Dropdowns in the page's own style; created last so that every option the scenes add is present.
  for (const select of document.querySelectorAll("select")) new Picker(select);

  for (const [index, scene] of scenes.entries()) {
    const region = make("p", { className: "visually-hidden", id: `description-${index + 1}` });
    scene.scope.append(region);
    for (const canvas of scene.scope.querySelectorAll("canvas")) canvas.setAttribute("aria-describedby", region.id);
    descriptions.set(scene, region);
    for (const type of ["input", "click", "change"]) scene.scope.addEventListener(type, () => awaitingAnnouncement.add(scene));
  }

  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      const scene = scenes.find((candidate) => candidate.scope === entry.target);
      if (entry.isIntersecting) {
        visible.add(scene);
        scene.render();
      } else visible.delete(scene);
    }
  });
  for (const scene of scenes) observer.observe(scene.scope);

  // Moving figures can be paused (WCAG 2.2.2); readers who ask for reduced motion start paused.
  const playback = new Playback(document.querySelector("[data-playback]"), { startPlaying: !root.matchMedia("(prefers-reduced-motion: reduce)").matches });
  playback.on("pause", () => visible.forEach((scene) => scene.settle()));
  playback.on("step", () => visible.forEach((scene) => {
    scene.step();
    scene.settle();
    announce(scene);
  }));

  let lastFrame = null;
  function animate(now) {
    const dtMs = lastFrame === null ? 0 : Math.min(MAX_FRAME_MS, now - lastFrame);
    lastFrame = now;
    if (playback.playing && !document.hidden) for (const scene of visible) scene.advance(dtMs, playback.cycleMs);
    // A figure the reader changed while paused shows the end of its new cycle, not its start (WCAG 2.2.2).
    for (const scene of awaitingAnnouncement) {
      if (!playback.playing) scene.settle();
      announce(scene);
    }
    awaitingAnnouncement.clear();
    root.requestAnimationFrame(animate);
  }

  const redrawVisible = () => visible.forEach((scene) => scene.render());
  const themeChanged = () => {
    palette.invalidate();
    scenes.forEach((scene) => scene.render());
  };
  let resizePending = false;
  root.addEventListener("resize", () => {
    if (resizePending) return;
    resizePending = true;
    root.requestAnimationFrame(() => {
      resizePending = false;
      redrawVisible();
    });
  });
  root.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", themeChanged);
  new MutationObserver(themeChanged).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

  // Section navigator in the sticky bar, built from the headings, with the section in view marked as current.
  function buildNavigator() {
    const list = document.querySelector("[data-contents]");
    const current = document.querySelector("[data-current-section]");
    const sections = [...document.querySelectorAll("section.part")];
    const links = new Map(sections.map((section, index) => {
      const title = section.querySelector("h2").textContent.trim();
      const link = make("a", { href: `#${section.id}`, textContent: `${index + 1}. ${title}` });
      list.append(make("li", {}, [link]));
      return [section, { link, label: `${index + 1}. ${title}` }];
    }));
    const spy = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        for (const { link } of links.values()) link.removeAttribute("aria-current");
        const { link, label } = links.get(entry.target);
        link.setAttribute("aria-current", "location");
        current.textContent = label;
      }
    }, { rootMargin: "-30% 0px -60% 0px" });
    sections.forEach((section) => spy.observe(section));
    list.addEventListener("click", () => list.closest("details")?.removeAttribute("open"));
  }

  // Figures are numbered in page order; <a data-figure-ref="id"> links read "Figure N".
  function numberFigures() {
    const numbers = new Map();
    document.querySelectorAll("figure[id]").forEach((figure, index) => {
      numbers.set(figure.id, index + 1);
      const label = figure.querySelector("[data-figure-label]");
      if (label) label.textContent = t("figureLabel", { number: index + 1 });
    });
    for (const ref of document.querySelectorAll("[data-figure-ref]")) {
      const number = numbers.get(ref.dataset.figureRef);
      if (!number) throw new Error(`No figure with id "${ref.dataset.figureRef}"`);
      Object.assign(ref, { href: `#${ref.dataset.figureRef}`, textContent: t("figure", { number }) });
    }
  }

  function fillFacts() {
    for (const node of document.querySelectorAll("[data-fact]")) {
      if (!(node.dataset.fact in facts)) throw new Error(`No fact named "${node.dataset.fact}"`);
      node.textContent = facts[node.dataset.fact];
    }
  }

  const outcomes = new OutcomeIndex(data.outcomes);
  renderLedger(document.querySelector("[data-ledger]"), outcomes);
  renderInlineOutcomes(document, outcomes);
  renderPlantClaims(document, data.plantClaims);
  renderPredictions(document.querySelector("[data-predictions]"), data.predictions);
  renderStatistics(document, data.validation.statistics);
  fillFacts();
  numberFigures();
  buildNavigator();

  for (const scene of scenes) {
    scene.step();
    scene.settle();
    announce(scene);
  }
  // After the first readings, so that report names written by the scenes become links too.
  const archive = new ResultsArchive({ list: document.querySelector("[data-archive]"), dialog: document.querySelector("[data-viewer]"), catalogue: root.DPC_RESULTS_CATALOGUE ?? [] });
  archive.linkify(document);
  restorePlace();
  // Live only after the first descriptions are in place, so loading the page does not read them all out.
  for (const region of descriptions.values()) region.setAttribute("aria-live", "polite");
  root.requestAnimationFrame(animate);
})(globalThis);

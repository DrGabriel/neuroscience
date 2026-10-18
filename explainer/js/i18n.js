// Locales: each file in js/locales registers its messages (written by scripts) and content (the page's text).
// The reader's language is chosen from ?lang=, then a remembered choice, then the browser, then English (UK).
(function (root) {
  "use strict";

  const DEFAULT_LOCALE = "en-GB";
  const STORAGE_KEY = "dpc-explainer-locale";
  const registry = new Map();

  // A locale: { name, notice? (shown at the top, e.g. for an unreviewed translation), messages, content }.
  function registerLocale(code, locale) {
    registry.set(code, Object.freeze(locale));
  }

  function remembered() {
    try {
      return root.localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  }

  function remember(code) {
    try {
      root.localStorage.setItem(STORAGE_KEY, code);
    } catch {
      // Storage can be blocked (private window); the choice then lasts for this visit only.
    }
  }

  function chooseLocale() {
    const requested = typeof location === "undefined" ? null : new URLSearchParams(location.search).get("lang");
    const browser = typeof navigator === "undefined" ? [] : navigator.languages ?? [navigator.language];
    const candidates = [requested, remembered(), ...browser, ...browser.map((tag) => tag?.split("-")[0])];
    const match = (tag) => [...registry.keys()].find((code) => code === tag || code.split("-")[0] === tag);
    return candidates.map(match).find(Boolean) ?? DEFAULT_LOCALE;
  }

  class Translator {
    constructor(code) {
      this.code = code;
      this.locale = registry.get(code);
      this.fallback = registry.get(DEFAULT_LOCALE);
      this.formats = new Map();
      this.percentFormat = new Intl.NumberFormat(code, { style: "percent", maximumFractionDigits: 0 });
    }

    // The message for a key with {name} placeholders filled; a missing placeholder is an error.
    t(key, params = {}) {
      const template = this.locale.messages[key] ?? this.fallback.messages[key];
      if (template === undefined) throw new Error(`No message "${key}"`);
      return template.replace(/\{(\w+)\}/g, (_, name) => {
        if (!(name in params)) throw new Error(`Message "${key}" needs {${name}}`);
        return String(params[name]);
      });
    }

    content(key) {
      const html = this.locale.content[key] ?? this.fallback.content[key];
      if (html === undefined) throw new Error(`No page text "${key}"`);
      return html;
    }

    fixed(value, decimals) {
      if (value === null || value === undefined) return this.t("none");
      if (!this.formats.has(decimals)) this.formats.set(decimals, new Intl.NumberFormat(this.code, { minimumFractionDigits: decimals, maximumFractionDigits: decimals }));
      return this.formats.get(decimals).format(value);
    }

    percent(share) {
      return this.percentFormat.format(share);
    }

    count(value) {
      return this.fixed(value, 0);
    }
  }

  // Resolved lazily, after every locale file has registered.
  let active = null;
  const translator = () => (active ??= new Translator(chooseLocale()));

  root.DPC = Object.assign(root.DPC || {}, {
    DEFAULT_LOCALE,
    registry,
    registerLocale,
    remember,
    translator,
    t: (key, params) => translator().t(key, params),
    fixed: (value, decimals) => translator().fixed(value, decimals),
    percent: (share) => translator().percent(share),
    count: (value) => translator().count(value),
    // An organism's name in the reader's language, from its study key (celegans, drosophila, human).
    organismName: (key) => translator().t(`organism_${key}`),
  });
})(globalThis);

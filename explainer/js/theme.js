// Light, dark or system colour theme, remembered per browser where storage is available.
(function (root) {
  "use strict";

  const ThemeMode = Object.freeze({ SYSTEM: "SYSTEM", LIGHT: "LIGHT", DARK: "DARK" });
  const THEME_ATTRIBUTE = Object.freeze({ [ThemeMode.LIGHT]: "light", [ThemeMode.DARK]: "dark" });
  const STORAGE_KEY = "dpc-explainer-theme";

  function stored() {
    try {
      return ThemeMode[root.localStorage.getItem(STORAGE_KEY)] || ThemeMode.SYSTEM;
    } catch {
      return ThemeMode.SYSTEM;
    }
  }

  function remember(mode) {
    try {
      root.localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      // Storage can be blocked (private window); the choice then lasts for this visit only.
    }
  }

  function apply(mode) {
    const attribute = THEME_ATTRIBUTE[mode];
    if (attribute) document.documentElement.setAttribute("data-theme", attribute);
    else document.documentElement.removeAttribute("data-theme");
    for (const button of document.querySelectorAll("[data-theme-mode]")) {
      button.setAttribute("aria-pressed", String(button.dataset.themeMode === mode));
    }
  }

  for (const button of document.querySelectorAll("[data-theme-mode]")) {
    button.addEventListener("click", () => {
      const mode = ThemeMode[button.dataset.themeMode];
      remember(mode);
      apply(mode);
    });
  }
  apply(stored());

})(globalThis);

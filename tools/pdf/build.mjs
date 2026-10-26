// Builds a print-ready PDF of the paper from its Markdown source.
//
//   npm install            (once, in tools/pdf)
//   node build.mjs <paper.md> <out.pdf> [--draft "<banner and footer text>"]
//
// Maths ($...$, $$...$$) is typeset with KaTeX and Mermaid diagrams are rendered in the browser (Mermaid is loaded
// from a pinned CDN version at build time). The body text is set in Source Serif 4 from explainer/assets/fonts
// (SIL Open Font License), so the PDF embeds only openly licensed fonts. The page is printed by the Chrome
// installed on this machine, found by Playwright; the intermediate HTML goes to a temporary folder.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { marked } from "marked";
import katex from "katex";
import { chromium } from "playwright-core";

const MERMAID_URL = "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs";
const RENDER_TIMEOUT_MS = 60000;
const PAGE = Object.freeze({ format: "A4", margin: { top: "20mm", bottom: "20mm", left: "18mm", right: "18mm" } });
const HERE = path.dirname(fileURLToPath(import.meta.url));
const FONTS = path.resolve(HERE, "../../explainer/assets/fonts");
// Diagram labels are set in the body face; they must not inherit the monospace face of <pre>.
const DIAGRAM_FONT = '"Source Serif 4", serif';

function parseArguments(argv) {
  const [source, target, ...rest] = argv;
  if (!source || !target) {
    console.error('usage: node build.mjs <paper.md> <out.pdf> [--draft "<text>"]');
    process.exit(2);
  }
  const draftAt = rest.indexOf("--draft");
  // The language comes from the file name (paper.pt-BR.md); English (UK) otherwise.
  const lang = (source.match(/\.([a-z]{2}-[A-Z]{2})\.md$/) || [, "en-GB"])[1];
  return { source, target, lang, draft: draftAt >= 0 ? rest[draftAt + 1] : null };
}

// Formulas and code blocks are set aside before Markdown parsing so that their characters are not reinterpreted.
function renderBody(markdown) {
  const formulas = [];
  const protect = (tex, displayMode) => {
    formulas.push(katex.renderToString(tex, { displayMode, throwOnError: true }));
    return `@@MATH${formulas.length - 1}@@`;
  };
  const codeBlocks = [];
  const prepared = markdown
    .replace(/```[\s\S]*?```/g, (block) => `@@CODE${codeBlocks.push(block) - 1}@@`)
    .replace(/\$\$([\s\S]+?)\$\$/g, (_, tex) => protect(tex.trim(), true))
    .replace(/\$([^$\n]+?)\$/g, (_, tex) => protect(tex, false))
    .replace(/@@CODE(\d+)@@/g, (_, i) => codeBlocks[i]);
  const renderer = new marked.Renderer();
  const defaultCode = renderer.code.bind(renderer);
  renderer.code = (code, language) => (language === "mermaid" ? `<pre class="mermaid">${code}</pre>` : defaultCode(code, language));
  // Markdown keeps a figure's caption in the image's alt text, which the browser never prints, so print it beneath.
  renderer.image = (href, title, text) => `<figure><img src="${href}" alt="${text}"><figcaption>${text}</figcaption></figure>`;
  return marked.parse(prepared, { renderer, gfm: true }).replace(/@@MATH(\d+)@@/g, (_, i) => formulas[i]);
}

// Fonts are embedded as data URLs: Chrome refuses font files from another folder of a local page.
const FONT_FILES = Object.freeze([
  { family: "Source Serif 4", style: "normal", weight: "400 600", file: "SourceSerif4-roman-normal-latin.woff2" },
  { family: "Source Serif 4", style: "normal", weight: "400 600", file: "SourceSerif4-roman-normal-latin-ext.woff2" },
  { family: "Source Serif 4", style: "italic", weight: "400", file: "SourceSerif4-italic-latin.woff2" },
  { family: "Source Serif 4", style: "italic", weight: "400", file: "SourceSerif4-italic-latin-ext.woff2" },
  { family: "IBM Plex Mono", style: "normal", weight: "400", file: "IBMPlexMono-Regular.woff2" },
]);

function fontFaces() {
  return FONT_FILES.map(({ family, style, weight, file }) => {
    const data = fs.readFileSync(path.join(FONTS, file)).toString("base64");
    return `@font-face { font-family: "${family}"; font-style: ${style}; font-weight: ${weight}; src: url(data:font/woff2;base64,${data}) format("woff2"); }`;
  }).join("\n");
}

// baseHref: the folder of the Markdown source, so its relative image paths resolve from the temporary page.
function htmlPage({ markdown, draft, lang, baseHref }) {
  const require = createRequire(import.meta.url);
  const katexCssPath = require.resolve("katex/dist/katex.min.css");
  const katexCss = fs.readFileSync(katexCssPath, "utf8").replace(/url\(fonts\//g, `url(${pathToFileURL(path.dirname(katexCssPath)).href}/fonts/`);
  const title = (markdown.match(/^# (.+)$/m) || [, "Paper"])[1];
  const banner = draft ? `<p class="draft">${draft}</p>` : "";
  return `<!doctype html><html lang="${lang}"><head><meta charset="utf-8"><base href="${baseHref}"><title>${title}</title>
<style>${fontFaces()}</style><style>${katexCss}</style>
<style>
  body { font-family: "Source Serif 4", Georgia, serif; font-size: 10.5pt; line-height: 1.45; color: #111; background: #fff; }
  h1 { font-size: 19pt; line-height: 1.2; margin: 0 0 12pt; }
  h2 { font-size: 14pt; margin: 20pt 0 6pt; border-bottom: 1px solid #ccc; padding-bottom: 3pt; break-after: avoid; }
  h3 { font-size: 11.5pt; margin: 14pt 0 4pt; break-after: avoid; }
  /* Short words such as acronyms must not be split across lines. */
  p, li { text-align: justify; hyphens: auto; hyphenate-limit-chars: 7 3 3; }
  table { border-collapse: collapse; width: 100%; font-size: 8.8pt; margin: 8pt 0; }
  th, td { border: 1px solid #bbb; padding: 3pt 5pt; vertical-align: top; text-align: left; }
  th { background: #f0f0f0; }
  tr { break-inside: avoid; }
  a { color: #1a4f8b; text-decoration: none; word-break: break-word; }
  code, pre { font-family: "IBM Plex Mono", monospace; font-size: 9pt; }
  /* File names and identifiers must stay whole: a hyphen inside one would change it. */
  code { hyphens: none; }
  pre:not(.mermaid) { background: #f6f6f6; padding: 6pt; font-size: 8pt; white-space: pre-wrap; }
  pre.mermaid { font-family: ${DIAGRAM_FONT}; font-size: 10.5pt; white-space: normal; text-align: center; background: none; break-inside: avoid; }
  hr { border: 0; border-top: 1px solid #ddd; margin: 14pt 0; }
  figure { margin: 10pt 0; break-inside: avoid; text-align: center; }
  figure img { max-width: 100%; height: auto; }
  figcaption { font-size: 9pt; line-height: 1.35; text-align: left; margin-top: 4pt; }
  .draft { border: 1px solid #b42318; color: #b42318; padding: 6pt 8pt; font-weight: 600; }
</style></head><body>${banner}${renderBody(markdown)}
<script type="module">
  import mermaid from "${MERMAID_URL}";
  // Mermaid sizes each box from the font at the moment it runs, so the embedded font must be loaded first.
  await document.fonts.load(${JSON.stringify(`16px ${DIAGRAM_FONT}`)});
  await document.fonts.ready;
  mermaid.initialize({ startOnLoad: false, theme: "neutral", themeVariables: { fontFamily: ${JSON.stringify(DIAGRAM_FONT)} }, flowchart: { htmlLabels: true } });
  await mermaid.run({ querySelector: "pre.mermaid" });
  window.__rendered = true;
</script></body></html>`;
}

async function printPdf({ html, target, draft }) {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), "dpc-pdf-"));
  const page = path.join(folder, "paper.html");
  fs.writeFileSync(page, html);
  const browser = await chromium.launch({ channel: "chrome" });
  try {
    const tab = await browser.newPage();
    await tab.goto(pathToFileURL(page).href);
    await tab.waitForFunction("window.__rendered === true", null, { timeout: RENDER_TIMEOUT_MS });
    await tab.evaluate(() => document.fonts.ready);
    // A missing figure prints as a tiny broken-image icon that no text check notices, so refuse to build without it.
    const broken = await tab.evaluate(async () => {
      const images = [...document.images];
      await Promise.all(images.map((image) => (image.complete ? null : new Promise((done) => { image.onload = image.onerror = done; }))));
      return images.filter((image) => image.naturalWidth === 0).map((image) => image.getAttribute("src"));
    });
    if (broken.length) throw new Error(`images failed to load: ${broken.join(", ")}`);
    const footer = `<div style="font-family:Source Serif 4,serif;font-size:8px;width:100%;text-align:center;color:#666">${draft ? `${draft} · ` : ""}<span class="pageNumber"></span>/<span class="totalPages"></span></div>`;
    await tab.pdf({ path: target, ...PAGE, printBackground: true, displayHeaderFooter: true, headerTemplate: "<span></span>", footerTemplate: footer });
  } finally {
    await browser.close();
    fs.rmSync(folder, { recursive: true, force: true });
  }
}

const { source, target, lang, draft } = parseArguments(process.argv.slice(2));
const baseHref = pathToFileURL(path.dirname(path.resolve(source)) + path.sep).href;
await printPdf({ html: htmlPage({ markdown: fs.readFileSync(source, "utf8"), draft, lang, baseHref }), target, draft });
console.log(`wrote ${target}`);

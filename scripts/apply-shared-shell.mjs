// Applies the canonical RVAS shared shell chrome to every flat HTML page in site/.
import { existsSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');
const SITE = join(ROOT, 'site');
const REPO = 'https://github.com/microsoft/frontier-fabric-governance-rvas';

const pages = readdirSync(SITE).filter((name) => name.endsWith('.html')).sort();

function activeKey(name) {
  if (name === 'delivery.html') return 'delivery';
  if (name === 'builder.html') return 'builder';
  if (name === 'docs.html' || name.startsWith('doc-') || name.startsWith('page-')) return 'docs';
  return 'challenges';
}

function navHtml(active) {
  const item = (href, key, label) => `<a href="${href}"${active === key ? ' aria-current="page"' : ''}>${label}</a>`;
  return `  <header class="nav" role="banner">
    <div class="nav-inner">
      <a class="brand" href="index.html" aria-label="RVAS - Agentic Governance Blueprint for Fabric">
        <img src="assets/img/logo-full.png" alt="RVAP" class="rvap-nav-logo" height="32">
      </a>
      <nav class="nav-links" id="navLinks" aria-label="Primary">
        ${item('index.html', 'challenges', 'Challenges')}
        ${item('delivery.html', 'delivery', 'Delivery')}
        ${item('builder.html', 'builder', 'Builder')}
        ${item('docs.html', 'docs', 'Docs')}
        <a class="cta" href="challenge-00-setup.html">Start with Challenge 00 →</a>
        <a class="gh" href="${REPO}" target="_blank" rel="noopener">GitHub ↗</a>
      </nav>
      <div class="nav-actions">
        <button class="icon-btn nav-toggle" type="button" aria-label="Open navigation menu" aria-expanded="false" aria-controls="navLinks">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
        </button>
      </div>
    </div>
  </header>`;
}

const footerHtml = `  <footer class="footer" role="contentinfo">
    <div class="footer-inner">
      <a class="brand" href="index.html" aria-label="RVAS - Agentic Governance Blueprint for Fabric">
        <img src="assets/img/logo-full.png" alt="RVAP" class="rvap-nav-logo" height="28">
      </a>
      <p>// prove governance in hours · repeat it across every Fabric tenant</p>
      <nav class="footer-links" aria-label="Footer">
        <a href="index.html">Challenges</a>
        <a href="delivery.html">Delivery</a>
        <a href="builder.html">Builder</a>
        <a href="docs.html">Docs</a>
        <a href="${REPO}" target="_blank" rel="noopener">GitHub ↗</a>
      </nav>
    </div>
  </footer>`;

function injectHead(html) {
  html = html.replace(/\n\s*<link rel="stylesheet" href="assets\/css\/shell\.css"\s*\/?>/g, '');
  html = html.replace(/\n\s*<link rel="stylesheet" href="assets\/css\/brand\.css"\s*\/?>/g, '');
  const brandLink = existsSync(join(SITE, 'assets/css/brand.css')) ? '  <link rel="stylesheet" href="assets/css/brand.css">\n' : '';
  if (html.includes('<link rel="stylesheet" href="assets/styles.css">')) {
    return html.replace('<link rel="stylesheet" href="assets/styles.css">', `<link rel="stylesheet" href="assets/styles.css">\n${brandLink}  <link rel="stylesheet" href="assets/css/shell.css">`);
  }
  return html.replace('</head>', `${brandLink}  <link rel="stylesheet" href="assets/css/shell.css">\n</head>`);
}

function injectScript(html) {
  html = html.replace(/\n\s*<script src="assets\/js\/shell\.js"><\/script>/g, '');
  return html.replace('</body>', '  <script src="assets/js/shell.js"></script>\n</body>');
}

for (const page of pages) {
  const path = join(SITE, page);
  let html = readFileSync(path, 'utf8');
  html = injectHead(html);
  html = html.replace(/\n\s*<div class="orb orb-[123]"><\/div>/g, '');
  html = html.replace(/\s*<!--[^<]*TOP NAV[^<]*-->\s*/g, '\n');
  html = html.replace(/\s*<nav class="topnav">[\s\S]*?<\/nav>/, `\n${navHtml(activeKey(page))}\n`);
  html = html.replace(/\s*<!--[^<]*FOOTER[^<]*-->\s*/g, '\n');
  html = html.replace(/\s*<footer\b[\s\S]*?<\/footer>/, `\n${footerHtml}\n`);
  html = injectScript(html);
  writeFileSync(path, html);
}

console.log(`Applied shared shell to ${pages.length} pages.`);

// ════════════════════════════════════════════════════════════════════════
//  build-site.mjs — static generator for the Agentic Governance Blueprint
//  for Fabric GitHub Pages site.
//
//  Renders every human-readable Markdown file in the repo into a branded,
//  self-contained HTML page under ./site so a visitor never has to leave
//  GitHub Pages to read the content. Internal .md links are rewritten to the
//  generated on-site pages; links to code / schema / directories fall back to
//  GitHub (opened in a new tab). Challenge pages are enriched with metadata
//  from site/challenges.json (stage, duration, dependencies, tags, prev/next).
//
//  Usage:  node scripts/build-site.mjs
//  Output: site/challenge-*.html, site/doc-*.html, site/page-*.html, site/docs.html
//
//  The generated files carry an AUTO-GENERATED banner and should not be hand
//  edited — edit the source Markdown and re-run this script (CI does this on
//  every Pages deploy).
// ════════════════════════════════════════════════════════════════════════

import { marked } from 'marked';
import { readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');
const SITE = join(ROOT, 'site');

const REPO = 'https://github.com/microsoft/frontier-fabric-governance-rvas';
const BRANCH = 'main';

marked.setOptions({ gfm: true, breaks: false, mangle: false, headerIds: false });

// ── Helpers ─────────────────────────────────────────────────────────────
const escapeHtml = (s = '') =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
   .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

const slugify = (s = '') =>
  s.toLowerCase().replace(/&[a-z]+;/g, ' ').replace(/<[^>]+>/g, '')
   .replace(/[^\w\s-]/g, '').trim().replace(/\s+/g, '-').replace(/-+/g, '-');

// Strip inline Markdown to plain text (for descriptions / meta tags).
const stripMd = (s = '') =>
  s.replace(/!\[[^\]]*\]\([^)]*\)/g, '')
   .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
   .replace(/[*_`>#]/g, '')
   .replace(/\s+/g, ' ')
   .trim();

const truncate = (s, n = 172) => (s.length > n ? s.slice(0, n - 1).trimEnd() + '…' : s);

// ── Collect all content Markdown files (repo-root-relative paths) ─────────
const SKIP_DIRS = new Set(['.git', '.venv', 'node_modules', '.agents', 'site', '.github', 'dist', '__pycache__']);

// Internal operational records that should NOT be published to the public site.
// - deployment-handoff.md is a live-infrastructure deployment log (subscription,
//   tenant, managed-identity, and resource identifiers) — not customer-facing
//   RVAS delivery content.
// - validation-report.md is a generated CI artifact (written by scripts/validate.py)
//   that just echoes a workspace manifest name and a PASS/FAIL — not reference
//   content, and it needlessly surfaces a workspace name.
// Keep any local copies in the repo tree, but do not amplify them on Pages.
const EXCLUDE_FILES = new Set([
  'docs/deployment-handoff.md',
  'validation-report.md',
]);

function walk(dir, rel = '') {
  const out = [];
  for (const name of readdirSync(dir)) {
    const abs = join(dir, name);
    const relPath = rel ? `${rel}/${name}` : name;
    const st = statSync(abs);
    if (st.isDirectory()) {
      if (SKIP_DIRS.has(name) || name === '.venv') continue;
      out.push(...walk(abs, relPath));
    } else if (name.endsWith('.md')) {
      if (relPath.includes('/.venv/') || relPath.includes('/node_modules/')) continue;
      out.push(relPath);
    }
  }
  return out;
}

const allMd = walk(ROOT).filter((p) => !p.startsWith('.github/') && !EXCLUDE_FILES.has(p)).sort();

// ── Slug (output filename) for a given repo-relative Markdown path ─────────
function slugForMd(relPath) {
  const m = relPath.match(/^challenges\/([^/]+)\/challenge\.md$/);
  if (m) return `challenge-${m[1]}.html`;
  const d = relPath.match(/^docs\/(.+)\.md$/);
  if (d) return `doc-${d[1].replace(/\//g, '-').toLowerCase()}.html`;
  return `page-${relPath.replace(/\.md$/, '').replace(/[^A-Za-z0-9]+/g, '-').toLowerCase()}.html`;
}

const slugMap = new Map(allMd.map((p) => [p, slugForMd(p)]));

// ── Path resolution + link rewriting ──────────────────────────────────────
function resolveRepoPath(fromDir, rel) {
  const parts = fromDir ? fromDir.split('/') : [];
  for (const seg of rel.split('/')) {
    if (seg === '' || seg === '.') continue;
    if (seg === '..') parts.pop();
    else parts.push(seg);
  }
  return parts.join('/');
}

function resolveHref(href, fromDir) {
  const raw = href.trim();
  if (!raw) return { href, external: false };
  if (raw.startsWith('#')) return { href: raw, external: false };
  if (/^[a-z][a-z0-9+.-]*:/i.test(raw) || raw.startsWith('//')) return { href: raw, external: true };

  const hashIdx = raw.indexOf('#');
  const anchor = hashIdx >= 0 ? raw.slice(hashIdx) : '';
  const path = hashIdx >= 0 ? raw.slice(0, hashIdx) : raw;
  const isDir = path.endsWith('/');
  const resolved = resolveRepoPath(fromDir, path);

  if (slugMap.has(resolved)) return { href: slugMap.get(resolved) + anchor, external: false };

  const hasExt = /\.[A-Za-z0-9]+$/.test(resolved);
  const kind = isDir || !hasExt ? 'tree' : 'blob';
  return { href: `${REPO}/${kind}/${BRANCH}/${resolved}${anchor}`, external: true };
}

function rewriteAnchors(html, fromDir) {
  return html.replace(/<a\s+href="([^"]*)"([^>]*)>/g, (m, href, rest) => {
    const res = resolveHref(href, fromDir);
    let attrs = rest;
    if (res.external) {
      if (!/\btarget=/.test(attrs)) attrs += ' target="_blank"';
      if (!/\brel=/.test(attrs)) attrs += ' rel="noopener"';
    }
    return `<a href="${escapeHtml(res.href)}"${attrs}>`;
  });
}

// ── Heading IDs + table-of-contents extraction (h2/h3) ────────────────────
function processHeadings(html) {
  const toc = [];
  const used = new Map();
  const out = html.replace(/<h([234])>([\s\S]*?)<\/h\1>/g, (m, lvl, inner) => {
    const text = inner.replace(/<[^>]+>/g, '').trim();
    let id = slugify(text) || 'section';
    if (used.has(id)) { const n = used.get(id) + 1; used.set(id, n); id = `${id}-${n}`; }
    else used.set(id, 0);
    if (lvl === '2' || lvl === '3') toc.push({ level: Number(lvl), id, text });
    return `<h${lvl} id="${id}">${inner}</h${lvl}>`;
  });
  return { html: out, toc };
}

// Flag <ul>/<li> that contain task-list checkboxes so CSS can drop the bullet.
function markTaskLists(html) {
  return html.replace(/<li>(<input [^>]*type="checkbox"[^>]*>)/g, '<li class="task">$1');
}

// ── Extract title (first H1) and body ─────────────────────────────────────
function titleFromPath(relPath) {
  const base = relPath.split('/').pop().replace(/\.md$/i, '');
  const special = { SECURITY: 'Security', README: 'Overview', LICENSE: 'License' };
  if (special[base]) return special[base];
  return base
    .replace(/[-_]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function extractTitle(md, relPath = '') {
  const lines = md.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const m = lines[i].match(/^#\s+(.+?)\s*#*\s*$/);
    if (m) { lines.splice(i, 1); return { title: m[1].trim(), body: lines.join('\n') }; }
  }
  return { title: titleFromPath(relPath), body: md };
}

function firstParagraph(body) {
  // Drop HTML comments (e.g. the SECURITY.md policy-block markers) up front.
  const cleaned = body.replace(/<!--[\s\S]*?-->/g, '');
  const lines = cleaned.split(/\r?\n/);
  const parts = [];
  let inFence = false;
  const joined = () => stripMd(parts.join(' ')).replace(/\s+/g, ' ').trim();
  for (const ln of lines) {
    const t = ln.trim();
    if (/^(```|~~~)/.test(t)) { inFence = !inFence; continue; }
    if (inFence) continue;                        // skip code / mermaid interiors
    if (t.startsWith('<')) continue;              // raw HTML lines
    if (/^(-{3,}|\*{3,}|\|)/.test(t)) {           // hr / table row
      if (joined().length >= 60) break; else continue;
    }
    if (/^#/.test(t)) {                            // heading
      if (joined().length >= 60) break; else continue;
    }
    if (!t) {                                      // blank line
      if (joined().length >= 60) break; else continue;
    }
    // Prose line, blockquote, or list item — accumulate its text.
    const text = t.replace(/^>\s?/, '').replace(/^([-*+]|\d+\.)\s+/, '');
    if (text) parts.push(text);
    if (joined().length >= 150) break;
  }
  return truncate(joined());
}

// ── Shared chrome ─────────────────────────────────────────────────────────
function navHtml(active) {
  const item = (href, key, label, cls = '') => {
    const classes = [cls, active === key ? 'active' : ''].filter(Boolean).join(' ');
    return `<a href="${href}"${classes ? ` class="${classes}"` : ''}>${label}</a>`;
  };
  return `
  <nav class="topnav">
    <div class="topnav-inner">
      <a class="brand" href="index.html" aria-label="RVAP — Real Value Acceleration Program (home)"><img class="brand-logo" src="assets/img/logo-full.png" alt="RVAP — Real Value Acceleration Program"></a>
      <div class="nav-links">
        ${item('index.html', 'challenges', 'Challenges')}
        ${item('delivery.html', 'delivery', 'Delivery')}
        ${item('builder.html', 'builder', 'Builder')}
        ${item('docs.html', 'docs', 'Docs')}
        ${item(REPO, 'gh', 'GitHub ↗', 'gh')}
      </div>
    </div>
  </nav>`;
}

const FOOTER = `
  <footer>
    <div class="footer-inner">
      <div>
        <div class="footer-brand">Agentic Governance <em>·</em> Blueprint for Fabric</div>
        <div class="footer-sub">// prove governance in hours · repeat it across every Fabric tenant</div>
      </div>
      <a class="footer-cta" href="docs.html">↗ Browse all docs</a>
    </div>
  </footer>`;

const TOC_SCRIPT = `  <script>
    (function () {
      var links = Array.prototype.slice.call(document.querySelectorAll('.doc-toc a'));
      if (!links.length || !('IntersectionObserver' in window)) return;
      var byId = {};
      links.forEach(function (a) { byId[a.getAttribute('href').slice(1)] = a; });
      var heads = links.map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); }).filter(Boolean);
      var current = null;
      var obs = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) { if (e.isIntersecting) current = e.target.id; });
        links.forEach(function (a) { a.classList.remove('active'); });
        if (current && byId[current]) byId[current].classList.add('active');
      }, { rootMargin: '0px 0px -70% 0px', threshold: 0 });
      heads.forEach(function (h) { obs.observe(h); });
    })();
  </script>`;

function shell({ title, description, active, hero, body, toc }) {
  const tocHtml = toc && toc.length
    ? `<aside class="doc-toc"><div class="doc-toc-title">On this page</div><nav>${
        toc.map((h) => `<a class="lvl-${h.level}" href="#${h.id}">${escapeHtml(h.text)}</a>`).join('')
      }</nav></aside>`
    : '';
  const layoutClass = tocHtml ? 'doc-layout' : 'doc-layout doc-layout--notoc';
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(title)}</title>
  <meta name="description" content="${escapeHtml(description)}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="icon" type="image/png" href="assets/img/logo-mark-white.png">
  <link rel="stylesheet" href="assets/styles.css">
</head>
<body>
  <!-- ════════════════════════════════════════════════════════════════
       AUTO-GENERATED by scripts/build-site.mjs — do not edit by hand.
       Edit the source Markdown and re-run:  npm run build:site
  ═══════════════════════════════════════════════════════════════════ -->
  <div class="orb orb-1"></div>
  <div class="orb orb-2"></div>
  <div class="orb orb-3"></div>
${navHtml(active)}
${hero}
  <main>
    <div class="container">
      <div class="${layoutClass}">
        <article class="prose">
${body}
        </article>
        ${tocHtml}
      </div>
    </div>
  </main>
${FOOTER}
${toc && toc.length ? TOC_SCRIPT : ''}
</body>
</html>
`;
}

// ── Render one Markdown file to HTML body + TOC ───────────────────────────
function renderMarkdown(relPath, body) {
  const fromDir = relPath.includes('/') ? relPath.slice(0, relPath.lastIndexOf('/')) : '';
  let html = marked.parse(body);
  html = rewriteAnchors(html, fromDir);
  html = markTaskLists(html);
  const { html: withIds, toc } = processHeadings(html);
  return { html: withIds, toc };
}

// ── Load challenge metadata ───────────────────────────────────────────────
const challengeData = JSON.parse(readFileSync(join(SITE, 'challenges.json'), 'utf8'));
const stageLabel = Object.fromEntries((challengeData.stages || []).map((s) => [s.id, s.label]));
const challenges = challengeData.challenges || [];
const challengeBySlug = new Map(challenges.map((c) => [slugForMd(c.path), c]));

// ── Category for non-challenge pages ──────────────────────────────────────
function categoryOf(relPath) {
  if (relPath.startsWith('docs/')) return { key: 'guides', label: 'Guides & reference', cat: 'core' };
  if (relPath.startsWith('agent/')) return { key: 'agents', label: 'Agents', cat: 'intelligent' };
  if (relPath.startsWith('infra/')) return { key: 'infra', label: 'Infrastructure', cat: 'governed' };
  return { key: 'project', label: 'Project', cat: 'foundation' };
}

// ── Hero builders ─────────────────────────────────────────────────────────
function challengeHero(ch, title, relPath) {
  const idx = challenges.indexOf(ch);
  const prev = idx > 0 ? challenges[idx - 1] : null;
  const next = idx < challenges.length - 1 ? challenges[idx + 1] : null;
  const num = /^\d+$/.test(ch.id) ? `Challenge ${ch.id}` : 'Capstone';
  const tags = (ch.tags || []).map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join('');
  const navLink = (c, dir) => {
    if (!c) return '<span></span>';
    const n = /^\d+$/.test(c.id) ? c.id : 'Cap';
    const arrow = dir === 'prev' ? '←' : '→';
    const label = dir === 'prev' ? `${arrow} ${n} · ${escapeHtml(c.name)}` : `${n} · ${escapeHtml(c.name)} ${arrow}`;
    return `<a href="${slugForMd(c.path)}">${label}</a>`;
  };
  return `
  <header class="container hero hero-compact" data-stage="${ch.stage}">
    <div class="eyebrow"><span class="eyebrow-line"></span>${num} · ${escapeHtml(stageLabel[ch.stage] || ch.stage)}</div>
    <h1 class="doc-h1">${escapeHtml(title)}</h1>
    <p class="doc-tagline">${escapeHtml(ch.tagline || '')}</p>
    <div class="doc-meta">
      <span class="dm">⏱ <b>${escapeHtml(ch.duration || '')}</b></span>
      <span class="dm">depends <b>${escapeHtml(ch.depends || '—')}</b></span>
    </div>
    ${tags ? `<div class="doc-tags">${tags}</div>` : ''}
    <div class="hero-actions">
      <a class="btn btn-primary" href="builder.html#sel=${encodeURIComponent(ch.id)}">＋ Add to a delivery</a>
      <a class="btn btn-ghost" href="${REPO}/blob/${BRANCH}/${relPath}" target="_blank" rel="noopener">View source ↗</a>
    </div>
    <div class="doc-nav">${navLink(prev, 'prev')}${navLink(next, 'next')}</div>
  </header>`;
}

function docHero(relPath, title, description) {
  const cat = categoryOf(relPath);
  return `
  <header class="container hero hero-compact" data-stage="${cat.cat}">
    <div class="eyebrow"><span class="eyebrow-line"></span>${escapeHtml(cat.label)}</div>
    <h1 class="doc-h1">${escapeHtml(title)}</h1>
    ${description ? `<p class="doc-tagline">${escapeHtml(description)}</p>` : ''}
    <div class="hero-actions">
      <a class="btn btn-ghost" href="${REPO}/blob/${BRANCH}/${relPath}" target="_blank" rel="noopener">View source ↗</a>
      <a class="btn btn-ghost" href="docs.html">All docs</a>
    </div>
  </header>`;
}

// ── Generate every content page ───────────────────────────────────────────
const docIndex = []; // for docs.html
let count = 0;

for (const relPath of allMd) {
  const md = readFileSync(join(ROOT, relPath), 'utf8');
  const { title, body } = extractTitle(md, relPath);
  const { html, toc } = renderMarkdown(relPath, body);
  const description = firstParagraph(body);
  const slug = slugMap.get(relPath);
  const ch = challengeBySlug.get(slug);

  let hero, active, pageTitle;
  if (ch) {
    hero = challengeHero(ch, title, relPath);
    active = 'challenges';
    pageTitle = `${title} · Agentic Governance Blueprint for Fabric`;
  } else {
    hero = docHero(relPath, title, description);
    active = 'docs';
    pageTitle = `${title} · Agentic Governance Blueprint for Fabric`;
    const cat = categoryOf(relPath);
    docIndex.push({ slug, title, description, cat });
  }

  const pageDesc = description || `${title} — part of the Agentic Governance Blueprint for Fabric.`;
  writeFileSync(join(SITE, slug), shell({ title: pageTitle, description: pageDesc, active, hero, body: html, toc }));
  count++;
}

// ── docs.html — index of every non-challenge content page ─────────────────
const catOrder = ['project', 'guides', 'agents', 'infra'];
const catMeta = {
  project: { label: 'Project', blurb: 'Overview, license, and security posture.', cat: 'foundation' },
  guides: { label: 'Guides & reference', blurb: 'Setup, identity, delivery, and the governance rulebook.', cat: 'core' },
  agents: { label: 'Agents', blurb: 'Copilot Studio, M365, and declarative-agent runbooks.', cat: 'intelligent' },
  infra: { label: 'Infrastructure', blurb: 'Terraform / Bicep that backs the control plane.', cat: 'governed' },
};

function docCard(entry) {
  return `
        <a class="card" data-cat="${entry.cat.cat}" href="${entry.slug}">
          <div class="card-head">
            <span class="badge">${escapeHtml(entry.cat.label)}</span>
            <span class="card-arrow">→</span>
          </div>
          <h3 class="card-title">${escapeHtml(entry.title)}</h3>
          <p class="card-desc">${escapeHtml(entry.description || '')}</p>
        </a>`;
}

let docsSections = '';
for (const key of catOrder) {
  const items = docIndex.filter((d) => d.cat.key === key).sort((a, b) => a.title.localeCompare(b.title));
  if (!items.length) continue;
  const meta = catMeta[key];
  docsSections += `
      <div class="section-label" data-stage="${meta.cat}"><span class="sl-dot"></span>${meta.label}<span class="sl-blurb">— ${meta.blurb}</span></div>
      <div class="grid">${items.map(docCard).join('')}</div>`;
}

const docsHero = `
  <header class="container hero">
    <div class="page-intro">
      <div class="eyebrow"><span class="eyebrow-line"></span>Documentation</div>
      <h2>Everything, on one site.</h2>
      <p>
        Every guide, runbook, and reference in the blueprint — rendered here so you never
        have to leave the site to read it. Looking for the hands-on labs?
        The <a href="index.html">ten challenges live on the home page</a>, and you can
        <a href="builder.html">compose a custom delivery</a> from them.
      </p>
    </div>
  </header>`;

const docsPage = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Docs · Agentic Governance Blueprint for Fabric</title>
  <meta name="description" content="Browse every guide, runbook, and reference for the Agentic Governance Blueprint for Fabric — setup, identity, delivery, agents, and infrastructure — without leaving the site.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="icon" type="image/png" href="assets/img/logo-mark-white.png">
  <link rel="stylesheet" href="assets/styles.css">
</head>
<body>
  <!-- AUTO-GENERATED by scripts/build-site.mjs — do not edit by hand. -->
  <div class="orb orb-1"></div>
  <div class="orb orb-2"></div>
  <div class="orb orb-3"></div>
${navHtml('docs')}
${docsHero}
  <main>
    <div class="container">
${docsSections}
    </div>
  </main>
${FOOTER}
</body>
</html>
`;
writeFileSync(join(SITE, 'docs.html'), docsPage);

console.log(`✓ Generated ${count} content pages + docs.html`);
console.log(`  challenges: ${challenges.length} · docs index entries: ${docIndex.length}`);

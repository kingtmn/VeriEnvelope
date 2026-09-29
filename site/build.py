#!/usr/bin/env python3
"""Build the public, read-only VeriEnvelope site from sealed result files."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import shutil
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
DIST = SITE / "dist"
CONFIG = SITE / "site.json"
BASE_URL = "https://verienvelope.pages.dev"
REPOSITORY_URL = "https://github.com/kingtmn/VeriEnvelope"
OG_IMAGE = f"{BASE_URL}/assets/og-card.png"

SITE_SCHEMA = {
    "@context": "https://schema.org",
    "@graph": [
        {
            "@type": "WebSite",
            "@id": f"{BASE_URL}/#website",
            "name": "VeriEnvelope",
            "url": f"{BASE_URL}/",
            "description": "Evidence-bound verification of specific AI tool claims under declared conditions.",
        },
        {
            "@type": "SoftwareSourceCode",
            "@id": f"{BASE_URL}/#source",
            "name": "VeriEnvelope",
            "codeRepository": REPOSITORY_URL,
            "license": "https://opensource.org/license/mit",
            "programmingLanguage": "Python",
            "description": "An open evidence system for verifying specific Tool claims under declared conditions.",
        },
    ],
}
SITE_SCHEMA_JSON = json.dumps(SITE_SCHEMA, ensure_ascii=False, separators=(",", ":"))


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def canonical_url(path: str) -> str:
    return f"{BASE_URL}{path}"


def page(
    title: str,
    body: str,
    *,
    description: str,
    path: str,
    og_type: str = "website",
) -> str:
    full_title = "VeriEnvelope" if title == "Home" else f"{title} · VeriEnvelope"
    canonical = canonical_url(path)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{esc(description)}">
  <meta name="theme-color" content="#f3f0e8">
  <link rel="canonical" href="{esc(canonical)}">
  <meta property="og:type" content="{esc(og_type)}">
  <meta property="og:site_name" content="VeriEnvelope">
  <meta property="og:title" content="{esc(full_title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{esc(canonical)}">
  <meta property="og:image" content="{esc(OG_IMAGE)}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="VeriEnvelope — It passed. What exactly passed?">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc(full_title)}">
  <meta name="twitter:description" content="{esc(description)}">
  <meta name="twitter:image" content="{esc(OG_IMAGE)}">
  <title>{esc(full_title)}</title>
  <link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/assets/styles.css">
  <script type="application/ld+json">{SITE_SCHEMA_JSON}</script>
</head>
<body>
  <a class="skip-link" href="#content">Skip to content</a>
  <header class="site-header">
    <nav class="nav shell" aria-label="Primary navigation">
      <a class="brand" href="/" aria-label="VeriEnvelope home"><span class="brand-mark" aria-hidden="true">VE</span><span>VeriEnvelope</span></a>
      <div class="nav-links">
        <a href="/cases/">Cases</a>
        <a href="/methodology/">Methodology</a>
        <a href="/about/">About</a>
        <a href="/request/">Request verification</a>
        <a class="nav-source" href="{REPOSITORY_URL}">View source ↗</a>
      </div>
    </nav>
  </header>
  <main id="content">{body}</main>
  <footer class="site-footer">
    <div class="shell footer-grid">
      <div><a class="brand footer-brand" href="/">VeriEnvelope</a><p>Specific claims. Reproducible evidence. Explicit boundaries.</p></div>
      <div><p>Public presentation v0.2 · Tool claim scope v0.1</p><p>Feedback: <a href="mailto:kingtmn1@gmail.com">kingtmn1@gmail.com</a></p></div>
    </div>
  </footer>
</body>
</html>
"""


def status_badge(status: str) -> str:
    css = status.replace("_", "-")
    label = status.replace("_", " ")
    return f'<span class="status {esc(css)}"><span aria-hidden="true"></span>{esc(label)}</span>'


def write_page(relative: str, content: str) -> None:
    target = DIST / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def load_cases() -> tuple[dict, list[dict]]:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    loaded = []
    for entry in config["cases"]:
        result_path = ROOT / entry["result_path"]
        result = json.loads(result_path.read_text(encoding="utf-8"))
        capabilities = {item["capability_id"]: item for item in result["capabilities"]}
        primary = capabilities[entry["primary_capability"]]
        if primary["status"] != entry["expected_status"]:
            raise ValueError(
                f"{entry['slug']}: expected {entry['expected_status']}, got {primary['status']}"
            )
        loaded.append({**entry, "result": result, "primary": primary})
    return config, loaded


def case_card(case: dict) -> str:
    result = case["result"]
    return f"""
<article class="case-card">
  <div class="case-card-top"><span class="surface">{esc(case['surface'])}</span>{status_badge(case['primary']['status'])}</div>
  <p class="case-object">{esc(case['name'])}</p>
  <h3>{esc(case['claim_label'])}</h3>
  <dl class="case-meta">
    <div><dt>Claim</dt><dd><code>{esc(case['primary_capability'])}</code></dd></div>
    <div><dt>Method</dt><dd><code>{esc(result['method_id'])} {esc(result['method_version'])}</code></dd></div>
  </dl>
  <a class="source-link" href="/cases/{esc(case['slug'])}/"><span>View evidence trail</span><span aria-hidden="true">→</span></a>
</article>"""


def list_items(values: list[str]) -> str:
    if not values:
        return '<p class="quiet">None empirically established for this run.</p>'
    return "<ul>" + "".join(f"<li>{esc(value)}</li>" for value in values) + "</ul>"


def build_case(case: dict, repository_url: str) -> str:
    result = case["result"]
    primary = case["primary"]
    envelope = primary["envelope"]
    history = result.get("history", [])
    history_html = list_items(
        [
            f"{event['timestamp']} — {event['event_type']}: {event['reason']}"
            for event in history
        ]
    )
    evidence_url = f"{repository_url}/blob/main/{case['result_path']}"
    method_url = f"{repository_url}/blob/main/methods/{result['method_id']}/method.yaml"
    body = f"""
<div class="shell page-shell">
  <section class="case-hero">
    <p class="eyebrow">{esc(case['surface'])}</p>
    <p class="case-kicker">{esc(case['name'])}</p>
    <h1>{esc(case['claim_label'])}</h1>
    <div class="case-result-line">{status_badge(primary['status'])}<span>One claim. One declared envelope.</span></div>
  </section>
  <div class="record-grid">
    <section class="record-section wide">
      <p class="record-number">01 / Claim</p>
      <h2>What was tested</h2>
      <p class="record-lede">{esc(primary['testable_statement'])}</p>
      <p class="quiet">This is a claim about one fixed component version under declared conditions—not the product as a whole.</p>
    </section>
    <section class="record-section">
      <p class="record-number">02 / Result</p>
      <h2>What the record says</h2>
      <p>{status_badge(primary['status'])}</p>
      <p>{esc(primary['notes'])}</p>
      <p>Admission: <code>{esc(result['admission'])}</code></p>
    </section>
    <section class="record-section">
      <p class="record-number">Identity</p>
      <h2>What was fixed</h2>
      <p><code>{esc(result['component_id'])}</code> · version <code>{esc(result['component_version'])}</code></p>
      <p>Commit: <code>{esc(result['component_commit'])}</code></p>
      <p>Run: <code>{esc(result['run_id'])}</code></p>
    </section>
    <section class="record-section">
      <p class="record-number">03 / Method</p>
      <h2>What decided it</h2>
      <p><code>{esc(result['method_id'])} {esc(result['method_version'])}</code></p>
      <p>Decision rule: <code>{esc(result['rule_id'])}</code></p>
      <a class="source-link inline" href="{esc(method_url)}"><span>Open frozen Method</span><span aria-hidden="true">↗</span></a>
    </section>
    <section class="record-section">
      <p class="record-number">04 / Evidence</p>
      <h2>What was observed</h2>
      <p>Observation: <code>{esc(result['observation'])}</code></p>
      <p>Outcome: <code>{esc(result['outcome_class'])}</code></p>
      <a class="source-link inline" href="{esc(evidence_url)}"><span>Open sealed result</span><span aria-hidden="true">↗</span></a>
    </section>
    <section class="record-section wide" id="envelope">
      <p class="record-number">05 / Envelope</p>
      <h2>Where the conclusion stops</h2>
      <div class="envelope-grid">
        <div><h3>Tested conditions</h3>{list_items(envelope['tested_conditions'])}</div>
        <div><h3>Untested areas</h3>{list_items(envelope['untested_areas'])}</div>
        <div><h3>Known limits in this run</h3>{list_items(envelope['known_limits'])}</div>
        <div><h3>Revalidation triggers</h3>{list_items(envelope['revalidation_triggers'])}</div>
      </div>
    </section>
    <section class="record-section wide">
      <p class="record-number">History</p>
      <h2>The record is append-only</h2>
      {history_html}
      <p class="quiet">Historical evidence is retained. A later result does not erase an earlier run.</p>
    </section>
  </div>
</div>"""
    return page(
        f"{case['name']}: {case['claim_label']}",
        body,
        description=(
            f"Evidence trail for the {case['name']} claim '{case['claim_label']}': "
            f"{primary['status']} under {result['method_id']} {result['method_version']}."
        ),
        path=f"/cases/{case['slug']}/",
        og_type="article",
    )


def method_flow() -> str:
    steps = [
        ("01", "Claim", "The narrow behavior stated before execution."),
        ("02", "Method", "The frozen rule that says what counts."),
        ("03", "Evidence", "The observation preserved without a rewrite."),
        ("04", "Envelope", "The conditions and limits attached to the result."),
    ]
    return "".join(
        f'<div class="flow-step"><span>{number}</span><h3>{name}</h3><p>{description}</p></div>'
        for number, name, description in steps
    )


def build() -> None:
    config, cases = load_cases()
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    (DIST / "assets").mkdir(parents=True)
    for asset in ("styles.css", "favicon.svg", "og-card.svg", "og-card.png"):
        shutil.copyfile(SITE / "assets" / asset, DIST / "assets" / asset)

    cards = "".join(case_card(case) for case in cases)
    playwright = next(case for case in cases if case["slug"] == "playwright-navigate")
    playwright_result = playwright["result"]
    playwright_evidence = f"{config['repository_url']}/blob/main/{playwright['result_path']}"
    playwright_method = f"{config['repository_url']}/blob/main/methods/{playwright_result['method_id']}/method.yaml"
    old_filesystem = f"{config['repository_url']}/blob/main/evidence/mcp.server-filesystem/0.6.3/run-605485ecb4594a0d9fabd0002ca19899/result.json"
    new_filesystem = f"{config['repository_url']}/blob/main/evidence/mcp.server-filesystem/0.6.3/run-a030ab0bf2ee40faaf0b22cf003147ce/result.json"
    home = f"""
<section class="hero-section">
  <div class="shell hero">
    <div class="hero-copy">
      <p class="eyebrow">Evidence-bound verification for AI tools</p>
      <h1><span>“It passed.”</span> What exactly passed?</h1>
      <p class="hero-proposition">Verify specific claims, not products.</p>
      <p class="lede">VeriEnvelope tests whether one Tool claim is supported under declared conditions—and keeps the Method, Evidence, and boundary attached to the result.</p>
      <div class="hero-actions">
        <a class="button primary" href="/cases/playwright-navigate/">See a real case <span aria-hidden="true">→</span></a>
        <a class="button" href="#how-it-works">How it works</a>
      </div>
    </div>
    <aside class="hero-note" aria-label="VeriEnvelope principle">
      <p class="note-label">Principle / 001</p>
      <p>A result without its envelope is incomplete.</p>
      <span>Claim · Method · Evidence · Boundary</span>
    </aside>
  </div>
</section>
<section class="story-section story-dark">
  <div class="shell story-grid">
    <div>
      <p class="eyebrow">A real record / Playwright MCP</p>
      <h2>One claim was not demonstrated.</h2>
      <p class="story-lede"><code>browser_navigate</code> did not demonstrate the preregistered claim under the frozen method and runtime envelope.</p>
      <div class="clarifier"><strong>This does not mean Playwright is broken.</strong><span>It means this specific claim was not demonstrated under this frozen method and runtime envelope. The cause remains unclassified.</span></div>
    </div>
    <div class="finding-card">
      <p class="finding-label">Claim record</p>
      <dl>
        <div><dt>Tool</dt><dd>Playwright MCP</dd></div>
        <div><dt>Claim</dt><dd><code>browser_navigate</code> reaches the fixed local page</dd></div>
        <div><dt>Status</dt><dd>{status_badge('not_demonstrated')}</dd></div>
        <div><dt>Method</dt><dd><code>{esc(playwright_result['method_id'])} {esc(playwright_result['method_version'])}</code></dd></div>
      </dl>
      <div class="record-links"><a href="{esc(playwright_evidence)}">Evidence ↗</a><a href="{esc(playwright_method)}">Method ↗</a><a href="/cases/playwright-navigate/#envelope">Envelope →</a></div>
    </div>
  </div>
</section>
<section class="method-section" id="how-it-works">
  <div class="shell">
    <div class="section-intro">
      <p class="eyebrow">The record, end to end</p>
      <h2>Every conclusion travels with its boundary.</h2>
      <p>MCP verification and AI tool evaluation become more reproducible when the claim, decision rule, evidence, and tested conditions remain inspectable as one chain.</p>
    </div>
    <div class="method-flow">{method_flow()}</div>
    <p class="method-caption">The Viewer does not rerun tools or recalculate verdicts. GitHub remains the source of truth.</p>
  </div>
</section>
<section class="history-section">
  <div class="shell history-grid">
    <div class="history-heading">
      <p class="eyebrow">A second story / Filesystem MCP</p>
      <h2>Sometimes the tool isn’t wrong. The test is.</h2>
      <p class="history-pull">Evidence stayed.<br>The conclusion changed.</p>
    </div>
    <div class="timeline">
      <div><span>01</span><h3>The observation matched</h3><p><code>read_text_file</code> returned the preregistered fixture bytes. That raw observation remains valid.</p></div>
      <div><span>02</span><h3>The rule chain failed review</h3><p>Method 0.1.0 omitted the capability status, while the Runner supplied <code>demonstrated</code>. That status was not authorized by the frozen Method.</p></div>
      <div><span>03</span><h3>The history was preserved</h3><p>The old evidence package was not edited or deleted. Its formal conclusion stopped counting as current.</p></div>
      <div><span>04</span><h3>The test was repaired and rerun</h3><p>Method 0.2.0 made the rule explicit. After a Runner fix, new authorization, and a new measurement, the current claim was demonstrated.</p></div>
      <div class="timeline-links"><a href="{esc(old_filesystem)}">Inspect the historical record ↗</a><a href="{esc(new_filesystem)}">Inspect the current record ↗</a></div>
    </div>
  </div>
</section>
<section class="cases-section">
  <div class="shell">
    <div class="section-head">
      <div><p class="eyebrow">Current Tool scope</p><h2>Five claims. Five evidence trails.</h2></div>
      <p>No product scores. No leaderboard. Each card names the surface, frozen Method version, claim status, and record.</p>
    </div>
    <div class="case-grid">{cards}</div>
  </div>
</section>
<section class="final-cta">
  <div class="shell final-cta-inner">
    <div><p class="eyebrow">Open to challenge</p><h2>Challenge a claim.<br>Point to the evidence.</h2></div>
    <div><p>Found a counterexample, a narrower wording, or a Tool claim worth testing? Start with an exact component and an observable behavior.</p><div class="hero-actions"><a class="button light" href="{REPOSITORY_URL}/issues/new">Open a GitHub issue ↗</a><a class="text-link" href="/request/">Read the request policy →</a></div></div>
  </div>
</section>"""
    write_page(
        "index.html",
        page(
            "Home",
            home,
            description="VeriEnvelope verifies specific AI Tool and MCP claims with reproducible evidence, frozen methods, and explicit boundaries—not product scores.",
            path="/",
        ),
    )

    cases_body = f"""
<div class="shell page-shell">
  <section class="case-hero listing-hero">
    <p class="eyebrow">Current v0.1 Tool scope</p>
    <h1>Five claims.<br>Five evidence trails.</h1>
    <p class="claim">Each record links one testable statement to its frozen Method, sealed evidence, status, envelope, and history. This is not a benchmark or leaderboard.</p>
  </section>
  <div class="case-grid">{cards}</div>
</div>"""
    write_page(
        "cases/index.html",
        page(
            "Tool verification cases",
            cases_body,
            description="Five evidence-based AI Tool and MCP verification cases, each with a claim, frozen method, sealed result, and explicit envelope.",
            path="/cases/",
        ),
    )

    for case in cases:
        write_page(f"cases/{case['slug']}/index.html", build_case(case, config["repository_url"]))

    methodology = f"""
<div class="shell page-shell">
<article class="prose">
  <p class="eyebrow">Methodology</p>
  <h1>Measure a claim. Keep its boundary.</h1>
  <p class="lede">VeriEnvelope is an evidence-based evaluation system for reproducible AI Tool and Model Context Protocol testing. It separates specification, implementation, observation, interpretation, and admission.</p>
  <div class="method-flow compact">{method_flow()}</div>
  <h2>Before execution</h2>
  <p>The component identity, testable statement, expected observation, decision rules, execution boundary, and revalidation triggers are written down before a measurement is authorized.</p>
  <h2>After execution</h2>
  <p>Raw observation remains distinct from interpretation and diagnosis. A result can be <code>demonstrated</code>, <code>not_demonstrated</code>, <code>insufficient</code>, <code>unknown</code>, or <code>out_of_envelope</code>.</p>
  <h2>What admission means</h2>
  <p><code>admitted</code> means the record may enter the current registry within its stated envelope. It does not certify the component, establish production readiness, or decide fitness for use.</p>
  <h2>History is part of the evidence</h2>
  <p>When a Method or Runner defect is found, the old package stays. A repaired Method requires a new authorization and a new measurement. The Filesystem case preserves exactly that sequence.</p>
  <p><a class="button primary" href="{REPOSITORY_URL}/blob/main/methodology/core_method.md">Read the full Methodology ↗</a></p>
</article>
</div>"""
    write_page(
        "methodology/index.html",
        page(
            "Methodology",
            methodology,
            description="How VeriEnvelope performs reproducible AI Tool and MCP testing by separating claims, Methods, Evidence, decisions, and applicability envelopes.",
            path="/methodology/",
        ),
    )

    about = f"""
<div class="shell page-shell">
<article class="prose">
  <p class="eyebrow">About</p>
  <h1>Results are easy to share. Conditions are easy to lose.</h1>
  <p class="lede">VeriEnvelope started from a simple frustration: software results were often easier to publish than the conditions that made those results true. So we built the record backwards—from the claim, to the method, to the evidence, and finally to the boundary.</p>
  <h2>What it is</h2>
  <p>An open evidence system for specific Tool claims: public Methods, a reference implementation, sealed evidence packages, and history that does not erase inconvenient runs. GitHub is the source of truth; this site is a Viewer and entry point.</p>
  <h2>What it is not</h2>
  <p>It is not a certification body, security guarantee, product ranking, reliability score, general AI benchmark, or claim that a component is suitable for your use case.</p>
  <h2>Current boundary</h2>
  <p>v0.1 covers Tool claims only. Skill, Agent, Multi-Agent, and Workflow verification remain outside the active scope and beyond GATE 2.</p>
  <p><a class="button primary" href="{REPOSITORY_URL}">Inspect the source and evidence ↗</a></p>
</article>
</div>"""
    write_page(
        "about/index.html",
        page(
            "About",
            about,
            description="Why VeriEnvelope keeps specific AI Tool claims attached to their Methods, Evidence, tested conditions, and limits.",
            path="/about/",
        ),
    )

    request = f"""
<div class="shell page-shell">
<article class="prose request-page">
  <p class="eyebrow">Request verification</p>
  <h1>Propose a claim, not a verdict.</h1>
  <p class="lede">A request can come from a maintainer, a vendor, a user nomination, or VeriEnvelope’s own research selection. Its source does not change the Method or buy a result.</p>
  <div class="request-sources"><span>Maintainer</span><span>Vendor</span><span>User nomination</span><span>Research selection</span></div>
  <h2>Include</h2>
  <ul>
    <li>The exact component, version, and source repository.</li>
    <li>One behavior that can be stated as a narrow, observable claim.</li>
    <li>Any required network access, credentials, files, or runtime constraints.</li>
    <li>Why the claim matters and what must remain outside the conclusion.</li>
  </ul>
  <h2>What influence can—and cannot—buy</h2>
  <p>Request source, audience demand, or future payment may affect selection, priority, scope, or report format. They cannot purchase <code>demonstrated</code>, widen an Envelope, hide a negative result, or change the frozen decision rule.</p>
  <p>No submission backend or payment flow exists today. Use a public GitHub Issue or email for sensitive preliminary context.</p>
  <div class="hero-actions"><a class="button primary" href="{REPOSITORY_URL}/issues/new">Open a GitHub issue ↗</a><a class="button" href="mailto:kingtmn1@gmail.com">Email VeriEnvelope</a></div>
</article>
</div>"""
    write_page(
        "request/index.html",
        page(
            "Request verification",
            request,
            description="Propose a specific AI Tool or MCP verification claim. Requests may affect selection, never the evidence-bound result.",
            path="/request/",
        ),
    )

    not_found = """
<div class="shell page-shell">
<article class="prose error-page">
  <p class="eyebrow">404 / Boundary reached</p>
  <h1>This page is outside the envelope.</h1>
  <p class="lede">The requested record was not found. The evidence trail continues from the public index.</p>
  <p><a class="button primary" href="/">Return home</a></p>
</article>
</div>"""
    write_page(
        "404.html",
        page(
            "Page not found",
            not_found,
            description="The requested VeriEnvelope page was not found.",
            path="/404.html",
        ),
    )

    paths = ["/", "/cases/", "/methodology/", "/about/", "/request/"] + [
        f"/cases/{case['slug']}/" for case in cases
    ]
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    today = date.today().isoformat()
    for path in paths:
        sitemap.append(f"  <url><loc>{canonical_url(path)}</loc><lastmod>{today}</lastmod></url>")
    sitemap.append("</urlset>")
    write_page("sitemap.xml", "\n".join(sitemap) + "\n")
    write_page("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n")

    schema_hash = hashlib.sha256(SITE_SCHEMA_JSON.encode("utf-8")).digest()
    schema_csp = base64.b64encode(schema_hash).decode("ascii")
    write_page(
        "_headers",
        "/*\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  Permissions-Policy: camera=(), microphone=(), geolocation=()\n"
        f"  Content-Security-Policy: default-src 'self'; script-src 'sha256-{schema_csp}'; style-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'\n",
    )


if __name__ == "__main__":
    build()

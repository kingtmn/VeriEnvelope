#!/usr/bin/env python3
"""Build the public, read-only VeriEnvelope site from sealed result files."""

from __future__ import annotations

import html
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
DIST = SITE / "dist"
CONFIG = SITE / "site.json"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def page(title: str, body: str, *, description: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{esc(description)}">
  <title>{esc(title)} · VeriEnvelope</title>
  <link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/assets/styles.css">
</head>
<body>
  <header class="site-header">
    <nav class="nav shell" aria-label="Primary navigation">
      <a class="brand" href="/">VeriEnvelope</a>
      <div class="nav-links">
        <a href="/cases/">Cases</a>
        <a href="/methodology/">Methodology</a>
        <a href="/about/">About</a>
        <a href="/request/">Request verification</a>
        <a href="https://github.com/kingtmn/VeriEnvelope">GitHub</a>
      </div>
    </nav>
  </header>
  <main class="shell">{body}</main>
  <footer class="site-footer">
    <div class="shell">
      <span>VeriEnvelope v0.1 · Evidence-bound Tool Verification</span>
      <span>Feedback: <a href="mailto:kingtmn1@gmail.com">kingtmn1@gmail.com</a></span>
    </div>
  </footer>
</body>
</html>
"""


def status_badge(status: str) -> str:
    css = status.replace("_", "-")
    return f'<span class="status {esc(css)}">{esc(status)}</span>'


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
  <span class="surface">{esc(case['surface'])}</span>
  <h3>{esc(case['name'])}</h3>
  {status_badge(case['primary']['status'])}
  <p class="claim">{esc(case['claim_label'])}</p>
  <p class="meta"><code>{esc(result['method_id'])} {esc(result['method_version'])}</code></p>
  <a class="source-link" href="/cases/{esc(case['slug'])}/">Read claim, evidence, and envelope →</a>
</article>"""


def list_items(values: list[str]) -> str:
    if not values:
        return '<p class="quiet">None recorded for this run.</p>'
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
<section class="case-hero">
  <p class="eyebrow">{esc(case['surface'])}</p>
  <h1>{esc(case['name'])}</h1>
  <p class="claim">{esc(case['claim_label'])}</p>
  {status_badge(primary['status'])}
</section>
<div class="record-grid">
  <section class="record-section wide">
    <h2>Claim</h2>
    <p>{esc(primary['testable_statement'])}</p>
    <p class="quiet">This is a claim about one fixed component version under declared conditions—not the product as a whole.</p>
  </section>
  <section class="record-section">
    <h2>Result</h2>
    <p>{status_badge(primary['status'])}</p>
    <p>{esc(primary['notes'])}</p>
    <p>Admission: <code>{esc(result['admission'])}</code></p>
  </section>
  <section class="record-section">
    <h2>Identity</h2>
    <p><code>{esc(result['component_id'])}</code> · version <code>{esc(result['component_version'])}</code></p>
    <p>Commit: <code>{esc(result['component_commit'])}</code></p>
    <p>Run: <code>{esc(result['run_id'])}</code></p>
  </section>
  <section class="record-section">
    <h2>Method</h2>
    <p><code>{esc(result['method_id'])} {esc(result['method_version'])}</code></p>
    <p>Decision rule: <code>{esc(result['rule_id'])}</code></p>
    <a class="source-link" href="{esc(method_url)}">Open frozen Method on GitHub →</a>
  </section>
  <section class="record-section">
    <h2>Evidence</h2>
    <p>Observation: <code>{esc(result['observation'])}</code></p>
    <p>Outcome: <code>{esc(result['outcome_class'])}</code></p>
    <a class="source-link" href="{esc(evidence_url)}">Open sealed result on GitHub →</a>
  </section>
  <section class="record-section wide">
    <h2>Envelope</h2>
    <h3>Tested conditions</h3>
    {list_items(envelope['tested_conditions'])}
    <h3>Untested areas</h3>
    {list_items(envelope['untested_areas'])}
    <h3>Known limits recorded by this run</h3>
    {list_items(envelope['known_limits'])}
    <h3>Revalidation triggers</h3>
    {list_items(envelope['revalidation_triggers'])}
  </section>
  <section class="record-section wide">
    <h2>History</h2>
    {history_html}
    <p class="quiet">Historical evidence is retained. A later result does not erase an earlier run.</p>
  </section>
</div>"""
    return page(
        case["name"],
        body,
        description=f"VeriEnvelope result for {case['claim_label']}.",
    )


def build() -> None:
    config, cases = load_cases()
    DIST.mkdir(parents=True, exist_ok=True)
    (DIST / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SITE / "assets" / "styles.css", DIST / "assets" / "styles.css")
    shutil.copyfile(SITE / "assets" / "favicon.svg", DIST / "assets" / "favicon.svg")

    cards = "".join(case_card(case) for case in cases)
    home = f"""
<section class="hero">
  <p class="eyebrow">Evidence-bound Tool Verification</p>
  <h1>A result without its envelope is incomplete.</h1>
  <p class="lede">VeriEnvelope verifies specific claims under declared conditions. It keeps the Method, raw Evidence, decision rule, limits, and history attached to every result.</p>
  <div class="hero-actions">
    <a class="button primary" href="/cases/">Explore five cases</a>
    <a class="button" href="/methodology/">Read the methodology</a>
  </div>
</section>
<section class="principle" aria-label="How to read a result">
  <div><strong>Claim</strong><span>One narrow statement, fixed before execution.</span></div>
  <div><strong>Evidence</strong><span>What was actually observed and how it was classified.</span></div>
  <div><strong>Envelope</strong><span>Where the conclusion stops, and what requires revalidation.</span></div>
</section>
<section>
  <div class="section-head">
    <div><p class="eyebrow">Current v0.1 cases</p><h2>Five claims, not five scores.</h2></div>
    <p>A <code>not_demonstrated</code> result is retained beside demonstrated results. It is not converted into a product verdict.</p>
  </div>
  <div class="case-grid">{cards}</div>
</section>
<section class="feedback">
  <p class="eyebrow">Feedback</p>
  <h2>Challenge a claim. Point to the evidence.</h2>
  <p>Corrections, counterexamples, and narrow verification requests are welcome at <a href="mailto:kingtmn1@gmail.com">kingtmn1@gmail.com</a>.</p>
</section>"""
    write_page("index.html", page("Home", home, description="Evidence-bound verification of specific Tool claims under declared conditions."))

    cases_body = f"""
<section class="case-hero">
  <p class="eyebrow">v0.1 registry view</p>
  <h1>Cases</h1>
  <p class="claim">Each card links a narrow claim to its Method, sealed result, applicability envelope, and history. This is not a leaderboard.</p>
</section>
<div class="case-grid">{cards}</div>"""
    write_page("cases/index.html", page("Cases", cases_body, description="Five VeriEnvelope v0.1 Tool verification cases."))

    for case in cases:
        write_page(f"cases/{case['slug']}/index.html", build_case(case, config["repository_url"]))

    methodology = """
<article class="prose">
  <p class="eyebrow">Methodology</p>
  <h1>Measure a claim. Keep its boundary.</h1>
  <p class="lede">VeriEnvelope separates the specification, the reference runner, the observation, and the decision. A convenient implementation is never allowed to silently become the rule.</p>
  <h2>Before execution</h2>
  <p>The component identity, testable statement, expected observation, decision rules, execution boundary, and revalidation triggers are written down before a measurement is authorized.</p>
  <h2>After execution</h2>
  <p>Raw observation remains distinct from interpretation and diagnosis. A result can be <code>demonstrated</code>, <code>not_demonstrated</code>, <code>insufficient</code>, <code>unknown</code>, or <code>out_of_envelope</code>.</p>
  <h2>What admission means</h2>
  <p><code>admitted</code> means the record may enter the current registry within its stated envelope. It does not certify the component, establish production readiness, or decide fitness for use.</p>
  <h2>History is part of the evidence</h2>
  <p>When a Method or runner defect is found, the old package stays. A repaired Method requires a new authorization and a new measurement. The Filesystem case in v0.1 preserves exactly that sequence.</p>
  <p><a class="button primary" href="https://github.com/kingtmn/VeriEnvelope/blob/main/methodology/core_method.md">Read the full Methodology on GitHub</a></p>
</article>"""
    write_page("methodology/index.html", page("Methodology", methodology, description="How VeriEnvelope separates claims, observations, decisions, and applicability envelopes."))

    about = """
<article class="prose">
  <p class="eyebrow">About</p>
  <h1>Verification without a product score.</h1>
  <p class="lede">VeriEnvelope is an experimental, open evidence system for narrow Tool claims. GitHub is the source of truth; this site is a reader.</p>
  <h2>What it is</h2>
  <p>A public Method, reference implementation, sealed evidence packages, and a history that does not erase inconvenient runs.</p>
  <h2>What it is not</h2>
  <p>It is not a certification body, security guarantee, product ranking, reliability score, or claim that a component is suitable for your use case.</p>
  <h2>Current boundary</h2>
  <p>v0.1 covers Tool-level claims only. Skill, Agent, Multi-Agent, and Workflow verification remain outside the active scope.</p>
  <p><a class="button primary" href="https://github.com/kingtmn/VeriEnvelope">Inspect the source and evidence</a></p>
</article>"""
    write_page("about/index.html", page("About", about, description="What VeriEnvelope is and is not."))

    request = """
<article class="prose">
  <p class="eyebrow">Request verification</p>
  <h1>Propose a claim, not a verdict.</h1>
  <p class="lede">Maintainers, vendors, and users may propose a component and a specific behavior to verify. The source of a request does not change the Method or the result.</p>
  <h2>Include</h2>
  <ul>
    <li>The exact component, version, and source repository.</li>
    <li>One behavior that can be stated as a narrow, observable claim.</li>
    <li>Any required network access, credentials, files, or runtime constraints.</li>
    <li>Why the claim matters and what must remain outside the conclusion.</li>
  </ul>
  <h2>Boundary</h2>
  <p>A request may affect selection, priority, scope, or report format. It cannot purchase <code>demonstrated</code>, a wider envelope, or the removal of a negative result.</p>
  <p><a class="button primary" href="https://github.com/kingtmn/VeriEnvelope/issues/new">Open a GitHub issue</a></p>
</article>"""
    write_page("request/index.html", page("Request verification", request, description="How to propose a narrow Tool verification claim."))

    not_found = """
<article class="prose">
  <p class="eyebrow">404</p>
  <h1>This page is outside the envelope.</h1>
  <p>The requested page was not found.</p>
  <p><a class="button primary" href="/">Return home</a></p>
</article>"""
    write_page("404.html", page("Not found", not_found, description="Page not found."))
    write_page("robots.txt", "User-agent: *\nAllow: /\n")
    write_page(
        "_headers",
        "/*\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  Permissions-Policy: camera=(), microphone=(), geolocation=()\n"
        "  Content-Security-Policy: default-src 'self'; style-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'\n",
    )


if __name__ == "__main__":
    build()

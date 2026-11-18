# VeriEnvelope

> **“It passed.” What exactly passed?**

VeriEnvelope is an open evidence system for verifying specific Tool claims under declared conditions.

**Verify specific claims, not products.** A result without its envelope is incomplete.

```text
Claim → Method → Evidence → Envelope
```

### What happened when Playwright MCP tried to open a local page?

We asked Playwright MCP 0.0.82 to navigate to a fixed local page. The frozen test looked for its title, `ve-pilot-2`. The recorded tool response included this line:

> Error: async initializeServer: Target page, context or browser has been closed

The status for that claim was **`not_demonstrated`** under Method `VE-METHOD-MCP-002` 0.4.0. This does **not** mean Playwright is broken. The cause remains unclassified.

[Inspect the transcript](https://verienvelope.pages.dev/cases/playwright-navigate/#transcript) · [Read the tested conditions](https://verienvelope.pages.dev/cases/playwright-navigate/#envelope) · [Get the Markdown citation](https://verienvelope.pages.dev/cases/playwright-navigate/#cite)

**Keep this evidence library handy.** Star the repository to find the records again when a tool claim comes up in a review. Each [published case](https://verienvelope.pages.dev/cases/) includes a citation you can paste into an issue or pull request, with the component version, claim status, frozen Method, and a link to the exact evidence snapshot.

### Check the Playwright record on your machine

With Git and Python 3.11+ installed, run:

```bash
git clone --depth 1 https://github.com/kingtmn/VeriEnvelope.git
cd VeriEnvelope
python3 site/check_records.py playwright-navigate
```

Expected output:

```text
playwright-navigate: Method, seal and listed artifact hashes match
```

The check compares the local file bytes to the published digests. The seal is unsigned. To check all five packages, omit the case name. For scripts, the [JSON index](https://verienvelope.pages.dev/cases/index.json) provides run IDs, claim statuses, and source links.

## Why this exists

Software results are often easier to publish than the conditions that made those results true. `PASS`, `FAIL`, `verified`, and `safe` travel quickly; the component identity, decision rule, runtime, permissions, untested areas, and revalidation triggers often do not.

VeriEnvelope exists to bind those parts back together. It asks:

1. What exact behavior was claimed?
2. What was fixed before execution?
3. What was actually observed?
4. Which frozen rule authorized the result?
5. Where does that conclusion stop?
6. If the conclusion changes, does the history remain visible?

## Sometimes the tool isn’t wrong. The test is.

The Filesystem MCP case preserves a real correction chain.

Its first `read_text_file` observation matched the preregistered fixture bytes. But an independent review found that Method 0.1.0 did not specify the formal capability status while the Runner supplied `demonstrated`. The raw observation remained valid; the formal status was not authorized by the frozen Method.

The old evidence package stayed unchanged. Method 0.2.0 made the decision rule explicit, the Runner was repaired, a new run was authorized, and the claim was measured again. Only then did the current `demonstrated` conclusion return.

> **Evidence stayed. The conclusion changed.**

- [Historical record](evidence/mcp.server-filesystem/0.6.3/run-605485ecb4594a0d9fabd0002ca19899/result.json)
- [Current record](evidence/mcp.server-filesystem/0.6.3/run-a030ab0bf2ee40faaf0b22cf003147ce/result.json)
- [Revalidation note](docs/research/pilot3_rule_revalidation.md)

## Methodology

VeriEnvelope separates the normative Method from its implementation and from any downstream registry decision.

| Layer | Location | Responsibility |
| --- | --- | --- |
| Method Specification | `methods/` | Public rules that can be reproduced without this repository's Runner. |
| Reference Implementation | `runner/` | One implementation of a Method; never the sole normative authority. |
| Verification Result | One run's `result.json` | The conclusion from one measurement. Third-party results do not become official automatically. |

The evidence chain is:

```text
Measurement Object
  → Method
  → Raw Observation
  → Interpretation / Decision Rule
  → Claim Result
  → Claim Envelope
  → Admission Rule
  → Registry Decision
```

Observation is not itself a verdict. Runner behavior is not Method authority. Admission is not certification.

Start with [the core methodology](methodology/core_method.md), [the responsibility model](docs/architecture/responsibility_model.md), and [the glossary](docs/glossary.md).

## Architecture

- `methods/` — frozen, public Method specifications and version history
- `runner/` — one reference implementation of those Methods
- `evidence/` — sealed run packages and raw observations
- `schemas/` — machine-readable record contracts
- `registry/` — identities, authorizations, history, and registry state
- `site/` — read-only public Viewer generated from five current sealed results
- `viewer/` — local single-record renderer

GitHub is the source of truth. The website is a Viewer and entry point; it does not rerun tools or recalculate conclusions.

## Current boundary

- v0.1 covers Tool claims only. Skill, Agent, Multi-Agent, and Workflow verification remain outside the active scope; GATE 2 is locked.
- The data model can represent `tool` and `mcp_server` objects.
- The reference `run_case` path rejects third-party component verification. Unknown code is not installed on the host.
- A result with `admission=admitted` is not publication, certification, security assurance, or production readiness.
- The local and public Viewers render existing records without judging them again.

The governing constraints are in [CONSTITUTION.md](CONSTITUTION.md). Method lineage is recorded in [METHODOLOGY_LINEAGE.md](METHODOLOGY_LINEAGE.md). Current status is in [CURRENT_STATE.md](CURRENT_STATE.md).

## Run locally

Requires Python 3.11+.

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```

Run the measurement-pipeline self-audit and render a local record:

```bash
.venv/bin/python -m verienvelope run \
  --method methods/VE-METHOD-001 \
  --case methods/VE-METHOD-001/cases/echo_match.json \
  --out evidence/_scratch

.venv/bin/python -m verienvelope view \
  --result evidence/_scratch/fixture.method001/0.0.0/*/result.json \
  --out viewer/preview/index.html
```

`evidence/_scratch/` and `viewer/preview/` are gitignored. Exit code 0 means only that this observation matched; it does not admit a component.

## Build the public site

`site/` generates a static, read-only presentation from five current sealed results.

Public URL: <https://verienvelope.pages.dev/>

```bash
python3 site/build.py
python3 site/verify_public.py
```

Cloudflare Pages configuration is documented in [site/README.md](site/README.md). The publication evidence and hygiene checks are recorded in [docs/release/PUBLICATION_AUDIT_V0_1.md](docs/release/PUBLICATION_AUDIT_V0_1.md) and [docs/release/PUBLICATION_HYGIENE_V0_1.md](docs/release/PUBLICATION_HYGIENE_V0_1.md).

## Explicitly out of scope

User accounts, comments, rankings, payments, ads, self-service verdict submission, bulk scoring, Agent or Multi-Agent standards, enterprise certification, a universal global standard, and model-generated adjudication. VeriEnvelope does not claim to be a “world first” or an authority that certifies products.

## Working-name notice

**VeriEnvelope** remains a working project name. The repository does not claim that a complete trademark or domain clearance has been performed. Formal release planning should still include appropriate USPTO, WIPO, EUIPO, CNIPA, GitHub, domain, company, and product-name checks.

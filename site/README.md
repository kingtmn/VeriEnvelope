# Public site

The public site is a read-only view over five sealed v0.1 result files. It does not rerun components or recalculate a verdict.

Build and verify with Python 3.11 or newer:

```bash
python3 site/build.py
python3 site/verify_public.py
```

The generated directory is `site/dist/` and remains untracked.

Published site: <https://verienvelope.pages.dev/>

Cloudflare Pages configuration:

```text
Production branch: main
Build command: python3 site/build.py && python3 site/verify_public.py
Build output directory: site/dist
Root directory: /
```

GitHub remains the source of truth. `site/site.json` only selects a sealed result and its primary capability for presentation; the status, Method, evidence metadata, Envelope, and History are read from the result file at build time.

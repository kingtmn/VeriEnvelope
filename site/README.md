# Public site

The public presentation is v0.2. It remains a read-only view over five sealed v0.1 Tool results and does not rerun components or recalculate a verdict.

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

The generated site includes unique page titles and descriptions, canonical URLs, Open Graph and Twitter metadata, JSON-LD, `sitemap.xml`, `robots.txt`, a 1200 × 630 social preview, responsive layouts, keyboard focus styles, and a custom 404 page. `verify_public.py` checks these presentation requirements in addition to the existing result, hygiene, and link constraints.

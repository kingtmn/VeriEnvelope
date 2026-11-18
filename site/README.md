# Public site

The v0.3 evidence viewer reads five sealed v0.1 Tool results. Its index is available as HTML and JSON. Case pages display an escaped excerpt of the recorded primary response and link to the complete log at the public source revision.

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

GitHub remains the source of truth. `site/site.json` selects each primary capability and pins its public source revision, Method hash, and seal hash. The build checks the recorded artifacts before rendering. Run `python3 site/check_records.py` to perform just the byte checks offline.

The generated site includes unique page titles and descriptions, canonical URLs, Open Graph and Twitter metadata, JSON-LD, `sitemap.xml`, `robots.txt`, a 1200 × 630 social preview, responsive layouts, keyboard focus styles, and a custom 404 page. `verify_public.py` checks these presentation requirements in addition to the existing result, hygiene, and link constraints.

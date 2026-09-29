#!/usr/bin/env python3
"""Fail a public build when the release view or repository hygiene drifts."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
DIST = SITE / "dist"
EXPECTED_CASE_COUNT = 5
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}"),
    "OpenAI-style key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "Cloudflare token assignment": re.compile(r"CLOUDFLARE_API_TOKEN\s*[:=]\s*[A-Za-z0-9_-]{16,}"),
}
PERSONAL_PATH = re.compile("/" + r"Users/(?!<user>)[^/\s`\"']+")
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
HTML_LINK = re.compile(r"(?:href|src)=\"([^\"]+)\"")


def tracked_files() -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    )
    return [ROOT / item.decode() for item in completed.stdout.split(b"\0") if item]


def check_hygiene(errors: list[str]) -> None:
    for path in tracked_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        relative = path.relative_to(ROOT)
        if PERSONAL_PATH.search(text):
            errors.append(f"personal absolute path in {relative}")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"{label} shape in {relative}")


def check_markdown_links(errors: list[str]) -> None:
    for path in ROOT.rglob("*.md"):
        if any(part in {".git", ".venv", ".pytest_cache"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip().split("#", 1)[0]
            if not target or "://" in target or target.startswith(("mailto:", "#")):
                continue
            if not (path.parent / target).resolve().exists():
                errors.append(f"broken Markdown link in {path.relative_to(ROOT)}: {target}")


def check_cases(errors: list[str]) -> None:
    config = json.loads((SITE / "site.json").read_text(encoding="utf-8"))
    cases = config.get("cases", [])
    if len(cases) != EXPECTED_CASE_COUNT:
        errors.append(f"expected {EXPECTED_CASE_COUNT} cases, found {len(cases)}")
    slugs: set[str] = set()
    runs: set[str] = set()
    for case in cases:
        if case["slug"] in slugs:
            errors.append(f"duplicate case slug: {case['slug']}")
        slugs.add(case["slug"])
        result_path = ROOT / case["result_path"]
        if not result_path.is_file():
            errors.append(f"missing result: {case['result_path']}")
            continue
        result = json.loads(result_path.read_text(encoding="utf-8"))
        run_id = result.get("run_id")
        if run_id in runs:
            errors.append(f"duplicate run id: {run_id}")
        runs.add(run_id)
        capabilities = {
            item["capability_id"]: item for item in result.get("capabilities", [])
        }
        primary = capabilities.get(case["primary_capability"])
        if primary is None:
            errors.append(f"{case['slug']}: missing primary capability")
        elif primary.get("status") != case["expected_status"]:
            errors.append(
                f"{case['slug']}: expected {case['expected_status']}, got {primary.get('status')}"
            )
        method = ROOT / "methods" / result["method_id"] / "method.yaml"
        if not method.is_file():
            errors.append(f"{case['slug']}: missing current Method")
        else:
            method_text = method.read_text(encoding="utf-8")
            version = re.search(r'^version:\s*["\']?([^"\'\s]+)', method_text, re.MULTILINE)
            if not version or version.group(1) != result["method_version"]:
                errors.append(f"{case['slug']}: Method version does not match result")


def check_generated_links(errors: list[str]) -> None:
    if not DIST.is_dir():
        errors.append("site/dist is missing; run site/build.py first")
        return
    for path in DIST.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        for target in HTML_LINK.findall(text):
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith(("mailto:", "#")):
                continue
            clean = parsed.path
            if clean.startswith("/"):
                candidate = DIST / clean.lstrip("/")
            else:
                candidate = path.parent / clean
            if clean.endswith("/"):
                candidate = candidate / "index.html"
            elif not candidate.suffix:
                candidate = candidate / "index.html"
            if not candidate.exists():
                errors.append(f"broken generated link in {path.relative_to(DIST)}: {target}")
    home = (DIST / "index.html").read_text(encoding="utf-8")
    if 'mailto:hongtang1@proton.me' not in home:
        errors.append("homepage feedback email is missing")


def main() -> int:
    errors: list[str] = []
    check_hygiene(errors)
    check_markdown_links(errors)
    check_cases(errors)
    check_generated_links(errors)
    if errors:
        for error in sorted(set(errors)):
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Public verification passed: 5 cases, repository hygiene, source links, and generated links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

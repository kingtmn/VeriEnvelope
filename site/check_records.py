"""Verify the published record bytes locally. No tool execution or network access."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runner"))
from verienvelope.evidence_integrity import check_evidence_integrity


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_record(entry, root=ROOT):
    package = (root / entry["result_path"]).parent
    seal_path = package / "seal.json"
    if digest(seal_path) != entry["seal_sha256"]:
        raise ValueError("seal.json differs from the publication snapshot")
    seal = json.loads(seal_path.read_bytes())
    errors = check_evidence_integrity(package, {"artifacts": seal["files"]})
    if errors:
        raise ValueError(", ".join(errors))
    manifest = json.loads((package / "manifest.json").read_bytes())
    errors = check_evidence_integrity(package, manifest)
    if errors:
        raise ValueError(", ".join(errors))
    method = root / "methods" / manifest["method_id"] / "method.yaml"
    if digest(method) != entry["method_sha256"]:
        raise ValueError("Method differs from the publication snapshot")


def main():
    entries = json.loads((ROOT / "site/site.json").read_bytes())["cases"]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", nargs="?", choices=[entry["slug"] for entry in entries])
    args = parser.parse_args()
    for entry in entries:
        if args.case and entry["slug"] != args.case:
            continue
        try:
            check_record(entry)
        except (OSError, ValueError, KeyError) as exc:
            parser.exit(1, f"{entry['slug']}: {exc}\n")
        print(f"{entry['slug']}: Method, seal and listed artifact hashes match")


if __name__ == "__main__":
    main()

"""SHA-256 seal for a finished evidence package.

The manifest lists raw inputs and logs hashed before result.json and notes.md
exist. This seal is written after those files, and it does not hash itself.
It can show that a listed file changed after sealing. It cannot show that
someone rewrote a file and the seal together.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from verienvelope.errors import SchemaError, VeriEnvelopeError
from verienvelope.evidence_integrity import resolve_package_path, sha256_bytes
from verienvelope.schema_io import dump_json, validate_instance

SEAL_FILENAME = "seal.json"
SEALED_PATHS = (
    "manifest.json",
    "environment.json",
    "input/case.json",
    "input/component.json",
    "stdout.log",
    "stderr.log",
    "result.json",
    "notes.md",
)


def write_package_seal(package_dir: Path) -> dict[str, Any]:
    files: list[dict[str, str]] = []
    for relative in SEALED_PATHS:
        target = resolve_package_path(package_dir, relative)
        if target is None or not target.is_file():
            raise VeriEnvelopeError(f"cannot seal missing file: {relative}")
        files.append({"path": relative, "sha256": sha256_bytes(target.read_bytes())})
    document = {
        "kind": "evidence_package_seal",
        "algorithm": "sha256",
        "files": files,
    }
    validate_instance("seal.schema.json", document)
    dump_json(package_dir / SEAL_FILENAME, document)
    return document


def check_package_seal(package_dir: Path) -> list[str]:
    """Return failures. An empty list means every sealed path still matches."""
    if not package_dir.is_dir():
        return ["evidence package directory is missing"]
    seal_path = package_dir / SEAL_FILENAME
    if not seal_path.is_file():
        return ["final package seal is missing"]
    try:
        loaded = json.loads(seal_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ["final package seal is not json"]
    if not isinstance(loaded, dict):
        return ["final package seal is not an object"]
    try:
        validate_instance("seal.schema.json", loaded)
    except SchemaError as exc:
        return [f"final package seal does not match its schema: {exc}"]

    errors: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(loaded["files"]):
        relative = item["path"]
        digest = item["sha256"]
        if relative == SEAL_FILENAME:
            errors.append("seal must not hash itself")
            continue
        target = resolve_package_path(package_dir, relative)
        if target is None:
            errors.append(f"seal path escapes the package: {relative}")
            continue
        if relative in seen:
            errors.append(f"seal repeats path: {relative}")
            continue
        seen.add(relative)
        if not target.is_file():
            errors.append(f"missing sealed file: {relative}")
            continue
        actual = sha256_bytes(target.read_bytes())
        if actual != digest:
            errors.append(f"seal mismatch: {relative}")
    for required in SEALED_PATHS:
        if required not in seen:
            errors.append(f"seal omits required file: {required}")
    return errors

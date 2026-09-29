"""Check that a manifest's artifacts still exist inside the package and match SHA-256."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

REQUIRED_ARTIFACTS = (
    "stdout.log",
    "stderr.log",
    "environment.json",
    "input/case.json",
    "input/component.json",
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def hash_package_files(package_dir: Path) -> list[dict[str, str]]:
    root = package_dir.resolve()
    records: list[dict[str, str]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        records.append({"path": relative, "sha256": sha256_bytes(path.read_bytes())})
    return records


def resolve_package_path(package_dir: Path, relative: str) -> Path | None:
    if not isinstance(relative, str) or relative == "":
        return None
    if relative.startswith(("/", "\\")) or "\\" in relative:
        return None
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return None
    root = package_dir.resolve()
    candidate = (root / relative_path).resolve()
    if not candidate.is_relative_to(root):
        return None
    return candidate


def check_evidence_integrity(package_dir: Path, manifest: dict[str, Any]) -> list[str]:
    """Return human-readable failures. An empty list means the listed artifacts match."""
    if not package_dir.is_dir():
        return ["evidence package directory is missing"]
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return ["manifest has no artifact list"]

    errors: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(artifacts):
        if not isinstance(item, dict):
            errors.append(f"artifact {index} is not an object")
            continue
        relative = item.get("path")
        digest = item.get("sha256")
        if not isinstance(relative, str):
            errors.append(f"artifact {index} has no path")
            continue
        target = resolve_package_path(package_dir, relative)
        if target is None:
            errors.append(f"artifact path escapes the package: {relative}")
            continue
        seen.add(relative)
        if not isinstance(digest, str) or len(digest) != 64:
            errors.append(f"artifact {relative} has no sha256")
            continue
        if not target.is_file():
            errors.append(f"missing artifact: {relative}")
            continue
        actual = sha256_bytes(target.read_bytes())
        if actual != digest:
            errors.append(f"hash mismatch: {relative}")
    for required in REQUIRED_ARTIFACTS:
        if required not in seen:
            errors.append(f"manifest omits required artifact: {required}")
    return errors

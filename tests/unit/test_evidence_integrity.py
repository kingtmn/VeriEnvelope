from pathlib import Path

from verienvelope.evidence_integrity import (
    check_evidence_integrity,
    hash_package_files,
    resolve_package_path,
)


def _package(tmp_path: Path) -> tuple[Path, dict]:
    package = tmp_path / "pkg"
    (package / "input").mkdir(parents=True)
    (package / "stdout.log").write_bytes(b"stdout")
    (package / "stderr.log").write_bytes(b"stderr")
    (package / "environment.json").write_text('{"os":"test"}\n', encoding="utf-8")
    (package / "input" / "case.json").write_text("{}\n", encoding="utf-8")
    (package / "input" / "component.json").write_text("{}\n", encoding="utf-8")
    return package, {"artifacts": hash_package_files(package)}


def test_intact_package_has_no_integrity_errors(tmp_path: Path) -> None:
    package, manifest = _package(tmp_path)
    assert check_evidence_integrity(package, manifest) == []


def test_missing_evidence_is_reported(tmp_path: Path) -> None:
    package, manifest = _package(tmp_path)
    (package / "stdout.log").unlink()
    errors = check_evidence_integrity(package, manifest)
    assert any("missing artifact: stdout.log" in error for error in errors)


def test_modified_evidence_is_a_hash_mismatch(tmp_path: Path) -> None:
    package, manifest = _package(tmp_path)
    (package / "stderr.log").write_bytes(b"rewritten")
    errors = check_evidence_integrity(package, manifest)
    assert any("hash mismatch: stderr.log" in error for error in errors)


def test_manifest_hash_mismatch_is_reported(tmp_path: Path) -> None:
    package, manifest = _package(tmp_path)
    manifest["artifacts"][0]["sha256"] = "0" * 64
    errors = check_evidence_integrity(package, manifest)
    assert any(error.startswith("hash mismatch:") for error in errors)


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    package, manifest = _package(tmp_path)
    manifest["artifacts"].append({"path": "../outside.log", "sha256": "ab" * 32})
    errors = check_evidence_integrity(package, manifest)
    assert any("escapes the package" in error for error in errors)
    assert resolve_package_path(package, "/etc/passwd") is None
    outside = tmp_path / "outside.log"
    outside.write_bytes(b"secret")
    assert resolve_package_path(package, "../outside.log") is None


def test_omitted_required_artifact_is_reported(tmp_path: Path) -> None:
    package, manifest = _package(tmp_path)
    manifest["artifacts"] = [
        item for item in manifest["artifacts"] if item["path"] != "environment.json"
    ]
    errors = check_evidence_integrity(package, manifest)
    assert any("omits required artifact: environment.json" in error for error in errors)

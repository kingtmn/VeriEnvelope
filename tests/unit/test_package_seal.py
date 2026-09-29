import json
from pathlib import Path

from verienvelope.admission import evaluate_admission
from verienvelope.evidence_integrity import check_evidence_integrity, hash_package_files
from verienvelope.package_seal import SEALED_PATHS, check_package_seal, write_package_seal


def _finished(tmp_path: Path) -> tuple[Path, dict]:
    package = tmp_path / "pkg"
    (package / "input").mkdir(parents=True)
    (package / "stdout.log").write_bytes(b"stdout")
    (package / "stderr.log").write_bytes(b"stderr")
    (package / "environment.json").write_text("{}\n", encoding="utf-8")
    (package / "input" / "case.json").write_text("{}\n", encoding="utf-8")
    (package / "input" / "component.json").write_text("{}\n", encoding="utf-8")
    manifest = {"artifacts": hash_package_files(package)}
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (package / "result.json").write_text('{"admission":"admitted"}\n', encoding="utf-8")
    (package / "notes.md").write_text("notes\n", encoding="utf-8")
    write_package_seal(package)
    return package, manifest


def _result() -> dict:
    return {
        "record_purpose": "component_verification",
        "capabilities": [
            {
                "capability_id": "cap-1",
                "status": "demonstrated",
                "supporting_evidence": ["ev-1"],
            }
        ],
        "evidence_refs": ["ev-1"],
        "envelope": {
            "tested_conditions": ["local"],
            "known_limits": ["one environment"],
            "untested_areas": ["network off"],
        },
        "history": [],
    }


def _component() -> dict:
    return {
        "id": "example.local",
        "version": "1.0.0",
        "source_repository": "https://example.invalid/component",
        "commit": "abc123",
        "status": "candidate",
    }


def _evidence() -> list[dict]:
    return [{"evidence_id": "ev-1", "source_type": "ve_test"}]


def test_intact_package_passes_raw_and_seal(tmp_path: Path) -> None:
    package, manifest = _finished(tmp_path)
    seal = json.loads((package / "seal.json").read_text(encoding="utf-8"))
    assert [item["path"] for item in seal["files"]] == list(SEALED_PATHS)
    assert "seal.json" not in {item["path"] for item in seal["files"]}
    assert check_evidence_integrity(package, manifest) == []
    assert check_package_seal(package) == []
    status, reasons = evaluate_admission(
        _result(), _component(), _evidence(), package, manifest
    )
    assert status == "admitted"
    assert reasons == []


def test_modified_result_json_fails_integrity(tmp_path: Path) -> None:
    package, manifest = _finished(tmp_path)
    (package / "result.json").write_text('{"admission":"changed"}\n', encoding="utf-8")
    assert check_evidence_integrity(package, manifest) == []
    assert any("seal mismatch: result.json" in error for error in check_package_seal(package))
    status, reasons = evaluate_admission(
        _result(), _component(), _evidence(), package, manifest
    )
    assert status == "insufficient"
    assert any("result.json" in reason for reason in reasons)


def test_modified_notes_fail_integrity(tmp_path: Path) -> None:
    package, manifest = _finished(tmp_path)
    (package / "notes.md").write_text("edited\n", encoding="utf-8")
    errors = check_package_seal(package)
    assert any("seal mismatch: notes.md" in error for error in errors)
    status, _reasons = evaluate_admission(
        _result(), _component(), _evidence(), package, manifest
    )
    assert status == "insufficient"


def test_modified_manifest_fails_the_seal(tmp_path: Path) -> None:
    package, manifest = _finished(tmp_path)
    (package / "manifest.json").write_text('{"artifacts":[]}\n', encoding="utf-8")
    assert check_evidence_integrity(package, manifest) == []
    assert any("seal mismatch: manifest.json" in error for error in check_package_seal(package))
    status, reasons = evaluate_admission(
        _result(), _component(), _evidence(), package, manifest
    )
    assert status == "insufficient"
    assert any("manifest.json" in reason for reason in reasons)


def test_modified_stdout_fails_raw_and_seal(tmp_path: Path) -> None:
    package, manifest = _finished(tmp_path)
    (package / "stdout.log").write_bytes(b"changed")
    raw = check_evidence_integrity(package, manifest)
    seal = check_package_seal(package)
    assert any("hash mismatch: stdout.log" in error for error in raw)
    assert any("seal mismatch: stdout.log" in error for error in seal)
    status, _reasons = evaluate_admission(
        _result(), _component(), _evidence(), package, manifest
    )
    assert status == "insufficient"


def test_missing_sealed_file_fails(tmp_path: Path) -> None:
    package, _manifest = _finished(tmp_path)
    (package / "notes.md").unlink()
    errors = check_package_seal(package)
    assert any("missing sealed file: notes.md" in error for error in errors)


def test_altered_seal_entry_fails(tmp_path: Path) -> None:
    package, _manifest = _finished(tmp_path)
    seal_path = package / "seal.json"
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    seal["files"][0]["sha256"] = "0" * 64
    seal_path.write_text(json.dumps(seal), encoding="utf-8")
    errors = check_package_seal(package)
    assert any(error.startswith("seal mismatch:") for error in errors)


def test_seal_path_escape_is_rejected(tmp_path: Path) -> None:
    package, _manifest = _finished(tmp_path)
    seal_path = package / "seal.json"
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    seal["files"].append({"path": "../outside.log", "sha256": "ab" * 32})
    seal_path.write_text(json.dumps(seal), encoding="utf-8")
    errors = check_package_seal(package)
    assert any("escapes the package" in error for error in errors)

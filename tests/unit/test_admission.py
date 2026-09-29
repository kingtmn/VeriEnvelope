import copy
import json
from pathlib import Path

from verienvelope.admission import evaluate_admission, unresolved_defect
from verienvelope.evidence_integrity import hash_package_files
from verienvelope.package_seal import write_package_seal


def _component() -> dict:
    return {
        "id": "example.local",
        "name": "Example",
        "component_type": "mcp_server",
        "description": "synthetic gate fixture",
        "source_repository": "https://example.invalid/component",
        "version": "1.0.0",
        "commit": "abc123",
        "status": "candidate",
    }


def _result() -> dict:
    return {
        "record_purpose": "component_verification",
        "observation": "match",
        "outcome_class": "confirmed",
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


def _evidence() -> list[dict]:
    return [{"evidence_id": "ev-1", "source_type": "ve_test"}]


def _intact(tmp_path: Path) -> tuple[Path, dict]:
    package = tmp_path / "pkg"
    (package / "input").mkdir(parents=True)
    (package / "stdout.log").write_bytes(b"ok")
    (package / "stderr.log").write_bytes(b"")
    (package / "environment.json").write_text("{}\n", encoding="utf-8")
    (package / "input" / "case.json").write_text("{}\n", encoding="utf-8")
    (package / "input" / "component.json").write_text("{}\n", encoding="utf-8")
    manifest = {"artifacts": hash_package_files(package)}
    (package / "manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    (package / "result.json").write_text("{}\n", encoding="utf-8")
    (package / "notes.md").write_text("notes\n", encoding="utf-8")
    write_package_seal(package)
    return package, manifest


def test_complete_ve_test_can_be_admitted(tmp_path: Path) -> None:
    package, manifest = _intact(tmp_path)
    status, reasons = evaluate_admission(
        _result(), _component(), _evidence(), package, manifest
    )
    assert status == "admitted"
    assert reasons == []


def test_admission_does_not_infer_demonstrated_from_a_match(tmp_path: Path) -> None:
    package, manifest = _intact(tmp_path)
    result = _result()
    result["capabilities"][0]["status"] = "not_demonstrated"
    status, _reasons = evaluate_admission(
        result, _component(), _evidence(), package, manifest
    )
    assert status == "withheld"


def test_unexecuted_claim_keeps_a_demonstrated_claim_insufficient(tmp_path: Path) -> None:
    package, manifest = _intact(tmp_path)
    result = _result()
    result["capabilities"].append(
        {
            "capability_id": "C2",
            "status": "insufficient",
            "supporting_evidence": [],
        }
    )
    status, reasons = evaluate_admission(
        result, _component(), _evidence(), package, manifest
    )
    assert status == "insufficient"
    assert any("not executed" in reason for reason in reasons)


def test_admission_without_a_package_is_insufficient() -> None:
    status, reasons = evaluate_admission(_result(), _component(), _evidence())
    assert status == "insufficient"
    assert any("integrity" in reason for reason in reasons)


def test_pipeline_self_test_is_never_admitted(tmp_path: Path) -> None:
    package, manifest = _intact(tmp_path)
    result = _result()
    result["record_purpose"] = "pipeline_self_test"
    status, reasons = evaluate_admission(result, _component(), _evidence(), package, manifest)
    assert status == "insufficient"
    assert any("pipeline_self_test" in reason for reason in reasons)


def test_missing_commit_stays_insufficient(tmp_path: Path) -> None:
    package, manifest = _intact(tmp_path)
    component = _component()
    component["commit"] = None
    status, _reasons = evaluate_admission(_result(), component, _evidence(), package, manifest)
    assert status == "insufficient"


def test_vendor_claim_does_not_open_the_gate(tmp_path: Path) -> None:
    package, manifest = _intact(tmp_path)
    status, reasons = evaluate_admission(
        _result(),
        _component(),
        [{"evidence_id": "ev-1", "source_type": "vendor_claim"}],
        package,
        manifest,
    )
    assert status == "withheld"
    assert any("ve_test" in reason for reason in reasons)


def test_independent_test_does_not_become_an_official_admission(tmp_path: Path) -> None:
    package, manifest = _intact(tmp_path)
    status, _reasons = evaluate_admission(
        _result(),
        _component(),
        [{"evidence_id": "ev-1", "source_type": "independent_test"}],
        package,
        manifest,
    )
    assert status == "withheld"


def test_not_demonstrated_is_withheld_when_the_record_is_complete(tmp_path: Path) -> None:
    package, manifest = _intact(tmp_path)
    result = _result()
    result["capabilities"][0]["status"] = "not_demonstrated"
    result["observation"] = "mismatch"
    result["outcome_class"] = "component_failure"
    status, _reasons = evaluate_admission(result, _component(), _evidence(), package, manifest)
    assert status == "withheld"


def test_empty_observed_limits_do_not_block_admission(tmp_path: Path) -> None:
    package, manifest = _intact(tmp_path)
    result = _result()
    result["envelope"]["known_limits"] = []
    status, reasons = evaluate_admission(result, _component(), _evidence(), package, manifest)
    assert status == "admitted"
    assert reasons == []


def test_empty_envelope_is_insufficient_even_if_capability_failed(tmp_path: Path) -> None:
    package, manifest = _intact(tmp_path)
    result = _result()
    result["capabilities"][0]["status"] = "not_demonstrated"
    result["envelope"]["untested_areas"] = []
    status, _reasons = evaluate_admission(result, _component(), _evidence(), package, manifest)
    assert status == "insufficient"


def test_unresolved_evaluation_defect_withholds_admission(tmp_path: Path) -> None:
    package, manifest = _intact(tmp_path)
    result = _result()
    result["history"] = [
        {"event_type": "confirmed"},
        {"event_type": "evaluation_defect"},
    ]
    status, _reasons = evaluate_admission(result, _component(), _evidence(), package, manifest)
    assert status == "withheld"


def test_revalidated_defect_can_clear_the_open_flag(tmp_path: Path) -> None:
    package, manifest = _intact(tmp_path)
    history = [
        {"event_type": "evaluation_defect"},
        {"event_type": "revalidated"},
    ]
    assert unresolved_defect(history) is False
    result = _result()
    result["history"] = history
    status, _reasons = evaluate_admission(result, _component(), _evidence(), package, manifest)
    assert status == "admitted"


def test_new_defect_after_a_fix_stays_unresolved() -> None:
    assert unresolved_defect(
        [
            {"event_type": "runner_defect"},
            {"event_type": "fixed"},
            {"event_type": "method_defect"},
        ]
    )


def test_withdrawn_component_is_withheld(tmp_path: Path) -> None:
    package, manifest = _intact(tmp_path)
    component = copy.deepcopy(_component())
    component["status"] = "withdrawn"
    status, _reasons = evaluate_admission(_result(), component, _evidence(), package, manifest)
    assert status == "withheld"


def test_hash_mismatch_blocks_admission(tmp_path: Path) -> None:
    package, manifest = _intact(tmp_path)
    (package / "stdout.log").write_bytes(b"changed")
    status, reasons = evaluate_admission(
        _result(), _component(), _evidence(), package, manifest
    )
    assert status == "insufficient"
    assert any("hash mismatch" in reason for reason in reasons)

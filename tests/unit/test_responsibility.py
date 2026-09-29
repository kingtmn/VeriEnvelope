"""Responsibility boundaries. These tests do not start Everything."""

from pathlib import Path

from verienvelope.artifact_identity import (
    execution_artifact,
    identity_reference,
    source_identity,
)
from verienvelope.envelope import claim_envelope
from verienvelope.errors import VeriEnvelopeError
from verienvelope.pilot_preflight import (
    append_authorization_consumed,
    consumed_runs,
    load_run3_authorization,
    load_run_authorization,
    run3_authorized,
    run_authorized,
)
from verienvelope.project_gate import pilot_status, project_gate_1
from verienvelope.revalidation import verification_applicability
import pytest


def test_identity_reference_changes_with_source_or_artifact() -> None:
    source = source_identity()
    artifact = execution_artifact()
    first = identity_reference(source, artifact)
    assert first.startswith("sha256:")
    assert identity_reference(source, artifact) == first
    moved = dict(source)
    moved["source_commit"] = "0" * 40
    assert identity_reference(moved, artifact) != first
    other_image = dict(artifact)
    other_image["local_image_id"] = "sha256:" + "ab" * 32
    assert identity_reference(source, other_image) != first


def test_observed_limits_may_be_empty_and_unknown_may_not() -> None:
    envelope = claim_envelope(
        tested_conditions=["stdio"],
        known_limits=[],
        untested_areas=["other transports"],
        revalidation_triggers=["source_commit"],
    )
    assert envelope["known_limits"] == []
    with pytest.raises(VeriEnvelopeError):
        claim_envelope(
            tested_conditions=["stdio"],
            known_limits=[],
            untested_areas=[],
            revalidation_triggers=["source_commit"],
        )


def test_applicability_does_not_touch_evidence(tmp_path) -> None:
    recorded = {
        "source_commit": "a",
        "execution_artifact": "sha256:1",
        "method_version": "0.3.0",
        "runner_version": "0.1.0",
        "protocol": "2025-03-26",
    }
    evidence = tmp_path / "stdout.log"
    evidence.write_bytes(b"historical")
    before = evidence.read_bytes()
    assert verification_applicability(recorded, dict(recorded)) == "current"
    for key in recorded:
        changed = dict(recorded)
        changed[key] = "different"
        assert verification_applicability(recorded, changed) == "revalidation_required"
    assert evidence.read_bytes() == before


def test_one_pilot_does_not_pass_project_gate_1() -> None:
    chain = {
        "identity": True,
        "claims": True,
        "method": True,
        "execution": True,
        "evidence": True,
        "l0": True,
        "l1": True,
        "l2": True,
        "history": True,
        "admission_decision": True,
    }
    assert pilot_status(chain) == "complete"
    assert project_gate_1(semantic_tool_cases=0) == "not_passed"
    assert project_gate_1(semantic_tool_cases=1) == "not_passed"
    assert project_gate_1(semantic_tool_cases=3) == "passed"
    assert pilot_status({"identity": True}) == "incomplete"


def test_run3_authorization_is_not_run2() -> None:
    assert run3_authorized(consumed=frozenset()) is True
    assert run_authorized(consumed=frozenset()) is True
    assert run3_authorized() is False
    assert run_authorized() is False
    current = {
        "authorized": True,
        "planned_run": "external-run-3",
        "primary_claim": "C3",
        "method_version": "0.3.0",
        "execution_artifact": "sha256:5f1784c80a95be56091a16ac8f6955b32eb170dcf89ee3b9d2cb86c0b26fe1d6",
        "sandbox_policy": "ADR-008-amendment-1",
        "timestamp": "2026-09-26T14:45:00Z",
        "previous_run": {
            "planned_run": "external-run-2",
            "primary_claim": "C2",
            "status": "completed",
        },
    }
    assert run3_authorized(current, consumed=frozenset()) is True
    assert run3_authorized(current) is False
    assert run_authorized(current) is False
    assert load_run_authorization()["authorized"] is True
    assert load_run3_authorization()["authorized"] is True
    assert {"external-run-2", "external-run-3"} <= consumed_runs()


def test_consumed_event_is_appended(tmp_path: Path) -> None:
    path = tmp_path / "authorization-events.jsonl"
    path.write_text('{"event":"authorization_consumed","planned_run":"external-run-2"}\n', encoding="utf-8")
    before = path.read_bytes()
    append_authorization_consumed(
        "external-run-9",
        path=path,
        recorded_at="2026-09-26T15:34:00Z",
        note="append only",
    )
    text = path.read_text(encoding="utf-8")
    assert text.encode("utf-8").startswith(before)
    assert consumed_runs(path) == frozenset({"external-run-2", "external-run-9"})

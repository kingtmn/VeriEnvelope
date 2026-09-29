"""Reject records that contradict themselves. Unknown is not rewritten into pass."""

from __future__ import annotations

from typing import Any

from verienvelope.errors import VeriEnvelopeError


def _headline_claim(capability: dict[str, Any]) -> str | None:
    """The result observation belongs to the primary claim named in tested_under."""
    tested = str(capability.get("tested_under") or "")
    marker = "primary "
    if marker not in tested:
        return None
    token = tested.split(marker, 1)[1].split(";", 1)[0].strip()
    return token or None


def consistency_errors(result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    observation = result.get("observation")
    outcome = result.get("outcome_class")
    if outcome == "confirmed" and observation != "match":
        errors.append("outcome confirmed requires observation match")
    if result.get("admission") == "admitted":
        if result.get("record_purpose") != "component_verification":
            errors.append("only component_verification records can be admitted")
        if result.get("admission_reasons"):
            errors.append("admitted records must have empty admission_reasons")
    if (
        result.get("record_purpose") in {"pipeline_self_test", "instrument_self_test"}
        and result.get("admission") == "admitted"
    ):
        errors.append("self-test records cannot be admitted")

    refs = set(result.get("evidence_refs") or [])
    for capability in result.get("capabilities") or []:
        status = capability.get("status")
        supporting = capability.get("supporting_evidence") or []
        if status == "demonstrated":
            if not supporting:
                errors.append("demonstrated capability lacks supporting evidence")
            headline = _headline_claim(capability)
            if headline is None or capability.get("capability_id") == headline:
                if observation != "match":
                    errors.append("demonstrated capability requires observation match")
                if outcome != "confirmed":
                    errors.append("demonstrated capability requires outcome confirmed")
        for evidence_id in supporting:
            if evidence_id not in refs:
                errors.append(
                    f"supporting evidence {evidence_id} is not listed in evidence_refs"
                )
    return errors


def assert_consistent(result: dict[str, Any]) -> None:
    errors = consistency_errors(result)
    if errors:
        raise VeriEnvelopeError("result is internally inconsistent:\n" + "\n".join(errors))

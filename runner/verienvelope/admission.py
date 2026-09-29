"""Admission gate. Missing material stays insufficient; it is not a rejection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from verienvelope.evidence_integrity import check_evidence_integrity
from verienvelope.package_seal import check_package_seal

DEFECT_EVENTS = frozenset({"method_defect", "runner_defect", "evaluation_defect"})
RESOLVED_EVENTS = frozenset({"fixed", "revalidated"})
_ENVELOPE_KEYS = ("tested_conditions", "untested_areas")
_CLAIM_ENVELOPE_KEYS = ("tested_conditions", "untested_areas", "revalidation_triggers")


def unresolved_defect(history: list[dict[str, Any]]) -> bool:
    """A later fixed or revalidated event clears the current open-defect flag.

    It does not track defects one by one. That is enough while a record's
    history stays short, and it is the wrong model once several defects overlap.
    """
    open_defect = False
    for event in history:
        kind = event.get("event_type")
        if kind in DEFECT_EVENTS:
            open_defect = True
        elif kind in RESOLVED_EVENTS:
            open_defect = False
    return open_defect


def evaluate_admission(
    result: dict[str, Any],
    component: dict[str, Any],
    evidence_records: list[dict[str, Any]] | None = None,
    package_dir: Path | None = None,
    manifest: dict[str, Any] | None = None,
    *,
    check_seal: bool = True,
) -> tuple[str, list[str]]:
    integrity_errors = _integrity_errors(package_dir, manifest, check_seal=check_seal)
    purpose = result.get("record_purpose")
    if purpose in {"pipeline_self_test", "instrument_self_test"}:
        reasons = [
            f"record_purpose is {purpose}; this record is not an admission decision"
        ]
        if package_dir is not None or manifest is not None:
            reasons.extend(integrity_errors)
        return "insufficient", reasons
    if result.get("record_purpose") != "component_verification":
        return (
            "insufficient",
            ["record_purpose is not component_verification"],
        )

    missing: list[str] = []
    failures: list[str] = []
    if package_dir is None and manifest is None:
        missing.append("evidence package was not supplied for an integrity check")
    else:
        missing.extend(integrity_errors)

    for field in ("id", "version", "source_repository"):
        if not component.get(field):
            missing.append(f"identity field {field} is absent")
    if not component.get("commit"):
        missing.append("identity is not locked: commit is absent")
    if component.get("status") == "withdrawn":
        failures.append("component status is withdrawn")

    capabilities = result.get("capabilities") or []
    if not capabilities:
        missing.append("no capabilities were recorded")
    demonstrated = [cap for cap in capabilities if cap.get("status") == "demonstrated"]
    negative = [cap for cap in capabilities if cap.get("status") == "not_demonstrated"]
    unfinished = [
        cap
        for cap in capabilities
        if cap.get("status") in {"insufficient", "unknown", "out_of_envelope"}
    ]
    if negative:
        failures.append("a recorded capability is not_demonstrated")
    if unfinished:
        missing.append("a recorded capability was not executed")
    if not demonstrated and not negative:
        missing.append("no capability is demonstrated")

    records = evidence_records or []
    by_id = {record.get("evidence_id"): record for record in records}
    if not records:
        missing.append("evidence records were not supplied")
    for capability in demonstrated:
        evidence_ids = capability.get("supporting_evidence") or []
        if not evidence_ids:
            missing.append(
                f"capability {capability.get('capability_id')} is demonstrated without evidence"
            )
            continue
        saw_ve_test = False
        for evidence_id in evidence_ids:
            record = by_id.get(evidence_id)
            if record is None:
                missing.append(f"evidence {evidence_id} was not supplied")
                continue
            if record.get("source_type") == "ve_test":
                saw_ve_test = True
        if evidence_ids and not saw_ve_test and records:
            failures.append(
                f"capability {capability.get('capability_id')} has no ve_test evidence"
            )

    if not result.get("evidence_refs"):
        missing.append("no evidence refs")

    envelope = result.get("envelope") or {}
    for key in _ENVELOPE_KEYS:
        if not envelope.get(key):
            missing.append(f"envelope.{key} is empty")
    if "known_limits" not in envelope:
        missing.append("envelope.known_limits is absent")
    for capability in capabilities:
        claim_envelope = capability.get("envelope")
        if not isinstance(claim_envelope, dict):
            continue
        claim_id = capability.get("capability_id")
        for key in _CLAIM_ENVELOPE_KEYS:
            if not claim_envelope.get(key):
                missing.append(f"capability {claim_id} envelope.{key} is empty")
        if "known_limits" not in claim_envelope:
            missing.append(f"capability {claim_id} envelope.known_limits is absent")

    if unresolved_defect(result.get("history") or []):
        failures.append("history has an unresolved method, runner, or evaluation defect")

    if missing:
        return "insufficient", missing + failures
    if failures:
        return "withheld", failures
    return "admitted", []


def _integrity_errors(
    package_dir: Path | None,
    manifest: dict[str, Any] | None,
    *,
    check_seal: bool,
) -> list[str]:
    if package_dir is None or manifest is None:
        return ["evidence integrity check needs both the package directory and the manifest"]
    errors = check_evidence_integrity(package_dir, manifest)
    if check_seal:
        errors.extend(check_package_seal(package_dir))
    return errors

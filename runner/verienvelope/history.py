"""Append-only history. This does not stop someone from rewriting Git."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from verienvelope.errors import VeriEnvelopeError


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def make_event(
    *,
    event_type: str,
    previous_state: str | None,
    new_state: str,
    reason: str,
    evidence_refs: list[str],
    timestamp: str | None = None,
) -> dict[str, Any]:
    if not reason:
        raise VeriEnvelopeError("history reason must not be empty")
    return {
        "event_id": new_id("evt"),
        "timestamp": timestamp or utc_now(),
        "event_type": event_type,
        "previous_state": previous_state,
        "new_state": new_state,
        "reason": reason,
        "evidence_refs": list(evidence_refs),
    }


def assert_history_extends(previous: list[dict[str, Any]], proposed: list[dict[str, Any]]) -> None:
    if proposed[: len(previous)] != previous:
        raise VeriEnvelopeError(
            "history prefix was altered or truncated; append a new event instead"
        )
    if len(proposed) < len(previous):
        raise VeriEnvelopeError("history was truncated")


def append_history(result: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    before = list(result.get("history") or [])
    after = [*before, event]
    assert_history_extends(before, after)
    if len(after) != len(before) + 1:
        raise VeriEnvelopeError("history append did not add exactly one event")
    updated = dict(result)
    updated["history"] = after
    return updated

"""Pilot completion and Project GATE 1 are different questions.

One finished external component does not open a public site.
"""

from __future__ import annotations

from typing import Mapping

PILOT_CHAIN = (
    "identity",
    "claims",
    "method",
    "execution",
    "evidence",
    "l0",
    "l1",
    "l2",
    "history",
    "admission_decision",
)
PROJECT_GATE_1_MINIMUM = 3


def pilot_status(chain: Mapping[str, bool]) -> str:
    if all(bool(chain.get(part)) for part in PILOT_CHAIN):
        return "complete"
    return "incomplete"


def project_gate_1(*, semantic_tool_cases: int) -> str:
    """Count tool-specific semantic measurements, not completed pilots.

    initialize or tools/list alone does not qualify. A pilot that stopped
    before that semantic claim can still be complete and still adds zero.
    """
    if semantic_tool_cases >= PROJECT_GATE_1_MINIMUM:
        return "passed"
    return "not_passed"

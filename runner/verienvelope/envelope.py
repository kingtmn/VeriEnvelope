"""Claim envelope. Four information categories, not four new layers.

Field names stay the ones already in the verification result:

- tested_conditions: declared scope
- known_limits: observed limits; an empty list is allowed
- untested_areas: unknown region
- revalidation_triggers: revalidation boundary
"""

from __future__ import annotations

from typing import Any

from verienvelope.errors import VeriEnvelopeError


def claim_envelope(
    *,
    tested_conditions: list[str],
    known_limits: list[str],
    untested_areas: list[str],
    revalidation_triggers: list[str],
) -> dict[str, list[str]]:
    if not tested_conditions:
        raise VeriEnvelopeError("declared scope is empty")
    if known_limits is None:
        raise VeriEnvelopeError("observed limits must be a list")
    if not untested_areas:
        raise VeriEnvelopeError("unknown region is empty")
    if not revalidation_triggers:
        raise VeriEnvelopeError("revalidation boundary is empty")
    return {
        "tested_conditions": list(tested_conditions),
        "known_limits": list(known_limits),
        "untested_areas": list(untested_areas),
        "revalidation_triggers": list(revalidation_triggers),
    }


def claim_envelope_from_run(envelope: dict[str, Any]) -> dict[str, list[str]]:
    """Copy the four categories already on a run-level envelope."""
    return claim_envelope(
        tested_conditions=list(envelope["tested_conditions"]),
        known_limits=list(envelope["known_limits"]),
        untested_areas=list(envelope["untested_areas"]),
        revalidation_triggers=list(envelope["revalidation_triggers"]),
    )

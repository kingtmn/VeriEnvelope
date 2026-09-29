"""Map one execution onto a rule id. Outcomes stay in the method file."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from verienvelope.errors import MethodError

IMPLEMENTED_RULE_IDS = ("R1", "R2", "R3", "R4", "R5")


@dataclass(frozen=True)
class RuleOutcome:
    rule_id: str
    observation: str
    outcome_class: str
    capability_status: str
    run_note: str


def rule_table(method: dict[str, Any]) -> dict[str, RuleOutcome]:
    raw = method.get("classification_rules")
    if not isinstance(raw, list) or not raw:
        raise MethodError("method has no classification_rules")
    table: dict[str, RuleOutcome] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise MethodError("classification rule is not a mapping")
        rule_id = item.get("id")
        if not isinstance(rule_id, str) or rule_id == "":
            raise MethodError("classification rule is missing an id")
        if rule_id in table:
            raise MethodError(f"duplicate rule id {rule_id}")
        try:
            table[rule_id] = RuleOutcome(
                rule_id=rule_id,
                observation=item["observation"],
                outcome_class=item["outcome_class"],
                capability_status=item["capability_status"],
                run_note=item["run_note"],
            )
        except KeyError as exc:
            raise MethodError(f"rule {rule_id} is missing {exc.args[0]}") from exc
    declared = tuple(table)
    if declared != IMPLEMENTED_RULE_IDS:
        raise MethodError(
            "runner implements "
            f"{list(IMPLEMENTED_RULE_IDS)} but method declares {list(declared)}"
        )
    return table


def select_rule_id(
    *,
    blocked: bool,
    timed_out: bool,
    exit_code: int | None,
    stdout: bytes | None,
    expected_exit_code: int,
    expected_stdout: bytes,
) -> str:
    """Return the rule id. The method file supplies the outcome labels."""
    if blocked:
        return "R5"
    if timed_out:
        return "R4"
    if exit_code != expected_exit_code:
        return "R3"
    if stdout != expected_stdout:
        return "R2"
    return "R1"

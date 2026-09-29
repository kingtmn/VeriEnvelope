import yaml

from tests.paths import METHOD
from verienvelope.rules import IMPLEMENTED_RULE_IDS, rule_table, select_rule_id

ORACLE = {
    "R1": ("match", "confirmed", "demonstrated"),
    "R2": ("mismatch", "component_failure", "not_demonstrated"),
    "R3": ("execution_error", "component_failure", "not_demonstrated"),
    "R4": ("execution_error", "unclassified", "insufficient"),
    "R5": ("blocked", "out_of_envelope", "insufficient"),
}


def test_method_rules_match_the_independent_oracle() -> None:
    method = yaml.safe_load((METHOD / "method.yaml").read_text(encoding="utf-8"))
    table = rule_table(method)
    assert tuple(table) == IMPLEMENTED_RULE_IDS
    for rule_id, expected in ORACLE.items():
        rule = table[rule_id]
        assert (rule.observation, rule.outcome_class, rule.capability_status) == expected


def test_exit_mismatch_wins_over_stdout_mismatch() -> None:
    assert (
        select_rule_id(
            blocked=False,
            timed_out=False,
            exit_code=2,
            stdout=b"other",
            expected_exit_code=0,
            expected_stdout=b"expected",
        )
        == "R3"
    )


def test_timeout_is_not_classified_as_a_component_failure() -> None:
    assert (
        select_rule_id(
            blocked=False,
            timed_out=True,
            exit_code=None,
            stdout=b"",
            expected_exit_code=0,
            expected_stdout=b"expected",
        )
        == "R4"
    )

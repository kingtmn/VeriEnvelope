import copy
from pathlib import Path

import pytest
import yaml

from tests.paths import ROOT
from verienvelope.errors import MethodError, PolicyError, SchemaError
from verienvelope.pilot_preflight import checklist, gate_open, load_execution_facts
from verienvelope.policy import assert_execution_allowed
from verienvelope.revalidation import TRIGGER_KINDS
from verienvelope.rules import rule_table
from verienvelope.run import run_case
from verienvelope.schema_io import validate_instance
from verienvelope.view import render_html

METHOD = ROOT / "methods" / "VE-METHOD-MCP-001"
CANDIDATE = ROOT / "registry" / "candidates" / "mcp.server-everything.json"
NON_CLAIMS = (
    "production readiness",
    "security",
    "general reliability",
    "bug-free",
    "all MCP capabilities",
    "all tools",
    "malicious input resistance",
    "cross-platform correctness",
    "long-running stability",
    "performance",
    "resource exhaustion resistance",
    "network behavior",
)
UNCONDITIONAL = {
    "echo",
    "get-annotated-message",
    "get-env",
    "get-resource-links",
    "get-resource-reference",
    "get-structured-content",
    "get-sum",
    "get-tiny-image",
    "gzip-file-as-resource",
    "simulate-research-query",
    "toggle-simulated-logging",
    "toggle-subscriber-updates",
    "trigger-long-running-operation",
}


def _method() -> dict:
    return yaml.safe_load((METHOD / "method.yaml").read_text(encoding="utf-8"))


def test_candidate_matches_the_component_schema() -> None:
    import json

    component = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    validate_instance("component.schema.json", component)
    assert component["status"] == "candidate"
    rejected = dict(component)
    rejected["status"] = "admitted"
    with pytest.raises(SchemaError):
        validate_instance("component.schema.json", rejected)
    assert component["component_type"] == "mcp_server"
    assert component["commit"] == "f46d9578190b476b3501923ea8977d899e8db2cb"
    assert component["version"] == "2.0.0"
    assert "stars" not in component


def test_method_pins_the_same_commit_and_three_claims() -> None:
    method = _method()
    component_commit = json_commit()
    assert method["identity"]["commit"] == component_commit
    assert method["id"] == "VE-METHOD-MCP-001"
    assert str(method["version"]) == "0.3.0"
    assert "2025-03-26" in method["claims"][0]["expected_observation"]
    assert "Echo: verienvelope-pilot-echo" in method["claims"][2]["expected_observation"]
    rules = {item["id"]: item for item in method["classification_rules"]}
    assert rules["M2"]["outcome_class"] == "unclassified"
    assert rules["M4"]["outcome_class"] == "unclassified"
    assert rules["M6"]["outcome_class"] == "unclassified"
    assert method["purpose"] == "mcp_pilot"
    assert [claim["id"] for claim in method["claims"]] == ["C1", "C2", "C3"]
    echo = method["claims"][2]
    assert echo["tool"] == "echo"
    assert echo["arguments"]["message"] == "verienvelope-pilot-echo"
    assert "Echo: verienvelope-pilot-echo" in echo["expected_observation"]
    names = set(method["claims"][1]["unconditional_tools"])
    assert names == UNCONDITIONAL
    assert set(method["envelope"]["revalidation_triggers"]) == TRIGGER_KINDS
    for phrase in NON_CLAIMS:
        assert any(phrase in item for item in method["envelope"]["untested_areas"])


def json_commit() -> str:
    import json

    return json.loads(CANDIDATE.read_text(encoding="utf-8"))["commit"]


def test_run_case_refuses_the_mcp_method_before_execution(tmp_path: Path) -> None:
    with pytest.raises(PolicyError, match="isolation"):
        assert_execution_allowed(_method())
    with pytest.raises(PolicyError, match="isolation"):
        run_case(METHOD, tmp_path / "missing-case.json", tmp_path / "out")


def test_reference_rule_table_does_not_accept_mcp_rules() -> None:
    with pytest.raises(MethodError):
        rule_table(_method())


def test_preflight_document_matches_the_checklist() -> None:
    facts = load_execution_facts()
    items = checklist(facts)
    assert [item.number for item in items] == list(range(1, 23))
    text = (ROOT / "methodology" / "pilot_preflight.md").read_text(encoding="utf-8")
    for item in items:
        assert item.condition in text
    if gate_open():
        assert "PILOT PREFLIGHT GATE：READY" in text
    else:
        assert "PILOT PREFLIGHT GATE：NOT READY" in text


def test_viewer_shows_pilot_non_claims(tmp_path: Path) -> None:
    from tests.paths import METHOD as SELF_TEST

    result = run_case(SELF_TEST, SELF_TEST / "cases" / "echo_match.json", tmp_path)
    shown = copy.deepcopy(result)
    shown["envelope"]["untested_areas"] = [
        f"不声明 {phrase}" for phrase in NON_CLAIMS
    ]
    html = render_html(shown)
    assert "这次不声明" in html
    for phrase in NON_CLAIMS:
        assert phrase in html

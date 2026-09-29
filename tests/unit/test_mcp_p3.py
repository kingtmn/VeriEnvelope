"""Pilot #3 judgments use the preregistered fixture bytes. No container."""

import copy
import inspect

import pytest

from verienvelope.errors import VeriEnvelopeError
from verienvelope.mcp_p3 import (
    FIXTURE_PATH,
    TOOL_NAME,
    fixture_text,
    judge_discovery,
    judge_read,
    judge_session,
    load_method,
    rule_table,
)
from verienvelope.schema_io import load_yaml, repo_root


def _read_message(text: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 3,
        "result": {"content": [{"type": "text", "text": text}]},
    }


def test_filesystem_method_pins_the_fixture():
    method = load_method()
    assert method["version"] == "0.2.0"
    assert method["identity"]["commit"] == "f46d9578190b476b3501923ea8977d899e8db2cb"
    assert method["execution"]["sandbox_policy"] == "ADR-008-amendment-3"
    assert method["execution"]["local_image_id"].startswith("sha256:")
    text = fixture_text(method)
    assert text == "ve-pilot-3\n"
    assert FIXTURE_PATH == "/app/fixture/ve-pilot-3.txt"
    assert TOOL_NAME == "read_text_file"


def test_method_0_1_0_still_has_the_incomplete_rules():
    frozen = load_yaml(repo_root() / "methods" / "VE-METHOD-MCP-003" / "versions" / "0.1.0.yaml")
    rules = {item["id"]: item for item in frozen["classification_rules"]}
    assert frozen["version"] == "0.1.0"
    assert "capability_status" not in rules["P3-M7"]
    assert "capability_status" not in rules["P3-M1"]
    assert "capability_status" not in rules["P3-M4"]
    assert rules["P3-M6"]["when"] == "这条规则保留编号，不与 P3-M2 重叠。"


def test_a_rule_without_capability_status_cannot_load():
    method = copy.deepcopy(load_method())
    for item in method["classification_rules"]:
        if item["id"] == "P3-M7":
            del item["capability_status"]
    with pytest.raises(VeriEnvelopeError, match="P3-M7"):
        rule_table(method)


def test_p3_m7_status_comes_from_the_method():
    method = load_method()
    judgment = judge_read(method, _read_message("ve-pilot-3\n"), "ve-pilot-3\n")
    rule = next(item for item in method["classification_rules"] if item["id"] == "P3-M7")
    assert judgment.rule_id == "P3-M7"
    assert judgment.observation == rule["observation"]
    assert judgment.outcome_class == rule["outcome_class"]
    assert judgment.capability_status == rule["capability_status"]
    assert judgment.note == rule["run_note"]
    assert '"demonstrated"' not in inspect.getsource(judge_read)


def test_runner_follows_a_replaced_method_status():
    method = copy.deepcopy(load_method())
    for item in method["classification_rules"]:
        if item["id"] == "P3-M7":
            item["capability_status"] = "unknown"
    judgment = judge_read(method, _read_message("ve-pilot-3\n"), "ve-pilot-3\n")
    assert judgment.observation == "match"
    assert judgment.outcome_class == "confirmed"
    assert judgment.capability_status == "unknown"


def test_a_different_text_uses_the_method_mismatch_rule():
    method = load_method()
    judgment = judge_read(method, _read_message("other"), "ve-pilot-3\n")
    rule = next(item for item in method["classification_rules"] if item["id"] == "P3-M8")
    assert judgment.rule_id == "P3-M8"
    assert judgment.outcome_class == rule["outcome_class"]
    assert judgment.capability_status == rule["capability_status"]


def test_discovery_accepts_extra_tool_names():
    method = load_method()
    message = {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {"tools": [{"name": "read_text_file"}, {"name": "write_file"}]},
    }
    judgment = judge_discovery(method, message)
    rule = next(item for item in method["classification_rules"] if item["id"] == "P3-M4")
    assert judgment.observation == rule["observation"]
    assert judgment.capability_status == rule["capability_status"]


def test_session_does_not_require_a_server_name():
    method = load_method()
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"protocolVersion": "2025-03-26", "serverInfo": {"name": "anything", "version": "0"}},
    }
    judgment = judge_session(method, message)
    rule = next(item for item in method["classification_rules"] if item["id"] == "P3-M1")
    assert judgment.rule_id == "P3-M1"
    assert judgment.capability_status == rule["capability_status"]

"""Pilot #5 judgments read labels from the method. No container."""

import copy
import inspect

import pytest

from verienvelope.errors import VeriEnvelopeError
from verienvelope.mcp_p5 import (
    expected_entities,
    judge_create,
    judge_discovery,
    judge_session,
    load_method,
    rule_table,
)


ENTITY = {"name": "ve-pilot-5", "entityType": "fixture", "observations": ["fixed"]}


def _create_message(text: str, is_error: bool = False) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 3,
        "result": {"content": [{"type": "text", "text": text}], "isError": is_error},
    }


def test_memory_method_pins_the_entity():
    method = load_method()
    assert method["version"] == "0.1.0"
    assert method["identity"]["commit"] == "f46d9578190b476b3501923ea8977d899e8db2cb"
    assert method["execution"]["sandbox_policy"] == "ADR-008-amendment-3"
    assert method["execution"]["memory_file_path"] == "/tmp/ve-pilot-5.jsonl"
    assert method["execution"]["local_image_id"].startswith("sha256:")
    assert expected_entities(method) == [ENTITY]


def test_every_selected_rule_has_a_capability_status():
    table = rule_table(load_method())
    assert "P5-M6" not in table
    assert "P5-M7" in table


def test_a_rule_without_capability_status_cannot_load():
    method = copy.deepcopy(load_method())
    for item in method["classification_rules"]:
        if item["id"] == "P5-M7":
            del item["capability_status"]
    with pytest.raises(VeriEnvelopeError, match="P5-M7"):
        rule_table(method)


def test_p5_m7_status_comes_from_the_method():
    method = load_method()
    judgment = judge_create(
        method,
        _create_message('[{"name":"ve-pilot-5","entityType":"fixture","observations":["fixed"]}]'),
        [ENTITY],
    )
    rule = next(item for item in method["classification_rules"] if item["id"] == "P5-M7")
    assert judgment.rule_id == "P5-M7"
    assert judgment.observation == rule["observation"]
    assert judgment.outcome_class == rule["outcome_class"]
    assert judgment.capability_status == rule["capability_status"]
    assert judgment.note == rule["run_note"]
    assert '"demonstrated"' not in inspect.getsource(judge_create)
    assert '"demonstrated"' not in inspect.getsource(judge_session)


def test_runner_follows_a_replaced_method_status():
    method = copy.deepcopy(load_method())
    for item in method["classification_rules"]:
        if item["id"] == "P5-M7":
            item["capability_status"] = "unknown"
    judgment = judge_create(
        method,
        _create_message('[{"name":"ve-pilot-5","entityType":"fixture","observations":["fixed"]}]'),
        [ENTITY],
    )
    assert judgment.observation == "match"
    assert judgment.capability_status == "unknown"


def test_a_different_entity_uses_the_mismatch_rule():
    method = load_method()
    judgment = judge_create(
        method,
        _create_message('[{"name":"other","entityType":"fixture","observations":["fixed"]}]'),
        [ENTITY],
    )
    assert judgment.rule_id == "P5-M8"


def test_unparsed_text_is_a_mismatch_when_the_result_exists():
    method = load_method()
    judgment = judge_create(method, _create_message("not-json"), [ENTITY])
    assert judgment.rule_id == "P5-M8"


def test_an_error_flag_does_not_match_the_success_rule():
    method = load_method()
    judgment = judge_create(
        method,
        _create_message('[{"name":"ve-pilot-5","entityType":"fixture","observations":["fixed"]}]', is_error=True),
        [ENTITY],
    )
    assert judgment.rule_id == "P5-M8"


def test_discovery_accepts_extra_tool_names():
    method = load_method()
    message = {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {"tools": [{"name": "read_graph"}, {"name": "create_entities"}]},
    }
    assert judge_discovery(method, message).rule_id == "P5-M4"


def test_session_checks_only_the_protocol_version():
    method = load_method()
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"protocolVersion": "2025-03-26", "serverInfo": {"name": "anything", "version": "0"}},
    }
    assert judge_session(method, message).rule_id == "P5-M1"
    assert judge_session(method, None).rule_id == "P5-M2"

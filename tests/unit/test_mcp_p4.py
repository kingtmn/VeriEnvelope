"""Pilot #4 judgments read labels from the method. No container."""

import copy
import inspect

import pytest

from verienvelope.errors import VeriEnvelopeError
from verienvelope.mcp_p4 import (
    expected_substring,
    judge_convert,
    judge_discovery,
    judge_session,
    load_method,
    rule_table,
)


SUBSTRING = '  "time_difference": "+9.0h"'


def _session(name: str = "mcp-time", version: str = "1.29.0", protocol: str = "2025-03-26") -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": protocol,
            "serverInfo": {"name": name, "version": version},
        },
    }


def _convert_message(text: str, is_error: bool = False) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 3,
        "result": {"content": [{"type": "text", "text": text}], "isError": is_error},
    }


def test_time_method_pins_the_conversion():
    method = load_method()
    assert method["version"] == "0.1.0"
    assert method["identity"]["commit"] == "f46d9578190b476b3501923ea8977d899e8db2cb"
    assert method["execution"]["sandbox_policy"] == "ADR-008-amendment-3"
    assert method["execution"]["local_image_id"].startswith("sha256:")
    assert method["execution"]["tzdata_version"] == "2024.2"
    assert expected_substring(method) == SUBSTRING
    assert method["execution"]["arguments"] == {
        "source_timezone": "UTC",
        "time": "12:00",
        "target_timezone": "Asia/Tokyo",
    }


def test_every_selected_rule_has_a_capability_status():
    table = rule_table(load_method())
    assert set(table) >= {
        "P4-M1",
        "P4-M2",
        "P4-M3",
        "P4-M4",
        "P4-M5",
        "P4-M7",
        "P4-M8",
        "P4-M9",
        "P4-M10",
        "P4-M11",
    }
    assert "P4-M6" not in table


def test_a_rule_without_capability_status_cannot_load():
    method = copy.deepcopy(load_method())
    for item in method["classification_rules"]:
        if item["id"] == "P4-M7":
            del item["capability_status"]
    with pytest.raises(VeriEnvelopeError, match="P4-M7"):
        rule_table(method)


def test_p4_m7_status_comes_from_the_method():
    method = load_method()
    text = '{\n  "time_difference": "+9.0h"\n}'
    judgment = judge_convert(method, _convert_message(text), SUBSTRING)
    rule = next(item for item in method["classification_rules"] if item["id"] == "P4-M7")
    assert judgment.rule_id == "P4-M7"
    assert judgment.observation == rule["observation"]
    assert judgment.outcome_class == rule["outcome_class"]
    assert judgment.capability_status == rule["capability_status"]
    assert judgment.note == rule["run_note"]
    assert '"demonstrated"' not in inspect.getsource(judge_convert)
    assert '"demonstrated"' not in inspect.getsource(judge_session)


def test_runner_follows_a_replaced_method_status():
    method = copy.deepcopy(load_method())
    for item in method["classification_rules"]:
        if item["id"] == "P4-M7":
            item["capability_status"] = "unknown"
    judgment = judge_convert(method, _convert_message('{\n  "time_difference": "+9.0h"\n}'), SUBSTRING)
    assert judgment.observation == "match"
    assert judgment.outcome_class == "confirmed"
    assert judgment.capability_status == "unknown"


def test_a_different_difference_uses_the_mismatch_rule():
    method = load_method()
    judgment = judge_convert(method, _convert_message('  "time_difference": "+0.0h"'), SUBSTRING)
    rule = next(item for item in method["classification_rules"] if item["id"] == "P4-M8")
    assert judgment.rule_id == "P4-M8"
    assert judgment.capability_status == rule["capability_status"]


def test_an_error_flag_does_not_match_the_success_rule():
    method = load_method()
    judgment = judge_convert(
        method,
        _convert_message('  "time_difference": "+9.0h"', is_error=True),
        SUBSTRING,
    )
    assert judgment.rule_id == "P4-M8"


def test_discovery_accepts_extra_tool_names():
    method = load_method()
    message = {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {"tools": [{"name": "get_current_time"}, {"name": "convert_time"}]},
    }
    judgment = judge_discovery(method, message)
    assert judgment.rule_id == "P4-M4"


def test_session_requires_the_method_server_identity():
    method = load_method()
    assert judge_session(method, _session()).rule_id == "P4-M1"
    assert judge_session(method, _session(name="other")).rule_id == "P4-M3"
    assert judge_session(method, _session(version="0")).rule_id == "P4-M3"
    assert judge_session(method, None).rule_id == "P4-M2"

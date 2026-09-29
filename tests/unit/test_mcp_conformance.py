import json

import yaml

from tests.paths import ROOT
from verienvelope.artifact_identity import (
    ARTIFACT_ORIGIN,
    BUILD_TIMESTAMP,
    LOCAL_IMAGE_ID,
    PACKAGE_VERSION,
    REGISTRY_DIGEST,
    SOURCE_COMMIT,
    source_identity,
)
from verienvelope.mcp_protocol import (
    CLIENT_NAME,
    CLIENT_VERSION,
    ECHO_MESSAGE,
    ECHO_TEXT,
    ECHO_TOOL,
    EVERYTHING_SERVER_NAME,
    EVERYTHING_SERVER_VERSION,
    EVERYTHING_TOOLS,
    PROTOCOL_VERSION,
    initialize_request,
    judge_echo,
    judge_initialize,
    tools_call_echo_request,
)
from verienvelope.pilot_preflight import (
    ExecutionFacts,
    checklist,
    gate_ready,
    load_execution_facts,
)

GOLDEN_PATH = ROOT / "tests" / "golden" / "ve_method_mcp_001.json"
METHOD_PATH = ROOT / "methods" / "VE-METHOD-MCP-001" / "method.yaml"


def _golden() -> dict:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def _method() -> dict:
    return yaml.safe_load(METHOD_PATH.read_text(encoding="utf-8"))


def test_method_matches_independent_golden() -> None:
    golden = _golden()
    method = _method()
    assert method["id"] == golden["method_id"]
    assert str(method["version"]) == golden["method_version"]
    assert method["client_handshake"]["protocol_version_offered"] == golden["protocol_version_offered"]
    assert method["client_handshake"]["client_info"]["name"] == golden["client_name"]
    assert method["client_handshake"]["client_info"]["version"] == golden["client_version"]
    assert method["identity"]["server_name"] == golden["server_name"]
    assert method["identity"]["server_version"] == golden["server_version"]
    assert method["claims"][1]["unconditional_tools"] == golden["tools"]
    echo = method["claims"][2]
    assert echo["tool"] == golden["echo_tool"]
    assert echo["arguments"]["message"] == golden["echo_message"]
    assert golden["echo_text"] in echo["expected_observation"]
    rules = {item["id"]: item for item in method["classification_rules"]}
    for rule_id in ("M2", "M4", "M6", "M9"):
        assert rules[rule_id]["outcome_class"] == golden["mismatch_outcome_class"]
        assert rules[rule_id]["capability_status"] == golden["mismatch_capability_status"]
    assert rules["M2"]["observation"] == golden["initialize_error_observation"]
    assert rules["M4"]["observation"] == "mismatch"
    assert rules["M6"]["observation"] == "mismatch"
    assert golden["protocol_version_offered"] in method["claims"][0]["expected_observation"]
    assert "mcp-servers/everything" in method["claims"][0]["expected_observation"]
    assert rules["M10"]["observation"] == golden["protocol_mismatch_observation"]
    assert rules["M10"]["outcome_class"] == golden["mismatch_outcome_class"]
    assert rules["M10"]["capability_status"] == golden["mismatch_capability_status"]
    assert golden["artifact_origin"] in method["assurance"]["provenance"]
    assert golden["local_image_id"] in method["assurance"]["provenance"]
    assert "npm registry" in method["assurance"]["provenance"]


def test_executor_matches_independent_golden_not_the_method_file() -> None:
    golden = _golden()
    assert PROTOCOL_VERSION == golden["protocol_version_offered"]
    assert CLIENT_NAME == golden["client_name"]
    assert CLIENT_VERSION == golden["client_version"]
    assert EVERYTHING_SERVER_NAME == golden["server_name"]
    assert EVERYTHING_SERVER_VERSION == golden["server_version"]
    assert list(EVERYTHING_TOOLS) == golden["tools"]
    assert ECHO_TOOL == golden["echo_tool"]
    assert ECHO_MESSAGE == golden["echo_message"]
    assert ECHO_TEXT == golden["echo_text"]
    request = initialize_request()
    assert request["id"] == golden["initialize_request_id"]
    assert request["params"]["protocolVersion"] == golden["protocol_version_offered"]
    assert request["params"]["capabilities"] == {}
    assert request["params"]["clientInfo"]["name"] == golden["client_name"]
    call = tools_call_echo_request()
    assert call["params"]["name"] == golden["echo_tool"]
    assert call["params"]["arguments"]["message"] == golden["echo_message"]
    matched = judge_initialize(
        {
            "jsonrpc": "2.0",
            "id": golden["initialize_request_id"],
            "result": {
                "protocolVersion": golden["protocol_version_offered"],
                "serverInfo": {
                    "name": golden["server_name"],
                    "version": golden["server_version"],
                },
            },
        },
        expected_name=golden["server_name"],
        expected_version=golden["server_version"],
        expected_protocol=golden["protocol_version_offered"],
        expected_id=golden["initialize_request_id"],
    )
    assert matched.observation == "match"
    assert matched.outcome_class == "confirmed"
    wrong_protocol = judge_initialize(
        {
            "jsonrpc": "2.0",
            "id": golden["initialize_request_id"],
            "result": {
                "protocolVersion": "1999-01-01",
                "serverInfo": {
                    "name": golden["server_name"],
                    "version": golden["server_version"],
                },
            },
        },
        expected_name=golden["server_name"],
        expected_version=golden["server_version"],
        expected_protocol=golden["protocol_version_offered"],
        expected_id=golden["initialize_request_id"],
    )
    assert wrong_protocol.observation == golden["protocol_mismatch_observation"]
    assert wrong_protocol.rule_id == golden["protocol_mismatch_rule"]
    assert wrong_protocol.outcome_class == golden["mismatch_outcome_class"]
    assert wrong_protocol.capability_status == golden["mismatch_capability_status"]
    assert wrong_protocol.outcome_class != "component_failure"
    missing_protocol = judge_initialize(
        {
            "jsonrpc": "2.0",
            "id": golden["initialize_request_id"],
            "result": {
                "serverInfo": {
                    "name": golden["server_name"],
                    "version": golden["server_version"],
                }
            },
        },
        expected_name=golden["server_name"],
        expected_version=golden["server_version"],
        expected_protocol=golden["protocol_version_offered"],
        expected_id=golden["initialize_request_id"],
    )
    assert missing_protocol.observation == golden["protocol_mismatch_observation"]
    assert missing_protocol.capability_status == golden["mismatch_capability_status"]
    assert missing_protocol.outcome_class == golden["mismatch_outcome_class"]
    mismatched = judge_echo(
        {"result": {"content": [{"type": "text", "text": "Echo: other"}], "extra": True}},
        expected_text=golden["echo_text"],
    )
    assert mismatched.observation == "mismatch"
    assert mismatched.outcome_class == golden["mismatch_outcome_class"]
    assert mismatched.capability_status == golden["mismatch_capability_status"]
    extra = judge_echo(
        {
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": golden["echo_text"],
                        "annotations": {"audience": ["user"]},
                    }
                ],
                "_fixtureExtra": {"ignored": True},
            }
        },
        expected_text=golden["echo_text"],
    )
    assert extra.observation == "match"


def test_artifact_identity_is_not_an_npm_release() -> None:
    golden = _golden()
    identity = source_identity()
    assert identity["package_version"] == PACKAGE_VERSION == golden["server_version"]
    assert identity["package_version_meaning"] == golden["package_version_meaning"]
    assert identity["source_commit"] == SOURCE_COMMIT
    assert ARTIFACT_ORIGIN == golden["artifact_origin"]
    assert LOCAL_IMAGE_ID == golden["local_image_id"]
    assert REGISTRY_DIGEST is golden["registry_digest"]
    record = json.loads(
        (ROOT / "registry" / "candidates" / "everything-build.json").read_text(encoding="utf-8")
    )
    assert record["source_identity"]["package_version_meaning"] == golden["package_version_meaning"]
    assert record["execution_artifact"]["artifact_origin"] == golden["artifact_origin"]
    assert record["execution_artifact"]["local_image_id"] == golden["local_image_id"]
    assert record["execution_artifact"]["registry_digest"] is None
    assert record["execution_artifact"]["build_timestamp"] == BUILD_TIMESTAMP
    assert record["image_digest"] == golden["local_image_id"]


def test_gate_stays_closed_without_an_image_digest() -> None:
    facts = ExecutionFacts(
        executor_implemented=True,
        fixture_validated=True,
        evidence_path_validated=True,
        image_built=True,
        image_digest=None,
        execution_contradiction=False,
    )
    assert gate_ready(facts) is False
    numbers = [item.number for item in checklist(facts)]
    assert numbers == list(range(1, 23))


def test_gate_stays_closed_when_the_fixture_self_test_is_not_validated() -> None:
    facts = ExecutionFacts(
        executor_implemented=True,
        fixture_validated=False,
        evidence_path_validated=True,
        image_built=True,
        image_digest="sha256:" + "ab" * 32,
        execution_contradiction=False,
    )
    assert gate_ready(facts) is False


def test_missing_build_record_is_not_ready() -> None:
    facts = load_execution_facts(ROOT / "registry" / "candidates" / "missing-build.json")
    assert gate_ready(facts) is False

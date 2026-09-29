"""C2 selection and gating. These tests do not start Everything."""

import json

from verienvelope.artifact_identity import LOCAL_IMAGE_ID
from verienvelope.mcp_c2 import RUN1_EVIDENCE, c2_exchange
from verienvelope.mcp_protocol import (
    EVERYTHING_TOOLS,
    encode_message,
    name_diff,
    select_response,
)
from verienvelope.pilot_preflight import gate_open, load_run_authorization, run_authorized
from verienvelope.sandbox import split_container_env

NOTE = b'{"jsonrpc":"2.0","method":"notifications/message","params":{"level":"info"}}\n'


class _Lines:
    def __init__(self, lines: list[bytes]) -> None:
        self.lines = list(lines)
        self.written: list[bytes] = []

    def write(self, payload: bytes) -> None:
        self.written.append(payload)

    def read(self, _timeout: float) -> bytes:
        if not self.lines:
            return b""
        return self.lines.pop(0)


def _initialize() -> bytes:
    return encode_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {"listChanged": True}},
                "instructions": "not part of C1",
                "serverInfo": {
                    "name": "mcp-servers/everything",
                    "title": "Everything Reference Server",
                    "version": "2.0.0",
                },
            },
        }
    )


def _tools(names: list[str]) -> bytes:
    return encode_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {
                        "name": name,
                        "description": "ignored",
                        "inputSchema": {"type": "object"},
                    }
                    for name in names
                ]
            },
        }
    )


def _methods(payloads: list[bytes]) -> list[str]:
    return [json.loads(payload)["method"] for payload in payloads]


def test_notification_does_not_hide_the_matching_id() -> None:
    other = encode_message({"jsonrpc": "2.0", "id": 9, "result": {"tools": []}})
    selected = select_response([NOTE, other, _tools(["echo"])], 2)
    assert selected.matched is not None
    assert selected.matched["id"] == 2
    assert selected.matched["result"]["tools"][0]["name"] == "echo"
    assert [item["kind"] for item in selected.unmatched] == ["unmatched", "unmatched"]


def test_image_env_is_recorded_apart_from_the_process() -> None:
    split = split_container_env(
        (
            "PATH=/usr/bin",
            "LANG=C",
            "NODE_VERSION=22.12.0",
            "YARN_VERSION=1.22.22",
        )
    )
    assert split["host_inheritance"] == "none"
    assert split["image_defined_env"] == [
        "NODE_VERSION=22.12.0",
        "YARN_VERSION=1.22.22",
    ]
    assert "NODE_VERSION" not in split["process_env_names"]


def test_run2_authorization_is_not_the_shared_checklist() -> None:
    assert gate_open() is True
    current = load_run_authorization()
    assert current is not None
    assert current["authorized"] is True
    assert run_authorized(current, consumed=frozenset()) is True
    assert run_authorized(current) is False
    assert current["planned_run"] == "external-run-2"
    assert current["primary_claim"] == "C2"
    assert current["previous_run"]["planned_run"] == "external-run-1"
    assert current["previous_run"]["status"] == "completed"
    closed = dict(current)
    closed["execution_artifact"] = "sha256:" + "ab" * 32
    assert run_authorized(closed) is False
    assert run_authorized({"authorized": True, "planned_run": "external-run-1"}) is False
    assert LOCAL_IMAGE_ID == current["execution_artifact"]


def test_prerequisite_failure_does_not_send_tools_list() -> None:
    session = _Lines(
        [
            encode_message(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "error": {"code": -32603, "message": "no"},
                }
            )
        ]
    )
    outcome = c2_exchange(
        session.write,
        session.read,
        expected_name="mcp-servers/everything",
        expected_version="2.0.0",
        expected_tools=frozenset(EVERYTHING_TOOLS),
        timeout=5,
    )
    assert _methods(session.written) == ["initialize"]
    assert outcome.measured is False
    assert outcome.primary.capability_status == "insufficient"
    assert outcome.primary.observation == "not_run"
    assert outcome.primary.outcome_class == "unclassified"
    assert outcome.prerequisite.observation == "execution_error"
    assert "tools/call" not in _methods(session.written)


def test_prerequisite_success_sends_tools_list_and_ignores_extra_fields() -> None:
    names = list(reversed(EVERYTHING_TOOLS))
    session = _Lines([_initialize(), NOTE, _tools(names)])
    outcome = c2_exchange(
        session.write,
        session.read,
        expected_name="mcp-servers/everything",
        expected_version="2.0.0",
        expected_tools=frozenset(EVERYTHING_TOOLS),
        timeout=5,
    )
    assert _methods(session.written) == [
        "initialize",
        "notifications/initialized",
        "tools/list",
    ]
    assert outcome.prerequisite.observation == "match"
    assert outcome.primary.observation == "match"
    assert outcome.primary.capability_status == "demonstrated"
    assert outcome.primary.outcome_class == "confirmed"
    assert outcome.names["missing"] == []
    assert outcome.names["unexpected"] == []
    assert outcome.unmatched
    assert RUN1_EVIDENCE.startswith("mcp.server-everything/")


def test_missing_and_extra_names_are_differences_not_causes() -> None:
    short = [name for name in EVERYTHING_TOOLS if name != "echo"]
    session = _Lines([_initialize(), _tools(short)])
    missing = c2_exchange(
        session.write,
        session.read,
        expected_name="mcp-servers/everything",
        expected_version="2.0.0",
        expected_tools=frozenset(EVERYTHING_TOOLS),
        timeout=5,
    )
    assert missing.primary.observation == "mismatch"
    assert missing.primary.capability_status == "not_demonstrated"
    assert missing.primary.outcome_class == "unclassified"
    assert missing.names["missing"] == ["echo"]
    assert missing.names["unexpected"] == []
    extra_names = list(EVERYTHING_TOOLS) + ["extra-tool"]
    extra_session = _Lines([_initialize(), _tools(extra_names)])
    extra = c2_exchange(
        extra_session.write,
        extra_session.read,
        expected_name="mcp-servers/everything",
        expected_version="2.0.0",
        expected_tools=frozenset(EVERYTHING_TOOLS),
        timeout=5,
    )
    assert extra.primary.observation == "mismatch"
    assert extra.names["unexpected"] == ["extra-tool"]
    assert extra.primary.outcome_class != "component_failure"
    described = name_diff(frozenset(EVERYTHING_TOOLS), frozenset(short))
    assert described["missing"] == ["echo"]
    assert "cause" not in described

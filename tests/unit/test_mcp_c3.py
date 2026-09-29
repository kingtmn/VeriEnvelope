"""C3 gating on a fake stdio session. This does not start Everything."""

import json

from verienvelope.mcp_c3 import c3_exchange
from verienvelope.mcp_protocol import ECHO_TEXT, EVERYTHING_TOOLS, encode_message


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


def _methods(payloads: list[bytes]) -> list[str]:
    return [json.loads(payload)["method"] for payload in payloads]


def _initialize() -> bytes:
    return encode_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
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
            "result": {"tools": [{"name": name, "description": "ignored"} for name in names]},
        }
    )


def _echo(text: str, *, extra: bool = False) -> bytes:
    content: dict = {"type": "text", "text": text}
    result: dict = {"content": [content]}
    if extra:
        content["annotations"] = {"audience": ["user"]}
        result["metadata"] = {"ignored": True}
    return encode_message({"jsonrpc": "2.0", "id": 3, "result": result})


def _exchange(lines: list[bytes]):
    session = _Lines(lines)
    outcome = c3_exchange(
        session.write,
        session.read,
        expected_name="mcp-servers/everything",
        expected_version="2.0.0",
        expected_tools=frozenset(EVERYTHING_TOOLS),
        timeout=5,
    )
    return outcome, _methods(session.written)


def test_c1_failure_blocks_tools_list() -> None:
    error = encode_message(
        {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "no"}}
    )
    outcome, methods = _exchange([error, _tools(list(EVERYTHING_TOOLS)), _echo(ECHO_TEXT)])
    assert methods == ["initialize"]
    assert outcome.measured is False
    assert outcome.primary.capability_status == "insufficient"
    assert outcome.primary.observation == "not_run"
    assert outcome.prerequisite_c1.observation == "execution_error"


def test_c2_failure_blocks_tools_call() -> None:
    names = [name for name in EVERYTHING_TOOLS if name != "echo"]
    outcome, methods = _exchange([_initialize(), _tools(names), _echo(ECHO_TEXT)])
    assert methods == ["initialize", "notifications/initialized", "tools/list"]
    assert "tools/call" not in methods
    assert outcome.prerequisite_c1.observation == "match"
    assert outcome.prerequisite_c2.observation == "mismatch"
    assert outcome.primary.capability_status == "insufficient"
    assert outcome.primary.observation == "not_run"
    assert outcome.measured is False


def test_exact_echo_text_matches_and_extra_fields_do_not_add_a_claim() -> None:
    note = b'{"jsonrpc":"2.0","method":"notifications/tools/list_changed"}\n'
    names = list(reversed(EVERYTHING_TOOLS))
    outcome, methods = _exchange(
        [_initialize(), note, _tools(names), note, _echo(ECHO_TEXT, extra=True)]
    )
    assert methods == [
        "initialize",
        "notifications/initialized",
        "tools/list",
        "tools/call",
    ]
    assert outcome.prerequisite_c1.observation == "match"
    assert outcome.prerequisite_c2.observation == "match"
    assert outcome.primary.observation == "match"
    assert outcome.primary.capability_status == "demonstrated"
    assert outcome.primary.claim_id == "C3"
    assert outcome.primary.rule_id == "M5"
    assert outcome.unmatched


def test_wrong_echo_text_is_a_mismatch() -> None:
    outcome, methods = _exchange(
        [_initialize(), _tools(list(EVERYTHING_TOOLS)), _echo("Echo: something-else")]
    )
    assert methods[-1] == "tools/call"
    assert outcome.primary.observation == "mismatch"
    assert outcome.primary.capability_status == "not_demonstrated"
    assert outcome.primary.outcome_class == "unclassified"
    assert outcome.primary.rule_id == "M6"

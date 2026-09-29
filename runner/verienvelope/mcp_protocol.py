"""Minimal newline-delimited JSON-RPC for the four Pilot #1 messages.

The official MCP SDK is a TypeScript package. Using it here would require a
host or image install of that SDK, and the instrument would then be judging
the SDK's framing as well as the server. Pilot #1 only sends initialize,
notifications/initialized, tools/list, and tools/call. Those four messages
fit in the standard library. This module does not speak to Everything.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Callable

PROTOCOL_VERSION = "2025-03-26"
CLIENT_NAME = "verienvelope-pilot"
CLIENT_VERSION = "0.1.0"
ECHO_TOOL = "echo"
ECHO_MESSAGE = "verienvelope-pilot-echo"
ECHO_TEXT = "Echo: verienvelope-pilot-echo"

# Independent of method.yaml. tests/golden compares this constant to the golden file.
EVERYTHING_SERVER_NAME = "mcp-servers/everything"
EVERYTHING_SERVER_VERSION = "2.0.0"
EVERYTHING_TOOLS = (
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
)


@dataclass(frozen=True)
class ClaimJudgment:
    claim_id: str
    rule_id: str
    observation: str
    outcome_class: str
    capability_status: str
    note: str


def initialize_request() -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": CLIENT_NAME, "version": CLIENT_VERSION},
        },
    }


def initialized_notification() -> dict[str, Any]:
    return {"jsonrpc": "2.0", "method": "notifications/initialized"}


def tools_list_request() -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}


def tools_call_echo_request(message: str = ECHO_MESSAGE) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": ECHO_TOOL, "arguments": {"message": message}},
    }


def encode_message(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"


def parse_message(line: bytes) -> dict[str, Any] | None:
    text = line.decode("utf-8", errors="replace").strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def judge_initialize(
    message: dict[str, Any] | None,
    *,
    expected_name: str,
    expected_version: str,
    expected_protocol: str = PROTOCOL_VERSION,
    expected_id: int = 1,
    malformed: bool = False,
) -> ClaimJudgment:
    if malformed or message is None:
        return _c1_unparsed()
    if message.get("jsonrpc") != "2.0" or message.get("id") != expected_id:
        return _c1_unparsed()
    if "error" in message:
        return _c1_unparsed()
    result = message.get("result")
    if not isinstance(result, dict):
        return _c1_unparsed()
    if result.get("protocolVersion") != expected_protocol:
        return ClaimJudgment(
            "C1",
            "M10",
            "mismatch",
            "unclassified",
            "not_demonstrated",
            "C1 的 protocolVersion 没有被 demonstrated。原因未归类。",
        )
    info = result.get("serverInfo")
    if not isinstance(info, dict):
        return _c1_unparsed()
    if info.get("name") != expected_name or info.get("version") != expected_version:
        return ClaimJudgment(
            "C1",
            "M9",
            "mismatch",
            "unclassified",
            "not_demonstrated",
            "C1 的 serverInfo 与预期不一致。原因未归类。",
        )
    return ClaimJudgment(
        "C1",
        "M1",
        "match",
        "confirmed",
        "demonstrated",
        "C1 的 protocolVersion 与 serverInfo 符合固定握手。",
    )


def _c1_unparsed() -> ClaimJudgment:
    return ClaimJudgment(
        "C1",
        "M2",
        "execution_error",
        "unclassified",
        "not_demonstrated",
        "C1 没有被 demonstrated。原因未归类。",
    )


def judge_tools(
    message: dict[str, Any] | None,
    *,
    expected_names: frozenset[str],
) -> ClaimJudgment:
    names = _tool_names(message)
    if names is None:
        return ClaimJudgment(
            "C2",
            "M2",
            "execution_error",
            "unclassified",
            "not_demonstrated",
            "C2 没有可解析的 tools/list。原因未归类。",
        )
    if names != expected_names:
        return ClaimJudgment(
            "C2",
            "M4",
            "mismatch",
            "unclassified",
            "not_demonstrated",
            "C2 没有被 demonstrated。原因未归类。",
        )
    return ClaimJudgment(
        "C2",
        "M3",
        "match",
        "confirmed",
        "demonstrated",
        "C2 与固定工具名集合一致。",
    )


def judge_echo(
    message: dict[str, Any] | None,
    *,
    expected_text: str,
) -> ClaimJudgment:
    texts = _text_values(message)
    if texts is None:
        return ClaimJudgment(
            "C3",
            "M2",
            "execution_error",
            "unclassified",
            "not_demonstrated",
            "C3 没有可解析的 tools/call 文本。原因未归类。",
        )
    if expected_text not in texts:
        return ClaimJudgment(
            "C3",
            "M6",
            "mismatch",
            "unclassified",
            "not_demonstrated",
            "C3 没有被 demonstrated。原因未归类。",
        )
    return ClaimJudgment(
        "C3",
        "M5",
        "match",
        "confirmed",
        "demonstrated",
        "C3 只证明这一条 echo 文本。",
    )


@dataclass(frozen=True)
class SelectedResponse:
    matched: dict[str, Any] | None
    unmatched: tuple[dict[str, Any], ...]
    raw: bytes
    closed: bool


def select_response(lines: list[bytes], request_id: int) -> SelectedResponse:
    """Pick the JSON-RPC response with this id. Other messages stay unmatched."""
    unmatched: list[dict[str, Any]] = []
    raw = bytearray()
    for line in lines:
        raw.extend(line)
        if line == b"":
            return SelectedResponse(None, tuple(unmatched), bytes(raw), True)
        parsed = parse_message(line)
        if parsed is None:
            unmatched.append(
                {
                    "kind": "malformed",
                    "raw": line.decode("utf-8", errors="replace"),
                }
            )
            continue
        if parsed.get("id") == request_id and ("result" in parsed or "error" in parsed):
            return SelectedResponse(parsed, tuple(unmatched), bytes(raw), False)
        unmatched.append({"kind": "unmatched", "message": parsed})
    return SelectedResponse(None, tuple(unmatched), bytes(raw), False)


def read_until_response(
    read_line: Callable[[float], bytes],
    request_id: int,
    timeout: float,
) -> SelectedResponse:
    deadline = time.monotonic() + timeout
    lines: list[bytes] = []
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired("json-rpc", timeout)
        line = read_line(remaining)
        lines.append(line)
        selected = select_response(lines, request_id)
        if selected.matched is not None or line == b"":
            return selected


def name_diff(
    expected: frozenset[str],
    actual: frozenset[str] | None,
) -> dict[str, Any]:
    """Set difference only. It does not say why a name is absent or extra."""
    if actual is None:
        return {
            "expected": sorted(expected),
            "actual": None,
            "missing": None,
            "unexpected": None,
        }
    return {
        "expected": sorted(expected),
        "actual": sorted(actual),
        "missing": sorted(expected - actual),
        "unexpected": sorted(actual - expected),
    }


def judge_timeout() -> ClaimJudgment:
    return ClaimJudgment(
        "C1",
        "M7",
        "execution_error",
        "unclassified",
        "insufficient",
        "超时本身不能分成服务器、运行时或方法的错。",
    )


def judge_exit() -> ClaimJudgment:
    return ClaimJudgment(
        "C1",
        "M2",
        "execution_error",
        "unclassified",
        "not_demonstrated",
        "进程在响应前退出。C1 没有被 demonstrated。原因未归类。",
    )


def _tool_names(message: dict[str, Any] | None) -> frozenset[str] | None:
    if message is None or "error" in message:
        return None
    result = message.get("result")
    if not isinstance(result, dict):
        return None
    tools = result.get("tools")
    if not isinstance(tools, list):
        return None
    names: list[str] = []
    for item in tools:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            return None
        names.append(item["name"])
    return frozenset(names)


def _text_values(message: dict[str, Any] | None) -> set[str] | None:
    if message is None or "error" in message:
        return None
    result = message.get("result")
    if not isinstance(result, dict):
        return None
    content = result.get("content")
    if not isinstance(content, list):
        return None
    texts: set[str] = set()
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
            texts.add(item["text"])
    return texts

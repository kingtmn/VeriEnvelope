"""Line-delimited JSON-RPC stand-in for calibrating the MCP instrument.

This process is not an external component. It implements only initialize,
notifications/initialized, tools/list, and tools/call for the echo tool.
"""

from __future__ import annotations

import json
import sys
import time

SERVER_NAME = "verienvelope.mcp-fixture"
SERVER_VERSION = "0.0.0"


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else "normal"
    if mode == "exit_early":
        return 3
    if mode == "timeout":
        time.sleep(60)
        return 0

    name = SERVER_NAME
    if mode == "server_info_mismatch":
        name = "verienvelope.mcp-fixture-wrong"
    tool_names = ["echo", "extra-tool"] if mode == "tools_mismatch" else ["echo"]

    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(message, dict):
            continue
        method = message.get("method")
        message_id = message.get("id")
        if method == "initialize":
            if mode == "malformed":
                sys.stdout.write("NOT-JSON\n")
                sys.stdout.flush()
                return 0
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": name, "version": SERVER_VERSION},
                    },
                }
            )
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {
                        "tools": [
                            {
                                "name": tool_name,
                                "description": "fixture",
                                "inputSchema": {"type": "object"},
                            }
                            for tool_name in tool_names
                        ]
                    },
                }
            )
        elif method == "tools/call":
            params = message.get("params") if isinstance(message.get("params"), dict) else {}
            arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            text = f"Echo: {arguments.get('message', '')}"
            if mode == "echo_mismatch":
                text = "Echo: WRONG"
            content: dict[str, object] = {"type": "text", "text": text}
            result: dict[str, object] = {"content": [content]}
            if mode == "extra_metadata":
                content["annotations"] = {"audience": ["user"]}
                result["isError"] = False
                result["_fixtureExtra"] = {"ignored": True}
            _send({"jsonrpc": "2.0", "id": message_id, "result": result})
        elif message_id is not None:
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {"code": -32601, "message": "method not found"},
                }
            )
    return 0


def _send(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

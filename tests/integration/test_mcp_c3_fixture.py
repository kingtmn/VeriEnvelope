"""C3 session behavior on the controlled fixture. Not an Everything run."""

import json
from pathlib import Path

from verienvelope.mcp_c3 import RUN1_EVIDENCE, RUN2_EVIDENCE, run_c3_case
from verienvelope.mcp_instrument import FIXTURE_ID, FIXTURE_VERSION, fixture_image_id
from verienvelope.mcp_protocol import ECHO_TEXT
from verienvelope.package_seal import check_package_seal


def _component() -> dict:
    return {
        "id": FIXTURE_ID,
        "name": "Controlled MCP fixture",
        "component_type": "mcp_server",
        "description": "量具。不是外部组件。",
        "source_repository": "file://verienvelope/methods/VE-METHOD-MCP-001/fixtures/controlled_stdio.py",
        "version": FIXTURE_VERSION,
        "status": "candidate",
    }


def _run(tmp_path: Path, mode: str, tools: frozenset[str]):
    return run_c3_case(
        image=fixture_image_id(),
        command=["python", "-u", "/opt/ve-fixture/controlled_stdio.py", mode],
        output_root=tmp_path,
        expected_name=FIXTURE_ID,
        expected_version=FIXTURE_VERSION,
        expected_tools=tools,
        record_purpose="instrument_self_test",
        component=_component(),
    )


def test_fixture_c3_seals_a_separate_package(tmp_path: Path) -> None:
    result = _run(tmp_path, "normal", frozenset({"echo"}))
    assert result["evidence_dir"] not in {RUN1_EVIDENCE, RUN2_EVIDENCE}
    assert result["observation"] == "match"
    assert result["admission"] == "insufficient"
    assert [item["capability_id"] for item in result["capabilities"]] == ["C1", "C2", "C3"]
    assert all(item["status"] == "demonstrated" for item in result["capabilities"])
    assert all(item["envelope"]["known_limits"] == [] for item in result["capabilities"])
    assert "C4" not in {item["capability_id"] for item in result["capabilities"]}
    package = tmp_path / result["evidence_dir"]
    sent = json.loads((package / "input" / "case.json").read_text(encoding="utf-8"))
    assert sent["messages_sent"] == [
        "initialize",
        "notifications/initialized",
        "tools/list",
        "tools/call",
    ]
    assert b"tools/call" in (package / "input" / "tools-call.request.log").read_bytes()
    assert ECHO_TEXT.encode("utf-8") in (package / "input" / "tools-call.response.log").read_bytes()
    assert check_package_seal(package) == []
    html_source = (package / "result.json").read_text(encoding="utf-8")
    assert "声明范围" not in html_source


def test_fixture_c1_mismatch_does_not_list_tools(tmp_path: Path) -> None:
    result = _run(tmp_path, "server_info_mismatch", frozenset({"echo"}))
    assert result["observation"] == "not_run"
    assert result["capabilities"][0]["capability_id"] == "C3"
    assert result["capabilities"][0]["status"] == "insufficient"
    package = tmp_path / result["evidence_dir"]
    case = json.loads((package / "input" / "case.json").read_text(encoding="utf-8"))
    assert case["messages_sent"] == ["initialize"]
    assert case["prerequisite_c1"]["observation"] == "mismatch"
    assert (package / "input" / "tools-list.request.log").read_bytes() == b""
    assert (package / "input" / "tools-call.request.log").read_bytes() == b""
    assert check_package_seal(package) == []


def test_fixture_c2_mismatch_does_not_call_echo(tmp_path: Path) -> None:
    result = _run(tmp_path, "tools_mismatch", frozenset({"echo"}))
    assert result["observation"] == "not_run"
    assert result["capabilities"][0]["status"] == "insufficient"
    package = tmp_path / result["evidence_dir"]
    case = json.loads((package / "input" / "case.json").read_text(encoding="utf-8"))
    assert case["messages_sent"] == ["initialize", "notifications/initialized", "tools/list"]
    assert "tools/call" not in case["messages_sent"]
    assert case["prerequisite_c1"]["observation"] == "match"
    assert case["prerequisite_c2"]["observation"] == "mismatch"
    assert (package / "input" / "tools-call.request.log").read_bytes() == b""
    assert check_package_seal(package) == []

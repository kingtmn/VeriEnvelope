"""C2 session behavior on the controlled fixture. Not an Everything run."""

import json
from pathlib import Path

from verienvelope.mcp_c2 import RUN1_EVIDENCE, run_c2_case
from verienvelope.mcp_instrument import FIXTURE_ID, FIXTURE_VERSION, fixture_image_id
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


def test_fixture_c2_seals_a_separate_package(tmp_path: Path) -> None:
    result = run_c2_case(
        image=fixture_image_id(),
        command=["python", "-u", "/opt/ve-fixture/controlled_stdio.py", "normal"],
        output_root=tmp_path,
        expected_name=FIXTURE_ID,
        expected_version=FIXTURE_VERSION,
        expected_tools=frozenset({"echo"}),
        record_purpose="instrument_self_test",
        component=_component(),
    )
    assert result["evidence_dir"] != RUN1_EVIDENCE
    assert result["run_id"] not in RUN1_EVIDENCE
    assert result["observation"] == "match"
    assert result["admission"] == "insufficient"
    assert result["capabilities"][0]["capability_id"] == "C2"
    assert result["capabilities"][1]["capability_id"] == "C3"
    assert result["capabilities"][1]["status"] == "insufficient"
    package = tmp_path / result["evidence_dir"]
    case = json.loads((package / "input" / "case.json").read_text(encoding="utf-8"))
    assert case["primary_claim"] == "C2"
    assert case["messages_sent"] == [
        "initialize",
        "notifications/initialized",
        "tools/list",
    ]
    assert case["messages_not_sent"] == ["tools/call"]
    assert b"tools/call" not in (package / "input" / "tools-list.request.log").read_bytes()
    assert check_package_seal(package) == []


def test_fixture_prerequisite_mismatch_blocks_tools_list(tmp_path: Path) -> None:
    result = run_c2_case(
        image=fixture_image_id(),
        command=["python", "-u", "/opt/ve-fixture/controlled_stdio.py", "server_info_mismatch"],
        output_root=tmp_path,
        expected_name=FIXTURE_ID,
        expected_version=FIXTURE_VERSION,
        expected_tools=frozenset({"echo"}),
        record_purpose="instrument_self_test",
        component=_component(),
    )
    assert result["observation"] == "not_run"
    assert result["capabilities"][0]["status"] == "insufficient"
    package = tmp_path / result["evidence_dir"]
    case = json.loads((package / "input" / "case.json").read_text(encoding="utf-8"))
    assert case["messages_sent"] == ["initialize"]
    assert case["prerequisite_c1"]["observation"] == "mismatch"
    assert (package / "input" / "tools-list.request.log").read_bytes() == b""
    assert check_package_seal(package) == []

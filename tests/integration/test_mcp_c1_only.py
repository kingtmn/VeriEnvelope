"""The initialize-only path stops before tools/list. The subject here is the fixture."""

import json
from pathlib import Path

from verienvelope.artifact_identity import LOCAL_IMAGE_ID
from verienvelope.mcp_c1 import run_initialize_only
from verienvelope.mcp_instrument import FIXTURE_ID, FIXTURE_VERSION, fixture_image_id
from verienvelope.package_seal import check_package_seal


def test_initialize_only_stops_and_seals(tmp_path: Path) -> None:
    image = fixture_image_id()
    assert image != LOCAL_IMAGE_ID
    result = run_initialize_only(
        image=image,
        command=["python", "-u", "/opt/ve-fixture/controlled_stdio.py", "normal"],
        output_root=tmp_path,
        expected_name=FIXTURE_ID,
        expected_version=FIXTURE_VERSION,
        record_purpose="instrument_self_test",
        component={
            "id": FIXTURE_ID,
            "name": "Controlled MCP fixture",
            "component_type": "mcp_server",
            "description": "量具自检。不是外部组件。",
            "source_repository": "file://verienvelope/methods/VE-METHOD-MCP-001/fixtures/controlled_stdio.py",
            "version": FIXTURE_VERSION,
            "status": "candidate",
        },
        fixture_id=FIXTURE_ID,
    )
    assert result["record_purpose"] == "instrument_self_test"
    assert result["component_id"] != "mcp.server-everything"
    assert result["observation"] == "match"
    assert result["capabilities"][0]["capability_id"] == "C1"
    assert result["capabilities"][0]["status"] == "demonstrated"
    assert result["capabilities"][1]["status"] == "insufficient"
    assert result["capabilities"][2]["status"] == "insufficient"
    assert result["admission"] == "insufficient"
    assert result["outcome_class"] != "component_failure"
    package = tmp_path / result["evidence_dir"]
    case = json.loads((package / "input" / "case.json").read_text(encoding="utf-8"))
    assert case["messages_sent"] == ["initialize"]
    assert "tools/list" in case["messages_not_sent"]
    assert "tools/call" in case["messages_not_sent"]
    assert check_package_seal(package) == []
    request = (package / "input" / "request.log").read_bytes()
    assert b"tools/list" not in request
    assert b"initialize" in request

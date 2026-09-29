"""Instrument calibration. The subject is our fixture, not Everything."""

import json
from pathlib import Path

from verienvelope.mcp_instrument import FIXTURE_ID, run_fixture_case
from verienvelope.package_seal import check_package_seal

MODES = {
    "normal": ("match", "confirmed", "demonstrated"),
    "server_info_mismatch": ("mismatch", "unclassified", "not_demonstrated"),
    "tools_mismatch": ("mismatch", "unclassified", "not_demonstrated"),
    "echo_mismatch": ("mismatch", "unclassified", "not_demonstrated"),
    "exit_early": ("execution_error", "unclassified", "not_demonstrated"),
    "malformed": ("execution_error", "unclassified", "not_demonstrated"),
    "extra_metadata": ("match", "confirmed", "demonstrated"),
}


def test_controlled_modes_write_sealed_instrument_records(tmp_path: Path) -> None:
    for mode, (observation, outcome, status) in MODES.items():
        result = run_fixture_case(mode=mode, output_root=tmp_path / mode, timeout_seconds=10)
        assert result["record_purpose"] == "instrument_self_test"
        assert result["component_id"] == FIXTURE_ID
        assert result["component_id"] != "mcp.server-everything"
        assert result["admission"] == "insufficient"
        assert result["observation"] == observation
        assert result["outcome_class"] == outcome
        assert result["capabilities"][-1]["status"] == status
        assert result["outcome_class"] != "component_failure"
        package = tmp_path / mode / result["evidence_dir"]
        assert (package / "seal.json").is_file()
        assert (package / "result.json").is_file()
        assert check_package_seal(package) == []
        stored = json.loads((package / "result.json").read_text(encoding="utf-8"))
        assert stored["record_purpose"] == "instrument_self_test"
        if mode == "normal":
            assert b"Echo: verienvelope-pilot-echo" in (package / "stdout.log").read_bytes()
        if mode == "extra_metadata":
            assert b"Echo: verienvelope-pilot-echo" in (package / "stdout.log").read_bytes()
            assert b"_fixtureExtra" in (package / "stdout.log").read_bytes()


def test_timeout_stays_unclassified_and_cleans_up(tmp_path: Path) -> None:
    result = run_fixture_case(mode="timeout", output_root=tmp_path, timeout_seconds=2)
    assert result["observation"] == "execution_error"
    assert result["outcome_class"] == "unclassified"
    assert result["rule_id"] == "M7"
    assert result["capabilities"][0]["status"] == "insufficient"
    assert result["admission"] == "insufficient"
    package = tmp_path / result["evidence_dir"]
    assert check_package_seal(package) == []

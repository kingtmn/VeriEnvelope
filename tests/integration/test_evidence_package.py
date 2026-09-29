"""Evidence packages produced by the reference runner."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.paths import METHOD, ROOT
from verienvelope.errors import PolicyError
from verienvelope.package_seal import SEALED_PATHS, check_package_seal
from verienvelope.run import run_case
from verienvelope.schema_io import validate_instance

ORACLE = {
    "echo_match.json": ("R1", "match", "confirmed", "demonstrated"),
    "echo_mismatch.json": ("R2", "mismatch", "component_failure", "not_demonstrated"),
    "echo_nonzero.json": ("R3", "execution_error", "component_failure", "not_demonstrated"),
    "timeout.json": ("R4", "execution_error", "unclassified", "insufficient"),
    "secret_probe.json": ("R1", "match", "confirmed", "demonstrated"),
}


def _comparable(result: dict) -> dict:
    return {
        "observation": result["observation"],
        "outcome_class": result["outcome_class"],
        "rule_id": result["rule_id"],
        "admission": result["admission"],
        "record_purpose": result["record_purpose"],
        "capability_status": result["capabilities"][0]["status"],
        "environment_id": result["environment"]["environment_id"],
        "component_commit": result["component_commit"],
        "component_version": result["component_version"],
    }


def test_each_method_case_writes_a_traceable_package(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VE_TEST_SECRET", "ve-test-secret")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "ve-test-secret")
    for name, expected in ORACLE.items():
        out = tmp_path / name
        result = run_case(METHOD, METHOD / "cases" / name, out)
        rule_id, observation, outcome, status = expected
        assert result["rule_id"] == rule_id
        assert result["observation"] == observation
        assert result["outcome_class"] == outcome
        assert result["capabilities"][0]["status"] == status
        assert result["admission"] == "insufficient"
        assert result["record_purpose"] == "pipeline_self_test"
        assert result["component_commit"] is None
        package = out / result["evidence_dir"]
        for filename in (
            "manifest.json",
            "environment.json",
            "result.json",
            "notes.md",
            "stdout.log",
            "stderr.log",
            "seal.json",
        ):
            assert (package / filename).is_file(), filename
        assert (package / "input" / "component.json").is_file()
        assert (package / "input" / "case.json").is_file()
        manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
        stored = json.loads((package / "result.json").read_text(encoding="utf-8"))
        environment = json.loads((package / "environment.json").read_text(encoding="utf-8"))
        validate_instance("evidence.schema.json", manifest)
        validate_instance("verification_result.schema.json", stored)
        assert manifest["observation"] == stored["observation"]
        assert manifest["outcome_class"] == stored["outcome_class"]
        assert manifest["run_id"] == stored["run_id"]
        assert manifest["source_type"] == "ve_test"
        assert manifest["artifacts"]
        listed = {artifact["path"] for artifact in manifest["artifacts"]}
        assert "result.json" not in listed
        assert "notes.md" not in listed
        assert "manifest.json" not in listed
        assert "seal.json" not in listed
        for artifact in manifest["artifacts"]:
            payload = (package / artifact["path"]).read_bytes()
            assert hashlib.sha256(payload).hexdigest() == artifact["sha256"]
            assert ".." not in Path(artifact["path"]).parts
        assert check_package_seal(package) == []
        for relative in SEALED_PATHS:
            assert (package / relative).is_file()
        assert environment == stored["environment"]
        assert environment == manifest["environment"]
        assert "username" not in environment
        assert b"ve-test-secret" not in _package_bytes(package)
        notes = (package / "notes.md").read_text(encoding="utf-8")
        assert "不是组件准入" in notes
        assert stored["history"][0]["previous_state"] is None
        assert stored["history"][0]["new_state"] == stored["outcome_class"]
        assert stored["history"][0]["event_type"] == stored["outcome_class"]


def test_failure_output_is_kept(tmp_path: Path) -> None:
    result = run_case(METHOD, METHOD / "cases" / "echo_mismatch.json", tmp_path)
    package = tmp_path / result["evidence_dir"]
    assert b"mismatch fixture" in (package / "stderr.log").read_bytes()
    assert result["capabilities"][0]["status"] == "not_demonstrated"


def test_repeated_match_is_stable_except_for_run_identity(tmp_path: Path) -> None:
    first = run_case(METHOD, METHOD / "cases" / "echo_match.json", tmp_path / "a")
    second = run_case(METHOD, METHOD / "cases" / "echo_match.json", tmp_path / "b")
    assert _comparable(first) == _comparable(second)
    assert first["run_id"] != second["run_id"]
    assert first["result_id"] != second["result_id"]
    assert first["timestamp"]
    assert first["evidence_refs"] != second["evidence_refs"]


def test_absolute_entrypoint_is_blocked_without_reading_it(tmp_path: Path) -> None:
    case_path = _blocked_case(tmp_path, "/etc/passwd")
    marker = Path("/etc/passwd").read_bytes().splitlines()[0]
    result = run_case(METHOD, case_path, tmp_path / "out")
    package = (tmp_path / "out") / result["evidence_dir"]
    assert result["rule_id"] == "R5"
    assert result["observation"] == "blocked"
    assert result["outcome_class"] == "out_of_envelope"
    assert result["capabilities"][0]["status"] == "insufficient"
    assert not (package / "input" / "entrypoint.py").exists()
    assert marker not in _package_bytes(package)


def test_invalid_timeout_is_an_error_not_a_pass(tmp_path: Path) -> None:
    source = json.loads((METHOD / "cases" / "echo_match.json").read_text(encoding="utf-8"))
    source["case_id"] = "VE-METHOD-001-TIMEOUT-CAP"
    source["timeout_seconds"] = 31
    case_path = tmp_path / "case.json"
    case_path.write_text(json.dumps(source), encoding="utf-8")
    out = tmp_path / "out"
    with pytest.raises(PolicyError):
        run_case(METHOD, case_path, out)
    assert list(out.rglob("result.json")) == []


def test_cli_match_is_not_an_admission(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "runner")
    env["VE_TEST_SECRET"] = "ve-test-secret"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "verienvelope",
            "run",
            "--method",
            str(METHOD),
            "--case",
            str(METHOD / "cases" / "echo_match.json"),
            "--out",
            str(tmp_path),
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "admission=insufficient" in completed.stdout
    assert "record_purpose=pipeline_self_test" in completed.stdout

    mismatch = subprocess.run(
        [
            sys.executable,
            "-m",
            "verienvelope",
            "run",
            "--method",
            str(METHOD),
            "--case",
            str(METHOD / "cases" / "echo_mismatch.json"),
            "--out",
            str(tmp_path / "mismatch"),
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert mismatch.returncode == 1, mismatch.stderr


def test_method_trigger_list_is_copied_into_the_result(tmp_path: Path) -> None:
    method = yaml.safe_load((METHOD / "method.yaml").read_text(encoding="utf-8"))
    result = run_case(METHOD, METHOD / "cases" / "echo_match.json", tmp_path)
    assert result["envelope"]["revalidation_triggers"] == method["envelope"]["revalidation_triggers"]
    assert "component_version=0.0.0" in result["envelope"]["version_constraints"]


def _blocked_case(tmp_path: Path, entrypoint: str) -> Path:
    source = json.loads((METHOD / "cases" / "echo_match.json").read_text(encoding="utf-8"))
    source["case_id"] = "VE-METHOD-001-BLOCKED"
    source["entrypoint"] = entrypoint
    path = tmp_path / "blocked.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    return path


def _package_bytes(package: Path) -> bytes:
    blob = b""
    for path in package.rglob("*"):
        if path.is_file():
            blob += path.read_bytes()
    return blob

"""Run one method case and write an evidence package.

The method file decides what a rule means. This module decides which rule fired
and refuses to emit a result that fails schema or consistency checks.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from verienvelope import __version__
from verienvelope.admission import evaluate_admission
from verienvelope.consistency import assert_consistent
from verienvelope.envelope import claim_envelope_from_run
from verienvelope.errors import MethodError, PolicyError, VeriEnvelopeError
from verienvelope.evidence_integrity import check_evidence_integrity, hash_package_files
from verienvelope.package_seal import check_package_seal, write_package_seal
from verienvelope.history import make_event, new_id, utc_now
from verienvelope.policy import (
    assert_execution_allowed,
    checked_timeout,
    safe_method_path,
    scrubbed_subprocess_env,
)
from verienvelope.rules import IMPLEMENTED_RULE_IDS, rule_table, select_rule_id
from verienvelope.schema_io import dump_json, load_json, load_yaml, validate_instance

RUNNER_NAME = "verienvelope-reference"
_METHOD_KEYS = (
    "id",
    "version",
    "purpose",
    "classification_rules",
    "assurance",
    "envelope",
)
_ASSURANCE_KEYS = (
    "dependencies",
    "permissions",
    "execution_mode",
    "external_services",
    "provenance",
    "reproducibility_notes",
)
_ENVELOPE_KEYS = (
    "tested_conditions",
    "known_limits",
    "untested_areas",
    "version_constraints",
    "revalidation_triggers",
)


@dataclass
class Execution:
    rule_id: str
    stdout: bytes
    stderr: bytes
    exit_code: int | None
    blocked_reason: str | None
    input_files: dict[str, bytes]


def capture_environment() -> dict[str, str]:
    captured = {
        "os": platform.system(),
        "os_release": platform.release(),
        "arch": platform.machine(),
        "python": platform.python_version(),
        "runner_name": RUNNER_NAME,
        "runner_version": __version__,
        "implementation": platform.python_implementation(),
    }
    digest = hashlib.sha256(
        json.dumps(captured, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]
    captured["environment_id"] = f"env-{digest}"
    return captured


def process_exit_code(result: dict[str, Any]) -> int:
    """Operator exit code. Zero means the observation matched, not that a component was admitted."""
    if result["observation"] == "match":
        return 0
    if result["outcome_class"] == "component_failure":
        return 1
    return 2


def run_case(method_dir: Path, case_path: Path, output_root: Path) -> dict[str, Any]:
    method_dir = method_dir.resolve()
    case_path = case_path.resolve()
    output_root = output_root.resolve()
    method = load_yaml(method_dir / "method.yaml")
    _require_method(method)
    assert_execution_allowed(method)

    case = load_json(case_path)
    validate_instance("test_case.schema.json", case)
    if (case["method_id"], case["method_version"]) != (method["id"], str(method["version"])):
        raise MethodError(
            "case method id/version does not match method.yaml "
            f"({case['method_id']} {case['method_version']} != {method['id']} {method['version']})"
        )

    rules = rule_table(method)
    component = _load_component(method_dir, case["component_path"])
    execution = _execute(method_dir, case)
    rule = rules[execution.rule_id]
    run_id = new_id("run")
    evidence_id = new_id("ev")
    timestamp = utc_now()
    relative_dir = f"{component['id']}/{component['version']}/{run_id}"
    environment = capture_environment()
    assurance = _copy_mapping(method["assurance"], _ASSURANCE_KEYS, "assurance")
    envelope = _envelope(
        method,
        case,
        environment,
        rule.run_note,
        component["version"],
    )
    tested_under = (
        f"method {method['id']} {method['version']}; "
        f"runner {RUNNER_NAME} {__version__}; "
        f"environment {environment['environment_id']}; "
        f"fixture {case['fixture_id']}"
    )
    manifest = {
        "evidence_id": evidence_id,
        "run_id": run_id,
        "source_type": "ve_test",
        "method_id": method["id"],
        "method_version": str(method["version"]),
        "runner_version": __version__,
        "environment": environment,
        "fixture_id": case["fixture_id"],
        "timestamp": timestamp,
        "raw_artifact_path": relative_dir,
        "observation": rule.observation,
        "outcome_class": rule.outcome_class,
        "notes": _manifest_notes(rule.rule_id, rule.run_note, execution.blocked_reason),
    }
    result: dict[str, Any] = {
        "result_id": new_id("res"),
        "record_purpose": method["purpose"],
        "component_id": component["id"],
        "component_version": component["version"],
        "component_commit": component.get("commit"),
        "component_type": component["component_type"],
        "source_repository": component["source_repository"],
        "method_id": method["id"],
        "method_version": str(method["version"]),
        "runner_name": RUNNER_NAME,
        "runner_version": __version__,
        "implemented_rule_ids": list(IMPLEMENTED_RULE_IDS),
        "rule_id": rule.rule_id,
        "environment": environment,
        "fixture_id": case["fixture_id"],
        "run_id": run_id,
        "timestamp": timestamp,
        "observation": rule.observation,
        "outcome_class": rule.outcome_class,
        "capabilities": [
            {
                "capability_id": case["case_id"],
                "claim": case["claim"],
                "testable_statement": case["testable_statement"],
                "status": rule.capability_status,
                "supporting_evidence": [evidence_id],
                "tested_under": tested_under,
                "notes": rule.run_note,
                "envelope": claim_envelope_from_run(envelope),
            }
        ],
        "assurance": assurance,
        "envelope": envelope,
        "evidence_refs": [evidence_id],
        "evidence_dir": relative_dir,
        "history": [
            make_event(
                event_type=rule.outcome_class,
                previous_state=None,
                new_state=rule.outcome_class,
                reason=f"rule {rule.rule_id}: {rule.run_note}",
                evidence_refs=[evidence_id],
                timestamp=timestamp,
            )
        ],
        "admission": "insufficient",
        "admission_reasons": [],
    }
    package_dir = output_root / relative_dir
    _write_hashed_artifacts(
        package_dir=package_dir,
        environment=environment,
        component=component,
        case=case,
        execution=execution,
    )
    manifest["artifacts"] = hash_package_files(package_dir)
    integrity_errors = check_evidence_integrity(package_dir, manifest)
    if integrity_errors:
        raise VeriEnvelopeError(
            "evidence package failed its own integrity check:\n" + "\n".join(integrity_errors)
        )
    admission, reasons = evaluate_admission(
        result,
        component,
        [manifest],
        package_dir=package_dir,
        manifest=manifest,
        check_seal=False,
    )
    result["admission"] = admission
    result["admission_reasons"] = reasons
    assert_consistent(result)
    validate_instance("verification_result.schema.json", result)
    validate_instance("evidence.schema.json", manifest)
    dump_json(package_dir / "manifest.json", manifest)
    dump_json(package_dir / "result.json", result)
    (package_dir / "notes.md").write_text(
        _notes(result, execution.blocked_reason),
        encoding="utf-8",
    )
    write_package_seal(package_dir)
    seal_errors = check_package_seal(package_dir)
    if seal_errors:
        raise VeriEnvelopeError(
            "evidence package failed its final seal:\n" + "\n".join(seal_errors)
        )
    return result


def _require_method(method: dict[str, Any]) -> None:
    missing = [key for key in _METHOD_KEYS if key not in method]
    if missing:
        raise MethodError("method.yaml is missing: " + ", ".join(missing))


def _copy_mapping(raw: Any, keys: tuple[str, ...], label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise MethodError(f"method {label} is missing")
    missing = [key for key in keys if key not in raw]
    if missing:
        raise MethodError(f"method {label} is missing: " + ", ".join(missing))
    return {key: raw[key] for key in keys}


def _envelope(
    method: dict[str, Any],
    case: dict[str, Any],
    environment: dict[str, str],
    run_note: str,
    component_version: str,
) -> dict[str, Any]:
    base = _copy_mapping(method["envelope"], _ENVELOPE_KEYS, "envelope")
    return {
        "tested_conditions": [
            *base["tested_conditions"],
            f"timeout_seconds={case['timeout_seconds']}",
            f"environment_id={environment['environment_id']}",
        ],
        "known_limits": list(base["known_limits"]),
        "known_failures": [run_note],
        "untested_areas": list(base["untested_areas"]),
        "environment_constraints": [
            f"{environment['os']} {environment['arch']}",
            f"python {environment['python']}",
            "只覆盖这次捕获到的环境。",
        ],
        "version_constraints": [
            *base["version_constraints"],
            f"component_version={component_version}",
        ],
        "revalidation_triggers": list(base["revalidation_triggers"]),
    }


def _load_component(method_dir: Path, relative: str) -> dict[str, Any]:
    path = safe_method_path(method_dir, relative)
    if not path.is_file():
        raise MethodError(f"component file does not exist: {relative}")
    component = load_json(path)
    validate_instance("component.schema.json", component)
    return component


def _execute(method_dir: Path, case: dict[str, Any]) -> Execution:
    try:
        entrypoint = safe_method_path(method_dir, case["entrypoint"])
        input_file = safe_method_path(method_dir, case["input_file"])
        expected_file = safe_method_path(method_dir, case["expected_stdout_file"])
        missing = [
            label
            for label, path in (
                ("entrypoint", entrypoint),
                ("input_file", input_file),
                ("expected_stdout_file", expected_file),
            )
            if not path.is_file()
        ]
        if missing:
            raise PolicyError("required file does not exist: " + ", ".join(missing))
    except PolicyError as exc:
        return Execution(
            rule_id=select_rule_id(
                blocked=True,
                timed_out=False,
                exit_code=None,
                stdout=None,
                expected_exit_code=0,
                expected_stdout=b"",
            ),
            stdout=b"",
            stderr=str(exc).encode("utf-8"),
            exit_code=None,
            blocked_reason=str(exc),
            input_files={},
        )

    timeout = checked_timeout(case["timeout_seconds"])
    expected_exit = case["expected_exit_code"]
    if isinstance(expected_exit, bool) or not isinstance(expected_exit, int):
        raise MethodError("expected_exit_code must be an integer")
    expected_stdout = expected_file.read_bytes()
    stored = {
        "entrypoint.py": entrypoint.read_bytes(),
        "payload.bin": input_file.read_bytes(),
    }
    with tempfile.TemporaryDirectory(prefix="ve-run-") as work:
        work_path = Path(work)
        script_path = work_path / "entrypoint.py"
        payload_path = work_path / "input.bin"
        script_path.write_bytes(stored["entrypoint.py"])
        payload_path.write_bytes(stored["payload.bin"])
        try:
            completed = subprocess.run(
                [sys.executable, str(script_path), str(payload_path)],
                cwd=work_path,
                env=scrubbed_subprocess_env(),
                timeout=timeout,
                capture_output=True,
                stdin=subprocess.DEVNULL,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = _as_bytes(exc.stdout)
            stderr = _as_bytes(exc.stderr)
            return Execution(
                rule_id=select_rule_id(
                    blocked=False,
                    timed_out=True,
                    exit_code=None,
                    stdout=stdout,
                    expected_exit_code=expected_exit,
                    expected_stdout=expected_stdout,
                ),
                stdout=stdout,
                stderr=stderr,
                exit_code=None,
                blocked_reason=None,
                input_files=stored,
            )

    return Execution(
        rule_id=select_rule_id(
            blocked=False,
            timed_out=False,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            expected_exit_code=expected_exit,
            expected_stdout=expected_stdout,
        ),
        stdout=completed.stdout,
        stderr=completed.stderr,
        exit_code=completed.returncode,
        blocked_reason=None,
        input_files=stored,
    )


def _as_bytes(value: bytes | str | None) -> bytes:
    if value is None:
        return b""
    if isinstance(value, str):
        return value.encode("utf-8")
    return value


def _manifest_notes(rule_id: str, run_note: str, blocked_reason: str | None) -> str:
    text = f"rule {rule_id}. {run_note}"
    if blocked_reason:
        text = f"{text} Refusal: {blocked_reason}"
    return text


def _write_hashed_artifacts(
    *,
    package_dir: Path,
    environment: dict[str, str],
    component: dict[str, Any],
    case: dict[str, Any],
    execution: Execution,
) -> None:
    """Write the files that will be hashed. manifest.json and result.json come later."""
    package_dir.mkdir(parents=True, exist_ok=False)
    input_dir = package_dir / "input"
    input_dir.mkdir()
    dump_json(package_dir / "environment.json", environment)
    dump_json(input_dir / "component.json", component)
    dump_json(input_dir / "case.json", case)
    for name, payload in execution.input_files.items():
        (input_dir / name).write_bytes(payload)
    (package_dir / "stdout.log").write_bytes(execution.stdout)
    (package_dir / "stderr.log").write_bytes(execution.stderr)


def _notes(result: dict[str, Any], blocked_reason: str | None) -> str:
    reasons = "；".join(result["admission_reasons"]) or "无"
    refusal = f"\n拒绝原因：{blocked_reason}\n" if blocked_reason else ""
    return (
        "# 运行记录\n\n"
        f"- 方法：{result['method_id']} {result['method_version']}\n"
        f"- runner：{result['runner_name']} {result['runner_version']}\n"
        f"- 规则：{result['rule_id']}\n"
        f"- 观察：{result['observation']}\n"
        f"- 结果类别：{result['outcome_class']}\n"
        f"- 记录用途：{result['record_purpose']}\n"
        f"- 准入：{result['admission']}\n"
        f"- 准入原因：{reasons}\n"
        f"{refusal}\n"
        "进程退出码 0 只表示观察为 match。它不是组件准入。\n"
        "观察不是解释。没有观察到失败，只说明这次列出的条件里没有观察到失败。\n"
    )

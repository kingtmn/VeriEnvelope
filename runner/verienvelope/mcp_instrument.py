"""Calibrate the MCP instrument against the controlled fixture.

The fixture runs inside the OCI boundary. This module never starts
mcp.server-everything. A finished record is instrument_self_test and cannot
be admitted.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from verienvelope import __version__
from verienvelope.admission import evaluate_admission
from verienvelope.consistency import assert_consistent
from verienvelope.errors import VeriEnvelopeError
from verienvelope.evidence_integrity import check_evidence_integrity, hash_package_files
from verienvelope.history import make_event, new_id, utc_now
from verienvelope.mcp_protocol import (
    ECHO_MESSAGE,
    ECHO_TEXT,
    ClaimJudgment,
    encode_message,
    initialize_request,
    initialized_notification,
    judge_echo,
    judge_exit,
    judge_initialize,
    judge_timeout,
    judge_tools,
    read_until_response,
    tools_call_echo_request,
    tools_list_request,
)
from verienvelope.package_seal import check_package_seal, write_package_seal
from verienvelope.run import RUNNER_NAME, capture_environment
from verienvelope.sandbox import RuntimeLimits, StdioSession
from verienvelope.schema_io import dump_json, validate_instance

FIXTURE_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "methods"
    / "VE-METHOD-MCP-001"
    / "fixtures"
    / "controlled_stdio.py"
)
_FIXTURE_IMAGE_ID: str | None = None
FIXTURE_ID = "verienvelope.mcp-fixture"
FIXTURE_VERSION = "0.0.0"
METHOD_ID = "VE-METHOD-MCP-001"
METHOD_VERSION = "0.3.0"
SUBSTRATE_IMAGE = "python:3.11-slim"


@dataclass(frozen=True)
class FixtureExpectation:
    server_name: str
    server_version: str
    tool_names: frozenset[str]
    echo_text: str


DEFAULT_FIXTURE = FixtureExpectation(
    server_name=FIXTURE_ID,
    server_version=FIXTURE_VERSION,
    tool_names=frozenset({"echo"}),
    echo_text=ECHO_TEXT,
)


def fixture_image_id() -> str:
    """Bake our script into a local image so runtime does not mount the host.

    Colima does not see macOS temporary directories as bind sources. The build
    context is uploaded to the daemon. The running container has no host mount.
    """
    global _FIXTURE_IMAGE_ID
    if _FIXTURE_IMAGE_ID:
        return _FIXTURE_IMAGE_ID
    from verienvelope.sandbox import _docker

    with tempfile.TemporaryDirectory(prefix="ve-mcp-image-") as work:
        context = Path(work)
        shutil.copyfile(FIXTURE_SOURCE, context / "controlled_stdio.py")
        (context / "Dockerfile").write_text(
            "FROM python:3.11-slim\n"
            "COPY controlled_stdio.py /opt/ve-fixture/controlled_stdio.py\n",
            encoding="utf-8",
        )
        completed = _docker(["docker", "build", "-q", str(context)], timeout=180)
    if completed.returncode != 0:
        raise VeriEnvelopeError(
            "fixture image build failed:\n" + completed.stderr.decode("utf-8", errors="replace")
        )
    image_id = completed.stdout.decode("utf-8").strip()
    if not image_id.startswith("sha256:"):
        raise VeriEnvelopeError(f"fixture image id was not returned: {image_id!r}")
    _FIXTURE_IMAGE_ID = image_id
    return image_id


def run_fixture_case(
    *,
    mode: str,
    output_root: Path,
    image: str = SUBSTRATE_IMAGE,
    expectation: FixtureExpectation = DEFAULT_FIXTURE,
    timeout_seconds: float = 10,
) -> dict[str, Any]:
    if FIXTURE_ID == "mcp.server-everything":
        raise VeriEnvelopeError("the controlled fixture must not use the external component id")
    limits = RuntimeLimits(cpus="0.5", memory="128m", pids_limit=32, timeout_seconds=timeout_seconds)
    image_ref = fixture_image_id() if image == SUBSTRATE_IMAGE else image
    command = ["python", "-u", "/opt/ve-fixture/controlled_stdio.py", mode]
    with StdioSession(
        image=image_ref,
        command=command,
        limits=limits,
    ) as session:
        judgments, stdout, stderr = _exchange(
            session,
            expectation=expectation,
            read_timeout=timeout_seconds,
        )
        image_id = session.image.image_id
    if not session.removed():
        raise VeriEnvelopeError("sandbox session was not removed")
    return _write_package(
        output_root=output_root,
        mode=mode,
        judgments=judgments,
        stdout=stdout,
        stderr=stderr,
        image_id=image_id,
        expectation=expectation,
    )


def _judge_selected(selected, judge):
    if selected.matched is None:
        return judge(None, True)
    return judge(selected.matched, False)


def _exchange(
    session: StdioSession,
    *,
    expectation: FixtureExpectation,
    read_timeout: float,
) -> tuple[list[ClaimJudgment], bytes, bytes]:
    lines: list[bytes] = []
    try:
        session.write_line(encode_message(initialize_request()))
        first = read_until_response(session.read_line, 1, read_timeout)
        lines.append(first.raw)
        c1 = _judge_selected(
            first,
            lambda message, malformed: judge_initialize(
                message,
                expected_name=expectation.server_name,
                expected_version=expectation.server_version,
                malformed=malformed,
            ),
        )
        if c1.observation != "match":
            return [c1], b"".join(lines), session.stderr
        session.write_line(encode_message(initialized_notification()))
        session.write_line(encode_message(tools_list_request()))
        second = read_until_response(session.read_line, 2, read_timeout)
        lines.append(second.raw)
        c2 = _judge_selected(
            second,
            lambda message, malformed: judge_tools(
                None if malformed else message,
                expected_names=expectation.tool_names,
            ),
        )
        if c2.observation != "match":
            return [c1, c2], b"".join(lines), session.stderr
        session.write_line(encode_message(tools_call_echo_request(ECHO_MESSAGE)))
        third = read_until_response(session.read_line, 3, read_timeout)
        lines.append(third.raw)
        c3 = _judge_selected(
            third,
            lambda message, malformed: judge_echo(
                None if malformed else message,
                expected_text=expectation.echo_text,
            ),
        )
        session.close_stdin()
        return [c1, c2, c3], b"".join(lines), session.stderr
    except subprocess.TimeoutExpired:
        return [judge_timeout()], b"".join(lines), session.stderr


def _write_package(
    *,
    output_root: Path,
    mode: str,
    judgments: list[ClaimJudgment],
    stdout: bytes,
    stderr: bytes,
    image_id: str,
    expectation: FixtureExpectation,
) -> dict[str, Any]:
    primary = _primary(judgments)
    run_id = new_id("run")
    evidence_id = new_id("ev")
    timestamp = utc_now()
    relative_dir = f"{FIXTURE_ID}/{FIXTURE_VERSION}/{run_id}"
    environment = capture_environment()
    component = {
        "id": FIXTURE_ID,
        "name": "Controlled MCP fixture",
        "component_type": "mcp_server",
        "description": "量具自检底物。不是外部组件，不能当作 GATE 1 证据。",
        "source_repository": "file://verienvelope/methods/VE-METHOD-MCP-001/fixtures/controlled_stdio.py",
        "version": FIXTURE_VERSION,
        "status": "candidate",
    }
    case = {
        "case_id": f"instrument-{mode}",
        "mode": mode,
        "expected_server_name": expectation.server_name,
        "expected_server_version": expectation.server_version,
        "expected_tools": sorted(expectation.tool_names),
        "expected_echo_text": expectation.echo_text,
        "record_purpose": "instrument_self_test",
    }
    tested_under = (
        f"method {METHOD_ID} {METHOD_VERSION}; runner {RUNNER_NAME} {__version__}; "
        f"fixture {FIXTURE_ID}; image {image_id}; mode {mode}"
    )
    capabilities = []
    for item in judgments:
        status = item.capability_status
        note = item.note
        if primary.observation != "match" and status == "demonstrated":
            status = "not_demonstrated"
            note = f"{note} 总观察不是 match，本条不标 demonstrated。"
        capabilities.append(
            {
                "capability_id": item.claim_id,
                "claim": item.claim_id,
                "testable_statement": note,
                "status": status,
                "supporting_evidence": [evidence_id] if status == "demonstrated" else [],
                "tested_under": tested_under,
                "notes": note,
            }
        )
    envelope = {
        "tested_conditions": [
            "controlled fixture inside the OCI runtime boundary",
            f"image_id={image_id}",
            f"mode={mode}",
            "network none",
        ],
        "known_limits": [
            "这是量具自检，不是 mcp.server-everything 的测量",
            "不匹配的第一次归类是 unclassified",
        ],
        "known_failures": [primary.note],
        "untested_areas": [
            "不声明 production readiness",
            "不声明 security",
            "外部 MCP 服务器",
        ],
        "environment_constraints": [
            f"{environment['os']} {environment['arch']}",
            f"python {environment['python']}",
            f"container image {image_id}",
        ],
        "version_constraints": [f"method {METHOD_VERSION}", f"fixture {FIXTURE_VERSION}"],
        "revalidation_triggers": ["method_revision", "runner_bug", "runtime"],
    }
    assurance = {
        "dependencies": ["python:3.11-slim substrate", "OCI runtime"],
        "permissions": ["stdio", "readonly fixture mount", "tmpfs /work"],
        "execution_mode": "oci_runtime_network_none",
        "external_services": [],
        "provenance": "Controlled fixture owned by this repository. Not an external component.",
        "reproducibility_notes": "Compare observation, outcome_class, and capability status. Ignore run_id.",
    }
    manifest = {
        "evidence_id": evidence_id,
        "run_id": run_id,
        "source_type": "ve_test",
        "method_id": METHOD_ID,
        "method_version": METHOD_VERSION,
        "runner_version": __version__,
        "environment": environment,
        "fixture_id": FIXTURE_ID,
        "timestamp": timestamp,
        "raw_artifact_path": relative_dir,
        "observation": primary.observation,
        "outcome_class": primary.outcome_class,
        "notes": f"rule {primary.rule_id}. instrument_self_test mode={mode}. {primary.note}",
    }
    result: dict[str, Any] = {
        "result_id": new_id("res"),
        "record_purpose": "instrument_self_test",
        "component_id": FIXTURE_ID,
        "component_version": FIXTURE_VERSION,
        "component_commit": None,
        "component_type": "mcp_server",
        "source_repository": component["source_repository"],
        "method_id": METHOD_ID,
        "method_version": METHOD_VERSION,
        "runner_name": RUNNER_NAME,
        "runner_version": __version__,
        "implemented_rule_ids": ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10"],
        "rule_id": primary.rule_id,
        "environment": environment,
        "fixture_id": FIXTURE_ID,
        "run_id": run_id,
        "timestamp": timestamp,
        "observation": primary.observation,
        "outcome_class": primary.outcome_class,
        "capabilities": capabilities,
        "assurance": assurance,
        "envelope": envelope,
        "evidence_refs": [evidence_id],
        "evidence_dir": relative_dir,
        "history": [
            make_event(
                event_type=primary.outcome_class,
                previous_state=None,
                new_state=primary.outcome_class,
                reason=f"rule {primary.rule_id}: {primary.note}",
                evidence_refs=[evidence_id],
                timestamp=timestamp,
            )
        ],
        "admission": "insufficient",
        "admission_reasons": [],
    }
    package_dir = output_root / relative_dir
    package_dir.mkdir(parents=True, exist_ok=False)
    input_dir = package_dir / "input"
    input_dir.mkdir()
    dump_json(package_dir / "environment.json", environment)
    dump_json(input_dir / "component.json", component)
    dump_json(input_dir / "case.json", case)
    (package_dir / "stdout.log").write_bytes(stdout)
    (package_dir / "stderr.log").write_bytes(stderr)
    manifest["artifacts"] = hash_package_files(package_dir)
    integrity_errors = check_evidence_integrity(package_dir, manifest)
    if integrity_errors:
        raise VeriEnvelopeError("instrument package failed raw integrity:\n" + "\n".join(integrity_errors))
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
        "# 量具自检\n\n"
        f"- 记录用途：instrument_self_test\n"
        f"- 模式：{mode}\n"
        f"- 规则：{primary.rule_id}\n"
        f"- 观察：{primary.observation}\n"
        f"- 结果类别：{primary.outcome_class}\n"
        f"- 准入：{admission}\n\n"
        "这不是外部组件验证。观察不是原因。\n",
        encoding="utf-8",
    )
    write_package_seal(package_dir)
    seal_errors = check_package_seal(package_dir)
    if seal_errors:
        raise VeriEnvelopeError("instrument package failed its seal:\n" + "\n".join(seal_errors))
    return result


def _primary(judgments: list[ClaimJudgment]) -> ClaimJudgment:
    for item in judgments:
        if item.observation != "match":
            return item
    if not judgments:
        raise VeriEnvelopeError("instrument produced no judgment")
    return judgments[-1] if all(item.observation == "match" for item in judgments) else judgments[0]

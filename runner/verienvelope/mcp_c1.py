"""Send one initialize, then stop.

This module can start the pinned Everything image once. It does not send
notifications/initialized, tools/list, or tools/call. A C1 match is not
admission and is not GATE 1.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from verienvelope import __version__
from verienvelope.admission import evaluate_admission
from verienvelope.artifact_identity import (
    ARTIFACT_ORIGIN,
    CONTAINER_ARGV,
    CONTAINER_WORKDIR,
    LOCAL_IMAGE_ID,
    PACKAGE_NAME,
    PACKAGE_VERSION,
    SOURCE_COMMIT,
    SOURCE_REPOSITORY,
    execution_artifact,
    source_identity,
)
from verienvelope.consistency import assert_consistent
from verienvelope.errors import VeriEnvelopeError
from verienvelope.evidence_integrity import check_evidence_integrity, hash_package_files
from verienvelope.history import make_event, new_id, utc_now
from verienvelope.mcp_protocol import (
    PROTOCOL_VERSION,
    ClaimJudgment,
    encode_message,
    initialize_request,
    judge_exit,
    judge_initialize,
    judge_timeout,
    parse_message,
)
from verienvelope.package_seal import check_package_seal, write_package_seal
from verienvelope.run import RUNNER_NAME, capture_environment
from verienvelope.sandbox import BoundaryObservation, RuntimeLimits, StdioSession, control_plane_env
from verienvelope.schema_io import dump_json, load_yaml, repo_root, validate_instance

METHOD_VERSION = "0.3.0"
C1_LIMITS = RuntimeLimits(
    cpus="1",
    memory="512m",
    pids_limit=64,
    timeout_seconds=20,
    user="65532:65532",
)
_RULE_IDS = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10"]
_NOT_SENT = ["notifications/initialized", "tools/list", "tools/call"]


def run_everything_c1(output_root: Path) -> dict[str, Any]:
    """One external initialize against the pinned local image id. No second try."""
    if _existing_external_results(output_root):
        raise VeriEnvelopeError(
            "an Everything evidence package already exists; refusing another run"
        )
    _require_frozen_method()
    if _image_workdir(LOCAL_IMAGE_ID) != CONTAINER_WORKDIR:
        raise VeriEnvelopeError(
            "Everything image workdir is not the pinned component path; initialize was not sent"
        )
    component = {
        "id": "mcp.server-everything",
        "name": "Everything MCP Server",
        "component_type": "mcp_server",
        "description": (
            "SOURCE IDENTITY 的 package_version 2.0.0 是源码 metadata。"
            "执行工件是 locally_built_from_pinned_source，不是 npm registry 发布物，也不是官方镜像。"
        ),
        "source_repository": SOURCE_REPOSITORY,
        "version": PACKAGE_VERSION,
        "commit": SOURCE_COMMIT,
        "status": "candidate",
        "publisher": "Model Context Protocol a Series of LF Projects, LLC.",
    }
    return run_initialize_only(
        image=LOCAL_IMAGE_ID,
        command=list(CONTAINER_ARGV),
        output_root=output_root,
        expected_name="mcp-servers/everything",
        expected_version=PACKAGE_VERSION,
        record_purpose="component_verification",
        component=component,
        fixture_id="c1-initialize",
        allow_external=True,
    )


def run_initialize_only(
    *,
    image: str,
    command: list[str],
    output_root: Path,
    expected_name: str,
    expected_version: str,
    record_purpose: str,
    component: dict[str, Any],
    fixture_id: str,
    allow_external: bool = False,
) -> dict[str, Any]:
    if component.get("id") == "mcp.server-everything" and not allow_external:
        raise VeriEnvelopeError("refusing to start Everything outside the one-shot C1 entry")
    request = initialize_request()
    raw_request = encode_message(request)
    limits = C1_LIMITS
    judgment: ClaimJudgment
    stdout = b""
    stderr = b""
    boundary: BoundaryObservation | None = None
    image_id = ""
    exit_code: int | None = None
    sent: list[str] = []
    request_sent_at: str | None = None
    response_at: str | None = None
    try:
        with StdioSession(image=image, command=command, limits=limits) as session:
            image_id = session.image.image_id
            if image_id == LOCAL_IMAGE_ID and not allow_external:
                raise VeriEnvelopeError("refusing to start the Everything image")
            if allow_external and image_id != LOCAL_IMAGE_ID:
                raise VeriEnvelopeError("external C1 must use the pinned local image id")
            boundary = session.boundary
            if not _boundary_ok(boundary):
                judgment = ClaimJudgment(
                    "C1",
                    "M8",
                    "blocked",
                    "out_of_envelope",
                    "insufficient",
                    "运行边界与方法不一致，initialize 没有发送。原因未归类。",
                )
            else:
                request_sent_at = utc_now()
                session.write_line(raw_request)
                sent.append("initialize")
                try:
                    line = session.read_line(limits.timeout_seconds)
                except subprocess.TimeoutExpired:
                    judgment = judge_timeout()
                    response_at = utc_now()
                else:
                    response_at = utc_now()
                    stdout = line
                    if line == b"":
                        judgment = judge_exit()
                    else:
                        parsed = parse_message(line)
                        judgment = judge_initialize(
                            parsed,
                            expected_name=expected_name,
                            expected_version=expected_version,
                            expected_protocol=PROTOCOL_VERSION,
                            expected_id=1,
                            malformed=parsed is None,
                        )
                session.close_stdin()
    except VeriEnvelopeError as exc:
        if sent:
            raise
        judgment = ClaimJudgment(
            "C1",
            "M2",
            "execution_error",
            "unclassified",
            "not_demonstrated",
            "容器没有给出 initialize 响应。原因未归类。",
        )
        stderr = str(exc).encode("utf-8")
        image_id = image_id or image
    else:
        stderr = session.stderr
        exit_code = session.exit_code
        if not session.removed():
            raise VeriEnvelopeError("sandbox session was not removed")
    return _write_package(
        output_root=output_root,
        component=component,
        fixture_id=fixture_id,
        record_purpose=record_purpose,
        judgment=judgment,
        stdout=stdout,
        stderr=stderr,
        request=request,
        raw_request=raw_request,
        image_id=image_id,
        boundary=boundary,
        exit_code=exit_code,
        sent=sent,
        request_sent_at=request_sent_at,
        response_at=response_at,
        allow_external=allow_external,
    )


def _require_frozen_method() -> None:
    method = load_yaml(repo_root() / "methods" / "VE-METHOD-MCP-001" / "method.yaml")
    if str(method.get("version")) != METHOD_VERSION:
        raise VeriEnvelopeError(f"refusing to run because the method is not {METHOD_VERSION}")
    offered = method["client_handshake"]["protocol_version_offered"]
    if offered != PROTOCOL_VERSION:
        raise VeriEnvelopeError("method protocolVersion and the executor constant diverged")


def _existing_external_results(output_root: Path) -> bool:
    base = output_root / "mcp.server-everything"
    return base.is_dir() and any(base.glob("**/result.json"))


def _image_workdir(image_id: str) -> str:
    completed = subprocess.run(
        ["docker", "image", "inspect", image_id],
        capture_output=True,
        check=False,
        env=control_plane_env(),
    )
    if completed.returncode != 0:
        raise VeriEnvelopeError("pinned Everything image is not present locally")
    payload = json.loads(completed.stdout.decode("utf-8"))
    workdir = payload[0].get("Config", {}).get("WorkingDir")
    return workdir if isinstance(workdir, str) else ""


def _boundary_ok(boundary: BoundaryObservation | None) -> bool:
    if boundary is None:
        return False
    if boundary.user != "65532:65532":
        return False
    if boundary.network_mode != "none":
        return False
    if not boundary.readonly_rootfs:
        return False
    if "ALL" not in boundary.cap_drop:
        return False
    if not any("no-new-privileges" in item for item in boundary.security_opt):
        return False
    if boundary.mount_sources:
        return False
    return True


def _write_package(
    *,
    output_root: Path,
    component: dict[str, Any],
    fixture_id: str,
    record_purpose: str,
    judgment: ClaimJudgment,
    stdout: bytes,
    stderr: bytes,
    request: dict[str, Any],
    raw_request: bytes,
    image_id: str,
    boundary: BoundaryObservation | None,
    exit_code: int | None,
    sent: list[str],
    request_sent_at: str | None,
    response_at: str | None,
    allow_external: bool,
) -> dict[str, Any]:
    validate_instance("component.schema.json", component)
    run_id = new_id("run")
    evidence_id = new_id("ev")
    timestamp = utc_now()
    version = str(component["version"])
    relative_dir = f"{component['id']}/{version}/{run_id}"
    environment = capture_environment()
    if allow_external:
        provenance = (
            "SOURCE IDENTITY 是源码 commit "
            f"{SOURCE_COMMIT}，package {PACKAGE_NAME} metadata {PACKAGE_VERSION}。"
            "package_version 不是 npm registry 发布 artifact。"
            f"EXECUTION ARTIFACT IDENTITY 是 {ARTIFACT_ORIGIN}，"
            f"local_image_id {LOCAL_IMAGE_ID}，registry_digest null。"
        )
    else:
        provenance = "Controlled fixture. Not an external component and not an npm artifact."
    assurance = {
        "dependencies": [
            f"source package metadata {PACKAGE_NAME} {PACKAGE_VERSION}",
            f"local image {image_id}",
            "OCI runtime",
        ],
        "permissions": ["stdio", "tmpfs /work", "user 65532:65532"],
        "execution_mode": "oci_runtime_network_none",
        "external_services": [],
        "provenance": provenance,
        "reproducibility_notes": (
            "Compare C1 observation, capability status, and outcome class. "
            "Ignore run_id. A C1 match does not admit the component. "
            f"artifact={json.dumps(execution_artifact(), sort_keys=True)}"
        ),
    }
    if allow_external:
        assurance["dependencies"] = [
            f"source package metadata {PACKAGE_NAME} {PACKAGE_VERSION}",
            "lockfile sha256 df3034c8bb82e772389fa4518793c0cee24361c581c66e7bb04d0d7270dc24e1",
            "node v22.12.0",
            "npm 10.9.0",
            "base image sha256:51eff88af6dff26f59316b6e356188ffa2c422bd3c3b76f2556a2e7e89d080bd",
            f"local image {LOCAL_IMAGE_ID}",
            "OCI runtime",
        ]
    tested_under = (
        f"method VE-METHOD-MCP-001 {METHOD_VERSION}; runner {RUNNER_NAME} {__version__}; "
        f"image {image_id}; user 65532:65532; network none"
    )
    capabilities = [
        _capability(judgment, evidence_id, tested_under),
        _unrun("C2", "tools/list 没有发送。", tested_under),
        _unrun("C3", "tools/call 没有发送。", tested_under),
    ]
    envelope = {
        "tested_conditions": [
            f"image_id={image_id}",
            "initialize only",
            "network none",
            "user 65532:65532",
        ],
        "known_limits": [
            "C2 和 C3 没有执行",
            "package version 不是 npm 发布包的验证结论",
            "C1 demonstrated 不是组件准入",
        ],
        "known_failures": [] if judgment.observation == "match" else [judgment.note],
        "untested_areas": [
            "不声明 production readiness",
            "不声明 security",
            "C2 tools/list",
            "C3 echo",
        ],
        "environment_constraints": [
            f"{environment['os']} {environment['arch']}",
            "readonly root, cap-drop ALL, no-new-privileges, tmpfs /work",
        ],
        "version_constraints": [f"method {METHOD_VERSION}"],
        "revalidation_triggers": ["method_revision", "runner_bug", "runtime"],
    }
    case = {
        "case_id": "c1-initialize",
        "request": request,
        "messages_sent": sent,
        "messages_not_sent": _NOT_SENT,
        "limits": {
            "cpus": C1_LIMITS.cpus,
            "memory": C1_LIMITS.memory,
            "pids_limit": C1_LIMITS.pids_limit,
            "timeout_seconds": C1_LIMITS.timeout_seconds,
            "user": C1_LIMITS.user,
        },
        "record_purpose": record_purpose,
        "source_identity": source_identity() if allow_external else {"fixture": fixture_id},
        "execution_artifact": execution_artifact() if allow_external else {"image_id": image_id},
    }
    runtime = {
        "image_id": image_id,
        "request_sent_at": request_sent_at,
        "response_at": response_at,
        "exit_code": exit_code,
        "boundary": _boundary_dict(boundary),
        "messages_sent": sent,
    }
    manifest = {
        "evidence_id": evidence_id,
        "run_id": run_id,
        "source_type": "ve_test",
        "method_id": "VE-METHOD-MCP-001",
        "method_version": METHOD_VERSION,
        "runner_version": __version__,
        "environment": environment,
        "fixture_id": fixture_id,
        "timestamp": timestamp,
        "raw_artifact_path": relative_dir,
        "observation": judgment.observation,
        "outcome_class": judgment.outcome_class,
        "notes": f"rule {judgment.rule_id}. {judgment.note}",
    }
    result: dict[str, Any] = {
        "result_id": new_id("res"),
        "record_purpose": record_purpose,
        "component_id": component["id"],
        "component_version": version,
        "component_commit": component.get("commit"),
        "component_type": "mcp_server",
        "source_repository": component["source_repository"],
        "method_id": "VE-METHOD-MCP-001",
        "method_version": METHOD_VERSION,
        "runner_name": RUNNER_NAME,
        "runner_version": __version__,
        "implemented_rule_ids": _RULE_IDS,
        "rule_id": judgment.rule_id,
        "environment": environment,
        "fixture_id": fixture_id,
        "run_id": run_id,
        "timestamp": timestamp,
        "observation": judgment.observation,
        "outcome_class": judgment.outcome_class,
        "capabilities": capabilities,
        "assurance": assurance,
        "envelope": envelope,
        "evidence_refs": [evidence_id],
        "evidence_dir": relative_dir,
        "history": [
            make_event(
                event_type=judgment.outcome_class,
                previous_state=None,
                new_state=judgment.outcome_class,
                reason=f"rule {judgment.rule_id}: {judgment.note}",
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
    dump_json(input_dir / "artifact.json", execution_artifact() if allow_external else {"image_id": image_id})
    (input_dir / "request.log").write_bytes(raw_request)
    dump_json(package_dir / "runtime.json", runtime)
    (package_dir / "stdout.log").write_bytes(stdout)
    (package_dir / "stderr.log").write_bytes(stderr)
    manifest["artifacts"] = hash_package_files(package_dir)
    integrity_errors = check_evidence_integrity(package_dir, manifest)
    if integrity_errors:
        raise VeriEnvelopeError("C1 package failed raw integrity:\n" + "\n".join(integrity_errors))
    admission, reasons = evaluate_admission(
        result,
        component,
        [manifest],
        package_dir=package_dir,
        manifest=manifest,
        check_seal=False,
    )
    if admission == "admitted":
        admission = "insufficient"
        reasons = [
            "C2 and C3 were not executed; one C1 observation is not component admission",
            *reasons,
        ]
    result["admission"] = admission
    result["admission_reasons"] = reasons
    assert_consistent(result)
    validate_instance("verification_result.schema.json", result)
    validate_instance("evidence.schema.json", manifest)
    dump_json(package_dir / "manifest.json", manifest)
    dump_json(package_dir / "result.json", result)
    (package_dir / "notes.md").write_text(_notes(result, judgment, sent), encoding="utf-8")
    write_package_seal(package_dir)
    seal_errors = check_package_seal(package_dir)
    if seal_errors:
        raise VeriEnvelopeError("C1 package failed its seal:\n" + "\n".join(seal_errors))
    integrity_after = check_evidence_integrity(package_dir, manifest)
    if integrity_after:
        raise VeriEnvelopeError("C1 package manifest drifted:\n" + "\n".join(integrity_after))
    return result


def _capability(judgment: ClaimJudgment, evidence_id: str, tested_under: str) -> dict[str, Any]:
    status = judgment.capability_status
    return {
        "capability_id": "C1",
        "claim": "C1 initialize",
        "testable_statement": judgment.note,
        "status": status,
        "supporting_evidence": [evidence_id] if status == "demonstrated" else [],
        "tested_under": tested_under,
        "notes": judgment.note,
    }


def _unrun(claim_id: str, note: str, tested_under: str) -> dict[str, Any]:
    return {
        "capability_id": claim_id,
        "claim": claim_id,
        "testable_statement": note,
        "status": "insufficient",
        "supporting_evidence": [],
        "tested_under": tested_under,
        "notes": note,
    }


def _boundary_dict(boundary: BoundaryObservation | None) -> dict[str, Any] | None:
    if boundary is None:
        return None
    return {
        "network_mode": boundary.network_mode,
        "readonly_rootfs": boundary.readonly_rootfs,
        "cap_drop": list(boundary.cap_drop),
        "security_opt": list(boundary.security_opt),
        "user": boundary.user,
        "pids_limit": boundary.pids_limit,
        "memory": boundary.memory,
        "nano_cpus": boundary.nano_cpus,
        "mount_sources": list(boundary.mount_sources),
        "env": list(boundary.env),
    }


def _notes(result: dict[str, Any], judgment: ClaimJudgment, sent: list[str]) -> str:
    return (
        "# C1 initialize\n\n"
        f"- 记录用途：{result['record_purpose']}\n"
        f"- 发送：{', '.join(sent) if sent else '没有发送'}\n"
        "- 没有发送：notifications/initialized、tools/list、tools/call\n"
        f"- 规则：{judgment.rule_id}\n"
        f"- 观察：{judgment.observation}\n"
        f"- 能力：{judgment.capability_status}\n"
        f"- 结果类别：{judgment.outcome_class}\n"
        f"- 准入：{result['admission']}\n\n"
        "这次只记录 C1。C1 demonstrated 不是组件准入，也不是 GATE 1。观察不是原因。\n"
        "package version 是源码 metadata，不是 npm registry 发布物。\n"
    )

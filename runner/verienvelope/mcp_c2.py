"""One new container for C2. Initialize is a prerequisite, not the primary claim.

This module does not send tools/call. It does not edit Run #1 and it does not
edit VE-METHOD-MCP-001 0.3.0.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
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
    EVERYTHING_TOOLS,
    PROTOCOL_VERSION,
    ClaimJudgment,
    encode_message,
    initialize_request,
    initialized_notification,
    judge_initialize,
    judge_tools,
    name_diff,
    read_until_response,
    tools_list_request,
)
from verienvelope.mcp_protocol import _tool_names
from verienvelope.package_seal import check_package_seal, write_package_seal
from verienvelope.pilot_preflight import run_authorized
from verienvelope.run import RUNNER_NAME, capture_environment
from verienvelope.sandbox import (
    SANDBOX_POLICY_VERSION,
    BoundaryObservation,
    RuntimeLimits,
    StdioSession,
    control_plane_env,
    split_container_env,
)
from verienvelope.schema_io import dump_json, load_yaml, repo_root, validate_instance

METHOD_VERSION = "0.3.0"
RUN1_EVIDENCE = "mcp.server-everything/2.0.0/run-b0a7fe2de38d42fd951a10d6cfa06e9a"
C2_LIMITS = RuntimeLimits(
    cpus="1",
    memory="512m",
    pids_limit=64,
    timeout_seconds=20,
    user="65532:65532",
)
_RULE_IDS = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10"]
_NOT_MEASURED = ClaimJudgment(
    "C2",
    "C2-not-measured",
    "not_run",
    "unclassified",
    "insufficient",
    "tools/list 没有发送。C2 没有被测量。",
)


@dataclass(frozen=True)
class C2Exchange:
    sent: tuple[str, ...]
    prerequisite: ClaimJudgment
    primary: ClaimJudgment
    measured: bool
    stdout: bytes
    initialize_response: bytes
    tools_response: bytes
    notification: bytes
    unmatched: tuple[dict[str, Any], ...]
    names: dict[str, Any]


def run_everything_c2(output_root: Path) -> dict[str, Any]:
    """External run #2. One new container. Stops after tools/list or earlier."""
    if not run_authorized():
        raise VeriEnvelopeError("external run #2 is not authorized")
    if _c2_already_recorded(output_root):
        raise VeriEnvelopeError("a C2 evidence package already exists; refusing another run")
    _require_method_unchanged()
    if _image_workdir(LOCAL_IMAGE_ID) != CONTAINER_WORKDIR:
        raise VeriEnvelopeError("Everything image workdir changed; C2 was not started")
    component = _everything_component()
    return run_c2_case(
        image=LOCAL_IMAGE_ID,
        command=list(CONTAINER_ARGV),
        output_root=output_root,
        expected_name="mcp-servers/everything",
        expected_version=PACKAGE_VERSION,
        expected_tools=frozenset(EVERYTHING_TOOLS),
        record_purpose="component_verification",
        component=component,
        allow_external=True,
    )


def run_c2_case(
    *,
    image: str,
    command: list[str],
    output_root: Path,
    expected_name: str,
    expected_version: str,
    expected_tools: frozenset[str],
    record_purpose: str,
    component: dict[str, Any],
    allow_external: bool = False,
) -> dict[str, Any]:
    if allow_external and image != LOCAL_IMAGE_ID:
        raise VeriEnvelopeError("external C2 must use the pinned local image id")
    if component.get("id") == "mcp.server-everything" and not allow_external:
        raise VeriEnvelopeError("refusing to start Everything outside run #2")
    limits = C2_LIMITS
    exchange: C2Exchange | None = None
    boundary: BoundaryObservation | None = None
    image_id = image
    exit_code: int | None = None
    stderr = b""
    try:
        with StdioSession(image=image, command=command, limits=limits) as session:
            image_id = session.image.image_id
            if allow_external and image_id != LOCAL_IMAGE_ID:
                raise VeriEnvelopeError("pinned image id did not match the running container")
            boundary = session.boundary
            if not _boundary_ok(boundary):
                exchange = _blocked()
            else:
                exchange = c2_exchange(
                    session.write_line,
                    session.read_line,
                    expected_name=expected_name,
                    expected_version=expected_version,
                    expected_tools=expected_tools,
                    timeout=limits.timeout_seconds,
                )
                session.close_stdin()
    except VeriEnvelopeError as exc:
        if exchange is not None and exchange.sent:
            raise
        exchange = _blocked(str(exc))
        stderr = str(exc).encode("utf-8")
    else:
        stderr = session.stderr
        exit_code = session.exit_code
        if not session.removed():
            raise VeriEnvelopeError("sandbox session was not removed")
    assert exchange is not None
    return _write_package(
        output_root=output_root,
        component=component,
        record_purpose=record_purpose,
        exchange=exchange,
        stdout=exchange.stdout,
        stderr=stderr,
        image_id=image_id,
        boundary=boundary,
        exit_code=exit_code,
        allow_external=allow_external,
    )


def c2_exchange(
    write_line,
    read_line,
    *,
    expected_name: str,
    expected_version: str,
    expected_tools: frozenset[str],
    timeout: float,
) -> C2Exchange:
    """Send initialize, then tools/list only if that prerequisite matches."""
    deadline = time.monotonic() + timeout
    sent: list[str] = []
    raw = bytearray()
    unmatched: list[dict[str, Any]] = []
    initialize = initialize_request()
    write_line(encode_message(initialize))
    sent.append("initialize")
    try:
        selected = _read(read_line, 1, deadline)
    except subprocess.TimeoutExpired:
        return _unmeasured(
            sent,
            ClaimJudgment(
                "C1",
                "M7",
                "execution_error",
                "unclassified",
                "insufficient",
                "等待 initialize 超时。原因未归类。",
            ),
            bytes(raw),
            b"",
            b"",
            b"",
            tuple(unmatched),
            expected_tools,
        )
    raw.extend(selected.raw)
    unmatched.extend(selected.unmatched)
    if selected.matched is None:
        prerequisite = ClaimJudgment(
            "C1",
            "M2",
            "execution_error",
            "unclassified",
            "not_demonstrated",
            "initialize 没有返回可对应的响应。原因未归类。",
        )
        return _unmeasured(
            sent, prerequisite, bytes(raw), selected.raw, b"", b"", tuple(unmatched), expected_tools
        )
    prerequisite = judge_initialize(
        selected.matched,
        expected_name=expected_name,
        expected_version=expected_version,
        expected_protocol=PROTOCOL_VERSION,
        expected_id=1,
    )
    if prerequisite.observation != "match":
        return _unmeasured(
            sent,
            prerequisite,
            bytes(raw),
            selected.raw,
            b"",
            b"",
            tuple(unmatched),
            expected_tools,
        )
    notification = encode_message(initialized_notification())
    write_line(notification)
    sent.append("notifications/initialized")
    listing = tools_list_request()
    write_line(encode_message(listing))
    sent.append("tools/list")
    try:
        listed = _read(read_line, 2, deadline)
    except subprocess.TimeoutExpired:
        primary = ClaimJudgment(
            "C2",
            "M7",
            "execution_error",
            "unclassified",
            "insufficient",
            "等待 tools/list 超时。原因未归类。",
        )
        return C2Exchange(
            tuple(sent),
            prerequisite,
            primary,
            True,
            bytes(raw),
            selected.raw,
            b"",
            notification,
            tuple(unmatched),
            name_diff(expected_tools, None),
        )
    raw.extend(listed.raw)
    unmatched.extend(listed.unmatched)
    actual = _tool_names(listed.matched)
    if listed.matched is None:
        primary = ClaimJudgment(
            "C2",
            "M2",
            "execution_error",
            "unclassified",
            "not_demonstrated",
            "tools/list 没有返回可对应的响应。原因未归类。",
        )
    else:
        primary = judge_tools(listed.matched, expected_names=expected_tools)
    return C2Exchange(
        tuple(sent),
        prerequisite,
        primary,
        True,
        bytes(raw),
        selected.raw,
        listed.raw,
        notification,
        tuple(unmatched),
        name_diff(expected_tools, actual),
    )


def _read(read_line, request_id: int, deadline: float):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise subprocess.TimeoutExpired("json-rpc", 0)
    return read_until_response(read_line, request_id, remaining)


def _unmeasured(
    sent: list[str],
    prerequisite: ClaimJudgment,
    stdout: bytes,
    initialize_response: bytes,
    tools_response: bytes,
    notification: bytes,
    unmatched: tuple[dict[str, Any], ...],
    expected_tools: frozenset[str],
) -> C2Exchange:
    return C2Exchange(
        tuple(sent),
        prerequisite,
        _NOT_MEASURED,
        False,
        stdout,
        initialize_response,
        tools_response,
        notification,
        unmatched,
        name_diff(expected_tools, None),
    )


def _blocked(detail: str = "") -> C2Exchange:
    note = "运行边界与方法不一致，initialize 没有发送。原因未归类。"
    if detail:
        note = note + " " + detail
    return C2Exchange(
        (),
        ClaimJudgment("C1", "M8", "blocked", "out_of_envelope", "insufficient", note),
        _NOT_MEASURED,
        False,
        b"",
        b"",
        b"",
        b"",
        (),
        name_diff(frozenset(EVERYTHING_TOOLS), None),
    )


def _require_method_unchanged() -> None:
    method = load_yaml(repo_root() / "methods" / "VE-METHOD-MCP-001" / "method.yaml")
    if str(method.get("version")) != METHOD_VERSION:
        raise VeriEnvelopeError("refusing to run because the method is not 0.3.0")
    offered = method["client_handshake"]["protocol_version_offered"]
    if offered != PROTOCOL_VERSION:
        raise VeriEnvelopeError("method protocolVersion and the executor constant diverged")
    names = set(method["claims"][1]["unconditional_tools"])
    if names != set(EVERYTHING_TOOLS):
        raise VeriEnvelopeError("C2 names in the method diverged from the executor constant")


def _c2_already_recorded(output_root: Path) -> bool:
    base = output_root / "mcp.server-everything"
    if not base.is_dir():
        return False
    for case_path in base.glob("**/input/case.json"):
        data = json.loads(case_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("primary_claim") == "C2":
            return True
    return False


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
    return (
        boundary.user == "65532:65532"
        and boundary.network_mode == "none"
        and boundary.readonly_rootfs
        and "ALL" in boundary.cap_drop
        and any("no-new-privileges" in item for item in boundary.security_opt)
        and not boundary.mount_sources
    )


def _everything_component() -> dict[str, Any]:
    return {
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


def _write_package(
    *,
    output_root: Path,
    component: dict[str, Any],
    record_purpose: str,
    exchange: C2Exchange,
    stdout: bytes,
    stderr: bytes,
    image_id: str,
    boundary: BoundaryObservation | None,
    exit_code: int | None,
    allow_external: bool,
) -> dict[str, Any]:
    validate_instance("component.schema.json", component)
    primary = exchange.primary
    run_id = new_id("run")
    evidence_id = new_id("ev")
    timestamp = utc_now()
    relative_dir = f"{component['id']}/{component['version']}/{run_id}"
    if relative_dir == RUN1_EVIDENCE:
        raise VeriEnvelopeError("refusing to write C2 into the C1 evidence directory")
    environment = capture_environment()
    config_env = tuple(boundary.env) if boundary is not None else ()
    split = split_container_env(config_env)
    provenance = (
        f"primary_claim C2. prerequisite C1 observation {exchange.prerequisite.observation}. "
        f"Run #1 remains at {RUN1_EVIDENCE}. "
        f"artifact_origin {ARTIFACT_ORIGIN}. local_image_id {image_id}. "
        "package_version is source metadata, not an npm registry artifact."
    )
    assurance = {
        "dependencies": [
            f"source package metadata {PACKAGE_NAME} {PACKAGE_VERSION}",
            f"local image {image_id}",
            f"sandbox {SANDBOX_POLICY_VERSION}",
            "OCI runtime",
        ],
        "permissions": ["stdio", "tmpfs /work", "user 65532:65532"],
        "execution_mode": "oci_runtime_network_none",
        "external_services": [],
        "provenance": provenance,
        "reproducibility_notes": (
            "Primary claim is C2. Prerequisite initialize is not a replacement of Run #1. "
            "Name differences are set descriptions, not causes. "
            f"artifact={json.dumps(execution_artifact() if allow_external else {'image_id': image_id}, sort_keys=True)} "
            f"env={json.dumps(split, sort_keys=True)}"
        ),
    }
    tested_under = (
        f"method VE-METHOD-MCP-001 {METHOD_VERSION}; primary C2; "
        f"image {image_id}; sandbox {SANDBOX_POLICY_VERSION}"
    )
    note = primary.note
    if exchange.names.get("missing") or exchange.names.get("unexpected"):
        note = (
            f"{note} missing={exchange.names.get('missing')} "
            f"unexpected={exchange.names.get('unexpected')}。这是集合差分，不是原因。"
        )
    capabilities = [
        {
            "capability_id": "C2",
            "claim": "C2 tools/list",
            "testable_statement": "tools/list 的 name 集合与预注册的 unconditional_tools 相等。",
            "status": primary.capability_status,
            "supporting_evidence": [evidence_id] if primary.capability_status == "demonstrated" else [],
            "tested_under": tested_under,
            "notes": note,
        },
        {
            "capability_id": "C3",
            "claim": "C3 echo",
            "testable_statement": "这次运行不发送 tools/call。",
            "status": "insufficient",
            "supporting_evidence": [],
            "tested_under": tested_under,
            "notes": "tools/call 没有发送。",
        },
    ]
    envelope = {
        "tested_conditions": [
            f"image_id={image_id}",
            "primary_claim=C2",
            "network none",
            "user 65532:65532",
        ],
        "known_limits": [
            "C3 没有执行",
            "C1 在这次会话里只是前置观察",
            "多出来的响应字段不进入判定",
        ],
        "known_failures": [] if primary.observation == "match" else [note],
        "untested_areas": [
            "不声明 production readiness",
            "不声明 security",
            "C3 echo",
        ],
        "environment_constraints": [
            f"{environment['os']} {environment['arch']}",
            "host environment is not inherited",
            "image-defined ENV is recorded separately from the process",
        ],
        "version_constraints": [f"method {METHOD_VERSION}", SANDBOX_POLICY_VERSION],
        "revalidation_triggers": ["method_revision", "runner_bug", "runtime"],
    }
    case = {
        "case_id": "c2-tools-list",
        "primary_claim": "C2",
        "method_version": METHOD_VERSION,
        "messages_sent": list(exchange.sent),
        "messages_not_sent": ["tools/call"],
        "prerequisite_c1": {
            "observation": exchange.prerequisite.observation,
            "capability_status": exchange.prerequisite.capability_status,
            "outcome_class": exchange.prerequisite.outcome_class,
            "rule_id": exchange.prerequisite.rule_id,
            "note": exchange.prerequisite.note,
            "replaces_run_1": False,
            "run_1_evidence": RUN1_EVIDENCE,
        },
        "tool_names": exchange.names,
        "tool_name_diff_is_not_a_cause": True,
        "record_purpose": record_purpose,
        "source_identity": source_identity() if allow_external else {"fixture": component["id"]},
        "execution_artifact": execution_artifact() if allow_external else {"image_id": image_id},
        "initialize_request": initialize_request(),
        "tools_list_request": tools_list_request() if "tools/list" in exchange.sent else None,
    }
    runtime = {
        "image_id": image_id,
        "exit_code": exit_code,
        "sandbox_policy": SANDBOX_POLICY_VERSION,
        "environment_boundary": split,
        "boundary": None
        if boundary is None
        else {
            "network_mode": boundary.network_mode,
            "readonly_rootfs": boundary.readonly_rootfs,
            "cap_drop": list(boundary.cap_drop),
            "security_opt": list(boundary.security_opt),
            "user": boundary.user,
            "pids_limit": boundary.pids_limit,
            "memory": boundary.memory,
            "nano_cpus": boundary.nano_cpus,
            "mount_sources": list(boundary.mount_sources),
        },
        "messages_sent": list(exchange.sent),
    }
    manifest = {
        "evidence_id": evidence_id,
        "run_id": run_id,
        "source_type": "ve_test",
        "method_id": "VE-METHOD-MCP-001",
        "method_version": METHOD_VERSION,
        "runner_version": __version__,
        "environment": environment,
        "fixture_id": "c2-tools-list",
        "timestamp": timestamp,
        "raw_artifact_path": relative_dir,
        "observation": primary.observation,
        "outcome_class": primary.outcome_class,
        "notes": (
            f"primary C2 rule {primary.rule_id}. "
            f"prerequisite C1 {exchange.prerequisite.observation}. {primary.note}"
        ),
    }
    result: dict[str, Any] = {
        "result_id": new_id("res"),
        "record_purpose": record_purpose,
        "component_id": component["id"],
        "component_version": str(component["version"]),
        "component_commit": component.get("commit"),
        "component_type": "mcp_server",
        "source_repository": component["source_repository"],
        "method_id": "VE-METHOD-MCP-001",
        "method_version": METHOD_VERSION,
        "runner_name": RUNNER_NAME,
        "runner_version": __version__,
        "implemented_rule_ids": _RULE_IDS,
        "rule_id": primary.rule_id,
        "environment": environment,
        "fixture_id": "c2-tools-list",
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
                reason=(
                    f"Run #2 primary C2. prerequisite C1 {exchange.prerequisite.observation}. "
                    f"Run #1 at {RUN1_EVIDENCE} is not replaced. {primary.note}"
                ),
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
    (input_dir / "initialize.request.log").write_bytes(encode_message(initialize_request()))
    (input_dir / "initialize.response.log").write_bytes(exchange.initialize_response)
    (input_dir / "initialized.notification.log").write_bytes(exchange.notification)
    (input_dir / "tools-list.request.log").write_bytes(
        encode_message(tools_list_request()) if "tools/list" in exchange.sent else b""
    )
    (input_dir / "tools-list.response.log").write_bytes(exchange.tools_response)
    dump_json(input_dir / "unmatched.json", list(exchange.unmatched))
    dump_json(package_dir / "runtime.json", runtime)
    (package_dir / "stdout.log").write_bytes(stdout)
    (package_dir / "stderr.log").write_bytes(stderr)
    manifest["artifacts"] = hash_package_files(package_dir)
    integrity_errors = check_evidence_integrity(package_dir, manifest)
    if integrity_errors:
        raise VeriEnvelopeError("C2 package failed raw integrity:\n" + "\n".join(integrity_errors))
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
        reasons = ["C3 was not executed; a C2 observation is not component admission", *reasons]
    result["admission"] = admission
    result["admission_reasons"] = reasons
    assert_consistent(result)
    validate_instance("verification_result.schema.json", result)
    validate_instance("evidence.schema.json", manifest)
    dump_json(package_dir / "manifest.json", manifest)
    dump_json(package_dir / "result.json", result)
    (package_dir / "notes.md").write_text(
        "# C2 tools/list\n\n"
        f"- 主测量：C2\n"
        f"- 前置 C1 观察：{exchange.prerequisite.observation}\n"
        f"- Run #1 仍在：{RUN1_EVIDENCE}\n"
        f"- 发送：{', '.join(exchange.sent) if exchange.sent else '没有发送'}\n"
        "- 没有发送：tools/call\n"
        f"- C2 观察：{primary.observation}\n"
        f"- C2 状态：{primary.capability_status}\n"
        f"- 结果类别：{primary.outcome_class}\n"
        f"- 准入：{admission}\n"
        f"- 名字差分：{json.dumps(exchange.names, ensure_ascii=False)}\n\n"
        "名字差分只描述集合。它不是原因。这次不覆盖 Run #1，也不执行 C3。\n",
        encoding="utf-8",
    )
    write_package_seal(package_dir)
    seal_errors = check_package_seal(package_dir)
    if seal_errors:
        raise VeriEnvelopeError("C2 package failed its seal:\n" + "\n".join(seal_errors))
    return result

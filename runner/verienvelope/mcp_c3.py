"""One new container for C3. C1 and C2 are prerequisites, not the primary claim.

This module sends tools/call only after both prerequisites match. It does not
edit earlier evidence packages or VE-METHOD-MCP-001 0.3.0. It does not create
another capability.
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
    identity_reference,
    source_identity,
)
from verienvelope.consistency import assert_consistent
from verienvelope.envelope import claim_envelope
from verienvelope.errors import VeriEnvelopeError
from verienvelope.evidence_integrity import check_evidence_integrity, hash_package_files
from verienvelope.history import make_event, new_id, utc_now
from verienvelope.mcp_protocol import (
    ECHO_MESSAGE,
    ECHO_TEXT,
    ECHO_TOOL,
    EVERYTHING_TOOLS,
    PROTOCOL_VERSION,
    ClaimJudgment,
    encode_message,
    initialize_request,
    initialized_notification,
    judge_echo,
    judge_initialize,
    judge_tools,
    name_diff,
    read_until_response,
    tools_call_echo_request,
    tools_list_request,
)
from verienvelope.mcp_protocol import _tool_names
from verienvelope.package_seal import check_package_seal, write_package_seal
from verienvelope.pilot_preflight import run3_authorized
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
RUN2_EVIDENCE = "mcp.server-everything/2.0.0/run-b32dbaa357824eb0a7a9474cf35b7d34"
C3_LIMITS = RuntimeLimits(
    cpus="1",
    memory="512m",
    pids_limit=64,
    timeout_seconds=20,
    user="65532:65532",
)
_RULE_IDS = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10"]
_REVALIDATION = [
    "source_commit",
    "execution_artifact",
    "method_version",
    "runner_version",
    "protocol",
]
_NOT_MEASURED = ClaimJudgment(
    "C3",
    "C3-not-measured",
    "not_run",
    "unclassified",
    "insufficient",
    "tools/call 没有发送。C3 没有被测量。",
)
_C2_NOT_RUN = ClaimJudgment(
    "C2",
    "C2-not-measured",
    "not_run",
    "unclassified",
    "insufficient",
    "tools/list 没有发送。",
)


@dataclass(frozen=True)
class C3Exchange:
    sent: tuple[str, ...]
    prerequisite_c1: ClaimJudgment
    prerequisite_c2: ClaimJudgment
    primary: ClaimJudgment
    measured: bool
    stdout: bytes
    initialize_response: bytes
    tools_response: bytes
    echo_response: bytes
    notification: bytes
    unmatched: tuple[dict[str, Any], ...]
    names: dict[str, Any]


def run_everything_c3(output_root: Path) -> dict[str, Any]:
    """External run #3. One new container. Stops after one echo call or earlier."""
    if not run3_authorized():
        raise VeriEnvelopeError("external run #3 is not authorized")
    if _c3_already_recorded(output_root):
        raise VeriEnvelopeError("a C3 evidence package already exists; refusing another run")
    _require_method_unchanged()
    if _image_workdir(LOCAL_IMAGE_ID) != CONTAINER_WORKDIR:
        raise VeriEnvelopeError("Everything image workdir changed; C3 was not started")
    return run_c3_case(
        image=LOCAL_IMAGE_ID,
        command=list(CONTAINER_ARGV),
        output_root=output_root,
        expected_name="mcp-servers/everything",
        expected_version=PACKAGE_VERSION,
        expected_tools=frozenset(EVERYTHING_TOOLS),
        record_purpose="component_verification",
        component=_everything_component(),
        allow_external=True,
    )


def run_c3_case(
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
        raise VeriEnvelopeError("external C3 must use the pinned local image id")
    if component.get("id") == "mcp.server-everything" and not allow_external:
        raise VeriEnvelopeError("refusing to start Everything outside run #3")
    limits = C3_LIMITS
    exchange: C3Exchange | None = None
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
                exchange = c3_exchange(
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
        expected_name=expected_name,
        expected_version=expected_version,
        expected_tools=expected_tools,
    )


def c3_exchange(
    write_line,
    read_line,
    *,
    expected_name: str,
    expected_version: str,
    expected_tools: frozenset[str],
    timeout: float,
) -> C3Exchange:
    """Replay initialize and tools/list. Call echo only if both match."""
    deadline = time.monotonic() + timeout
    sent: list[str] = []
    raw = bytearray()
    unmatched: list[dict[str, Any]] = []
    write_line(encode_message(initialize_request()))
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
            _C2_NOT_RUN,
            bytes(raw),
            b"",
            b"",
            b"",
            b"",
            (),
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
    else:
        prerequisite = judge_initialize(
            selected.matched,
            expected_name=expected_name,
            expected_version=expected_version,
        )
    if prerequisite.observation != "match":
        return _unmeasured(
            sent,
            prerequisite,
            _C2_NOT_RUN,
            bytes(raw),
            selected.raw,
            b"",
            b"",
            b"",
            tuple(unmatched),
            expected_tools,
        )
    notification = encode_message(initialized_notification())
    write_line(notification)
    sent.append("notifications/initialized")
    write_line(encode_message(tools_list_request()))
    sent.append("tools/list")
    try:
        listed = _read(read_line, 2, deadline)
    except subprocess.TimeoutExpired:
        return _unmeasured(
            sent,
            prerequisite,
            ClaimJudgment(
                "C2",
                "M7",
                "execution_error",
                "unclassified",
                "insufficient",
                "等待 tools/list 超时。原因未归类。",
            ),
            bytes(raw),
            selected.raw,
            b"",
            notification,
            tuple(unmatched),
            expected_tools,
        )
    raw.extend(listed.raw)
    unmatched.extend(listed.unmatched)
    actual = _tool_names(listed.matched)
    if listed.matched is None:
        tools_judgment = ClaimJudgment(
            "C2",
            "M2",
            "execution_error",
            "unclassified",
            "not_demonstrated",
            "tools/list 没有返回可对应的响应。原因未归类。",
        )
    else:
        tools_judgment = judge_tools(listed.matched, expected_names=expected_tools)
    if tools_judgment.observation != "match":
        return _unmeasured(
            sent,
            prerequisite,
            tools_judgment,
            bytes(raw),
            selected.raw,
            listed.raw,
            b"",
            notification,
            tuple(unmatched),
            expected_tools,
            actual,
        )
    call = tools_call_echo_request()
    write_line(encode_message(call))
    sent.append("tools/call")
    try:
        echoed = _read(read_line, 3, deadline)
    except subprocess.TimeoutExpired:
        primary = ClaimJudgment(
            "C3",
            "M7",
            "execution_error",
            "unclassified",
            "insufficient",
            "等待 tools/call 超时。原因未归类。",
        )
        return C3Exchange(
            tuple(sent),
            prerequisite,
            tools_judgment,
            primary,
            True,
            bytes(raw),
            selected.raw,
            listed.raw,
            b"",
            notification,
            tuple(unmatched),
            name_diff(expected_tools, actual),
        )
    raw.extend(echoed.raw)
    unmatched.extend(echoed.unmatched)
    if echoed.matched is None:
        primary = ClaimJudgment(
            "C3",
            "M2",
            "execution_error",
            "unclassified",
            "not_demonstrated",
            "tools/call 没有返回可对应的响应。原因未归类。",
        )
    else:
        primary = judge_echo(echoed.matched, expected_text=ECHO_TEXT)
    return C3Exchange(
        tuple(sent),
        prerequisite,
        tools_judgment,
        primary,
        True,
        bytes(raw),
        selected.raw,
        listed.raw,
        echoed.raw,
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
    prerequisite_c1: ClaimJudgment,
    prerequisite_c2: ClaimJudgment,
    stdout: bytes,
    initialize_response: bytes,
    tools_response: bytes,
    echo_response: bytes,
    notification: bytes,
    unmatched: tuple[dict[str, Any], ...],
    expected_tools: frozenset[str],
    actual: frozenset[str] | None = None,
) -> C3Exchange:
    return C3Exchange(
        tuple(sent),
        prerequisite_c1,
        prerequisite_c2,
        _NOT_MEASURED,
        False,
        stdout,
        initialize_response,
        tools_response,
        echo_response,
        notification,
        unmatched,
        name_diff(expected_tools, actual),
    )


def _blocked(detail: str = "") -> C3Exchange:
    note = "运行边界与方法不一致，initialize 没有发送。原因未归类。"
    if detail:
        note = note + " " + detail
    blocked = ClaimJudgment("C1", "M8", "blocked", "out_of_envelope", "insufficient", note)
    return C3Exchange(
        (),
        blocked,
        _C2_NOT_RUN,
        _NOT_MEASURED,
        False,
        b"",
        b"",
        b"",
        b"",
        b"",
        (),
        name_diff(frozenset(), None),
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
    echo = method["claims"][2]
    if echo.get("tool") != ECHO_TOOL:
        raise VeriEnvelopeError("C3 tool diverged from the executor constant")
    if echo.get("arguments", {}).get("message") != ECHO_MESSAGE:
        raise VeriEnvelopeError("C3 echo message diverged from the executor constant")
    if ECHO_TEXT not in echo.get("expected_observation", ""):
        raise VeriEnvelopeError("C3 expected text diverged from the executor constant")


def _c3_already_recorded(output_root: Path) -> bool:
    base = output_root / "mcp.server-everything"
    if not base.is_dir():
        return False
    for case_path in base.glob("**/input/case.json"):
        data = json.loads(case_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("primary_claim") == "C3":
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


def _claim_views(
    *,
    image_id: str,
    expected_name: str,
    expected_version: str,
    expected_tools: frozenset[str],
) -> dict[str, dict[str, list[str]]]:
    unknown = [
        "其他 source commit 未测",
        "其他 execution artifact 未测",
        "其他 transport 未测",
        "非空 client capabilities 未测",
        "不声明 production readiness",
        "不声明 security",
        "不声明 general reliability",
    ]
    shared = [
        f"image_id={image_id}",
        "transport stdio",
        "client capabilities {}",
        f"protocolVersion {PROTOCOL_VERSION}",
        f"sandbox {SANDBOX_POLICY_VERSION}",
    ]
    return {
        "C1": claim_envelope(
            tested_conditions=[
                *shared,
                f"serverInfo.name {expected_name}",
                f"serverInfo.version {expected_version}",
            ],
            known_limits=[],
            untested_areas=[*unknown, "initialize 之后的工具行为不是 C1"],
            revalidation_triggers=_REVALIDATION,
        ),
        "C2": claim_envelope(
            tested_conditions=[
                *shared,
                "names " + ", ".join(sorted(expected_tools)),
                "order is irrelevant",
                "description inputSchema annotations and title are not asserted",
            ],
            known_limits=[],
            untested_areas=[*unknown, "非空 client capabilities 下的工具集合未由 C2 实测"],
            revalidation_triggers=_REVALIDATION,
        ),
        "C3": claim_envelope(
            tested_conditions=[
                *shared,
                f"tool {ECHO_TOOL}",
                f"arguments.message {ECHO_MESSAGE}",
                f"text item type=text text={ECHO_TEXT}",
                "other response fields are not asserted",
            ],
            known_limits=[],
            untested_areas=[*unknown, "其他 tool 未测", "只断言这一条 echo 文本"],
            revalidation_triggers=_REVALIDATION,
        ),
    }


def _capability(
    judgment: ClaimJudgment,
    *,
    statement: str,
    evidence_id: str,
    tested_under: str,
    envelope: dict[str, list[str]],
) -> dict[str, Any]:
    demonstrated = judgment.capability_status == "demonstrated"
    return {
        "capability_id": judgment.claim_id,
        "claim": judgment.claim_id,
        "testable_statement": statement,
        "status": judgment.capability_status,
        "supporting_evidence": [evidence_id] if demonstrated else [],
        "tested_under": tested_under,
        "notes": judgment.note,
        "envelope": envelope,
    }


def _write_package(
    *,
    output_root: Path,
    component: dict[str, Any],
    record_purpose: str,
    exchange: C3Exchange,
    stdout: bytes,
    stderr: bytes,
    image_id: str,
    boundary: BoundaryObservation | None,
    exit_code: int | None,
    allow_external: bool,
    expected_name: str,
    expected_version: str,
    expected_tools: frozenset[str],
) -> dict[str, Any]:
    evidence_id = new_id("ev")
    run_id = new_id("run")
    timestamp = utc_now()
    version = str(component["version"])
    relative_dir = f"{component['id']}/{version}/{run_id}"
    if relative_dir in {RUN1_EVIDENCE, RUN2_EVIDENCE}:
        raise VeriEnvelopeError("refusing to overwrite an earlier evidence package")
    environment = capture_environment()
    primary = exchange.primary
    views = _claim_views(
        image_id=image_id,
        expected_name=expected_name,
        expected_version=expected_version,
        expected_tools=expected_tools,
    )
    tested_under = (
        f"method VE-METHOD-MCP-001 {METHOD_VERSION}; primary C3; "
        f"image {image_id}; sandbox {SANDBOX_POLICY_VERSION}"
    )
    if (
        primary.observation == "match"
        and exchange.prerequisite_c1.observation == "match"
        and exchange.prerequisite_c2.observation == "match"
    ):
        capabilities = [
            _capability(
                exchange.prerequisite_c1,
                statement="initialize 的 id、protocolVersion 和 serverInfo 符合预注册条件。",
                evidence_id=evidence_id,
                tested_under=tested_under,
                envelope=views["C1"],
            ),
            _capability(
                exchange.prerequisite_c2,
                statement="tools/list 的 name 集合与这次预注册的集合相等。",
                evidence_id=evidence_id,
                tested_under=tested_under,
                envelope=views["C2"],
            ),
            _capability(
                primary,
                statement=f"echo 的文本断言是 {ECHO_TEXT}。",
                evidence_id=evidence_id,
                tested_under=tested_under,
                envelope=views["C3"],
            ),
        ]
    else:
        capabilities = [
            _capability(
                primary,
                statement=f"echo 的文本断言是 {ECHO_TEXT}。这次没有把它测成一条新能力。",
                evidence_id=evidence_id,
                tested_under=tested_under,
                envelope=views["C3"],
            )
        ]
    if any(item["capability_id"] == "C4" for item in capabilities):
        raise VeriEnvelopeError("refusing to create a capability beyond C3")
    reference = ""
    if allow_external:
        reference = identity_reference(source_identity(), execution_artifact())
    provenance = (
        f"primary_claim C3. prerequisite C1 {exchange.prerequisite_c1.observation}. "
        f"prerequisite C2 {exchange.prerequisite_c2.observation}. "
        f"Run #1 remains at {RUN1_EVIDENCE}. Run #2 remains at {RUN2_EVIDENCE}. "
        f"artifact_origin {ARTIFACT_ORIGIN}. local_image_id {image_id}. "
        "package_version is source metadata, not an npm registry artifact. "
        f"identity_reference {reference or 'fixture'}."
    )
    split = split_container_env(boundary.env if boundary is not None else [])
    assurance = {
        "dependencies": [
            f"source package metadata {PACKAGE_NAME} {PACKAGE_VERSION}"
            if allow_external
            else "controlled fixture",
            f"local image {image_id}",
            f"sandbox {SANDBOX_POLICY_VERSION}",
        ],
        "permissions": ["stdio", "tmpfs /work", "user 65532:65532"],
        "execution_mode": "oci_runtime_network_none",
        "external_services": [],
        "provenance": provenance,
        "reproducibility_notes": (
            "Primary claim is C3. Prerequisite observations do not replace earlier runs. "
            "The echo assertion is one text item. "
            f"identity_reference={reference}"
        ),
    }
    envelope = {
        "tested_conditions": views["C3"]["tested_conditions"],
        "known_limits": [],
        "known_failures": [] if primary.observation == "match" else [primary.note],
        "untested_areas": views["C3"]["untested_areas"],
        "environment_constraints": [
            f"{environment['os']} {environment['arch']}",
            "host environment is not inherited",
            "image-defined ENV is recorded separately from the process",
        ],
        "version_constraints": [f"method {METHOD_VERSION}", f"runner {__version__}"],
        "revalidation_triggers": list(_REVALIDATION),
    }
    case = {
        "case_id": "c3-echo",
        "primary_claim": "C3",
        "method_version": METHOD_VERSION,
        "messages_sent": list(exchange.sent),
        "messages_not_sent": [
            name
            for name in ("initialize", "notifications/initialized", "tools/list", "tools/call")
            if name not in exchange.sent
        ],
        "prerequisite_c1": _judgment_record(exchange.prerequisite_c1),
        "prerequisite_c2": _judgment_record(exchange.prerequisite_c2),
        "replaces_earlier_runs": False,
        "run_1_evidence": RUN1_EVIDENCE,
        "run_2_evidence": RUN2_EVIDENCE,
        "echo_request": tools_call_echo_request() if "tools/call" in exchange.sent else None,
        "record_purpose": record_purpose,
        "source_identity": source_identity() if allow_external else {"fixture": component["id"]},
        "execution_artifact": execution_artifact() if allow_external else {"image_id": image_id},
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
        "fixture_id": "c3-echo",
        "timestamp": timestamp,
        "raw_artifact_path": relative_dir,
        "observation": primary.observation,
        "outcome_class": primary.outcome_class,
        "notes": (
            f"primary C3 rule {primary.rule_id}. "
            f"prerequisite C1 {exchange.prerequisite_c1.observation}. "
            f"prerequisite C2 {exchange.prerequisite_c2.observation}. {primary.note}"
        ),
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
        "rule_id": primary.rule_id,
        "environment": environment,
        "fixture_id": "c3-echo",
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
                    f"Run #3 primary C3. "
                    f"prerequisite C1 {exchange.prerequisite_c1.observation}. "
                    f"prerequisite C2 {exchange.prerequisite_c2.observation}. "
                    "Earlier runs are not replaced. "
                    f"{primary.note}"
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
    dump_json(
        input_dir / "artifact.json",
        execution_artifact() if allow_external else {"image_id": image_id},
    )
    (input_dir / "initialize.request.log").write_bytes(encode_message(initialize_request()))
    (input_dir / "initialize.response.log").write_bytes(exchange.initialize_response)
    (input_dir / "initialized.notification.log").write_bytes(exchange.notification)
    (input_dir / "tools-list.request.log").write_bytes(
        encode_message(tools_list_request()) if "tools/list" in exchange.sent else b""
    )
    (input_dir / "tools-list.response.log").write_bytes(exchange.tools_response)
    (input_dir / "tools-call.request.log").write_bytes(
        encode_message(tools_call_echo_request()) if "tools/call" in exchange.sent else b""
    )
    (input_dir / "tools-call.response.log").write_bytes(exchange.echo_response)
    dump_json(input_dir / "unmatched.json", list(exchange.unmatched))
    dump_json(package_dir / "runtime.json", runtime)
    (package_dir / "stdout.log").write_bytes(stdout)
    (package_dir / "stderr.log").write_bytes(stderr)
    manifest["artifacts"] = hash_package_files(package_dir)
    integrity_errors = check_evidence_integrity(package_dir, manifest)
    if integrity_errors:
        raise VeriEnvelopeError("C3 package failed raw integrity:\n" + "\n".join(integrity_errors))
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
    (package_dir / "notes.md").write_text(_notes(exchange, admission, reference), encoding="utf-8")
    write_package_seal(package_dir)
    seal_errors = check_package_seal(package_dir)
    if seal_errors:
        raise VeriEnvelopeError("C3 package failed its seal:\n" + "\n".join(seal_errors))
    return result


def _judgment_record(judgment: ClaimJudgment) -> dict[str, Any]:
    return {
        "observation": judgment.observation,
        "capability_status": judgment.capability_status,
        "outcome_class": judgment.outcome_class,
        "rule_id": judgment.rule_id,
        "note": judgment.note,
        "replaces_earlier_run": False,
    }


def _notes(exchange: C3Exchange, admission: str, reference: str) -> str:
    meaning = ""
    if admission == "admitted":
        meaning = (
            "admitted 只表示声明范围内可以进入当前 registry。"
            "它不是认证，不是推荐，也不是生产级。\n"
        )
    return (
        "# C3 echo\n\n"
        "- 主测量：C3\n"
        f"- 前置 C1 观察：{exchange.prerequisite_c1.observation}\n"
        f"- 前置 C2 观察：{exchange.prerequisite_c2.observation}\n"
        f"- Run #1 仍在：{RUN1_EVIDENCE}\n"
        f"- Run #2 仍在：{RUN2_EVIDENCE}\n"
        f"- 发送：{', '.join(exchange.sent) if exchange.sent else '没有发送'}\n"
        f"- C3 观察：{exchange.primary.observation}\n"
        f"- C3 状态：{exchange.primary.capability_status}\n"
        f"- 结果类别：{exchange.primary.outcome_class}\n"
        f"- 准入：{admission}\n"
        f"- identity reference：{reference or 'fixture'}\n"
        "- 已观察到的限制：没有\n\n"
        "前置观察不覆盖以前的运行。多出来的响应字段不进入判定。没有新的能力编号。\n"
        f"{meaning}"
    )

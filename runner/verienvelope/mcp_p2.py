"""Pilot #2 runner. One primary claim per invocation. It does not edit method 0.1.0.

A mismatch stops later messages in this process. Another primary claim needs
its own authorization. This module does not start Pilot #3.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from verienvelope import __version__
from verienvelope.admission import evaluate_admission
from verienvelope.consistency import assert_consistent
from verienvelope.envelope import claim_envelope
from verienvelope.errors import VeriEnvelopeError
from verienvelope.evidence_integrity import check_evidence_integrity, hash_package_files
from verienvelope.history import make_event, new_id, utc_now
from verienvelope.mcp_protocol import (
    ClaimJudgment,
    encode_message,
    initialize_request,
    initialized_notification,
    name_diff,
    read_until_response,
)
from verienvelope.package_seal import check_package_seal, write_package_seal
from verienvelope.pilot_preflight import append_authorization_consumed, consumed_runs
from verienvelope.run import capture_environment
from verienvelope.sandbox import (
    SANDBOX_POLICY_VERSION,
    BoundaryObservation,
    RuntimeLimits,
    StdioSession,
    split_container_env,
)
from verienvelope.schema_io import dump_json, load_json, load_yaml, repo_root, validate_instance

METHOD_ID = "VE-METHOD-MCP-002"
METHOD_VERSION = "0.4.0"
RUNNER_NAME = "verienvelope-mcp-p2"
PRIMARY_ORDER = ("C1", "C2", "C3")
TITLE_SUBSTRING = "- Page Title: ve-pilot-2"
NAVIGATE_URL = "file:///app/fixture/ve-pilot-2.html"
_REVALIDATION = [
    "method_revision",
    "runner_bug",
    "runtime",
    "relevant_dependency",
    "protocol",
]
_RULE_IDS = [
    "P2-M1",
    "P2-M2",
    "P2-M3",
    "P2-M4",
    "P2-M5",
    "P2-M6",
    "P2-M7",
    "P2-M8",
    "P2-M9",
    "P2-M10",
    "P2-M11",
]


@dataclass
class P2Exchange:
    primary: str
    sent: list[str] = field(default_factory=list)
    stdout: bytes = b""
    unmatched: list[dict[str, Any]] = field(default_factory=list)
    judgments: dict[str, ClaimJudgment] = field(default_factory=dict)
    transport: dict[str, ClaimJudgment] = field(default_factory=dict)
    name_comparison: dict[str, Any] | None = None
    requests: dict[str, dict[str, Any]] = field(default_factory=dict)


def method_path() -> Path:
    return repo_root() / "methods" / "VE-METHOD-MCP-002" / "method.yaml"


def load_method() -> dict[str, Any]:
    method = load_yaml(method_path())
    if method.get("id") != METHOD_ID or str(method.get("version")) != METHOD_VERSION:
        raise VeriEnvelopeError(f"VE-METHOD-MCP-002 {METHOD_VERSION} is not the file on disk")
    if method["execution"]["sandbox_policy"] != SANDBOX_POLICY_VERSION:
        raise VeriEnvelopeError("method sandbox policy does not match the runner contract")
    return method


def planned_run_for(primary: str) -> str:
    if primary not in PRIMARY_ORDER:
        raise VeriEnvelopeError(f"unknown primary claim: {primary}")
    return f"external-run-p2-{PRIMARY_ORDER.index(primary) + 1}"


def authorization_path(primary: str) -> Path:
    return repo_root() / "registry" / "runs" / f"{planned_run_for(primary)}.json"


def recorded_judgments(judgments: dict[str, ClaimJudgment]) -> dict[str, dict[str, str]]:
    """Keep claim ids. Message names such as initialize are transport bookkeeping."""
    return {
        claim_id: {
            "rule_id": item.rule_id,
            "observation": item.observation,
            "outcome_class": item.outcome_class,
            "capability_status": item.capability_status,
            "note": item.note,
        }
        for claim_id, item in judgments.items()
        if claim_id in PRIMARY_ORDER
    }


def run_pilot2(
    output_root: Path,
    primary: str,
    planned_run: str | None = None,
) -> dict[str, Any]:
    """Execute one authorized primary claim. Refuses a consumed authorization."""
    if primary not in PRIMARY_ORDER:
        raise VeriEnvelopeError(f"unknown primary claim: {primary}")
    method = load_method()
    image = str(method["execution"]["local_image_id"])
    if not image.startswith("sha256:"):
        raise VeriEnvelopeError("local image is not pinned; refusing to start")
    planned = planned_run or planned_run_for(primary)
    if planned in consumed_runs():
        raise VeriEnvelopeError(f"{planned} is already consumed")
    _require_authorization(primary, image, planned)
    _require_previous_match(output_root, primary)
    append_authorization_consumed(
        planned,
        path=repo_root() / "registry" / "runs" / "authorization-events.jsonl",
        recorded_at=utc_now(),
        note="Pilot #2 authorization consumed at start. The authorization file is not rewritten.",
    )
    component = _component(method)
    limits = RuntimeLimits()
    exchange: P2Exchange | None = None
    boundary: BoundaryObservation | None = None
    exit_code: int | None = None
    stderr = b""
    image_id = image
    try:
        with StdioSession(
            image=image,
            command=["/app/start.sh"],
            limits=limits,
        ) as session:
            image_id = session.image.image_id
            if image_id != image:
                raise VeriEnvelopeError("running image id does not match the method pin")
            boundary = session.boundary
            if not _boundary_ok(boundary):
                exchange = _stopped(primary, _blocked())
            else:
                exchange = _exchange(session, method, primary, timeout=25)
                session.close_stdin()
    except VeriEnvelopeError as exc:
        if exchange is not None and exchange.sent:
            raise
        exchange = _stopped(primary, _blocked(str(exc)))
        stderr = str(exc).encode("utf-8")
    else:
        stderr = session.stderr
        exit_code = session.exit_code
        if not session.removed():
            raise VeriEnvelopeError("sandbox session was not removed")
    assert exchange is not None
    return _write_package(
        output_root=output_root,
        method=method,
        component=component,
        exchange=exchange,
        stdout=exchange.stdout,
        stderr=stderr,
        image_id=image_id,
        boundary=boundary,
        exit_code=exit_code,
    )


def judge_initialize(message: dict[str, Any] | None, method: dict[str, Any]) -> ClaimJudgment:
    identity = method["identity"]
    if message is None or message.get("jsonrpc") != "2.0" or message.get("id") != 1:
        return _unparsed("C1")
    if "error" in message:
        return _unparsed("C1")
    result = message.get("result")
    if not isinstance(result, dict):
        return _unparsed("C1")
    if result.get("protocolVersion") != "2025-03-26":
        return ClaimJudgment(
            "C1",
            "P2-M4",
            "mismatch",
            "unclassified",
            "not_demonstrated",
            "C1 的 protocolVersion 没有被 demonstrated。原因未归类。",
        )
    info = result.get("serverInfo")
    if not isinstance(info, dict):
        return _unparsed("C1")
    if info.get("name") != identity["server_name"] or info.get("version") != identity["server_version"]:
        return ClaimJudgment(
            "C1",
            "P2-M3",
            "mismatch",
            "unclassified",
            "not_demonstrated",
            "C1 的 serverInfo 没有被 demonstrated。原因未归类。",
        )
    return ClaimJudgment(
        "C1",
        "P2-M1",
        "match",
        "confirmed",
        "demonstrated",
        "C1 的 protocolVersion 与 serverInfo 符合运行前写下的字符串。",
    )


def judge_tools(message: dict[str, Any] | None, expected: frozenset[str]) -> ClaimJudgment:
    names = _tool_names(message)
    if names is None:
        return _unparsed("C2")
    if names != expected:
        return ClaimJudgment(
            "C2",
            "P2-M6",
            "mismatch",
            "unclassified",
            "not_demonstrated",
            "C2 没有被 demonstrated。原因未归类。",
        )
    return ClaimJudgment(
        "C2",
        "P2-M5",
        "match",
        "confirmed",
        "demonstrated",
        "C2 与运行前抽出的名字集合一致。",
    )


def judge_navigate(message: dict[str, Any] | None) -> ClaimJudgment:
    texts = _text_values(message)
    if texts is None:
        return _unparsed("C3")
    if not any(TITLE_SUBSTRING in text for text in texts):
        return ClaimJudgment(
            "C3",
            "P2-M8",
            "mismatch",
            "unclassified",
            "not_demonstrated",
            "C3 没有被 demonstrated。原因未归类。",
        )
    return ClaimJudgment(
        "C3",
        "P2-M7",
        "match",
        "confirmed",
        "demonstrated",
        "C3 只证明标题子串 - Page Title: ve-pilot-2。",
    )


def _exchange(session: StdioSession, method: dict[str, Any], primary: str, timeout: float) -> P2Exchange:
    exchange = P2Exchange(primary=primary)
    _send(session, exchange, "initialize", initialize_request(), 1, timeout)
    exchange.judgments["C1"] = _timeout_or(exchange, "C1", judge_initialize(exchange.requests.get("initialize-response"), method))
    if primary == "C1" or exchange.judgments["C1"].observation != "match":
        if primary != "C1":
            exchange.judgments[primary] = _not_sent(primary)
        return exchange
    _send_notice(session, exchange, initialized_notification())
    expected = frozenset(_claim(method, "C2")["core_tools"])
    _send(session, exchange, "tools/list", _tools_list(), 2, timeout)
    listed = exchange.requests.get("tools/list-response")
    exchange.judgments["C2"] = _timeout_or(exchange, "C2", judge_tools(listed, expected))
    exchange.name_comparison = name_diff(expected, _tool_names(listed))
    if primary == "C2" or exchange.judgments["C2"].observation != "match":
        if primary != "C2":
            exchange.judgments["C3"] = _not_sent("C3")
        return exchange
    _send(session, exchange, "tools/call", _navigate_request(), 3, timeout)
    exchange.judgments["C3"] = _timeout_or(exchange, "C3", judge_navigate(exchange.requests.get("tools/call-response")))
    return exchange


def _send(session: StdioSession, exchange: P2Exchange, name: str, payload: dict[str, Any], request_id: int, timeout: float) -> None:
    raw = encode_message(payload)
    exchange.stdout += raw
    exchange.requests[name] = payload
    exchange.sent.append(name)
    session.write_line(raw)
    try:
        selected = read_until_response(session.read_line, request_id, timeout)
    except Exception:
        exchange.transport[name] = _timed_out(name)
        return
    exchange.stdout += selected.raw
    exchange.unmatched.extend(selected.unmatched)
    exchange.requests[f"{name}-response"] = selected.matched or {}
    if selected.matched is None:
        exchange.transport[name] = _unparsed(_claim_for_message(name))


def _send_notice(session: StdioSession, exchange: P2Exchange, payload: dict[str, Any]) -> None:
    raw = encode_message(payload)
    exchange.stdout += raw
    exchange.sent.append("notifications/initialized")
    session.write_line(raw)


def _timeout_or(exchange: P2Exchange, claim: str, judgment: ClaimJudgment) -> ClaimJudgment:
    early = exchange.transport.get(_message_for(claim))
    if early is not None and early.rule_id == "P2-M9":
        return ClaimJudgment(claim, "P2-M9", "execution_error", "unclassified", "insufficient", early.note)
    return judgment


def _message_for(claim: str) -> str:
    return {"C1": "initialize", "C2": "tools/list", "C3": "tools/call"}[claim]


def _claim_for_message(name: str) -> str:
    return {"initialize": "C1", "tools/list": "C2", "tools/call": "C3"}[name]


def _tools_list() -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}


def _navigate_request() -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "browser_navigate", "arguments": {"url": NAVIGATE_URL}},
    }


def _tool_names(message: dict[str, Any] | None) -> frozenset[str] | None:
    if not message or "error" in message:
        return None
    result = message.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("tools"), list):
        return None
    names: list[str] = []
    for item in result["tools"]:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            return None
        names.append(item["name"])
    return frozenset(names)


def _text_values(message: dict[str, Any] | None) -> list[str] | None:
    if not message or "error" in message:
        return None
    result = message.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("content"), list):
        return None
    texts: list[str] = []
    for item in result["content"]:
        if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
            texts.append(item["text"])
    return texts


def _unparsed(claim: str) -> ClaimJudgment:
    return ClaimJudgment(
        claim,
        "P2-M2",
        "execution_error",
        "unclassified",
        "not_demonstrated",
        f"{claim} 没有可解析的对应响应。原因未归类。",
    )


def _timed_out(name: str) -> ClaimJudgment:
    claim = _claim_for_message(name)
    return ClaimJudgment(
        claim,
        "P2-M9",
        "execution_error",
        "unclassified",
        "insufficient",
        "超时本身不能分成服务器、浏览器、运行时或方法的错。",
    )


def _blocked(detail: str = "") -> ClaimJudgment:
    note = "目标进程没有在本方法的边界内完成这次观察。这不是组件失败的判定。"
    if detail:
        note = f"{note} {detail}"
    return ClaimJudgment("C1", "P2-M10", "blocked", "out_of_envelope", "insufficient", note)


def _not_sent(claim: str) -> ClaimJudgment:
    return ClaimJudgment(
        claim,
        "P2-M11",
        "not_run",
        "unclassified",
        "insufficient",
        "前置 claim 与预期冲突，因此没有发送这条 primary。",
    )


def _stopped(primary: str, judgment: ClaimJudgment) -> P2Exchange:
    exchange = P2Exchange(primary=primary)
    exchange.judgments[primary] = ClaimJudgment(
        primary,
        judgment.rule_id,
        judgment.observation,
        judgment.outcome_class,
        judgment.capability_status,
        judgment.note,
    )
    return exchange


def _require_authorization(primary: str, image: str, planned: str) -> None:
    path = repo_root() / "registry" / "runs" / f"{planned}.json"
    if not path.is_file():
        raise VeriEnvelopeError(f"missing authorization for {primary}")
    data = load_json(path)
    expected = {
        "authorized": True,
        "planned_run": planned,
        "primary_claim": primary,
        "method_version": METHOD_VERSION,
        "execution_artifact": image,
        "sandbox_policy": SANDBOX_POLICY_VERSION,
    }
    for key, value in expected.items():
        if data.get(key) != value:
            raise VeriEnvelopeError(f"authorization field {key} does not match this run")


def _require_previous_match(output_root: Path, primary: str) -> None:
    index = PRIMARY_ORDER.index(primary)
    if index == 0:
        return
    previous = PRIMARY_ORDER[index - 1]
    if _latest_observation(output_root, previous) != "match":
        raise VeriEnvelopeError(
            f"refusing {primary}: {previous} does not have a match package. "
            "This is not a retry."
        )


def _latest_observation(output_root: Path, claim: str) -> str | None:
    root = output_root / "mcp.playwright-mcp" / "0.0.82"
    if not root.is_dir():
        return None
    matches: list[tuple[str, str]] = []
    for result_path in root.glob("run-*/result.json"):
        result = load_json(result_path)
        if result.get("rule_id") in _RULE_IDS and _primary_of(result) == claim:
            matches.append((result.get("timestamp", ""), result.get("observation", "")))
    if not matches:
        return None
    matches.sort()
    return matches[-1][1]


def _primary_of(result: dict[str, Any]) -> str:
    fixture = str(result.get("fixture_id") or "")
    if fixture.startswith("p2-"):
        return fixture.removeprefix("p2-").upper()
    return ""


def _component(method: dict[str, Any]) -> dict[str, Any]:
    identity = method["identity"]
    return {
        "id": identity["component_id"],
        "name": "Playwright MCP",
        "component_type": "mcp_server",
        "description": (
            "MCP server from microsoft/playwright-mcp. "
            "package_version is source metadata, not a verified npm artifact."
        ),
        "source_repository": identity["repository"],
        "license": "Apache-2.0",
        "version": identity["package_version"],
        "commit": identity["commit"],
        "publisher": "Microsoft",
        "status": "candidate",
    }


def _claim(method: dict[str, Any], claim_id: str) -> dict[str, Any]:
    for claim in method["claims"]:
        if claim["id"] == claim_id:
            return claim
    raise VeriEnvelopeError(f"method is missing {claim_id}")


def _views(method: dict[str, Any], image_id: str) -> dict[str, dict[str, list[str]]]:
    shared = [
        f"image_id={image_id}",
        "transport stdio",
        "client capabilities {}",
        "protocolVersion 2025-03-26",
        f"sandbox {SANDBOX_POLICY_VERSION}",
        "memory 512m",
        "pids 64",
    ]
    unknown = [
        "其他 commit 未测",
        "真实网站未测",
        "宿主文件系统未测",
        "不声明 production readiness",
        "不声明 security",
    ]
    return {
        "C1": claim_envelope(
            tested_conditions=[
                *shared,
                f"serverInfo.name {method['identity']['server_name']}",
                f"serverInfo.version {method['identity']['server_version']}",
            ],
            known_limits=[],
            untested_areas=[*unknown, "initialize 之后的工具行为不是 C1"],
            revalidation_triggers=_REVALIDATION,
        ),
        "C2": claim_envelope(
            tested_conditions=[*shared, "core tool name set", "order is irrelevant"],
            known_limits=[],
            untested_areas=[*unknown, "skillOnly 工具不在预期集合里"],
            revalidation_triggers=_REVALIDATION,
        ),
        "C3": claim_envelope(
            tested_conditions=[*shared, "tool browser_navigate", f"url {NAVIGATE_URL}", f"substring {TITLE_SUBSTRING}"],
            known_limits=[],
            untested_areas=[*unknown, "整份 snapshot 未断言"],
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


def assemble_capabilities(
    judgments: dict[str, ClaimJudgment],
    *,
    primary: str,
    statements: dict[str, str],
    views: dict[str, dict[str, list[str]]],
    tested_under: str,
    evidence_id: str,
) -> list[dict[str, Any]]:
    """Keep a measured prerequisite. Not being the primary claim is not insufficient."""
    capabilities = []
    for claim_id in PRIMARY_ORDER:
        judgment = judgments.get(claim_id)
        if judgment is None:
            capabilities.append(_unrun(claim_id, "这一次没有发送。", tested_under, views[claim_id]))
            continue
        capabilities.append(
            _capability(
                judgment,
                statement=statements[claim_id],
                evidence_id=evidence_id,
                tested_under=tested_under,
                envelope=views[claim_id],
            )
        )
    return capabilities


def _unrun(claim_id: str, note: str, tested_under: str, envelope: dict[str, list[str]]) -> dict[str, Any]:
    return {
        "capability_id": claim_id,
        "claim": claim_id,
        "testable_statement": note,
        "status": "insufficient",
        "supporting_evidence": [],
        "tested_under": tested_under,
        "notes": note,
        "envelope": envelope,
    }


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
    method: dict[str, Any],
    component: dict[str, Any],
    exchange: P2Exchange,
    stdout: bytes,
    stderr: bytes,
    image_id: str,
    boundary: BoundaryObservation | None,
    exit_code: int | None,
) -> dict[str, Any]:
    validate_instance("component.schema.json", component)
    primary = exchange.judgments[exchange.primary]
    run_id = new_id("run")
    evidence_id = new_id("ev")
    timestamp = utc_now()
    version = str(component["version"])
    relative_dir = f"{component['id']}/{version}/{run_id}"
    environment = capture_environment()
    tested_under = (
        f"method {METHOD_ID} {METHOD_VERSION}; primary {exchange.primary}; "
        f"image {image_id}; sandbox {SANDBOX_POLICY_VERSION}"
    )
    views = _views(method, image_id)
    statements = {
        "C1": "initialize 的 protocolVersion 与 serverInfo 符合运行前字符串。",
        "C2": "tools/list 的 name 集合等于预注册的 core_tools。",
        "C3": f"browser_navigate 的文本包含 {TITLE_SUBSTRING}。",
    }
    capabilities = assemble_capabilities(
        exchange.judgments,
        primary=exchange.primary,
        statements=statements,
        views=views,
        tested_under=tested_under,
        evidence_id=evidence_id,
    )
    envelope = {
        "tested_conditions": views[exchange.primary]["tested_conditions"],
        "known_limits": [],
        "known_failures": [] if primary.observation == "match" else [primary.note],
        "untested_areas": views[exchange.primary]["untested_areas"],
        "environment_constraints": [
            f"{environment['os']} {environment['arch']}",
            "host environment is not inherited",
            "cpus 1, memory 512m, pids 64, network none",
        ],
        "version_constraints": [f"method {METHOD_VERSION}"],
        "revalidation_triggers": list(_REVALIDATION),
    }
    split = split_container_env(boundary.env if boundary is not None else [])
    assurance = {
        "dependencies": [
            "source package metadata @playwright/mcp 0.0.82",
            f"playwright-core {method['execution']['playwright_core']}",
            f"local image {image_id}",
            "OCI runtime",
        ],
        "permissions": ["stdio", "tmpfs /work", "tmpfs /tmp", "user 65532:65532"],
        "execution_mode": "oci_runtime_network_none",
        "external_services": [],
        "provenance": (
            f"primary {exchange.primary}. commit {component['commit']}. "
            f"artifact_origin locally_built_from_pinned_source. local_image_id {image_id}. "
            "package_version is source metadata, not an npm registry artifact."
        ),
        "reproducibility_notes": (
            "Compare observation, outcome class, and capability status. Ignore run_id. "
            "A match is not certification."
        ),
    }
    manifest = {
        "evidence_id": evidence_id,
        "run_id": run_id,
        "source_type": "ve_test",
        "method_id": METHOD_ID,
        "method_version": METHOD_VERSION,
        "runner_version": __version__,
        "environment": environment,
        "fixture_id": f"p2-{exchange.primary.lower()}",
        "timestamp": timestamp,
        "raw_artifact_path": relative_dir,
        "observation": primary.observation,
        "outcome_class": primary.outcome_class,
        "notes": f"primary {exchange.primary} rule {primary.rule_id}. {primary.note}",
    }
    result: dict[str, Any] = {
        "result_id": new_id("res"),
        "record_purpose": "component_verification",
        "component_id": component["id"],
        "component_version": version,
        "component_commit": component.get("commit"),
        "component_type": "mcp_server",
        "source_repository": component["source_repository"],
        "method_id": METHOD_ID,
        "method_version": METHOD_VERSION,
        "runner_name": RUNNER_NAME,
        "runner_version": __version__,
        "implemented_rule_ids": _RULE_IDS,
        "rule_id": primary.rule_id,
        "environment": environment,
        "fixture_id": f"p2-{exchange.primary.lower()}",
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
        "admission_reasons": ["pending"],
    }
    package_dir = output_root / relative_dir
    package_dir.mkdir(parents=True, exist_ok=False)
    input_dir = package_dir / "input"
    input_dir.mkdir()
    dump_json(package_dir / "environment.json", environment)
    dump_json(input_dir / "component.json", component)
    dump_json(
        input_dir / "case.json",
        {
            "case_id": f"p2-{exchange.primary.lower()}",
            "primary_claim": exchange.primary,
            "messages_sent": list(exchange.sent),
            "name_comparison": exchange.name_comparison,
            "method_version": METHOD_VERSION,
            "judgments": recorded_judgments(exchange.judgments),
        },
    )
    dump_json(input_dir / "artifact.json", {"local_image_id": image_id, "artifact_origin": "locally_built_from_pinned_source"})
    (input_dir / "request.log").write_bytes(stdout)
    if exchange.unmatched:
        dump_json(package_dir / "unmatched.json", exchange.unmatched)
    dump_json(
        package_dir / "runtime.json",
        {
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
        },
    )
    (package_dir / "stdout.log").write_bytes(stdout)
    (package_dir / "stderr.log").write_bytes(stderr)
    manifest["artifacts"] = hash_package_files(package_dir)
    admission, reasons = evaluate_admission(
        result,
        component,
        [manifest],
        package_dir=package_dir,
        manifest=manifest,
        check_seal=False,
    )
    if exchange.primary != "C3" and admission == "admitted":
        admission = "insufficient"
        reasons = ["later primary claims were not executed in this pilot chain", *reasons]
    result["admission"] = admission
    result["admission_reasons"] = reasons
    assert_consistent(result)
    validate_instance("verification_result.schema.json", result)
    validate_instance("evidence.schema.json", manifest)
    dump_json(package_dir / "manifest.json", manifest)
    dump_json(package_dir / "result.json", result)
    (package_dir / "notes.md").write_text(
        "\n".join(
            [
                f"# Pilot #2 {exchange.primary}",
                "",
                f"observation: {primary.observation}",
                f"rule: {primary.rule_id}",
                f"outcome_class: {primary.outcome_class}",
                f"admission: {admission}",
                "",
                primary.note,
                "",
                "admitted 只表示当前政策允许这条记录进入声明范围，不是认证，也不是推荐。",
                "We verify declared claims. We do not decide fitness for your use.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    write_package_seal(package_dir)
    seal_errors = check_package_seal(package_dir)
    if seal_errors:
        raise VeriEnvelopeError("package failed its seal:\n" + "\n".join(seal_errors))
    integrity_after = check_evidence_integrity(package_dir, manifest)
    if integrity_after:
        raise VeriEnvelopeError("package manifest drifted:\n" + "\n".join(integrity_after))
    return result


def seal_partial_package(package_dir: Path) -> dict[str, Any]:
    """Seal logs that were already written. Does not start a container."""
    from datetime import datetime, timezone

    package_dir = package_dir.resolve()
    if (package_dir / "result.json").exists() or (package_dir / "seal.json").exists():
        raise VeriEnvelopeError("refusing to rewrite a package that already has a result")
    case = load_json(package_dir / "input" / "case.json")
    component = load_json(package_dir / "input" / "component.json")
    environment = load_json(package_dir / "environment.json")
    runtime = load_json(package_dir / "runtime.json")
    validate_instance("component.schema.json", component)
    method = load_method()
    primary_id = str(case["primary_claim"])
    if primary_id not in PRIMARY_ORDER:
        raise VeriEnvelopeError("partial package has no primary claim")
    judgments = {
        claim_id: ClaimJudgment(
            claim_id,
            item["rule_id"],
            item["observation"],
            item["outcome_class"],
            item["capability_status"],
            item["note"],
        )
        for claim_id, item in case["judgments"].items()
    }
    primary = judgments[primary_id]
    image_id = str(runtime["image_id"])
    run_id = package_dir.name
    version = str(component["version"])
    relative_dir = f"{component['id']}/{version}/{run_id}"
    expected = (repo_root() / "evidence" / relative_dir).resolve()
    if package_dir != expected:
        raise VeriEnvelopeError("partial package is not the evidence path for this run")
    if str(case["method_version"]) != METHOD_VERSION:
        raise VeriEnvelopeError("partial package method version does not match the runner")
    timestamp = datetime.fromtimestamp(
        (package_dir / "stdout.log").stat().st_mtime, timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    evidence_id = new_id("ev")
    tested_under = (
        f"method {METHOD_ID} {METHOD_VERSION}; primary {primary_id}; "
        f"image {image_id}; sandbox {SANDBOX_POLICY_VERSION}"
    )
    views = _views(method, image_id)
    statements = {
        "C1": "initialize 的 protocolVersion 与 serverInfo 符合运行前字符串。",
        "C2": "tools/list 的 name 集合等于预注册的 core_tools。",
        "C3": f"browser_navigate 的文本包含 {TITLE_SUBSTRING}。",
    }
    capabilities = assemble_capabilities(
        judgments,
        primary=primary_id,
        statements=statements,
        views=views,
        tested_under=tested_under,
        evidence_id=evidence_id,
    )
    envelope = {
        "tested_conditions": views[primary_id]["tested_conditions"],
        "known_limits": [],
        "known_failures": [] if primary.observation == "match" else [primary.note],
        "untested_areas": views[primary_id]["untested_areas"],
        "environment_constraints": [
            f"{environment['os']} {environment['arch']}",
            "host environment is not inherited",
            "cpus 1, memory 512m, pids 64, network none",
        ],
        "version_constraints": [f"method {METHOD_VERSION}"],
        "revalidation_triggers": list(_REVALIDATION),
    }
    assurance = {
        "dependencies": [
            "source package metadata @playwright/mcp 0.0.82",
            f"playwright-core {method['execution']['playwright_core']}",
            f"local image {image_id}",
            "OCI runtime",
        ],
        "permissions": ["stdio", "tmpfs /work", "tmpfs /tmp", "user 65532:65532"],
        "execution_mode": "oci_runtime_network_none",
        "external_services": [],
        "provenance": (
            f"primary {primary_id}. commit {component['commit']}. "
            f"artifact_origin locally_built_from_pinned_source. local_image_id {image_id}. "
            "package_version is source metadata, not an npm registry artifact."
        ),
        "reproducibility_notes": (
            "Compare observation, outcome class, and capability status. Ignore run_id. "
            "A match is not certification."
        ),
    }
    manifest = {
        "evidence_id": evidence_id,
        "run_id": run_id,
        "source_type": "ve_test",
        "method_id": METHOD_ID,
        "method_version": METHOD_VERSION,
        "runner_version": __version__,
        "environment": environment,
        "fixture_id": f"p2-{primary_id.lower()}",
        "timestamp": timestamp,
        "raw_artifact_path": relative_dir,
        "observation": primary.observation,
        "outcome_class": primary.outcome_class,
        "notes": f"primary {primary_id} rule {primary.rule_id}. {primary.note}",
    }
    result: dict[str, Any] = {
        "result_id": new_id("res"),
        "record_purpose": "component_verification",
        "component_id": component["id"],
        "component_version": version,
        "component_commit": component.get("commit"),
        "component_type": "mcp_server",
        "source_repository": component["source_repository"],
        "method_id": METHOD_ID,
        "method_version": METHOD_VERSION,
        "runner_name": RUNNER_NAME,
        "runner_version": __version__,
        "implemented_rule_ids": _RULE_IDS,
        "rule_id": primary.rule_id,
        "environment": environment,
        "fixture_id": f"p2-{primary_id.lower()}",
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
        "admission_reasons": ["pending"],
    }
    manifest["artifacts"] = hash_package_files(package_dir)
    admission, reasons = evaluate_admission(
        result,
        component,
        [manifest],
        package_dir=package_dir,
        manifest=manifest,
        check_seal=False,
    )
    if primary_id != "C3" and admission == "admitted":
        admission = "insufficient"
        reasons = ["later primary claims were not executed in this pilot chain", *reasons]
    result["admission"] = admission
    result["admission_reasons"] = reasons
    assert_consistent(result)
    validate_instance("verification_result.schema.json", result)
    validate_instance("evidence.schema.json", manifest)
    dump_json(package_dir / "manifest.json", manifest)
    dump_json(package_dir / "result.json", result)
    (package_dir / "notes.md").write_text(
        "\n".join(
            [
                f"# Pilot #2 {primary_id}",
                "",
                f"observation: {primary.observation}",
                f"rule: {primary.rule_id}",
                f"outcome_class: {primary.outcome_class}",
                f"admission: {admission}",
                "",
                primary.note,
                "",
                "admitted 只表示当前政策允许这条记录进入声明范围，不是认证，也不是推荐。",
                "We verify declared claims. We do not decide fitness for your use.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    write_package_seal(package_dir)
    seal_errors = check_package_seal(package_dir)
    if seal_errors:
        raise VeriEnvelopeError("package failed its seal:\n" + "\n".join(seal_errors))
    integrity_after = check_evidence_integrity(package_dir, manifest)
    if integrity_after:
        raise VeriEnvelopeError("package manifest drifted:\n" + "\n".join(integrity_after))
    return result


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run one Pilot #2 primary claim")
    parser.add_argument("--primary", required=True, choices=list(PRIMARY_ORDER))
    parser.add_argument("--planned-run", default=None)
    parser.add_argument("--output-root", type=Path, default=repo_root() / "evidence")
    args = parser.parse_args()
    result = run_pilot2(args.output_root, args.primary, planned_run=args.planned_run)
    print(json.dumps({"run_id": result["run_id"], "observation": result["observation"], "rule_id": result["rule_id"], "admission": result["admission"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

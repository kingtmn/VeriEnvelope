"""Pilot #4 runner. One primary claim: convert a fixed clock time.

The expected time difference is read from the method. This module does not
start another pilot and does not edit earlier evidence.
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
    read_until_response,
    tools_list_request,
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

METHOD_ID = "VE-METHOD-MCP-004"
METHOD_VERSION = "0.1.0"
RUNNER_NAME = "verienvelope-mcp-p4"
PRIMARY_ORDER = ("S1", "S2", "R1")
_RULE_IDS = [
    "P4-M1",
    "P4-M2",
    "P4-M3",
    "P4-M4",
    "P4-M5",
    "P4-M7",
    "P4-M8",
    "P4-M9",
    "P4-M10",
    "P4-M11",
]
_RULE_FIELDS = ("when", "observation", "outcome_class", "capability_status", "run_note")
_CAPABILITY_STATUSES = frozenset(
    {"demonstrated", "not_demonstrated", "insufficient", "unknown", "out_of_envelope"}
)
_REVALIDATION = [
    "commit 变化",
    "local image 变化",
    "sandbox policy 变化",
    "tzdata 版本变化",
    "预注册子串变化",
]


@dataclass
class P4Exchange:
    primary: str
    sent: list[str] = field(default_factory=list)
    stdout: bytes = b""
    judgments: dict[str, ClaimJudgment] = field(default_factory=dict)
    transport: dict[str, ClaimJudgment] = field(default_factory=dict)
    requests: dict[str, dict[str, Any]] = field(default_factory=dict)
    unmatched: list[dict[str, Any]] = field(default_factory=list)


def method_path() -> Path:
    return repo_root() / "methods" / "VE-METHOD-MCP-004" / "method.yaml"


def load_method() -> dict[str, Any]:
    method = load_yaml(method_path())
    if method.get("id") != METHOD_ID or str(method.get("version")) != METHOD_VERSION:
        raise VeriEnvelopeError(f"{METHOD_ID} {METHOD_VERSION} is not the file on disk")
    if method["execution"]["sandbox_policy"] != SANDBOX_POLICY_VERSION:
        raise VeriEnvelopeError("method sandbox policy does not match the runner contract")
    rule_table(method)
    return method


def rule_table(method: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Every rule the runner selects must carry its own normative labels."""
    raw = method.get("classification_rules")
    if not isinstance(raw, list) or not raw:
        raise VeriEnvelopeError("method has no classification_rules")
    table: dict[str, dict[str, str]] = {}
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            raise VeriEnvelopeError("classification rule is missing an id")
        rule_id = item["id"]
        if rule_id in table:
            raise VeriEnvelopeError(f"duplicate rule id {rule_id}")
        fields: dict[str, str] = {}
        for field in _RULE_FIELDS:
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                raise VeriEnvelopeError(f"rule {rule_id} is missing {field}")
            fields[field] = value
        if fields["capability_status"] not in _CAPABILITY_STATUSES:
            raise VeriEnvelopeError(f"rule {rule_id} has an unknown capability_status")
        table[rule_id] = fields
    missing = [rule_id for rule_id in _RULE_IDS if rule_id not in table]
    if missing:
        raise VeriEnvelopeError("method is missing rules the runner selects: " + ", ".join(missing))
    return table


def apply_rule(method: dict[str, Any], claim_id: str, rule_id: str) -> ClaimJudgment:
    rule = rule_table(method)[rule_id]
    return ClaimJudgment(
        claim_id,
        rule_id,
        rule["observation"],
        rule["outcome_class"],
        rule["capability_status"],
        rule["run_note"],
    )


def expected_substring(method: dict[str, Any]) -> str:
    text = method["execution"]["text_substring"]
    if not isinstance(text, str) or not text:
        raise VeriEnvelopeError("method has no text_substring")
    return text


def run_pilot4(output_root: Path, planned_run: str) -> dict[str, Any]:
    method = load_method()
    expected = expected_substring(method)
    image = str(method["execution"]["local_image_id"])
    if not image.startswith("sha256:"):
        raise VeriEnvelopeError("local image is not pinned; refusing to start")
    if planned_run in consumed_runs():
        raise VeriEnvelopeError(f"{planned_run} is already consumed")
    _require_authorization(image, planned_run)
    append_authorization_consumed(
        planned_run,
        path=repo_root() / "registry" / "runs" / "authorization-events.jsonl",
        recorded_at=utc_now(),
        note="Pilot #4 authorization consumed at start. The authorization file is not rewritten.",
    )
    component = _component(method)
    limits = RuntimeLimits()
    exchange: P4Exchange | None = None
    boundary: BoundaryObservation | None = None
    exit_code: int | None = None
    stderr = b""
    image_id = image
    try:
        with StdioSession(image=image, command=["/app/start.sh"], limits=limits) as session:
            image_id = session.image.image_id
            if image_id != image:
                raise VeriEnvelopeError("running image id does not match the method pin")
            boundary = session.boundary
            if not _boundary_ok(boundary):
                exchange = _stopped(apply_rule(method, "R1", "P4-M10"))
            else:
                exchange = _exchange(session, method, expected, timeout=float(method["execution"]["timeout_seconds"]))
                session.close_stdin()
    except VeriEnvelopeError as exc:
        if exchange is not None and exchange.sent:
            raise
        exchange = _stopped(apply_rule(method, "R1", "P4-M10"))
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
        expected=expected,
    )


def judge_session(method: dict[str, Any], message: dict[str, Any] | None) -> ClaimJudgment:
    if message is None or message.get("jsonrpc") != "2.0" or message.get("id") != 1 or "error" in message:
        return apply_rule(method, "S1", "P4-M2")
    result = message.get("result")
    if not isinstance(result, dict):
        return apply_rule(method, "S1", "P4-M2")
    info = result.get("serverInfo")
    if not isinstance(info, dict):
        return apply_rule(method, "S1", "P4-M3")
    execution = method["execution"]
    matched = (
        result.get("protocolVersion") == execution["protocol_version"]
        and info.get("name") == execution["server_name"]
        and info.get("version") == execution["server_version"]
    )
    return apply_rule(method, "S1", "P4-M1" if matched else "P4-M3")


def judge_discovery(method: dict[str, Any], message: dict[str, Any] | None) -> ClaimJudgment:
    names = _tool_names(message)
    if names is None:
        return apply_rule(method, "S2", "P4-M2")
    if method["execution"]["tool_name"] not in names:
        return apply_rule(method, "S2", "P4-M5")
    return apply_rule(method, "S2", "P4-M4")


def judge_convert(method: dict[str, Any], message: dict[str, Any] | None, expected: str) -> ClaimJudgment:
    texts = _text_values(message)
    if texts is None:
        return apply_rule(method, "R1", "P4-M2")
    result = message["result"] if isinstance(message, dict) else {}
    found = any(expected in item for item in texts)
    if not isinstance(result, dict) or result.get("isError") is True or not found:
        return apply_rule(method, "R1", "P4-M8")
    return apply_rule(method, "R1", "P4-M7")


def _exchange(session: StdioSession, method: dict[str, Any], expected: str, timeout: float) -> P4Exchange:
    exchange = P4Exchange(primary="R1")
    _send(session, exchange, method, "initialize", initialize_request(), 1, timeout)
    exchange.judgments["S1"] = _timeout_or(
        method, exchange, "initialize", judge_session(method, exchange.requests.get("initialize-response"))
    )
    if exchange.judgments["S1"].observation != "match":
        exchange.judgments["S2"] = apply_rule(method, "S2", "P4-M11")
        exchange.judgments["R1"] = apply_rule(method, "R1", "P4-M11")
        return exchange
    _send_notice(session, exchange, initialized_notification())
    _send(session, exchange, method, "tools/list", tools_list_request(), 2, timeout)
    exchange.judgments["S2"] = _timeout_or(
        method, exchange, "tools/list", judge_discovery(method, exchange.requests.get("tools/list-response"))
    )
    if exchange.judgments["S2"].observation != "match":
        exchange.judgments["R1"] = apply_rule(method, "R1", "P4-M11")
        return exchange
    _send(session, exchange, method, "tools/call", _convert_request(method), 3, timeout)
    exchange.judgments["R1"] = _timeout_or(
        method, exchange, "tools/call", judge_convert(method, exchange.requests.get("tools/call-response"), expected)
    )
    return exchange


def _convert_request(method: dict[str, Any]) -> dict[str, Any]:
    execution = method["execution"]
    return {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": execution["tool_name"], "arguments": dict(execution["arguments"])},
    }


def _send(
    session: StdioSession,
    exchange: P4Exchange,
    method: dict[str, Any],
    name: str,
    payload: dict[str, Any],
    request_id: int,
    timeout: float,
) -> None:
    raw = encode_message(payload)
    exchange.stdout += raw
    exchange.requests[name] = payload
    exchange.sent.append(name)
    session.write_line(raw)
    try:
        selected = read_until_response(session.read_line, request_id, timeout)
    except Exception:
        claim = "S1" if name == "initialize" else "S2" if name == "tools/list" else "R1"
        exchange.transport[name] = apply_rule(method, claim, "P4-M9")
        return
    exchange.stdout += selected.raw
    exchange.unmatched.extend(selected.unmatched)
    exchange.requests[f"{name}-response"] = selected.matched or {}
    if selected.matched is None:
        claim = "S1" if name == "initialize" else "S2" if name == "tools/list" else "R1"
        exchange.transport[name] = apply_rule(method, claim, "P4-M2")


def _send_notice(session: StdioSession, exchange: P4Exchange, payload: dict[str, Any]) -> None:
    raw = encode_message(payload)
    exchange.stdout += raw
    exchange.sent.append("notifications/initialized")
    session.write_line(raw)


def _timeout_or(
    method: dict[str, Any], exchange: P4Exchange, message: str, judgment: ClaimJudgment
) -> ClaimJudgment:
    early = exchange.transport.get(message)
    if early is not None and early.rule_id == "P4-M9":
        return apply_rule(method, judgment.claim_id, "P4-M9")
    if early is not None and early.rule_id == "P4-M2":
        return apply_rule(method, judgment.claim_id, "P4-M2")
    return judgment


def _require_authorization(image: str, planned: str) -> None:
    path = repo_root() / "registry" / "runs" / f"{planned}.json"
    data = load_json(path)
    expected = {
        "authorized": True,
        "planned_run": planned,
        "primary_claim": "R1",
        "method_version": METHOD_VERSION,
        "execution_artifact": image,
        "sandbox_policy": SANDBOX_POLICY_VERSION,
    }
    for key, value in expected.items():
        if data.get(key) != value:
            raise VeriEnvelopeError(f"authorization field {key} does not match this run")


def _component(method: dict[str, Any]) -> dict[str, Any]:
    identity = method["identity"]
    return {
        "id": identity["component_id"],
        "name": "Time MCP",
        "component_type": "mcp_server",
        "description": (
            "MCP server from modelcontextprotocol/servers src/time. "
            "package_version is source metadata, not a verified package registry artifact."
        ),
        "source_repository": identity["repository"],
        "license": "MIT",
        "version": identity["package_version"],
        "commit": identity["commit"],
        "publisher": "Model Context Protocol a Series of LF Projects, LLC.",
        "status": "candidate",
    }


def _views(method: dict[str, Any], image_id: str) -> dict[str, dict[str, list[str]]]:
    shared = [
        f"image_id={image_id}",
        "transport stdio",
        "client capabilities {}",
        "protocolVersion 2025-03-26",
        f"sandbox {SANDBOX_POLICY_VERSION}",
        "local timezone UTC",
        f"tzdata {method['execution']['tzdata_version']}",
    ]
    unknown = [
        "get_current_time 未测",
        "日期、星期和 is_dst 未测",
        "其他时区对未测",
        "夏令时切换日未测",
    ]
    execution = method["execution"]
    tool_name = execution["tool_name"]
    return {
        "S1": claim_envelope(
            tested_conditions=[
                *shared,
                f"protocolVersion {execution['protocol_version']}",
                f"serverInfo.name {execution['server_name']}",
                f"serverInfo.version {execution['server_version']}",
            ],
            known_limits=[],
            untested_areas=[*unknown],
            revalidation_triggers=_REVALIDATION,
        ),
        "S2": claim_envelope(
            tested_conditions=[*shared, f"tool name {tool_name} is present"],
            known_limits=[],
            untested_areas=[*unknown, "其余工具名不要求一致"],
            revalidation_triggers=_REVALIDATION,
        ),
        "R1": claim_envelope(
            tested_conditions=[*shared, f"tool {tool_name}", "UTC 12:00 to Asia/Tokyo", "time_difference substring"],
            known_limits=[],
            untested_areas=[*unknown],
            revalidation_triggers=_REVALIDATION,
        ),
    }


def _write_package(
    *,
    output_root: Path,
    method: dict[str, Any],
    component: dict[str, Any],
    exchange: P4Exchange,
    stdout: bytes,
    stderr: bytes,
    image_id: str,
    boundary: BoundaryObservation | None,
    exit_code: int | None,
    expected: str,
) -> dict[str, Any]:
    validate_instance("component.schema.json", component)
    primary = exchange.judgments["R1"]
    run_id = new_id("run")
    evidence_id = new_id("ev")
    timestamp = utc_now()
    version = str(component["version"])
    relative_dir = f"{component['id']}/{version}/{run_id}"
    environment = capture_environment()
    tested_under = (
        f"method {METHOD_ID} {METHOD_VERSION}; primary R1; "
        f"image {image_id}; sandbox {SANDBOX_POLICY_VERSION}"
    )
    views = _views(method, image_id)
    statements = {
        "S1": "initialize 的协议版本、服务器名和服务器版本与方法一致。",
        "S2": "tools/list 包含 convert_time。",
        "R1": "convert_time 的文本包含预注册的 time_difference。",
    }
    capabilities = []
    for claim_id in PRIMARY_ORDER:
        judgment = exchange.judgments.get(claim_id)
        if judgment is None:
            judgment = apply_rule(method, claim_id, "P4-M11")
        demonstrated = judgment.capability_status == "demonstrated"
        capabilities.append(
            {
                "capability_id": claim_id,
                "claim": claim_id,
                "testable_statement": statements[claim_id],
                "status": judgment.capability_status,
                "supporting_evidence": [evidence_id] if demonstrated else [],
                "tested_under": tested_under,
                "notes": judgment.note,
                "envelope": views[claim_id],
            }
        )
    envelope = {
        "tested_conditions": views["R1"]["tested_conditions"],
        "known_limits": [],
        "known_failures": [] if primary.observation == "match" else [primary.note],
        "untested_areas": views["R1"]["untested_areas"],
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
            "source package metadata mcp-server-time 0.6.2",
            f"local image {image_id}",
            "OCI runtime",
        ],
        "permissions": ["stdio", "tmpfs /work", "tmpfs /tmp", "user 65532:65532"],
        "execution_mode": "oci_runtime_network_none",
        "external_services": [],
        "provenance": (
            f"primary R1. commit {component['commit']}. "
            f"artifact_origin locally_built_from_pinned_source. local_image_id {image_id}. "
            f"tzdata {method['execution']['tzdata_version']}. "
            "package_version is source metadata, not a package registry artifact."
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
        "fixture_id": "p4-r1",
        "timestamp": timestamp,
        "raw_artifact_path": relative_dir,
        "observation": primary.observation,
        "outcome_class": primary.outcome_class,
        "notes": f"primary R1 rule {primary.rule_id}. {primary.note}",
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
        "fixture_id": "p4-r1",
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
            "case_id": "p4-r1",
            "primary_claim": "R1",
            "messages_sent": list(exchange.sent),
            "method_version": METHOD_VERSION,
            "expected_text": expected,
            "judgments": {
                claim_id: {
                    "rule_id": item.rule_id,
                    "observation": item.observation,
                    "outcome_class": item.outcome_class,
                    "capability_status": item.capability_status,
                    "note": item.note,
                }
                for claim_id, item in exchange.judgments.items()
            },
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
                "# Pilot #4 R1",
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


def _stopped(judgment: ClaimJudgment) -> P4Exchange:
    exchange = P4Exchange(primary="R1")
    exchange.judgments["R1"] = judgment
    return exchange


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


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run the Pilot #4 conversion claim once")
    parser.add_argument("--planned-run", required=True)
    parser.add_argument("--output-root", type=Path, default=repo_root() / "evidence")
    args = parser.parse_args()
    result = run_pilot4(args.output_root, args.planned_run)
    print(json.dumps({"run_id": result["run_id"], "observation": result["observation"], "rule_id": result["rule_id"], "admission": result["admission"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

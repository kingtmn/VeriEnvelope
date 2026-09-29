"""Render a verification result as one HTML file. This file does not judge."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from verienvelope.schema_io import load_json, validate_instance

_CORRECTION_EVENTS = frozenset(
    {
        "fixed",
        "revalidated",
        "evaluation_defect",
        "method_defect",
        "runner_defect",
    }
)


def render_html(result: dict[str, Any]) -> str:
    validate_instance("verification_result.schema.json", result)
    purpose = result["record_purpose"]
    banner = ""
    if purpose == "pipeline_self_test":
        banner = (
            "<p class=\"banner\">这是测量管线自审记录，不是组件验证结论。"
            "admission=insufficient 表示这次不能用来收录组件。</p>"
        )
    elif purpose == "instrument_self_test":
        banner = (
            "<p class=\"banner\">这是 MCP 测量仪器的自检记录，不是外部组件验证。"
            "admission=insufficient。观察不是原因。</p>"
        )
    elif result["admission"] == "withheld":
        banner = (
            "<p class=\"banner\">未满足收录门栓。Pilot 阶段不把未收录写成公开否定。</p>"
        )
    history = result["history"]
    correction = [event for event in history if event["event_type"] in _CORRECTION_EVENTS]
    correction_text = (
        _history_table(correction)
        if correction
        else "<p>没有更正或缺陷事件。</p>"
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>VeriEnvelope 记录 {_text(result["result_id"])}</title>
  <style>
    body {{ font-family: "Iowan Old Style", Palatino, Georgia, serif; margin: 1.25rem auto; max-width: 46rem; padding: 0 1rem; line-height: 1.45; color: #1c1915; background: #f7f4ee; }}
    h1 {{ font-size: 1.6rem; }}
    h2 {{ font-size: 1.15rem; margin-top: 2rem; }}
    code, pre {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .banner {{ background: #efe6c9; padding: 0.8rem 1rem; }}
    .meta {{ color: #4a453c; }}
    table {{ border-collapse: collapse; width: 100%; }}
    td, th {{ border-top: 1px solid #d9d2c5; text-align: left; vertical-align: top; padding: 0.4rem 0.75rem 0.4rem 0; }}
    th {{ white-space: nowrap; width: 1%; }}
    td {{ overflow-wrap: anywhere; }}
  </style>
</head>
<body>
  <h1>VeriEnvelope 记录</h1>
  <p class="meta">本页没有总分。工作名称未做商标清查。查看器不重新裁决。We verify declared claims. We do not decide fitness for your use.</p>
  {banner}
  <h2>这个组件是谁？</h2>
  {_dl([
      ("组件", result["component_id"]),
      ("类型", result["component_type"]),
      ("来源", result["source_repository"]),
      ("记录用途", purpose),
  ])}
  <h2>哪个版本？</h2>
  <p>version 字段是源码或 fixture 的 metadata，不是 registry 发布物的验证结论。</p>
  {_artifact_note(result["assurance"]["provenance"])}
  {_dl([
      ("源码 metadata 版本", result["component_version"]),
      ("commit", result["component_commit"]),
      ("方法", f"{result['method_id']} {result['method_version']}"),
      ("runner", f"{result['runner_name']} {result['runner_version']}"),
      ("环境", result["environment"]["environment_id"]),
      ("操作系统", f"{result['environment']['os']} {result['environment']['arch']}"),
      ("Python", result["environment"]["python"]),
      ("fixture", result["fixture_id"]),
      ("run id", result["run_id"]),
      ("时间", result["timestamp"]),
  ])}
  <h2>实测能做什么？</h2>
  {_capabilities(result["capabilities"])}
  <p>观察：<code>{_text(result["observation"])}</code>。结果类别：<code>{_text(result["outcome_class"])}</code>。规则：<code>{_text(result["rule_id"])}</code>。结果类别是解释，不是观察本身。</p>
  <p>demonstrated 只覆盖上面这条可测试陈述，以及本页列出的条件。没有观察到失败，不能推出未测范围内没有失败，也不能推出安全、可靠、无缺陷或已经隔离。</p>
  <h2>为什么相信？</h2>
  {_assurance(result["assurance"])}
  <p>验证政策决定：<code>{_text(result["admission"])}</code>。这不是发布状态，也不是 certified。</p>
  {_admission_note(result["admission"])}
  {_list(result["admission_reasons"])}
  <h2>哪些地方没有验证？</h2>
  {_nonclaims(result["envelope"]["untested_areas"])}
  {_list(result["envelope"]["untested_areas"])}
  <h3>已观察到的限制</h3>
  {_observed_limits(result["envelope"]["known_limits"])}
  <h3>测过的条件</h3>
  {_list(result["envelope"]["tested_conditions"])}
  <h2>已知失败在哪里？</h2>
  {_list(result["envelope"]["known_failures"])}
  <h2>原始证据在哪里？</h2>
  <p>证据目录：<code>{_text(result["evidence_dir"])}</code></p>
  {_list(result["evidence_refs"])}
  <h2>有没有历史修正？</h2>
  {correction_text}
  <h3>全部历史事件</h3>
  {_history_table(history)}
</body>
</html>
"""


def write_html(result_path: Path, destination: Path) -> None:
    result = load_json(result_path)
    if not isinstance(result, dict):
        raise TypeError(f"{result_path} did not contain an object")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_html(result), encoding="utf-8")


def _capabilities(capabilities: list[dict[str, Any]]) -> str:
    blocks = []
    for capability in capabilities:
        rows = [
            ("能力", capability["capability_id"]),
            ("声明", capability["claim"]),
            ("可测试陈述", capability["testable_statement"]),
            ("结果", capability["status"]),
            ("证据", _joined(capability["supporting_evidence"])),
            ("测量条件", capability["tested_under"]),
            ("备注", capability["notes"]),
        ]
        claim = capability.get("envelope")
        if isinstance(claim, dict):
            rows.extend(
                [
                    ("声明范围", _joined(claim["tested_conditions"])),
                    ("已观察到的限制", _observed_limits(claim["known_limits"])),
                    ("未知 / 未测", _joined(claim["untested_areas"])),
                    ("重新验证边界", _joined(claim["revalidation_triggers"])),
                ]
            )
        else:
            rows.append(
                (
                    "声明范围",
                    "这条旧记录没有单独的 claim envelope。状态旁边的测量条件，以及本页后面的整次运行边界，必须一起读。",
                )
            )
        blocks.append("<section>" + _dl(rows) + "</section>")
    return "\n".join(blocks)


def _artifact_note(provenance: str) -> str:
    if "locally_built_from_pinned_source" not in provenance:
        return ""
    return (
        "<p>执行工件是 locally_built_from_pinned_source。"
        "package version 只是源码 metadata，不是 npm registry 发布物，也不是官方镜像。</p>"
    )


def _assurance(assurance: dict[str, Any]) -> str:
    return _dl(
        [
            ("依赖", _joined(assurance["dependencies"])),
            ("权限", _joined(assurance["permissions"])),
            ("执行方式", assurance["execution_mode"]),
            ("外部服务", _joined(assurance["external_services"])),
            ("来源说明", assurance["provenance"]),
            ("复现时比较什么", assurance["reproducibility_notes"]),
        ]
    )


def _history_table(events: list[dict[str, Any]]) -> str:
    if not events:
        return "<p>UNKNOWN</p>"
    return "\n".join(
        _dl(
            [
                ("事件", event["event_id"]),
                ("时间", event["timestamp"]),
                ("类型", event["event_type"]),
                ("之前", event["previous_state"]),
                ("之后", event["new_state"]),
                ("原因", event["reason"]),
            ]
        )
        for event in events
    )


def _dl(rows: list[tuple[str, Any]]) -> str:
    body = []
    for label, value in rows:
        body.append(f"<tr><th>{escape(label)}</th><td>{_text(value)}</td></tr>")
    return "<table>" + "".join(body) + "</table>"


def _admission_note(admission: str) -> str:
    if admission != "admitted":
        return ""
    return (
        "<p>admitted 只表示当前验证政策允许在声明范围内收录。"
        "它不是 certified，不是 production ready，也不是 best choice。</p>"
    )


def _observed_limits(items: list[str]) -> str:
    if not items:
        return (
            "None empirically established。"
            "当前没有通过主动实验观察到限制。这不等于不存在限制。"
        )
    return _joined(items)


def _joined(values: list[str]) -> str:
    if not values:
        return "无"
    return ", ".join(values)


def _nonclaims(items: list[str]) -> str:
    claimed_out = [item for item in items if str(item).startswith("不声明")]
    if not claimed_out:
        return ""
    return "<h3>这次不声明</h3>" + _list(claimed_out)


def _list(items: list[str]) -> str:
    if not items:
        return "<p>UNKNOWN</p>"
    return "<ul>" + "".join(f"<li>{_text(item)}</li>" for item in items) + "</ul>"


def _text(value: Any) -> str:
    if value is None or value == "":
        return "UNKNOWN"
    return escape(str(value))

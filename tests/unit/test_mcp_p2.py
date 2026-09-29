"""Pilot #2 judgments stay on the pre-registered strings. No container."""

from verienvelope.mcp_protocol import ClaimJudgment
from verienvelope.mcp_p2 import (
    assemble_capabilities,
    judge_initialize,
    judge_navigate,
    judge_tools,
    load_method,
    recorded_judgments,
)
from verienvelope.schema_io import load_yaml, repo_root

METHOD = repo_root() / "methods" / "VE-METHOD-MCP-002" / "method.yaml"
FROZEN = repo_root() / "methods" / "VE-METHOD-MCP-001" / "method.yaml"


def test_everything_method_stays_0_3_0():
    method = load_yaml(FROZEN)
    assert method["version"] == "0.3.0"
    assert method["status"] == "specified_not_executed"


def test_playwright_method_is_preregistered():
    method = load_method()
    assert method["id"] == "VE-METHOD-MCP-002"
    assert method["version"] == "0.4.0"
    assert method["execution"]["sandbox_policy"] == "ADR-008-amendment-3"
    assert [claim["id"] for claim in method["claims"]] == ["C1", "C2", "C3"]
    assert method["identity"]["server_name"] == "Playwright"
    basis = method["identity"]["expectation_basis"]
    assert "decorateMCPCommand" in basis["source_location"]
    assert "Implementation name" in basis["semantic_mapping"]
    assert method["envelope"]["known_limits"] == []
    assert METHOD.is_file()


def test_c1_match_uses_preregistered_server_info():
    method = load_method()
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": "2025-03-26",
            "serverInfo": {
                "name": "Playwright",
                "version": "1.64.0-alpha-1789764292000",
            },
        },
    }
    judgment = judge_initialize(message, method)
    assert judgment.rule_id == "P2-M1"
    assert judgment.observation == "match"
    assert judgment.outcome_class == "confirmed"


def test_c1_name_mismatch_is_not_a_cause():
    method = load_method()
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": "2025-03-26",
            "serverInfo": {"name": "api", "version": "1.64.0-alpha-1789764292000"},
        },
    }
    judgment = judge_initialize(message, method)
    assert judgment.rule_id == "P2-M3"
    assert judgment.outcome_class == "unclassified"
    assert judgment.capability_status == "not_demonstrated"


def test_c2_expected_set_excludes_skill_only_names():
    method = load_method()
    names = set(method["claims"][1]["core_tools"])
    assert len(names) == 25
    assert "browser_webmcp_list" not in names
    assert "browser_check" not in names
    assert "browser_pdf_save" not in names


def test_c2_compares_the_preregistered_set_only():
    method = load_method()
    expected = frozenset(method["claims"][1]["core_tools"])
    tools = [{"name": name} for name in sorted(expected)]
    match = judge_tools({"result": {"tools": tools}}, expected)
    assert match.observation == "match"
    extra = [*tools, {"name": "browser_extra"}]
    mismatch = judge_tools({"result": {"tools": extra}}, expected)
    assert mismatch.rule_id == "P2-M6"
    assert mismatch.outcome_class == "unclassified"


def test_c3_accepts_the_title_substring_inside_a_longer_snapshot():
    message = {
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": "- Page URL: file:///app/fixture/ve-pilot-2.html\n- Page Title: ve-pilot-2\n",
                }
            ]
        }
    }
    judgment = judge_navigate(message)
    assert judgment.rule_id == "P2-M7"
    assert judgment.observation == "match"


def test_method_0_1_0_text_is_unchanged():
    frozen = load_yaml(repo_root() / "methods" / "VE-METHOD-MCP-002" / "versions" / "0.1.0.yaml")
    assert frozen["version"] == "0.1.0"
    rules = {item["id"]: item["when"] for item in frozen["classification_rules"]}
    assert "进程在响应前退出" in rules["P2-M10"]
    assert "没有可解析的对应响应" in rules["P2-M2"]


def test_method_0_2_0_still_expects_api():
    frozen = load_yaml(repo_root() / "methods" / "VE-METHOD-MCP-002" / "versions" / "0.2.0.yaml")
    assert frozen["version"] == "0.2.0"
    assert frozen["identity"]["server_name"] == "api"
    assert "createServer(\"api\"" in frozen["identity"]["server_name_source"]


def test_method_0_3_0_does_not_change_the_other_expectations():
    method = load_yaml(repo_root() / "methods" / "VE-METHOD-MCP-002" / "versions" / "0.3.0.yaml")
    frozen = load_yaml(repo_root() / "methods" / "VE-METHOD-MCP-002" / "versions" / "0.2.0.yaml")
    assert method["version"] == "0.3.0"
    assert method["execution"]["sandbox_policy"] == "ADR-008-amendment-2"
    assert method["identity"]["server_version"] == frozen["identity"]["server_version"]
    assert method["client_handshake"]["protocol_version_offered"] == "2025-03-26"
    assert method["claims"][1]["core_tools"] == frozen["claims"][1]["core_tools"]
    assert method["claims"][2]["statement"] == frozen["claims"][2]["statement"]


def test_method_0_4_0_only_changes_the_sandbox_contract():
    current = load_method()
    frozen = load_yaml(repo_root() / "methods" / "VE-METHOD-MCP-002" / "versions" / "0.3.0.yaml")
    assert current["identity"] == frozen["identity"]
    assert current["claims"] == frozen["claims"]
    assert "tmpfs /tmp" in " ".join(current["envelope"]["tested_conditions"])


def test_method_0_2_0_rules_do_not_share_the_exit_clause():
    method = load_yaml(repo_root() / "methods" / "VE-METHOD-MCP-002" / "versions" / "0.2.0.yaml")
    rules = {item["id"]: item["when"] for item in method["classification_rules"]}
    assert "已经启动" in rules["P2-M2"]
    assert "进程在响应前退出" not in rules["P2-M10"]
    assert "之前拒绝" in rules["P2-M10"]


def test_a_failed_primary_keeps_demonstrated_prerequisites():
    views = {
        claim: {"tested_conditions": ["x"], "known_limits": [], "untested_areas": ["y"], "revalidation_triggers": ["z"]}
        for claim in ("C1", "C2", "C3")
    }
    statements = {"C1": "c1", "C2": "c2", "C3": "c3"}
    judgments = {
        "C1": ClaimJudgment("C1", "P2-M1", "match", "confirmed", "demonstrated", "c1 matched"),
        "C2": ClaimJudgment("C2", "P2-M5", "match", "confirmed", "demonstrated", "c2 matched"),
        "C3": ClaimJudgment("C3", "P2-M8", "mismatch", "unclassified", "not_demonstrated", "c3 missed"),
    }
    recorded = assemble_capabilities(
        judgments,
        primary="C3",
        statements=statements,
        views=views,
        tested_under="method",
        evidence_id="ev",
    )
    assert [item["status"] for item in recorded] == ["demonstrated", "demonstrated", "not_demonstrated"]
    assert recorded[0]["notes"] == "c1 matched"


def test_an_unsent_claim_stays_insufficient():
    recorded = assemble_capabilities(
        {"C1": ClaimJudgment("C1", "P2-M1", "match", "confirmed", "demonstrated", "c1 matched")},
        primary="C1",
        statements={"C1": "c1", "C2": "c2", "C3": "c3"},
        views={
            claim: {"tested_conditions": ["x"], "known_limits": [], "untested_areas": ["y"], "revalidation_triggers": ["z"]}
            for claim in ("C1", "C2", "C3")
        },
        tested_under="method",
        evidence_id="ev",
    )
    assert [item["status"] for item in recorded] == ["demonstrated", "insufficient", "insufficient"]


def test_recorded_judgments_drop_the_transport_key():
    judgments = {
        "C1": ClaimJudgment("C1", "P2-M2", "execution_error", "unclassified", "not_demonstrated", "no response"),
        "initialize": ClaimJudgment("C1", "P2-M2", "execution_error", "unclassified", "not_demonstrated", "no response"),
    }
    recorded = recorded_judgments(judgments)
    assert list(recorded) == ["C1"]


def test_c3_without_the_title_is_unclassified():
    message = {"result": {"content": [{"type": "text", "text": "Access to \"file:\" protocol is blocked."}]}}
    judgment = judge_navigate(message)
    assert judgment.rule_id == "P2-M8"
    assert judgment.outcome_class == "unclassified"
    assert "component" not in judgment.outcome_class

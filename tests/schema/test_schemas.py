import json
from copy import deepcopy

import pytest

from tests.paths import ROOT
from verienvelope.schema_io import validate_instance
from verienvelope.errors import SchemaError


def test_example_component_validates() -> None:
    component = json.loads(
        (ROOT / "registry" / "examples" / "component.example.json").read_text(encoding="utf-8")
    )
    validate_instance("component.schema.json", component)


def test_component_schema_rejects_popularity_fields() -> None:
    component = json.loads(
        (ROOT / "registry" / "examples" / "component.example.json").read_text(encoding="utf-8")
    )
    tainted = deepcopy(component)
    tainted["stars"] = 100
    with pytest.raises(SchemaError):
        validate_instance("component.schema.json", tainted)


def test_method_cases_match_test_case_schema() -> None:
    for path in sorted((METHOD_DIR()).glob("*.json")):
        validate_instance("test_case.schema.json", json.loads(path.read_text(encoding="utf-8")))


def test_fixture_component_validates() -> None:
    component = json.loads(
        (ROOT / "methods" / "VE-METHOD-001" / "fixtures" / "component.json").read_text(
            encoding="utf-8"
        )
    )
    validate_instance("component.schema.json", component)
    assert "commit" not in component


def test_repo_does_not_mark_a_candidate_admitted() -> None:
    skipped = {".git", ".venv", "__pycache__", "_scratch", "preview"}
    for path in ROOT.rglob("*.json"):
        if skipped.intersection(path.parts):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            continue
        assert data.get("status") != "admitted", path
        if "evidence" not in path.parts:
            assert data.get("admission") != "admitted", path


def test_external_evidence_keeps_admission_separate_from_a_score() -> None:
    evidence = ROOT / "evidence"
    manifests = [
        path
        for path in evidence.rglob("manifest.json")
        if "_scratch" not in path.parts
    ]
    assert manifests
    for manifest_path in manifests:
        package = manifest_path.parent
        result = json.loads((package / "result.json").read_text(encoding="utf-8"))
        assert result["record_purpose"] == "component_verification"
        allowed_versions = {
            "VE-METHOD-MCP-001": {"0.3.0"},
            "VE-METHOD-MCP-002": {"0.1.0", "0.2.0", "0.3.0", "0.4.0"},
            "VE-METHOD-MCP-003": {"0.1.0", "0.2.0"},
            "VE-METHOD-MCP-004": {"0.1.0"},
            "VE-METHOD-MCP-005": {"0.1.0"},
        }
        assert result["method_version"] in allowed_versions[result["method_id"]]
        pinned = {
            "run-47f9611e16544d998d983bfa4d7c1b43": "0.1.0",
            "run-d46735b07c1c434b9461370aca6a7268": "0.2.0",
            "run-b93181d9aee447d1ad4328d15a8363dc": "0.3.0",
            "run-d5e468f88bab49db8fd1f48276b154aa": "0.3.0",
            "run-a554d6a9f8fc4d41b1f3764e5cbc1476": "0.3.0",
            "run-d22d4d1928204029b8d2e45e82f749ad": "0.4.0",
            "run-605485ecb4594a0d9fabd0002ca19899": "0.1.0",
            "run-a030ab0bf2ee40faaf0b22cf003147ce": "0.2.0",
            "run-f4ba0e8b9d3243f7b42f103a9624fb19": "0.1.0",
            "run-21d1582275e347ee9389bc241b6756dd": "0.1.0",
        }
        if package.name in pinned:
            assert result["method_version"] == pinned[package.name]
        assert result["outcome_class"] != "component_failure"
        assert all(cap["capability_id"] != "C4" for cap in result["capabilities"])
        if result["admission"] == "admitted":
            demonstrated = {
                cap["capability_id"]
                for cap in result["capabilities"]
                if cap["status"] == "demonstrated"
            }
            required = {
                "VE-METHOD-MCP-001": {"C1", "C2", "C3"},
                "VE-METHOD-MCP-002": {"C1", "C2", "C3"},
                "VE-METHOD-MCP-003": {"S1", "S2", "R1"},
                "VE-METHOD-MCP-004": {"S1", "S2", "R1"},
                "VE-METHOD-MCP-005": {"S1", "S2", "R1"},
            }[result["method_id"]]
            assert required <= demonstrated
            assert result["admission_reasons"] == []
            for cap in result["capabilities"]:
                envelope = cap["envelope"]
                assert envelope["tested_conditions"]
                assert envelope["untested_areas"]
                assert envelope["revalidation_triggers"]
                assert "known_limits" in envelope


def METHOD_DIR():
    return ROOT / "methods" / "VE-METHOD-001" / "cases"

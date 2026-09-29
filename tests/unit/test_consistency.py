from verienvelope.consistency import consistency_errors


def test_demonstrated_without_match_is_inconsistent() -> None:
    errors = consistency_errors(
        {
            "observation": "mismatch",
            "outcome_class": "component_failure",
            "admission": "insufficient",
            "record_purpose": "pipeline_self_test",
            "admission_reasons": ["not an admission"],
            "evidence_refs": ["ev-1"],
            "capabilities": [
                {
                    "capability_id": "cap-1",
                    "status": "demonstrated",
                    "supporting_evidence": ["ev-1"],
                }
            ],
        }
    )
    assert errors


def test_a_demonstrated_prerequisite_can_sit_beside_a_missed_primary() -> None:
    tested = "method VE-METHOD-MCP-002 0.4.0; primary C3; image sha256:abc; sandbox ADR-008-amendment-3"
    errors = consistency_errors(
        {
            "observation": "mismatch",
            "outcome_class": "unclassified",
            "admission": "insufficient",
            "record_purpose": "component_verification",
            "admission_reasons": ["a recorded capability is not_demonstrated"],
            "evidence_refs": ["ev-1"],
            "capabilities": [
                {
                    "capability_id": "C1",
                    "status": "demonstrated",
                    "supporting_evidence": ["ev-1"],
                    "tested_under": tested,
                },
                {
                    "capability_id": "C3",
                    "status": "not_demonstrated",
                    "supporting_evidence": [],
                    "tested_under": tested,
                },
            ],
        }
    )
    assert errors == []


def test_the_primary_claim_cannot_be_demonstrated_on_a_mismatch() -> None:
    tested = "method VE-METHOD-MCP-002 0.4.0; primary C3; image sha256:abc"
    errors = consistency_errors(
        {
            "observation": "mismatch",
            "outcome_class": "unclassified",
            "admission": "insufficient",
            "record_purpose": "component_verification",
            "admission_reasons": ["pending"],
            "evidence_refs": ["ev-1"],
            "capabilities": [
                {
                    "capability_id": "C3",
                    "status": "demonstrated",
                    "supporting_evidence": ["ev-1"],
                    "tested_under": tested,
                }
            ],
        }
    )
    assert "demonstrated capability requires observation match" in errors


def test_match_and_confirmed_do_not_generate_demonstrated() -> None:
    errors = consistency_errors(
        {
            "observation": "match",
            "outcome_class": "confirmed",
            "admission": "insufficient",
            "record_purpose": "component_verification",
            "admission_reasons": ["pending"],
            "evidence_refs": ["ev-1"],
            "capabilities": [
                {
                    "capability_id": "R1",
                    "status": "not_demonstrated",
                    "supporting_evidence": [],
                    "tested_under": "method VE-METHOD-MCP-003 0.2.0; primary R1",
                }
            ],
        }
    )
    assert "demonstrated capability requires observation match" not in errors


def test_self_test_cannot_be_marked_admitted() -> None:
    errors = consistency_errors(
        {
            "observation": "match",
            "outcome_class": "confirmed",
            "admission": "admitted",
            "record_purpose": "pipeline_self_test",
            "admission_reasons": [],
            "evidence_refs": ["ev-1"],
            "capabilities": [
                {
                    "capability_id": "cap-1",
                    "status": "demonstrated",
                    "supporting_evidence": ["ev-1"],
                }
            ],
        }
    )
    assert any("admitted" in error for error in errors)

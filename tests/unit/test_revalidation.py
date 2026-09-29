import yaml

from tests.paths import METHOD, ROOT
from verienvelope.revalidation import TRIGGER_KINDS, admission_reuse_allowed, must_revalidate


def test_each_documented_trigger_requires_revalidation() -> None:
    method = yaml.safe_load((METHOD / "method.yaml").read_text(encoding="utf-8"))
    declared = set(method["envelope"]["revalidation_triggers"])
    assert declared == set(TRIGGER_KINDS)
    for kind in TRIGGER_KINDS:
        assert must_revalidate([kind]) is True


def test_unknown_change_is_not_treated_as_harmless() -> None:
    assert must_revalidate(["renamed_a_comment"]) is True


def test_no_declared_change_does_not_force_revalidation() -> None:
    assert must_revalidate([]) is False


def test_version_change_blocks_admission_reuse() -> None:
    assert admission_reuse_allowed(component_version_changed=True, changes=[]) is False


def test_same_version_with_a_trigger_blocks_reuse() -> None:
    assert (
        admission_reuse_allowed(
            component_version_changed=False,
            changes=["runner_bug"],
        )
        is False
    )


def test_same_binding_does_not_require_the_helper_to_forbid_reuse() -> None:
    assert admission_reuse_allowed(component_version_changed=False, changes=[]) is True


def test_revalidation_doc_points_at_the_code_list() -> None:
    text = (ROOT / "methodology" / "revalidation.md").read_text(encoding="utf-8")
    assert "TRIGGER_KINDS" in text
    assert "不自动" in text or "不得复用" in text

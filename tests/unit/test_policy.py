import os

import pytest

from verienvelope.errors import PolicyError
from verienvelope.policy import (
    MAX_TIMEOUT_SECONDS,
    assert_execution_allowed,
    checked_timeout,
    safe_method_path,
    scrubbed_subprocess_env,
)


def test_component_verification_is_refused() -> None:
    with pytest.raises(PolicyError, match="isolation"):
        assert_execution_allowed({"purpose": "component_verification"})


def test_secret_is_not_copied_into_the_subprocess_environment(monkeypatch) -> None:
    monkeypatch.setenv("VE_TEST_SECRET", "ve-test-secret")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "ve-test-secret")
    scrubbed = scrubbed_subprocess_env()
    assert "VE_TEST_SECRET" not in scrubbed
    assert "AWS_SECRET_ACCESS_KEY" not in scrubbed
    assert scrubbed["PYTHONHASHSEED"] == "0"


def test_parent_environment_remains_unchanged(monkeypatch) -> None:
    monkeypatch.setenv("VE_TEST_SECRET", "ve-test-secret")
    scrubbed_subprocess_env()
    assert os.environ["VE_TEST_SECRET"] == "ve-test-secret"


def test_absolute_path_is_refused(tmp_path) -> None:
    with pytest.raises(PolicyError):
        safe_method_path(tmp_path, "/etc/passwd")


def test_parent_segment_is_refused(tmp_path) -> None:
    with pytest.raises(PolicyError):
        safe_method_path(tmp_path, "../outside.py")


def test_timeout_above_the_cap_is_refused() -> None:
    with pytest.raises(PolicyError):
        checked_timeout(MAX_TIMEOUT_SECONDS + 1)

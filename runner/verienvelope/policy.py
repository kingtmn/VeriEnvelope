"""Execution limits for the reference runner."""

from __future__ import annotations

import os
from pathlib import Path

from verienvelope.errors import PolicyError

MAX_TIMEOUT_SECONDS = 30
_ENV_ALLOWLIST = ("PATH", "LANG", "LC_ALL", "TZ", "SYSTEMROOT", "COMSPEC")


def assert_execution_allowed(method: dict) -> None:
    purpose = method.get("purpose")
    if purpose != "pipeline_self_test":
        raise PolicyError(
            "Reference runner executes only methods whose purpose is "
            "pipeline_self_test. run_case does not enter the container "
            "isolation boundary. External execution stays refused until a "
            "pilot executor is invoked explicitly. "
            f"This method purpose is {purpose!r}."
        )


def scrubbed_subprocess_env() -> dict[str, str]:
    kept: dict[str, str] = {}
    for name in _ENV_ALLOWLIST:
        value = os.environ.get(name)
        if value is not None:
            kept[name] = value
    kept["PYTHONNOUSERSITE"] = "1"
    kept["PYTHONHASHSEED"] = "0"
    return kept


def safe_method_path(method_dir: Path, relative: str) -> Path:
    if not isinstance(relative, str) or relative == "":
        raise PolicyError("path must be a non-empty relative string")
    if relative.startswith(("/", "\\")) or "\\" in relative:
        raise PolicyError(f"absolute or non-relative path is refused: {relative}")
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise PolicyError(f"path escapes the method directory: {relative}")
    root = method_dir.resolve()
    candidate = (root / relative_path).resolve()
    if not candidate.is_relative_to(root):
        raise PolicyError(f"path escapes the method directory: {relative}")
    return candidate


def checked_timeout(seconds: object) -> float:
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
        raise PolicyError("timeout_seconds must be a number")
    if seconds <= 0 or seconds > MAX_TIMEOUT_SECONDS:
        raise PolicyError(
            f"timeout_seconds must be within (0, {MAX_TIMEOUT_SECONDS}]"
        )
    return float(seconds)

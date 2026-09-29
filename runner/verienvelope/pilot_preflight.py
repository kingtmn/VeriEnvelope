"""Checklist that must be true before the first external MCP process starts.

READY means the first external process may be started. It does not mean that
process passed. `run_case` still refuses every purpose other than
pipeline_self_test.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from verienvelope.schema_io import repo_root


@dataclass(frozen=True)
class PreflightItem:
    number: int
    item_id: str
    condition: str
    met: bool
    note: str


ITEMS: tuple[PreflightItem, ...] = (
    PreflightItem(
        1,
        "identity",
        "Candidate identity pinned",
        True,
        "registry/candidates/mcp.server-everything.json",
    ),
    PreflightItem(
        2,
        "commit",
        "Commit pinned",
        True,
        "f46d9578190b476b3501923ea8977d899e8db2cb",
    ),
    PreflightItem(
        3,
        "claims",
        "Claims written before execution",
        True,
        "C1 C2 C3 were registered before any external run.",
    ),
    PreflightItem(
        4,
        "method",
        "Method version fixed",
        True,
        "VE-METHOD-MCP-001 0.3.0",
    ),
    PreflightItem(
        5,
        "expected",
        "Expected observations fixed",
        True,
        "Written in the method file before any execution.",
    ),
    PreflightItem(
        6,
        "interpretation",
        "Interpretation rules fixed",
        True,
        "M1–M10. M2/M4/M6/M9/M10 do not assign a cause.",
    ),
    PreflightItem(
        7,
        "non_claims",
        "Explicit non-claims fixed",
        True,
        "Listed in the method envelope and shown by the viewer when present.",
    ),
    PreflightItem(
        8,
        "evidence_package",
        "Evidence package ready",
        True,
        "The self-test writer still produces the package. No MCP package exists.",
    ),
    PreflightItem(
        9,
        "seal",
        "Final package seal ready",
        True,
        "seal.json covers the finished files. It does not hash itself.",
    ),
    PreflightItem(
        10,
        "sandbox",
        "Runtime sandbox implemented",
        True,
        "runner/verienvelope/sandbox.py. Not wired to run_case. Everything was not started.",
    ),
    PreflightItem(
        11,
        "build_isolation",
        "Build/acquisition isolation defined",
        True,
        "pull_image is separate from run_command. Host npm/npx/pip/uvx are refused. The Everything image has not been built.",
    ),
    PreflightItem(
        12,
        "network",
        "Network policy explicit",
        True,
        "Runtime network is none. This method allows no runtime destination.",
    ),
    PreflightItem(
        13,
        "secret_tested",
        "Secret isolation tested",
        True,
        "Toy process inside the boundary. Not an external component result.",
    ),
    PreflightItem(
        14,
        "resources_tested",
        "Resource limits tested",
        True,
        "CPU, memory, and PID limits observed on the toy container.",
    ),
    PreflightItem(
        15,
        "cleanup_tested",
        "Container cleanup tested",
        True,
        "Timed-out toy container is removed.",
    ),
    PreflightItem(
        16,
        "revalidation",
        "Revalidation triggers declared",
        True,
        "Same trigger kinds as the reference runner, declared on VE-METHOD-MCP-001.",
    ),
)


@dataclass(frozen=True)
class ExecutionFacts:
    executor_implemented: bool = False
    fixture_validated: bool = False
    evidence_path_validated: bool = False
    image_built: bool = False
    image_digest: str | None = None
    execution_contradiction: bool = False


def execution_items(facts: ExecutionFacts) -> tuple[PreflightItem, ...]:
    digest = facts.image_digest or ""
    digest_ok = digest.startswith("sha256:") and len(digest) > len("sha256:")
    return (
        PreflightItem(
            17,
            "executor",
            "MCP protocol executor implemented",
            facts.executor_implemented,
            "Four messages only. Everything is not started.",
        ),
        PreflightItem(
            18,
            "fixture_validation",
            "MCP executor validated against a controlled local fixture",
            facts.fixture_validated,
            "instrument_self_test. Not external evidence.",
        ),
        PreflightItem(
            19,
            "evidence_path",
            "Full sandbox → MCP executor → evidence → seal path validated",
            facts.evidence_path_validated,
            "Validated on the controlled fixture.",
        ),
        PreflightItem(
            20,
            "image_built",
            "Candidate image built from pinned source in isolated build",
            facts.image_built,
            "Built image is not run.",
        ),
        PreflightItem(
            21,
            "image_digest",
            "Candidate image digest recorded",
            digest_ok,
            digest or "missing",
        ),
        PreflightItem(
            22,
            "no_contradiction",
            "No unresolved execution-path contradiction",
            not facts.execution_contradiction,
            "Any open contradiction keeps the gate closed.",
        ),
    )


def checklist(facts: ExecutionFacts) -> tuple[PreflightItem, ...]:
    return ITEMS + execution_items(facts)


def gate_ready(facts: ExecutionFacts) -> bool:
    return all(item.met for item in checklist(facts))


def build_record_path() -> Path:
    return repo_root() / "registry" / "candidates" / "everything-build.json"


def load_execution_facts(path: Path | None = None) -> ExecutionFacts:
    record = path or build_record_path()
    if not record.is_file():
        return ExecutionFacts(executor_implemented=True)
    data = json.loads(record.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return ExecutionFacts(execution_contradiction=True)
    digest = data.get("image_digest")
    return ExecutionFacts(
        executor_implemented=bool(data.get("executor_implemented")),
        fixture_validated=bool(data.get("fixture_validated")),
        evidence_path_validated=bool(data.get("evidence_path_validated")),
        image_built=bool(data.get("image_built")),
        image_digest=digest if isinstance(digest, str) else None,
        execution_contradiction=bool(data.get("execution_contradiction")),
    )


def unmet_items(facts: ExecutionFacts | None = None) -> tuple[PreflightItem, ...]:
    return tuple(item for item in checklist(facts or load_execution_facts()) if not item.met)


def gate_open() -> bool:
    return gate_ready(load_execution_facts())


RUN2_AUTHORIZATION = {
    "planned_run": "external-run-2",
    "primary_claim": "C2",
    "method_version": "0.3.0",
    "execution_artifact": "sha256:5f1784c80a95be56091a16ac8f6955b32eb170dcf89ee3b9d2cb86c0b26fe1d6",
    "sandbox_policy": "ADR-008-amendment-1",
}


def run_authorization_path() -> Path:
    return repo_root() / "registry" / "runs" / "external-run-2.json"


def load_run_authorization(path: Path | None = None) -> dict | None:
    record = path or run_authorization_path()
    if not record.is_file():
        return None
    data = json.loads(record.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    return data


def authorization_events_path() -> Path:
    return repo_root() / "registry" / "runs" / "authorization-events.jsonl"


def consumed_runs(path: Path | None = None) -> frozenset[str]:
    """Runs whose one-time authorization has been consumed.

    The original authorization files stay as they were. This log only appends.
    """
    record = authorization_events_path() if path is None else path
    if not record.is_file():
        return frozenset()
    found: set[str] = set()
    for line in record.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if (
            isinstance(event, dict)
            and event.get("event") == "authorization_consumed"
            and isinstance(event.get("planned_run"), str)
        ):
            found.add(event["planned_run"])
    return frozenset(found)


def append_authorization_consumed(
    planned_run: str,
    *,
    path: Path,
    recorded_at: str,
    note: str,
) -> None:
    event = {
        "event": "authorization_consumed",
        "note": note,
        "planned_run": planned_run,
        "recorded_at": recorded_at,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def run_authorized(
    data: dict | None = None,
    *,
    consumed: frozenset[str] | None = None,
) -> bool:
    """Authorize external run #2 only. The shared checklist does not.

    Run #2 having been READY does not authorize run #3. A consumed run
    cannot be started again, even though its authorization file stays true.
    """
    loaded = data if data is not None else load_run_authorization()
    return _start_allowed(
        loaded,
        RUN2_AUTHORIZATION,
        previous_planned="external-run-1",
        consumed=consumed,
    )


RUN3_AUTHORIZATION = {
    "planned_run": "external-run-3",
    "primary_claim": "C3",
    "method_version": "0.3.0",
    "execution_artifact": "sha256:5f1784c80a95be56091a16ac8f6955b32eb170dcf89ee3b9d2cb86c0b26fe1d6",
    "sandbox_policy": "ADR-008-amendment-1",
}


def run3_authorization_path() -> Path:
    return repo_root() / "registry" / "runs" / "external-run-3.json"


def load_run3_authorization(path: Path | None = None) -> dict | None:
    record = path or run3_authorization_path()
    if not record.is_file():
        return None
    data = json.loads(record.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    return data


def run3_authorized(
    data: dict | None = None,
    *,
    consumed: frozenset[str] | None = None,
) -> bool:
    """Authorize external run #3 only, after run #2 is completed."""
    loaded = load_run3_authorization() if data is None else data
    if not _start_allowed(
        loaded,
        RUN3_AUTHORIZATION,
        previous_planned="external-run-2",
        consumed=consumed,
    ):
        return False
    previous = loaded.get("previous_run") if isinstance(loaded, dict) else None
    return isinstance(previous, dict) and previous.get("primary_claim") == "C2"


def _start_allowed(
    loaded: dict | None,
    expected: dict[str, str],
    *,
    previous_planned: str,
    consumed: frozenset[str] | None,
) -> bool:
    if not _run_matches(loaded, expected, previous_planned=previous_planned):
        return False
    assert loaded is not None
    used = consumed_runs() if consumed is None else consumed
    return loaded.get("planned_run") not in used


def _run_matches(loaded: dict | None, expected: dict[str, str], *, previous_planned: str) -> bool:
    if not gate_open():
        return False
    if not isinstance(loaded, dict) or loaded.get("authorized") is not True:
        return False
    for key, value in expected.items():
        if loaded.get(key) != value:
            return False
    previous = loaded.get("previous_run")
    if not isinstance(previous, dict):
        return False
    if previous.get("planned_run") != previous_planned or previous.get("status") != "completed":
        return False
    timestamp = loaded.get("timestamp")
    return isinstance(timestamp, str) and len(timestamp) >= 10

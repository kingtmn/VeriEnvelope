"""When an old admission must not be reused. Nothing here copies an admission."""

from __future__ import annotations

TRIGGER_KINDS = frozenset(
    {
        "major_version",
        "relevant_dependency",
        "permission",
        "runtime",
        "protocol",
        "method_revision",
        "runner_bug",
        "external_counterexample",
        "security_or_capability_change",
    }
)


def must_revalidate(changes: list[str]) -> bool:
    """Any declared change requires a new run. Unknown kinds are not treated as safe."""
    return bool(changes)


def admission_reuse_allowed(*, component_version_changed: bool, changes: list[str]) -> bool:
    if component_version_changed:
        return False
    if must_revalidate(changes):
        return False
    return True


APPLICABILITY_KEYS = (
    "source_commit",
    "execution_artifact",
    "method_version",
    "runner_version",
    "protocol",
)


def verification_applicability(recorded: dict[str, object], current: dict[str, object]) -> str:
    """Whether an old result still represents the object now.

    Returns ``current`` or ``revalidation_required``. It does not read or
    write evidence files. Historical evidence stays where it was.
    """
    for key in APPLICABILITY_KEYS:
        if recorded.get(key) != current.get(key):
            return "revalidation_required"
    return "current"

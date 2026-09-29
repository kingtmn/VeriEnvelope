"""diagnostic_only. not_registry_evidence. One variable: tmpfs /tmp."""

from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path

from verienvelope.sandbox import RuntimeLimits, control_plane_env

IMAGE = "sha256:cc8221f580a2ff7cdecac250da533250ef12e03a4101c13363056039072544cd"
HERE = Path(__file__).resolve().parent
BODY = (HERE / "check_mkdtemp.mjs").read_text(encoding="utf-8")
OUT = HERE / "results"
ISOLATED_TMP = "/tmp:rw,noexec,nosuid,nodev,size=16m"


def _amendment_2_flags(name: str, limits: RuntimeLimits) -> list[str]:
    """The contract that existed when D0/D1 were recorded. Not the live runner."""
    return [
        "--rm",
        "--name",
        name,
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--user",
        limits.user,
        "--pids-limit",
        str(limits.pids_limit),
        "--memory",
        limits.memory,
        "--memory-swap",
        limits.memory,
        "--cpus",
        limits.cpus,
        "--tmpfs",
        "/work:rw,noexec,nosuid,nodev,size=16m",
    ]


def _run(label: str, extra_flags: list[str]) -> dict[str, object]:
    limits = RuntimeLimits()
    name = "ve-diag-" + uuid.uuid4().hex[:12]
    flags = _amendment_2_flags(name, limits)
    flags.extend(extra_flags)
    command = [
        "env",
        "-i",
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "LANG=C",
        "node",
        "--input-type=module",
        "-e",
        BODY,
    ]
    created = subprocess.run(
        ["docker", "create", *flags, IMAGE, *command],
        capture_output=True,
        env=control_plane_env(),
        check=False,
    )
    if created.returncode != 0:
        raise SystemExit(created.stderr.decode("utf-8", "replace"))
    try:
        completed = subprocess.run(
            ["docker", "start", "-a", name],
            capture_output=True,
            env=control_plane_env(),
            timeout=limits.timeout_seconds,
            check=False,
        )
        code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, env=control_plane_env(), check=False)
    return {
        "label": label,
        "diagnostic_only": True,
        "not_registry_evidence": True,
        "extra_flags": extra_flags,
        "exit_code": code,
        "stdout": stdout.decode("utf-8", "replace"),
        "stderr": stderr.decode("utf-8", "replace"),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cases = {
        "D0": _run("D0", []),
        "D1": _run("D1", ["--tmpfs", ISOLATED_TMP]),
    }
    for label, record in cases.items():
        (OUT / f"{label}.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(label, record["exit_code"], record["stdout"].strip(), record["stderr"].strip()[:240])


if __name__ == "__main__":
    main()

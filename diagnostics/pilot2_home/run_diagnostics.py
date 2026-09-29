"""Read-only environment diagnostics for the pinned Playwright image.

diagnostic_only. not_registry_evidence. Does not start the MCP server and does
not write under evidence/.
"""

from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path

from verienvelope.sandbox import RuntimeLimits, control_plane_env, runtime_flags

IMAGE = "sha256:cc8221f580a2ff7cdecac250da533250ef12e03a4101c13363056039072544cd"
PATH_VALUE = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
HERE = Path(__file__).resolve().parent
OUT = HERE / "results"

HOMEDIR = (HERE / "check_homedir.mjs").read_text(encoding="utf-8")
IMPORT = (HERE / "import_core.mjs").read_text(encoding="utf-8")


def _argv(home: str | None, body: str, *, module: bool) -> list[str]:
    env = ["env", "-i", f"PATH={PATH_VALUE}", "LANG=C"]
    if home is not None:
        env.append(f"HOME={home}")
        prefix = "mkdir -p /work/home && "
    else:
        prefix = ""
    node = "node --input-type=module -e" if module else "node -e"
    owner = "ls -ld /work/home;" if home is not None else ""
    script = f"{prefix}{node} \"$1\"; status=$?; {owner} exit $status"
    return [*env, "sh", "-c", script, "ve-diag", body]


def _run(label: str, command: list[str]) -> dict[str, object]:
    limits = RuntimeLimits()
    name = "ve-diag-" + uuid.uuid4().hex[:12]
    flags = runtime_flags(name=name, limits=limits)
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
        timed_out = False
        code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        code = None
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
    finally:
        subprocess.run(
            ["docker", "rm", "-f", name],
            capture_output=True,
            env=control_plane_env(),
            check=False,
        )
    record = {
        "label": label,
        "diagnostic_only": True,
        "not_registry_evidence": True,
        "command": command,
        "exit_code": code,
        "timed_out": timed_out,
        "stdout": stdout.decode("utf-8", "replace"),
        "stderr": stderr.decode("utf-8", "replace"),
    }
    (OUT / f"{label}.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(label, "exit", code, "stdout", record["stdout"][:200].replace("\n", " "), "stderr", record["stderr"][:240].replace("\n", " "))
    return record


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    facts = [
        "env",
        "-i",
        f"PATH={PATH_VALUE}",
        "LANG=C",
        "sh",
        "-c",
        "printf 'HOME=[%s]\\n' \"${HOME-}\"; id; "
        "awk -F: '$3==65532 {print}' /etc/passwd; "
        "echo '---passwd---'; cat /etc/passwd; "
        "ls -ld /work; touch /work/ve-write && echo work-writable",
    ]
    _run("facts", facts)
    _run("D0", _argv(None, HOMEDIR, module=True))
    _run("D1", _argv("/work/home", HOMEDIR, module=True))
    _run("import-D0", _argv(None, IMPORT, module=False))
    _run("import-D1", _argv("/work/home", IMPORT, module=False))


if __name__ == "__main__":
    main()

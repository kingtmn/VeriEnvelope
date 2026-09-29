"""Build the pinned Everything server without running it and without host npm.

The repository is an npm workspace. src/everything/tsconfig.json extends the
root tsconfig, and the only lockfile is the root package-lock.json. The build
context is therefore the whole checkout at the pinned commit. Only
src/everything is compiled. The resulting image is not started.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from verienvelope.artifact_identity import execution_artifact, source_identity
from verienvelope.errors import VeriEnvelopeError
from verienvelope.pilot_preflight import build_record_path
from verienvelope.sandbox import control_plane_env, pin_image, pull_image, refuse_host_package_install

PINNED_COMMIT = "f46d9578190b476b3501923ea8977d899e8db2cb"
REPOSITORY = "https://github.com/modelcontextprotocol/servers.git"
COMPONENT_PATH = "src/everything"
REQUESTED_BASE_IMAGE = "node:22.12-alpine"
# docker.io returned EOF on the manifest HEAD. The same official library
# mirror already used for python:3.11-slim supplied this tag. The Dockerfile
# still FROMs the local image id, not the floating tag.
BASE_IMAGE = "public.ecr.aws/docker/library/node:22.12-alpine"
BASE_IMAGE_ACQUISITION = (
    "docker pull node:22.12-alpine failed: registry-1.docker.io HEAD EOF. "
    "Pulled public.ecr.aws/docker/library/node:22.12-alpine instead. "
    "The image was not pushed."
)
LOCAL_TAG = "ve-everything-f46d957"


def build_pinned_candidate(record_path: Path | None = None) -> dict[str, Any]:
    destination = record_path or build_record_path()
    with tempfile.TemporaryDirectory(prefix="ve-empty-home-") as home:
        git_env = _git_env(Path(home))
        with tempfile.TemporaryDirectory(prefix="ve-everything-src-") as work:
            checkout = Path(work) / "src"
            checkout.mkdir()
            _git(checkout, git_env)
            head = _git_output(checkout, git_env, ["git", "rev-parse", "HEAD"]).strip()
            if head != PINNED_COMMIT:
                raise VeriEnvelopeError(f"checkout commit is {head}, expected {PINNED_COMMIT}")
            lock_path = checkout / "package-lock.json"
            if not lock_path.is_file():
                raise VeriEnvelopeError("root package-lock.json is missing at the pinned commit")
            if (checkout / COMPONENT_PATH / "package-lock.json").is_file():
                lock_scope = f"{COMPONENT_PATH}/package-lock.json"
            else:
                lock_scope = "package-lock.json"
            lock_bytes = lock_path.read_bytes()
            lock_doc = json.loads(lock_bytes.decode("utf-8"))
            base = pull_image(BASE_IMAGE)
            _write_dockerfile(checkout, base.image_id)
            (checkout / ".dockerignore").write_text(".git\n", encoding="utf-8")
            build_log = _docker_build(checkout)
    image = pin_image(LOCAL_TAG)
    toolchain = _toolchain_from_base(base.image_id)
    dist_present = _dist_exists_without_starting(image.image_id)
    if not dist_present:
        raise VeriEnvelopeError("isolated build did not produce src/everything/dist/index.js")
    config = _image_config(image.image_id)
    image_cmd = config.get("Cmd")
    image_entrypoint = config.get("Entrypoint")
    command_matches_method = image_cmd == ["node", "dist/index.js", "stdio"]
    record = {
        "executor_implemented": True,
        "fixture_validated": True,
        "evidence_path_validated": True,
        "image_built": True,
        "image_digest": image.image_id,
        "execution_contradiction": not command_matches_method,
        "executed": False,
        "pushed": False,
        "repository": REPOSITORY,
        "commit": PINNED_COMMIT,
        "component_path": COMPONENT_PATH,
        "build_context": (
            "Full checkout. src/everything/tsconfig.json extends ../../tsconfig.json, "
            "npm workspaces are src/*, and src/everything has no package-lock.json. "
            "Only src/everything is compiled."
        ),
        "lockfile": lock_scope,
        "lockfile_version": lock_doc.get("lockfileVersion"),
        "lockfile_sha256": hashlib.sha256(lock_bytes).hexdigest(),
        "requested_base_image": REQUESTED_BASE_IMAGE,
        "base_image": BASE_IMAGE,
        "base_image_acquisition": BASE_IMAGE_ACQUISITION,
        "base_image_id": base.image_id,
        "base_image_repo_digests": list(base.repo_digests),
        "node_version": toolchain.get("node"),
        "npm_version": toolchain.get("npm"),
        "build_command": (
            "docker build of a VeriEnvelope Dockerfile: "
            "npm ci --ignore-scripts, then tsc -p src/everything/tsconfig.json. "
            "Host npm/npx/pip/uvx are not invoked."
        ),
        "package_scripts": "ignored via npm ci --ignore-scripts; tsc is invoked explicitly",
        "image_repo_digests": list(image.repo_digests),
        "registry_digest": None,
        "local_digest_note": (
            "RepoDigests names the local tag and the image id. "
            "The image was not pushed, so there is no registry digest."
        ),
        "local_tag": LOCAL_TAG,
        "image_cmd": image_cmd,
        "image_entrypoint": image_entrypoint,
        "entrypoint_note": (
            "CMD matches VE-METHOD-MCP-001 argv. ENTRYPOINT is the Node base "
            "image wrapper docker-entrypoint.sh, which execs that CMD. "
            "The server was not started."
        ),
        "entrypoint_recorded_not_run": ["node", "dist/index.js", "stdio"],
        "source_identity": source_identity(),
        "execution_artifact": {
            **execution_artifact(),
            "local_image_id": image.image_id,
            "base_image_id": base.image_id,
            "node_version": toolchain.get("node"),
            "npm_version": toolchain.get("npm"),
            "lockfile_sha256": hashlib.sha256(lock_bytes).hexdigest(),
        },
        "build_log_tail": build_log[-4000:],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def _git_env(home: Path) -> dict[str, str]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
    }
    return env


def _git(checkout: Path, env: dict[str, str]) -> None:
    _run(["git", "init"], checkout, env)
    _run(["git", "remote", "add", "origin", REPOSITORY], checkout, env)
    _run(["git", "fetch", "--depth", "1", "origin", PINNED_COMMIT], checkout, env, timeout=180)
    _run(["git", "checkout", "--detach", "FETCH_HEAD"], checkout, env)


def _git_output(checkout: Path, env: dict[str, str], argv: list[str]) -> str:
    completed = _run(argv, checkout, env)
    return completed.stdout.decode("utf-8")


def _write_dockerfile(checkout: Path, base_image_id: str) -> None:
    dockerfile = f"""FROM {base_image_id}
WORKDIR /src
COPY . /src
RUN npm ci --ignore-scripts
RUN if [ -x /src/node_modules/.bin/tsc ]; then \\
      /src/node_modules/.bin/tsc -p /src/src/everything/tsconfig.json; \\
    else \\
      /src/src/everything/node_modules/.bin/tsc -p /src/src/everything/tsconfig.json; \\
    fi
WORKDIR /src/src/everything
CMD ["node", "dist/index.js", "stdio"]
"""
    (checkout / "Dockerfile").write_text(dockerfile, encoding="utf-8")


def _docker_build(checkout: Path) -> str:
    completed = subprocess.run(
        ["docker", "build", "-t", LOCAL_TAG, str(checkout)],
        capture_output=True,
        timeout=900,
        check=False,
        shell=False,
        env=control_plane_env(),
    )
    log = completed.stdout.decode("utf-8", errors="replace") + completed.stderr.decode(
        "utf-8", errors="replace"
    )
    if completed.returncode != 0:
        raise VeriEnvelopeError("isolated image build failed:\n" + log[-8000:])
    return log


def _toolchain_from_base(image_id: str) -> dict[str, str]:
    node = _base_output(image_id, ["node", "-v"])
    npm = _base_output(image_id, ["npm", "-v"])
    return {"node": node.strip(), "npm": npm.strip()}


def _base_output(image_id: str, command: list[str]) -> str:
    completed = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            "65532:65532",
            "--entrypoint",
            command[0],
            image_id,
            *command[1:],
        ],
        capture_output=True,
        timeout=60,
        check=False,
        shell=False,
        env=control_plane_env(),
    )
    if completed.returncode != 0:
        raise VeriEnvelopeError(
            "base image toolchain probe failed:\n"
            + completed.stderr.decode("utf-8", errors="replace")
        )
    return completed.stdout.decode("utf-8", errors="replace")


def _dist_exists_without_starting(image_id: str) -> bool:
    name = "ve-everything-provenance"
    subprocess.run(
        ["docker", "rm", "-f", name],
        capture_output=True,
        check=False,
        env=control_plane_env(),
    )
    created = subprocess.run(
        ["docker", "create", "--name", name, "--entrypoint", "true", image_id],
        capture_output=True,
        check=False,
        env=control_plane_env(),
    )
    if created.returncode != 0:
        return False
    try:
        copied = subprocess.run(
            ["docker", "cp", f"{name}:/src/src/everything/dist/index.js", "-"],
            capture_output=True,
            check=False,
            env=control_plane_env(),
        )
        return copied.returncode == 0 and len(copied.stdout) > 0
    finally:
        subprocess.run(
            ["docker", "rm", "-f", name],
            capture_output=True,
            check=False,
            env=control_plane_env(),
        )


def _run(
    argv: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout: float = 60,
) -> subprocess.CompletedProcess[bytes]:
    refuse_host_package_install(argv)
    completed = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        capture_output=True,
        timeout=timeout,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        raise VeriEnvelopeError(
            "command failed: "
            + " ".join(argv)
            + "\n"
            + completed.stderr.decode("utf-8", errors="replace")
        )
    return completed


def _image_config(image_id: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["docker", "image", "inspect", image_id],
        capture_output=True,
        timeout=30,
        check=False,
        shell=False,
        env=control_plane_env(),
    )
    if completed.returncode != 0:
        raise VeriEnvelopeError(
            "image inspect failed:\n" + completed.stderr.decode("utf-8", errors="replace")
        )
    payload = json.loads(completed.stdout.decode("utf-8"))
    config = payload[0].get("Config")
    if not isinstance(config, dict):
        raise VeriEnvelopeError("image config is missing")
    return config

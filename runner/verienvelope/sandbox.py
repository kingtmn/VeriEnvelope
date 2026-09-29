"""Minimum OCI boundary for a later pilot run.

This module can start a process inside the runtime boundary. `run_case` does not
call it. The one external initialize lives in `mcp_c1` and uses these flags.

Acquisition and runtime are different operations. Runtime never pulls an image
and never runs npm, npx, pip, or uvx on the host. A pull, if one is requested,
is `pull_image` only.
"""

from __future__ import annotations

import json
import os
import selectors
import subprocess
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from verienvelope.errors import PolicyError, VeriEnvelopeError

HOST_PACKAGE_COMMANDS = frozenset({"npm", "npx", "pip", "pip3", "uv", "uvx"})
_CONTROL_PLANE_KEYS = (
    "PATH",
    "HOME",
    "DOCKER_HOST",
    "DOCKER_CONTEXT",
    "DOCKER_CONFIG",
    "DOCKER_CERT_PATH",
)
_CONTAINER_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
SANDBOX_POLICY_VERSION = "ADR-008-amendment-3"
PROCESS_ENV_NAMES = frozenset({"PATH", "LANG", "HOME"})
ISOLATED_HOME = "/work/home"


@dataclass(frozen=True)
class RuntimeLimits:
    cpus: str = "1"
    memory: str = "512m"
    pids_limit: int = 64
    timeout_seconds: float = 30
    user: str = "65532:65532"


@dataclass(frozen=True)
class ImagePin:
    reference: str
    image_id: str
    repo_digests: tuple[str, ...]


@dataclass(frozen=True)
class BoundaryObservation:
    network_mode: str
    readonly_rootfs: bool
    cap_drop: tuple[str, ...]
    security_opt: tuple[str, ...]
    user: str
    pids_limit: int | None
    memory: int
    nano_cpus: int
    mount_sources: tuple[str, ...]
    env: tuple[str, ...]


@dataclass(frozen=True)
class SandboxRun:
    image: ImagePin
    name: str
    exit_code: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool
    removed: bool
    boundary: BoundaryObservation


def refuse_host_package_install(argv: list[str]) -> None:
    if not argv:
        raise PolicyError("empty host command is refused")
    executable = Path(argv[0]).name
    if executable in HOST_PACKAGE_COMMANDS:
        raise PolicyError(
            f"host package install is refused: {executable}. "
            "Dependency acquisition has to happen inside an isolated build, "
            "not on the host."
        )


def split_container_env(config_env: tuple[str, ...] | list[str]) -> dict[str, Any]:
    """Separate image-declared names from the process wrapper.

    Docker Config.Env includes ENV from the image. The target process is
    started under env -i and only receives PATH and LANG. Image variables
    are recorded; they are not host inheritance and not the process environment.
    """
    image_defined: list[str] = []
    process_facing: list[str] = []
    for item in config_env:
        name, _, _value = item.partition("=")
        if name in PROCESS_ENV_NAMES:
            process_facing.append(item)
        else:
            image_defined.append(item)
    return {
        "host_inheritance": "none",
        "process_wrapper": "mkdir /work/home && env -i PATH LANG HOME=/work/home",
        "process_env_names": sorted(PROCESS_ENV_NAMES),
        "container_config_env": list(config_env),
        "image_defined_env": image_defined,
        "sandbox_policy": SANDBOX_POLICY_VERSION,
    }


def control_plane_env() -> dict[str, str]:
    """Environment for the docker client. It is not the container environment."""
    env: dict[str, str] = {}
    for key in _CONTROL_PLANE_KEYS:
        value = os.environ.get(key)
        if value:
            env[key] = value
    env.setdefault("PATH", "/usr/bin:/bin")
    return env


def pull_argv(reference: str) -> list[str]:
    if not reference or reference.strip() != reference:
        raise PolicyError("image reference is empty")
    return ["docker", "pull", reference]


def pull_image(reference: str) -> ImagePin:
    """Acquisition phase. This uses the network. Runtime does not call it."""
    completed = _docker(pull_argv(reference), timeout=120)
    if completed.returncode != 0:
        raise VeriEnvelopeError(
            "image pull failed:\n" + completed.stderr.decode("utf-8", errors="replace")
        )
    return pin_image(reference)


def pin_image(reference: str) -> ImagePin:
    completed = _docker(["docker", "image", "inspect", reference], timeout=30)
    if completed.returncode != 0:
        raise VeriEnvelopeError(
            f"image is not present locally: {reference}\n"
            + completed.stderr.decode("utf-8", errors="replace")
        )
    payload = json.loads(completed.stdout.decode("utf-8"))
    if not payload:
        raise VeriEnvelopeError(f"image inspect returned nothing: {reference}")
    image = payload[0]
    image_id = image.get("Id")
    if not isinstance(image_id, str) or not image_id.startswith("sha256:"):
        raise VeriEnvelopeError(f"image id is missing: {reference}")
    digests = image.get("RepoDigests") or []
    if not isinstance(digests, list):
        digests = []
    return ImagePin(
        reference=reference,
        image_id=image_id,
        repo_digests=tuple(item for item in digests if isinstance(item, str)),
    )


def runtime_flags(
    *,
    name: str,
    limits: RuntimeLimits,
    readonly_input: Path | None = None,
) -> list[str]:
    if limits.pids_limit < 1:
        raise PolicyError("pids_limit must be positive")
    if limits.timeout_seconds <= 0 or limits.timeout_seconds > 30:
        raise PolicyError("sandbox timeout_seconds must be within (0, 30]")
    flags = [
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
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=16m",
        "--env",
        f"PATH={_CONTAINER_PATH}",
        "--env",
        "LANG=C",
    ]
    if readonly_input is not None:
        source = _reject_bind(readonly_input)
        flags.extend(
            [
                "--mount",
                f"type=bind,source={source},target=/input,readonly",
            ]
        )
    return flags


def target_argv(command: list[str]) -> list[str]:
    """Start the target with an empty isolated HOME.

    Amendment 2. The directory is on the existing tmpfs /work. It is not the
    host home. Network, read-only root, capabilities, and the uid stay as before.
    """
    if not command:
        raise PolicyError("container command is empty")
    script = (
        "mkdir -p /work/home; "
        "path=$1; shift; "
        'exec env -i "PATH=$path" "LANG=C" "HOME=/work/home" "$@"'
    )
    return ["sh", "-c", script, "ve-sandbox", _CONTAINER_PATH, *command]


def run_command(
    *,
    image: str,
    command: list[str],
    limits: RuntimeLimits | None = None,
    readonly_input: Path | None = None,
    stdin: bytes | None = None,
) -> SandboxRun:
    """Run one command to completion. Does not pull. Does not mount the host home."""
    if not command:
        raise PolicyError("container command is empty")
    command = target_argv(command)
    limits = limits or RuntimeLimits()
    name = _container_name()
    pin = pin_image(image)
    flags = runtime_flags(name=name, limits=limits, readonly_input=readonly_input)
    create = ["docker", "create", *flags, image, *command]
    if stdin is not None:
        create.insert(2, "-i")
    created = _docker(create, timeout=30)
    if created.returncode != 0:
        raise VeriEnvelopeError(
            "container create failed:\n" + created.stderr.decode("utf-8", errors="replace")
        )
    timed_out = False
    exit_code: int | None = None
    stdout = b""
    stderr = b""
    try:
        boundary = _observe(name)
        run_args = ["docker", "start", "-a", name]
        if stdin is not None:
            run_args = ["docker", "start", "-ai", name]
        try:
            completed = _docker(run_args, timeout=limits.timeout_seconds, stdin=stdin)
            exit_code = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = _as_bytes(exc.stdout)
            stderr = _as_bytes(exc.stderr)
    finally:
        _docker(["docker", "rm", "-f", name], timeout=30)
    removed = not _container_present(name)
    return SandboxRun(
        image=pin,
        name=name,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        removed=removed,
        boundary=boundary,
    )


def _reject_bind(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.name == "docker.sock":
        raise PolicyError("docker socket mount is refused")
    home = Path.home().resolve()
    if resolved == home or home in resolved.parents:
        raise PolicyError("host home mount is refused")
    return resolved


def _container_name() -> str:
    return "ve-sbx-" + uuid.uuid4().hex[:12]


def _observe(name: str) -> BoundaryObservation:
    completed = _docker(["docker", "inspect", name], timeout=30)
    if completed.returncode != 0:
        raise VeriEnvelopeError(f"container inspect failed: {name}")
    payload = json.loads(completed.stdout.decode("utf-8"))
    host = payload[0]["HostConfig"]
    config = payload[0]["Config"]
    mounts = payload[0].get("Mounts") or []
    sources = tuple(
        mount.get("Source", "")
        for mount in mounts
        if mount.get("Type") == "bind"
    )
    cap_drop = tuple(host.get("CapDrop") or [])
    security = tuple(host.get("SecurityOpt") or [])
    env = tuple(config.get("Env") or [])
    return BoundaryObservation(
        network_mode=str(host.get("NetworkMode")),
        readonly_rootfs=bool(host.get("ReadonlyRootfs")),
        cap_drop=cap_drop,
        security_opt=security,
        user=str(config.get("User") or ""),
        pids_limit=host.get("PidsLimit"),
        memory=int(host.get("Memory") or 0),
        nano_cpus=int(host.get("NanoCpus") or 0),
        mount_sources=sources,
        env=env,
    )


def _container_present(name: str) -> bool:
    completed = _docker(
        ["docker", "ps", "-aq", "--filter", f"name=^{name}$"],
        timeout=30,
    )
    return bool(completed.stdout.strip())


def _docker(
    argv: list[str],
    *,
    timeout: float,
    stdin: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    refuse_host_package_install(argv)
    return subprocess.run(
        argv,
        input=stdin,
        capture_output=True,
        timeout=timeout,
        check=False,
        shell=False,
        env=control_plane_env(),
    )


class StdioSession:
    """Interactive stdin/stdout for one ephemeral container.

    The target process stays inside the runtime boundary. This object is the
    host-side pipe. It does not pull an image.
    """

    def __init__(
        self,
        *,
        image: str,
        command: list[str],
        limits: RuntimeLimits | None = None,
        readonly_input: Path | None = None,
    ) -> None:
        if not command:
            raise PolicyError("container command is empty")
        self.limits = limits or RuntimeLimits()
        self.name = _container_name()
        self.image = pin_image(image)
        self.command = target_argv(command)
        self.readonly_input = readonly_input
        self.boundary: BoundaryObservation | None = None
        self.timed_out = False
        self.exit_code: int | None = None
        self._proc: subprocess.Popen[bytes] | None = None
        self._stderr = bytearray()
        self._stderr_thread: threading.Thread | None = None
        self._closed = False

    def __enter__(self) -> "StdioSession":
        flags = runtime_flags(
            name=self.name,
            limits=self.limits,
            readonly_input=self.readonly_input,
        )
        create = ["docker", "create", "-i", *flags, self.image.image_id, *self.command]
        created = _docker(create, timeout=30)
        if created.returncode != 0:
            raise VeriEnvelopeError(
                "container create failed:\n" + created.stderr.decode("utf-8", errors="replace")
            )
        try:
            self.boundary = _observe(self.name)
            self._proc = subprocess.Popen(
                ["docker", "start", "-ai", self.name],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=control_plane_env(),
            )
        except Exception:
            self.close()
            raise
        assert self._proc.stderr is not None
        self._stderr_thread = threading.Thread(
            target=_drain_stderr,
            args=(self._proc.stderr, self._stderr),
            daemon=True,
        )
        self._stderr_thread.start()
        return self

    def write_line(self, payload: bytes) -> None:
        proc = self._require_proc()
        if proc.stdin is None:
            raise VeriEnvelopeError("stdio session has no stdin")
        if not payload.endswith(b"\n"):
            payload += b"\n"
        proc.stdin.write(payload)
        proc.stdin.flush()

    def read_line(self, timeout: float) -> bytes:
        proc = self._require_proc()
        if proc.stdout is None:
            raise VeriEnvelopeError("stdio session has no stdout")
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ)
        try:
            ready = selector.select(timeout)
        finally:
            selector.close()
        if not ready:
            self.timed_out = True
            raise subprocess.TimeoutExpired(proc.args, timeout)
        return proc.stdout.readline()

    def close_stdin(self) -> None:
        proc = self._proc
        if proc is None or proc.stdin is None:
            return
        proc.stdin.close()

    @property
    def stderr(self) -> bytes:
        return bytes(self._stderr)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        proc = self._proc
        if proc is not None:
            if proc.stdin is not None and not proc.stdin.closed:
                proc.stdin.close()
            try:
                self.exit_code = proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                self.exit_code = proc.wait(timeout=2)
            if self._stderr_thread is not None:
                self._stderr_thread.join(timeout=2)
        _docker(["docker", "rm", "-f", self.name], timeout=30)

    def removed(self) -> bool:
        return not _container_present(self.name)

    def __exit__(self, exc_type, exc, tb) -> None:
        if isinstance(exc, subprocess.TimeoutExpired):
            self.timed_out = True
        self.close()

    def _require_proc(self) -> subprocess.Popen[bytes]:
        if self._proc is None:
            raise VeriEnvelopeError("stdio session is not open")
        return self._proc


def _drain_stderr(pipe, bucket: bytearray) -> None:
    try:
        while True:
            chunk = pipe.read(4096)
            if not chunk:
                break
            bucket.extend(chunk)
    except Exception:
        return


def _as_bytes(value: bytes | str | None) -> bytes:
    if value is None:
        return b""
    if isinstance(value, str):
        return value.encode("utf-8")
    return value

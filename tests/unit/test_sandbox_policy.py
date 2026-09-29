import inspect
from pathlib import Path

import pytest

from verienvelope.errors import PolicyError
from verienvelope.sandbox import (
    RuntimeLimits,
    control_plane_env,
    pull_argv,
    refuse_host_package_install,
    run_command,
    runtime_flags,
    target_argv,
)


def test_host_package_install_is_refused() -> None:
    for argv in (
        ["npm", "install"],
        ["npx", "-y", "@modelcontextprotocol/server-everything"],
        ["pip", "install", "something"],
        ["uvx", "some-tool"],
    ):
        with pytest.raises(PolicyError):
            refuse_host_package_install(argv)


def test_runtime_flags_keep_the_boundary(tmp_path: Path) -> None:
    flags = runtime_flags(name="ve-sbx-test", limits=RuntimeLimits(), readonly_input=tmp_path)
    text = " ".join(flags)
    assert "--network" in flags and flags[flags.index("--network") + 1] == "none"
    assert "--read-only" in flags
    assert "ALL" in flags
    assert "no-new-privileges" in flags
    assert "65532:65532" in flags
    assert "--pids-limit" in flags
    assert "--memory" in flags
    assert "--cpus" in flags
    assert "docker.sock" not in text
    assert str(Path.home()) not in text
    assert f"source={tmp_path.resolve()}" in text
    assert "readonly" in text
    assert "/tmp:rw,noexec,nosuid,nodev,size=16m" in flags
    assert "type=bind,source=/tmp" not in text


def test_home_and_socket_mounts_are_refused(tmp_path: Path) -> None:
    with pytest.raises(PolicyError, match="home"):
        runtime_flags(
            name="ve-sbx-test",
            limits=RuntimeLimits(),
            readonly_input=Path.home() / "notes.txt",
        )
    socket = tmp_path / "docker.sock"
    with pytest.raises(PolicyError, match="socket"):
        runtime_flags(name="ve-sbx-test", limits=RuntimeLimits(), readonly_input=socket)


def test_isolated_home_is_not_the_host_home() -> None:
    argv = target_argv(["node", "/app/start.sh"])
    text = " ".join(argv)
    assert "HOME=/work/home" in text
    assert "env -i" in text
    assert str(Path.home()) not in text
    assert "/Users/" not in text


def test_acquisition_is_not_part_of_runtime() -> None:
    assert pull_argv("python:3.11-slim") == ["docker", "pull", "python:3.11-slim"]
    assert "pull_image" not in inspect.getsource(run_command)


def test_control_plane_env_drops_a_secret(monkeypatch) -> None:
    monkeypatch.setenv("VE_TEST_SECRET", "ve-test-secret")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "ve-test-secret")
    env = control_plane_env()
    assert "VE_TEST_SECRET" not in env
    assert "AWS_SECRET_ACCESS_KEY" not in env

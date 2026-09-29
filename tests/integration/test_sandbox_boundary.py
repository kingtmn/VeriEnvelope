"""Boundary tests for a process we control.

These runs are not evidence about an external component. They do not start
the Everything server and they do not install anything on the host.
"""

from pathlib import Path

import pytest

from verienvelope.sandbox import RuntimeLimits, pin_image, run_command

SUBSTRATE = "python:3.11-slim"
# Local image inspected on this machine before the tests. A moved tag must fail.
EXPECTED_IMAGE_ID = (
    "sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6"
)
TIGHT = RuntimeLimits(
    cpus="0.5",
    memory="128m",
    pids_limit=16,
    timeout_seconds=10,
)


def _assert_common(run) -> None:
    assert run.image.image_id == EXPECTED_IMAGE_ID
    assert run.image.repo_digests
    assert run.removed is True
    assert run.boundary.network_mode == "none"
    assert run.boundary.readonly_rootfs is True
    assert "ALL" in run.boundary.cap_drop
    assert any("no-new-privileges" in item for item in run.boundary.security_opt)
    assert run.boundary.user == "65532:65532"
    assert run.boundary.nano_cpus == 500_000_000
    assert run.boundary.memory == 128 * 1024 * 1024
    assert run.boundary.pids_limit == TIGHT.pids_limit
    assert run.boundary.mount_sources == ()
    assert not any(item.startswith("VE_TEST_SECRET=") for item in run.boundary.env)
    home = str(Path.home())
    assert all(not source.startswith(home) for source in run.boundary.mount_sources)
    assert b"ve-test-secret" not in run.stdout
    assert b"ve-test-secret" not in run.stderr


@pytest.fixture(scope="module")
def substrate() -> str:
    pin = pin_image(SUBSTRATE)
    assert pin.image_id == EXPECTED_IMAGE_ID
    return SUBSTRATE


def test_network_is_blocked(substrate: str, monkeypatch) -> None:
    monkeypatch.setenv("VE_TEST_SECRET", "ve-test-secret")
    run = run_command(
        image=substrate,
        command=[
            "python",
            "-c",
            "import socket\n"
            "s=socket.socket(); s.settimeout(2)\n"
            "try:\n"
            " s.connect(('1.1.1.1', 80)); print('net:ok')\n"
            "except Exception:\n"
            " print('net:fail')\n",
        ],
        limits=TIGHT,
    )
    _assert_common(run)
    assert b"net:fail" in run.stdout
    assert run.timed_out is False


def test_secret_and_home_are_unavailable(substrate: str, monkeypatch) -> None:
    monkeypatch.setenv("VE_TEST_SECRET", "ve-test-secret")
    home = str(Path.home())
    run = run_command(
        image=substrate,
        command=[
            "python",
            "-c",
            "import os, pathlib\n"
            f"print('secret', os.environ.get('VE_TEST_SECRET', 'absent'))\n"
            "print('gpg', 'GPG_KEY' in os.environ)\n"
            f"print('home', pathlib.Path({home!r}).exists())\n"
            "print('keys', ','.join(sorted(os.environ)))\n",
        ],
        limits=TIGHT,
    )
    _assert_common(run)
    assert b"secret absent" in run.stdout
    assert b"gpg False" in run.stdout
    assert b"home False" in run.stdout
    assert b"keys HOME,LANG,LC_CTYPE,PATH" in run.stdout


def test_only_the_temporary_directory_is_writable(substrate: str) -> None:
    run = run_command(
        image=substrate,
        command=[
            "python",
            "-c",
            "import pathlib\n"
            "try:\n"
            " pathlib.Path('/etc/ve-write').write_text('x'); print('root:ok')\n"
            "except Exception:\n"
            " print('root:fail')\n"
            "try:\n"
            " pathlib.Path('/work/ok').write_text('x'); print('work:ok')\n"
            "except Exception:\n"
            " print('work:fail')\n",
        ],
        limits=TIGHT,
    )
    _assert_common(run)
    assert b"root:fail" in run.stdout
    assert b"work:ok" in run.stdout


def test_pid_limit_stops_further_forks(substrate: str) -> None:
    limits = RuntimeLimits(
        cpus="0.5",
        memory="128m",
        pids_limit=8,
        timeout_seconds=10,
    )
    run = run_command(
        image=substrate,
        command=[
            "python",
            "-c",
            "import os\n"
            "fails=0\n"
            "forked=0\n"
            "for _ in range(30):\n"
            " try:\n"
            "  pid=os.fork()\n"
            " except OSError:\n"
            "  fails += 1\n"
            "  break\n"
            " if pid==0:\n"
            "  os._exit(0)\n"
            " forked += 1\n"
            "print(f'forked {forked} fails {fails}')\n",
        ],
        limits=limits,
    )
    assert run.removed is True
    assert run.boundary.pids_limit == 8
    assert b"fails 1" in run.stdout


def test_isolated_tmp_accepts_mkdtemp(substrate: str) -> None:
    run = run_command(
        image=substrate,
        command=["python", "-c", "import tempfile; print(tempfile.mkdtemp(prefix='ve-tmp-'), end='')"],
        limits=TIGHT,
    )
    _assert_common(run)
    assert run.stdout.startswith(b"/tmp/ve-tmp-")
    assert run.timed_out is False


def test_timeout_cleans_up_the_container(substrate: str) -> None:
    limits = RuntimeLimits(
        cpus="0.5",
        memory="128m",
        pids_limit=16,
        timeout_seconds=2,
    )
    run = run_command(
        image=substrate,
        command=["python", "-c", "import time; time.sleep(20)"],
        limits=limits,
    )
    assert run.timed_out is True
    assert run.removed is True
    assert run.exit_code is None


def test_stdio_roundtrip_stays_inside_the_boundary(substrate: str) -> None:
    run = run_command(
        image=substrate,
        command=["python", "-c", "import sys; sys.stdout.write(sys.stdin.readline())"],
        limits=TIGHT,
        stdin=b"ve-stdio\n",
    )
    _assert_common(run)
    assert run.stdout == b"ve-stdio\n"
    assert run.timed_out is False


def test_node_base_process_does_not_receive_image_env() -> None:
    from verienvelope.artifact_identity import BASE_IMAGE_ID

    run = run_command(
        image=BASE_IMAGE_ID,
        command=["printenv"],
        limits=TIGHT,
    )
    names = {
        line.split("=", 1)[0]
        for line in run.stdout.decode("utf-8").splitlines()
        if line
    }
    assert names == {"PATH", "LANG", "HOME"}
    values = dict(
        line.split("=", 1)
        for line in run.stdout.decode("utf-8").splitlines()
        if "=" in line
    )
    assert values["HOME"] == "/work/home"
    config = "\n".join(run.boundary.env)
    assert "NODE_VERSION=22.12.0" in config
    assert "YARN_VERSION=1.22.22" in config
    assert run.removed is True

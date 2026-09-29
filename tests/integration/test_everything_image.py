"""The pinned Everything image is local provenance, not a run."""

import json
import subprocess

from tests.paths import ROOT
from verienvelope.pilot_preflight import gate_open
from verienvelope.sandbox import control_plane_env

RECORD = ROOT / "registry" / "candidates" / "everything-build.json"


def test_recorded_image_matches_local_inspect_and_was_not_started() -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    assert record["executed"] is False
    assert record["pushed"] is False
    assert record["registry_digest"] is None
    assert record["execution_contradiction"] is False
    assert record["commit"] == "f46d9578190b476b3501923ea8977d899e8db2cb"
    assert record["image_cmd"] == ["node", "dist/index.js", "stdio"]
    assert gate_open() is True
    inspected = subprocess.run(
        ["docker", "image", "inspect", record["local_tag"]],
        capture_output=True,
        check=False,
        env=control_plane_env(),
    )
    assert inspected.returncode == 0, inspected.stderr.decode("utf-8", errors="replace")
    image = json.loads(inspected.stdout.decode("utf-8"))[0]
    assert image["Id"] == record["image_digest"]
    assert image["Config"]["Cmd"] == ["node", "dist/index.js", "stdio"]
    running = subprocess.run(
        ["docker", "ps", "-q", "--filter", f"ancestor={record['image_digest']}"],
        capture_output=True,
        check=False,
        env=control_plane_env(),
    )
    assert running.returncode == 0
    assert running.stdout.strip() == b""

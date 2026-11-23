"""Regression guards for the release workflow.

The workflow failed for years without anyone noticing because nothing verified
that it could produce the asset it promises to attach.
"""

from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "release.yml"


def _step(name: str) -> dict:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["build"]["steps"]
    return next(step for step in steps if step.get("name") == name)


def test_release_job_can_upload_an_asset() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert workflow["permissions"]["contents"] == "write"


def test_build_step_extracts_the_binary_from_the_image() -> None:
    build = _step("Build binary")["run"]
    assert "docker build -t podman-compose-bin ." in build
    # docker build has no volume flag; the old workflow passed one and died.
    assert "-v" not in build
    assert "docker create --name podman-compose-bin podman-compose-bin" in build
    assert (
        "docker cp podman-compose-bin:/result/podman-compose release/podman-compose-linux-x86"
        in build
    )


def test_upload_step_uses_the_renamed_asset() -> None:
    assert _step("Upload release asset")["with"]["files"] == "./release/podman-compose-linux-x86"

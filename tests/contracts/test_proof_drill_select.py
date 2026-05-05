from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "proof-drill-select"


def _json(*args: str) -> dict:
    result = subprocess.run([str(SCRIPT), *args, "--json"], cwd=REPO, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr + result.stdout
    return json.loads(result.stdout)


def test_selects_headless_docker_proof_command() -> None:
    payload = _json("--scope", "os-self", "--class", "proof-drill", "--contains", "headless")
    ids = {entry["id"] for entry in payload["entries"]}
    assert "headless-docker-service-drill" in ids
    assert "headless-codex-provider-smoke" in ids
    for entry in payload["entries"]:
        assert entry["opt_in_required"] is True


def test_consumer_default_profile_excludes_maintainer_drills() -> None:
    payload = _json("--scope", "consumer-project", "--profile", "consumer-default")
    assert [entry["id"] for entry in payload["entries"]] == ["consumer-project-run-tests"]
    assert payload["entries"][0]["opt_in_required"] is False


def test_command_output_prints_only_commands() -> None:
    result = subprocess.run(
        [str(SCRIPT), "--id", "headless-codex-provider-smoke", "--commands"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip().startswith("COS_RUN_PROVIDER_SMOKE=1")
    assert "COS_CODEX_EXEC_MODEL" in result.stdout

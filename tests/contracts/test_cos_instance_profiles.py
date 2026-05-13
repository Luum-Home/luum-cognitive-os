from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "manifests" / "cos-instance-profiles.yaml"
SCRIPT = REPO_ROOT / "scripts" / "cos-instance-init"
ADR = REPO_ROOT / "docs" / "02-Decisions" / "adrs" / "ADR-163-cos-instance-installer.md"
ARCH = REPO_ROOT / "docs" / "architecture" / "cos-instance-installer.md"
MANUAL = REPO_ROOT / "docs" / "manual-tests" / "cos-instance-installer.md"

REQUIRED_PROFILE_FIELDS = {
    "id",
    "display_name",
    "status",
    "proof_level",
    "target",
    "entrypoints",
    "writes",
    "requires",
    "smoke_commands",
    "proof_drill_ids",
    "evidence_sources",
}


def _manifest() -> dict:
    return yaml.safe_load(MANIFEST.read_text())


def _run(*args: str) -> dict:
    result = subprocess.run([str(SCRIPT), *args], cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr + result.stdout
    return json.loads(result.stdout)


def test_instance_profile_manifest_contract() -> None:
    data = _manifest()
    assert data["schema_version"] == "cos-instance-profiles.v1"
    assert str(data["review_date"]) == "2026-05-05"
    assert data["separation_of_concerns"]["consumer_project_installer"]["command"] == "scripts/cos_init.py"
    assert data["separation_of_concerns"]["cos_instance_installer"]["command"] == "scripts/cos-instance-init"

    ids: set[str] = set()
    for profile in data["profiles"]:
        missing = REQUIRED_PROFILE_FIELDS - set(profile)
        assert not missing, f"{profile.get('id', '<missing-id>')} missing {sorted(missing)}"
        assert profile["id"] not in ids
        ids.add(profile["id"])
        assert isinstance(profile["entrypoints"], list)
        assert isinstance(profile["writes"], list)
        assert isinstance(profile["smoke_commands"], list)
        assert isinstance(profile["proof_drill_ids"], list)
        assert isinstance(profile["evidence_sources"], list)

    assert {"local", "docker-headless", "host-cli-bridge", "vm", "k8s"} <= ids
    assert "copying ~/.codex/auth.json" in data["blocked_behaviors"]
    assert "copying ~/.claude" in data["blocked_behaviors"]


def test_local_and_docker_profiles_dry_run() -> None:
    local = _run("--profile", "local", "--dry-run", "--json")
    docker = _run("--profile", "docker-headless", "--dry-run", "--json")

    assert local["mode"] == "dry-run"
    assert local["plan"]["profile"] == "local"
    assert docker["plan"]["profile"] == "docker-headless"
    assert docker["plan"]["file_checks"]
    assert "scripts/cos-headless-service-drill --json" in docker["plan"]["smoke_commands"]
    assert {row["id"] for row in docker["plan"]["proof_drills"]} >= {"headless-docker-service-drill", "headless-codex-provider-smoke"}


def test_instance_doctor_and_smoke_expose_proof_drill_handoff() -> None:
    docker = _run("--profile", "docker-headless", "--dry-run", "--doctor", "--smoke", "--json")
    assert docker["plan"]["proof_drills"]
    assert any(row["opt_in_required"] for row in docker["plan"]["proof_drills"])
    assert any("opt-in drills are not executed automatically" in note for note in docker["plan"]["notes"])


def test_write_creates_instance_metadata_in_disposable_workspace() -> None:
    with tempfile.TemporaryDirectory(prefix="cos-instance-contract.") as tmp:
        tmp_path = Path(tmp)
        repo = tmp_path / "repo"
        repo.mkdir()
        archive = subprocess.run(["git", "archive", "HEAD"], cwd=REPO_ROOT, capture_output=True, check=True)
        extract = subprocess.run(["tar", "-x", "-C", str(repo)], input=archive.stdout, capture_output=True, check=False)
        assert extract.returncode == 0, extract.stderr.decode(errors="replace")

        for profile in ("local", "docker-headless"):
            result = subprocess.run(
                [str(SCRIPT), "--project-dir", str(repo), "--profile", profile, "--write", "--json"],
                cwd=repo,
                text=True,
                capture_output=True,
                check=False,
            )
            assert result.returncode == 0, result.stderr + result.stdout
            payload = json.loads(result.stdout)
            assert payload["result"]["status"] == "written"
            assert (repo / ".cognitive-os" / "instances" / profile / "instance.json").exists()
            assert (repo / ".cognitive-os" / "instances" / profile / "commands.md").exists()


def test_planned_profiles_are_write_blocked() -> None:
    result = subprocess.run(
        [str(SCRIPT), "--profile", "host-cli-bridge", "--write", "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["result"]["status"] == "write-blocked"


def test_docs_reference_instance_installer_contract() -> None:
    for path in (ADR, ARCH, MANUAL):
        text = path.read_text()
        assert "scripts/cos-instance-init" in text
        assert "manifests/cos-instance-profiles.yaml" in text or path == MANUAL
    assert "Cognitive OS is not an IDE plugin" in ARCH.read_text()

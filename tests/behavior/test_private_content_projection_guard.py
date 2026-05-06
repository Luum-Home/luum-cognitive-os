import json
import subprocess

import pytest


@pytest.mark.behavior
def test_private_content_audit_cli_classifies_strategy_as_local_only(project_root):
    result = subprocess.run(
        [
            "python3",
            str(project_root / "scripts" / "private_content_audit.py"),
            "--project-dir",
            str(project_root),
            "--classify",
            ".cognitive-os/strategy/research/02-real-self-improvement.md",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["classification"]["class"] == "local-only"
    assert payload["classification"]["surface_id"] == "strategy-private"


@pytest.mark.behavior
def test_private_content_audit_cli_blocks_unknown_root_in_strict_mode(tmp_path, project_root):
    (tmp_path / ".cognitive-os" / "strategy").mkdir(parents=True)
    (tmp_path / ".cognitive-os" / "new-private-root").mkdir(parents=True)

    result = subprocess.run(
        [
            "python3",
            str(project_root / "scripts" / "private_content_audit.py"),
            "--project-dir",
            str(tmp_path),
            "--manifest",
            str(project_root / "manifests" / "private-content.yaml"),
            "--unknown-surfaces",
            "--strict",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["summary"]["warn"] == 1
    assert payload["findings"][0]["code"] == "unknown-private-root"


@pytest.mark.behavior
def test_cos_private_content_audit_route_smoke(project_root):
    cos = project_root / "scripts" / "cos"
    result = subprocess.run(
        [str(cos), "private-content", "audit", "--json"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "private-content-audit/v1"
    assert payload["summary"]["block"] == 0


@pytest.mark.behavior
def test_cos_private_content_audit_wrapper_smoke(project_root):
    wrapper = project_root / "scripts" / "cos-private-content-audit"
    result = subprocess.run(
        [str(wrapper), "--strict", "--json"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "private-content-audit/v1"
    assert payload["summary"] == {"block": 0, "info": 0, "warn": 0}


@pytest.mark.behavior
def test_private_content_projection_blocks_strategy_export_to_cloud(project_root, tmp_path):
    result = subprocess.run(
        [
            "python3",
            str(project_root / "scripts" / "private_content_audit.py"),
            "--project-dir",
            str(tmp_path),
            "--manifest",
            str(project_root / "manifests" / "private-content.yaml"),
            "--check-projection",
            ".cognitive-os/strategy/research/02-real-self-improvement.md",
            "--destination",
            "cloud",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "block"
    assert payload["classification"]["class"] == "local-only"
    assert "class_disallows_export" in payload["reasons"]
    metric = tmp_path / ".cognitive-os" / "metrics" / "private-content-access.jsonl"
    assert metric.exists()


@pytest.mark.behavior
def test_private_content_projection_never_reads_or_exports_secret_paths(project_root, tmp_path):
    secret = tmp_path / ".env"
    secret.write_text("TOKEN=do-not-read\n", encoding="utf-8")
    result = subprocess.run(
        [
            str(project_root / "scripts" / "cos"),
            "private-content",
            "check-projection",
            str(secret),
            "--project-dir",
            str(tmp_path),
            "--manifest",
            str(project_root / "manifests" / "private-content.yaml"),
            "--destination",
            "cloud",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["classification"]["class"] == "secret-never-touch"
    assert payload["classification"]["may_read_content"] is False
    assert "secret_never_touch" in payload["reasons"]

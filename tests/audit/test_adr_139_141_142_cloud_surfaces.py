from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_engram_cloud_enroll_wrapper_exists_and_uses_generic_env_names() -> None:
    path = ROOT / "scripts" / "cos-engram-cloud-enroll"
    text = path.read_text(encoding="utf-8")

    assert path.exists()
    assert "engram cloud config --server" in text
    assert "engram cloud enroll" in text
    assert "ENGRAM_PROJECT_SCOPE" in text
    assert "ENGRAM_CLOUD_TOKEN" in text
    for blocked in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "CLAUDE_API_KEY", "QWEN_API_KEY"):
        assert blocked not in text


def test_engram_auto_sync_keeps_git_jsonl_and_adds_cloud_mode() -> None:
    hook = (ROOT / "packages" / "engram-sync" / "hooks" / "engram-auto-sync.sh").read_text(encoding="utf-8")
    sync = (ROOT / "scripts" / "engram-sync.sh").read_text(encoding="utf-8")

    assert '"$SYNC_SCRIPT" >/dev/null 2>&1 || true' in hook
    assert 'if [ "${ENGRAM_CLOUD_AUTOSYNC:-0}" = "1" ]; then' in hook
    assert '"$SYNC_SCRIPT" --cloud' in hook
    assert 'engram sync --cloud --project "$SCOPE"' in sync
    assert "ENGRAM_SYNC_MODE=\"engram-cloud\"" in sync
    assert "--cloud --all" not in sync


def test_cos_worker_compose_declares_local_engram_cloud_stack() -> None:
    compose = yaml.safe_load((ROOT / "docker" / "cos-worker" / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    assert "cos-engram-cloud-db" in services
    assert "cos-engram-cloud" in services
    cloud = services["cos-engram-cloud"]
    assert "engram-cloud" in cloud["profiles"]
    assert cloud["environment"]["ENGRAM_CLOUD_HOST"] == "0.0.0.0"
    assert "ENGRAM_DATABASE_URL" in cloud["environment"]
    assert cloud["command"] == ["engram", "cloud", "serve"]


def test_audit_archive_and_gdpr_procedure_exist() -> None:
    archive = ROOT / "scripts" / "cos-audit-archive"
    gdpr = ROOT / "docs" / "architecture" / "gdpr-erasure-procedure.md"

    assert archive.exists()
    assert gdpr.exists()
    assert "source_preserved" in archive.read_text(encoding="utf-8")
    assert "audit_class" in gdpr.read_text(encoding="utf-8")

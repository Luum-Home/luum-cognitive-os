"""Portability proof for shared local service daemon scripts."""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LOCAL_SERVICES = [
    "scripts/cos-postgres-local.sh",
    "scripts/cos-valkey-local.sh",
]


def test_local_service_scripts_anchor_to_runtime_project_dir_not_source_checkout() -> None:
    for rel in LOCAL_SERVICES:
        text = (REPO / rel).read_text(encoding="utf-8")
        assert "SCOPE: both" in "\n".join(text.splitlines()[:4])
        assert "COGNITIVE_OS_PROJECT_DIR" in text or "CLAUDE_PROJECT_DIR" in text
        assert ".cognitive-os/runtime" in text
        assert "/Users/" not in text

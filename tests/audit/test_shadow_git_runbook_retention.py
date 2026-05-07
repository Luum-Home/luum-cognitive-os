from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.mark.audit
def test_shadow_git_manifest_links_runbook_and_retention(project_root: Path) -> None:
    manifest = yaml.safe_load((project_root / "manifests" / "shadow-git.yaml").read_text())
    assert manifest["status"] == "active"
    assert set(manifest["restore"]["modes_implemented"]) == {"files_only", "conversation_only", "files_and_conversation"}
    assert manifest["retention"]["command"].startswith("scripts/cos-rollback --prune")
    assert (project_root / manifest["runbook"]).is_file()


@pytest.mark.audit
def test_shadow_git_runbook_documents_combined_restore(project_root: Path) -> None:
    text = (project_root / "docs/runbooks/shadow-git-rollback.md").read_text()
    assert "files_and_conversation" in text
    assert "--target-seq" in text
    assert "--prune" in text

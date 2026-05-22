from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "cos-token-savings-audit"


def load_module():
    loader = importlib.machinery.SourceFileLoader("cos_token_savings_audit", str(SCRIPT))
    spec = importlib.util.spec_from_loader("cos_token_savings_audit", loader)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["cos_token_savings_audit"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_audit_anonymizes_project_paths_by_default(tmp_path: Path) -> None:
    mod = load_module()
    project = tmp_path / "secret-customer-repo"
    project.mkdir()
    (project / "cognitive-os.yaml").write_text("project: {name: secret}\n", encoding="utf-8")
    (project / "README.md").write_text("readme text" * 100, encoding="utf-8")

    row = mod.analyze_project(project, "project-001")
    rendered = mod.render_markdown([row])

    assert row.project_path is None
    assert "secret-customer-repo" not in rendered
    assert "project-001" in rendered


def test_discovery_prefers_stronger_so_markers(tmp_path: Path) -> None:
    mod = load_module()
    weak = tmp_path / "weak"
    strong = tmp_path / "strong"
    weak.mkdir()
    strong.mkdir()
    (weak / ".claude").mkdir()
    (weak / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    (strong / "cognitive-os.yaml").write_text("project: {name: strong}\n", encoding="utf-8")
    (strong / ".cognitive-os").mkdir()

    projects = mod.discover_projects(tmp_path, limit=1)

    assert projects == [strong]

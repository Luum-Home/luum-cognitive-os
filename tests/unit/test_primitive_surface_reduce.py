from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "primitive_surface_reduce.py"
spec = importlib.util.spec_from_file_location("primitive_surface_reduce", MODULE_PATH)
assert spec and spec.loader
primitive_surface_reduce = importlib.util.module_from_spec(spec)
sys.modules["primitive_surface_reduce"] = primitive_surface_reduce
spec.loader.exec_module(primitive_surface_reduce)


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "hooks").mkdir(parents=True)
    (root / ".claude").mkdir()
    (root / "manifests").mkdir()
    (root / "scripts").mkdir()
    (root / "docs" / "business").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "packages" / "demo" / "hooks").mkdir(parents=True)
    (root / "cognitive-os.yaml").write_text("project:\n  name: luum-cognitive-os\n")
    (root / "scripts" / "primitive_surface_reduce.py").write_text("# marker\n")
    (root / "scripts" / "primitive_gap_snapshot.py").write_text("# marker\n")
    (root / "docs" / "business" / "durable-product-master-plan.md").write_text("# Plan\n")
    (root / "hooks" / "registered.sh").write_text("#!/usr/bin/env bash\ntrue\n")
    (root / "hooks" / "demoted.sh").write_text("#!/usr/bin/env bash\ntrue\n")
    (root / "hooks" / "tested-demoted.sh").write_text("#!/usr/bin/env bash\ntrue\n")
    (root / "packages" / "demo" / "hooks" / "optional.sh").write_text("#!/usr/bin/env bash\ntrue\n")
    (root / "hooks" / "optional.sh").symlink_to(root / "packages" / "demo" / "hooks" / "optional.sh")
    (root / ".claude" / "settings.json").write_text(
        json.dumps({"hooks": {"SessionStart": [{"hooks": [{"command": "bash hooks/registered.sh"}]}]}})
    )
    (root / "manifests" / "reduction-demotions.json").write_text(
        json.dumps(
            {
                "demotions": [
                    {"family": "hooks", "path": "hooks/demoted.sh"},
                    {"family": "hooks", "path": "hooks/tested-demoted.sh"},
                ]
            }
        )
    )
    (root / "manifests" / "optional-hook-aliases.json").write_text(
        json.dumps(
            {
                "aliases": [
                    {
                        "family": "hooks",
                        "path": "hooks/optional.sh",
                        "target": "../packages/demo/hooks/optional.sh",
                        "decision": "accepted-optional-alias",
                    }
                ]
            }
        )
    )
    (root / "tests" / "test_hooks.py").write_text("def test_hook(): assert 'tested-demoted.sh'\n")
    return root


def test_plan_hooks_marks_only_unregistered_demoted_untested_as_safe(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    actions = primitive_surface_reduce.plan_hooks(root)
    by_path = {action.path: action for action in actions}

    assert "hooks/registered.sh" not in by_path
    assert by_path["hooks/demoted.sh"].action == "archive-demoted-hook"
    assert by_path["hooks/demoted.sh"].safe_to_apply is True
    assert by_path["hooks/tested-demoted.sh"].action == "keep-demoted-tested-hook"
    assert by_path["hooks/tested-demoted.sh"].safe_to_apply is False
    assert "hooks/optional.sh" not in by_path


def test_apply_safe_archives_only_safe_hook(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    actions = primitive_surface_reduce.plan_hooks(root)

    applied = primitive_surface_reduce.apply_actions(root, actions)

    assert [action.path for action in applied] == ["hooks/demoted.sh"]
    assert not (root / "hooks" / "demoted.sh").exists()
    assert (root / "archive" / "primitive-surface" / "hooks" / "demoted.sh").exists()
    assert (root / "hooks" / "tested-demoted.sh").exists()
    assert (root / "hooks" / "optional.sh").is_symlink()


def test_cli_writes_plan_and_apply_reports(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    plan = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--project-dir", str(root), "--plan"],
        text=True,
        capture_output=True,
        check=False,
    )
    apply = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--project-dir", str(root), "--apply-safe"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert plan.returncode == 0, plan.stderr
    assert apply.returncode == 0, apply.stderr
    payload = json.loads((root / "docs" / "reports" / "primitive-surface-reduction-latest.json").read_text())
    assert payload["mode"] == "apply-safe"
    assert len(payload["applied"]) == 1
    assert "Primitive Surface Reduction" in (root / "docs" / "reports" / "primitive-surface-reduction-latest.md").read_text()


def test_cli_refuses_non_os_repo(tmp_path: Path) -> None:
    root = tmp_path / "target-project"
    root.mkdir()
    (root / "cognitive-os.yaml").write_text("project:\n  name: app\n")

    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--project-dir", str(root), "--plan"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "os-only" in result.stdout

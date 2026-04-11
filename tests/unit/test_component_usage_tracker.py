"""Unit tests for lib/component_usage_tracker.py.

All tests use tmp_path with synthetic mock files so no live repo
access is required.

Run with: pytest tests/unit/test_component_usage_tracker.py -v
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.component_usage_tracker import ComponentUsageTracker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """Minimal fake repo skeleton."""
    (tmp_path / "hooks").mkdir()
    (tmp_path / "lib").mkdir()
    (tmp_path / "rules").mkdir()
    (tmp_path / "skills").mkdir()
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True)
    return tmp_path


def make_settings(path: Path, hook_names: list[str]) -> None:
    commands = [
        {"type": "command", "command": f'bash "$CLAUDE_PROJECT_DIR/hooks/{h}"'}
        for h in hook_names
    ]
    data = {
        "hooks": {
            "PreToolUse": [{"matcher": "Agent", "hooks": commands}]
        }
    }
    path.write_text(json.dumps(data))


# ---------------------------------------------------------------------------
# Hook scan tests
# ---------------------------------------------------------------------------


def test_scan_hooks_finds_registered(repo: Path) -> None:
    (repo / "hooks" / "my-hook.sh").write_text("#!/bin/bash")
    make_settings(repo / ".claude" / "settings.json", ["my-hook.sh"])

    t = ComponentUsageTracker(str(repo))
    result = t.scan_hook_registrations()

    assert "my-hook.sh" in result["registered"]


def test_scan_hooks_finds_files(repo: Path) -> None:
    (repo / "hooks" / "alpha.sh").write_text("#!/bin/bash")
    (repo / "hooks" / "beta.sh").write_text("#!/bin/bash")

    t = ComponentUsageTracker(str(repo))
    result = t.scan_hook_registrations()

    assert "alpha.sh" in result["files_exist"]
    assert "beta.sh" in result["files_exist"]


def test_scan_hooks_unregistered(repo: Path) -> None:
    (repo / "hooks" / "registered.sh").write_text("#!/bin/bash")
    (repo / "hooks" / "orphan.sh").write_text("#!/bin/bash")
    make_settings(repo / ".claude" / "settings.json", ["registered.sh"])

    t = ComponentUsageTracker(str(repo))
    result = t.scan_hook_registrations()

    assert "orphan.sh" in result["exists_but_unregistered"]
    assert "registered.sh" not in result["exists_but_unregistered"]


def test_scan_hooks_registered_but_missing(repo: Path) -> None:
    # Register a hook that has no file on disk
    make_settings(repo / ".claude" / "settings.json", ["ghost-hook.sh"])

    t = ComponentUsageTracker(str(repo))
    result = t.scan_hook_registrations()

    assert "ghost-hook.sh" in result["registered_but_missing"]


def test_scan_hooks_coverage_pct(repo: Path) -> None:
    for name in ["a.sh", "b.sh", "c.sh", "d.sh"]:
        (repo / "hooks" / name).write_text("#!/bin/bash")
    make_settings(repo / ".claude" / "settings.json", ["a.sh", "b.sh"])

    t = ComponentUsageTracker(str(repo))
    result = t.scan_hook_registrations()

    assert result["coverage_pct"] == 50.0


# ---------------------------------------------------------------------------
# Lib import scan tests
# ---------------------------------------------------------------------------


def test_scan_libs_finds_imports(repo: Path) -> None:
    (repo / "lib" / "my_util.py").write_text("def foo(): pass")
    consumer = repo / "hooks" / "consumer.py"
    consumer.write_text("from lib.my_util import foo\nfoo()")

    t = ComponentUsageTracker(str(repo))
    result = t.scan_lib_imports()

    imported_names = [e["lib"] for e in result["imported"]]
    assert "my_util" in imported_names


def test_scan_libs_never_imported(repo: Path) -> None:
    (repo / "lib" / "orphaned_lib.py").write_text("def bar(): pass")

    t = ComponentUsageTracker(str(repo))
    result = t.scan_lib_imports()

    assert "orphaned_lib" in result["never_imported"]


def test_scan_libs_usage_pct(repo: Path) -> None:
    (repo / "lib" / "used.py").write_text("x=1")
    (repo / "lib" / "unused.py").write_text("y=2")
    (repo / "hooks" / "importer.py").write_text("from lib.used import x")

    t = ComponentUsageTracker(str(repo))
    result = t.scan_lib_imports()

    assert result["usage_pct"] == 50.0


# ---------------------------------------------------------------------------
# Rule reference scan tests
# ---------------------------------------------------------------------------


def test_scan_rules_referenced(repo: Path) -> None:
    (repo / "rules" / "my-rule.md").write_text("# My Rule")
    (repo / "rules" / "RULES-COMPACT.md").write_text(
        "Always active: [`my-rule`] is essential."
    )

    t = ComponentUsageTracker(str(repo))
    result = t.scan_rule_references()

    assert "my-rule" in result["referenced_in_compact"]


def test_scan_rules_unreferenced(repo: Path) -> None:
    (repo / "rules" / "orphan-rule.md").write_text("# Orphan")
    (repo / "rules" / "RULES-COMPACT.md").write_text("Nothing here.")

    t = ComponentUsageTracker(str(repo))
    result = t.scan_rule_references()

    assert "orphan-rule" in result["unreferenced"]


def test_scan_rules_total(repo: Path) -> None:
    for name in ["rule-a.md", "rule-b.md", "rule-c.md"]:
        (repo / "rules" / name).write_text(f"# {name}")
    (repo / "rules" / "RULES-COMPACT.md").write_text("stuff")

    t = ComponentUsageTracker(str(repo))
    result = t.scan_rule_references()

    assert result["total_rules"] == 3


# ---------------------------------------------------------------------------
# Skill metrics scan tests
# ---------------------------------------------------------------------------


def test_scan_skills_from_metrics(repo: Path) -> None:
    skill_dir = repo / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# My Skill")

    metrics_lines = [
        json.dumps({"skill": "my-skill", "tokens": 100, "success": True}),
        json.dumps({"skill": "my-skill", "tokens": 200, "success": True}),
    ]
    (repo / ".cognitive-os" / "metrics" / "skill-metrics.jsonl").write_text(
        "\n".join(metrics_lines)
    )

    t = ComponentUsageTracker(str(repo))
    result = t.scan_skill_metrics()

    invoked = [e["skill"] for e in result["invoked_ever"]]
    assert "my-skill" in invoked
    assert "my-skill" not in result["never_invoked"]


def test_scan_skills_broken_metrics(repo: Path) -> None:
    metrics_lines = [
        json.dumps({"skill": "s1", "tokens": 0, "success": False}),
        json.dumps({"skill": "s1", "tokens": 0, "success": True}),
        json.dumps({"skill": "s2", "tokens": 50, "success": True}),
    ]
    (repo / ".cognitive-os" / "metrics" / "skill-metrics.jsonl").write_text(
        "\n".join(metrics_lines)
    )

    t = ComponentUsageTracker(str(repo))
    result = t.scan_skill_metrics()

    assert result["broken_metrics"] == 2


def test_scan_skills_never_invoked(repo: Path) -> None:
    skill_dir = repo / "skills" / "silent-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Silent")
    # No metrics file at all

    t = ComponentUsageTracker(str(repo))
    result = t.scan_skill_metrics()

    assert "silent-skill" in result["never_invoked"]


# ---------------------------------------------------------------------------
# Full report tests
# ---------------------------------------------------------------------------


def test_generate_report_structure(repo: Path) -> None:
    t = ComponentUsageTracker(str(repo))
    report = t.generate_usage_report()

    assert "hooks" in report
    assert "libs" in report
    assert "rules" in report
    assert "skills" in report
    assert "dead_weight" in report

    dw = report["dead_weight"]
    assert "hooks" in dw
    assert "libs" in dw
    assert "rules" in dw
    assert "skills" in dw
    assert "total_dead" in dw
    assert "total_components" in dw
    assert "health_pct" in dw


def test_health_score_calculation(repo: Path) -> None:
    # 2 hooks exist, 1 registered → 1 dead hook
    for name in ["reg.sh", "unreg.sh"]:
        (repo / "hooks" / name).write_text("#!/bin/bash")
    make_settings(repo / ".claude" / "settings.json", ["reg.sh"])

    # 2 libs, 1 imported
    (repo / "lib" / "used.py").write_text("x=1")
    (repo / "lib" / "unused.py").write_text("y=2")
    (repo / "hooks" / "importer.py").write_text("from lib.used import x")

    t = ComponentUsageTracker(str(repo))
    report = t.generate_usage_report()
    dw = report["dead_weight"]

    # total_dead should be at least the 1 unregistered hook + 1 unused lib
    assert dw["total_dead"] >= 2
    assert 0.0 <= dw["health_pct"] <= 100.0
    assert dw["total_components"] > 0


def test_format_report_readable(repo: Path) -> None:
    t = ComponentUsageTracker(str(repo))
    report = t.generate_usage_report()
    text = t.format_usage_report(report)

    assert "COMPONENT USAGE REPORT" in text
    assert "HOOKS:" in text
    assert "LIBS:" in text
    assert "RULES:" in text
    assert "SKILLS:" in text
    assert "DEAD WEIGHT SUMMARY:" in text
    assert "Health score:" in text


# ---------------------------------------------------------------------------
# Resilience tests
# ---------------------------------------------------------------------------


def test_empty_project_no_crash(tmp_path: Path) -> None:
    """Handles a completely empty directory without crashing."""
    t = ComponentUsageTracker(str(tmp_path))
    report = t.generate_usage_report()
    text = t.format_usage_report(report)

    # Should produce a report with zero counts, not an exception
    assert "COMPONENT USAGE REPORT" in text
    assert report["dead_weight"]["total_components"] == 0

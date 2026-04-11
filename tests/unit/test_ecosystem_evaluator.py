"""Unit tests for lib/ecosystem_evaluator.py.

Coverage:
1.  test_check_plugins_returns_list          — even with no plugins dir, returns []
2.  test_check_plugins_finds_submodules      — detects .claude/plugins/* git dirs
3.  test_check_tools_reads_ecosystem_md      — parses EVALUATE/WATCH from markdown
4.  test_stale_detection_30_days             — >30 days marks tool as stale
5.  test_not_stale_recent                    — <30 days marks tool as not stale
6.  test_reinvention_name_match              — detects exact stem match
7.  test_format_report_readable              — output contains section headers
8.  test_no_crash_without_plugins            — graceful when plugins dir missing
9.  test_save_timestamp                      — creates the timestamp file
10. test_generate_report_structure           — report has plugins, tools, reinvention keys
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.ecosystem_evaluator import EcosystemEvaluator  # noqa: E402

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_project(tmp_path: Path) -> Path:
    """Minimal project layout."""
    (tmp_path / ".claude" / "plugins").mkdir(parents=True)
    (tmp_path / "lib").mkdir()
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True)
    return tmp_path


@pytest.fixture()
def evaluator(tmp_project: Path) -> EcosystemEvaluator:
    return EcosystemEvaluator(str(tmp_project))


@pytest.fixture()
def ecosystem_md_content() -> str:
    return """\
# Ecosystem Tools

### Archon — AI Agent Workflow Engine (EVALUATE)

| Property | Value |
|----------|-------|
| Purpose | YAML-defined DAG workflow engine |
| GitHub | [coleam00/Archon](https://github.com/coleam00/Archon) |
| License | MIT |
| Status | **EVALUATE** — Adopt patterns via clean-room |

### AgentGateway (Linux Foundation) — AI-Native Proxy (WATCH)

| Property | Value |
|----------|-------|
| Purpose | AI-native proxy for MCP/A2A |
| GitHub | [agentgateway/agentgateway](https://github.com/agentgateway/agentgateway) |
| License | Apache-2.0 |
| Status | **WATCH** — Compare with existing gateway |

### ccusage — Claude Code Token Analytics (ADOPT)

| Property | Value |
|----------|-------|
| Status | **ADOPT** — already in use |
"""


# ---------------------------------------------------------------------------
# 1. check_plugins_returns_list — no plugins dir
# ---------------------------------------------------------------------------

def test_check_plugins_returns_list_no_dir(tmp_path: Path) -> None:
    e = EcosystemEvaluator(str(tmp_path))
    # plugins dir does not exist
    result = e.check_plugin_updates()
    assert isinstance(result, list)
    assert result == []


# ---------------------------------------------------------------------------
# 2. check_plugins_finds_submodules
# ---------------------------------------------------------------------------

def test_check_plugins_finds_submodules(tmp_project: Path) -> None:
    # Create a fake git dir inside a plugin
    plugin_dir = tmp_project / ".claude" / "plugins" / "test-plugin"
    plugin_dir.mkdir()
    (plugin_dir / ".git").mkdir()

    e = EcosystemEvaluator(str(tmp_project))

    # Patch subprocess so we don't need a real remote
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = e.check_plugin_updates()

    assert len(result) == 1
    assert result[0]["plugin"] == "test-plugin"
    assert "new_commits" in result[0]
    assert "highlights" in result[0]
    assert "adoption_candidates" in result[0]


# ---------------------------------------------------------------------------
# 3. check_tools_reads_ecosystem_md
# ---------------------------------------------------------------------------

def test_check_tools_reads_ecosystem_md(
    tmp_project: Path, ecosystem_md_content: str
) -> None:
    md_path = tmp_project / "packages" / "ecosystem-tools" / "rules"
    md_path.mkdir(parents=True)
    (md_path / "ecosystem-tools.md").write_text(ecosystem_md_content)

    e = EcosystemEvaluator(str(tmp_project))
    tools = e.check_evaluated_tools()

    statuses = {t["name"]: t["status"] for t in tools}
    # ADOPT should not be included
    assert "ccusage — Claude Code Token Analytics" not in statuses
    # EVALUATE and WATCH should be included
    evaluate_names = [t["name"] for t in tools if t["status"] == "EVALUATE"]
    watch_names = [t["name"] for t in tools if t["status"] == "WATCH"]
    assert len(evaluate_names) >= 1
    assert len(watch_names) >= 1


# ---------------------------------------------------------------------------
# 4. stale_detection_30_days
# ---------------------------------------------------------------------------

def test_stale_detection_30_days(tmp_project: Path) -> None:
    md_path = tmp_project / "packages" / "ecosystem-tools" / "rules"
    md_path.mkdir(parents=True)
    md_file = md_path / "ecosystem-tools.md"
    md_file.write_text(
        "### OldTool (EVALUATE)\n"
        "| Status | **EVALUATE** — stale |\n"
    )

    # Set file mtime to 40 days ago
    old_mtime = time.time() - (40 * 86400)
    os.utime(str(md_file), (old_mtime, old_mtime))

    e = EcosystemEvaluator(str(tmp_project))
    tools = e.check_evaluated_tools()
    assert len(tools) >= 1
    assert tools[0]["is_stale"] is True
    assert tools[0]["days_since_eval"] > 30


# ---------------------------------------------------------------------------
# 5. not_stale_recent
# ---------------------------------------------------------------------------

def test_not_stale_recent(tmp_project: Path) -> None:
    md_path = tmp_project / "packages" / "ecosystem-tools" / "rules"
    md_path.mkdir(parents=True)
    md_file = md_path / "ecosystem-tools.md"
    md_file.write_text(
        "### NewTool (WATCH)\n"
        "| Status | **WATCH** — fresh |\n"
    )

    # File modified today (mtime = now)
    now = time.time()
    os.utime(str(md_file), (now, now))

    e = EcosystemEvaluator(str(tmp_project))
    tools = e.check_evaluated_tools()
    assert len(tools) >= 1
    assert tools[0]["is_stale"] is False


# ---------------------------------------------------------------------------
# 6. reinvention_name_match
# ---------------------------------------------------------------------------

def test_reinvention_name_match(tmp_project: Path) -> None:
    # Create a lib file
    (tmp_project / "lib" / "context_manager.py").write_text("# our lib")

    # Create a matching plugin file
    plugin_dir = tmp_project / ".claude" / "plugins" / "hermes-agent"
    plugin_dir.mkdir()
    (plugin_dir / ".git").mkdir()
    (plugin_dir / "context_manager.py").write_text("# plugin lib")

    e = EcosystemEvaluator(str(tmp_project))
    risks = e.check_reinvention_risk()

    assert len(risks) >= 1
    assert risks[0]["similarity"] == "name_match"
    assert "context_manager" in risks[0]["our_lib"]


# ---------------------------------------------------------------------------
# 7. format_report_readable
# ---------------------------------------------------------------------------

def test_format_report_readable(evaluator: EcosystemEvaluator) -> None:
    report = {
        "plugins": [
            {
                "plugin": "hermes",
                "path": "/tmp/hermes",
                "new_commits": 5,
                "highlights": ["abc feat: new compression"],
                "last_checked": "2026-04-11T00:00:00Z",
                "adoption_candidates": ["new compression"],
            }
        ],
        "tools": [
            {
                "name": "Archon",
                "status": "EVALUATE",
                "github_url": "https://github.com/foo/bar",
                "last_evaluated": "2026-02-01",
                "days_since_eval": 45,
                "is_stale": True,
                "recommendation": "re-evaluate",
            }
        ],
        "reinvention": [
            {
                "our_lib": "lib/context_estimator.py",
                "plugin_file": "hermes-agent/context_manager.py",
                "plugin": "hermes-agent",
                "similarity": "purpose_overlap",
            }
        ],
    }
    text = evaluator.format_report(report)
    assert "PLUGINS:" in text
    assert "EVALUATED TOOLS:" in text
    assert "REINVENTION RISK:" in text
    assert "hermes" in text
    assert "Archon" in text
    assert "===" in text


# ---------------------------------------------------------------------------
# 8. no_crash_without_plugins
# ---------------------------------------------------------------------------

def test_no_crash_without_plugins(tmp_path: Path) -> None:
    # No .claude/plugins directory at all
    e = EcosystemEvaluator(str(tmp_path))
    result = e.check_plugin_updates()
    assert result == []
    risks = e.check_reinvention_risk()
    assert risks == []


# ---------------------------------------------------------------------------
# 9. save_timestamp
# ---------------------------------------------------------------------------

def test_save_timestamp(tmp_project: Path) -> None:
    e = EcosystemEvaluator(str(tmp_project))
    ts_file = tmp_project / ".cognitive-os" / "metrics" / "ecosystem-eval-last-run"
    assert not ts_file.exists()

    e.save_check_timestamp()

    assert ts_file.exists()
    content = ts_file.read_text().strip()
    assert content.isdigit()
    assert int(content) > 0


# ---------------------------------------------------------------------------
# 10. generate_report_structure
# ---------------------------------------------------------------------------

def test_generate_report_structure(tmp_project: Path) -> None:
    e = EcosystemEvaluator(str(tmp_project))

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        report = e.generate_evaluation_report()

    assert "plugins" in report
    assert "tools" in report
    assert "reinvention" in report
    assert "generated_at" in report
    assert isinstance(report["plugins"], list)
    assert isinstance(report["tools"], list)
    assert isinstance(report["reinvention"], list)

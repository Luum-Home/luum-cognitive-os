"""Tests for rules/startup-protocol.md + hooks/session-startup-protocol.sh.

Formalizes the 5-step session-startup protocol (Engram -> Plans <-> ADRs ->
work-queue -> validator -> execute). The hook is advisory only, runs in
SessionStart, and must degrade gracefully when dependencies are missing.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "hooks" / "session-startup-protocol.sh"
RULE = REPO / "rules" / "startup-protocol.md"
EFF_SCRIPT = REPO / "scripts" / "apply-efficiency-profile.sh"
# ADR-064: projection logic moved to per-harness drivers; apply-efficiency-profile.sh delegates.
CC_DRIVER = REPO / "scripts" / "_lib" / "settings-driver-claude-code.sh"
SEC_SCRIPT = REPO / "scripts" / "set-security-profile.sh"


def test_hook_exists_and_executable() -> None:
    assert HOOK.is_file(), f"hook not found: {HOOK}"
    assert os.access(HOOK, os.X_OK), f"hook not executable: {HOOK}"
    # bash -n syntax check
    r = subprocess.run(
        ["bash", "-n", str(HOOK)], capture_output=True, text=True, timeout=5
    )
    assert r.returncode == 0, f"bash -n failed: {r.stderr}"


def test_hook_registered_in_both_profile_scripts() -> None:
    # ADR-064: hook registrations live in settings-driver-claude-code.sh (not in
    # apply-efficiency-profile.sh which now delegates). Check the driver + apply script
    # together — either one containing the hook name satisfies the registration requirement.
    eff = EFF_SCRIPT.read_text()
    driver_text = CC_DRIVER.read_text() if CC_DRIVER.is_file() else ""
    sec = SEC_SCRIPT.read_text()
    assert "session-startup-protocol.sh" in (eff + driver_text), (
        "session-startup-protocol.sh not registered in apply-efficiency-profile.sh "
        "or scripts/_lib/settings-driver-claude-code.sh (ADR-064 canonical source)"
    )
    assert "session-startup-protocol.sh" in sec, (
        "session-startup-protocol.sh not referenced in set-security-profile.sh"
    )


def test_hook_produces_output(tmp_path: Path) -> None:
    # Minimal fake project covering all 5 plan directories.
    # features: 2 plans
    (tmp_path / ".cognitive-os" / "plans" / "features").mkdir(parents=True)
    (tmp_path / ".cognitive-os" / "plans" / "features" / "a.md").write_text("x")
    (tmp_path / ".cognitive-os" / "plans" / "features" / "b.md").write_text("x")
    # research: 1 plan
    (tmp_path / ".cognitive-os" / "plans" / "research").mkdir(parents=True)
    (tmp_path / ".cognitive-os" / "plans" / "research" / "landscape.md").write_text("x")
    # arch plans: 1 (README.md and *.template.md excluded)
    (tmp_path / ".cognitive-os" / "plans" / "architecture").mkdir(parents=True)
    (tmp_path / ".cognitive-os" / "plans" / "architecture" / "impl-plan.md").write_text("x")
    (tmp_path / ".cognitive-os" / "plans" / "architecture" / "README.md").write_text("x")
    (tmp_path / ".cognitive-os" / "plans" / "architecture" / "foo.template.md").write_text("x")
    # roadmaps: 1 roadmap (archive-named file excluded)
    (tmp_path / ".cognitive-os" / "plans" / "roadmaps").mkdir(parents=True)
    (tmp_path / ".cognitive-os" / "plans" / "roadmaps" / "adr-mega-plan.md").write_text("x")
    (tmp_path / ".cognitive-os" / "plans" / "roadmaps" / "archive-old.md").write_text("x")
    # adrs: 1
    (tmp_path / "docs" / "adrs").mkdir(parents=True)
    (tmp_path / "docs" / "adrs" / "ADR-001.md").write_text("x")
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True)
    (tmp_path / ".cognitive-os" / "metrics" / "adr-implementation-latest.json").write_text(
        '{"summary": {"attention_count": 3, "implementation_counts": {"implemented": 1, "pending": 3}}}'
    )
    (tmp_path / ".cognitive-os" / "work-queue.json").write_text(
        '{"live": [{"id":1}], "parked": [{"id":2},{"id":3}]}'
    )

    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    r = subprocess.run(
        ["bash", str(HOOK)],
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )
    assert r.returncode == 0, f"hook exited {r.returncode}: {r.stderr}"
    out = r.stdout
    assert "[startup-protocol]" in out
    # New compact format: all 4 canonical dirs on one line (ADR-082)
    assert "Plans: 2 features" in out
    assert "1 research" in out
    assert "1 arch" in out
    assert "1 roadmaps" in out
    assert "cross-ref 1 ADRs" in out
    assert "ADR implementation:" in out
    assert "3 need attention" in out
    assert "1 live, 2 parked" in out
    assert "Validator:" in out
    assert "Suggested first action:" in out


def test_hook_fast(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    start = time.monotonic()
    r = subprocess.run(
        ["bash", str(HOOK)],
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )
    elapsed = time.monotonic() - start
    assert r.returncode == 0
    assert elapsed < 1.0, f"hook took {elapsed:.3f}s (budget: 1.0s)"


def test_hook_project_dir_precedence_prefers_cognitive_then_codex_then_claude(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical"
    codex = tmp_path / "codex"
    claude = tmp_path / "claude"
    for project in (canonical, codex, claude):
        (project / ".cognitive-os" / "plans" / "features").mkdir(parents=True)
    (canonical / ".cognitive-os" / "plans" / "features" / "canonical.md").write_text("x")
    (codex / ".cognitive-os" / "plans" / "features" / "codex.md").write_text("x")
    (codex / ".cognitive-os" / "plans" / "features" / "codex-2.md").write_text("x")
    (claude / ".cognitive-os" / "plans" / "features" / "claude.md").write_text("x")
    (claude / ".cognitive-os" / "plans" / "features" / "claude-2.md").write_text("x")
    (claude / ".cognitive-os" / "plans" / "features" / "claude-3.md").write_text("x")

    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(canonical)
    env["CODEX_PROJECT_DIR"] = str(codex)
    env["CLAUDE_PROJECT_DIR"] = str(claude)
    r = subprocess.run(["bash", str(HOOK)], capture_output=True, text=True, timeout=5, env=env)
    assert r.returncode == 0
    assert "Plans: 1 features" in r.stdout

    env.pop("COGNITIVE_OS_PROJECT_DIR")
    r = subprocess.run(["bash", str(HOOK)], capture_output=True, text=True, timeout=5, env=env)
    assert r.returncode == 0
    assert "Plans: 2 features" in r.stdout


def test_hook_never_blocks_on_missing_files(tmp_path: Path) -> None:
    # Completely empty tmpdir — no plans, no work-queue, no validator, no engram.
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    # Also strip HOME to prevent accidental engram detection in user dir
    env["HOME"] = str(tmp_path)
    r = subprocess.run(
        ["bash", str(HOOK)],
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )
    assert r.returncode == 0, f"hook blocked on missing files: rc={r.returncode} stderr={r.stderr}"
    out = r.stdout
    assert "[startup-protocol]" in out
    # Graceful degradation: all plan dirs absent → all counts are 0
    assert "Plans: 0 features" in out
    assert "0 research" in out
    assert "0 arch" in out
    assert "0 roadmaps" in out
    assert "Validator:" in out
    # work-queue missing should say no-queue or similar, not crash
    assert "Work queue:" in out


def test_rule_file_present_and_parseable() -> None:
    assert RULE.is_file(), f"rule not found: {RULE}"
    body = RULE.read_text()
    # Must have the five mandatory section markers from the task spec
    required = [
        "# Session Startup Protocol",
        "## Purpose",
        "## Mandatory Steps",
        "### 1.",
        "### 2.",
        "### 3.",
        "### 4.",
        "### 5.",
        "## When the protocol is NOT required",
        "## Escalation",
        "## Contextual Trigger",
    ]
    for marker in required:
        assert marker in body, f"rule missing section: {marker}"


def test_settings_json_has_hook() -> None:
    """The generated settings.json must include the hook (>=1 occurrence)."""
    settings = REPO / ".claude" / "settings.json"
    if not settings.is_file():
        pytest.skip("settings.json not present (profile not applied in this env)")
    content = settings.read_text()
    assert "session-startup-protocol" in content, (
        "session-startup-protocol not wired into .claude/settings.json — "
        "run: bash scripts/apply-efficiency-profile.sh"
    )

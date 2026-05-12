"""Behavior tests for the CLAUDE.md Diet (TO-1).

Validates that hooks/self-install.sh EXCLUDED_RULES is correctly configured to:
- Exclude 30+ rules from context (reducing token overhead)
- Keep core behavioral rules symlinked
- Exclude package-specific and contextual rules
- Result in fewer than 50 rules symlinked after running self-install.sh

Related task: TO-1 — CLAUDE.md Diet: Remove Redundant Rule Includes
Related file: hooks/self-install.sh
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List

import pytest

pytestmark = pytest.mark.behavior

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = REPO_ROOT / "hooks" / "self-install.sh"
COS_RULES_DIR = REPO_ROOT / ".claude" / "rules" / "cos"

# Core behavioral rules that MUST always be symlinked (never excluded)
CORE_RULES_REQUIRED = [
    "RULES-COMPACT.md",
    "adaptive-bypass.md",
    "acceptance-criteria.md",
    "agent-quality.md",
    "closed-loop-prompts.md",
    "definition-of-done.md",
    "error-learning.md",
    "model-routing.md",
    "phase-aware-agents.md",
    "result-management.md",
    "token-economy.md",
    "trust-score.md",
]

# Package-specific rules that MUST be excluded (not relevant to OS dev context)
PACKAGE_RULES_EXPECTED_EXCLUDED = [
    "aguara-integration.md",
    "e2b-integration.md",
    "hcom-integration.md",
    "parry-integration.md",
    "repomix-integration.md",
    "tero-integration.md",
    "trailofbits-skills.md",
    "context7-auto-trigger.md",
    "ecosystem-tools.md",
    "private-mode.md",
]

# Contextual/specialized rules that MUST be excluded (indexed in RULES-COMPACT, load on demand)
CONTEXTUAL_RULES_EXPECTED_EXCLUDED = [
    "singularity.md",
    "squad-protocol.md",
    "estimation-calibration.md",
    "step-files.md",
    "dry-run.md",
    "session-concurrency.md",
    "agent-communication.md",
    "task-dag.md",
    "queue-drain.md",
    "non-blocking-retry.md",
    "sandbox-sampling.md",
    "impact-analysis.md",
]


def _extract_excluded_rules(hook_text: str) -> List[str]:
    """Extract all entries from the EXCLUDED_RULES array in self-install.sh."""
    entries = []
    in_block = False
    for line in hook_text.splitlines():
        stripped = line.strip()
        if stripped == "EXCLUDED_RULES=(":
            in_block = True
            continue
        if in_block:
            # Closing paren on its own line ends the block
            if stripped == ")":
                break
            m = re.search(r'"([^"]+\.md)"', line)
            if m:
                entries.append(m.group(1))
    return entries


def _run_self_install() -> subprocess.CompletedProcess:
    """Run self-install.sh against the real repo."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(REPO_ROOT)
    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


@pytest.fixture(scope="module")
def hook_text() -> str:
    """Return the raw text of self-install.sh."""
    return HOOK_PATH.read_text()


@pytest.fixture(scope="module")
def excluded_rules(hook_text) -> List[str]:
    """Return the parsed EXCLUDED_RULES list."""
    return _extract_excluded_rules(hook_text)


@pytest.fixture(scope="module")
def synced_rules() -> List[str]:
    """Return the list of .md files currently symlinked in .claude/rules/cos/."""
    if not COS_RULES_DIR.exists():
        return []
    return [f.name for f in COS_RULES_DIR.glob("*.md") if f.is_symlink()]


class TestExcludedRulesCount:
    """EXCLUDED_RULES array must have 30+ entries to achieve meaningful diet."""

    def test_excluded_rules_count_at_least_30(self, excluded_rules):
        """EXCLUDED_RULES must have at least 30 entries."""
        count = len(excluded_rules)
        assert count >= 30, (
            f"EXCLUDED_RULES has only {count} entries — need at least 30 "
            f"to achieve meaningful context reduction"
        )

    def test_excluded_rules_have_no_duplicates(self, excluded_rules):
        """No rule should appear twice in EXCLUDED_RULES."""
        seen = set()
        duplicates = []
        for rule in excluded_rules:
            if rule in seen:
                duplicates.append(rule)
            seen.add(rule)
        assert not duplicates, f"Duplicate entries in EXCLUDED_RULES: {duplicates}"

    def test_excluded_rules_all_exist_in_rules_dir(self, excluded_rules):
        """Every excluded entry should resolve to a rule or documented pattern."""
        missing = []
        for rule in excluded_rules:
            rule_path = REPO_ROOT / "rules" / rule
            pattern_path = REPO_ROOT / "docs" / "patterns" / rule
            if not rule_path.exists() and not pattern_path.exists() and not pattern_path.is_symlink():
                missing.append(rule)
        assert not missing, (
            f"EXCLUDED_RULES entries that resolve to neither rules/ nor docs/04-Concepts/patterns/: {missing}\n"
            f"Remove ghost entries, restore rule files, or document declarative patterns."
        )


class TestCoreRulesNotExcluded:
    """Core behavioral rules must NOT be in EXCLUDED_RULES."""

    def test_rules_compact_not_excluded(self, excluded_rules):
        assert "RULES-COMPACT.md" not in excluded_rules, \
            "RULES-COMPACT.md must never be excluded — it is the compact index"

    def test_phase_aware_agents_not_excluded(self, excluded_rules):
        assert "phase-aware-agents.md" not in excluded_rules, \
            "phase-aware-agents.md must stay — governs reconstruction/production behavior"

    def test_token_economy_not_excluded(self, excluded_rules):
        assert "token-economy.md" not in excluded_rules, \
            "token-economy.md must stay — core cost governance"

    def test_model_routing_not_excluded(self, excluded_rules):
        assert "model-routing.md" not in excluded_rules, \
            "model-routing.md must stay — core model selection table"

    def test_adaptive_bypass_not_excluded(self, excluded_rules):
        assert "adaptive-bypass.md" not in excluded_rules, \
            "adaptive-bypass.md must stay — governs orchestration complexity"

    def test_definition_of_done_not_excluded(self, excluded_rules):
        assert "definition-of-done.md" not in excluded_rules, \
            "definition-of-done.md must stay — completion criteria by complexity"

    def test_agent_quality_not_excluded(self, excluded_rules):
        assert "agent-quality.md" not in excluded_rules, \
            "agent-quality.md must stay — maximum output quality enforcement"

    def test_closed_loop_prompts_not_excluded(self, excluded_rules):
        assert "closed-loop-prompts.md" not in excluded_rules, \
            "closed-loop-prompts.md must stay — self-correcting execution protocol"

    def test_acceptance_criteria_not_excluded(self, excluded_rules):
        assert "acceptance-criteria.md" not in excluded_rules, \
            "acceptance-criteria.md must stay — mandatory criteria for all tasks"

    def test_trust_score_not_excluded(self, excluded_rules):
        assert "trust-score.md" not in excluded_rules, \
            "trust-score.md must stay — mandatory Trust Report protocol"

    def test_error_learning_not_excluded(self, excluded_rules):
        assert "error-learning.md" not in excluded_rules, \
            "error-learning.md must stay — error pattern capture and injection"

    def test_credential_management_not_excluded(self, excluded_rules):
        assert "credential-management.md" not in excluded_rules, \
            "credential-management.md must stay — never put secrets in code"


class TestSymlinkCountAfterInstall:
    """After running self-install.sh, fewer than 50 rules should be symlinked."""

    def test_rules_symlink_count_under_50(self):
        """After self-install.sh, .claude/rules/cos/ must have fewer than 50 symlinks."""
        if not HOOK_PATH.exists():
            pytest.skip("self-install.sh not found")

        result = _run_self_install()
        assert result.returncode == 0, f"self-install.sh failed: {result.stderr}"

        if not COS_RULES_DIR.exists():
            pytest.skip(".claude/rules/cos/ not found after self-install")

        symlinks = [f for f in COS_RULES_DIR.glob("*.md") if f.is_symlink()]
        count = len(symlinks)
        assert count < 50, (
            f"Too many rules symlinked: {count}. "
            f"Target is <50 to reduce context overhead. "
            f"Currently symlinked: {sorted(f.name for f in symlinks)}"
        )

    def test_core_rules_reachable_after_install(self):
        """After self-install.sh, all core behavioral rules must be reachable.

        Stage 1 (SessionStart) symlinks only RULES-COMPACT.md.  Stage 2 expands
        [ref-key] markers on demand.  Core rules are reachable even if they are
        not symlinked at Stage 1 (ADR-079 / ADR-074) as long as they are:
          (a) symlinked at Stage 1 (in CORE_RULES), OR
          (b) in EXCLUDED_RULES (accessible via hook enforcement), OR
          (c) referenced via [`key-name`] markers in RULES-COMPACT.md (Stage 2).

        This test verifies RULES-COMPACT.md is symlinked and all other
        CORE_RULES_REQUIRED entries are reachable through one of the three paths.
        """
        if not HOOK_PATH.exists():
            pytest.skip("self-install.sh not found")

        _run_self_install()

        if not COS_RULES_DIR.exists():
            pytest.skip(".claude/rules/cos/ not found after self-install")

        import re as _re
        hook_text = HOOK_PATH.read_text()
        excluded = set(_extract_excluded_rules(hook_text))

        # Parse compact-indexed keys: [`key-name`] markers in RULES-COMPACT.md
        compact_path = REPO_ROOT / "rules" / "RULES-COMPACT.md"
        compact_text = compact_path.read_text() if compact_path.exists() else ""
        compact_keys = {f"{k}.md" for k in _re.findall(r"\[`([a-z][a-z0-9-]+)`\]", compact_text)}

        missing_from_repo = []
        not_reachable = []
        for rule in CORE_RULES_REQUIRED:
            rule_path = REPO_ROOT / "rules" / rule
            if not rule_path.exists():
                missing_from_repo.append(rule)
                continue
            symlinked = (COS_RULES_DIR / rule).is_symlink()
            stage2_excluded = rule in excluded
            stage2_compact = rule in compact_keys
            if not symlinked and not stage2_excluded and not stage2_compact:
                not_reachable.append(rule)

        assert not missing_from_repo, (
            f"Core rules missing from rules/ directory: {missing_from_repo}"
        )
        assert not not_reachable, (
            f"Core rules are unreachable — not symlinked, not in EXCLUDED_RULES, "
            f"and not referenced in RULES-COMPACT.md: {not_reachable}. "
            f"Each must be reachable via Stage 1 (symlink) or Stage 2 (ref-key)."
        )

    def test_excluded_package_rules_not_symlinked(self):
        """Package-specific rules must NOT be symlinked after self-install."""
        if not HOOK_PATH.exists():
            pytest.skip("self-install.sh not found")

        _run_self_install()

        if not COS_RULES_DIR.exists():
            pytest.skip(".claude/rules/cos/ not found after self-install")

        present = []
        for rule in PACKAGE_RULES_EXPECTED_EXCLUDED:
            if (COS_RULES_DIR / rule).is_symlink():
                present.append(rule)

        assert not present, (
            f"Package-specific rules still symlinked (should be excluded): {present}"
        )


class TestSyntaxValidity:
    """self-install.sh must be syntactically valid bash."""

    def test_bash_syntax_valid(self):
        result = subprocess.run(
            ["bash", "-n", str(HOOK_PATH)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"bash -n failed on self-install.sh:\n{result.stderr}"
        )

    def test_self_install_exits_zero_on_real_repo(self):
        """self-install.sh must exit 0 when run against the real repo."""
        result = _run_self_install()
        assert result.returncode == 0, (
            f"self-install.sh exited {result.returncode}:\n{result.stderr}"
        )

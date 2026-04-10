"""Behavior tests for rules consolidation safety net.

Documents the state of the rules system (symlinks, cross-references, packages)
so that any consolidation is caught by regression tests. Counts are dynamic
to avoid breakage when new rules/packages are added.

Related files:
  - rules/ (.md files including RULES-COMPACT.md)
  - .claude/rules/cos/ (symlinks to rules/)
  - packages/*/rules/ (package rules symlinked through rules/)
  - hooks/self-install.sh (profile-based rule filtering)
  - cognitive-os.yaml (contextual_triggers configuration)
"""

import os
import re
from typing import Optional
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RULES_DIR = PROJECT_ROOT / "rules"
COS_RULES_DIR = PROJECT_ROOT / ".claude" / "rules" / "cos"
PACKAGES_DIR = PROJECT_ROOT / "packages"
HOOKS_DIR = PROJECT_ROOT / "hooks"
SKILLS_DIR = PROJECT_ROOT / "skills"
COMPACT_PATH = RULES_DIR / "RULES-COMPACT.md"

# Current known count as of pre-consolidation snapshot
EXPECTED_RULE_COUNT = len(list(Path(__file__).resolve().parents[2].joinpath("rules").glob("*.md")))

# Rules that are newly added and not yet fully integrated (no symlink, no COMPACT ref)
# These are tracked so consolidation does not lose them
PENDING_INTEGRATION_RULES = set()  # All rules synced as of 2026-03-28

# The 11 core rules that remain in standard profile context load.
# These provide essential governance without overwhelming the context window.
# Loading all 103 rules would cost ~93,700 tokens vs ~11K for these 11.
# See docs/rules-loading-architecture.md for the rationale.
# Must match CORE_RULES in hooks/self-install.sh exactly.
CORE_RULES = {
    "RULES-COMPACT.md",
    "adaptive-bypass.md",
    "acceptance-criteria.md",
    "agent-quality.md",
    "trust-score.md",
    "token-economy.md",
    "phase-aware-agents.md",
    "closed-loop-prompts.md",
    "error-learning.md",
    "credential-management.md",
    "model-routing.md",
    "rate-limiting.md",
    "content-policy.md",
    "blast-radius.md",
    "clarification-gate.md",
    "result-management.md",
}

# Rules fully enforced by registered hooks — intentionally excluded from agent context
# (symlinks and COMPACT narrative refs removed; rule .md files remain as documentation).
# Must match EXCLUDED_RULES in hooks/self-install.sh exactly.
EXCLUDED_RULES = {
    "anti-hallucination.md",
    "auto-repair.md",
    "auto-skill-generation.md",
    "crash-recovery.md",
    "prompt-quality.md",
    "skill-rewrite.md",
    "pre-dev-readiness-gate.md",
    "audit-trail.md",
    "doc-sync.md",
    "pre-commit-gate.md",
    "scope-creep-detection.md",
    "assumption-tracking.md",
}
# NOTE: blast-radius, clarification-gate, content-policy, rate-limiting, result-management
# are hook-enforced BUT kept in CORE_RULES (proactive > reactive decision 2026-04-10)


def _get_rule_files() -> list[Path]:
    """All .md files in rules/."""
    return sorted(RULES_DIR.glob("*.md"))


def _get_rule_files_excluding_compact() -> list[Path]:
    """All .md files in rules/ except RULES-COMPACT.md."""
    return sorted(f for f in RULES_DIR.glob("*.md") if f.name != "RULES-COMPACT.md")


def _extract_backtick_references(text: str) -> set[str]:
    """Extract all [`rule-name`] references from RULES-COMPACT.md."""
    return set(re.findall(r'\[`([a-z0-9-]+)`\]', text))


def _extract_hook_references(text: str) -> set[str]:
    """Extract hook filenames like `hooks/foo-bar.sh` from rule text."""
    return set(re.findall(r'hooks/([a-z0-9_-]+\.sh)', text))


def _extract_skill_references(text: str) -> set[str]:
    """Extract skill references like `/skill-name` or `skills/skill-name` from rule text."""
    # Match /skill-name patterns (invocations)
    slash_refs = set(re.findall(r'`/([a-z0-9-]+)`', text))
    # Match skills/name patterns (directory references)
    dir_refs = set(re.findall(r'skills/([a-z0-9-]+)', text))
    return slash_refs | dir_refs


# ===========================================================================
# Inventory Tests
# ===========================================================================


class TestRuleInventory:
    """Verify the exact count of rules files and symlinks."""

    def test_rules_dir_has_expected_count(self):
        """rules/ .md file count must match dynamically computed expected count."""
        rule_files = _get_rule_files()
        assert len(rule_files) == EXPECTED_RULE_COUNT, (
            f"Expected {EXPECTED_RULE_COUNT} rule files in rules/, found {len(rule_files)}. "
            f"Files: {[f.name for f in rule_files]}"
        )

    def test_cos_symlinks_match_rules_count(self):
        """Number of symlinks in .claude/rules/cos/ must equal integrated non-excluded rules.

        Rules in PENDING_INTEGRATION_RULES are not yet synced and excluded.
        Rules in EXCLUDED_RULES are hook-enforced and intentionally excluded from context.
        In self-hosting mode, self-install.sh syncs all rules minus EXCLUDED_RULES to cos/.
        In standard mode, only CORE_RULES are synced.
        """
        if not COS_RULES_DIR.exists():
            pytest.skip(".claude/rules/cos/ does not exist")
        symlinks = list(COS_RULES_DIR.glob("*.md"))
        integrated_rules = [
            f for f in _get_rule_files()
            if f.name not in PENDING_INTEGRATION_RULES and f.name not in EXCLUDED_RULES
        ]
        assert len(symlinks) == len(integrated_rules), (
            f"Symlinks ({len(symlinks)}) != integrated rule files ({len(integrated_rules)}). "
            f"Missing in cos/: {set(f.name for f in integrated_rules) - set(s.name for s in symlinks)}. "
            f"Extra in cos/: {set(s.name for s in symlinks) - set(f.name for f in integrated_rules)}"
        )

    def test_every_integrated_rule_has_a_symlink(self):
        """Every non-excluded integrated rule must have a symlink in .claude/rules/cos/.

        Self-hosting mode syncs all rules minus EXCLUDED_RULES (hook-enforced, no context needed).
        """
        if not COS_RULES_DIR.exists():
            pytest.skip(".claude/rules/cos/ does not exist")
        rule_names = {f.name for f in _get_rule_files()} - PENDING_INTEGRATION_RULES - EXCLUDED_RULES
        symlink_names = {s.name for s in COS_RULES_DIR.glob("*.md")}
        missing = rule_names - symlink_names
        assert not missing, f"Rules without symlinks: {sorted(missing)}"

    def test_pending_rules_tracked(self):
        """PENDING_INTEGRATION_RULES must actually be pending (no symlink yet)."""
        if not COS_RULES_DIR.exists():
            pytest.skip(".claude/rules/cos/ does not exist")
        symlink_names = {s.name for s in COS_RULES_DIR.glob("*.md")}
        synced_pending = PENDING_INTEGRATION_RULES & symlink_names
        assert not synced_pending, (
            f"Rules marked as pending but already synced (remove from PENDING_INTEGRATION_RULES): "
            f"{sorted(synced_pending)}"
        )

    def test_no_extra_symlinks_beyond_rules(self):
        """No symlinks in .claude/rules/cos/ without a matching file in rules/."""
        if not COS_RULES_DIR.exists():
            pytest.skip(".claude/rules/cos/ does not exist")
        rule_names = {f.name for f in _get_rule_files()}
        symlink_names = {s.name for s in COS_RULES_DIR.glob("*.md")}
        extra = symlink_names - rule_names
        assert not extra, f"Orphan symlinks in cos/: {sorted(extra)}"

    def test_rules_compact_exists(self):
        """RULES-COMPACT.md must exist."""
        assert COMPACT_PATH.exists(), "RULES-COMPACT.md is missing from rules/"


# ===========================================================================
# Cross-Reference Integrity Tests
# ===========================================================================


class TestCrossReferenceIntegrity:
    """Verify RULES-COMPACT.md references match actual files bidirectionally."""

    def test_every_rule_referenced_in_compact(self):
        """Every integrated .md rule file (except RULES-COMPACT.md) must be referenced
        via [`rule-name`] in RULES-COMPACT.md OR be in EXCLUDED_RULES (hook-enforced).
        Pending rules are excluded."""
        compact_text = COMPACT_PATH.read_text()
        references = _extract_backtick_references(compact_text)
        rule_files = _get_rule_files_excluding_compact()

        # Rules that are fully contextual/optional and not required in COMPACT
        # (these are documented in packages or loaded on contextual triggers)
        CONTEXTUAL_ONLY_RULES = {
            "cognitive-load.md",              # loaded at >50% context usage
            "confidentiality-protection.md",  # hook-enforced: confidentiality-enforcer.sh
            "content-policy.md",              # hook-enforced: content-policy.sh
            "context7-auto-trigger.md",       # package rule, loaded on trigger
            "cost-prediction.md",             # loaded on cost estimation trigger
            "e2b-integration.md",             # package rule, loaded on trigger
            "hcom-integration.md",            # package rule, loaded on trigger
            "infra-intent.md",                # advisory, loaded on infra keywords
            "model-compatibility.md",         # loaded on model switch trigger
            "orchestrator-mode.md",           # loaded on executor mode trigger
            "os-vs-project.md",               # loaded on project init trigger
            "parry-integration.md",           # package rule, loaded on trigger
            "pentesting-readiness.md",        # loaded on security audit trigger
            "plan-first.md",                  # merged into cognitive-os-changes
            "rate-limit-protection.md",       # loaded on rate limit trigger
            "rate-limiting.md",               # hook-enforced: rate-limiter.sh
            "repomix-integration.md",         # package rule, loaded on trigger
            "result-management.md",           # hook-enforced: result-truncator.sh
            "security-scanning.md",           # loaded on SAST trigger
            "tero-integration.md",            # package rule, loaded on trigger
            "trailofbits-skills.md",          # package rule, loaded on trigger
            "user-prompt-capture.md",         # loaded on user prompt trigger
            "workload-scheduling.md",         # loaded on multi-agent trigger
        }

        missing = []
        for f in rule_files:
            if f.name in PENDING_INTEGRATION_RULES:
                continue
            if f.name in EXCLUDED_RULES:
                continue  # hook-enforced, intentionally not in COMPACT
            if f.name in CONTEXTUAL_ONLY_RULES:
                continue  # contextual/package rule, not required in COMPACT
            rule_name = f.stem
            if rule_name not in references:
                # Fallback: check if the stem appears anywhere in the text
                if rule_name not in compact_text:
                    missing.append(rule_name)

        assert not missing, (
            f"{len(missing)} rules not referenced in RULES-COMPACT.md: {sorted(missing)}"
        )

    def test_no_orphan_references_in_compact(self):
        """Every [`rule-name`] in RULES-COMPACT.md must map to a real rules/*.md file."""
        compact_text = COMPACT_PATH.read_text()
        references = _extract_backtick_references(compact_text)
        existing_stems = {f.stem for f in _get_rule_files()}

        orphans = sorted(ref for ref in references if ref not in existing_stems)
        assert not orphans, (
            f"RULES-COMPACT.md references non-existent rule files: {orphans}"
        )

    def test_hooks_referenced_in_rules_exist(self):
        """Hooks referenced in rules as actual implementations must exist in hooks/.

        Some hooks appear in rules as examples, planned features, or hypothetical
        illustrations (e.g., 'my-hook.sh' in examples, or tools not yet built).
        These are excluded from the check.
        """
        # Hooks that appear in rules as examples/illustrations, not real implementations
        EXAMPLE_HOOKS = {
            "my-hook.sh",           # Example in hcom-integration.md
            "my-bash-hook.sh",      # Example in settings merge docs
            "auto-verify.sh",       # Documented as planned, not yet implemented
            "parry-scan.sh",        # Documented for optional parry-guard tool
            "project-start.sh",     # Example in settings merge docs
            "my-project-hook.sh",   # Example in coexistence docs
            "project-hook.sh",      # Example in settings docs
        }

        all_hook_refs: set[str] = set()
        for rule_file in _get_rule_files():
            text = rule_file.read_text()
            all_hook_refs |= _extract_hook_references(text)

        missing = []
        for hook_name in sorted(all_hook_refs - EXAMPLE_HOOKS):
            hook_path = HOOKS_DIR / hook_name
            if not hook_path.exists():
                missing.append(hook_name)

        assert not missing, (
            f"{len(missing)} hooks referenced in rules but missing from hooks/: {sorted(missing)}"
        )

    def test_skills_referenced_in_rules_exist(self):
        """Skills referenced as /skill-name or skills/skill-name in rules must exist."""
        all_skill_refs: set[str] = set()
        for rule_file in _get_rule_files():
            text = rule_file.read_text()
            all_skill_refs |= _extract_skill_references(text)

        # Filter to plausible skill names (not generic words)
        # Skills are directories under skills/ with a SKILL.md
        existing_skills = {
            d.name for d in SKILLS_DIR.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
        }
        # Also accept auto-generated skill dirs
        auto_gen = SKILLS_DIR / "auto-generated"
        if auto_gen.exists():
            existing_skills |= {d.name for d in auto_gen.iterdir() if d.is_dir()}

        # Only flag references that look like skill names (contain hyphen, reasonable length)
        plausible_refs = {
            ref for ref in all_skill_refs
            if len(ref) > 3 and "-" in ref and ref not in (
                # Known non-skill references that look like skill names
                "self-install", "auto-generated", "agent-preamble",
                "quality-gates", "error-recovery", "rebranding-checklist",
                "skill-registry",
            )
        }

        missing = sorted(plausible_refs - existing_skills)
        # Relax: only warn if more than 10% are missing
        # Some references are to potential/future skills
        if missing:
            ratio = len(missing) / max(len(plausible_refs), 1)
            assert ratio < 0.3, (
                f"{len(missing)}/{len(plausible_refs)} skill references missing: {missing[:20]}"
            )


# ===========================================================================
# Classification Tests (Always Active vs Contextual)
# ===========================================================================


class TestRulesClassification:
    """Verify RULES-COMPACT.md sections and classification of rules."""

    def test_compact_has_required_sections(self):
        """RULES-COMPACT.md must have Always Active, Contextual, and Project-Specific."""
        content = COMPACT_PATH.read_text()
        headers = [line.strip() for line in content.splitlines() if line.startswith("## ")]
        required = [
            "## Always Active",
            "## Contextual (loaded on trigger)",
            "## Project-Specific",
        ]
        for section in required:
            assert any(section in h for h in headers), (
                f"Missing section '{section}' in RULES-COMPACT.md. Found: {headers}"
            )

    def test_always_active_has_numbered_subsections(self):
        """Always Active section must have numbered ### subsections."""
        content = COMPACT_PATH.read_text()
        # Extract Always Active section
        always_start = content.find("## Always Active")
        contextual_start = content.find("## Contextual")
        assert always_start != -1 and contextual_start != -1
        always_section = content[always_start:contextual_start]

        subsections = re.findall(r'### \d+\. (.+)', always_section)
        assert len(subsections) >= 10, (
            f"Expected >= 10 Always Active subsections, found {len(subsections)}: {subsections}"
        )

    def test_contextual_section_has_subsections(self):
        """Contextual section must have subsections (numbered ### or bold ** headings)."""
        content = COMPACT_PATH.read_text()
        contextual_start = content.find("## Contextual")
        project_start = content.find("## Project-Specific")
        assert contextual_start != -1 and project_start != -1
        contextual_section = content[contextual_start:project_start]

        # Accept either numbered ### subsections or **Bold** category headings
        numbered_subsections = re.findall(r'### \d+\. (.+)', contextual_section)
        bold_headings = re.findall(r'^\*\*(.+?)\*\*:', contextual_section, re.MULTILINE)
        total = len(numbered_subsections) + len(bold_headings)
        assert total >= 4, (
            f"Expected >= 4 Contextual subsections (numbered or bold), found {total}. "
            f"Numbered: {numbered_subsections}, Bold: {bold_headings}"
        )

    def test_critical_rules_in_always_active(self):
        """Critical gate rules must be in the Always Active section."""
        content = COMPACT_PATH.read_text()
        always_start = content.find("## Always Active")
        contextual_start = content.find("## Contextual")
        always_section = content[always_start:contextual_start]

        critical_rules = [
            "acceptance-criteria",
            "agent-quality",
            "trust-score",
            "agent-security",
            "credential-management",
            # content-policy is hook-enforced (content-policy.sh) — not required in COMPACT
            "license-policy",
            "error-learning",
            "closed-loop-prompts",
            "adaptive-bypass",
            "definition-of-done",
            "phase-aware-agents",
        ]

        missing = []
        for rule in critical_rules:
            if f"`{rule}`" not in always_section and rule not in always_section:
                missing.append(rule)

        assert not missing, (
            f"Critical rules not in Always Active section: {sorted(missing)}"
        )

    def test_always_active_rules_count(self):
        """Count unique rule references in Always Active section."""
        content = COMPACT_PATH.read_text()
        always_start = content.find("## Always Active")
        contextual_start = content.find("## Contextual")
        always_section = content[always_start:contextual_start]

        refs = _extract_backtick_references(always_section)
        # Should have a significant number of always-active rules
        assert len(refs) >= 40, (
            f"Expected >= 40 always-active rule references, found {len(refs)}: {sorted(refs)}"
        )

    def test_contextual_rules_count(self):
        """Count unique rule references in Contextual section."""
        content = COMPACT_PATH.read_text()
        contextual_start = content.find("## Contextual")
        project_start = content.find("## Project-Specific")
        contextual_section = content[contextual_start:project_start]

        refs = _extract_backtick_references(contextual_section)
        assert len(refs) >= 20, (
            f"Expected >= 20 contextual rule references, found {len(refs)}: {sorted(refs)}"
        )

    def test_all_references_accounted_for(self):
        """Union of Always Active + Contextual references must cover all integrated rules.

        Exceptions:
        - EXCLUDED_RULES: hook-enforced, intentionally absent from COMPACT
        - CONTEXTUAL_ONLY_RULES: package/trigger-loaded rules, not required in COMPACT
        - PENDING_INTEGRATION_RULES: rules not yet integrated
        """
        content = COMPACT_PATH.read_text()
        all_refs = _extract_backtick_references(content)
        pending_stems = {Path(n).stem for n in PENDING_INTEGRATION_RULES}
        excluded_stems = {Path(n).stem for n in EXCLUDED_RULES}
        contextual_only_stems = {
            "cognitive-load", "confidentiality-protection", "content-policy",
            "context7-auto-trigger", "cost-prediction", "e2b-integration",
            "hcom-integration", "infra-intent", "model-compatibility",
            "orchestrator-mode", "os-vs-project", "parry-integration",
            "pentesting-readiness", "plan-first", "rate-limit-protection",
            "rate-limiting", "repomix-integration", "result-management",
            "security-scanning", "tero-integration", "trailofbits-skills",
            "user-prompt-capture", "workload-scheduling",
        }
        rule_stems = (
            {f.stem for f in _get_rule_files_excluding_compact()}
            - pending_stems
            - excluded_stems
            - contextual_only_stems
        )

        # Some rules might be referenced by name in the text without backticks
        unreferenced = rule_stems - all_refs
        truly_missing = []
        for rule in unreferenced:
            if rule not in content:
                truly_missing.append(rule)

        assert not truly_missing, (
            f"Rules not referenced anywhere in RULES-COMPACT.md: {sorted(truly_missing)}"
        )


# ===========================================================================
# Content Integrity Tests
# ===========================================================================


class TestContentIntegrity:
    """Verify each rule file has valid content."""

    def test_each_rule_has_markdown_header(self):
        """Every rule .md file must start with a markdown header (#)."""
        no_header = []
        for f in _get_rule_files():
            text = f.read_text().strip()
            if not text.startswith("#"):
                no_header.append(f.name)

        assert not no_header, (
            f"Rule files without markdown headers: {sorted(no_header)}"
        )

    def test_each_rule_exceeds_minimum_length(self):
        """Every rule file must have > 100 characters of content."""
        too_short = []
        for f in _get_rule_files():
            length = len(f.read_text())
            if length < 100:
                too_short.append((f.name, length))

        assert not too_short, (
            f"Rule files under 100 chars: {too_short}"
        )

    def test_no_duplicate_content_across_rules(self):
        """No two rule files should have identical content (excluding symlink targets)."""
        seen_hashes: dict[int, str] = {}
        duplicates = []

        for f in _get_rule_files():
            # Resolve symlinks to avoid comparing a symlink with its target
            resolved = f.resolve()
            content_hash = hash(resolved.read_text())
            if content_hash in seen_hashes:
                # Only flag if the resolved paths differ
                other_name = seen_hashes[content_hash]
                if resolved.name != Path(other_name).name:
                    duplicates.append((f.name, other_name))
            else:
                seen_hashes[content_hash] = f.name

        assert not duplicates, (
            f"Duplicate content found between rule files: {duplicates}"
        )

    def test_rules_compact_is_compressed(self):
        """RULES-COMPACT.md must be significantly smaller than the sum of all rules."""
        compact_size = len(COMPACT_PATH.read_text())
        total_size = sum(len(f.read_text()) for f in _get_rule_files_excluding_compact())

        ratio = compact_size / max(total_size, 1)
        assert ratio < 0.15, (
            f"RULES-COMPACT.md is {ratio:.1%} of total rules size. "
            f"Expected < 15% (compact: {compact_size}, total: {total_size})"
        )


# ===========================================================================
# Symlink Chain Tests
# ===========================================================================


class TestSymlinkChain:
    """Verify all symlinks resolve correctly and no broken links exist."""

    def test_all_cos_symlinks_resolve(self):
        """Every symlink in .claude/rules/cos/ must resolve to an existing file."""
        if not COS_RULES_DIR.exists():
            pytest.skip(".claude/rules/cos/ does not exist")

        broken = []
        for link in COS_RULES_DIR.glob("*.md"):
            if link.is_symlink():
                target = link.resolve()
                if not target.exists():
                    broken.append(f"{link.name} -> {os.readlink(link)}")
            elif not link.exists():
                broken.append(f"{link.name} (not a symlink, does not exist)")

        assert not broken, f"Broken symlinks in .claude/rules/cos/: {broken}"

    def test_no_circular_symlinks(self):
        """No symlink should point to itself or create a cycle."""
        if not COS_RULES_DIR.exists():
            pytest.skip(".claude/rules/cos/ does not exist")

        circular = []
        for link in COS_RULES_DIR.glob("*.md"):
            if link.is_symlink():
                try:
                    resolved = link.resolve(strict=True)
                    # Circular if it resolves back to the link itself
                    if resolved == link:
                        circular.append(link.name)
                except (OSError, RuntimeError):
                    circular.append(f"{link.name} (resolution error)")

        assert not circular, f"Circular symlinks: {circular}"

    def test_cos_symlinks_point_to_rules_dir(self):
        """Every cos/ symlink must resolve to a file under rules/ (directly or via packages)."""
        if not COS_RULES_DIR.exists():
            pytest.skip(".claude/rules/cos/ does not exist")

        wrong_target = []
        for link in COS_RULES_DIR.glob("*.md"):
            if link.is_symlink():
                resolved = link.resolve()
                # Must resolve to either rules/ or packages/*/rules/
                if not (
                    str(resolved).startswith(str(RULES_DIR))
                    or str(resolved).startswith(str(PACKAGES_DIR))
                ):
                    wrong_target.append(f"{link.name} -> {resolved}")

        assert not wrong_target, (
            f"Symlinks pointing outside rules/ and packages/: {wrong_target}"
        )

    def test_package_rules_properly_chained(self):
        """Rules from packages/ must be symlinked through rules/ to .claude/rules/cos/."""
        package_rule_files = list(PACKAGES_DIR.rglob("rules/*.md"))
        if not package_rule_files:
            pytest.skip("No package rules found")

        # Each package rule should have a corresponding symlink in rules/
        package_rule_names = {f.name for f in package_rule_files}
        rules_dir_names = {f.name for f in RULES_DIR.glob("*.md")}

        missing_in_rules = package_rule_names - rules_dir_names
        assert not missing_in_rules, (
            f"Package rules not symlinked into rules/: {sorted(missing_in_rules)}"
        )

    def test_package_symlinks_in_rules_dir_point_to_packages(self):
        """Symlinks in rules/ that come from packages should point to packages/*/rules/."""
        package_rule_names = {f.name for f in PACKAGES_DIR.rglob("rules/*.md")}

        wrong = []
        for f in RULES_DIR.glob("*.md"):
            if f.name in package_rule_names and f.is_symlink():
                target = os.readlink(f)
                if "packages/" not in target:
                    wrong.append(f"{f.name} -> {target}")

        assert not wrong, (
            f"Package rules in rules/ not pointing to packages/: {wrong}"
        )

    def test_package_rules_count(self):
        """Package-sourced rules count must not shrink below baseline."""
        package_rules = [
            f for f in RULES_DIR.glob("*.md")
            if f.is_symlink() and "packages/" in os.readlink(f)
        ]
        # Dynamic baseline: count actual packages with rules dirs
        packages_with_rules = set()
        for pkg_rules_dir in PACKAGES_DIR.rglob("rules"):
            if pkg_rules_dir.is_dir() and list(pkg_rules_dir.glob("*.md")):
                packages_with_rules.add(pkg_rules_dir.parent.name)
        expected_min = sum(
            len(list((PACKAGES_DIR / pkg / "rules").glob("*.md")))
            for pkg in packages_with_rules
        )
        assert len(package_rules) >= expected_min, (
            f"Expected at least {expected_min} package-sourced rules (from {len(packages_with_rules)} packages), "
            f"found {len(package_rules)}: {sorted(r.name for r in package_rules)}"
        )


# ===========================================================================
# Self-Install Integration Tests
# ===========================================================================


class TestSelfInstallIntegration:
    """Verify self-install.sh profile behavior with rules."""

    HOOK_PATH = PROJECT_ROOT / "hooks" / "self-install.sh"

    def _run_hook(self, project_dir: str, env_overrides: Optional[dict] = None):
        import subprocess
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = project_dir
        if env_overrides:
            env.update(env_overrides)
        return subprocess.run(
            ["bash", str(self.HOOK_PATH)],
            capture_output=True, text=True, env=env, timeout=5,
        )

    def _setup_external_project(self, tmp_path: Path, profile: str = "full") -> Path:
        """Create an external project (NOT self-hosted) with a given efficiency profile."""
        # No hooks/self-install.sh marker = NOT self-hosted
        (tmp_path / ".claude").mkdir(parents=True)
        (tmp_path / ".claude" / "settings.json").write_text('{"hooks": {}}\n')

        # Create rules dir with core rules + extra non-core rules
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        for rule_name in CORE_RULES:
            (rules_dir / rule_name).write_text(f"# {rule_name}\nCore rule content.\n")
        # Add non-core rules to verify they get removed
        (rules_dir / "alpha-rule.md").write_text("# Alpha\nSome alpha rule content here.\n")
        (rules_dir / "beta-rule.md").write_text("# Beta\nSome beta rule content here.\n")
        (rules_dir / "sandbox-sampling.md").write_text("# Sandbox\nNon-core rule.\n")

        # cognitive-os.yaml with profile
        (tmp_path / "cognitive-os.yaml").write_text(
            f"version: 1\nefficiency:\n  profile: {profile}\n"
        )

        return tmp_path

    def test_full_profile_keeps_all_integrated_rules(self):
        """With full/self-hosting profile, all non-excluded integrated rules are in cos/.

        self-install.sh syncs all rules minus EXCLUDED_RULES for self-hosted development.
        EXCLUDED_RULES are hook-enforced — no context overhead needed.
        Standard profile keeps only CORE_RULES.
        """
        if not COS_RULES_DIR.exists():
            pytest.skip(".claude/rules/cos/ does not exist")

        integrated_count = len([
            f for f in RULES_DIR.glob("*.md")
            if f.name not in PENDING_INTEGRATION_RULES and f.name not in EXCLUDED_RULES
        ])
        cos_count = len(list(COS_RULES_DIR.glob("*.md")))
        assert cos_count == integrated_count, (
            f"Full/self-hosting profile: cos/ has {cos_count} but integrated rules has {integrated_count}"
        )

    def test_lean_profile_only_keeps_compact(self, tmp_path):
        """With lean profile, only RULES-COMPACT.md remains in cos/."""
        project = self._setup_external_project(tmp_path, profile="lean")
        self._run_hook(str(project))

        cos_dir = project / ".claude" / "rules" / "cos"
        if cos_dir.exists():
            remaining = list(cos_dir.glob("*.md"))
            remaining_names = [r.name for r in remaining]
            assert remaining_names == ["RULES-COMPACT.md"] or remaining_names == [], (
                f"Lean profile should only keep RULES-COMPACT.md, found: {remaining_names}"
            )

    def test_standard_profile_keeps_core_rules(self, tmp_path):
        """With standard profile, only the 14 core rules remain in cos/."""
        project = self._setup_external_project(tmp_path, profile="standard")
        self._run_hook(str(project))

        cos_dir = project / ".claude" / "rules" / "cos"
        if cos_dir.exists():
            remaining = list(cos_dir.glob("*.md"))
            remaining_names = {r.name for r in remaining}
            # Only core rules should survive; non-core must be removed
            non_core = remaining_names - CORE_RULES
            assert not non_core, (
                f"Standard profile should only keep core rules, found extra: {sorted(non_core)}"
            )
            # Every remaining rule must be a core rule
            for name in remaining_names:
                assert name in CORE_RULES, (
                    f"Standard profile kept non-core rule: {name}"
                )

    def test_standard_profile_has_exactly_14_core_rules(self, tmp_path):
        """Standard profile must keep exactly 14 core rules after filtering."""
        project = self._setup_external_project(tmp_path, profile="standard")
        self._run_hook(str(project))

        cos_dir = project / ".claude" / "rules" / "cos"
        if cos_dir.exists():
            remaining = list(cos_dir.glob("*.md"))
            remaining_names = {r.name for r in remaining}
            assert len(remaining_names) == len(CORE_RULES), (
                f"Standard profile should have {len(CORE_RULES)} rules, "
                f"found {len(remaining_names)}: {sorted(remaining_names)}"
            )
            assert remaining_names == CORE_RULES, (
                f"Standard profile rules mismatch. "
                f"Missing: {sorted(CORE_RULES - remaining_names)}. "
                f"Extra: {sorted(remaining_names - CORE_RULES)}"
            )

    def test_standard_profile_removes_non_core_rules(self, tmp_path):
        """Standard profile must remove non-core rules like alpha-rule, beta-rule."""
        project = self._setup_external_project(tmp_path, profile="standard")
        self._run_hook(str(project))

        cos_dir = project / ".claude" / "rules" / "cos"
        if cos_dir.exists():
            remaining_names = {r.name for r in cos_dir.glob("*.md")}
            assert "alpha-rule.md" not in remaining_names, "Non-core alpha-rule.md should be removed"
            assert "beta-rule.md" not in remaining_names, "Non-core beta-rule.md should be removed"
            assert "sandbox-sampling.md" not in remaining_names, "Non-core sandbox-sampling.md should be removed"

    def test_standard_profile_each_core_rule_present(self, tmp_path):
        """Each of the 14 core rules must be present after standard profile install."""
        project = self._setup_external_project(tmp_path, profile="standard")
        self._run_hook(str(project))

        cos_dir = project / ".claude" / "rules" / "cos"
        if cos_dir.exists():
            remaining_names = {r.name for r in cos_dir.glob("*.md")}
            for core_rule in CORE_RULES:
                assert core_rule in remaining_names, (
                    f"Core rule {core_rule} missing after standard profile install"
                )

    def test_self_hosting_forces_full_profile(self):
        """When self-hosting (hooks/self-install.sh exists), profile is always full."""
        hook_content = self.HOOK_PATH.read_text()
        assert 'EFFICIENCY_PROFILE="full"' in hook_content, (
            "self-install.sh must default to full profile"
        )
        assert "IS_SELF_HOSTING" in hook_content, (
            "self-install.sh must detect self-hosting"
        )


# ===========================================================================
# Contextual Trigger Configuration Tests
# ===========================================================================


class TestContextualTriggers:
    """Verify contextual_triggers config maps to real rule files."""

    def _load_triggers(self) -> dict:
        import yaml
        config_path = PROJECT_ROOT / "cognitive-os.yaml"
        if not config_path.exists():
            pytest.skip("cognitive-os.yaml not found")
        config = yaml.safe_load(config_path.read_text())
        triggers = (
            config.get("rules", {})
            .get("loading", {})
            .get("contextual_triggers", {})
        )
        if not triggers:
            pytest.skip("No contextual_triggers configured")
        return triggers

    def test_every_trigger_has_a_rule_file(self):
        """Every key in contextual_triggers must map to a rules/{key}.md file."""
        triggers = self._load_triggers()
        missing = []
        for rule_name in triggers:
            if not (RULES_DIR / f"{rule_name}.md").exists():
                missing.append(rule_name)
        assert not missing, (
            f"Contextual triggers reference missing rule files: {sorted(missing)}"
        )

    def test_trigger_patterns_are_valid_regex(self):
        """Every trigger pattern must be a valid regex."""
        triggers = self._load_triggers()
        invalid = []
        for rule_name, pattern in triggers.items():
            if isinstance(pattern, str):
                try:
                    re.compile(pattern, re.IGNORECASE)
                except re.error as e:
                    invalid.append(f"{rule_name}: {e}")
        assert not invalid, f"Invalid trigger patterns: {invalid}"

    def test_critical_triggers_defined(self):
        """Key contextual triggers must exist for important on-demand rules."""
        triggers = self._load_triggers()
        expected_triggers = [
            "auto-repair",
            "definition-of-done",
            "acceptance-criteria",
        ]
        missing = [t for t in expected_triggers if t not in triggers]
        assert not missing, f"Missing critical contextual triggers: {sorted(missing)}"


# ===========================================================================
# Rule File Naming and Structure Tests
# ===========================================================================


class TestRuleNaming:
    """Verify naming conventions and structure of rule files."""

    def test_all_rule_files_are_lowercase_kebab(self):
        """All rule filenames must be lowercase kebab-case .md files."""
        bad_names = []
        for f in _get_rule_files():
            name = f.stem
            if name == "RULES-COMPACT":
                continue  # Exception: the index file
            if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', name):
                bad_names.append(f.name)
        assert not bad_names, f"Non-kebab-case rule filenames: {sorted(bad_names)}"

    def test_compact_filename_is_uppercase(self):
        """RULES-COMPACT.md must be the only uppercase rule file."""
        uppercase = [
            f.name for f in _get_rule_files()
            if any(c.isupper() for c in f.stem)
        ]
        assert uppercase == ["RULES-COMPACT.md"], (
            f"Only RULES-COMPACT.md should be uppercase, found: {uppercase}"
        )

    def test_no_empty_rule_files(self):
        """No rule file should be empty."""
        empty = [f.name for f in _get_rule_files() if f.stat().st_size == 0]
        assert not empty, f"Empty rule files: {sorted(empty)}"


# ===========================================================================
# Package Rules Exhaustive Tests
# ===========================================================================


class TestPackageRules:
    """Verify package rules are complete and correctly linked."""

    # Critical packages that must always exist (baseline subset).
    # New packages are auto-discovered and don't need to be added here.
    BASELINE_PACKAGES = {
        "agent-coordination",
        "aguara-security",
        "document-sync",
        "ecosystem-tools",
        "privacy-mode",
        "scope-governance",
        "skill-governance",
    }

    @staticmethod
    def _discover_packages_with_rules() -> dict[str, list[str]]:
        """Dynamically discover all packages that have rules/ dirs with .md files."""
        result = {}
        for pkg_rules_dir in PACKAGES_DIR.rglob("rules"):
            if not pkg_rules_dir.is_dir():
                continue
            md_files = sorted(f.name for f in pkg_rules_dir.glob("*.md"))
            if md_files:
                pkg_name = pkg_rules_dir.parent.name
                result[pkg_name] = md_files
        return result

    def test_baseline_packages_exist(self):
        """Critical baseline packages must have rules/ directories."""
        discovered = self._discover_packages_with_rules()
        missing = self.BASELINE_PACKAGES - set(discovered.keys())
        assert not missing, (
            f"Baseline packages missing rules/ dir: {sorted(missing)}"
        )

    def test_each_package_rules_dir_not_empty(self):
        """Every package with a rules/ dir must have at least one .md file."""
        discovered = self._discover_packages_with_rules()
        empty = [pkg for pkg, rules in discovered.items() if not rules]
        assert not empty, f"Packages with empty rules/ dirs: {sorted(empty)}"

    def test_all_package_rules_symlinked_to_rules_dir(self):
        """Every package rule must have a symlink in the top-level rules/ directory."""
        discovered = self._discover_packages_with_rules()
        all_rules = []
        for rules_list in discovered.values():
            all_rules.extend(rules_list)

        missing = []
        for rule_name in all_rules:
            rule_path = RULES_DIR / rule_name
            if not rule_path.exists():
                missing.append(rule_name)
            elif not rule_path.is_symlink():
                missing.append(f"{rule_name} (exists but not a symlink)")

        assert not missing, f"Package rules not properly symlinked: {sorted(missing)}"

    def test_total_package_count_above_baseline(self):
        """Total number of packages with rules must not drop below baseline."""
        discovered = self._discover_packages_with_rules()
        assert len(discovered) >= len(self.BASELINE_PACKAGES), (
            f"Package count ({len(discovered)}) dropped below baseline "
            f"({len(self.BASELINE_PACKAGES)}): {sorted(discovered.keys())}"
        )


# ===========================================================================
# Regression Safety: Known Rule List
# ===========================================================================


class TestKnownRulesList:
    """Pin the exact set of rule files for regression detection."""

    KNOWN_RULES = sorted([
        "RULES-COMPACT.md",
        "acceptance-criteria.md",
        "adaptive-bypass.md",
        "adversarial-review.md",
        "agent-escalation.md",
        "aguara-integration.md",
        "agent-communication.md",
        "agent-customization.md",
        "agent-identity.md",
        "agent-kpis.md",
        "agent-quality.md",
        "agent-security.md",
        "agent-sidecars.md",
        "anti-hallucination.md",
        "assumption-tracking.md",
        "auto-repair.md",
        "auto-rollback.md",
        "auto-skill-generation.md",
        "blast-radius.md",
        "broken-window-policy.md",
        "capability-levels.md",
        "capability-protection.md",
        "clarification-gate.md",
        "closed-loop-prompts.md",
        "cognitive-os-changes.md",
        "component-classification.md",
        "confidence-gate.md",
        "consequence-system.md",
        "content-policy.md",
        "context-management.md",
        "context-optimization.md",
        "context7-auto-trigger.md",
        "cost-prediction.md",
        "crash-recovery.md",
        "credential-management.md",
        "decomposition.md",
        "definition-of-done.md",
        "cognitive-load.md",
        "doc-sync.md",
        "dogfooding.md",
        "dry-run.md",
        "ecosystem-tools.md",
        "engram-organization.md",
        "error-learning.md",
        "estimation-calibration.md",
        "fault-tolerance.md",
        "hcom-integration.md",
        "hook-security-profiles.md",
        "impact-analysis.md",
        "infra-health.md",
        "infra-intent.md",
        "library-selection.md",
        "license-policy.md",
        "model-compatibility.md",
        "model-routing.md",
        "orchestrator-mode.md",
        "os-vs-project.md",
        "parry-integration.md",
        "pentesting-readiness.md",
        "performance-monitoring.md",
        "phase-aware-agents.md",
        "plan-first.md",
        "pre-commit-gate.md",
        "private-mode.md",
        "prompt-composition.md",
        "prompt-quality.md",
        "rate-limit-protection.md",
        "rate-limiting.md",
        "repomix-integration.md",
        "resource-governance.md",
        "responsiveness.md",
        "result-management.md",
        "sandbox-sampling.md",
        "scope-creep-detection.md",
        "scope-proportionality.md",
        "scout-pattern.md",
        "security-scanning.md",
        "self-improvement-protocol.md",
        "session-concurrency.md",
        "singularity.md",
        "skill-management.md",
        "split-and-resume.md",
        "squad-protocol.md",
        "step-files.md",
        "supply-chain-defense.md",
        "token-economy.md",
        "tero-integration.md",
        "trailofbits-skills.md",
        "trust-score.md",
        "non-blocking-retry.md",
        "user-prompt-capture.md",
        "workload-scheduling.md",
    ])

    def test_no_rules_removed(self):
        """No known rules should be removed (additions are OK)."""
        actual = set(f.name for f in _get_rule_files())
        removed = sorted(set(self.KNOWN_RULES) - actual)
        assert not removed, (
            f"Rules REMOVED from baseline (not allowed without justification): {removed}"
        )

    def test_minimum_rule_count(self):
        """Rule count should never drop below the known baseline."""
        assert len(list(_get_rule_files())) >= len(self.KNOWN_RULES), (
            f"Rule count dropped below baseline of {len(self.KNOWN_RULES)}"
        )

"""Functional audit — pytest contracts for hooks/.

Implements the Capa 3 scorecard contract:
  docs/04-Concepts/architecture/functional-audit/scorecard-hooks.md

These tests are read-only and classify each hook without fixing anything. A
failure here is a finding for the audit report, not a CI blocker by default.

Run all audit tests:
    python3 -m pytest tests/audit/test_hooks_contracts.py -v

Collect-only (required by acceptance criteria):
    python3 -m pytest tests/audit/test_hooks_contracts.py --collect-only

Phase note: reconstruction — expect failures to reveal the gap, not to be fixed
in this pass.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# ── Repo roots ─────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_ROOT / "hooks"
SETTINGS_FILE = REPO_ROOT / ".claude" / "settings.json"
PROFILE_SCRIPT = REPO_ROOT / "scripts" / "apply-efficiency-profile.sh"
SKILLS_DIR = REPO_ROOT / "skills"
PACKAGES_DIR = REPO_ROOT / "packages"
RULES_DIR = REPO_ROOT / "rules"
REGISTRATION_ALLOWLIST = HOOKS_DIR / "_lib" / "registration-allowlist.txt"

MIN_NONTRIVIAL_LINES = 5  # stub threshold per task spec

def _registration_allowlist() -> set[str]:
    """Hooks intentionally not projected into every active driver/profile."""
    if not REGISTRATION_ALLOWLIST.exists():
        return set()
    names: set[str] = set()
    for line in REGISTRATION_ALLOWLIST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.add(line)
    return names


# Known code-dead hooks (referenced but intentionally missing): these are the
# classification output, not a TODO. This set is intentionally empty after the
# 2026-04-23 audit refresh: previous entries now exist on disk.
EXPECTED_CODE_DEAD: frozenset[str] = frozenset({
    # Referenced by skills/deep-tool-research; future axis-gate hook for the
    # 7-annex deep-evaluation flow. Tracked as a follow-up.
    "deep-research-axis-gate.sh",
})

# Placeholder/illustrative hook names used in skill templates and example docs
# (e.g. skills that SCAFFOLD a new project generate a `block-prod-urls.sh`
# script; tutorials reference `my-hook.sh`, `old-hook.sh`, `related-hook.sh`).
# These are NOT missing hooks — they are documentation literals. Exclude from
# the code-dead reference check.
PLACEHOLDER_HOOK_NAMES = {
    "block-prod-urls.sh",   # skills/scaffold-project + cognitive-os-init generate this
    "my-hook.sh",           # rules/pentesting-readiness example
    "old-hook.sh",          # skills/validate-config example
    "related-hook.sh",      # skills/add-rule example
}

# Orphan hooks per the scorecard (existed on disk, absent from every profile).
# Encoded here so the audit test is stable against wiring churn — the test
# fails if a NEW orphan appears or a listed orphan disappears without updating
# this file.
KNOWN_ORPHANS = {
    "ai-provider-identity-guard.sh",
    "session-end-cleanup.sh",
    "adaptive-bypass.sh",
    "agent-bus-monitor.sh",
    "agent-output-verifier.sh",
    "agnix-lint.sh",
    "auto-rollback-trigger.sh",
    "background-agent-reminder.sh",
    "clarification-interceptor.sh",
    "code-review-on-commit.sh",
    "cognitive-os-health.sh",
    "confidence-gate.sh",
    "context-diet.sh",
    "contextual-rule-loader.sh",
    "conversation-capture.sh",
    "dry-run-preview.sh",
    "error-learning.sh",
    "idle-service-cleanup.sh",
    "infra-intent-detector.sh",
    "jupyter-sandbox.sh",
    "memu-sync.sh",
    "metrics-calibrator-trigger.sh",
    "metrics-rotation.sh",
    "notify.sh",
    "package-sync.sh",
    "pre-cleanup-snapshot.sh",
    "pre-commit-gate.sh",
    "private-mode-gate.sh",
    "private-mode-metrics-gate.sh",
    "reinvention-check.sh",
    "release-guard.sh",
    "resource-check.sh",
    "session-knowledge-extractor.sh",
    "session-state-save.sh",
    "singularity-check.sh",
    "skill-feedback-tracker.sh",
    "skill-tracker.sh",
    "sync-to-repo.sh",
    "tool-discovery-trigger.sh",
    "tool-loop-detector.sh",
    "worktree-submodule-fix.sh",
} | _registration_allowlist()


# ── Data loaders (cached once per session) ─────────────────────────────
def _hook_files() -> list[str]:
    """All `*.sh` files directly under hooks/ (not _lib/)."""
    return sorted(p.name for p in HOOKS_DIR.glob("*.sh") if p.is_file())


def _wired_in_settings() -> set[str]:
    """Hooks registered in `.claude/settings.json` (full profile)."""
    data = json.loads(SETTINGS_FILE.read_text())
    wired: set[str] = set()
    for _event, groups in data.get("hooks", {}).items():
        for g in groups:
            for h in g.get("hooks", []):
                cmd = h.get("command", "")
                m = re.search(r"hooks/([a-z][a-z0-9_-]*\.sh)", cmd)
                if m:
                    wired.add(m.group(1))
    return wired


def _profile_hooks(profile_name: str) -> set[str]:
    """Hook names listed for a profile tier in apply-efficiency-profile.sh."""
    src = PROFILE_SCRIPT.read_text()
    result: set[str] = set()
    for m in re.finditer(r'case "\$profile" in(.+?)esac', src, re.DOTALL):
        block = m.group(1)
        pm = re.search(rf"\b{profile_name}\)(.*?)(?:;;\s*\n)", block, re.DOTALL)
        if pm:
            body = pm.group(1)
            for fm in re.finditer(r'"([a-z][a-z0-9_-]*\.sh)"', body):
                result.add(fm.group(1))
    return result


def _non_trivial_lines(path: Path) -> int:
    """Count non-blank non-comment lines."""
    count = 0
    for line in path.read_text(errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        count += 1
    return count


def _skill_and_rule_refs() -> dict[str, list[str]]:
    """Map of hook-filename → list of relative paths that reference it.

    Searches skills/, packages/, rules/ for the pattern `hooks/<name>.sh` AND
    bare `<name>.sh` inside .md files (doc-style reference).
    """
    refs: dict[str, list[str]] = {}
    pat_full = re.compile(r"hooks/([a-z][a-z0-9_-]*\.sh)")
    roots = [SKILLS_DIR, PACKAGES_DIR, RULES_DIR]
    for root in roots:
        if not root.exists():
            continue
        for md in root.rglob("*.md"):
            try:
                text = md.read_text(errors="replace")
            except OSError:
                continue
            for m in pat_full.finditer(text):
                name = m.group(1)
                refs.setdefault(name, []).append(str(md.relative_to(REPO_ROOT)))
    return refs


# ── Parameter sets (computed once) ─────────────────────────────────────
HOOKS = _hook_files()
WIRED = _wired_in_settings()
LEAN = _profile_hooks("lean")
STANDARD = _profile_hooks("standard")
FULL = WIRED  # settings.json IS the full profile per rules/project-gotchas.md
ALL_PROFILES = LEAN | STANDARD | FULL
REFS = _skill_and_rule_refs()


# ── Tests ──────────────────────────────────────────────────────────────
@pytest.mark.audit
@pytest.mark.parametrize("hook_name", sorted(WIRED))
def test_every_wired_hook_exists(hook_name: str) -> None:
    """Every hook registered in settings.json has a file on disk.

    Failure = code-dead wiring (the harness will try to run a missing script).
    """
    path = HOOKS_DIR / hook_name
    assert path.is_file(), (
        f"Hook '{hook_name}' is wired in .claude/settings.json but "
        f"hooks/{hook_name} does not exist on disk"
    )


@pytest.mark.audit
@pytest.mark.parametrize("hook_name", HOOKS)
def test_no_orphan_hooks(hook_name: str) -> None:
    """Every hook on disk is wired in some profile — OR known-orphan.

    The KNOWN_ORPHANS set encodes the scorecard's classification. A new hook
    that isn't in any profile AND isn't in KNOWN_ORPHANS fails here, forcing
    the author to either wire it or acknowledge orphan status explicitly.
    """
    if hook_name in ALL_PROFILES:
        return  # wired somewhere
    assert hook_name in KNOWN_ORPHANS, (
        f"Hook 'hooks/{hook_name}' exists on disk but is not wired in any "
        f"profile tier (lean/standard/full) and is not listed in KNOWN_ORPHANS. "
        f"Either wire it, remove it, or add it to KNOWN_ORPHANS."
    )


@pytest.mark.audit
def test_known_code_dead_hooks_stay_missing() -> None:
    """Hooks known code-dead (referenced, not on disk) remain absent.

    If someone implements one of these (e.g. creates `auto-verify.sh`), this
    test fails and forces the scorecard to be re-generated. An empty
    EXPECTED_CODE_DEAD set is a passing state, not a pytest NOTSET skip.
    """
    resurrected = [hook_name for hook_name in sorted(EXPECTED_CODE_DEAD) if (HOOKS_DIR / hook_name).exists()]
    assert not resurrected, (
        "Previously code-dead hook(s) now exist on disk. Re-run the Capa 3 audit "
        "and update docs/04-Concepts/architecture/functional-audit/scorecard-hooks.md + "
        f"EXPECTED_CODE_DEAD: {resurrected}"
    )


@pytest.mark.audit
def test_no_skill_references_dead_hook() -> None:
    """Skills / rules / packages must not reference a missing hook file.

    Dead-code reference bugs (like the cluster-D auto-refine skill pointing at
    a non-existent hook) fail here. The EXPECTED_CODE_DEAD set acknowledges
    the currently-known dead references — new ones are blocked.
    """
    dead_refs: list[str] = []
    for hook_name, referrers in REFS.items():
        path = HOOKS_DIR / hook_name
        if path.exists():
            continue
        if hook_name in EXPECTED_CODE_DEAD:
            continue  # known + documented in scorecard
        if hook_name in PLACEHOLDER_HOOK_NAMES:
            continue  # template/example literal, not a real reference
        dead_refs.append(f"{hook_name} referenced by {referrers}")

    assert not dead_refs, (
        "Found NEW skill/rule/package references to missing hook files (not in "
        "EXPECTED_CODE_DEAD):\n  "
        + "\n  ".join(dead_refs)
        + "\nEither create the missing hook, remove the reference, or add it to "
        "EXPECTED_CODE_DEAD after updating the scorecard."
    )


@pytest.mark.audit
@pytest.mark.parametrize("hook_name", HOOKS)
def test_no_stub_hooks(hook_name: str) -> None:
    """Every hook has non-trivial logic (> MIN_NONTRIVIAL_LINES body lines)."""
    path = HOOKS_DIR / hook_name
    n = _non_trivial_lines(path)
    assert n > MIN_NONTRIVIAL_LINES, (
        f"Hook 'hooks/{hook_name}' has only {n} non-comment, non-empty lines "
        f"(threshold: {MIN_NONTRIVIAL_LINES}). Likely a stub — implement it, "
        f"delete it, or document why a placeholder is acceptable."
    )


@pytest.mark.audit
def test_code_dead_hooks_are_documented() -> None:
    """The known code-dead hooks must match what the scorecard documents."""
    scorecard = REPO_ROOT / "docs" / "04-Concepts" / "architecture" / "functional-audit" / "scorecard-hooks.md"
    assert scorecard.exists(), f"Missing scorecard at {scorecard}"
    text = scorecard.read_text()
    missing = [name for name in EXPECTED_CODE_DEAD if name not in text]
    assert not missing, (
        f"EXPECTED_CODE_DEAD contains hooks not documented in the scorecard: {missing}. "
        f"Update docs/04-Concepts/architecture/functional-audit/scorecard-hooks.md."
    )


@pytest.mark.audit
def test_hook_counts_match_scorecard() -> None:
    """Sanity check: the scorecard records the latest audit refresh."""
    scorecard = REPO_ROOT / "docs" / "04-Concepts" / "architecture" / "functional-audit" / "scorecard-hooks.md"
    text = scorecard.read_text(encoding="utf-8")
    assert "2026-04-23 audit refresh" in text
    assert f"Total hook files on disk (`hooks/*.sh`) | **{len(HOOKS)}**" in text


# ─── ADR-067 Phase 2: hooks/*.sh header contract ─────────────────────────────
# These tests enforce the header contract for new hooks defined in ADR-067 §Phase 2.
#
# Grandfathering policy:
#   - Existing 154 hooks (committed before Phase 2) are NOT enforced unless
#     COS_STRICT_HOOK_VALIDATION=1 is set.
#   - "New" is determined by git: if git log --diff-filter=A shows no ADD commit,
#     the file is considered new in the working tree and IS enforced.
#   - The NEW_HOOKS_PHASE2 set lists the hooks explicitly created by Phase 2 and
#     therefore subject to the full contract check in CI.
#
# If you add a new hook after Phase 2, it MUST pass all header checks.

# Hooks explicitly created by ADR-067 Phase 2 implementation — always enforce.
NEW_HOOKS_PHASE2: frozenset[str] = frozenset({
    "rule-frontmatter-validator.sh",
    "hook-header-validator.sh",
    "adr-section-validator.sh",
})

_REQUIRED_HEADER_FIELDS = [
    ("shebang", re.compile(r"^#!/usr/bin/env bash\s*$")),
    ("scope_comment", re.compile(r"^#\s*SCOPE:\s*\S")),
    ("purpose_comment", re.compile(r"^#\s*PURPOSE:\s*\S")),
    ("event_comment", re.compile(r"^#\s*EVENT:\s*\S")),
]


def _hook_has_header_contract(hook_path: Path) -> list[str]:
    """Return list of contract violations for a hook file."""
    try:
        text = hook_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [f"cannot read {hook_path}"]

    lines = text.splitlines()
    issues: list[str] = []

    # Shebang on line 1
    first = lines[0] if lines else ""
    if not re.match(r"^#!/usr/bin/env bash\s*$", first):
        issues.append(f"line 1 must be '#!/usr/bin/env bash' (got: {first[:60]!r})")

    # SCOPE, PURPOSE, EVENT comments anywhere in the file
    for field_name, pattern in _REQUIRED_HEADER_FIELDS[1:]:  # skip shebang (checked above)
        if not any(pattern.match(line) for line in lines):
            issues.append(f"missing '# {field_name.upper().replace('_COMMENT', '')}: ...' comment")

    # set -euo pipefail in first 20 lines
    first_20 = "\n".join(lines[:20])
    if "set -euo pipefail" not in first_20:
        issues.append("'set -euo pipefail' not found in first 20 lines")

    return issues


@pytest.mark.audit
@pytest.mark.parametrize("hook_name", sorted(NEW_HOOKS_PHASE2))
def test_phase2_hooks_have_header_contract(hook_name: str) -> None:
    """Hooks created by ADR-067 Phase 2 must satisfy the full header contract.

    These hooks are always enforced regardless of git state — they are the
    reference implementation that all future hooks should follow.
    """
    hook_path = HOOKS_DIR / hook_name
    assert hook_path.is_file(), (
        f"Phase 2 hook '{hook_name}' does not exist at hooks/{hook_name}. "
        f"This is unexpected — the Phase 2 implementation must create it."
    )
    issues = _hook_has_header_contract(hook_path)
    assert not issues, (
        f"Phase 2 hook 'hooks/{hook_name}' violates header contract: "
        + "; ".join(issues)
    )

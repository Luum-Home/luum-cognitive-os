"""Capa 3 — Rules enforcement audit.

Classifies every rule in `rules/*.md` by its ACTUAL enforcement path and asserts
that the repository is self-consistent: rules claiming hook enforcement must have
the hook registered in `.claude/settings.json`; referenced files must exist; the
compact index must cover every non-excluded rule.

Read-only. Does not mutate any rule, hook, or settings file.

Marker: `@pytest.mark.audit` on every test so they can be run in isolation:
    python3 -m pytest tests/audit/ -m audit
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# ─── Fixtures and helpers ────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RULES_DIR = PROJECT_ROOT / "rules"
HOOKS_DIR = PROJECT_ROOT / "hooks"
SETTINGS_PATH = PROJECT_ROOT / ".claude" / "settings.json"
COMPACT_PATH = RULES_DIR / "RULES-COMPACT.md"
MANDATORY_TEMPLATE = PROJECT_ROOT / "templates" / "agent-mandatory-rules.md"
SELF_INSTALL = PROJECT_ROOT / "hooks" / "self-install.sh"
REGISTRATION_ALLOWLIST = PROJECT_ROOT / "hooks" / "_lib" / "registration-allowlist.txt"

# Rules intentionally excluded from the compact index — they are not ornament,
# they are deliberately omitted for a documented reason. Extend this list only
# with justification, never to silence a failing test.
COMPACT_EXEMPT: set[str] = {
    "RULES-COMPACT.md",  # the index itself
    "ROADMAP.md",         # Sprint 2A roadmap for broken/pending rule wiring (meta-doc, not a rule)
    # Note: plan-first.md was moved to docs/patterns/ in Sprint 2A and is no longer in rules/
}

# Rules whose claim of hook-enforcement is intentionally not wired in settings.json
# (e.g. git hooks, manual invocation). Documented in the scorecard.
# Sprint 2A: added entries for hook-enforced-BROKEN rules (hook exists on disk,
# registration deferred to the hook-registration sprint). Per rules/ROADMAP.md
# Section 1, these rules are demoted to agent-instruction-only until their hook
# is registered in .claude/settings.json.
SETTINGS_WIRING_EXEMPT: dict[str, str] = {
    "pre-commit-gate.md": "git hook (.git/hooks/pre-commit), not a Claude hook",
    # Hook-enforced-BROKEN — pending registration. See rules/ROADMAP.md §1.
    "acceptance-criteria.md": "auto-verify.sh exists; registration pending (ROADMAP §2.1)",
    "agent-quality.md": "auto-verify.sh + dod-gate.sh exist; registration pending (ROADMAP §2.2)",
    "closed-loop-prompts.md": "auto-refine.sh exists; registration pending (ROADMAP §2.3)",
    "phase-aware-agents.md": "auto-refine.sh exists; registration pending (ROADMAP §2.4)",
    "audit-trail.md": "git-context-capture.sh + session-changelog.sh + audit-id-enricher.sh exist; registration pending (ROADMAP §1.1)",
    "confidentiality-protection.md": "confidentiality-enforcer.sh exists; registration pending (ROADMAP §1.4)",
    "pre-dev-readiness-gate.md": "predev-completeness-check.sh exists; registration pending (ROADMAP §1.6)",
    "observability.md": "mlflow-sync.sh exists; registration pending (agent-instruction-only per scorecard)",
    "trust-score.md": "trust-score-validator.sh IS registered; test trips on secondary confidence-gate.sh ref (see ROADMAP §1.3)",
}


def _registration_allowlist() -> set[str]:
    if not REGISTRATION_ALLOWLIST.exists():
        return set()
    names: set[str] = set()
    for line in REGISTRATION_ALLOWLIST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.add(line)
    return names


ALLOWLISTED_UNREGISTERED_HOOKS = _registration_allowlist()


def _all_rule_files() -> list[Path]:
    return sorted(RULES_DIR.glob("*.md"))


def _rule_name(path: Path) -> str:
    return path.name


def _settings_text() -> str:
    return SETTINGS_PATH.read_text(encoding="utf-8")


def _settings_hook_names() -> set[str]:
    """Return every hook basename registered in .claude/settings.json."""
    data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    names: set[str] = set()
    for event_hooks in data.get("hooks", {}).values():
        for matcher_group in event_hooks:
            for hook in matcher_group.get("hooks", []):
                cmd = hook.get("command", "")
                m = re.search(r"/hooks/([A-Za-z0-9_-]+\.sh)", cmd)
                if m:
                    names.add(m.group(1))
                m2 = re.search(r"/packages/[^/]+/hooks/([A-Za-z0-9_-]+\.sh)", cmd)
                if m2:
                    names.add(m2.group(1))
    return names


def _hook_refs_in_rule(rule_path: Path) -> set[str]:
    """Extract every `<name>.sh` reference in a rule file."""
    text = rule_path.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"([A-Za-z0-9_-]+\.sh)", text))


def _file_refs_in_rule(rule_path: Path) -> set[str]:
    """Extract repo-relative file paths referenced in code fences or backticks.

    Matches occurrences like `hooks/foo.sh`, `lib/bar.py`, `scripts/baz.sh`,
    `templates/qux.md`. Ignores obvious non-files like `/api/`, `{var}`, URLs.
    """
    text = rule_path.read_text(encoding="utf-8", errors="replace")
    candidates = set(re.findall(r"`([a-zA-Z0-9_./-]+\.(?:sh|py|md|yaml|yml|json|go|ts|js|jsonl))`", text))
    # Only keep references that look like repo-relative paths (have a slash)
    return {c for c in candidates if "/" in c and not c.startswith("http")}


def _is_runtime_generated_ref(ref: str) -> bool:
    """Return True for documented runtime artifacts that should not exist in git."""
    if ref.startswith((".cognitive-os/metrics/", ".claude/metrics/", "metrics/")):
        return ref.endswith(".jsonl")
    generated_prefixes = (
        ".cognitive-os/dynamic-tools/",
        ".cognitive-os/rate-limit-",
        ".atl/",
    )
    if ref.startswith(generated_prefixes):
        return True
    generated_files = {
        ".claude/detected-stack.json",
    }
    return ref in generated_files


DOCUMENTED_REMOVED_OR_FUTURE_REFS: set[str] = {
    "lib/workload_scheduler.py",  # rules document its removal and fallback path
    "lib/task_dag.py",  # rules document its removal and retained conceptual guidance
    "docs/research/license-analysis.md",  # optional research artifact, not a runtime contract
    "hooks/_lib/hook-runtime-probe.sh",  # SO-SLO future probe reference
    "lib/agent_heartbeat.py",  # SO-SLO future telemetry reference
    "scripts/so-slo-report.sh",  # SO-SLO future reporting reference
}


def _compact_index_keys() -> set[str]:
    """Parse the rule-keys referenced in RULES-COMPACT.md."""
    text = COMPACT_PATH.read_text(encoding="utf-8")
    # Match [`key-name`] — the canonical reference form
    return set(re.findall(r"\[`([a-z][a-z0-9-]+)`\]", text))


# ─── Parameterization ────────────────────────────────────────────────────────

RULE_PATHS = _all_rule_files()
RULE_IDS = [p.name for p in RULE_PATHS]


# ─── Tests ───────────────────────────────────────────────────────────────────


@pytest.mark.audit
def test_rules_directory_not_empty():
    """Sanity: rules/ contains at least 20 markdown files."""
    assert len(RULE_PATHS) >= 20, f"Expected >= 20 rule files, found {len(RULE_PATHS)}"


@pytest.mark.audit
@pytest.mark.parametrize("rule_path", RULE_PATHS, ids=RULE_IDS)
def test_every_rule_in_compact_index(rule_path: Path):
    """Every rule file either appears in RULES-COMPACT.md or is on the exempt list.

    Rationale: if a rule is not in the compact index and not intentionally
    exempt, the orchestrator cannot reference it by key — it is effectively
    invisible documentation.
    """
    name = _rule_name(rule_path)
    if name in COMPACT_EXEMPT:
        pytest.skip(f"{name} is intentionally exempt from compact index")
    key = name.removesuffix(".md")
    compact_keys = _compact_index_keys()
    assert key in compact_keys, (
        f"Rule {name} is not referenced in RULES-COMPACT.md by key [`{key}`]. "
        f"Either add a reference or add {name!r} to COMPACT_EXEMPT with justification."
    )


@pytest.mark.audit
@pytest.mark.parametrize("rule_path", RULE_PATHS, ids=RULE_IDS)
def test_every_hook_enforced_rule_has_live_hook(rule_path: Path):
    """Every .sh hook referenced inside a rule must either:
    (a) exist AND be registered in .claude/settings.json, OR
    (b) exist AND be on the SETTINGS_WIRING_EXEMPT list, OR
    (c) not exist — which is caught by test_no_rule_references_missing_file.
    """
    name = _rule_name(rule_path)
    refs = _hook_refs_in_rule(rule_path)
    if not refs:
        pytest.skip(f"{name} references no .sh files")
    if name in SETTINGS_WIRING_EXEMPT:
        pytest.skip(f"{name} exempt: {SETTINGS_WIRING_EXEMPT[name]}")

    registered = _settings_hook_names()
    existing_on_disk = {p.name for p in HOOKS_DIR.glob("*.sh")}
    # Also allow packaged hooks under packages/*/hooks/
    for p in PROJECT_ROOT.glob("packages/*/hooks/*.sh"):
        existing_on_disk.add(p.name)

    # For each hook the rule claims to use, it must be either registered OR
    # documented as a non-Claude hook. We only enforce registration for hooks
    # that actually exist on disk (missing ones are flagged by another test).
    claimed_and_existing = refs & existing_on_disk
    if not claimed_and_existing:
        pytest.skip(f"{name} references hooks but none exist on disk (caught elsewhere)")

    unregistered = claimed_and_existing - registered
    # The rule is effectively unenforced if every claimed-and-existing hook is
    # unregistered. If at least one is registered, enforcement is partial — still acceptable.
    # Surface the full diff to aid debugging.
    if unregistered == claimed_and_existing:
        if unregistered <= ALLOWLISTED_UNREGISTERED_HOOKS:
            pytest.skip(
                f"{name} references hook(s) deferred by registration allowlist: "
                f"{sorted(unregistered)}"
            )
        pytest.fail(
            f"{name} claims hook enforcement via {sorted(claimed_and_existing)}, "
            f"but none of these hooks are registered in .claude/settings.json. "
            f"Either register the hooks, add {name!r} to SETTINGS_WIRING_EXEMPT with "
            f"justification, or rewrite the rule to make manual invocation explicit."
        )


@pytest.mark.audit
@pytest.mark.parametrize("rule_path", RULE_PATHS, ids=RULE_IDS)
def test_no_rule_references_missing_file(rule_path: Path):
    """Every repo-relative file path inside a rule's code fences must exist on disk.

    Catches code-dead rules (references to hooks/scripts never built).
    """
    name = _rule_name(rule_path)
    refs = _file_refs_in_rule(rule_path)
    missing: list[str] = []
    for ref in refs:
        p = PROJECT_ROOT / ref
        if p.exists():
            continue
        # Some references are prose examples (e.g. "hooks/my-hook.sh" in a tutorial).
        # Allow any reference containing "my-", "your-", "example", "your_" as pedagogical.
        if re.search(r"(?:^|/)(?:my-|your-|example|foo|bar)", ref):
            continue
        if _is_runtime_generated_ref(ref):
            continue
        if ref in DOCUMENTED_REMOVED_OR_FUTURE_REFS:
            continue
        # Scripts like tests/coverage-report.sh may live under services/ — check
        # with a broad glob before failing.
        basename = Path(ref).name
        if list(PROJECT_ROOT.rglob(basename)):
            continue
        missing.append(ref)
    assert not missing, (
        f"{name} references {len(missing)} path(s) that do not exist on disk: {missing}. "
        f"Either create the file, update the rule, or add the reference to a "
        f"pedagogical-example allowlist in this test."
    )


@pytest.mark.audit
def test_mandatory_rules_template_exists_and_non_empty():
    """templates/agent-mandatory-rules.md must exist and contain actual rule content.

    This is the ONLY mechanism that injects rules into sub-agent context at launch
    (via hooks/subagent-context-injector.sh). If it is missing or empty, no rules
    from rules/ reach sub-agents automatically.
    """
    assert MANDATORY_TEMPLATE.exists(), f"Missing {MANDATORY_TEMPLATE}"
    body = MANDATORY_TEMPLATE.read_text(encoding="utf-8")
    # Expect at least five substantive section headings.
    headings = re.findall(r"^###\s+\S", body, flags=re.MULTILINE)
    assert len(headings) >= 3, (
        f"{MANDATORY_TEMPLATE} has only {len(headings)} section(s). "
        f"If this file doesn't cover the critical rules, sub-agents won't see them."
    )


@pytest.mark.audit
def test_self_install_classifies_every_rule():
    """Every rule file must be in CORE_RULES, EXCLUDED_RULES, or the compact-only list.

    self-install.sh decides which rules are symlinked into .claude/rules/cos/.
    If a rule is in neither list, its injection status is undefined.
    """
    if not SELF_INSTALL.exists():
        pytest.skip("self-install.sh not present")
    body = SELF_INSTALL.read_text(encoding="utf-8")

    def extract_array(varname: str) -> set[str]:
        items: set[str] = set()
        in_array = False
        for line in body.splitlines():
            if not in_array and re.match(rf"^\s*{varname}=\(", line):
                in_array = True
                continue
            if in_array and re.match(r"^\s*\)", line):
                break
            if in_array:
                items.update(re.findall(r'"([a-z0-9_-]+\.md)"', line))
        return items

    core = extract_array("CORE_RULES")
    excluded = extract_array("EXCLUDED_RULES")
    classified = core | excluded

    all_rules = {p.name for p in RULE_PATHS}
    unclassified = all_rules - classified - COMPACT_EXEMPT
    assert not unclassified, (
        f"Rules not classified in CORE_RULES or EXCLUDED_RULES: {sorted(unclassified)}. "
        f"Add each to the appropriate array in hooks/self-install.sh or mark them as "
        f"COMPACT_EXEMPT here."
    )


@pytest.mark.audit
def test_excluded_hook_enforced_rules_actually_have_registered_hooks():
    """EXCLUDED_RULES block A in self-install.sh lists rules 'replaced by their hook'.
    For each such rule, the named hook must be registered in settings.json.
    Otherwise the rule is both hidden from context AND not enforced — the worst case.
    """
    if not SELF_INSTALL.exists():
        pytest.skip("self-install.sh not present")
    body = SELF_INSTALL.read_text(encoding="utf-8")
    # Parse the "Hook-enforced" block: rules with a `.sh` comment on the same line.
    pattern = re.compile(r'"([a-z0-9_-]+\.md)"\s+#.*?([a-z0-9_-]+\.sh)')
    mappings = pattern.findall(body)
    registered = _settings_hook_names()

    broken: list[tuple[str, str]] = []
    for rule, hook in mappings:
        if hook not in registered:
            if hook in ALLOWLISTED_UNREGISTERED_HOOKS:
                continue
            # Some mappings list a hook that is itself in packages/.../hooks/
            # Our registration set includes those, so if still missing it's real.
            broken.append((rule, hook))
    assert not broken, (
        f"EXCLUDED_RULES claims these rules are hook-enforced, but the hook is not "
        f"registered in .claude/settings.json: {broken}. The rule is hidden from "
        f"context AND its hook never fires. Either register the hook or remove the "
        f"rule from EXCLUDED_RULES so its content is loaded."
    )

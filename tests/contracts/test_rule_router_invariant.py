"""Contract tests for RuleRouter (ADR-179).

Invariants:
  1. Every rules/*.md with enforcement: agent-instruction has routing_patterns.
     ~60 rules are unmigrated PoC backlog; this is xfail until migrated.
  2. No enforcement: hook rule has a stale hook reference (the named hook
     either exists on disk or is in hooks/_lib/registration-allowlist.txt).
  3. RuleRouter coverage threshold matches manifests/rule-routing-coverage.yaml
     baseline.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.rule_router import RuleRouter, _enumerate_rule_paths, _parse_frontmatter

pytestmark = pytest.mark.contract


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read_frontmatter(path: Path) -> dict:
    try:
        return _parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}


def _all_rule_paths() -> list[Path]:
    return _enumerate_rule_paths(PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Invariant 1 — agent-instruction rules must have routing_patterns
# ---------------------------------------------------------------------------


def test_every_agent_instruction_rule_has_routing_patterns():
    missing = []
    for path in _all_rule_paths():
        fm = _read_frontmatter(path)
        if not fm:
            continue
        enforcement = str(fm.get("enforcement", "")).lower()
        if enforcement in {"agent-instruction", "hybrid"}:
            if not fm.get("routing_patterns"):
                missing.append(path.name)
    assert not missing, f"Missing routing_patterns: {missing}"


# ---------------------------------------------------------------------------
# Invariant 2 — hook-enforced rules point to a real hook
# ---------------------------------------------------------------------------


def test_hook_enforced_rules_have_real_hook():
    hooks_dir = PROJECT_ROOT / "hooks"
    allowlist_path = PROJECT_ROOT / "hooks" / "_lib" / "registration-allowlist.txt"
    allowlist: set[str] = set()
    if allowlist_path.is_file():
        for line in allowlist_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                allowlist.add(line)

    stale = []
    for path in _all_rule_paths():
        fm = _read_frontmatter(path)
        if not fm:
            continue
        if str(fm.get("enforcement", "")).lower() != "hook":
            continue
        rule_name = path.stem
        hook_file = hooks_dir / f"{rule_name}.sh"
        if hook_file.is_file():
            continue
        if f"{rule_name}.sh" in allowlist:
            continue
        stale.append(rule_name)
    assert not stale, f"Hook-enforced rules with no backing hook: {stale}"


# ---------------------------------------------------------------------------
# Invariant 3 — coverage matches manifest baseline
# ---------------------------------------------------------------------------


def test_coverage_baseline_matches_manifest():
    import yaml  # type: ignore[import]

    manifest_path = PROJECT_ROOT / "manifests" / "rule-routing-coverage.yaml"
    assert manifest_path.is_file(), "rule-routing-coverage.yaml must exist"
    data = yaml.safe_load(manifest_path.read_text())
    baseline = data.get("baseline", {})
    min_count = int(baseline.get("min_routed_rule_count", 0))

    router = RuleRouter(project_root=PROJECT_ROOT)
    assert router.routable_rule_count >= min_count, (
        f"RuleRouter exposes {router.routable_rule_count} routable rules, "
        f"below manifest baseline {min_count} — ratchet violation."
    )

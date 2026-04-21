# SCOPE: both
"""Skill frontmatter routing loader (ADR-050 Per-Skill Routing Policy).

Loads a `routing:` block from the YAML frontmatter of a `SKILL.md` file and
returns a canonicalised `SkillRequirements` object that `lib/dispatch.py`
consumes.

Frontmatter schema (all fields optional, conservative defaults):

    ---
    name: sdd-design
    model: opus
    routing:
      tier: frontier | balanced | cheap
      need_vision: false
      need_long_context: true
      providers_preferred: [claude]      # whitelist — cascade built from this
      providers_excluded: [minimax]      # blacklist — removed from cascade
      fallback_on_rate_limit: true       # default true
      fallback_on_any_error: false       # default false (quality-sensitive)
      budget_max_usd_per_call: 1.00      # None = unlimited
    ---

Design invariants:
  - Backward-compatible: a missing `routing:` block yields `None`, dispatch
    falls back to the current uniform cascade.
  - No heavy deps: PyYAML only (already a transitive dep across the repo).
  - Parse errors never raise to callers — they return `None` + optional warning
    on stderr so a malformed frontmatter cannot break dispatch.

See:
  - `docs/adrs/ADR-050-per-skill-routing-policy.md`
  - `lib/dispatch.py::dispatch(skill_requirements=...)`
  - `tests/unit/test_skill_routing.py`
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:  # PyYAML is already required by other lib/* modules
    import yaml  # type: ignore
except ImportError:  # pragma: no cover — handled at call site
    yaml = None  # type: ignore


# Recognised tier labels (validated loosely — unknown tiers warned + accepted)
VALID_TIERS = ("frontier", "balanced", "cheap")


@dataclass
class SkillRequirements:
    """Canonical, dispatch-ready routing block parsed from skill frontmatter.

    Dataclass form is the public contract between `lib/skill_routing.py` and
    `lib/dispatch.py`. Every field has a safe default so partial frontmatter
    is never a fatal error.
    """

    tier: Optional[str] = None  # "frontier" | "balanced" | "cheap" | None
    need_vision: bool = False
    need_long_context: bool = False
    providers_preferred: list[str] = field(default_factory=list)
    providers_excluded: list[str] = field(default_factory=list)
    fallback_on_rate_limit: bool = True
    fallback_on_any_error: bool = False
    budget_max_usd_per_call: Optional[float] = None

    def resolve_providers(self, default_cascade: list[str]) -> list[str]:
        """Compute the effective cascade for this skill.

        Precedence:
          1. If `providers_preferred` is non-empty → use it as the cascade
             (subject to exclusions below).
          2. Otherwise → start from `default_cascade`.
          3. Remove anything in `providers_excluded`.
        """
        if self.providers_preferred:
            base = list(self.providers_preferred)
        else:
            base = list(default_cascade)
        if self.providers_excluded:
            excl = set(self.providers_excluded)
            base = [p for p in base if p not in excl]
        return base


def _extract_frontmatter(text: str) -> Optional[str]:
    """Return the YAML block between the first pair of `---` fences, or None.

    Accepts either `---` on its own line or after an HTML comment (`<!-- ... -->`)
    so files like `skills/sdd-explore/SKILL.md` (prefixed with `<!-- SCOPE: both -->`)
    still parse cleanly.
    """
    lines = text.splitlines()
    # Find the first '---' line (skipping blank + HTML comment lines)
    start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "---":
            start = i
            break
        if stripped == "" or stripped.startswith("<!--"):
            continue
        # First non-blank non-comment line is not a fence → no frontmatter
        return None
    if start is None:
        return None
    # Find the closing fence
    for j in range(start + 1, len(lines)):
        if lines[j].strip() == "---":
            return "\n".join(lines[start + 1 : j])
    return None


def parse_routing_block(frontmatter_yaml: dict) -> Optional[SkillRequirements]:
    """Given a parsed frontmatter dict, extract and canonicalise `routing:`.

    Returns `None` if no routing block is present. Returns a best-effort
    `SkillRequirements` on partial/malformed blocks (unknown keys silently
    ignored; wrong types coerced or dropped with a stderr warning).
    """
    if not isinstance(frontmatter_yaml, dict):
        return None
    routing = frontmatter_yaml.get("routing")
    if routing is None:
        return None
    if not isinstance(routing, dict):
        print(
            f"[skill_routing] WARN: 'routing:' is not a mapping ({type(routing).__name__}) — ignored",
            file=sys.stderr,
        )
        return None

    req = SkillRequirements()

    tier = routing.get("tier")
    if isinstance(tier, str):
        if tier not in VALID_TIERS:
            print(
                f"[skill_routing] WARN: unknown tier {tier!r} (valid: {VALID_TIERS})",
                file=sys.stderr,
            )
        req.tier = tier

    req.need_vision = bool(routing.get("need_vision", False))
    req.need_long_context = bool(routing.get("need_long_context", False))

    pref = routing.get("providers_preferred")
    if isinstance(pref, list):
        req.providers_preferred = [str(p) for p in pref if isinstance(p, str)]
    elif pref is not None:
        print(
            f"[skill_routing] WARN: providers_preferred must be a list (got {type(pref).__name__})",
            file=sys.stderr,
        )

    excl = routing.get("providers_excluded")
    if isinstance(excl, list):
        req.providers_excluded = [str(p) for p in excl if isinstance(p, str)]
    elif excl is not None:
        print(
            f"[skill_routing] WARN: providers_excluded must be a list (got {type(excl).__name__})",
            file=sys.stderr,
        )

    # Booleans default true/false per ADR-050 schema
    if "fallback_on_rate_limit" in routing:
        req.fallback_on_rate_limit = bool(routing["fallback_on_rate_limit"])
    if "fallback_on_any_error" in routing:
        req.fallback_on_any_error = bool(routing["fallback_on_any_error"])

    budget = routing.get("budget_max_usd_per_call")
    if budget is not None:
        try:
            req.budget_max_usd_per_call = float(budget)
        except (TypeError, ValueError):
            print(
                f"[skill_routing] WARN: budget_max_usd_per_call must be numeric "
                f"(got {budget!r})",
                file=sys.stderr,
            )

    return req


def load_skill_requirements(skill_md_path: str | Path) -> Optional[SkillRequirements]:
    """High-level helper: read `SKILL.md`, return `SkillRequirements` or None.

    Never raises. Returns `None` on:
      - File missing
      - PyYAML unavailable
      - No frontmatter at all
      - No `routing:` block in frontmatter
      - Malformed YAML
    """
    if yaml is None:
        return None
    path = Path(skill_md_path)
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    fm_text = _extract_frontmatter(text)
    if fm_text is None:
        return None
    try:
        fm = yaml.safe_load(fm_text)
    except yaml.YAMLError as e:
        print(f"[skill_routing] WARN: malformed YAML in {path}: {e}", file=sys.stderr)
        return None
    return parse_routing_block(fm if isinstance(fm, dict) else {})


def to_dispatch_dict(req: SkillRequirements) -> dict:
    """Serialise `SkillRequirements` into the dict shape `dispatch()` consumes.

    Kept as a helper so dispatch's public API can stay `dict`-typed
    (avoids leaking the dataclass through the public signature).
    """
    return {
        "tier": req.tier,
        "need_vision": req.need_vision,
        "need_long_context": req.need_long_context,
        "providers_preferred": list(req.providers_preferred),
        "providers_excluded": list(req.providers_excluded),
        "fallback_on_rate_limit": req.fallback_on_rate_limit,
        "fallback_on_any_error": req.fallback_on_any_error,
        "budget_max_usd_per_call": req.budget_max_usd_per_call,
    }

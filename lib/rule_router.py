# SCOPE: os-only
# scope: both
"""Rule Router — Auto-select agent-instruction rules from prompt context.

Analogous to ``lib/skill_router.py`` (ADR-174), but for rules under
``rules/`` and ``packages/*/rules/``. See ADR-179.

A *rule* in the Cognitive OS is one of:
  - ``enforcement: hook``           — auto-fired by a backing hook; the router
                                       deliberately skips these.
  - ``enforcement: agent-instruction`` — narrative guidance the orchestrator
                                       must "load on trigger". The router's job.
  - ``enforcement: hybrid``         — both surfaces present; routed.

Frontmatter shape::

    ---
    enforcement: agent-instruction
    routing_patterns:
      - pattern: "\\bacceptance criteria\\b"
        confidence: 0.92
      - pattern: "verify command"
        confidence: 0.80
    trigger_priority: high
    ---

Usage::

    from lib.rule_router import RuleRouter
    router = RuleRouter()
    matches = router.top_matches("does it have acceptance criteria?", n=3)
    for m in matches:
        print(m.invoke_command)
        # "Load rule [acceptance-criteria](rules/acceptance-criteria.md) before proceeding"

The router never raises on malformed frontmatter — it logs to stderr and
skips the rule. This is by design: a single bad rule must not break routing.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class RuleMatch:
    """A matched rule with confidence and reasoning."""

    rule_name: str
    rule_path: str  # repo-relative path, e.g. "rules/acceptance-criteria.md"
    confidence: float
    reason: str
    invoke_command: str  # human-readable instruction to load the rule

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.rule_name} (confidence={self.confidence:.2f}): {self.reason}"


@dataclass
class _RuleEntry:
    rule_name: str
    rule_path: Path  # absolute resolved path
    repo_relative: str
    enforcement: str  # "hook" | "agent-instruction" | "hybrid"
    trigger_priority: str  # "low" | "medium" | "high"
    patterns: List[Tuple[re.Pattern, float]]


# ---------------------------------------------------------------------------
# Frontmatter parsing — minimal, no hard dep on PyYAML
# ---------------------------------------------------------------------------

def _read_frontmatter_block(text: str) -> Optional[str]:
    """Return the YAML between the first two '---' lines, or None."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "---":
            start = i
            break
        if stripped.startswith("<!--") or stripped == "":
            continue
        # Non-comment, non-empty content before frontmatter — no frontmatter.
        return None
    if start is None or start >= len(lines):
        return None
    end = None
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None
    return "\n".join(lines[start + 1:end])


def _parse_frontmatter(text: str) -> Dict[str, Any]:
    block = _read_frontmatter_block(text)
    if block is None:
        return {}
    try:
        import yaml  # type: ignore[import]
        data = yaml.safe_load(block) or {}
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        pass

    # Minimal fallback parser — handles flat scalars + simple list-of-mappings.
    result: Dict[str, Any] = {}
    current_key: Optional[str] = None
    current_list: Optional[List[Any]] = None
    for raw_line in block.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # List item under current key
        if line.lstrip().startswith("- "):
            item_str = line.lstrip()[2:].strip()
            if current_list is None:
                current_list = []
                if current_key is not None:
                    result[current_key] = current_list
            if ":" in item_str:
                # Inline mapping like "pattern: foo, confidence: 0.8"
                item: Dict[str, Any] = {}
                # Try to split by top-level commas first, otherwise treat as one k:v
                # but we expect multi-line entries below — so handle inline only.
                for part in item_str.split(","):
                    part = part.strip()
                    if ":" in part:
                        k, v = part.split(":", 1)
                        item[k.strip()] = v.strip().strip('"').strip("'")
                current_list.append(item)
            else:
                current_list.append(item_str.strip('"').strip("'"))
            continue
        # Sub-key under last list item: "    pattern: ..."
        m_sub = re.match(r"^\s+(\w[\w_-]*)\s*:\s*(.*)$", line)
        if m_sub and current_list and isinstance(current_list[-1], dict):
            k, v = m_sub.group(1), m_sub.group(2).strip().strip('"').strip("'")
            current_list[-1][k] = v
            continue
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            current_key = key
            current_list = None
            if value:
                result[key] = value.strip('"').strip("'")
            else:
                result[key] = ""
    return result


# ---------------------------------------------------------------------------
# Rule loading
# ---------------------------------------------------------------------------

def _detect_project_root() -> Path:
    here = Path(__file__).resolve()
    return here.parent.parent  # lib/rule_router.py -> repo root


def _enumerate_rule_paths(project_root: Path) -> List[Path]:
    """Return every rules/*.md across project + packages, deduped by realpath."""
    seen: Set[str] = set()
    found: List[Path] = []
    candidates: List[Path] = []
    rules_root = project_root / "rules"
    if rules_root.is_dir():
        candidates.extend(sorted(rules_root.glob("*.md")))
    packages = project_root / "packages"
    if packages.is_dir():
        for pkg in sorted(packages.iterdir()):
            pkg_rules = pkg / "rules"
            if pkg_rules.is_dir():
                candidates.extend(sorted(pkg_rules.glob("*.md")))
    for path in candidates:
        try:
            real = os.path.realpath(str(path))
        except OSError:
            continue
        if real in seen:
            continue
        seen.add(real)
        # Skip index/aggregate docs — we only route real rules.
        if path.name.upper() in {"RULES-COMPACT.MD", "ROADMAP.MD", "README.MD"}:
            continue
        found.append(path)
    return found


def _compile_patterns(
    raw: Any, source: Path
) -> List[Tuple[re.Pattern, float]]:
    if not isinstance(raw, list):
        return []
    out: List[Tuple[re.Pattern, float]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        pat = entry.get("pattern")
        if not pat:
            continue
        try:
            conf = float(entry.get("confidence", 0.80))
        except (TypeError, ValueError):
            conf = 0.80
        try:
            out.append((re.compile(str(pat), re.IGNORECASE), conf))
        except re.error as exc:
            print(
                f"[rule_router] WARNING: bad pattern in {source}: {exc}",
                file=sys.stderr,
            )
    return out


def _rule_to_entry(path: Path, project_root: Path) -> Optional[_RuleEntry]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    fm = _parse_frontmatter(text)
    if not fm:
        return None
    enforcement = str(fm.get("enforcement", "")).strip().lower()
    if enforcement not in {"hook", "agent-instruction", "hybrid"}:
        return None
    patterns = _compile_patterns(fm.get("routing_patterns"), path)
    trigger_priority = str(fm.get("trigger_priority", "medium")).strip().lower()
    if trigger_priority not in {"low", "medium", "high"}:
        trigger_priority = "medium"
    rule_name = path.stem
    try:
        repo_rel = str(path.resolve().relative_to(project_root))
    except ValueError:
        repo_rel = str(path)
    return _RuleEntry(
        rule_name=rule_name,
        rule_path=path,
        repo_relative=repo_rel,
        enforcement=enforcement,
        trigger_priority=trigger_priority,
        patterns=patterns,
    )


# ---------------------------------------------------------------------------
# Public router
# ---------------------------------------------------------------------------

class RuleRouter:
    """Match user prompts to agent-instruction rules.

    Hook-enforced rules are filtered out — they auto-fire and need no
    orchestrator nudge.
    """

    # Slight bonus for "high" priority rules so they edge out equal-confidence
    # competitors. Capped so a low-confidence high-priority match never beats
    # a high-confidence medium-priority one.
    _PRIORITY_BONUS = {"low": 0.0, "medium": 0.0, "high": 0.05}

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self._project_root = (project_root or _detect_project_root()).resolve()
        self._entries: List[_RuleEntry] = []
        self._all_loaded: List[_RuleEntry] = []
        self._reload()

    def _reload(self) -> None:
        all_loaded: List[_RuleEntry] = []
        routable: List[_RuleEntry] = []
        for path in _enumerate_rule_paths(self._project_root):
            entry = _rule_to_entry(path, self._project_root)
            if entry is None:
                continue
            all_loaded.append(entry)
            if entry.enforcement == "hook":
                continue  # hook-enforced rules are not routed
            if not entry.patterns:
                continue
            routable.append(entry)
        self._all_loaded = all_loaded
        self._entries = routable

    @property
    def loaded_rule_count(self) -> int:
        return len(self._all_loaded)

    @property
    def routable_rule_count(self) -> int:
        return len(self._entries)

    def all_loaded(self) -> List[_RuleEntry]:
        return list(self._all_loaded)

    def _score(self, entry: _RuleEntry, text: str) -> float:
        best = 0.0
        for compiled, base in entry.patterns:
            if compiled.search(text):
                if base > best:
                    best = base
        if best <= 0.0:
            return 0.0
        bonus = self._PRIORITY_BONUS.get(entry.trigger_priority, 0.0)
        return min(1.0, best + bonus)

    def _to_match(self, entry: _RuleEntry, score: float) -> RuleMatch:
        invoke = (
            f"Load rule [{entry.rule_name}]({entry.repo_relative}) before proceeding"
        )
        reason = f"Auto-routed via {entry.rule_name} frontmatter"
        return RuleMatch(
            rule_name=entry.rule_name,
            rule_path=entry.repo_relative,
            confidence=round(score, 4),
            reason=reason,
            invoke_command=invoke,
        )

    def best_match(self, prompt: str) -> Optional[RuleMatch]:
        if not prompt:
            return None
        text = prompt
        best: Optional[Tuple[float, _RuleEntry]] = None
        for entry in self._entries:
            score = self._score(entry, text)
            if score <= 0.0:
                continue
            if best is None or score > best[0]:
                best = (score, entry)
        if best is None:
            return None
        return self._to_match(best[1], best[0])

    def top_matches(
        self,
        prompt: str,
        n: int = 3,
        min_confidence: float = 0.70,
    ) -> List[RuleMatch]:
        if not prompt:
            return []
        scored: List[Tuple[float, _RuleEntry]] = []
        for entry in self._entries:
            score = self._score(entry, prompt)
            if score >= min_confidence:
                scored.append((score, entry))
        # Highest confidence first; rule_name tiebreaker for stability.
        scored.sort(key=lambda x: (-x[0], x[1].rule_name))
        return [self._to_match(e, s) for s, e in scored[:n]]


__all__ = ["RuleRouter", "RuleMatch"]

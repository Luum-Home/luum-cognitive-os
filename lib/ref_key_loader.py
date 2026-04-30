# SCOPE: both
r"""Ref-key loader — ADR-027 Phase 2.

Resolves `[\`ref-key\`]` markers in text to the corresponding rule file
content under `rules/*.md`. Enables contextual rule inclusion: compact
indices (like `rules/RULES-COMPACT.md` or `~/.claude/CLAUDE.md`) cite
a key by name; this loader expands the key on-demand when the orchestrator
or a hook needs the full rule.

Contract:
  - Input: text containing zero or more markers of the form [`<key>`]
    (backtick-wrapped). Nested markers are NOT recursively expanded by
    default (explicit max_depth controls this).
  - Resolution: <key> maps to rules/<key>.md OR to an entry in an
    optional overrides mapping.
  - Missing keys: logged as MetricEvent
    (source=ref_key_loader, event_type=miss) to
    .cognitive-os/metrics/ref-key-misses.jsonl; the original marker is
    PRESERVED in output (callers decide whether to treat a miss as an
    error).
  - Hits: returned as {key: content} by `resolve()`, substituted inline
    by `expand()`.

Tier filtering (ADR-075 Stage 2):
  Rules carry a `<!-- TIER: N -->` comment on their first line.
  When `tier_filter` is provided to `expand()`, only rules whose tier is
  in the filter set are expanded; others keep their marker intact.
  Rules without frontmatter are treated as Tier-1 (safe default).

Public API:
  find_ref_keys(text)                        -> list[str]
  resolve(text, overrides=None)              -> dict[str, str | None]  (None = miss)
  expand(text, overrides=None,
         max_depth=1, fence=None,
         tier_filter=None)                   -> str
  _read_tier(rule_path)                      -> int

Python 3.9+ stdlib + lib.metric_event.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

# Pattern: [`word-with-hyphens`] — enforce at least 2 chars, no whitespace,
# allow letters, digits, hyphens, underscores, dots.
_REF_KEY_RE = re.compile(r"\[`([A-Za-z][A-Za-z0-9_.\-]{0,80})`\]")

# Matches the tier frontmatter comment on line 1: <!-- TIER: N -->
_TIER_RE = re.compile(r"^<!--\s*TIER:\s*(\d+)\s*-->")


def _project_root() -> Path:
    return Path(
        os.environ.get(
            "COGNITIVE_OS_PROJECT_DIR",
            os.environ.get(
                "CODEX_PROJECT_DIR",
                os.environ.get(
                    "CLAUDE_PROJECT_DIR",
                    str(Path(__file__).resolve().parent.parent),
                ),
            ),
        )
    )


def _rules_dir() -> Path:
    return _project_root() / "rules"


def _miss_log_path() -> Path:
    return _project_root() / ".cognitive-os" / "metrics" / "ref-key-misses.jsonl"


def _read_tier(rule_path: Path) -> int:
    """Read only line 1 of a rule file and return its tier (0, 1, or 2).

    If no ``<!-- TIER: N -->`` frontmatter is present, returns 1 (safe default).
    Never raises; returns 1 on any I/O error.
    """
    try:
        with rule_path.open(encoding="utf-8") as fh:
            first_line = fh.readline()
        m = _TIER_RE.match(first_line)
        if m:
            return int(m.group(1))
    except OSError:
        pass
    return 1  # default: Tier-1


def find_ref_keys(text: str) -> List[str]:
    """Return a de-duplicated, order-preserving list of ref-keys in text."""
    if not isinstance(text, str) or not text:
        return []
    seen: Dict[str, None] = {}
    for m in _REF_KEY_RE.finditer(text):
        seen.setdefault(m.group(1), None)
    return list(seen.keys())


def _load_rule(key: str, overrides: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Resolve a single key to content. overrides wins over rules/<key>.md.

    Returns None if neither source has the key.
    """
    if overrides and key in overrides:
        return overrides[key]
    path = _rules_dir() / f"{key}.md"
    if path.is_file():
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None
    return None


def _emit_miss(key: str, source_hint: str = "") -> None:
    """Append a miss event to metrics. Never raises."""
    try:
        from lib.metric_event import MetricEvent, append_event
    except Exception:
        return
    try:
        ev = MetricEvent(
            source="ref_key_loader",
            event_type="miss",
            severity="warn",
            payload={"key": key, "source_hint": source_hint[:200]},
        )
        append_event(str(_miss_log_path()), ev)
    except Exception:
        # append_event already degrades; this is the safety net.
        pass


def resolve(
    text: str,
    overrides: Optional[Dict[str, str]] = None,
) -> Dict[str, Optional[str]]:
    """Resolve all ref-keys found in text.

    Returns a dict {key: content_or_none}. Misses keep the key with None
    as value. Misses are also logged.
    """
    out: Dict[str, Optional[str]] = {}
    keys = find_ref_keys(text)
    for k in keys:
        content = _load_rule(k, overrides)
        out[k] = content
        if content is None:
            _emit_miss(k, source_hint=text)
    return out


def expand(
    text: str,
    overrides: Optional[Dict[str, str]] = None,
    max_depth: int = 1,
    fence: Optional[str] = None,
    tier_filter: Optional[Set[int]] = None,
) -> str:
    """Expand [`key`] markers inline with the referenced rule content.

    Args:
        text: input text containing ref-key markers.
        overrides: optional {key: content} mapping.
        max_depth: how many expansion passes to perform. 1 = do not expand
                   refs that appear inside expanded content.
        fence: optional string wrapper placed around inserted content so
               callers can visually distinguish inlined text (e.g. "\\n---\\n").
        tier_filter: when provided, only expand rules whose ``<!-- TIER: N -->``
                     frontmatter tier is in this set.  Rules without frontmatter
                     are treated as Tier-1.  When None (default), all rules are
                     expanded (backward-compatible behaviour).

    Misses keep the original `[\\`key\\`]` marker intact.
    Rules excluded by tier_filter also keep their marker intact.
    """
    if not isinstance(text, str) or not text:
        return text
    if max_depth < 1:
        return text

    current = text
    for _ in range(max_depth):
        resolved = resolve(current, overrides)
        if not resolved:
            break

        def _sub(match: "re.Match[str]", _resolved: Dict = resolved) -> str:
            key = match.group(1)
            content = _resolved.get(key)
            if content is None:
                return match.group(0)  # preserve the marker on miss

            # Tier filtering: if a filter is active, check the rule's tier.
            if tier_filter is not None:
                rule_path = _rules_dir() / f"{key}.md"
                # overrides bypass tier filtering (they have no file to read)
                if not (overrides and key in overrides):
                    if rule_path.is_file():
                        tier = _read_tier(rule_path)
                        if tier not in tier_filter:
                            return match.group(0)  # keep marker, skip expansion

            if fence:
                return f"{fence}{content}{fence}"
            return content

        new_text = _REF_KEY_RE.sub(_sub, current)
        if new_text == current:
            break
        current = new_text
    return current


__all__ = [
    "find_ref_keys",
    "resolve",
    "expand",
    "_read_tier",
]

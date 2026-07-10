"""
ADR-263 — Tool Budget Catalog
Per-tool char thresholds derived from luum truncation-events.jsonl distribution.

Source-pattern: .private/external-pattern-research/annex-b-cost-budget.md §B1 (clean-room)
Thresholds are NOT copied from the reference catalog; they are independently
derived from the real distribution of tool outputs in this repository.

Derivation methodology (see ADR-263 §2):
- Read: Python files in this repo have median ~3 500 chars; p90 ~6 500 chars.
  preview_max set at p50 (3 000), reference_max at p25 (800).
  trim_threshold (4 500) = p75 — histéresis buffer to avoid cutting near-threshold files.
- Bash: grep/find outputs cluster at 800–1 500 chars.
  preview_max = 1 500 (p75), reference_max = 500 (p25), trim_threshold = 2 200 (p90).
- WebFetch: high variance, long tail.
  preview_max = 2 500, reference_max = 600, trim_threshold = 3 800.
- Grep: pattern match outputs are typically compact.
  preview_max = 1 200, reference_max = 400, trim_threshold = 1 800.
- _default: mirrors Bash conservative profile.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolBudgetEntry:
    """Threshold configuration for a single tool type."""

    # Maximum chars to include when mode = PREVIEW
    preview_max_chars: int

    # Maximum chars to include when mode = REFERENCE_ONLY (before replacing with pointer)
    reference_max_chars: int

    # Hysteresis: only trigger preview truncation if output > this value.
    # Prevents cutting near-threshold outputs unnecessarily.
    trim_threshold_chars: int


# ---------------------------------------------------------------------------
# Catalog: thresholds calibrated from luum truncation-events.jsonl
# ---------------------------------------------------------------------------

CATALOG: dict[str, ToolBudgetEntry] = {
    "Bash": ToolBudgetEntry(
        preview_max_chars=1500,
        reference_max_chars=500,
        trim_threshold_chars=2200,
    ),
    "Read": ToolBudgetEntry(
        preview_max_chars=3000,
        reference_max_chars=800,
        trim_threshold_chars=4500,
    ),
    "WebFetch": ToolBudgetEntry(
        preview_max_chars=2500,
        reference_max_chars=600,
        trim_threshold_chars=3800,
    ),
    "Grep": ToolBudgetEntry(
        preview_max_chars=1200,
        reference_max_chars=400,
        trim_threshold_chars=1800,
    ),
    "_default": ToolBudgetEntry(
        preview_max_chars=1500,
        reference_max_chars=500,
        trim_threshold_chars=2200,
    ),
}


def get_thresholds(tool_name: str) -> tuple[int, int]:
    """
    Return (preview_max_chars, reference_max_chars) for the given tool.
    Falls back to _default if the tool is not in the catalog.
    """
    entry = CATALOG.get(tool_name) or CATALOG["_default"]
    return entry.preview_max_chars, entry.reference_max_chars


def get_entry(tool_name: str) -> ToolBudgetEntry:
    """Return the full ToolBudgetEntry for a tool, falling back to _default."""
    return CATALOG.get(tool_name) or CATALOG["_default"]

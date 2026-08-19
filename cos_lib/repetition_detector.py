# SCOPE: both
"""Repetition Detector -- finds repeated tool-call patterns for auto-skill generation.

Reads skill-metrics.jsonl and surfaces sequences worth converting into skills.
Python 3.9+, stdlib only.

FIELD REALITY, measured 2026-08-19. The producer (packages/skill-governance/
hooks/skill-tracker.sh, PostToolUse matcher Agent) writes exactly:
    timestamp, skill, success, duration_ms, tokens, model

This module used to read `skill_name` and `tool_calls`. Neither is written by
anyone: `skill_name` is spelled `skill`, and `tool_calls` has NO producer in the
repo at all. Both readers therefore returned [] on every row of a 257-row file,
and format_report printed "(none detected)" -- which reads as "we looked and
found nothing" when the truth was "we never had the data". A zero that is not
emitted is not a zero, it is a hole.

`skill` also carries the sentinel "unknown-agent" on 98.4% of rows: a deliberate
marker (commit bc04ff86b) meaning "an Agent run nobody can attribute to a skill".
It is NOT a skill name and is excluded here; counting it as one would invent a
skill called unknown-agent, which is the bug that filled skill-feedback.jsonl
with 131 rows named after the operator.

Call source_status() to learn which fields actually have data before trusting a
zero from this module.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


class RepetitionDetector:
    def __init__(self, metrics_dir: str = ".cognitive-os/metrics") -> None:
        self._file = Path(metrics_dir) / "skill-metrics.jsonl"

    SENTINEL_SKILL = "unknown-agent"

    def source_status(self) -> dict[str, Any]:
        """Which required fields carry data. Read this before believing a zero."""
        entries = self._load()
        with_calls = sum(1 for e in entries if e.get("tool_calls"))
        with_skill = sum(
            1 for e in entries
            if e.get("skill") and e.get("skill") != self.SENTINEL_SKILL
        )
        return {
            "rows": len(entries),
            "rows_with_tool_calls": with_calls,
            "rows_with_named_skill": with_skill,
            "sequences_measurable": with_calls > 0,
            "chains_measurable": with_skill > 0,
        }

    def _load(self) -> list[dict[str, Any]]:
        if not self._file.exists():
            return []
        entries: list[dict[str, Any]] = []
        try:
            for line in self._file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        except (json.JSONDecodeError, OSError):
            pass
        return entries

    @staticmethod
    def _ngrams(seq: list[str], n: int) -> list[tuple[str, ...]]:
        return [tuple(seq[i : i + n]) for i in range(len(seq) - n + 1)]

    def analyze_tool_sequences(
        self, min_length: int = 3, min_occurrences: int = 3
    ) -> list[dict[str, Any]]:
        """Find repeated tool-call sub-sequences. Returns list sorted by savings desc."""
        entries = self._load()
        if not entries:
            return []

        occ: dict[tuple[str, ...], list[dict]] = defaultdict(list)
        for e in entries:
            calls: list[str] = e.get("tool_calls", [])
            for n in range(min_length, len(calls) + 1):
                for gram in self._ngrams(calls, n):
                    occ[gram].append({"tokens": e.get("tokens", 0),
                                      "context": e.get("skill", "")})

        # Keep only sequences that meet threshold; drop sub-sequences of longer matches
        qualified = {g: v for g, v in occ.items() if len(v) >= min_occurrences}
        to_drop: set[tuple] = set()
        keys = sorted(qualified, key=len, reverse=True)
        for i, long in enumerate(keys):
            for short in keys[i + 1 :]:
                if len(short) < len(long) and any(
                    long[j : j + len(short)] == short
                    for j in range(len(long) - len(short) + 1)
                ):
                    to_drop.add(short)

        patterns: list[dict[str, Any]] = []
        for gram, info in qualified.items():
            if gram in to_drop:
                continue
            avg = sum(o["tokens"] for o in info) / len(info)
            savings = max(0, avg - 500) * len(info)
            patterns.append({
                "sequence": list(gram),
                "occurrences": len(info),
                "avg_tokens": round(avg),
                "potential_savings": round(savings),
                "example_context": info[0]["context"],
            })

        patterns.sort(key=lambda p: p["potential_savings"], reverse=True)
        return patterns

    def analyze_skill_chains(self, min_occurrences: int = 3) -> list[dict[str, Any]]:
        """Find repeated consecutive skill invocation chains."""
        entries = self._load()
        skills = [
            e.get("skill", "") for e in entries
            if e.get("skill") and e.get("skill") != self.SENTINEL_SKILL
        ]
        if not skills:
            return []

        counts: dict[tuple[str, ...], int] = defaultdict(int)
        for n in range(2, len(skills) + 1):
            for gram in self._ngrams(skills, n):
                counts[gram] += 1

        chains = [
            {"chain": list(g), "occurrences": c,
             "suggestion": f"Create meta-skill combining these {len(g)} skills"}
            for g, c in counts.items() if c >= min_occurrences
        ]
        chains.sort(key=lambda c: c["occurrences"], reverse=True)
        return chains

    def estimate_savings(self, patterns: list[dict[str, Any]]) -> dict[str, int]:
        """Total token savings; monthly projection assumes 5 invocations/pattern."""
        total = sum(p.get("potential_savings", 0) for p in patterns)
        return {"patterns_found": len(patterns),
                "total_savings_tokens": total,
                "savings_per_month": total * 5}

    def suggest_skill_names(self, pattern: dict[str, Any]) -> list[str]:
        """Suggest skill names from tool sequence and context."""
        hints = {"Grep": "search", "Read": "read", "Edit": "edit",
                 "Write": "write", "Bash": "run"}
        parts = [hints.get(t, t.lower()) for t in pattern.get("sequence", [])]
        base = "-".join(parts[:3])
        ctx = pattern.get("example_context", "")
        names = [base]
        if ctx:
            names.append(ctx.replace(" ", "-").replace("_", "-").lower()[:30] + "-workflow")
        names.append(f"auto-{base}")
        return names

    def format_report(self, patterns: list[dict], chains: list[dict]) -> str:
        """Human-readable report with savings summary."""
        s = self.estimate_savings(patterns)
        status = self.source_status()
        lines = [
            "# Repetition Detector Report", "",
            "## Summary",
            f"- Patterns found: {s['patterns_found']}",
            f"- Total potential savings: {s['total_savings_tokens']:,} tokens",
            f"- Estimated monthly savings: {s['savings_per_month']:,} tokens",
            "", "## Repeated Tool Sequences",
        ]
        if not patterns:
            lines.append(
                "  (none detected)" if status["sequences_measurable"]
                else "  (NO DATA SOURCE: no row carries `tool_calls`; nothing "
                     "in this repo writes that field, so this is not a zero)"
            )
        for p in patterns:
            lines.append(f"  - {' → '.join(p['sequence'])} "
                         f"({p['occurrences']}x, saves ~{p['potential_savings']:,} tokens)")
            lines.append(f"    Suggested skill: {self.suggest_skill_names(p)[0]}")

        lines += ["", "## Repeated Skill Chains"]
        if not chains:
            lines.append(
                "  (none detected)" if status["chains_measurable"]
                else "  (NO DATA SOURCE: every row's `skill` is the "
                     "\"unknown-agent\" sentinel or absent)"
            )
        for c in chains:
            lines.append(f"  - {' → '.join(c['chain'])} "
                         f"({c['occurrences']}x) — {c['suggestion']}")
        return "\n".join(lines)

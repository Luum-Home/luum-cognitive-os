# scope: both
"""Repetition Detector -- finds repeated tool-call patterns for auto-skill generation.

Reads skill-metrics.jsonl (fields: skill_name, tool_calls, tokens, duration_ms, success)
and surfaces sequences worth converting into skills (~5K tokens saved per future call).
Python 3.9+, stdlib only.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


class RepetitionDetector:
    def __init__(self, metrics_dir: str = ".cognitive-os/metrics") -> None:
        self._file = Path(metrics_dir) / "skill-metrics.jsonl"

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
                                      "context": e.get("skill_name", "")})

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
        skills = [e.get("skill_name", "") for e in entries if e.get("skill_name")]
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
        lines = [
            "# Repetition Detector Report", "",
            "## Summary",
            f"- Patterns found: {s['patterns_found']}",
            f"- Total potential savings: {s['total_savings_tokens']:,} tokens",
            f"- Estimated monthly savings: {s['savings_per_month']:,} tokens",
            "", "## Repeated Tool Sequences",
        ]
        if not patterns:
            lines.append("  (none detected)")
        for p in patterns:
            lines.append(f"  - {' → '.join(p['sequence'])} "
                         f"({p['occurrences']}x, saves ~{p['potential_savings']:,} tokens)")
            lines.append(f"    Suggested skill: {self.suggest_skill_names(p)[0]}")

        lines += ["", "## Repeated Skill Chains"]
        if not chains:
            lines.append("  (none detected)")
        for c in chains:
            lines.append(f"  - {' → '.join(c['chain'])} "
                         f"({c['occurrences']}x) — {c['suggestion']}")
        return "\n".join(lines)

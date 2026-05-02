#!/usr/bin/env python3
# SCOPE: os-only
"""Generate one executive summary for the agentic mastery program."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / ".cognitive-os" / "reports"
OUTPUT = REPORTS / "agentic-mastery-summary.md"

SECTIONS = [
    ("Safety", ROOT / "docs" / "security" / "lethal-trifecta-gate.md"),
    ("ACI", ROOT / "docs" / "architecture" / "agent-computer-interface.md"),
    ("Trajectory", ROOT / "docs" / "architecture" / "agent-trajectory-schema.md"),
    ("Skill efficacy", REPORTS / "skill-efficacy-smoke-report.md"),
    ("Runtime benchmark", REPORTS / "runtime-benchmark-leaderboard.md"),
    ("Adversarial generalization", REPORTS / "adversarial-generalization-report.md"),
]


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    lines = ["# Agentic Mastery Summary", "", "| Area | Status | Evidence |", "|---|---|---|"]
    for name, path in SECTIONS:
        status = "present" if path.exists() else "missing"
        lines.append(f"| {name} | {status} | `{path.relative_to(ROOT)}` |")
    lines.extend([
        "",
        "## Operator command",
        "",
        "```bash",
        "make test-agentic-mastery",
        "```",
        "",
        "This summary is generated without model calls or external tool dependencies.",
    ])
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(OUTPUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

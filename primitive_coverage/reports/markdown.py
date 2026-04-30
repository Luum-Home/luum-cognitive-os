from __future__ import annotations

from primitive_coverage.model import CoverageReport


def render_markdown(report: CoverageReport) -> str:
    summary = report.summary()
    lines = [
        "# Primitive Coverage Report",
        "",
        f"Adapter: `{report.adapter}`",
        f"Targets: {summary['targets']}",
        f"Average score: {summary['average_score']}",
        "",
        "## Families",
        "",
        "| Family | Count | Average Score | Statuses |",
        "|---|---:|---:|---|",
    ]
    for family, info in summary["families"].items():
        statuses = ", ".join(f"{key}:{value}" for key, value in sorted(info["statuses"].items()))
        lines.append(f"| {family} | {info['count']} | {info['average_score']} | {statuses} |")
    lines.extend(["", "## Rows", "", "| Primitive | Score | Status | Gaps |", "|---|---:|---|---|"])
    for row in sorted(report.rows, key=lambda item: (item.family, item.path)):
        gaps = ", ".join(row.gaps)
        lines.append(f"| `{row.primitive_id}` | {row.score} | {row.status} | {gaps} |")
    return "\n".join(lines) + "\n"

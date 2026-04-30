#!/usr/bin/env python3
"""Generate a periodic primitive gap snapshot for Cognitive OS.

The snapshot is intentionally heuristic. It answers: which primitive families are
likely drifting toward real behavior, and which need row-level audit next?
"""

from __future__ import annotations

import argparse
import math
import json
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

TEXT_SUFFIXES = {".py", ".sh", ".md", ".json", ".yaml", ".yml", ".toml", ".txt"}
GENERATED_SNAPSHOT_BASENAMES = {
    "primitive-gap-latest.json",
    "primitive-gap-latest.md",
    "primitive-gap-regressions.md",
    "primitive-gap-history.jsonl",
}


@dataclass(frozen=True)
class PrimitiveFamilySnapshot:
    family: str
    total: int
    proven_signal: int
    partial_signal: int
    aspirational_signal: int
    evidence: str
    severity: str
    next_action: str


@dataclass(frozen=True)
class Snapshot:
    timestamp: str
    overall_risk: str
    families: list[PrimitiveFamilySnapshot]
    hook_latency: dict[str, int | None]


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except OSError:
        return ""


def text_files(root: Path, paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for item in paths:
        base = root / item
        if base.is_file() and base.suffix in TEXT_SUFFIXES:
            files.append(base)
        elif base.is_dir():
            for path in base.rglob("*"):
                if ".git" in path.parts or "__pycache__" in path.parts:
                    continue
                if path.name in GENERATED_SNAPSHOT_BASENAMES:
                    continue
                if path.is_file() and path.suffix in TEXT_SUFFIXES and path.stat().st_size < 2_000_000:
                    files.append(path)
    return files


def combined_text(root: Path, paths: list[str]) -> str:
    return "\n".join(read_text(path) for path in text_files(root, paths))


def hook_latency(root: Path) -> dict[str, int | None]:
    path = root / ".cognitive-os/metrics/hook-timing.jsonl"
    durations: list[int] = []
    if not path.exists():
        return {"events": 0, "p50_ms": None, "p95_ms": None, "max_ms": None}
    for line in read_text(path).splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        duration = item.get("duration_ms")
        if isinstance(duration, int | float):
            durations.append(int(duration))
    if not durations:
        return {"events": 0, "p50_ms": None, "p95_ms": None, "max_ms": None}
    durations.sort()
    p95_index = min(len(durations) - 1, max(0, math.ceil(len(durations) * 0.95) - 1))
    return {
        "events": len(durations),
        "p50_ms": int(statistics.median(durations)),
        "p95_ms": durations[p95_index],
        "max_ms": durations[-1],
    }


def collect(root: Path) -> Snapshot:
    settings = read_text(root / ".claude/settings.json")
    tests_text = combined_text(root, ["tests"])
    runtime_text = combined_text(root, ["hooks", "scripts", "lib", "cmd", "cognitive-os.yaml", ".github/workflows"])
    hooks = sorted((root / "hooks").glob("*.sh"))
    registered_hooks = [path for path in hooks if path.name in settings]
    tested_hooks = [path for path in hooks if path.name in tests_text]
    proven_hooks = [path for path in hooks if path in registered_hooks and path in tested_hooks]

    skills = sorted((root / "skills").glob("*/SKILL.md"))
    skill_names = [path.parent.name for path in skills]
    invoked_skills = [name for name in skill_names if name in runtime_text]
    tested_skills = [name for name in skill_names if name in tests_text]
    proven_skills = sorted(set(invoked_skills) & set(tested_skills))

    rules = sorted((root / "rules").glob("*.md"))
    rules_with_tier = [path for path in rules if "<!-- TIER:" in read_text(path)[:500]]
    rules_tested = [path for path in rules if path.name in tests_text or path.stem in tests_text]

    metrics = sorted((root / ".cognitive-os/metrics").glob("*.jsonl"))
    nonempty_metrics = [path for path in metrics if path.stat().st_size > 0]

    adrs = sorted((root / "docs/adrs").glob("ADR-*.md"))
    docs = sorted((root / "docs").rglob("*.md"))
    adr_numbers = [path.stem.split("-", 2)[1] for path in adrs if "-" in path.stem]
    adrs_with_proof = [number for number in adr_numbers if f"ADR-{number}" in tests_text or f"ADR-{number}" in runtime_text]

    memory_files = [
        *sorted((root / "lib").glob("*memory*.py")),
        *sorted((root / "hooks").glob("*memory*.sh")),
        *sorted((root / "skills").glob("*memory*/SKILL.md")),
    ]
    memory_referenced = [path for path in memory_files if path.name in runtime_text or path.stem in tests_text]

    mcp_files = [path for path in text_files(root, [".claude/settings.json", "docs", "rules", "skills", "hooks", "lib", "scripts"]) if "mcp" in read_text(path).lower()]
    mcp_tested = [path for path in mcp_files if path.name in tests_text]

    projection_files = [
        root / "cognitive-os.yaml",
        *sorted((root / "scripts").glob("*project*settings*")),
        *sorted((root / "scripts").glob("*projection*")),
        *sorted((root / "cmd").rglob("*projection*")),
    ]
    projection_existing = [path for path in projection_files if path.exists()]
    projection_tested = [path for path in projection_existing if path.name in tests_text]

    test_files = sorted((root / "tests").rglob("test_*.py"))
    quality_tests = [path for path in test_files if "quality" in path.parts or "audit" in path.parts or "contract" in path.parts]

    families = [
        PrimitiveFamilySnapshot(
            family="hooks",
            total=len(hooks),
            proven_signal=len(proven_hooks),
            partial_signal=len(set(registered_hooks) | set(tested_hooks)),
            aspirational_signal=len([path for path in hooks if path not in set(registered_hooks) | set(tested_hooks)]),
            evidence=f"registered={len(registered_hooks)} tested={len(tested_hooks)} both={len(proven_hooks)}",
            severity="high" if len(proven_hooks) < max(1, len(hooks) // 2) else "medium",
            next_action="row-audit hook lifecycle, metrics, consumers, and latency",
        ),
        PrimitiveFamilySnapshot(
            family="skills",
            total=len(skills),
            proven_signal=len(proven_skills),
            partial_signal=len(set(invoked_skills) | set(tested_skills)),
            aspirational_signal=len([name for name in skill_names if name not in set(invoked_skills) | set(tested_skills)]),
            evidence=f"runtime-mentioned={len(set(invoked_skills))} tested={len(set(tested_skills))} both={len(proven_skills)}",
            severity="high" if len(proven_skills) < max(1, len(skills) // 3) else "medium",
            next_action="cluster skills by purpose and identify manual-only or duplicate skills",
        ),
        PrimitiveFamilySnapshot(
            family="rules",
            total=len(rules),
            proven_signal=len(rules_tested),
            partial_signal=len(rules_with_tier),
            aspirational_signal=len([path for path in rules if path not in rules_tested and path not in rules_with_tier]),
            evidence=f"tier-comment={len(rules_with_tier)} tested-or-mentioned={len(rules_tested)}",
            severity="high" if len(rules_with_tier) < len(rules) else "medium",
            next_action="verify tier/load reality using lib/ref_key_loader.py semantics",
        ),
        PrimitiveFamilySnapshot(
            family="memory",
            total=len(memory_files),
            proven_signal=len(memory_referenced),
            partial_signal=len(memory_files),
            aspirational_signal=max(0, len(memory_files) - len(memory_referenced)),
            evidence=f"memory-named={len(memory_files)} runtime-or-test-referenced={len(memory_referenced)}",
            severity="high",
            next_action="prove automatic save/read/consume loop across sessions",
        ),
        PrimitiveFamilySnapshot(
            family="mcp_tools",
            total=len(set(mcp_files)),
            proven_signal=len(set(mcp_tested)),
            partial_signal=len(set(mcp_files)),
            aspirational_signal=max(0, len(set(mcp_files)) - len(set(mcp_tested))),
            evidence=f"mcp-mentioned-files={len(set(mcp_files))} test-mentioned-files={len(set(mcp_tested))}",
            severity="high",
            next_action="separate installed, optional, reference-only, and missing integrations",
        ),
        PrimitiveFamilySnapshot(
            family="config_projection",
            total=len(projection_existing),
            proven_signal=len(projection_tested),
            partial_signal=len(projection_existing),
            aspirational_signal=max(0, len(projection_existing) - len(projection_tested)),
            evidence=f"projection-files={len(projection_existing)} test-mentioned={len(projection_tested)}",
            severity="high",
            next_action="map config keys to readers and projected driver outputs",
        ),
        PrimitiveFamilySnapshot(
            family="metrics",
            total=len(metrics),
            proven_signal=len(nonempty_metrics),
            partial_signal=len(metrics),
            aspirational_signal=len(metrics) - len(nonempty_metrics),
            evidence=f"jsonl={len(metrics)} nonempty={len(nonempty_metrics)} empty={len(metrics) - len(nonempty_metrics)}",
            severity="medium" if nonempty_metrics else "high",
            next_action="assign owners and consumers to every metric stream",
        ),
        PrimitiveFamilySnapshot(
            family="tests_quality_gates",
            total=len(test_files),
            proven_signal=len(quality_tests),
            partial_signal=len(test_files),
            aspirational_signal=0,
            evidence=f"test_py={len(test_files)} audit-contract-quality={len(quality_tests)}",
            severity="high",
            next_action="run test-quality audit and map theater tests to primitives",
        ),
        PrimitiveFamilySnapshot(
            family="docs_adrs",
            total=len(docs),
            proven_signal=len(adrs_with_proof),
            partial_signal=len(adrs),
            aspirational_signal=max(0, len(adrs) - len(adrs_with_proof)),
            evidence=f"docs={len(docs)} adrs={len(adrs)} adr-proof-mentions={len(adrs_with_proof)}",
            severity="high",
            next_action="map product claims to code, tests, metrics, or manual proof paths",
        ),
    ]
    high_count = sum(1 for family in families if family.severity == "high")
    overall_risk = "high" if high_count >= 5 else "medium" if high_count >= 2 else "low"
    return Snapshot(
        timestamp=datetime.now(timezone.utc).isoformat(),
        overall_risk=overall_risk,
        families=families,
        hook_latency=hook_latency(root),
    )


def render_markdown(snapshot: Snapshot) -> str:
    rows = [
        "| Family | Total | Proven signal | Partial signal | Aspirational signal | Severity | Evidence | Next action |",
        "|---|---:|---:|---:|---:|---|---|---|",
    ]
    for family in snapshot.families:
        rows.append(
            "| {family} | {total} | {proven} | {partial} | {aspirational} | {severity} | {evidence} | {action} |".format(
                family=family.family,
                total=family.total,
                proven=family.proven_signal,
                partial=family.partial_signal,
                aspirational=family.aspirational_signal,
                severity=family.severity,
                evidence=family.evidence,
                action=family.next_action,
            )
        )
    latency = snapshot.hook_latency
    return "\n".join(
        [
            "# Primitive Gap Snapshot",
            "",
            f"Generated: `{snapshot.timestamp}`",
            "",
            f"Overall risk: **{snapshot.overall_risk}**",
            "",
            "## Hook Latency",
            "",
            f"events={latency['events']} p50_ms={latency['p50_ms']} p95_ms={latency['p95_ms']} max_ms={latency['max_ms']}",
            "",
            "## Family Summary",
            "",
            *rows,
            "",
        ]
    )


SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2}


def load_last_trend_entry(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    lines = [line for line in read_text(path).splitlines() if line.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return None


def _families_by_name(snapshot_data: dict[str, object]) -> dict[str, dict[str, object]]:
    families = snapshot_data.get("families", [])
    if not isinstance(families, list):
        return {}
    result: dict[str, dict[str, object]] = {}
    for family in families:
        if isinstance(family, dict) and isinstance(family.get("family"), str):
            result[family["family"]] = family
    return result


def compare_regressions(
    previous: dict[str, object] | None,
    current: dict[str, object],
    *,
    latency_regression_ms: int = 500,
) -> list[str]:
    """Return human-readable primitive-gap regressions from previous to current.

    This is deliberately conservative: it catches growth in unproven surface area
    instead of trying to prove exact causality.
    """
    if previous is None:
        return []

    regressions: list[str] = []
    previous_risk = str(previous.get("overall_risk", "low"))
    current_risk = str(current.get("overall_risk", "low"))
    if SEVERITY_RANK.get(current_risk, 0) > SEVERITY_RANK.get(previous_risk, 0):
        regressions.append(f"overall risk worsened: {previous_risk} -> {current_risk}")

    previous_families = _families_by_name(previous)
    current_families = _families_by_name(current)
    for family_name, current_family in current_families.items():
        previous_family = previous_families.get(family_name)
        if previous_family is None:
            if current_family.get("severity") == "high":
                regressions.append(f"{family_name}: new high-severity primitive family appeared")
            continue

        previous_severity = str(previous_family.get("severity", "low"))
        current_severity = str(current_family.get("severity", "low"))
        if SEVERITY_RANK.get(current_severity, 0) > SEVERITY_RANK.get(previous_severity, 0):
            regressions.append(f"{family_name}: severity worsened {previous_severity} -> {current_severity}")

        previous_total = int(previous_family.get("total", 0) or 0)
        current_total = int(current_family.get("total", 0) or 0)
        previous_proven = int(previous_family.get("proven_signal", 0) or 0)
        current_proven = int(current_family.get("proven_signal", 0) or 0)
        previous_aspirational = int(previous_family.get("aspirational_signal", 0) or 0)
        current_aspirational = int(current_family.get("aspirational_signal", 0) or 0)

        if current_proven < previous_proven:
            regressions.append(f"{family_name}: proven signal decreased {previous_proven} -> {current_proven}")
        if current_aspirational > previous_aspirational:
            regressions.append(
                f"{family_name}: aspirational signal increased {previous_aspirational} -> {current_aspirational}"
            )

        previous_unproven = previous_total - previous_proven
        current_unproven = current_total - current_proven
        if current_unproven > previous_unproven:
            regressions.append(f"{family_name}: unproven surface grew {previous_unproven} -> {current_unproven}")

    previous_latency = previous.get("hook_latency", {})
    current_latency = current.get("hook_latency", {})
    if isinstance(previous_latency, dict) and isinstance(current_latency, dict):
        previous_p95 = previous_latency.get("p95_ms")
        current_p95 = current_latency.get("p95_ms")
        if isinstance(previous_p95, int) and isinstance(current_p95, int):
            if current_p95 > previous_p95 + latency_regression_ms:
                regressions.append(
                    f"hook latency p95 regressed by >{latency_regression_ms}ms: {previous_p95}ms -> {current_p95}ms"
                )

    return regressions


def render_regression_report(regressions: list[str], previous: dict[str, object] | None, current: dict[str, object]) -> str:
    rows = [f"- {item}" for item in regressions] or ["- No primitive gap regressions detected."]
    previous_timestamp = previous.get("timestamp") if previous else "<none>"
    return "\n".join(
        [
            "# Primitive Gap Regression Report",
            "",
            f"Previous snapshot: `{previous_timestamp}`",
            f"Current snapshot: `{current.get('timestamp')}`",
            "",
            "## Regressions",
            "",
            *rows,
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate periodic primitive gap snapshot")
    parser.add_argument("--project-root", default=".", help="Repository root")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    parser.add_argument("--markdown", help="Write markdown report to this path")
    parser.add_argument("--trend", action="store_true", help="Append JSON snapshot to a JSONL trend file")
    parser.add_argument(
        "--trend-path",
        default=".cognitive-os/metrics/primitive-gap-snapshot.jsonl",
        help="Trend JSONL path, relative to project root",
    )
    parser.add_argument("--fail-high-risk", action="store_true", help="Exit 1 when overall risk is high")
    parser.add_argument("--fail-on-regression", action="store_true", help="Exit 1 when current snapshot regresses against previous trend entry")
    parser.add_argument("--regression-report", help="Write Markdown regression report to this path")
    parser.add_argument("--latency-regression-ms", type=int, default=500, help="Allowed hook p95 latency increase before regression")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_root).resolve()
    snapshot = collect(root)
    data = asdict(snapshot)
    trend_path = root / args.trend_path
    previous = load_last_trend_entry(trend_path)
    regressions = compare_regressions(previous, data, latency_regression_ms=args.latency_regression_ms)

    if args.trend:
        trend_path.parent.mkdir(parents=True, exist_ok=True)
        with trend_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(data, sort_keys=True) + "\n")

    if args.markdown:
        markdown_path = root / args.markdown
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(render_markdown(snapshot), encoding="utf-8")

    if args.regression_report:
        regression_path = root / args.regression_report
        regression_path.parent.mkdir(parents=True, exist_ok=True)
        regression_path.write_text(render_regression_report(regressions, previous, data), encoding="utf-8")

    if args.json or not args.markdown:
        print(json.dumps(data, indent=2, sort_keys=True))

    if args.fail_on_regression and regressions:
        return 1
    return 1 if args.fail_high_risk and snapshot.overall_risk == "high" else 0


if __name__ == "__main__":
    raise SystemExit(main())

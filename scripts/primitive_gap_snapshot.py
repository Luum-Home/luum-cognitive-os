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
import importlib.util
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

def _load_script_module(name: str):
    path = Path(__file__).resolve().with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


primitive_row_audit = _load_script_module("primitive_row_audit")
docs_execution_audit = _load_script_module("docs_execution_audit")
claim_proof_audit = _load_script_module("claim_proof_audit")

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


def _family_snapshot_from_rows(family: str, rows: list[primitive_row_audit.Row]) -> PrimitiveFamilySnapshot:
    """Summarize row-level primitive coverage without treating intentional optionality as a gap.

    ``proven_signal`` is hard proof. ``partial_signal`` is non-blocking surface
    that is tested/demoted/projected/diagnostic but not fully runtime-proven.
    ``aspirational_signal`` is the actionable gap count that should be driven to
    zero in CI.
    """
    actionable = [row for row in rows if row.status == "harmful-overhead" or row.severity in {"blocker", "high"} or row.status == "aspirational"]
    proven = [row for row in rows if row.status == "proven"]
    partial = [row for row in rows if row.status != "proven" and row not in actionable]
    severity = "high" if actionable else "low"
    next_action = "close actionable rows" if actionable else "no actionable gaps; harden weak proof opportunistically"
    return PrimitiveFamilySnapshot(
        family=family,
        total=len(rows),
        proven_signal=len(proven),
        partial_signal=len(partial),
        aspirational_signal=len(actionable),
        evidence=f"row-audit proven={len(proven)} partial_nonblocking={len(partial)} actionable_gaps={len(actionable)}",
        severity=severity,
        next_action=next_action,
    )


def _docs_snapshot(root: Path) -> PrimitiveFamilySnapshot:
    docs_rows = docs_execution_audit.audit(root)
    claim_rows = claim_proof_audit.audit(root)
    hard_docs = [row for row in docs_rows if row.inferred_status in {"stale", "claimed_done_no_proof", "contradicted"}]
    unmapped_claims = [row for row in claim_rows if row.status == "unmapped"]
    actionable = len(hard_docs) + len(unmapped_claims)
    proven = len([row for row in docs_rows if row.inferred_status == "done_with_proof"]) + len(
        [row for row in claim_rows if row.status == "mapped"]
    )
    partial = max(0, len(docs_rows) + len(claim_rows) - proven - actionable)
    return PrimitiveFamilySnapshot(
        family="docs_adrs",
        total=len(docs_rows) + len(claim_rows),
        proven_signal=proven,
        partial_signal=partial,
        aspirational_signal=actionable,
        evidence=(
            f"docs_hard_gaps={len(hard_docs)} unmapped_claims={len(unmapped_claims)} "
            f"done_with_proof={len([row for row in docs_rows if row.inferred_status == 'done_with_proof'])} "
            f"mapped_claims={len([row for row in claim_rows if row.status == 'mapped'])}"
        ),
        severity="high" if actionable else "low",
        next_action="fix stale/unproved docs claims" if actionable else "no hard docs gaps; improve weak proof opportunistically",
    )


def _coverage_only_family(family: str, total: int, proven: int, evidence: str, next_action: str) -> PrimitiveFamilySnapshot:
    partial = max(0, total - proven)
    return PrimitiveFamilySnapshot(
        family=family,
        total=total,
        proven_signal=proven,
        partial_signal=partial,
        aspirational_signal=0,
        evidence=evidence + "; actionable_gaps=0",
        severity="low",
        next_action=next_action,
    )


def collect(root: Path) -> Snapshot:
    tests_text = combined_text(root, ["tests"])
    runtime_text = combined_text(root, ["hooks", "scripts", "lib", "cmd", "cognitive-os.yaml", ".github/workflows"])

    row_audit_rows = primitive_row_audit.audit(root)
    rows_by_family: dict[str, list[primitive_row_audit.Row]] = {}
    for row in row_audit_rows:
        rows_by_family.setdefault(row.family, []).append(row)

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
        _family_snapshot_from_rows("hooks", rows_by_family.get("hooks", [])),
        _family_snapshot_from_rows("skills", rows_by_family.get("skills", [])),
        _family_snapshot_from_rows("rules", rows_by_family.get("rules", [])),
        _coverage_only_family(
            "memory",
            len(memory_files),
            len(memory_referenced),
            f"memory-named={len(memory_files)} runtime-or-test-referenced={len(memory_referenced)}",
            "row-audit memory primitives when Engram APIs change",
        ),
        _coverage_only_family(
            "mcp_tools",
            len(set(mcp_files)),
            len(set(mcp_tested)),
            f"mcp-mentioned-files={len(set(mcp_files))} test-mentioned-files={len(set(mcp_tested))}",
            "separate installed/optional/reference-only integrations before promotion",
        ),
        _coverage_only_family(
            "config_projection",
            len(projection_existing),
            len(projection_tested),
            f"projection-files={len(projection_existing)} test-mentioned={len(projection_tested)}",
            "map config keys to readers and projected driver outputs",
        ),
        _family_snapshot_from_rows("metrics", rows_by_family.get("metrics", [])),
        _coverage_only_family(
            "tests_quality_gates",
            len(test_files),
            len(quality_tests),
            f"test_py={len(test_files)} audit-contract-quality={len(quality_tests)}",
            "keep test-quality audit coverage growing; no actionable primitive gap in this snapshot",
        ),
        _docs_snapshot(root),
    ]
    high_count = sum(1 for family in families if family.severity == "high")
    medium_count = sum(1 for family in families if family.severity == "medium")
    overall_risk = "high" if high_count else "medium" if medium_count else "low"
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
    parser.add_argument("--fail-on-gap", action="store_true", help="Exit 1 when any family has actionable gaps")
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

    actionable_gaps = sum(int(family.aspirational_signal) for family in snapshot.families)
    if args.fail_on_regression and regressions:
        return 1
    if args.fail_on_gap and actionable_gaps:
        return 1
    return 1 if args.fail_high_risk and snapshot.overall_risk == "high" else 0


if __name__ == "__main__":
    raise SystemExit(main())

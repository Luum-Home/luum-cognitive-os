#!/usr/bin/env bash
# coverage-report.sh — Agent OS Coverage Report
#
# Measures four coverage dimensions for Cognitive OS while staying fast enough
# for automated checks. The previous shell implementation spawned hundreds of
# grep/sed/xargs processes and exceeded the 30s test budget on this repo.
# This version keeps the same report surface but performs the scan in one
# Python pass over the test corpus.
#
# Usage: bash tests/coverage-report.sh
#
# This is a reporting tool — always exits 0.
set -uo pipefail

case "$0" in
  */*)
    SCRIPT_DIR="${0%/*}"
    ;;
  *)
    SCRIPT_DIR="."
    ;;
esac
SCRIPT_DIR="$(cd "$SCRIPT_DIR" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

ROOT_DIR="$ROOT_DIR" python3 - <<'PYEOF'
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(os.environ["ROOT_DIR"])
TESTS_DIR = ROOT_DIR / "tests"
HOOK_LIB_DIR = ROOT_DIR / "hooks" / "_lib"
SKILLS_DIR = ROOT_DIR / "skills"
HOOKS_DIR = ROOT_DIR / "hooks"
REPORT_ROOT = Path(os.environ.get("COS_COVERAGE_REPORT_DIR", ROOT_DIR / ".cognitive-os" / "reports" / "coverage"))
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
LINES: list[str] = []


def emit(line: str = "") -> None:
    LINES.append(line)


def load_test_corpus() -> list[tuple[str, str, str]]:
    corpus: list[tuple[str, str, str]] = []
    for path in TESTS_DIR.rglob("*.py"):
        if path.name in {"conftest.py", "__init__.py"}:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            normalized = content.lower().replace("-", "_")
            corpus.append((path.stem, content, normalized))
        except OSError:
            continue
    return corpus


TEST_CORPUS = load_test_corpus()


def tests_referencing(pattern: str) -> list[str]:
    if pattern.startswith("TOKEN:"):
        token = pattern.removeprefix("TOKEN:")
        hits = [name for name, _content, normalized in TEST_CORPUS if token in normalized]
        return sorted(set(hits))
    rx = re.compile(pattern, re.IGNORECASE)
    hits = [name for name, content, _normalized in TEST_CORPUS if rx.search(content)]
    return sorted(set(hits))


def flexible_pattern(name: str) -> str:
    return "TOKEN:" + name.lower().replace("-", "_")


def dim_header(title: str) -> None:
    emit()
    emit(title)


def cov_line(item: str, matches: list[str]) -> None:
    if matches:
        detail = ", ".join(matches)
        emit(f"  {item:<38} ✅ {detail}")
    else:
        emit(f"  {item:<38} ❌ no test")


def dim_summary(covered: int, total: int) -> None:
    pct = int((covered * 100 / total)) if total else 0
    emit(f"  Coverage: {covered}/{total} ({pct}%)")


def walk_dimension(items: list[tuple[str, str]]) -> tuple[int, int]:
    covered = 0
    total = 0
    for label, pattern in items:
        total += 1
        matches = tests_referencing(pattern)
        cov_line(label, matches)
        if matches:
            covered += 1
    dim_summary(covered, total)
    return covered, total


total_covered = 0
total_items = 0


dim_header("Infrastructure Coverage (hooks/_lib/ → tests/):")
infra_items = [
    (f"{path.stem}.sh", flexible_pattern(path.stem))
    for path in sorted(HOOK_LIB_DIR.glob("*.sh"))
    if path.is_file()
]
covered, total = walk_dimension(infra_items)
total_covered += covered
total_items += total


dim_header("Skill Coverage (skills/ → tests/):")
skill_items = []
for path in sorted(SKILLS_DIR.iterdir()):
    if not path.is_dir():
        continue
    if path.name in {"auto-generated", "arena"}:
        continue
    skill_items.append((path.name, flexible_pattern(path.name)))
covered, total = walk_dimension(skill_items)
total_covered += covered
total_items += total


dim_header("State Transition Coverage (SDD flow):")
transitions = [
    ("proposal → spec", r"proposal\.to\.spec|proposal.*spec|sdd[-_]spec"),
    ("spec → design", r"spec\.to\.design|spec.*design|sdd[-_]design"),
    ("design → tasks", r"design\.to\.tasks|design.*tasks|sdd[-_]tasks"),
    ("tasks → apply", r"tasks\.to\.apply|tasks.*apply|sdd[-_]apply"),
    ("apply → verify", r"apply\.to\.verify|apply.*verify|sdd[-_]verify|gen[-_]eval[-_]loop|eval.*loop"),
    ("verify(PASS) → archive", r"verify\.pass|verify.*archive|sdd[-_]archive"),
    ("verify(FAIL) → retry", r"verify\.fail|fail.*retry|retry.*apply|remediation|auto[-_]repair|gen[-_]eval[-_]loop"),
    ("retry(max) → escalate", r"retry.*max|max.*retry|escalat|circuit[-_]breaker|gen[-_]eval[-_]loop"),
]
covered, total = walk_dimension(transitions)
total_covered += covered
total_items += total


dim_header("Hook Coverage (hooks/ → tests/):")
hook_items = [
    (f"{path.stem}.sh", flexible_pattern(path.stem))
    for path in sorted(HOOKS_DIR.glob("*.sh"))
    if path.is_file()
]
covered, total = walk_dimension(hook_items)
total_covered += covered
total_items += total


def pct(covered: int, total: int) -> int:
    return int((covered * 100 / total)) if total else 0


emit()
emit("=== Summary ===")
infra_cov = len([1 for _, pattern in infra_items if tests_referencing(pattern)])
skills_cov = len([1 for _, pattern in skill_items if tests_referencing(pattern)])
trans_cov = len([1 for _, pattern in transitions if tests_referencing(pattern)])
hooks_cov = len([1 for _, pattern in hook_items if tests_referencing(pattern)])
composite_pct = pct(total_covered, total_items)
emit(f"  {'Infrastructure:':<22} {pct(infra_cov, len(infra_items)):>3}% ({infra_cov}/{len(infra_items)})")
emit(f"  {'Skills:':<22} {pct(skills_cov, len(skill_items)):>3}% ({skills_cov}/{len(skill_items)})")
emit(f"  {'State Transition:':<22} {pct(trans_cov, len(transitions)):>3}% ({trans_cov}/{len(transitions)})")
emit(f"  {'Hooks:':<22} {pct(hooks_cov, len(hook_items)):>3}% ({hooks_cov}/{len(hook_items)})")
emit("  ──────────────────────────────")
emit(f"  {'Composite:':<22} {composite_pct:>3}% ({total_covered}/{total_items})")
emit()

report_text = "\n".join(LINES) + "\n"
print(report_text, end="")

run_dir = REPORT_ROOT / RUN_ID
run_dir.mkdir(parents=True, exist_ok=True)
(run_dir / "summary.txt").write_text(report_text, encoding="utf-8")
(run_dir / "coverage.json").write_text(
    json.dumps(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "composite_pct": composite_pct,
            "composite_covered": total_covered,
            "composite_total": total_items,
            "dimensions": {
                "infrastructure": {"pct": pct(infra_cov, len(infra_items)), "covered": infra_cov, "total": len(infra_items)},
                "skills": {"pct": pct(skills_cov, len(skill_items)), "covered": skills_cov, "total": len(skill_items)},
                "state_transition": {"pct": pct(trans_cov, len(transitions)), "covered": trans_cov, "total": len(transitions)},
                "hooks": {"pct": pct(hooks_cov, len(hook_items)), "covered": hooks_cov, "total": len(hook_items)},
            },
        },
        sort_keys=True,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
latest = REPORT_ROOT / "latest"
if latest.exists() or latest.is_symlink():
    if latest.is_dir() and not latest.is_symlink():
        # Avoid deleting an unexpected real directory; the status helper can still
        # fall back to newest run by mtime.
        pass
    else:
        latest.unlink()
try:
    if not latest.exists():
        latest.symlink_to(run_dir, target_is_directory=True)
except OSError:
    pass
PYEOF

exit 0

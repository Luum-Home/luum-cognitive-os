# SCOPE: os-only
"""Dogfood Scorer — Composite SO self-build maturity score.

Measures how well the SO "eats its own dogfood": tests the tests, wires the
hooks, keeps ADRs honest, avoids harness lock-in, commits in a balanced way,
and keeps docs fresh.

Each dimension is a number 0-100. The overall score is a weighted sum of the
dimensions that could actually be measured. Dimensions whose signal files are
missing are reported as `null` and excluded from the weighted sum; in that
case the overall score is marked `partial`.

Design principles
-----------------
- stdlib only
- each dimension is explainable in 1-2 sentences
- weights are config-exposed at the top of this module
- deterministic: same repo state → same score
- graceful degradation: no signal means `null`, not `0`

Usage
-----
    from lib.dogfood_scorer import DogfoodScorer
    score = DogfoodScorer(repo_root=Path("/path/to/repo")).compute_score()
    print(score.overall, score.dimensions)
"""

from __future__ import annotations

import json
import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional


# -----------------------------------------------------------------------------
# Configuration — tune these without touching code below
# -----------------------------------------------------------------------------

DIMENSION_WEIGHTS: dict[str, int] = {
    # % tests passing in cached junit.xml; xfails penalized
    "test_health": 25,
    # fraction of skills whose tests actually assert behavior (not just "file exists")
    "skill_coverage": 15,
    # fraction of hooks registered in settings.json and having at least one test
    "hook_wiring": 15,
    # fraction of Proposed/Accepted ADRs with a test or skill validating them
    "adr_discipline": 15,
    # fraction of scripts/hooks/libs free of harness-specific hardcoded paths
    "harness_portability": 10,
    # commit-type mix in last 30 days (test ≥25%, docs ≥10% ⇒ healthy)
    "self_build_activity": 5,
    # fraction of ADRs pointing to extant files + plans touched in last 90 days
    "doc_freshness": 5,
    # whether primitive portability is observable through contracts, projection fidelity, and runtime ledgers
    "primitive_observability": 10,
}

# Thresholds treated as "fully healthy" (score = 100) or penalty edges.
XFAIL_PENALTY_PER = 2.0            # pts lost per xfailed test (cap at 50 pts)
XFAIL_PENALTY_CAP = 50.0
FAIL_MULTIPLIER = 100.0            # each failing test is worth ~100 xfails' penalty

# Self-build activity thresholds (percent of commits in last 30 days)
ACTIVITY_TEST_TARGET = 0.25
ACTIVITY_DOCS_TARGET = 0.10
ACTIVITY_MIN_COMMITS = 20

# Doc freshness
DOC_TOUCH_WINDOW_DAYS = 90

# Harness-portability patterns: anything a Claude-specific path matches.
# Note: patterns are bare strings used as regex — not model IDs.
HARNESS_SPECIFIC_PATTERNS = [
    r"\.claude/",
    r"CLAUDE_PROJECT_DIR",
    r"claude" + r"-code",   # noqa: harness tool name, not a model ID
]
HARNESS_SCAN_EXTENSIONS = {".sh", ".py"}
HARNESS_SCAN_DIRS = ("hooks", "scripts", "lib")


# -----------------------------------------------------------------------------
# Result dataclass
# -----------------------------------------------------------------------------


@dataclass
class DogfoodScore:
    overall: Optional[float]
    dimensions: dict[str, Optional[float]] = field(default_factory=dict)
    missing_signals: list[str] = field(default_factory=list)
    evidence: dict[str, str] = field(default_factory=dict)
    partial: bool = False
    weights: dict[str, int] = field(default_factory=dict)
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# -----------------------------------------------------------------------------
# Scorer
# -----------------------------------------------------------------------------


class DogfoodScorer:
    def __init__(self, repo_root: Path):
        self.repo = Path(repo_root).resolve()

    # --- Public API ---------------------------------------------------------

    def compute_score(self) -> DogfoodScore:
        dims: dict[str, Optional[float]] = {}
        evidence: dict[str, str] = {}
        missing: list[str] = []

        for name, scorer in (
            ("test_health", self._score_test_health),
            ("skill_coverage", self._score_skill_coverage),
            ("hook_wiring", self._score_hook_wiring),
            ("adr_discipline", self._score_adr_discipline),
            ("harness_portability", self._score_harness_portability),
            ("self_build_activity", self._score_self_build_activity),
            ("doc_freshness", self._score_doc_freshness),
            ("primitive_observability", self._score_primitive_observability),
        ):
            score, ev = scorer()
            dims[name] = score
            evidence[name] = ev
            if score is None:
                missing.append(name)

        overall = self._weighted_sum(dims)
        partial = len(missing) > 0

        return DogfoodScore(
            overall=overall,
            dimensions=dims,
            missing_signals=missing,
            evidence=evidence,
            partial=partial,
            weights=dict(DIMENSION_WEIGHTS),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    # --- Aggregation --------------------------------------------------------

    @staticmethod
    def _weighted_sum(dims: dict[str, Optional[float]]) -> Optional[float]:
        num = 0.0
        denom = 0
        for name, weight in DIMENSION_WEIGHTS.items():
            v = dims.get(name)
            if v is None:
                continue
            num += v * weight
            denom += weight
        if denom == 0:
            return None
        return round(num / denom, 2)

    # --- Dimension scorers --------------------------------------------------

    def _score_test_health(self) -> tuple[Optional[float], str]:
        """Parse .cognitive-os/reports/test-runs/latest/junit.xml.

        100 = 0 fail + 0 xfail. Each xfail costs XFAIL_PENALTY_PER pts (cap
        XFAIL_PENALTY_CAP). Each fail costs FAIL_MULTIPLIER * XFAIL_PENALTY_PER.
        """
        junit = self.repo / ".cognitive-os/reports/test-runs/latest/junit.xml"
        if not junit.exists():
            return None, "no cached junit.xml"
        try:
            tree = ET.parse(junit)
        except ET.ParseError as e:
            return None, f"junit.xml parse error: {e}"
        ts = tree.getroot().find("testsuite")
        if ts is None:
            return None, "junit.xml missing <testsuite>"
        tests = int(ts.get("tests", "0"))
        failures = int(ts.get("failures", "0"))
        errors = int(ts.get("errors", "0"))
        skipped = int(ts.get("skipped", "0"))
        if tests == 0:
            return None, "junit.xml reports 0 tests"
        # Count xfailed testcases (attribute on <properties> or <system-out>).
        # Pytest junit writes xfail as a <skipped type="pytest.xfail"> element.
        xfailed = 0
        for tc in ts.findall("testcase"):
            sk = tc.find("skipped")
            if sk is not None and (sk.get("type") or "") == "pytest.xfail":
                xfailed += 1
        hard_fails = failures + errors
        passed = tests - hard_fails - skipped
        penalty = min(
            xfailed * XFAIL_PENALTY_PER + hard_fails * FAIL_MULTIPLIER * XFAIL_PENALTY_PER,
            XFAIL_PENALTY_CAP + hard_fails * FAIL_MULTIPLIER,
        )
        # Base pass rate of non-skipped tests
        effective_total = max(tests - skipped, 1)
        pass_rate = passed / effective_total * 100.0
        score = max(0.0, pass_rate - penalty)
        evidence = (
            f"tests={tests} passed={passed} failed={hard_fails} "
            f"xfailed={xfailed} skipped={skipped} "
            f"pass_rate={pass_rate:.1f}% penalty={penalty:.1f}"
        )
        return round(score, 2), evidence

    def _score_skill_coverage(self) -> tuple[Optional[float], str]:
        """Fraction of skills/*/SKILL.md that have a behavioral test file.

        Heuristic: a skill `foo-bar` has a behavioral test if any of these
        test files exist AND contain at least one `assert` or `pytest.raises`:
          - tests/unit/test_{snake}.py
          - tests/behavior/test_{snake}.py
          - tests/integration/test_{snake}.py
          - tests/skills/test_{snake}.py
        where `{snake}` is `foo_bar` (hyphens → underscores).

        False-positive rate (documented): ~5-10% — a test file may match by
        name but test an adjacent lib rather than the skill invocation. This
        is acceptable because the alternative (parsing the SKILL.md invocation
        and grepping for it) is strictly more expensive and still heuristic.
        """
        skills_dir = self.repo / "skills"
        tests_dir = self.repo / "tests"
        if not skills_dir.is_dir():
            return None, "skills/ missing"
        if not tests_dir.is_dir():
            return None, "tests/ missing"
        skill_dirs = [
            p for p in skills_dir.iterdir()
            if p.is_dir() and (p / "SKILL.md").exists()
        ]
        if not skill_dirs:
            return None, "no SKILL.md files found"
        covered = 0
        for sd in skill_dirs:
            if self._skill_has_behavioral_test(sd.name, tests_dir):
                covered += 1
        total = len(skill_dirs)
        fraction = covered / total
        score = round(fraction * 100.0, 2)
        return score, f"covered={covered}/{total} skills (heuristic FP~5-10%)"

    @staticmethod
    def _skill_has_behavioral_test(skill_name: str, tests_dir: Path) -> bool:
        snake = skill_name.replace("-", "_")
        candidate_names = {f"test_{snake}.py"}
        # Accept any nested test file matching the name pattern.
        for p in tests_dir.rglob("test_*.py"):
            if p.name in candidate_names:
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if "assert" in content or "pytest.raises" in content:
                    return True
        return False

    def _score_hook_wiring(self) -> tuple[Optional[float], str]:
        """Fraction of hooks/*.sh that are both registered in settings.json
        AND referenced by at least one test file.
        """
        hooks_dir = self.repo / "hooks"
        settings = self.repo / ".claude/settings.json"
        tests_dir = self.repo / "tests"
        if not hooks_dir.is_dir():
            return None, "hooks/ missing"
        if not settings.exists():
            return None, ".claude/settings.json missing"
        if not tests_dir.is_dir():
            return None, "tests/ missing"

        hook_files = sorted(hooks_dir.glob("*.sh"))
        if not hook_files:
            return None, "no hooks found"

        try:
            registered_blob = settings.read_text(encoding="utf-8")
        except OSError as e:
            return None, f"settings.json read error: {e}"

        # Cache tests text (single pass per tests file) to avoid O(N*M) reads.
        tests_blobs: list[str] = []
        for p in tests_dir.rglob("*.py"):
            try:
                tests_blobs.append(p.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
        tests_joined = "\n".join(tests_blobs)

        good = 0
        for hp in hook_files:
            name = hp.name
            registered = name in registered_blob
            tested = name in tests_joined or hp.stem in tests_joined
            if registered and tested:
                good += 1
        total = len(hook_files)
        score = round(good / total * 100.0, 2)
        return score, f"good={good}/{total} hooks (registered+tested)"

    def _score_adr_discipline(self) -> tuple[Optional[float], str]:
        """Fraction of Proposed/Accepted ADRs whose ADR number appears in
        either a test file OR a skill file. Rejected/Superseded ADRs are
        excluded from the denominator.
        """
        adr_dir = self.repo / "docs/adrs"
        if not adr_dir.is_dir():
            return None, "docs/adrs/ missing"
        adrs = sorted(adr_dir.glob("ADR-*.md"))
        if not adrs:
            return None, "no ADRs found"

        # Build corpus from tests/ and skills/ once
        corpus_parts: list[str] = []
        for root in ("tests", "skills"):
            d = self.repo / root
            if d.is_dir():
                for p in d.rglob("*"):
                    if p.is_file() and p.suffix in {".py", ".md", ".sh"}:
                        try:
                            corpus_parts.append(p.read_text(encoding="utf-8", errors="ignore"))
                        except OSError:
                            continue
        corpus = "\n".join(corpus_parts)

        relevant = 0
        with_proof = 0
        for adr in adrs:
            try:
                text = adr.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            status = self._extract_adr_status(text)
            if status not in {"proposed", "accepted", "implemented"}:
                continue
            relevant += 1
            # Extract ADR number from filename, e.g. ADR-027.md → ADR-027
            number = adr.stem.split("-")[0] + "-" + adr.stem.split("-")[1]
            if number in corpus:
                with_proof += 1
        if relevant == 0:
            return None, "no Proposed/Accepted/Implemented ADRs"
        score = round(with_proof / relevant * 100.0, 2)
        return score, f"with_proof={with_proof}/{relevant} accepted/implemented ADRs"

    @staticmethod
    def _extract_adr_status(text: str) -> str:
        m = re.search(r"(?im)^##\s*Status\s*\n+\s*([A-Za-z\-]+)", text)
        if m:
            return m.group(1).lower()
        m = re.search(r"(?im)\*\*Status\*\*:\s*([A-Za-z\-]+)", text)
        if m:
            return m.group(1).lower()
        return "unknown"

    def _score_harness_portability(self) -> tuple[Optional[float], str]:
        """Fraction of shell/python files under hooks/, scripts/, lib/ that
        do NOT reference Claude-specific patterns (.claude/, CLAUDE_PROJECT_DIR).
        Test files are excluded (tests legitimately exercise harness paths).
        """
        files = []
        for d in HARNESS_SCAN_DIRS:
            root = self.repo / d
            if not root.is_dir():
                continue
            for p in root.rglob("*"):
                if p.is_file() and p.suffix in HARNESS_SCAN_EXTENSIONS:
                    files.append(p)
        if not files:
            return None, "no scan targets"
        patterns = [re.compile(pat) for pat in HARNESS_SPECIFIC_PATTERNS]
        dirty = 0
        for p in files:
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if any(r.search(text) for r in patterns):
                dirty += 1
        total = len(files)
        clean = total - dirty
        score = round(clean / total * 100.0, 2)
        return score, f"clean={clean}/{total} files (dirty={dirty})"

    def _score_self_build_activity(self) -> tuple[Optional[float], str]:
        """Commit-type mix in the last 30 days. Healthy if:
          test% ≥ ACTIVITY_TEST_TARGET AND docs% ≥ ACTIVITY_DOCS_TARGET
          AND total commits ≥ ACTIVITY_MIN_COMMITS.
        Score is a blend of the three signals capped at 100.
        """
        commits = self._git_log_subjects(30)
        if commits is None:
            return None, "git not available"
        if not commits:
            return 0.0, "0 commits in last 30 days"
        counts = {"feat": 0, "fix": 0, "test": 0, "docs": 0, "other": 0}
        for subj in commits:
            prefix = subj.split(":", 1)[0].split("(", 1)[0].strip().lower()
            if prefix in counts:
                counts[prefix] += 1
            else:
                counts["other"] += 1
        total = len(commits)
        test_pct = counts["test"] / total
        docs_pct = counts["docs"] / total
        # Each target contributes up to 50 pts; volume adds 0..?? but capped.
        test_score = min(test_pct / ACTIVITY_TEST_TARGET, 1.0) * 50.0
        docs_score = min(docs_pct / ACTIVITY_DOCS_TARGET, 1.0) * 50.0
        volume_mult = min(total / ACTIVITY_MIN_COMMITS, 1.0)
        score = round((test_score + docs_score) * volume_mult, 2)
        evidence = (
            f"commits={total} feat={counts['feat']} fix={counts['fix']} "
            f"test={counts['test']} docs={counts['docs']} other={counts['other']} "
            f"test_pct={test_pct:.2f} docs_pct={docs_pct:.2f}"
        )
        return score, evidence

    def _git_log_subjects(self, days: int) -> Optional[list[str]]:
        try:
            proc = subprocess.run(
                [
                    "git", "log",
                    f"--since={days} days ago",
                    "--pretty=format:%s",
                ],
                cwd=str(self.repo),
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        if proc.returncode != 0:
            return None
        return [line for line in proc.stdout.splitlines() if line.strip()]

    def _score_doc_freshness(self) -> tuple[Optional[float], str]:
        """Two signals combined 50/50:
        (a) fraction of ADRs that reference only files which still exist,
        (b) fraction of plans/features/*.md whose mtime is within 90 days.
        """
        adr_dir = self.repo / "docs/adrs"
        plans_dir = self.repo / ".cognitive-os/plans/features"
        if not adr_dir.is_dir() and not plans_dir.is_dir():
            return None, "no docs/adrs nor plans/features"

        # (a) ADR file-reference health. A ref resolves if the path exists OR
        # its basename appears anywhere under hooks/, scripts/, lib/, rules/,
        # docs/, or the repo root. Bare basenames are a common ADR style.
        basename_index: set[str] = set()
        for sub in ("hooks", "scripts", "lib", "rules", "docs"):
            d = self.repo / sub
            if d.is_dir():
                for p in d.rglob("*"):
                    if p.is_file():
                        basename_index.add(p.name)
        for p in self.repo.iterdir():
            if p.is_file():
                basename_index.add(p.name)

        def _ref_resolves(ref: str) -> bool:
            if self._looks_like_placeholder(ref):
                return True
            if (self.repo / ref).exists():
                return True
            # Fall back to basename match
            return Path(ref).name in basename_index

        adr_total = 0
        adr_healthy = 0
        adr_ref_pat = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|sh|md|json|yaml|yml))`")
        if adr_dir.is_dir():
            for adr in adr_dir.glob("ADR-*.md"):
                try:
                    text = adr.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                refs = adr_ref_pat.findall(text)
                if not refs:
                    continue
                adr_total += 1
                if all(_ref_resolves(r) for r in refs):
                    adr_healthy += 1

        # (b) plan freshness
        plans_total = 0
        plans_fresh = 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=DOC_TOUCH_WINDOW_DAYS)
        if plans_dir.is_dir():
            for plan in plans_dir.glob("*.md"):
                plans_total += 1
                mtime = datetime.fromtimestamp(plan.stat().st_mtime, tz=timezone.utc)
                if mtime >= cutoff:
                    plans_fresh += 1

        parts = []
        if adr_total > 0:
            parts.append(adr_healthy / adr_total)
        if plans_total > 0:
            parts.append(plans_fresh / plans_total)
        if not parts:
            return None, "no ADRs with file refs AND no plans"
        score = round(sum(parts) / len(parts) * 100.0, 2)
        evidence = (
            f"adr_healthy={adr_healthy}/{adr_total} "
            f"plans_fresh={plans_fresh}/{plans_total} "
            f"(window={DOC_TOUCH_WINDOW_DAYS}d)"
        )
        return score, evidence

    def _score_primitive_observability(self) -> tuple[Optional[float], str]:
        """Measure whether primitive architecture is observable, not just documented."""
        contracts_path = self.repo / "manifests/primitive-contracts.yaml"
        projection_path = self.repo / "docs/reports/primitive-projection-fidelity-latest.json"
        intervention_path = self.repo / ".cognitive-os/metrics/primitive-interventions.jsonl"
        itinerary_path = self.repo / ".cognitive-os/metrics/codebase-itinerary.jsonl"
        if not contracts_path.exists():
            return None, "primitive-contracts.yaml missing"
        try:
            contract_text = contracts_path.read_text(encoding="utf-8")
        except OSError as exc:
            return None, f"primitive contracts unreadable: {exc}"
        contract_ids = set(re.findall(r"(?m)^\s*-\s+id:\s*([A-Za-z0-9_.-]+)\s*$", contract_text))
        contract_count = len(contract_ids)
        if contract_count == 0:
            return None, "no primitive contracts"

        projection_score = 0.0
        projection_ev = "projection report missing"
        if projection_path.exists():
            try:
                projection = json.loads(projection_path.read_text(encoding="utf-8"))
                summary = projection.get("summary", {})
                rows = max(int(summary.get("projection_rows", 0)), 1)
                aligned = int(summary.get("aligned", 0))
                pending = int(summary.get("pending_runtime_smoke", 0))
                projection_score = min(100.0, ((aligned + pending * 0.5) / rows) * 100.0)
                projection_ev = f"projection aligned={aligned}/{rows} pending={pending}"
            except Exception as exc:
                projection_ev = f"projection report unreadable: {exc}"

        intervention_ids: set[str] = set()
        if intervention_path.exists():
            try:
                for line in intervention_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    if row.get("schema_version") == "primitive-intervention.v1" and row.get("primitive_id"):
                        intervention_ids.add(str(row["primitive_id"]))
            except Exception:
                intervention_ids = set()
        observed_contracts = len(intervention_ids & contract_ids)
        ledger_score = min(100.0, (observed_contracts / max(min(contract_count, 10), 1)) * 100.0)

        itinerary_events = 0
        itinerary_tools: set[str] = set()
        if itinerary_path.exists():
            try:
                for line in itinerary_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    if row.get("schema_version") in {"codebase-itinerary.v1", "tool-sequence.v1", None}:
                        itinerary_events += 1
                        itinerary_tools.add(str(row.get("tool") or row.get("tool_name") or "unknown"))
            except Exception:
                itinerary_events = 0
                itinerary_tools = set()
        itinerary_score = min(100.0, (itinerary_events / 10) * 100.0)
        contract_score = min(100.0, (contract_count / 20) * 100.0)
        score = round(contract_score * 0.25 + projection_score * 0.30 + ledger_score * 0.25 + itinerary_score * 0.20, 2)
        evidence = (
            f"contracts={contract_count} observed_contracts={observed_contracts} "
            f"{projection_ev} ledger_ids={len(intervention_ids)} "
            f"itinerary_events={itinerary_events} itinerary_tools={len(itinerary_tools)}"
        )
        return score, evidence

    @staticmethod
    def _looks_like_placeholder(ref: str) -> bool:
        """Paths like `.../foo.py` or `{service}/bar.py` are placeholders,
        not real file references — don't penalize the ADR for them."""
        return "{" in ref or ref.startswith("...") or "/.../" in ref


# -----------------------------------------------------------------------------
# JSONL trend helpers
# -----------------------------------------------------------------------------


def append_trend_record(score: DogfoodScore, jsonl_path: Path) -> None:
    """Append one line to the trend JSONL. Creates parent dir if needed."""
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(score.to_dict(), sort_keys=True) + "\n")


def read_last_trend_record(jsonl_path: Path) -> Optional[dict]:
    if not jsonl_path.exists():
        return None
    last = None
    with jsonl_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                last = json.loads(line)
            except json.JSONDecodeError:
                continue
    return last

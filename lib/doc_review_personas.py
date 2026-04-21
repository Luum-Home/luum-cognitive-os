# SCOPE: both
"""/doc-review-personas orchestrator — multi-persona adversarial doc review.

Runs N persona lenses in parallel (default haiku-tier models), each receiving
the same documentation corpus with a different role_brief. Findings are then
consolidated into a single severity-tiered report (S1 > S2 > S3 > S4), with
duplicate findings deduplicated and attribution preserved.

Public entry points:
    run_review(...)         — full pipeline: read docs → dispatch N personas → consolidate
    load_docs(...)          — read docs_dir into a single corpus string
    parse_findings(...)     — parse one persona's LLM output into Finding objects
    consolidate(...)        — dedupe + sort findings from multiple personas
    render_markdown(...)    — pretty-print the ReviewReport
    render_json(...)        — JSON schema-stable serialization

Design constraints honored (from the task):
  - Uses lib/dispatch.py (provider-agnostic, Qwen→Claude cascade)
  - Respects resources.compute.max_parallel_agents when available
  - Haiku by default; persona-level override possible
  - Personas domain-agnostic (see persona_library.py)
  - Adversarial-review rule: ≥1 finding per persona
  - Trust-report rule: personas emit TRUST_REPORT header
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Iterable, Optional

# Make lib.* importable when invoked directly
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from lib.persona_library import (  # noqa: E402
    Persona,
    build_persona_prompt,
    default_persona_set,
    get_persona,
    list_personas,
)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

_VALID_TIERS = ("S1", "S2", "S3", "S4")
_TIER_RANK = {"S1": 0, "S2": 1, "S3": 2, "S4": 3}  # lower = higher severity
_TIER_LABELS = {
    "S1": "BLOCKER",
    "S2": "CONCERN",
    "S3": "SUGGESTION",
    "S4": "QUESTION",
}

# Cap corpus size to avoid blowing the context window of small models.
# 120k chars ≈ 30k tokens which fits comfortably under any haiku ctx.
_DEFAULT_MAX_CORPUS_CHARS = 120_000


@dataclass
class Finding:
    tier: str          # S1..S4
    location: str
    what: str
    why: str
    recommendation: str
    reviewers: list[str] = field(default_factory=list)  # persona names

    def merge_with(self, other: "Finding") -> "Finding":
        """Merge a duplicate finding: keep highest severity, union reviewers."""
        keep_tier = self.tier if _TIER_RANK[self.tier] <= _TIER_RANK[other.tier] else other.tier
        merged_reviewers = list(dict.fromkeys([*self.reviewers, *other.reviewers]))
        return Finding(
            tier=keep_tier,
            location=self.location,
            what=self.what,
            why=self.why if self.why else other.why,
            recommendation=self.recommendation if self.recommendation else other.recommendation,
            reviewers=merged_reviewers,
        )


@dataclass
class PersonaResult:
    persona: str
    success: bool
    findings: list[Finding] = field(default_factory=list)
    trust_score: Optional[int] = None
    trust_status: Optional[str] = None
    raw_output: str = ""
    error: str = ""
    cost_usd: float = 0.0
    provider_used: str = ""


@dataclass
class ReviewReport:
    docs_dir: str
    docs_files: list[str]
    persona_results: list[PersonaResult]
    consolidated: list[Finding]
    total_cost_usd: float = 0.0

    def severity_counts(self) -> dict[str, int]:
        counts = {t: 0 for t in _VALID_TIERS}
        for f in self.consolidated:
            counts[f.tier] = counts.get(f.tier, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# Docs loading
# ---------------------------------------------------------------------------

_DOC_EXTENSIONS = (".md", ".markdown", ".txt", ".rst", ".mdx")


def load_docs(
    docs_dir: Path,
    extensions: tuple[str, ...] = _DOC_EXTENSIONS,
    max_chars: int = _DEFAULT_MAX_CORPUS_CHARS,
) -> tuple[str, list[str]]:
    """Read every file under docs_dir matching `extensions` into a single
    corpus string, prefixed per-file with `### FILE: <relpath>` so personas
    can cite locations.

    Returns (corpus_text, list_of_relative_paths).

    Raises FileNotFoundError if docs_dir does not exist.
    Returns ("", []) if the directory is empty (callers should handle).
    """
    docs_dir = Path(docs_dir).resolve()
    if not docs_dir.exists():
        raise FileNotFoundError(f"docs_dir does not exist: {docs_dir}")
    if not docs_dir.is_dir():
        raise NotADirectoryError(f"docs_dir is not a directory: {docs_dir}")

    files: list[Path] = []
    for ext in extensions:
        files.extend(docs_dir.rglob(f"*{ext}"))
    files = sorted(set(files))

    corpus_parts: list[str] = []
    rel_paths: list[str] = []
    used_chars = 0

    for f in files:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = f.relative_to(docs_dir).as_posix()
        block = f"\n\n### FILE: {rel}\n\n{content}\n"
        if used_chars + len(block) > max_chars:
            # Budget-bound truncation. Append a marker so the persona knows
            # the corpus was capped (this is honest — no silent truncation).
            remaining = max_chars - used_chars
            if remaining > 200:
                corpus_parts.append(block[:remaining])
                corpus_parts.append(
                    f"\n\n<<<CORPUS TRUNCATED at {max_chars} chars — "
                    f"remaining files omitted from this review>>>\n"
                )
            break
        corpus_parts.append(block)
        rel_paths.append(rel)
        used_chars += len(block)

    return "".join(corpus_parts), rel_paths


# ---------------------------------------------------------------------------
# Parsing persona output
# ---------------------------------------------------------------------------

_HEADER_RE = re.compile(
    r"TRUST_REPORT:\s*SCORE=(\d+)\s+STATUS=(\w+)\s+EVIDENCE=(\d+)\s+UNCERTAINTIES=(\d+)",
    re.IGNORECASE,
)

_FIELD_RE = re.compile(
    r"^(TIER|LOCATION|WHAT|WHY|RECOMMENDATION)\s*:\s*(.*)$",
    re.IGNORECASE,
)


def parse_findings(
    raw_output: str,
    persona_name: str,
    default_severity_floor: str = "S3",
) -> tuple[list[Finding], Optional[int], Optional[str]]:
    """Parse a persona's raw LLM output into Finding objects + trust header.

    Extracts the TRUST_REPORT header (if present) and every `FINDING` block.
    Missing TIER → default_severity_floor. Missing mandatory fields →
    filled with `(unspecified)` so the object is still schema-valid.

    Returns (findings, trust_score, trust_status). Score/status None if header
    is absent.
    """
    trust_score: Optional[int] = None
    trust_status: Optional[str] = None
    m = _HEADER_RE.search(raw_output)
    if m:
        try:
            trust_score = int(m.group(1))
            trust_status = m.group(2).upper()
        except (ValueError, IndexError):
            pass

    # Split on FINDING markers. Each block is everything between markers.
    # We split on a line that is exactly FINDING (case-insensitive) with
    # optional whitespace around it.
    blocks: list[str] = []
    current: list[str] = []
    for line in raw_output.splitlines():
        if line.strip().upper() == "FINDING":
            if current:
                blocks.append("\n".join(current))
            current = []
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current))

    findings: list[Finding] = []
    for block in blocks:
        fields_found: dict[str, str] = {}
        # Collect continuation lines into the last-seen field, so multi-line
        # WHY/RECOMMENDATION survive.
        last_key: Optional[str] = None
        for line in block.splitlines():
            m2 = _FIELD_RE.match(line)
            if m2:
                key = m2.group(1).upper()
                val = m2.group(2).strip()
                fields_found[key] = val
                last_key = key
            elif last_key and line.strip():
                fields_found[last_key] = (fields_found.get(last_key, "") + " " + line.strip()).strip()

        # Skip empty blocks (the prose above the first FINDING, etc.)
        if not any(k in fields_found for k in ("TIER", "WHAT", "LOCATION")):
            continue

        tier = fields_found.get("TIER", default_severity_floor).upper().strip()
        if tier not in _VALID_TIERS:
            tier = default_severity_floor

        findings.append(Finding(
            tier=tier,
            location=fields_found.get("LOCATION", "(unspecified)").strip() or "(unspecified)",
            what=fields_found.get("WHAT", "(unspecified)").strip() or "(unspecified)",
            why=fields_found.get("WHY", "").strip(),
            recommendation=fields_found.get("RECOMMENDATION", "").strip(),
            reviewers=[persona_name],
        ))

    return findings, trust_score, trust_status


# ---------------------------------------------------------------------------
# Consolidation
# ---------------------------------------------------------------------------

def _dedupe_key(f: Finding) -> tuple[str, str]:
    """Key for dedup: (normalized_location, first_80_chars_of_what).

    Conservative: two findings are only considered duplicates when BOTH the
    location and the topic summary match closely. This avoids collapsing
    legitimately-distinct findings that happen to share a file.
    """
    loc = f.location.lower().strip()
    topic = re.sub(r"\s+", " ", f.what.lower().strip())[:80]
    return (loc, topic)


def consolidate(results: Iterable[PersonaResult]) -> list[Finding]:
    """Merge findings from multiple personas. Dedupe by (location, what-prefix),
    keep highest severity, union reviewers. Output sorted by severity then
    by location for stable diffs.
    """
    merged: dict[tuple[str, str], Finding] = {}
    for r in results:
        for f in r.findings:
            key = _dedupe_key(f)
            if key in merged:
                merged[key] = merged[key].merge_with(f)
            else:
                merged[key] = f

    all_findings = list(merged.values())
    all_findings.sort(key=lambda f: (_TIER_RANK.get(f.tier, 99), f.location, f.what))
    return all_findings


# ---------------------------------------------------------------------------
# Parallel dispatch
# ---------------------------------------------------------------------------

def _resolve_max_parallel(default: int = 5) -> int:
    """Read resources.compute.max_parallel_agents from cognitive-os.yaml if
    present. Fall back silently on the default when yaml/pyyaml/config
    missing — this keeps the library dependency-light."""
    try:
        import yaml  # type: ignore
    except ImportError:
        return default
    cfg_path = _REPO / "cognitive-os.yaml"
    if not cfg_path.exists():
        return default
    try:
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        val = (
            data.get("resources", {})
                .get("compute", {})
                .get("max_parallel_agents")
        )
        if isinstance(val, int) and val > 0:
            return val
    except Exception:  # noqa: BLE001
        pass
    return default


def _default_dispatch(prompt: str, model: str) -> dict:
    """Thin wrapper over lib.dispatch.dispatch() returning a plain dict.

    Returns {success, text, cost_usd, provider_used, error}.
    """
    from lib.dispatch import dispatch  # lazy import so tests can stub easily
    result = dispatch(
        prompt=prompt,
        providers=["qwen", "claude"],
        claude_executor=None,  # qwen-first; Claude fallback requires executor
        claude_model=model,
        task_type="doc-review",
        skill_name="doc-review-personas",
        verbose=False,
    )
    return {
        "success": result.success,
        "text": result.text,
        "cost_usd": result.cost_usd,
        "provider_used": result.provider_used,
        "error": result.error,
    }


def run_persona(
    persona: Persona,
    docs_text: str,
    model: str = "haiku",
    dispatch_fn: Optional[Callable[[str, str], dict]] = None,
) -> PersonaResult:
    """Run a single persona pass. Isolates LLM errors per-persona so one
    failure doesn't sink the whole review."""
    prompt = build_persona_prompt(persona, docs_text)
    fn = dispatch_fn or _default_dispatch
    try:
        resp = fn(prompt, model)
    except Exception as exc:  # noqa: BLE001 — one persona's failure is isolated
        return PersonaResult(
            persona=persona.name, success=False,
            error=f"dispatch raised: {exc}",
        )

    if not resp.get("success"):
        return PersonaResult(
            persona=persona.name, success=False,
            error=resp.get("error", "dispatch returned success=False"),
            raw_output=resp.get("text", ""),
            cost_usd=float(resp.get("cost_usd", 0.0)),
            provider_used=resp.get("provider_used", ""),
        )

    text = resp.get("text", "")
    findings, score, status = parse_findings(
        text, persona.name, default_severity_floor=persona.default_severity_floor,
    )
    return PersonaResult(
        persona=persona.name,
        success=True,
        findings=findings,
        trust_score=score,
        trust_status=status,
        raw_output=text,
        cost_usd=float(resp.get("cost_usd", 0.0)),
        provider_used=resp.get("provider_used", ""),
    )


def run_review(
    docs_dir: Path,
    personas: Optional[list[Persona]] = None,
    model: str = "haiku",
    max_parallel: Optional[int] = None,
    dispatch_fn: Optional[Callable[[str, str], dict]] = None,
    dry_run: bool = False,
) -> ReviewReport:
    """Top-level entry point.

    Args:
      docs_dir: path to the documentation corpus (walked recursively).
      personas: list of Persona. Defaults to default_persona_set().
      model: hint passed to dispatch. "haiku" by default; persona frontmatter
          or caller can override per-persona in the future.
      max_parallel: hard cap on concurrent persona calls. None → resolve from
          cognitive-os.yaml resources.compute.max_parallel_agents (default 5).
      dispatch_fn: test injection point. Real calls go through lib.dispatch.
      dry_run: if True, skip LLM calls and return a mock report describing
          which personas WOULD run. Useful for CLI `--dry-run` and CI.

    Returns ReviewReport with consolidated findings sorted by severity.
    """
    if personas is None:
        personas = default_persona_set()
    if not personas:
        raise ValueError("at least one persona is required")

    docs_text, files = load_docs(docs_dir)

    if not docs_text.strip():
        # Empty-corpus handling: emit one S4 review-incomplete finding per
        # persona so the report schema stays consistent.
        return ReviewReport(
            docs_dir=str(docs_dir),
            docs_files=[],
            persona_results=[
                PersonaResult(
                    persona=p.name, success=False,
                    error="empty corpus",
                    findings=[Finding(
                        tier="S4",
                        location=str(docs_dir),
                        what="REVIEW_INCOMPLETE: no documentation files found",
                        why="Corpus was empty — no review possible",
                        recommendation="Populate docs_dir before running /doc-review-personas",
                        reviewers=[p.name],
                    )],
                ) for p in personas
            ],
            consolidated=[Finding(
                tier="S4",
                location=str(docs_dir),
                what="REVIEW_INCOMPLETE: no documentation files found",
                why="Corpus was empty — no review possible",
                recommendation="Populate docs_dir before running /doc-review-personas",
                reviewers=[p.name for p in personas],
            )],
        )

    if dry_run:
        # Deterministic no-LLM preview. Each persona gets one S4 finding
        # describing the plan.
        persona_results = [
            PersonaResult(
                persona=p.name, success=True,
                findings=[Finding(
                    tier="S4",
                    location="dry-run",
                    what=f"Would dispatch persona {p.name!r} against {len(files)} docs",
                    why="dry-run mode: no API call made",
                    recommendation="Re-run without --dry-run to execute the review",
                    reviewers=[p.name],
                )],
                raw_output="(dry-run: no LLM call made)",
            ) for p in personas
        ]
        return ReviewReport(
            docs_dir=str(docs_dir),
            docs_files=files,
            persona_results=persona_results,
            consolidated=consolidate(persona_results),
        )

    max_workers = max_parallel if max_parallel is not None else _resolve_max_parallel(default=5)
    max_workers = max(1, min(max_workers, len(personas)))

    persona_results: list[PersonaResult] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(run_persona, p, docs_text, model, dispatch_fn): p
            for p in personas
        }
        for fut in concurrent.futures.as_completed(futures):
            persona_results.append(fut.result())

    # Preserve persona input order in the report for readability.
    name_order = {p.name: i for i, p in enumerate(personas)}
    persona_results.sort(key=lambda r: name_order.get(r.persona, 999))

    consolidated = consolidate(persona_results)
    total_cost = sum(r.cost_usd for r in persona_results)

    return ReviewReport(
        docs_dir=str(docs_dir),
        docs_files=files,
        persona_results=persona_results,
        consolidated=consolidated,
        total_cost_usd=total_cost,
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _section(title: str, findings: list[Finding]) -> str:
    if not findings:
        return f"### {title}\n\n_(none)_\n"
    rows = ["| Location | What | Why | Recommendation | Reviewer(s) |",
            "|----------|------|-----|----------------|-------------|"]
    for f in findings:
        def esc(s: str) -> str:
            return s.replace("|", "\\|").replace("\n", " ").strip() or "_(unspecified)_"
        rows.append(
            f"| {esc(f.location)} | {esc(f.what)} | {esc(f.why)} | "
            f"{esc(f.recommendation)} | {', '.join(f.reviewers)} |"
        )
    return f"### {title}\n\n" + "\n".join(rows) + "\n"


def render_markdown(report: ReviewReport) -> str:
    """Markdown report with Hallazgos críticos / medios / menores sections."""
    counts = report.severity_counts()
    by_tier: dict[str, list[Finding]] = {t: [] for t in _VALID_TIERS}
    for f in report.consolidated:
        by_tier[f.tier].append(f)

    lines = [
        "# Doc Review — Multi-Persona",
        "",
        f"- **docs_dir**: `{report.docs_dir}`",
        f"- **files reviewed**: {len(report.docs_files)}",
        f"- **personas**: {', '.join(r.persona for r in report.persona_results)}",
        f"- **total cost**: ${report.total_cost_usd:.4f}",
        "",
        "## Summary",
        "",
        f"- S1 BLOCKER: **{counts['S1']}**",
        f"- S2 CONCERN: **{counts['S2']}**",
        f"- S3 SUGGESTION: **{counts['S3']}**",
        f"- S4 QUESTION: **{counts['S4']}**",
        "",
        "## Hallazgos",
        "",
        _section("Críticos (S1 BLOCKER)", by_tier["S1"]),
        _section("Medios (S2 CONCERN)", by_tier["S2"]),
        _section("Menores (S3 SUGGESTION)", by_tier["S3"]),
        _section("Preguntas abiertas (S4 QUESTION)", by_tier["S4"]),
        "",
        "## Per-persona status",
        "",
        "| Persona | Status | Findings | Trust | Provider | Cost |",
        "|---------|--------|----------|-------|----------|------|",
    ]
    for r in report.persona_results:
        status = "OK" if r.success else f"FAIL ({r.error[:60]})"
        trust = f"{r.trust_score}/{r.trust_status}" if r.trust_score is not None else "_(no header)_"
        lines.append(
            f"| {r.persona} | {status} | {len(r.findings)} | {trust} | "
            f"{r.provider_used or '_'} | ${r.cost_usd:.4f} |"
        )
    return "\n".join(lines) + "\n"


def render_json(report: ReviewReport) -> str:
    """JSON serialization with stable schema."""
    payload = {
        "docs_dir": report.docs_dir,
        "docs_files": report.docs_files,
        "severity_counts": report.severity_counts(),
        "total_cost_usd": report.total_cost_usd,
        "consolidated": [asdict(f) for f in report.consolidated],
        "persona_results": [
            {
                "persona": r.persona,
                "success": r.success,
                "findings_count": len(r.findings),
                "findings": [asdict(f) for f in r.findings],
                "trust_score": r.trust_score,
                "trust_status": r.trust_status,
                "error": r.error,
                "cost_usd": r.cost_usd,
                "provider_used": r.provider_used,
            }
            for r in report.persona_results
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

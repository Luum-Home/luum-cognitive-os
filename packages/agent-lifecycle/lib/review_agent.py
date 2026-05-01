# SCOPE: os-only
"""
Review Agent — Phase 3 of learning-loop closure (ADR-096).

Post-hoc async audit of sub-agent outputs. After a parent agent completes,
a reviewer agent (different model — cross-review matrix) reads the output and
checks:
  1. Trust score validation — did the agent provide evidence for its claims?
  2. Claim accuracy — did the agent claim to write files that don't exist?
     Did it claim tests pass when they don't?
  3. Acceptance-criteria coverage — are all stated AC verifiable?

Findings are persisted to:
  - .cognitive-os/metrics/review-findings.jsonl (offline analysis)
  - Engram, observation type=review-finding (searchable by topic_key)

This module does NOT auto-modify skills or act on findings. Findings are
surfaced to /analyze-improvements (Phase 1's downstream consumer).
Closing the loop fully (review → auto-modify) is a separate follow-up after
we have quality data on review accuracy.

Cross-review matrix (locked in ADR-096 §Decision 3):
  haiku  → sonnet   (upward: cheap outputs reviewed by mid-tier)
  sonnet → opus     (upward: mid outputs reviewed by flagship)
  opus   → sonnet   (lateral: flagship reviewed by mid-tier to avoid echo chambers)
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Module constants (operator-visible defaults)
# ---------------------------------------------------------------------------

DEFAULT_SAMPLE_RATE: float = 0.2
DEFAULT_MAX_PER_DAY: int = 50

# Cross-review matrix: producer model tier → reviewer model tier
REVIEWER_MODEL_MATRIX: dict[str, str] = {
    "haiku": "sonnet",
    "sonnet": "opus",
    "opus": "sonnet",
}

# Budget state file lives under .cognitive-os/runtime/
_BUDGET_STATE_FILENAME = "review-budget.json"

# JSONL output for offline analysis
_DEFAULT_FINDINGS_JSONL = Path(".cognitive-os") / "metrics" / "review-findings.jsonl"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _project_dir() -> Path:
    """Resolve the project root from environment variables or cwd."""
    for env_var in ("COGNITIVE_OS_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        val = os.environ.get(env_var, "")
        if val:
            return Path(val)
    return Path(os.getcwd())


def _runtime_dir() -> Path:
    return _project_dir() / ".cognitive-os" / "runtime"


def _budget_state_path(state_file: Path | None = None) -> Path:
    if state_file is not None:
        return state_file
    return _runtime_dir() / _BUDGET_STATE_FILENAME


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def daily_budget_state(state_file: Path | None = None) -> dict[str, int]:
    """Load and return the daily review-dispatch budget tracker.

    Returns a dict mapping date strings (YYYY-MM-DD) → dispatch count.
    Auto-rolls over on date change: entries for dates other than today are
    preserved for history but do not affect the today-gate.

    Args:
        state_file: explicit path to budget JSON; defaults to
                    .cognitive-os/runtime/review-budget.json.
    """
    path = _budget_state_path(state_file)
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        # Sanitize: values must be ints
        return {k: int(v) for k, v in data.items() if isinstance(k, str)}
    except (json.JSONDecodeError, OSError, ValueError):
        return {}


def _save_budget_state(state: dict[str, int], state_file: Path | None = None) -> None:
    """Persist budget state dict to disk (best-effort)."""
    path = _budget_state_path(state_file)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def should_review(
    producer_output: dict[str, Any],
    sample_rate: float = DEFAULT_SAMPLE_RATE,
    daily_budget: dict[str, int] | None = None,
    max_per_day: int = DEFAULT_MAX_PER_DAY,
    state_file: Path | None = None,
) -> bool:
    """Stochastic + budget gate. Returns True if this output should be reviewed.

    Two gates, both must pass:
    1. Stochastic: random draw ≤ sample_rate (0.0 = never, 1.0 = always).
    2. Daily budget: today's dispatch count < max_per_day.

    Args:
        producer_output: the producer agent's output dict (used only for logging;
                         the stochastic gate does not inspect content).
        sample_rate: fraction of outputs to review, in [0.0, 1.0].
        daily_budget: mutable dict mapping date → count. Mutated in place if
                      review is approved (increments today's count). If None,
                      loaded from state_file automatically.
        max_per_day: daily cap; when exceeded, queue but don't dispatch.
        state_file: explicit path to budget state JSON.

    Returns:
        True iff both gates pass (review should proceed).
    """
    # Clamp sample_rate
    sample_rate = max(0.0, min(1.0, sample_rate))

    # Stochastic gate — fast path for 0.0 and 1.0
    if sample_rate == 0.0:
        return False
    if sample_rate < 1.0 and random.random() > sample_rate:
        return False

    # Budget gate
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Load persisted state if not provided
    _state_was_provided = daily_budget is not None
    if daily_budget is None:
        daily_budget = daily_budget_state(state_file)

    today_count = daily_budget.get(today, 0)
    if today_count >= max_per_day:
        return False

    # Both gates passed — increment counter and persist
    daily_budget[today] = today_count + 1
    if not _state_was_provided:
        _save_budget_state(daily_budget, state_file)

    return True


def select_reviewer_model(producer_model: str) -> str:
    """Implement the cross-review matrix (ADR-096 §Decision 3).

    The producer_model may be a full model name (e.g. "claude-sonnet-4-6")
    or an abstract tier name ("sonnet"). We extract the tier first.

    Unknown models fall back to "sonnet" (cost-bounded safe default).

    Args:
        producer_model: model name or tier string from the producer agent.

    Returns:
        Reviewer model tier string ("haiku", "sonnet", or "opus").
    """
    name = producer_model.lower()
    if "opus" in name:
        tier = "opus"
    elif "sonnet" in name:
        tier = "sonnet"
    elif "haiku" in name:
        tier = "haiku"
    else:
        # Unknown model — treat as sonnet tier (mid-range; conservative safe default).
        # This will map to opus reviewer via the matrix, which is intentionally
        # conservative: unknown producers get the highest-quality audit.
        tier = "sonnet"

    return REVIEWER_MODEL_MATRIX.get(tier, "sonnet")


def build_review_prompt(
    producer_output: dict[str, Any],
    criteria: list[str] | None = None,
) -> str:
    """Build the reviewer's audit prompt.

    Adapted from Hermes _spawn_background_review templates
    (source: .claude/plugins/hermes-agent/run_agent.py:2749-2828, MIT license).
    Hermes's memory-store and skill-store references replaced with COS
    Engram and TRUST_REPORT conventions.

    The prompt explicitly forbids rubber-stamping: the reviewer MUST identify
    at least 1 gap, uncertainty, or unverifiable claim.

    Args:
        producer_output: dict with at minimum a "text" or "output" field
                         containing the agent's response. Optional keys:
                         "task_description", "trust_report", "producer_model",
                         "producer_id", "tool_call_id".
        criteria: list of acceptance-criteria strings from the task. May be
                  empty or None if the task had no explicit AC.

    Returns:
        Fully-formed reviewer prompt string.
    """
    task_description = producer_output.get("task_description") or producer_output.get("task", "")
    output_text = (
        producer_output.get("text")
        or producer_output.get("output")
        or producer_output.get("tool_result")
        or ""
    )
    trust_report = producer_output.get("trust_report") or ""
    producer_model = producer_output.get("producer_model") or "unknown"
    producer_id = producer_output.get("producer_id") or "unknown"

    # Format acceptance criteria section
    if criteria:
        ac_block = "\n".join(f"  - {c}" for c in criteria)
        ac_section = f"""
## Acceptance Criteria (from task)

{ac_block}

For each criterion above: state whether the agent's output satisfies it,
partially satisfies it, or leaves it unverified. Cite specific evidence
from the output.
"""
    else:
        ac_section = """
## Acceptance Criteria

No explicit acceptance criteria were provided for this task. Your job is to
infer what criteria should have been present and check whether the output would
satisfy them.
"""

    # Format trust report section
    if trust_report:
        trust_section = f"""
## Agent's Trust Report (self-assessed)

{trust_report}

Evaluate whether the agent's self-assessed score is accurate. Is the
stated evidence sufficient? Are the uncertainties honest?
"""
    else:
        trust_section = """
## Agent's Trust Report

The agent did NOT include a Trust Report. This is a mandatory violation.
Document it as a critical gap in your findings.
"""

    prompt = f"""You are an independent auditor reviewing a sub-agent's completed task output.
Your role is to verify accuracy, completeness, and honesty — not to redo the work.

## Task Context

**Producer ID**: {producer_id}
**Producer Model**: {producer_model}
**Task Description**: {task_description or "(not provided)"}

## Agent Output (to review)

{output_text[:8000]}{"... [truncated]" if len(output_text) > 8000 else ""}
{ac_section}
{trust_section}
## Your Audit Checklist

Work through each item. For each: PASS / FAIL / PARTIAL / UNVERIFIABLE.

1. **Claim accuracy**: For every factual claim in the output (files written,
   tests passed, commands executed), assess whether the claim is verifiable
   from the output text. Flag any claim that cannot be verified.

2. **Trust report honesty**: Is the agent's self-score calibrated? Score
   inflation (claiming >0.8 with thin evidence) is a gap. Score deflation
   (false modesty) is also notable.

3. **Acceptance criteria coverage**: Does the output demonstrably satisfy
   each criterion? Cite the specific passage that provides evidence.

4. **Hallucination indicators**: Look for confident statements about external
   state (file system, test results, API responses) that are asserted without
   corroborating output. These are high-risk.

5. **Completeness**: Does the output leave any stated deliverable absent or
   stubbed (TODO, FIXME, placeholder)?

## CRITICAL INSTRUCTION — No Rubber-Stamping

You MUST identify at least 1 gap, uncertainty, or unverifiable claim. If the
output appears flawless, you are likely missing something — look harder. An
audit that finds zero issues is itself a finding of reviewer overconfidence.

## Required Output Format

Respond with a structured finding in this exact format:

REVIEW_SCORE: <integer 0-100>
EVIDENCE:
- <bullet: specific evidence for any PASS items>
GAPS:
- <bullet: gap, unverifiable claim, or missing criterion — at least 1>
RECOMMENDATIONS:
- <bullet: concrete action to address each gap>
REVIEWER_CONFIDENCE: <integer 0-100>
UNCERTAINTY: <1-2 sentences on what you could not verify from the text alone>

Do not include commentary outside this format.
"""
    return prompt


def parse_review_response(response: str) -> dict[str, Any]:
    """Extract structured fields from the reviewer's output.

    Tolerates minor formatting variations (extra whitespace, mixed case
    section headers). Returns a dict with keys: score, evidence, gaps,
    recommendations, reviewer_confidence, uncertainty.

    Malformed input returns a dict with score=-1 and an "error" key.

    Args:
        response: raw text response from the reviewer agent.

    Returns:
        Dict with parsed fields. On parse failure: {"score": -1, "error": ...}
    """
    if not response or not response.strip():
        return {"score": -1, "error": "empty reviewer response"}

    def _extract_section(text: str, key: str) -> str:
        """Extract everything after 'KEY:' up to the next all-caps section header."""
        pattern = rf"(?i){re.escape(key)}:\s*\n?(.*?)(?=\n[A-Z_]+:|$)"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_inline(text: str, key: str) -> str:
        """Extract single-line value after 'KEY: value'."""
        pattern = rf"(?i){re.escape(key)}:\s*(.+)"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        return ""

    def _parse_bullets(text: str) -> list[str]:
        """Split bullet-pointed text into a list of strings."""
        lines = text.split("\n")
        bullets: list[str] = []
        for line in lines:
            line = line.strip().lstrip("-•*").strip()
            if line:
                bullets.append(line)
        return bullets

    # Extract score
    score_str = _extract_inline(response, "REVIEW_SCORE")
    try:
        score = int(re.sub(r"[^0-9]", "", score_str))
        score = max(0, min(100, score))
    except (ValueError, TypeError):
        score = -1

    # Extract reviewer confidence
    conf_str = _extract_inline(response, "REVIEWER_CONFIDENCE")
    try:
        reviewer_confidence = int(re.sub(r"[^0-9]", "", conf_str))
        reviewer_confidence = max(0, min(100, reviewer_confidence))
    except (ValueError, TypeError):
        reviewer_confidence = -1

    evidence = _parse_bullets(_extract_section(response, "EVIDENCE"))
    gaps = _parse_bullets(_extract_section(response, "GAPS"))
    recommendations = _parse_bullets(_extract_section(response, "RECOMMENDATIONS"))
    uncertainty = _extract_inline(response, "UNCERTAINTY") or _extract_section(response, "UNCERTAINTY")

    result: dict[str, Any] = {
        "score": score,
        "evidence": evidence,
        "gaps": gaps,
        "recommendations": recommendations,
        "reviewer_confidence": reviewer_confidence,
        "uncertainty": uncertainty,
    }

    # Flag parse issues but still return partial data
    issues: list[str] = []
    if score == -1:
        issues.append("could not parse REVIEW_SCORE")
    if not gaps:
        issues.append("GAPS section missing or empty (possible rubber-stamp)")
    if issues:
        result["parse_warnings"] = issues

    return result


def persist_finding(
    finding: dict[str, Any],
    jsonl_path: Path | None = None,
    engram_topic: str = "review-finding",
) -> None:
    """Write finding to JSONL and save Engram observation type=review-finding.

    JSONL append is atomic per POSIX for writes ≤ PIPE_BUF; safe for concurrent
    writers. Engram save is best-effort: failure is logged to stderr but does
    not raise.

    Args:
        finding: dict with keys: score, evidence, gaps, recommendations,
                 producer_id, reviewer_id, reviewer_model, task_description,
                 timestamp (all optional extras tolerated).
        jsonl_path: path to review-findings.jsonl; defaults to
                    .cognitive-os/metrics/review-findings.jsonl relative to
                    project root.
        engram_topic: Engram topic_key for this finding. Default produces
                      unique keys per finding via content hash suffix.
    """
    # Resolve JSONL path
    if jsonl_path is None:
        jsonl_path = _project_dir() / _DEFAULT_FINDINGS_JSONL

    # Stamp timestamp if absent
    if "timestamp" not in finding:
        finding = {**finding, "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}

    # Stable content hash for deduplication (Engram topic_key suffix)
    content_sig = hashlib.sha256(
        json.dumps(finding, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:8]
    topic_key = f"{engram_topic}/{finding.get('producer_id', 'unknown')}-{content_sig}"

    # Append to JSONL
    try:
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(finding, ensure_ascii=False, default=str)
        with jsonl_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError as exc:
        import sys
        print(f"[review_agent] JSONL write failed: {exc}", file=sys.stderr)

    # Engram save (best-effort via CLI subprocess)
    _engram_save(finding, topic_key)


def _engram_save(finding: dict[str, Any], topic_key: str) -> None:
    """Persist finding to Engram via mem_save convention.

    Uses the Engram MCP client if available, otherwise emits a structured
    marker to stdout that the hook infrastructure can capture.

    This is best-effort: failure is silently swallowed (Engram must never
    crash the review pipeline).
    """
    try:
        # Try the in-process Engram client first (fastest, no subprocess)
        from lib.engram_client import mem_save  # type: ignore[import]
        score = finding.get("score", -1)
        gaps = finding.get("gaps", [])
        gaps_text = "\n".join(f"- {g}" for g in gaps) if gaps else "- (none recorded)"
        content = (
            f"Review score: {score}/100\n"
            f"Producer: {finding.get('producer_id', 'unknown')} "
            f"(model: {finding.get('producer_model', 'unknown')})\n"
            f"Reviewer: {finding.get('reviewer_id', 'unknown')} "
            f"(model: {finding.get('reviewer_model', 'unknown')})\n"
            f"Task: {str(finding.get('task_description', ''))[:200]}\n\n"
            f"Gaps:\n{gaps_text}\n\n"
            f"Uncertainty: {finding.get('uncertainty', '')}"
        )
        mem_save(
            title=f"Review finding: {finding.get('producer_id', 'unknown')} score={score}",
            content=content,
            observation_type="review-finding",
            topic_key=topic_key,
            project="luum-agent-os",
        )
    except Exception:  # noqa: BLE001
        # Fall back to structured stdout marker (hook infrastructure captures it)
        import sys
        print(
            f"[review_agent:engram_marker] topic_key={topic_key} "
            f"score={finding.get('score', -1)} "
            f"producer={finding.get('producer_id', 'unknown')}",
            file=sys.stderr,
        )

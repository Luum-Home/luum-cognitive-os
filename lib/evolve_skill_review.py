#!/usr/bin/env python3
# SCOPE: os-only
"""evolve_skill_review — LLM-driven extraction review job for the evolve loop spike.

ADR-262 §Decision 1: reads session turn logs, calls the LLM via lib.dispatch,
filters by confidence threshold, deduplicates, and enqueues passing proposals.

Clean-room implementation per ADR-259. LLM prompt authored from functional
criteria in ADR-262 §Decision 1 — no external pattern (ADR-259) source material incorporated.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "cognitive-os.yaml"

# Default config values (overridden by cognitive-os.yaml evolve.* section)
# DEFAULT_CADENCE_TURNS: calibrated to luum session lengths from skill-events.jsonl
# (median observed cluster of 4 turns before a recurring pattern stabilises).
DEFAULT_CADENCE_TURNS = 4
# DEFAULT_CONFIDENCE_THRESHOLD: calibration baseline; tighter than 0.72 to reduce
# false-positive skill proposals on noisy short sessions.
DEFAULT_CONFIDENCE_THRESHOLD = 0.70
DEFAULT_QUEUE_CAP = 50
DEFAULT_ENABLED = False


def _load_evolve_config() -> dict:
    """Load evolve section from cognitive-os.yaml, with fallbacks."""
    try:
        with CONFIG_PATH.open() as fh:
            cfg = yaml.safe_load(fh) or {}
        return cfg.get("evolve", {})
    except Exception as exc:
        logger.warning("Could not load cognitive-os.yaml: %s — using defaults", exc)
        return {}


def _read_session_turns(session_dir: Path, last_n: int) -> list[dict]:
    """Read the last N turn files from a session's turns/ directory.

    Each turn file is expected to be JSON. Returns empty list on any error.
    Turn files are sorted by name (lexicographic = chronological for ISO timestamps).
    """
    turns_dir = session_dir / "turns"
    if not turns_dir.is_dir():
        logger.debug("No turns directory found at %s", turns_dir)
        return []

    turn_files = sorted(turns_dir.glob("*.json"))
    if not turn_files:
        logger.debug("No turn files found in %s", turns_dir)
        return []

    selected = turn_files[-last_n:]
    turns = []
    for tf in selected:
        try:
            with tf.open() as fh:
                data = json.load(fh)
            turns.append(data)
        except Exception as exc:
            logger.warning("Skipping turn file %s: %s", tf.name, exc)
    return turns


def _build_llm_prompt(turns: list[dict], confidence_threshold: float) -> str:
    """Build a clean-room LLM prompt for skill candidate extraction.

    Functional criteria (ADR-262 §Decision 1):
    - Identify recurrent patterns across turns that represent reusable workflows.
    - Identify gaps where a skill could reduce repeated setup or orchestration steps.
    - Identify existing skills that could be improved based on observed usage friction.
    - Each candidate must include a confidence score reflecting true reusability.
    - Confidence >= {threshold} required for a proposal to be worthwhile.
    - Output must be strict JSON array, no prose.

    The prompt is written from these criteria, not from any external source.
    """
    # Serialize turn data, truncating to avoid token overflow
    MAX_TURN_CHARS = 4000
    turn_summaries = []
    for i, turn in enumerate(turns):
        raw = json.dumps(turn, ensure_ascii=False)
        if len(raw) > MAX_TURN_CHARS:
            raw = raw[:MAX_TURN_CHARS] + " ... [truncated]"
        turn_summaries.append(f"--- Turn {i + 1} ---\n{raw}")

    turns_text = "\n\n".join(turn_summaries) if turn_summaries else "(no turn data)"

    prompt = f"""You are a skill-extraction agent for an AI operating system. Your job is to analyze recent agent session turns and identify skill candidates: reusable workflows, patterns, or prompt structures that would benefit from being captured as a formal skill.

TURN DATA (last {len(turns)} turns):
{turns_text}

EXTRACTION CRITERIA:
1. Identify patterns that appear recurrently or that involved significant repeated setup.
2. Identify workflows where a named, parameterizable skill would reduce future effort.
3. Identify existing patterns that could be improved based on observed friction or repeated corrections.
4. For each candidate, assess confidence (0.0–1.0) that it is genuinely reusable and not session-specific.
5. Only include candidates with confidence >= {confidence_threshold:.2f}.
6. For `skill_revision` kind: the title must reference the existing skill being improved.

OUTPUT FORMAT — respond with ONLY a valid JSON array, no prose, no markdown fences:
[
  {{
    "kind": "skill_new",
    "title": "<short imperative title, max 60 chars>",
    "rationale": "<why this pattern is reusable, 1-3 sentences>",
    "draft": "<SKILL.md content: frontmatter + description + usage + acceptance criteria>",
    "confidence": 0.85
  }},
  {{
    "kind": "skill_revision",
    "title": "<existing skill name: specific improvement>",
    "rationale": "<what friction was observed and why the revision improves it>",
    "draft": "<revision description: what to change and why>",
    "confidence": 0.76
  }}
]

If no candidates meet the criteria, respond with an empty array: []
"""
    return prompt


def _parse_llm_response(text: str) -> list[dict]:
    """Parse the LLM response, extracting a JSON array of proposals.

    Handles:
    - Pure JSON response
    - JSON wrapped in markdown code fences
    - Partial JSON (attempts extraction)
    """
    text = text.strip()
    if not text:
        return []

    # Strip markdown fences if present
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if fence_match:
        text = fence_match.group(1).strip()

    # Find first [ and last ] to extract the array
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        logger.warning("LLM response does not contain a JSON array: %s", text[:200])
        return []

    array_text = text[start : end + 1]
    try:
        data = json.loads(array_text)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse LLM JSON array: %s — text: %s", exc, array_text[:200])
        return []

    if not isinstance(data, list):
        logger.warning("LLM response is not a list: %s", type(data))
        return []

    return data


def _validate_proposal_dict(item: Any, confidence_threshold: float) -> bool:
    """Return True if the dict has all required fields and meets confidence threshold."""
    if not isinstance(item, dict):
        return False
    required = {"kind", "title", "rationale", "draft", "confidence"}
    if not required.issubset(item.keys()):
        logger.debug("Proposal missing required fields: %s", required - item.keys())
        return False
    if item.get("kind") not in {"skill_new", "skill_revision"}:
        logger.debug("Invalid kind: %s", item.get("kind"))
        return False
    try:
        conf = float(item["confidence"])
    except (TypeError, ValueError):
        return False
    if conf < confidence_threshold:
        logger.debug(
            "Confidence %.2f below threshold %.2f for '%s' — discarded",
            conf,
            confidence_threshold,
            item.get("title", "")[:40],
        )
        return False
    return True


class EvolveSkillReview:
    """LLM-driven review job that reads session turns and enqueues skill proposals.

    Usage::

        review = EvolveSkillReview()
        count = review.run(session_dir=Path(".cognitive-os/sessions/abc123"))
        print(f"Enqueued {count} proposals")
    """

    def __init__(
        self,
        queue=None,  # EvolveTaskQueue instance; created lazily if None
        config: dict | None = None,
        _dispatch_fn=None,  # Injection point for tests
    ) -> None:
        self._queue = queue
        self._config = config if config is not None else _load_evolve_config()
        self._dispatch_fn = _dispatch_fn

    @property
    def queue(self):
        if self._queue is None:
            from lib.evolve_task_queue import EvolveTaskQueue
            self._queue = EvolveTaskQueue()
        return self._queue

    @property
    def confidence_threshold(self) -> float:
        return float(self._config.get("confidence_threshold", DEFAULT_CONFIDENCE_THRESHOLD))

    @property
    def cadence_turns(self) -> int:
        # Support both config key variants from ADR-262 (cadence_turns and review_interval_turns)
        v = self._config.get("cadence_turns") or self._config.get("review_interval_turns")
        try:
            return int(v) if v is not None else DEFAULT_CADENCE_TURNS
        except (TypeError, ValueError):
            return DEFAULT_CADENCE_TURNS

    def _dispatch(self, prompt: str) -> str:
        """Call the LLM via lib.dispatch, returning the response text."""
        if self._dispatch_fn is not None:
            return self._dispatch_fn(prompt)

        from lib.dispatch import dispatch  # lazy import — tests can stub via _dispatch_fn

        result = dispatch(
            prompt=prompt,
            providers=["qwen", "claude"],
            task_type="skill_extraction",
            skill_name="evolve_skill_review",
        )
        if not result.success:
            logger.warning("LLM dispatch failed for evolve review: %s", result.error)
            return ""
        return result.text

    def run(self, session_dir: Path | None = None) -> int:
        """Execute one review cycle.

        Reads the last N turns from session_dir, calls the LLM, filters by
        confidence, deduplicates, and enqueues passing proposals.

        Returns the number of proposals successfully enqueued.
        """
        n_turns = self.cadence_turns
        threshold = self.confidence_threshold

        # Resolve session directory
        if session_dir is None:
            session_dir = _find_active_session_dir()

        if session_dir is None or not session_dir.is_dir():
            logger.info("No active session directory found — skipping evolve review")
            return 0

        turns = _read_session_turns(session_dir, last_n=n_turns)
        if not turns:
            logger.info("No turn data in %s — skipping evolve review", session_dir)
            return 0

        prompt = _build_llm_prompt(turns, threshold)
        raw_response = self._dispatch(prompt)
        if not raw_response:
            return 0

        candidates = _parse_llm_response(raw_response)
        enqueued = 0

        for item in candidates:
            if not _validate_proposal_dict(item, threshold):
                continue

            from lib.evolve_task_queue import EvolveProposal

            try:
                proposal = EvolveProposal(
                    kind=item["kind"],
                    title=str(item["title"])[:120],
                    rationale=str(item["rationale"])[:500],
                    draft=str(item["draft"]),
                    confidence=float(item["confidence"]),
                )
            except (ValueError, KeyError) as exc:
                logger.warning("Skipping malformed proposal: %s", exc)
                continue

            result = self.queue.enqueue(proposal)
            if result is not None:
                enqueued += 1
                logger.info("Enqueued proposal '%s' (confidence=%.2f)", proposal.title[:60], proposal.confidence)

        logger.info("Evolve review complete: %d/%d candidates enqueued", enqueued, len(candidates))
        return enqueued


def _find_active_session_dir() -> Path | None:
    """Locate the most recently modified session directory.

    Searches .cognitive-os/sessions/ for subdirectories and returns the most
    recently modified one that contains a turns/ subdirectory.
    """
    sessions_root = REPO_ROOT / ".cognitive-os" / "sessions"
    if not sessions_root.is_dir():
        return None

    candidates = []
    for session_dir in sessions_root.iterdir():
        if session_dir.is_dir() and (session_dir / "turns").is_dir():
            candidates.append(session_dir)

    if not candidates:
        return None

    # Most recently modified
    return max(candidates, key=lambda p: p.stat().st_mtime)

# SCOPE: both
"""
Feedback Detector — Detects implicit and explicit user feedback signals.

Extends prompt_classifier.py's explicit feedback detection with:
- Implicit acceptance: user moves forward without complaint
- Implicit rejection: user repeats request differently
- Correction: user redirects approach
- Escalation to manual: user takes over

Inspired by: Hermes _SKILL_REVIEW_PROMPT pattern (MIT license)
But implemented deterministically with regex, not LLM calls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


class FeedbackType(Enum):
    EXPLICIT_POSITIVE = "explicit_positive"   # "perfect", "exactly", "great"
    EXPLICIT_NEGATIVE = "explicit_negative"   # "no", "wrong", "revert"
    IMPLICIT_POSITIVE = "implicit_positive"   # user continues with new task
    IMPLICIT_NEGATIVE = "implicit_negative"   # user repeats same request differently
    CORRECTION = "correction"                  # "actually", "instead", "I meant"
    ESCALATION = "escalation"                  # "I'll do it myself"
    NEUTRAL = "neutral"                        # no signal detected


@dataclass
class FeedbackSignal:
    type: FeedbackType
    confidence: float           # 0.0 to 1.0
    content: str                # the original message
    detail: Optional[str] = None  # extracted detail (e.g., what was corrected to)


# ---------------------------------------------------------------------------
# Pattern helpers (mirrors prompt_classifier.py style)
# ---------------------------------------------------------------------------

def _compile_patterns(patterns: List[Tuple[str, float]]) -> List[Tuple[re.Pattern, float]]:
    """Compile regex patterns with case-insensitive flag."""
    return [(re.compile(p, re.IGNORECASE), w) for p, w in patterns]


def _score_patterns(text: str, patterns: List[Tuple[re.Pattern, float]]) -> float:
    """Return the max weight among all matching patterns."""
    max_score = 0.0
    for pattern, weight in patterns:
        if pattern.search(text):
            max_score = max(max_score, weight)
    return max_score


# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

_EXPLICIT_POSITIVE_PATTERNS = _compile_patterns(
    [
        # Positive phrases
        (r"\b(perfect|exactly|great(?: job)?|nice(?: work)?|well done|that'?s right|yes that'?s it|looks good|spot on|nailed it|love it|awesome)\b", 1.0),
        # Additional variants
        (r"\b(perfect|great|excellent|nice|that is it|very good|turned out (well|great|perfect))\b", 1.0),
        # Keep-doing patterns (high-weight explicit positive)
        (r"\b(keep doing|keep it up|keep going|continue like this)\b", 1.0),
    ]
)

_EXPLICIT_NEGATIVE_PATTERNS = _compile_patterns(
    [
        # Order matters: "that's not" before generic "not"
        (r"\b(that'?s (wrong|not right|not what I|incorrect))\b", 1.0),
        (r"\b(wrong|revert|undo|rollback|don'?t do that|stop doing|not what I wanted|incorrect|bad idea)\b", 1.0),
        (r"^no[,!.]?\s*$", 1.0),                      # bare "no"
        (r"\bno[,!.]?\s+(don'?t|stop|never|that)\b", 1.0),
        # Additional variants
        (r"^no[,!.]?\s*(it|this|that)\b", 1.0),
    ]
)

_CORRECTION_PATTERNS = _compile_patterns(
    [
        # Correction openers
        (r"\b(actually[,]?\s|instead[,]?\s|I meant[,]?\s|rather[,]?\s|should be[,]?\s|not .+ use|correction[,:])", 0.7),
        # "X, not Y" or "use X not Y" patterns
        (r"\buse\s+\w+\s+(not|instead of)\b", 0.7),
        (r"\bnot\s+\w+[,]?\s+(use|try|do)\b", 0.7),
        # Additional variants correction openers
        (r"\b(in reality[,]?\s|better[,]?\s|I meant[,]?\s|should be[,]?\s|use .+ not[,]?\s|correction[,:])", 0.7),
    ]
)

# Explicit escalation — user signals they will handle it themselves
_ESCALATION_PATTERNS = _compile_patterns(
    [
        # Self-escalation phrases
        (r"\b(I'?ll do it (myself|manually)|let me do it|I'?ll handle it|never mind|forget it|I'?ll fix it myself|I'?ll take it from here)\b", 1.0),
    ]
)

# Action verbs that signal the user is issuing a NEW task (implicit positive)
_ACTION_VERB_PATTERNS = _compile_patterns(
    [
        (r"^(please\s+)?(build|fix|add|implement|create|write|make|set up|configure|deploy|refactor|migrate|update|remove|delete|install|upgrade|integrate|debug|optimize)\b", 0.6),
        (r"^(please\s+)?test\b", 0.6),
        (r"\b(build\w+|fix\w+|add\w+|implement\w+|create\w+|write\w+|configure\w+|deploy\w+|refactor\w*|migrate\w+|update\w+|delete\w+|install\w+|integrate\w+|optimize\w+|let us build)\b", 0.6),
        (r"^\/\w+", 0.5),   # slash command = new task
    ]
)


# ---------------------------------------------------------------------------
# Similarity helpers (for implicit negative detection)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> set:
    """Simple word-level tokenizer, lowercased, strips punctuation."""
    words = re.findall(r"[a-z]+", text.lower())
    # Remove very common stop-words to focus on content words
    stops = {
        "the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or",
        "is", "it", "that", "this", "i", "you", "me", "my", "your",
    }
    return {w for w in words if w not in stops and len(w) > 2}


def _jaccard_similarity(a: set, b: set) -> float:
    """Jaccard similarity between two token sets."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ---------------------------------------------------------------------------
# FeedbackDetector
# ---------------------------------------------------------------------------

class FeedbackDetector:
    """Detects feedback signals from user messages.

    Combines explicit pattern matching (high confidence) with
    implicit contextual signals (lower confidence) derived from
    comparing the current message to the previous agent task.
    """

    def detect(self, message: str, previous_task: str = "") -> FeedbackSignal:
        """Analyze a user message for feedback signals.

        Args:
            message: The user's message.
            previous_task: Description or summary of what the agent just did.

        Returns:
            FeedbackSignal with type, confidence, and optional detail.
        """
        if not message or not message.strip():
            return FeedbackSignal(
                type=FeedbackType.NEUTRAL,
                confidence=0.0,
                content=message or "",
            )

        stripped = message.strip()

        # --- Priority 1: Escalation (user takes over) ---
        esc_score = _score_patterns(stripped, _ESCALATION_PATTERNS)
        if esc_score >= 1.0:
            return FeedbackSignal(
                type=FeedbackType.ESCALATION,
                confidence=esc_score,
                content=stripped,
            )

        # --- Priority 2: Explicit negative ---
        neg_score = _score_patterns(stripped, _EXPLICIT_NEGATIVE_PATTERNS)

        # --- Priority 3: Explicit positive ---
        pos_score = _score_patterns(stripped, _EXPLICIT_POSITIVE_PATTERNS)

        # --- Priority 4: Correction ---
        cor_score = _score_patterns(stripped, _CORRECTION_PATTERNS)

        # Pick the best explicit signal (if any)
        explicit_best = max(pos_score, neg_score, cor_score)

        if explicit_best > 0:
            if pos_score == explicit_best:
                return FeedbackSignal(
                    type=FeedbackType.EXPLICIT_POSITIVE,
                    confidence=pos_score,
                    content=stripped,
                )
            if neg_score == explicit_best:
                return FeedbackSignal(
                    type=FeedbackType.EXPLICIT_NEGATIVE,
                    confidence=neg_score,
                    content=stripped,
                )
            # correction
            return FeedbackSignal(
                type=FeedbackType.CORRECTION,
                confidence=cor_score,
                content=stripped,
                detail=self._extract_correction_target(stripped),
            )

        # --- Priority 5: Implicit signals (require previous_task context) ---
        if previous_task and previous_task.strip():
            implicit = self._detect_implicit(stripped, previous_task.strip())
            if implicit is not None:
                return implicit

        # --- Default: neutral ---
        return FeedbackSignal(
            type=FeedbackType.NEUTRAL,
            confidence=0.0,
            content=stripped,
        )

    # ------------------------------------------------------------------
    # Implicit signal helpers
    # ------------------------------------------------------------------

    def _detect_implicit(self, message: str, previous_task: str) -> Optional[FeedbackSignal]:
        """Detect implicit positive/negative feedback by comparing to previous_task."""

        msg_tokens = _tokenize(message)
        prev_tokens = _tokenize(previous_task)

        similarity = _jaccard_similarity(msg_tokens, prev_tokens)

        # Implicit negative: high token overlap but different structure
        # (user is re-asking the same thing, signaling the previous attempt failed)
        if similarity >= 0.4:
            # Additional structural signal: message is substantially different
            # in length or phrasing while sharing many content words
            len_ratio = len(message) / max(len(previous_task), 1)
            if 0.3 <= len_ratio <= 3.0:
                # Looks like a rephrased repetition — implicit rejection
                return FeedbackSignal(
                    type=FeedbackType.IMPLICIT_NEGATIVE,
                    confidence=min(0.5, similarity),
                    content=message,
                    detail=f"Similarity to previous task: {similarity:.2f}",
                )

        # Implicit positive: message starts a clearly NEW task (low overlap)
        # and contains an action verb
        if similarity < 0.15:
            action_score = _score_patterns(message, _ACTION_VERB_PATTERNS)
            if action_score >= 0.5:
                return FeedbackSignal(
                    type=FeedbackType.IMPLICIT_POSITIVE,
                    confidence=0.3,
                    content=message,
                    detail="User moved on to a new task",
                )

        return None

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_correction_target(text: str) -> Optional[str]:
        """Try to extract what the user is correcting TO (if stated)."""
        # "not X, use Y" / "use X not Y" patterns
        m = re.search(r"use\s+(\w+)\s+(?:not|instead of)\s+(\w+)", text, re.IGNORECASE)
        if m:
            return f"use '{m.group(1)}' instead of '{m.group(2)}'"
        m = re.search(r"(?:instead|actually)[,]?\s+(?:use\s+)?(.+)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return None

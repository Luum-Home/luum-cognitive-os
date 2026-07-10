# SCOPE: both
"""Prompt Classifier — Categorize user prompts for selective engram capture.

Classifies user messages into categories and determines whether they should
be persisted via mem_save_prompt. Captures task requests, decisions, feedback,
and context while skipping acknowledgments, status queries, and navigation.

Uses repository-authored regex patterns.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class PromptCategory(str, Enum):
    """Categories for user prompts."""

    TASK_REQUEST = "task_request"
    DECISION = "decision"
    FEEDBACK = "feedback"
    CONTEXT = "context"
    STATUS_QUERY = "status_query"
    NAVIGATION = "navigation"
    ACKNOWLEDGMENT = "acknowledgment"
    UNKNOWN = "unknown"


# Categories that should be captured to engram
_CAPTURE_CATEGORIES = frozenset(
    {
        PromptCategory.TASK_REQUEST,
        PromptCategory.DECISION,
        PromptCategory.FEEDBACK,
        PromptCategory.CONTEXT,
    }
)

# Categories that should NOT be captured
_SKIP_CATEGORIES = frozenset(
    {
        PromptCategory.STATUS_QUERY,
        PromptCategory.NAVIGATION,
        PromptCategory.ACKNOWLEDGMENT,
    }
)


@dataclass(frozen=True)
class ClassificationResult:
    """Result of prompt classification."""

    category: PromptCategory
    should_capture: bool
    confidence: float  # 0.0 to 1.0

    def __str__(self) -> str:
        return f"{self.category.value} (capture={self.should_capture}, confidence={self.confidence:.2f})"


# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

# Each pattern set is a list of (compiled_regex, weight) tuples.
# Weights contribute to confidence scoring.

def _compile_patterns(patterns: List[Tuple[str, float]]) -> List[Tuple[re.Pattern, float]]:
    """Compile regex patterns with case-insensitive flag."""
    return [(re.compile(p, re.IGNORECASE), w) for p, w in patterns]


_TASK_PATTERNS = _compile_patterns(
    [
        # Action verbs — imperative/infinitive forms only
        (r"\b(build|fix|add|implement|create|write|make|set up|configure|deploy|refactor|migrate|update|remove|delete|install|upgrade|integrate|debug|optimize)\b", 0.7),
        # "test" as a verb command (not noun usage like "the test")
        (r"^(please\s+)?test\b", 0.7),
        # Imperative patterns
        (r"^(please\s+)?(can you|could you|I need you to|I want you to)", 0.5),
        (r"^(please\s+)?(can you|could you|I need you to|I want you to)", 0.5),
        # SDD commands
        (r"\/sdd-(new|ff|apply|verify|explore|continue)", 0.9),
        # Direct commands
        (r"^\/\w+", 0.4),
    ]
)

_DECISION_PATTERNS = _compile_patterns(
    [
        # Decision language
        (r"\b(use|go with|choose|prefer|let'?s do|let'?s go with|switch to|adopt|pick|select|we should|I want to use)\b", 0.6),
        # Additional decision language
        (r"\b(use|go with|choose|prefer|let us|switch to|adopt|select)\b", 0.6),
        # Explicit decision markers
        (r"\b(decision|decided|approach|strategy|the plan is)\b", 0.5),
    ]
)

_FEEDBACK_PATTERNS = _compile_patterns(
    [
        # Negative feedback
        (r"\b(don'?t|stop|no more|that'?s wrong|incorrect|bad|revert|undo|rollback|not what I)\b", 0.7),
        # Positive feedback
        (r"\b(keep doing|perfect|exactly|great job|that'?s right|correct|well done|nice)\b", 0.6),
        # Correction patterns
        (r"\b(actually|instead|rather|correction|I meant)\b", 0.6),
        (r"\b(in reality|better|correction|I meant to say)\b", 0.6),
    ]
)

_CONTEXT_PATTERNS = _compile_patterns(
    [
        # Context markers — high weight for clear context markers
        (r"\b(working on|the goal is|deadline|for context|fyi|note that|keep in mind|remember that)\b", 0.8),
        (r"\b(we need|the project|background)\b", 0.6),
        # Project info patterns
        (r"\b(the stack is|we use|our (api|database|service|framework))\b", 0.5),
    ]
)

_STATUS_PATTERNS = _compile_patterns(
    [
        # Status queries — high weight for clear status markers
        (r"\b(what'?s left|status|how'?s|progress|where are we|what remains|how far|what did you)\b", 0.8),
        # Question about current state
        (r"^(what|how|where|when|which|who)\b.*\?$", 0.3),
    ]
)

_NAVIGATION_PATTERNS = _compile_patterns(
    [
        # Navigation
        (r"\b(show me|read file|open|check|look at|display|list|cat|grep|find)\b", 0.6),
        # File references
        (r"\b(the file|this file|that file|in file)\b", 0.3),
    ]
)

_ACKNOWLEDGMENT_PATTERNS = _compile_patterns(
    [
        # Acknowledgments (short)
        (r"^(ok|okay|yes|yep|yeah|sure|got it|thanks|thank you|right|alright|go ahead|proceed|continue|lgtm|ack|roger|copy)\s*[.!]?\s*$", 0.9),
    ]
)


# ---------------------------------------------------------------------------
# Classification logic
# ---------------------------------------------------------------------------


def _score_patterns(
    text: str, patterns: List[Tuple[re.Pattern, float]]
) -> float:
    """Score text against a set of patterns. Returns max weight of any match."""
    max_score = 0.0
    for pattern, weight in patterns:
        if pattern.search(text):
            max_score = max(max_score, weight)
    return max_score


def classify_prompt(text: str) -> ClassificationResult:
    """Classify a user prompt into a category.

    Args:
        text: The user's message text.

    Returns:
        ClassificationResult with category, should_capture flag, and confidence.
    """
    if not text or not text.strip():
        return ClassificationResult(
            category=PromptCategory.UNKNOWN,
            should_capture=False,
            confidence=0.0,
        )

    stripped = text.strip()

    # Check acknowledgments first (very short messages)
    ack_score = _score_patterns(stripped, _ACKNOWLEDGMENT_PATTERNS)
    if ack_score > 0.5 and len(stripped.split()) <= 5:
        return ClassificationResult(
            category=PromptCategory.ACKNOWLEDGMENT,
            should_capture=False,
            confidence=ack_score,
        )

    # Score all categories
    scores = {
        PromptCategory.TASK_REQUEST: _score_patterns(stripped, _TASK_PATTERNS),
        PromptCategory.DECISION: _score_patterns(stripped, _DECISION_PATTERNS),
        PromptCategory.FEEDBACK: _score_patterns(stripped, _FEEDBACK_PATTERNS),
        PromptCategory.CONTEXT: _score_patterns(stripped, _CONTEXT_PATTERNS),
        PromptCategory.STATUS_QUERY: _score_patterns(stripped, _STATUS_PATTERNS),
        PromptCategory.NAVIGATION: _score_patterns(stripped, _NAVIGATION_PATTERNS),
    }

    # Find the highest scoring category
    best_category = max(scores, key=scores.get)  # type: ignore[arg-type]
    best_score = scores[best_category]

    if best_score == 0.0:
        # No patterns matched -- default to unknown
        # Long messages (>20 words) are likely context or tasks, capture them
        word_count = len(stripped.split())
        if word_count > 20:
            return ClassificationResult(
                category=PromptCategory.CONTEXT,
                should_capture=True,
                confidence=0.3,
            )
        return ClassificationResult(
            category=PromptCategory.UNKNOWN,
            should_capture=False,
            confidence=0.0,
        )

    should_capture = best_category in _CAPTURE_CATEGORIES
    return ClassificationResult(
        category=best_category,
        should_capture=should_capture,
        confidence=best_score,
    )


def should_capture_prompt(text: str) -> bool:
    """Quick check: should this prompt be saved to engram?

    Convenience wrapper around classify_prompt for simple yes/no decisions.
    """
    return classify_prompt(text).should_capture

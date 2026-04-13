# scope: both
"""
User Model — Synthesizes user preferences from captured prompts and feedback.

Builds an evolving model of the user's:
- Communication preferences (terse/verbose, language, formality)
- Technical context (stack, services, frameworks they work with)
- Work patterns (how they approach tasks)
- Explicit preferences (things they've asked for/against)

Stores in Engram under topic_key "agent/orchestrator/user-model"
so it persists across sessions.

Inspired by: Hermes Honcho user modeling (MIT license)
Implemented as: lightweight Engram-backed model (no external service)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class UserPreference:
    category: str      # "communication", "technical", "workflow", "explicit"
    key: str           # "language", "verbosity", "framework"
    value: str         # "Spanish informal", "terse", "Go + ginext"
    confidence: float  # 0.0 to 1.0
    source: str        # "explicit" or "inferred"


@dataclass
class UserModel:
    preferences: List[UserPreference] = field(default_factory=list)
    technical_context: Dict[str, str] = field(default_factory=dict)
    interaction_count: int = 0

    def record_preference(
        self,
        category: str,
        key: str,
        value: str,
        confidence: float = 0.7,
        source: str = "inferred",
    ) -> None:
        """Add or update a preference.

        If the (category, key) pair already exists, only update when the new
        confidence is at least as high as the existing one.
        """
        existing = next(
            (p for p in self.preferences if p.category == category and p.key == key),
            None,
        )
        if existing:
            if confidence >= existing.confidence:
                existing.value = value
                existing.confidence = confidence
                existing.source = source
        else:
            self.preferences.append(
                UserPreference(
                    category=category,
                    key=key,
                    value=value,
                    confidence=confidence,
                    source=source,
                )
            )

    def record_technical_context(self, key: str, value: str) -> None:
        """Record or overwrite a piece of technical context (stack, service, etc.)"""
        self.technical_context[key] = value

    def get_preference(self, category: str, key: str) -> Optional[UserPreference]:
        """Return the preference for (category, key), or None if not present."""
        return next(
            (p for p in self.preferences if p.category == category and p.key == key),
            None,
        )

    def get_profile_summary(self) -> str:
        """Generate a compact summary suitable for injection into agent prompts."""
        lines: List[str] = []

        if self.preferences:
            lines.append("USER PREFERENCES:")
            for p in sorted(self.preferences, key=lambda x: -x.confidence):
                lines.append(
                    f"  - [{p.category}] {p.key}: {p.value}"
                    f" (confidence: {p.confidence:.1f})"
                )

        if self.technical_context:
            lines.append("TECHNICAL CONTEXT:")
            for k, v in self.technical_context.items():
                lines.append(f"  - {k}: {v}")

        return "\n".join(lines) if lines else ""

    # ------------------------------------------------------------------
    # Serialisation helpers (dict-based, for testing without Engram)
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise to a plain dict (JSON-compatible)."""
        return {
            "preferences": [vars(p) for p in self.preferences],
            "technical_context": self.technical_context,
            "interaction_count": self.interaction_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserModel":
        """Deserialise from a plain dict produced by ``to_dict``."""
        model = cls()
        model.interaction_count = data.get("interaction_count", 0)
        model.technical_context = dict(data.get("technical_context", {}))
        for p in data.get("preferences", []):
            model.preferences.append(UserPreference(**p))
        return model

    # ------------------------------------------------------------------
    # Engram persistence
    # ------------------------------------------------------------------

    def save_to_engram(self, project: str = "") -> None:
        """Persist the model to Engram under topic_key ``agent/orchestrator/user-model``."""
        content = json.dumps(self.to_dict(), indent=2)
        engram_bin = os.environ.get("ENGRAM_BIN", "engram")
        cmd = [
            engram_bin,
            "save",
            "User Model",
            content,
            "--type",
            "pattern",
            "--topic",
            "agent/orchestrator/user-model",
        ]
        if project:
            cmd.extend(["--project", project])
        try:
            subprocess.run(cmd, capture_output=True, timeout=10)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Engram not installed or timed out — silently skip
            pass

    @classmethod
    def load_from_engram(cls, project: str = "") -> "UserModel":
        """Load the model from Engram.

        Returns an empty ``UserModel`` if Engram is not installed, the key is
        not found, or the stored payload cannot be parsed.
        """
        engram_bin = os.environ.get("ENGRAM_BIN", "engram")
        cmd = [engram_bin, "search", "agent/orchestrator/user-model"]
        if project:
            cmd.extend(["--project", project])

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return cls()

        if result.returncode != 0 or not result.stdout.strip():
            return cls()

        # Search results may have metadata lines — look for the first JSON object.
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line.startswith("{"):
                try:
                    data = json.loads(line)
                    return cls.from_dict(data)
                except (json.JSONDecodeError, TypeError, KeyError):
                    continue

        return cls()

    # ------------------------------------------------------------------
    # Inference from messages (lightweight, no LLM calls)
    # ------------------------------------------------------------------

    def infer_from_message(self, message: str) -> None:
        """Update the model based on a single user message.

        Uses heuristics only — no LLM calls.
        """
        self.interaction_count += 1

        # --- Language detection ---
        spanish_indicators = [
            "dale", "hacé", "poné", "usá", "mirá", "revisá",
            "necesito", "quiero", "podés", "tenés", "arreglá",
            "agregá", "creá", "escribí", "configurá", "borr",
        ]
        if any(word in message.lower() for word in spanish_indicators):
            self.record_preference(
                "communication", "language", "Spanish (informal)", 0.8, "inferred"
            )

        # --- Verbosity preference (short messages → terse user) ---
        if len(message.split()) < 10:
            self.record_preference(
                "communication", "verbosity", "terse", 0.3, "inferred"
            )

        # --- Technical context detection ---
        tech_patterns: Dict[str, List[str]] = {
            "go": [r"\bgo\b", r"\.go\b", r"\bgolang\b", r"\bginext\b"],
            "typescript": [r"\.ts\b", r"\btypescript\b", r"\bnestjs\b", r"\breact\b"],
            "python": [r"\.py\b", r"\bpython\b", r"\bpytest\b", r"\bpip\b"],
            "docker": [r"\bdocker\b", r"\bcontainer\b", r"\bcompose\b"],
        }
        for tech, patterns in tech_patterns.items():
            if any(re.search(p, message, re.IGNORECASE) for p in patterns):
                # Accumulate detected stacks (last one wins per key — keep all)
                existing = self.technical_context.get("stack", "")
                if tech not in existing:
                    updated = f"{existing}, {tech}" if existing else tech
                    self.record_technical_context("stack", updated)

    def infer_from_feedback(
        self,
        feedback_type: str,
        detail: Optional[str] = None,
        confidence: float = 0.8,
    ) -> None:
        """Update model based on a FeedbackSignal.type string.

        Caller passes ``signal.type.value`` and optionally ``signal.detail``.
        Keeps the UserModel independent from importing FeedbackDetector directly.
        """
        if feedback_type == "explicit_negative":
            self.record_preference(
                "workflow", "last_feedback", "negative", confidence, "explicit"
            )
        elif feedback_type == "explicit_positive":
            self.record_preference(
                "workflow", "last_feedback", "positive", confidence, "explicit"
            )
        elif feedback_type == "correction" and detail:
            # Store the correction as an explicit preference hint
            self.record_preference(
                "explicit", "correction", detail, confidence, "explicit"
            )
        elif feedback_type == "escalation":
            self.record_preference(
                "workflow", "prefers_manual_control", "true", confidence, "explicit"
            )

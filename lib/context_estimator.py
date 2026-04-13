# scope: both
"""Lightweight context window usage estimator for orchestrator awareness.

Tracks estimated token usage based on tool calls and messages.
Thresholds match context-management.md: 50% (efficiency), 70% (save), 85% (stop).
"""


class ContextEstimator:
    """Estimates current context window usage."""

    def __init__(self, max_tokens: int = 200_000):
        """Default 200K for sonnet, 1M for opus."""
        self._tool_calls = 0
        self._estimated_tokens = 0
        self._max_tokens = max_tokens

    def record_tool_call(self, tool_name: str, input_chars: int = 0, output_chars: int = 0):
        """Record a tool call and estimate its token contribution.
        Rough estimate: chars / 4 = tokens."""
        self._tool_calls += 1
        self._estimated_tokens += (input_chars + output_chars) // 4

    def record_message(self, role: str, chars: int):
        """Record a user/assistant message."""
        self._estimated_tokens += chars // 4

    def usage_percent(self) -> float:
        """Estimated context usage as percentage."""
        return min(100.0, (self._estimated_tokens / self._max_tokens) * 100)

    def tokens_remaining(self) -> int:
        """Estimated tokens remaining."""
        return max(0, self._max_tokens - self._estimated_tokens)

    def should_save_state(self) -> bool:
        """True if usage >= 70% (save threshold from context-management.md)."""
        return self.usage_percent() >= 70.0

    def should_stop_new_work(self) -> bool:
        """True if usage >= 85% (stop threshold)."""
        return self.usage_percent() >= 85.0

    def format_status(self) -> str:
        """One-line status: 'Context: 45% (90K/200K tokens) | 110K remaining'"""
        used = self._estimated_tokens
        total = self._max_tokens
        remaining = self.tokens_remaining()
        pct = self.usage_percent()
        return f"Context: {pct:.0f}% ({used // 1000}K/{total // 1000}K tokens) | {remaining // 1000}K remaining"

    def format_bar(self, width: int = 20) -> str:
        """Visual bar: [████████░░░░░░░░░░░░] 45%"""
        pct = self.usage_percent()
        filled = int(width * pct / 100)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}] {pct:.0f}%"

    def to_dict(self) -> dict:
        """Serialize for heartbeat integration."""
        return {
            "tool_calls": self._tool_calls,
            "estimated_tokens": self._estimated_tokens,
            "max_tokens": self._max_tokens,
            "usage_percent": round(self.usage_percent(), 1),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ContextEstimator":
        """Restore from heartbeat snapshot."""
        est = cls(max_tokens=data.get("max_tokens", 200_000))
        est._tool_calls = data.get("tool_calls", 0)
        est._estimated_tokens = data.get("estimated_tokens", 0)
        return est

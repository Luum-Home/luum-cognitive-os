"""Hook Tuner — Tracks false positive rates per hook and recommends threshold adjustments.

FP rate = retry_successes / total_blocks. Tune when rate > 10% with 10+ samples.
Cap: 3 auto-tunes per hook. Metrics in hook-false-positives.jsonl / hook-tuning.jsonl.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

_FP_THRESHOLD, _MIN_SAMPLES, _MAX_TUNES = 0.10, 10, 3


def _is_json(line: str) -> bool:
    try:
        json.loads(line)
        return True
    except json.JSONDecodeError:
        return False


class HookTuner:
    def __init__(self, metrics_dir: str = ".cognitive-os/metrics") -> None:
        self._dir = Path(metrics_dir)
        self._fp_file = self._dir / "hook-false-positives.jsonl"
        self._tuning_file = self._dir / "hook-tuning.jsonl"

    def _ensure_dir(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)

    def _append(self, path: Path, record: dict) -> None:
        self._ensure_dir()
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def _read_lines(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            return [json.loads(l) for l in lines if l.strip() and _is_json(l)]
        except OSError:
            return []

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def record_block(self, hook_name: str, prompt_snippet: str = "") -> None:
        """Record that a hook blocked an action (hook exited 2)."""
        self._append(self._fp_file, {
            "timestamp": self._now_iso(),
            "event": "block",
            "hook": hook_name,
            "prompt_snippet": prompt_snippet[:200],
        })

    def record_retry_success(self, hook_name: str) -> None:
        """Record that a retry after a block succeeded (false positive confirmed)."""
        self._append(self._fp_file, {
            "timestamp": self._now_iso(),
            "event": "retry_success",
            "hook": hook_name,
        })

    def get_false_positive_rate(self, hook_name: str, window_days: int = 7) -> float:
        """Calculate false positive rate for a hook over the last N days.

        Rate = retry_successes / total_blocks. Returns 0.0 if no data.
        """
        cutoff = self._cutoff_iso(window_days)
        records = [
            r for r in self._read_lines(self._fp_file)
            if r.get("hook") == hook_name and r.get("timestamp", "") >= cutoff
        ]
        blocks = sum(1 for r in records if r.get("event") == "block")
        retries = sum(1 for r in records if r.get("event") == "retry_success")
        if blocks == 0:
            return 0.0
        return retries / blocks

    def should_tune(self, hook_name: str) -> bool:
        """Return True if hook has FP rate > 10% with 10+ samples and < 3 tunes."""
        if self._tune_count(hook_name) >= _MAX_TUNES:
            return False
        records = [
            r for r in self._read_lines(self._fp_file)
            if r.get("hook") == hook_name
        ]
        blocks = sum(1 for r in records if r.get("event") == "block")
        if blocks < _MIN_SAMPLES:
            return False
        return self.get_false_positive_rate(hook_name) > _FP_THRESHOLD

    def get_tune_recommendation(self, hook_name: str) -> Optional[dict]:
        """Return tuning recommendation dict or None if no tuning needed."""
        if not self.should_tune(hook_name):
            return None
        fp_rate = self.get_false_positive_rate(hook_name)
        records = [r for r in self._read_lines(self._fp_file) if r.get("hook") == hook_name]
        samples = sum(1 for r in records if r.get("event") == "block")
        return {
            "hook": hook_name,
            "current_fp_rate": fp_rate,
            "samples": samples,
            "recommendation": "increase_threshold",
            "times_tuned": self._tune_count(hook_name),
        }

    def record_tune_event(
        self,
        hook_name: str,
        old_threshold: int,
        new_threshold: int,
        reason: str,
    ) -> None:
        """Log a tuning event to hook-tuning.jsonl."""
        self._append(self._tuning_file, {
            "timestamp": self._now_iso(),
            "hook": hook_name,
            "old_threshold": old_threshold,
            "new_threshold": new_threshold,
            "reason": reason,
        })

    def format_tuning_report(self) -> str:
        """Human-readable report of all hooks' FP rates and tuning history."""
        fp = self._read_lines(self._fp_file)
        tunes = self._read_lines(self._tuning_file)
        hooks = {r["hook"] for r in fp if "hook" in r}
        if not hooks:
            return "No hook false-positive data recorded yet."
        lines = ["Hook False-Positive Tuning Report", "=" * 36]
        for h in sorted(hooks):
            rate = self.get_false_positive_rate(h)
            blocks = sum(1 for r in fp if r.get("hook") == h and r.get("event") == "block")
            status = "TUNE RECOMMENDED" if self.should_tune(h) else "ok"
            lines.append(f"  {h}: FP={rate:.0%}  blocks={blocks}  tunes={self._tune_count(h)}  [{status}]")
        if tunes:
            lines += ["", "Tuning History:"]
            for r in tunes[-10:]:
                lines.append(f"  {r.get('timestamp','?')[:10]}  {r.get('hook','?')}  "
                              f"{r.get('old_threshold','?')}→{r.get('new_threshold','?')}  {r.get('reason','')}")
        return "\n".join(lines)

    def _cutoff_iso(self, window_days: int) -> str:
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        return cutoff.isoformat()

    def _tune_count(self, hook_name: str) -> int:
        return sum(
            1 for r in self._read_lines(self._tuning_file)
            if r.get("hook") == hook_name
        )

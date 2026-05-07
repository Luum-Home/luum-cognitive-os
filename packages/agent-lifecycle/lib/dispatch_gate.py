# SCOPE: both
"""ADR-228 unified dispatch pre-call gate."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path

from lib.retry_classifier import FailureClass, RetryPolicy, classify_failure, retry_policy_for
from lib.session_budget import SessionBudget, SessionBudgetExceeded


class IdempotencyConflict(RuntimeError):
    """Raised when an idempotency key was already claimed."""


@dataclass(frozen=True)
class DispatchGateDecision:
    allowed: bool
    pressure: str
    estimated_usd: float
    remaining_usd: float


def idempotency_key(session_id: str, event_seq: int, tool_name: str) -> str:
    return hashlib.sha256(f"{session_id}:{event_seq}:{tool_name}".encode("utf-8")).hexdigest()


def claim_idempotency_key(project_dir: str | Path, key: str, *, tool_name: str, ttl_seconds: int = 3600) -> None:
    path = Path(project_dir).resolve() / ".cognitive-os" / "metrics" / "idempotency-keys.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    if path.is_file():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("key") == key and now - float(row.get("claimed_at_epoch", 0)) < ttl_seconds:
                raise IdempotencyConflict(f"idempotency key already claimed for {tool_name}")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"schema_version": "idempotency-key/v1", "key": key, "tool_name": tool_name, "claimed_at_epoch": now}, sort_keys=True) + "\n")


class DispatchGate:
    def __init__(self, project_dir: str | Path, session_id: str, *, cap_usd: float) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.session_id = session_id
        self.budget = SessionBudget(self.project_dir, session_id, cap_usd=cap_usd)

    def pre_call(self, estimated_usd: float) -> DispatchGateDecision:
        pressure = self.budget.pre_call_check(estimated_usd)
        return DispatchGateDecision(True, pressure, float(estimated_usd), self.budget.remaining_usd)

    def record_actual(self, actual_usd: float) -> None:
        self.budget.record_actual(actual_usd)

    def classify(self, error_or_response: object) -> tuple[FailureClass, RetryPolicy]:
        failure = classify_failure(error_or_response)
        return failure, retry_policy_for(failure)

    def as_context_signal(self, decision: DispatchGateDecision) -> str:
        if decision.pressure == "caution":
            return "[COST_CAUTION]"
        if decision.pressure == "switch":
            return "[COST_WARNING] switch_to=cheapest_capable"
        if decision.pressure == "refuse":
            raise SessionBudgetExceeded("budget exhausted")
        return ""


@dataclass(frozen=True)
class CircuitBreakerDecision:
    allowed: bool
    state: str
    reason: str = ""


class ProviderCircuitBreaker:
    """Small file-backed provider circuit breaker for the dispatch hot path."""

    def __init__(
        self,
        project_dir: str | Path,
        provider: str,
        *,
        failure_threshold: int = 3,
        cooldown_seconds: int = 60,
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.provider = provider.replace("/", "_").replace("\\", "_")
        self.failure_threshold = int(failure_threshold)
        self.cooldown_seconds = int(cooldown_seconds)
        self.path = self.project_dir / ".cognitive-os" / "metrics" / "circuit-breakers" / f"{self.provider}.json"

    def _load(self) -> dict[str, object]:
        if self.path.is_file():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass
        return {
            "schema_version": "provider-circuit-breaker/v1",
            "provider": self.provider,
            "state": "closed",
            "consecutive_failures": 0,
            "opened_at_epoch": 0.0,
            "updated_at_epoch": time.time(),
        }

    def _save(self, data: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def allow_call(self) -> CircuitBreakerDecision:
        data = self._load()
        state = str(data.get("state") or "closed")
        opened = float(data.get("opened_at_epoch") or 0.0)
        now = time.time()
        if state == "open":
            remaining = self.cooldown_seconds - (now - opened)
            if remaining > 0:
                return CircuitBreakerDecision(False, "open", f"cooldown {remaining:.1f}s remaining")
            data["state"] = "half_open"
            data["updated_at_epoch"] = now
            self._save(data)
            return CircuitBreakerDecision(True, "half_open", "cooldown elapsed; allowing probe")
        return CircuitBreakerDecision(True, state)

    def record_result(self, *, success: bool, failure: FailureClass | None = None) -> dict[str, object]:
        data = self._load()
        now = time.time()
        if success:
            data.update({"state": "closed", "consecutive_failures": 0, "last_failure_class": "", "updated_at_epoch": now})
            self._save(data)
            return data

        failures = int(data.get("consecutive_failures") or 0) + 1
        state = str(data.get("state") or "closed")
        if failures >= self.failure_threshold or state == "half_open":
            state = "open"
            data["opened_at_epoch"] = now
        data.update({
            "state": state,
            "consecutive_failures": failures,
            "last_failure_class": str(failure.value if failure else "unknown"),
            "updated_at_epoch": now,
        })
        self._save(data)
        return data

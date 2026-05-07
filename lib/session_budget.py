# SCOPE: both
"""ADR-228 file-backed per-session budget gate."""
from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path


class SessionBudgetExceeded(RuntimeError):
    """Raised when a pre-call budget gate would exceed cap."""


@dataclass
class BudgetState:
    schema_version: str
    session_id: str
    cap_usd: float
    spent_usd: float
    calls: int
    updated_at: str


class SessionBudget:
    def __init__(self, project_dir: str | Path, session_id: str, *, cap_usd: float) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.session_id = session_id
        self.cap_usd = float(cap_usd)
        self.path = self.project_dir / ".cognitive-os" / "metrics" / "session-budgets" / f"{session_id}.json"
        self.state = self._load()

    def _load(self) -> BudgetState:
        if self.path.is_file():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                return BudgetState(
                    schema_version=str(raw.get("schema_version") or "session-budget/v1"),
                    session_id=self.session_id,
                    cap_usd=float(raw.get("cap_usd", self.cap_usd)),
                    spent_usd=float(raw.get("spent_usd", 0.0)),
                    calls=int(raw.get("calls", 0)),
                    updated_at=str(raw.get("updated_at") or _now()),
                )
            except Exception:
                pass
        return BudgetState("session-budget/v1", self.session_id, self.cap_usd, 0.0, 0, _now())

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=self.path.name, suffix=".tmp", dir=str(self.path.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(asdict(self.state), handle, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, self.path)

    @property
    def spent_usd(self) -> float:
        return self.state.spent_usd

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.state.cap_usd - self.state.spent_usd)

    @property
    def pressure(self) -> str:
        if self.state.cap_usd <= 0:
            return "refuse"
        pct = (self.state.spent_usd / self.state.cap_usd) * 100
        if pct >= 100:
            return "refuse"
        if pct >= 90:
            return "switch"
        if pct >= 70:
            return "caution"
        return "ok"

    def pre_call_check(self, estimated_usd: float) -> str:
        estimated = float(estimated_usd)
        if self.state.spent_usd + estimated > self.state.cap_usd:
            raise SessionBudgetExceeded(
                f"session {self.session_id} budget exceeded: spent={self.state.spent_usd:.4f} "
                f"estimated={estimated:.4f} cap={self.state.cap_usd:.4f}"
            )
        return self.pressure

    def record_actual(self, actual_usd: float) -> BudgetState:
        self.state.spent_usd = round(self.state.spent_usd + float(actual_usd), 8)
        self.state.calls += 1
        self.state.updated_at = _now()
        self._save()
        return self.state


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

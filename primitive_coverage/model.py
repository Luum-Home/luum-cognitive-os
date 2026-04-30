from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SIGNAL_WEIGHTS = {
    "declared": 15,
    "wired": 20,
    "referenced": 15,
    "tested": 20,
    "documented": 10,
    "runtime_seen": 10,
    "owner": 5,
    "proof": 5,
}


@dataclass
class PrimitiveRow:
    primitive_id: str
    family: str
    path: str
    signals: dict[str, bool] = field(default_factory=dict)
    consumers: list[str] = field(default_factory=list)
    claims: list[str] = field(default_factory=list)
    proof_links: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    status: str = "unknown"
    score: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def recompute(self) -> None:
        self.signals = {key: bool(self.signals.get(key, False)) for key in SIGNAL_WEIGHTS}
        self.gaps = []
        for signal in ("declared", "wired", "tested", "documented", "proof"):
            if not self.signals.get(signal, False):
                self.gaps.append(f"missing_{signal}")
        if not self.signals.get("runtime_seen", False):
            self.gaps.append("runtime_not_seen")
        if not self.consumers and not self.signals.get("referenced", False):
            self.gaps.append("no_static_consumers")
        self.score = sum(weight for signal, weight in SIGNAL_WEIGHTS.items() if self.signals.get(signal, False))
        if self.score >= 80 and not self.gaps:
            self.status = "real"
        elif self.score >= 60:
            self.status = "partial"
        elif self.signals.get("declared") or self.signals.get("referenced"):
            self.status = "dormant"
        else:
            self.status = "orphan"

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitive_id": self.primitive_id,
            "family": self.family,
            "path": self.path,
            "signals": dict(sorted(self.signals.items())),
            "consumers": sorted(set(self.consumers)),
            "claims": self.claims,
            "proof_links": sorted(set(self.proof_links)),
            "gaps": self.gaps,
            "status": self.status,
            "score": self.score,
            "metadata": self.metadata,
        }


@dataclass
class CoverageReport:
    adapter: str
    root: Path
    rows: list[PrimitiveRow]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def summary(self) -> dict[str, Any]:
        by_family: dict[str, dict[str, Any]] = {}
        status_counts: dict[str, int] = {}
        for row in self.rows:
            fam = by_family.setdefault(row.family, {"count": 0, "score_total": 0, "statuses": {}})
            fam["count"] += 1
            fam["score_total"] += row.score
            fam["statuses"][row.status] = fam["statuses"].get(row.status, 0) + 1
            status_counts[row.status] = status_counts.get(row.status, 0) + 1
        for fam in by_family.values():
            fam["average_score"] = round(fam["score_total"] / fam["count"], 2) if fam["count"] else 0
            del fam["score_total"]
        score = round(sum(row.score for row in self.rows) / len(self.rows), 2) if self.rows else 0
        return {
            "adapter": self.adapter,
            "targets": len(self.rows),
            "average_score": score,
            "statuses": dict(sorted(status_counts.items())),
            "families": dict(sorted(by_family.items())),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "generated_at": self.generated_at,
            "root": str(self.root),
            "summary": self.summary(),
            "rows": [row.to_dict() for row in sorted(self.rows, key=lambda r: (r.family, r.path))],
        }

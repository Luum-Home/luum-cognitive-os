# SCOPE: both
"""W3-2 DSPy structured-I/O pilot boundary.

The pilot is intentionally optional: it proves the integration seam for one
structured verification skill without making DSPy a hard dependency or touching
skill routing.
"""
from __future__ import annotations

import importlib.util
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class DspyPilotReport:
    schema_version: str
    status: str
    target_skill: str
    dspy_available: bool
    signature: dict[str, list[str]]
    router_touched: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def dspy_available() -> bool:
    return importlib.util.find_spec("dspy") is not None


def sdd_verify_signature() -> dict[str, list[str]]:
    return {
        "inputs": ["spec_markdown", "implementation_diff", "test_evidence"],
        "outputs": ["verdict", "missing_acceptance", "risk_notes", "next_action"],
    }


def build_pilot_report(target_skill: str = "sdd-verify") -> DspyPilotReport:
    available = dspy_available()
    return DspyPilotReport(
        schema_version="dspy-structured-skill-pilot/v1",
        status="ready" if available else "dependency-missing",
        target_skill=target_skill,
        dspy_available=available,
        signature=sdd_verify_signature(),
    )

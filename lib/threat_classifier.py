# SCOPE: both
"""Threat classification using STRIDE categories."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# STRIDE keyword mapping
# ---------------------------------------------------------------------------
STRIDE_CATEGORIES: Dict[str, List[str]] = {
    "spoofing": ["impersonation", "identity", "fake", "phishing", "social engineering"],
    "tampering": ["injection", "sql", "xss", "modification", "alter", "corrupt"],
    "repudiation": ["audit", "log", "trace", "deny", "non-repudiation"],
    "information-disclosure": [
        "data breach",
        "leak",
        "expose",
        "disclosure",
        "exfiltration",
    ],
    "denial-of-service": [
        "ddos",
        "dos",
        "flood",
        "overload",
        "availability",
        "resource exhaustion",
    ],
    "elevation-of-privilege": [
        "escalation",
        "privilege",
        "admin",
        "root",
        "bypass",
        "authorization",
    ],
}

SEVERITY_WEIGHTS: Dict[str, int] = {
    "CRITICAL": 10,
    "HIGH": 7,
    "MEDIUM": 4,
    "LOW": 1,
}

# ---------------------------------------------------------------------------
# Scoring constants for classify_threat
# ---------------------------------------------------------------------------
_VECTOR_SCORE: Dict[str, int] = {
    "network": 2,
    "local": 1,
    "physical": 0,
}

_ASSET_SCORE: Dict[str, int] = {
    "database": 3,
    "auth": 3,
    "api": 2,
    "ui": 1,
    "docs": 0,
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ThreatScenario:
    """A single threat scenario to be classified or analysed."""

    id: str
    description: str
    attack_vector: str
    asset_type: str
    severity: str = ""
    category: str = ""
    status: str = "OPEN"
    mitigation: str = ""


@dataclass
class ThreatClassification:
    """Classification result for a single threat scenario."""

    severity: str
    category: str
    likelihood: str
    impact: str


@dataclass
class ThreatMatrix:
    """Aggregated view across all threat scenarios in a threat model."""

    threats: List[ThreatScenario]
    by_severity: Dict[str, int]
    by_status: Dict[str, int]
    risk_score: float


# ---------------------------------------------------------------------------
# Severity ordering for sorting (CRITICAL first)
# ---------------------------------------------------------------------------
_SEVERITY_ORDER: Dict[str, int] = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
    "": 4,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_threat(
    description: str, attack_vector: str, asset_type: str
) -> ThreatClassification:
    """Classify a threat using STRIDE and a simple scoring model.

    Severity scoring:
        score = vector_score + asset_score
        >= 5  → CRITICAL
        >= 4  → HIGH
        >= 2  → MEDIUM
        else  → LOW

    Likelihood:
        network vector AND (database OR auth asset) → "high", else "medium"

    Impact:
        database OR auth → "high", api → "medium", else "low"

    Args:
        description: Free-text description of the threat.
        attack_vector: One of "network", "local", "physical".
        asset_type: One of "database", "auth", "api", "ui", "docs".

    Returns:
        ThreatClassification with severity, STRIDE category, likelihood, impact.
    """
    desc_lower = description.lower()

    # --- Determine STRIDE category ---
    category = _detect_stride_category(desc_lower)

    # --- Calculate severity score ---
    vector_score = _VECTOR_SCORE.get(attack_vector.lower(), 0)
    asset_score = _ASSET_SCORE.get(asset_type.lower(), 0)
    score = vector_score + asset_score

    if score >= 5:
        severity = "CRITICAL"
    elif score >= 4:
        severity = "HIGH"
    elif score >= 2:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    # --- Likelihood ---
    is_network = attack_vector.lower() == "network"
    is_high_value_asset = asset_type.lower() in ("database", "auth")
    likelihood = "high" if (is_network and is_high_value_asset) else "medium"

    # --- Impact ---
    if asset_type.lower() in ("database", "auth"):
        impact = "high"
    elif asset_type.lower() == "api":
        impact = "medium"
    else:
        impact = "low"

    return ThreatClassification(
        severity=severity,
        category=category,
        likelihood=likelihood,
        impact=impact,
    )


def generate_threat_matrix(threats: List[ThreatScenario]) -> ThreatMatrix:
    """Build a ThreatMatrix aggregating counts and risk score.

    Threats are sorted by severity (CRITICAL first).

    Args:
        threats: List of ThreatScenario objects (may have severity pre-set or "").

    Returns:
        ThreatMatrix with by_severity, by_status, and risk_score.
    """
    sorted_threats = sorted(
        threats, key=lambda t: _SEVERITY_ORDER.get(t.severity, 4)
    )

    by_severity: Dict[str, int] = {}
    by_status: Dict[str, int] = {}

    for t in threats:
        sev = t.severity or "UNKNOWN"
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_status[t.status] = by_status.get(t.status, 0) + 1

    risk = calculate_risk_score(threats)

    return ThreatMatrix(
        threats=sorted_threats,
        by_severity=by_severity,
        by_status=by_status,
        risk_score=risk,
    )


def calculate_risk_score(threats: List[ThreatScenario]) -> float:
    """Calculate a 0-100 composite risk score across all threats.

    Formula:
        weighted_sum = sum(
            SEVERITY_WEIGHTS[severity] * (1.5 if status == "OPEN" else 1.0)
        )
        max_possible  = len(threats) * 10 * 1.5   (all CRITICAL + OPEN)
        risk_score    = clamp(weighted_sum / max_possible * 100, 0, 100)

    Threats with an unrecognised severity default to weight 0.

    Args:
        threats: List of ThreatScenario objects.

    Returns:
        Risk score in [0, 100].
    """
    if not threats:
        return 0.0

    weighted_sum = 0.0
    for t in threats:
        weight = SEVERITY_WEIGHTS.get(t.severity, 0)
        multiplier = 1.5 if t.status == "OPEN" else 1.0
        weighted_sum += weight * multiplier

    max_possible = len(threats) * 10 * 1.5
    raw = (weighted_sum / max_possible) * 100.0
    return max(0.0, min(100.0, raw))


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _detect_stride_category(desc_lower: str) -> str:
    """Return the first matching STRIDE category or 'unknown'."""
    for category, keywords in STRIDE_CATEGORIES.items():
        for kw in keywords:
            if kw in desc_lower:
                return category
    return "unknown"

"""Unit tests for lib/threat_classifier.py."""

import pytest

from lib.threat_classifier import (
    ThreatClassification,
    ThreatMatrix,
    ThreatScenario,
    calculate_risk_score,
    classify_threat,
    generate_threat_matrix,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# E1: classify_threat — injection attack on database
# ---------------------------------------------------------------------------


class TestClassifyThreat:
    def test_classify_injection_threat(self):
        """E1 — SQL injection on database via network → HIGH or CRITICAL, tampering."""
        result = classify_threat(
            description="SQL injection in login form",
            attack_vector="network",
            asset_type="database",
        )

        assert isinstance(result, ThreatClassification)
        assert result.severity in ("HIGH", "CRITICAL"), (
            f"Expected HIGH or CRITICAL, got {result.severity}"
        )
        assert result.category == "tampering", (
            f"Expected STRIDE category 'tampering', got {result.category}"
        )

    def test_classify_threat_spoofing(self):
        """Phishing / impersonation keywords map to 'spoofing'."""
        result = classify_threat(
            description="Phishing attack targeting user identity",
            attack_vector="network",
            asset_type="auth",
        )
        assert result.category == "spoofing"

    def test_classify_threat_privilege_escalation(self):
        """Privilege escalation keywords map to 'elevation-of-privilege'."""
        result = classify_threat(
            description="Bypass authorization to gain admin access",
            attack_vector="local",
            asset_type="auth",
        )
        assert result.category == "elevation-of-privilege"

    def test_classify_threat_denial_of_service(self):
        """DDoS flood keyword maps to 'denial-of-service'."""
        result = classify_threat(
            description="DDoS flood targeting the API gateway",
            attack_vector="network",
            asset_type="api",
        )
        assert result.category == "denial-of-service"

    def test_classify_threat_severity_critical(self):
        """network + database/auth = score >= 5 → CRITICAL."""
        result = classify_threat(
            description="Data breach via exfiltration",
            attack_vector="network",
            asset_type="database",
        )
        # vector=2, asset=3 → score=5 → CRITICAL
        assert result.severity == "CRITICAL"

    def test_classify_threat_severity_low(self):
        """physical + docs = score 0 → LOW."""
        result = classify_threat(
            description="Someone reads a printed document",
            attack_vector="physical",
            asset_type="docs",
        )
        assert result.severity == "LOW"

    def test_classify_threat_likelihood_high(self):
        """network + auth/database → likelihood 'high'."""
        result = classify_threat(
            description="Data exfiltration",
            attack_vector="network",
            asset_type="database",
        )
        assert result.likelihood == "high"

    def test_classify_threat_likelihood_medium(self):
        """local vector → likelihood 'medium'."""
        result = classify_threat(
            description="Privilege escalation via local admin access",
            attack_vector="local",
            asset_type="auth",
        )
        assert result.likelihood == "medium"

    def test_classify_threat_impact_database(self):
        """database asset → impact 'high'."""
        result = classify_threat(
            description="SQL injection attack",
            attack_vector="local",
            asset_type="database",
        )
        assert result.impact == "high"

    def test_classify_threat_impact_api(self):
        """api asset → impact 'medium'."""
        result = classify_threat(
            description="Resource exhaustion on API",
            attack_vector="network",
            asset_type="api",
        )
        assert result.impact == "medium"

    def test_classify_threat_impact_ui(self):
        """ui asset → impact 'low'."""
        result = classify_threat(
            description="XSS in UI form",
            attack_vector="network",
            asset_type="ui",
        )
        assert result.impact == "low"

    def test_classify_threat_unknown_category(self):
        """Unrecognised description returns 'unknown' category."""
        result = classify_threat(
            description="An entirely novel and unrecognised threat",
            attack_vector="physical",
            asset_type="docs",
        )
        assert result.category == "unknown"


# ---------------------------------------------------------------------------
# E2: generate_threat_matrix — by_severity counts sum to total
# ---------------------------------------------------------------------------


class TestGenerateThreatMatrix:
    def _make_threats(self) -> list[ThreatScenario]:
        """Build 12 ThreatScenarios with mixed severities."""
        specs = [
            ("T01", "CRITICAL", "OPEN"),
            ("T02", "CRITICAL", "OPEN"),
            ("T03", "CRITICAL", "MITIGATED"),
            ("T04", "HIGH", "OPEN"),
            ("T05", "HIGH", "OPEN"),
            ("T06", "HIGH", "MITIGATED"),
            ("T07", "MEDIUM", "OPEN"),
            ("T08", "MEDIUM", "OPEN"),
            ("T09", "MEDIUM", "OPEN"),
            ("T10", "LOW", "OPEN"),
            ("T11", "LOW", "MITIGATED"),
            ("T12", "LOW", "OPEN"),
        ]
        return [
            ThreatScenario(
                id=tid,
                description="Sample threat",
                attack_vector="network",
                asset_type="api",
                severity=sev,
                status=status,
            )
            for tid, sev, status in specs
        ]

    def test_threat_matrix_counts(self):
        """E2 — by_severity values sum to the total number of threats (12)."""
        threats = self._make_threats()
        matrix = generate_threat_matrix(threats)

        assert isinstance(matrix, ThreatMatrix)
        total = sum(matrix.by_severity.values())
        assert total == 12, f"Expected 12, got {total}"

    def test_threat_matrix_sorted_critical_first(self):
        """CRITICAL threats appear before HIGH / MEDIUM / LOW in the list."""
        threats = self._make_threats()
        matrix = generate_threat_matrix(threats)

        severities = [t.severity for t in matrix.threats]
        seen_non_critical = False
        for sev in severities:
            if sev != "CRITICAL":
                seen_non_critical = True
            if seen_non_critical and sev == "CRITICAL":
                pytest.fail("CRITICAL appeared after a non-CRITICAL threat")

    def test_threat_matrix_by_status_sum(self):
        """by_status values also sum to total threat count."""
        threats = self._make_threats()
        matrix = generate_threat_matrix(threats)

        total = sum(matrix.by_status.values())
        assert total == 12

    def test_threat_matrix_empty(self):
        """Empty threat list produces zero counts and 0.0 risk score."""
        matrix = generate_threat_matrix([])

        assert matrix.by_severity == {}
        assert matrix.by_status == {}
        assert matrix.risk_score == 0.0

    def test_threat_matrix_risk_score_in_range(self):
        """risk_score is always in [0, 100]."""
        threats = self._make_threats()
        matrix = generate_threat_matrix(threats)

        assert 0.0 <= matrix.risk_score <= 100.0


# ---------------------------------------------------------------------------
# E3: calculate_risk_score — all CRITICAL + OPEN → > 70
# ---------------------------------------------------------------------------


class TestCalculateRiskScore:
    def test_high_risk_score(self):
        """E3 — 3 CRITICAL OPEN threats produce risk_score > 70."""
        threats = [
            ThreatScenario(
                id=f"T0{i}",
                description="Critical open threat",
                attack_vector="network",
                asset_type="database",
                severity="CRITICAL",
                status="OPEN",
            )
            for i in range(1, 4)
        ]
        score = calculate_risk_score(threats)

        assert score > 70, f"Expected risk_score > 70 for all-CRITICAL-OPEN, got {score}"

    def test_risk_score_all_critical_open_is_100(self):
        """All CRITICAL+OPEN threats → score should be exactly 100."""
        threats = [
            ThreatScenario(
                id=f"T{i}",
                description="Critical",
                attack_vector="network",
                asset_type="database",
                severity="CRITICAL",
                status="OPEN",
            )
            for i in range(5)
        ]
        score = calculate_risk_score(threats)
        assert score == pytest.approx(100.0)

    def test_risk_score_empty_list(self):
        """Empty list → 0.0 risk score."""
        assert calculate_risk_score([]) == 0.0

    def test_risk_score_mitigated_lowers_score(self):
        """MITIGATED threats score lower than OPEN threats of the same severity."""
        open_threats = [
            ThreatScenario(
                id="T1",
                description="Open",
                attack_vector="network",
                asset_type="database",
                severity="HIGH",
                status="OPEN",
            )
        ]
        mitigated_threats = [
            ThreatScenario(
                id="T1",
                description="Mitigated",
                attack_vector="network",
                asset_type="database",
                severity="HIGH",
                status="MITIGATED",
            )
        ]
        open_score = calculate_risk_score(open_threats)
        mitigated_score = calculate_risk_score(mitigated_threats)

        assert open_score > mitigated_score

    def test_risk_score_clamped_to_100(self):
        """risk_score never exceeds 100 regardless of inputs."""
        threats = [
            ThreatScenario(
                id=f"T{i}",
                description="Critical open",
                attack_vector="network",
                asset_type="database",
                severity="CRITICAL",
                status="OPEN",
            )
            for i in range(50)
        ]
        score = calculate_risk_score(threats)
        assert score <= 100.0

    def test_risk_score_low_only(self):
        """All LOW severity threats → risk_score much lower than all-CRITICAL."""
        low_threats = [
            ThreatScenario(
                id=f"T{i}",
                description="Low threat",
                attack_vector="physical",
                asset_type="docs",
                severity="LOW",
                status="OPEN",
            )
            for i in range(3)
        ]
        critical_threats = [
            ThreatScenario(
                id=f"T{i}",
                description="Critical threat",
                attack_vector="network",
                asset_type="database",
                severity="CRITICAL",
                status="OPEN",
            )
            for i in range(3)
        ]
        low_score = calculate_risk_score(low_threats)
        critical_score = calculate_risk_score(critical_threats)

        assert low_score < critical_score

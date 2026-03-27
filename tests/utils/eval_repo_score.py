"""Utility module: Repository evaluation scoring functions.

Python port of tests/_helpers/eval-repo-score.sh.
Can be imported by tests or run standalone.
"""


def score_license(license_id: str) -> int:
    """Score a license on a 0-10 scale."""
    mapping = {
        "MIT": 10, "ISC": 10,
        "Apache-2.0": 10, "Apache-2": 10,
        "BSD-2-Clause": 8, "BSD-3-Clause": 8,
        "MPL-2.0": 7,
        "LGPL-2.1": 6, "LGPL-3.0": 6,
        "GPL-2.0": 5, "GPL-3.0": 5,
        "AGPL-3.0": 0,
        "SSPL-1.0": 0, "SSPL": 0,
        "BUSL-1.1": 0, "BUSL": 0,
    }
    if not license_id:
        return 2
    return mapping.get(license_id, 3)


def score_activity(days_since_commit: int) -> int:
    """Score activity based on days since last commit (0-10)."""
    if days_since_commit <= 30:
        return 10
    elif days_since_commit <= 90:
        return 8
    elif days_since_commit <= 180:
        return 6
    elif days_since_commit <= 365:
        return 3
    else:
        return 0


def should_auto_reject(license_id: str, days_since_commit: int, archived: bool = False) -> str:
    """Determine if a repo should be auto-rejected.

    Returns a string: "REJECT:reason", "HOLD:reason", or "PASS".
    """
    if license_id in ("AGPL-3.0", "SSPL-1.0", "SSPL", "BUSL-1.1", "BUSL"):
        return f"REJECT:license:{license_id}"

    if archived:
        return "REJECT:archived"

    if days_since_commit > 365:
        return f"HOLD:inactive:{days_since_commit}d"

    return "PASS"


def calculate_weighted_score(
    relevance: int, license_score: int, activity: int, maturity: int, integration: int
) -> str:
    """Calculate weighted score (0.0-10.0).

    Weights: Relevance 30%, License 25%, Activity 20%, Maturity 15%, Integration 10%.
    """
    score = relevance * 30 + license_score * 25 + activity * 20 + maturity * 15 + integration * 10
    integer = score // 100
    decimal = (score % 100) // 10
    return f"{integer}.{decimal}"


def classify_score(score: str) -> str:
    """Classify a score string into ADOPT/TRIAL/ASSESS/HOLD/REJECT."""
    int_part, dec_part = score.split(".")
    normalized = int(int_part) * 10 + int(dec_part)

    if normalized >= 80:
        return "ADOPT"
    elif normalized >= 60:
        return "TRIAL"
    elif normalized >= 40:
        return "ASSESS"
    elif normalized >= 20:
        return "HOLD"
    else:
        return "REJECT"


if __name__ == "__main__":
    # Self-test
    assert score_license("MIT") == 10
    assert score_license("AGPL-3.0") == 0
    assert score_activity(15) == 10
    assert score_activity(400) == 0
    assert should_auto_reject("AGPL-3.0", 10) == "REJECT:license:AGPL-3.0"
    assert should_auto_reject("MIT", 10) == "PASS"
    assert should_auto_reject("MIT", 500) == "HOLD:inactive:500d"
    assert classify_score("8.5") == "ADOPT"
    assert classify_score("6.0") == "TRIAL"
    print("All self-tests passed.")

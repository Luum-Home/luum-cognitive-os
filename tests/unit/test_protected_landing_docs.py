"""Vendor-neutral documentation contract for ADR-116 protected landing."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS = [
    PROJECT_ROOT / "docs" / "02-Decisions" / "adrs" / "ADR-116-multi-session-coordination-primitives.md",
    PROJECT_ROOT / "docs" / "04-Concepts" / "architecture" / "direct-main-policy.md",
    PROJECT_ROOT / "docs" / "04-Concepts" / "architecture" / "protected-landing-contract.md",
    PROJECT_ROOT / ".cognitive-os" / "plans" / "architecture" / "multi-session-coordination-primitives-plan.md",
]


def read_all() -> str:
    return "\n".join(path.read_text() for path in DOCS)


def test_protected_landing_docs_are_vendor_neutral() -> None:
    text = read_all().lower()
    assert "vendor-neutral" in text
    assert "gitlab" in text
    assert "gitea" in text
    assert "forgejo" in text
    assert "bitbucket" in text
    assert "bare git" in text or "bare-git" in text
    assert "server-side" in text
    assert "unknown" in text


def test_docs_do_not_require_gh_or_github_as_core_dependency() -> None:
    text = read_all().lower()
    forbidden = [
        "must use github",
        "requires github",
        "must use gh",
        "requires gh",
        "gh is required",
        "github-only",
    ]
    for phrase in forbidden:
        assert phrase not in text
    assert "github is one adapter, not a requirement" in text
    assert "do not require `gh`" in text


def test_protected_landing_contract_lists_required_guarantees() -> None:
    text = (PROJECT_ROOT / "docs" / "04-Concepts" / "architecture" / "protected-landing-contract.md").read_text().lower()
    for guarantee in [
        "serialized writes",
        "fresh-base validation",
        "required gates",
        "direct-agent push rejection",
        "operator bypass visibility",
        "provenance",
    ]:
        assert guarantee in text

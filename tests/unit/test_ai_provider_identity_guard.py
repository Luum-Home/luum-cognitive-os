from __future__ import annotations

from lib.ai_provider_identity_guard import scan_text


def _policy() -> dict:
    return {
        "blocked_email_domains": ["anthropic.com", "openai.com"],
        "blocked_email_local_parts": ["noreply", "bot", "agent"],
        "provider_names": ["claude", "codex", "openai", "anthropic"],
        "allowed_emails": ["2144218+MatiasNAmendola@users.noreply.github.com", "noreply@github.com"],
        "allowed_paths": ["tests/"],
    }


def test_blocks_provider_like_email_without_naming_one_provider_only() -> None:
    email = "no" + "reply" + "@" + "anthropic" + ".com"
    findings = scan_text(f"Contact: {email}\n", path="CONTRIBUTING.md", policy=_policy())

    assert [finding.code for finding in findings] == ["ai-provider-email"]


def test_blocks_provider_coauthor_trailer_even_without_email() -> None:
    provider = "Co" + "dex"
    findings = scan_text(f"Co-authored-by: {provider}\n", path="COMMIT_EDITMSG", policy=_policy())

    assert [finding.code for finding in findings] == ["ai-provider-authorship-trailer"]


def test_allows_verified_github_noreply_identity() -> None:
    text = "Author: MatiasNAmendola <2144218+MatiasNAmendola@users.noreply.github.com>\n"

    assert scan_text(text, path="docs/09-Quality/legal/pre-public-readiness-checklist.md", policy=_policy()) == []


def test_allows_test_fixtures_by_path() -> None:
    email = "bot" + "@" + "openai" + ".com"

    assert scan_text(f"{email}\n", path="tests/fixtures/provider_email.txt", policy=_policy()) == []

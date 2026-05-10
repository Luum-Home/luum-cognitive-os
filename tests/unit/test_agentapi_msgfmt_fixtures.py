from __future__ import annotations

from lib.harness_adapter.agentapi_msgfmt import summarize_fixtures


def test_agentapi_msgfmt_fixture_vendor_has_expected_harnesses() -> None:
    summary = summarize_fixtures()
    assert "claude" in summary.harnesses
    assert "codex" in summary.harnesses
    assert "opencode" in summary.harnesses
    assert summary.format_case_count > 0
    assert summary.initialization_case_count > 0

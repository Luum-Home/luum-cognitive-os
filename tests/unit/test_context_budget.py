from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import pytest

from cos_lib.context_budget import count_tokens, evaluate, filter_hook_output, read_budget, record_usage
from cos_lib.context_budget_monitor import build_report

pytestmark = pytest.mark.unit


def test_count_tokens_heuristic_rounds_up() -> None:
    assert count_tokens("") == 0
    assert count_tokens("abcd") == 1
    assert count_tokens("abcde") == 2


def test_evaluate_thresholds() -> None:
    budgets = {"static": 100}
    assert evaluate("static", 100, budgets).verdict == "PASS"
    assert evaluate("static", 110, budgets).verdict == "WARN"
    assert evaluate("static", 151, budgets).verdict == "BLOCK"


def test_read_budget_from_cognitive_os_yaml(tmp_path: Path) -> None:
    cfg = tmp_path / "cognitive-os.yaml"
    cfg.write_text("context_budget:\n  static_max_tokens: 123\n  turn_max_tokens: 456\n", encoding="utf-8")
    budgets = read_budget(cfg)
    assert budgets["static"] == 123
    assert budgets["turn"] == 456
    assert budgets["user"] == 12000


def test_record_usage_appends_jsonl(tmp_path: Path) -> None:
    row = record_usage(tmp_path, source="test", layer="static", text="hello world", session_id="s1")
    assert row["source"] == "test"
    log = tmp_path / ".cognitive-os" / "metrics" / "context-budget.jsonl"
    saved = json.loads(log.read_text().splitlines()[0])
    assert saved["session_id"] == "s1"


def test_filter_hook_output_suppresses_blocking_context(tmp_path: Path) -> None:
    """The over-budget text must not reach the turn — but the envelope must."""
    (tmp_path / "cognitive-os.yaml").write_text("context_budget:\n  static_max_tokens: 1\n", encoding="utf-8")
    payload = {"hookSpecificOutput": {"additionalContext": "x" * 20}}
    out = filter_hook_output(tmp_path, source="test", hook_json=json.dumps(payload), session_id="s1")
    assert "x" * 20 not in out
    assert json.loads(out)["hookSpecificOutput"]["additionalContext"].startswith("[context-budget] DROPPED")


def test_default_budgets_cover_all_layers(tmp_path: Path) -> None:
    budgets = read_budget(tmp_path / "missing.yaml")
    assert budgets == {"static": 4000, "turn": 8000, "user": 12000, "cache": 32000}


def test_block_override_allows_but_keeps_block_verdict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COS_ALLOW_CONTEXT_BUDGET_OVERRUN", "1")
    verdict = evaluate("static", 151, {"static": 100})
    assert verdict.verdict == "BLOCK"
    assert verdict.allowed is True
    assert verdict.reason == "override"


def test_warn_band_extends_through_1_5_before_block() -> None:
    assert evaluate("static", 121, {"static": 100}).verdict == "WARN"
    assert evaluate("static", 150, {"static": 100}).verdict == "WARN"
    assert evaluate("static", 151, {"static": 100}).verdict == "BLOCK"


def test_filter_hook_output_passes_non_json_and_no_context(tmp_path: Path) -> None:
    assert filter_hook_output(tmp_path, source="test", hook_json="not-json", session_id="s1") == "not-json"
    payload = json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}})
    assert filter_hook_output(tmp_path, source="test", hook_json=payload, session_id="s1") == payload
    assert not (tmp_path / ".cognitive-os" / "metrics" / "context-budget.jsonl").exists()


def test_filter_hook_output_allows_block_with_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COS_ALLOW_CONTEXT_BUDGET_OVERRUN", "1")
    (tmp_path / "cognitive-os.yaml").write_text("context_budget:\n  static_max_tokens: 1\n", encoding="utf-8")
    payload = json.dumps({"hookSpecificOutput": {"additionalContext": "x" * 20}})
    assert filter_hook_output(tmp_path, source="test", hook_json=payload, session_id="s1") == payload
    row = json.loads((tmp_path / ".cognitive-os" / "metrics" / "context-budget.jsonl").read_text().splitlines()[-1])
    assert row["verdict"] == "BLOCK"
    assert row["allowed"] is True
    assert row["reason"] == "override"


def test_filter_hook_output_never_drops_silently(tmp_path: Path) -> None:
    """A budget-blocked payload must leave a trace and tell the consumer it was dropped.

    Suppressing is allowed; suppressing without a trace is the bug (gates-sin-trampa).
    Three things must hold when the budget forces a discard:
      1. the consumer learns a discard happened (the envelope survives with a notice),
      2. the discarded payload is identifiable in the metrics ledger (source + digest
         + preview + size), and
      3. the ledger's existing reader surfaces the discard.
    """
    (tmp_path / "cognitive-os.yaml").write_text("context_budget:\n  static_max_tokens: 1\n", encoding="utf-8")
    secret_context = "CRITICAL: the deploy key rotated, do not push. " * 8
    payload = {
        "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": secret_context},
    }

    out = filter_hook_output(tmp_path, source="my-hook", hook_json=json.dumps(payload), session_id="s1")

    # 1. The consumer must be able to find out that something was discarded.
    assert out != "", "budget-blocked payload vanished with no output at all"
    emitted = json.loads(out)
    notice = emitted["hookSpecificOutput"]["additionalContext"]
    assert secret_context not in notice, "notice must not smuggle the over-budget payload back in"
    assert "my-hook" in notice, "notice must name the hook whose output was dropped"
    assert "static" in notice, "notice must name the budget layer that forced the drop"
    assert emitted["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit", "envelope shape must survive"
    assert count_tokens(notice) <= 120, "the drop notice must itself be cheap"

    # 2. The ledger must identify what was dropped, from which hook, and why.
    log = tmp_path / ".cognitive-os" / "metrics" / "context-budget.jsonl"
    rows = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    assert len(rows) == 1, f"exactly one metric row per filtered payload, got {len(rows)}"
    row = rows[0]
    assert row["verdict"] == "BLOCK" and row["allowed"] is False
    assert row["dropped"] is True, "the ledger row does not mark the payload as dropped"
    assert row["source"] == "my-hook"
    assert row["dropped_chars"] == len(secret_context)
    assert row["dropped_sha256"] == hashlib.sha256(secret_context.encode("utf-8")).hexdigest()
    assert row["dropped_preview"], "no preview of the dropped payload was kept"
    assert secret_context.startswith(row["dropped_preview"])
    assert row["reason"], "a drop with an empty reason is a silent drop with extra steps"

    # 3. The reader of that ledger must surface the drop, not just store it.
    report = build_report(tmp_path, window_days=3650, now_epoch=time.time())
    assert report.dropped_count == 1
    assert report.dropped_by_source.get("my-hook") == 1
    assert any("drop" in finding.lower() for finding in report.findings), report.findings


def test_filter_hook_output_records_no_drop_when_budget_allows(tmp_path: Path) -> None:
    """The drop bookkeeping must not fire on payloads that pass the budget."""
    (tmp_path / "cognitive-os.yaml").write_text("context_budget:\n  static_max_tokens: 4000\n", encoding="utf-8")
    payload = json.dumps({"hookSpecificOutput": {"additionalContext": "small note"}})
    assert filter_hook_output(tmp_path, source="my-hook", hook_json=payload, session_id="s1") == payload
    row = json.loads((tmp_path / ".cognitive-os" / "metrics" / "context-budget.jsonl").read_text().splitlines()[-1])
    assert row["dropped"] is False
    assert "dropped_sha256" not in row
    report = build_report(tmp_path, window_days=3650, now_epoch=time.time())
    assert report.dropped_count == 0

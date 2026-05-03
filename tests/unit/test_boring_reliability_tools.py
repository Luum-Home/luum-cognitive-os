from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml

import scripts.cos_adoption_profile as adoption
import scripts.cos_default_visible_reducer as reducer
import scripts.cos_false_positive_ledger as fp_ledger
import scripts.cos_preamble_budget as preamble
import scripts.cos_wip_safety_score as wip


def primitive(pid: str, distribution: str, maturity: str = "advisory", state: str = "advisory") -> dict[str, object]:
    return {
        "id": pid,
        "kind": "hook",
        "owner_adr": "ADR-126",
        "lifecycle_state": state,
        "maturity": maturity,
        "distribution": distribution,
        "governance_class": "runtime-safety" if maturity == "blocking" else "delivery-structure",
        "risk_class": "blocking" if maturity == "blocking" else "advisory",
        "supported_harnesses": ["claude"],
        "projection_targets": [pid],
        "evidence_commands": [f"bash -n {pid}"],
        "exit_behavior": "exit_2" if maturity == "blocking" else "exit_0",
        "metrics_file": "none",
        "docs_claim_level": maturity,
        "rollback_or_repair_command": "disable",
        "sunset_criteria": "archive after no use",
    }


def write_manifest(tmp_path: Path, primitives: list[dict[str, object]]) -> Path:
    manifest = tmp_path / "primitive-lifecycle.yaml"
    manifest.write_text(yaml.safe_dump({"schema_version": 1, "primitives": primitives}), encoding="utf-8")
    return manifest


def test_adoption_profile_counts_core_surface(tmp_path: Path) -> None:
    manifest = write_manifest(tmp_path, [primitive("hooks/a.sh", "core", "blocking", "blocking"), primitive("hooks/b.sh", "lab", "observe", "sandbox")])

    report = adoption.build_profile("core", manifest)

    assert report["primitive_count"] == 1
    assert report["blocking_count"] == 1
    assert report["status"] == "pass"


def test_default_visible_reducer_recommends_non_killer_core(tmp_path: Path) -> None:
    manifest = write_manifest(tmp_path, [primitive("hooks/non-killer.sh", "core", "advisory")])

    report = reducer.build_recommendations(manifest)

    assert report["recommendation_count"] == 1
    assert report["recommendations"][0]["to"] == "lab"


def test_preamble_budget_reports_estimate(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("hello world", encoding="utf-8")
    docs = tmp_path / "docs" / "architecture"
    docs.mkdir(parents=True)
    (docs / "core-adoption-preamble.md").write_text("core preamble", encoding="utf-8")
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "RULES-COMPACT.md").write_text("rule text", encoding="utf-8")
    fake_adoption = {"default_visible_count": 1, "blocking_count": 1}
    monkeypatch.setattr(preamble.cos_adoption_profile, "build_profile", lambda profile: fake_adoption)

    report = preamble.build_budget("core", tmp_path)

    assert report["estimated_tokens"] > 0
    assert report["budget_tokens"] == 3200
    assert "AGENTS.md" in report["file_tokens"]


def test_false_positive_ledger_ignores_payload_filename_matches(tmp_path: Path) -> None:
    metrics = tmp_path / "metrics"
    metrics.mkdir()
    (metrics / "so-vitals.jsonl").write_text(
        '{"hook":"so-vitals","files":[".cognitive-os/metrics/adaptive-bypass.jsonl"]}\n',
        encoding="utf-8",
    )

    report = fp_ledger.build_report(metrics)

    assert report["false_positive_events"] == 0
    assert report["status"] == "pass"


def test_false_positive_ledger_counts_scoped_signals(tmp_path: Path) -> None:
    metrics = tmp_path / "metrics"
    metrics.mkdir()
    (metrics / "gate.jsonl").write_text(
        "\n".join(
            [
                '{"hook":"claim-gate","false_positive":true}',
                '{"hook":"claim-gate","operator_bypass":true}',
                '{"hook":"claim-gate","bypass_reason":"operator accepted false positive"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = fp_ledger.build_report(metrics)

    assert report["false_positive_events"] == 3
    assert report["top_hooks"] == [{"hook": "claim-gate", "count": 3}]


def test_wip_safety_score_penalizes_dirty_and_stash(tmp_path: Path) -> None:
    with patch.object(wip, "run_git", side_effect=lambda args, root: " M x\n" if args[0] == "status" else "stash@{0}: test\n"):
        report = wip.build_score(tmp_path)

    assert report["score"] < 100
    assert report["stash_count"] == 1


def test_dispatch_metrics_evidence_warns_when_empty(tmp_path: Path) -> None:
    import scripts.cos_boring_reliability as boring

    report = boring.dispatch_metrics_evidence(tmp_path)

    assert report["status"] == "warn"
    assert report["repair_command"] == "scripts/cos-dispatch-smoke --json"


def test_boring_reliability_includes_demotion_loop_status(tmp_path: Path, monkeypatch) -> None:
    import scripts.cos_boring_reliability as boring

    monkeypatch.setattr(boring.runtime_hook_reality, "build_report", lambda project_root: {"summary": {"status": "pass"}})
    monkeypatch.setattr(boring.cos_adoption_profile, "build_profile", lambda profile: {"status": "pass", "primitive_count": 0, "hook_count": 0, "default_visible_count": 0, "blocking_count": 0})
    monkeypatch.setattr(boring.cos_preamble_budget, "build_budget", lambda profile, root: {"status": "pass"})
    monkeypatch.setattr(boring.cos_default_visible_reducer, "build_recommendations", lambda: {"status": "pass", "recommendation_count": 0, "recommendations": []})
    monkeypatch.setattr(boring.cos_false_positive_ledger, "build_report", lambda path: {"status": "pass"})
    monkeypatch.setattr(boring.cos_wip_safety_score, "build_score", lambda root: {"status": "pass"})
    monkeypatch.setattr(boring.silent_failure_audit, "build_report", lambda root, scan, allow: {"status": "pass", "file_count": 0, "occurrence_count": 0, "fail_count": 0, "warn_count": 0})
    monkeypatch.setattr(boring.session_start_budget, "build_report", lambda profile, root: {"status": "pass", "profile": profile, "session_start_hook_count": 0, "counts_by_tier": {}, "budget": {}, "findings": []})
    monkeypatch.setattr(boring, "dispatch_metrics_evidence", lambda root: {"status": "pass"})
    monkeypatch.setattr(boring.cos_demotion_loop_audit, "build_report", lambda manifest: {"status": "warn", "demotion_count": 1, "roi_signed_demotion_count": 0, "findings": [], "policy": "test"})
    monkeypatch.setattr(boring, "readiness_summary", lambda root: {"status": "pass"})

    report = boring.build_dashboard("core", tmp_path)

    assert report["status"] == "warn"
    assert report["demotion_loop"]["demotion_count"] == 1
    assert report["demotion_loop"]["roi_signed_demotion_count"] == 0


def test_dispatch_smoke_writes_metrics(tmp_path: Path, monkeypatch) -> None:
    import scripts.cos_dispatch_smoke as smoke

    monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("CODEX_PROJECT_DIR", "")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

    report = smoke.build_report(tmp_path, "offline dispatch smoke test")

    assert report["status"] == "pass"
    assert (tmp_path / ".cognitive-os" / "metrics" / "llm-dispatch.jsonl").stat().st_size > 0
    assert (tmp_path / ".cognitive-os" / "metrics" / "task-history.jsonl").stat().st_size > 0

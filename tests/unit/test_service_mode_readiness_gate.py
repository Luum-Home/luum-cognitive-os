import json
import shutil
from pathlib import Path

from lib.service_mode_readiness import build_readiness_report

REPO = Path(__file__).resolve().parents[2]


def _copy_manifest(name: str, root: Path) -> None:
    dest = root / "manifests" / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "manifests" / name, dest)


def test_readiness_gate_fails_when_private_content_manifest_missing(tmp_path):
    report = build_readiness_report(tmp_path)

    private_gate = next(gate for gate in report["gates"] if gate["id"] == "private-content")
    assert report["status"] == "red"
    assert private_gate["status"] == "red"
    assert "manifest missing" in private_gate["summary"]


def test_readiness_gate_fails_when_trace_joiner_missing(tmp_path):
    _copy_manifest("private-content.yaml", tmp_path)
    _copy_manifest("reward-signal-contract.yaml", tmp_path)
    _copy_manifest("cross-stack-secret-audit.yaml", tmp_path)

    report = build_readiness_report(tmp_path)

    trace_gate = next(gate for gate in report["gates"] if gate["id"] == "run-flight-recorder")
    assert report["status"] == "red"
    assert trace_gate["status"] == "red"
    assert "latest run trace report missing" in trace_gate["summary"]


def test_readiness_gate_fails_when_secret_audit_manifest_missing(tmp_path):
    _copy_manifest("private-content.yaml", tmp_path)
    _copy_manifest("reward-signal-contract.yaml", tmp_path)

    report = build_readiness_report(tmp_path)

    secret_gate = next(gate for gate in report["gates"] if gate["id"] == "release-secret-audit")
    assert report["status"] == "red"
    assert secret_gate["status"] == "red"
    assert "secret audit manifest missing" in secret_gate["summary"]


def test_readiness_gate_fails_when_secret_audit_has_sensitive_surface(tmp_path):
    _copy_manifest("private-content.yaml", tmp_path)
    _copy_manifest("reward-signal-contract.yaml", tmp_path)
    _copy_manifest("cross-stack-secret-audit.yaml", tmp_path)
    (tmp_path / ".env").write_text("SECRET=value\n", encoding="utf-8")

    report = build_readiness_report(tmp_path)

    secret_gate = next(gate for gate in report["gates"] if gate["id"] == "release-secret-audit")
    assert report["status"] == "red"
    assert secret_gate["status"] == "red"
    assert secret_gate["evidence"]["status"] == "warn"


def test_readiness_gate_accepts_core_substrates_but_keeps_experiment_red(tmp_path):
    _copy_manifest("private-content.yaml", tmp_path)
    _copy_manifest("reward-signal-contract.yaml", tmp_path)
    _copy_manifest("cross-stack-secret-audit.yaml", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy(REPO / "scripts" / "cos-maintainer-agent", scripts / "cos-maintainer-agent")
    shutil.copy(REPO / "scripts" / "cos-promote-from-telemetry", scripts / "cos-promote-from-telemetry")
    shutil.copy(REPO / "scripts" / "cos_claim_signature_audit.py", scripts / "cos_claim_signature_audit.py")
    (scripts / "cos_demotion_loop_audit.py").write_text("def build_report(*args, **kwargs): return {'findings': []}\n", encoding="utf-8")
    skills = tmp_path / "skills" / "docs-to-artifact"
    skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text("---\nname: docs-to-artifact\n---\n", encoding="utf-8")
    metrics = tmp_path / ".cognitive-os" / "metrics"
    reports = tmp_path / ".cognitive-os" / "reports"
    metrics.mkdir(parents=True)
    reports.mkdir(parents=True)
    (metrics / "skill-feedback.jsonl").write_text(
        '{"timestamp":"2026-05-06T00:00:00Z","skill":"docs-to-artifact","success":true}\n',
        encoding="utf-8",
    )
    (reports / "run-trace-latest.json").write_text(
        json.dumps({"schema_version": "run-flight-recorder/v1", "event_count": 1, "streams": {"hook-timing": 1}}),
        encoding="utf-8",
    )
    (reports / "performance-ledger-latest.json").write_text(
        json.dumps({
            "schema_version": "performance-ledger/v1",
            "summary": {"valid": 1, "suspect": 0, "corrupt": 0, "total": 1, "eligible_for_rollup": 1},
            "consumption_policy": {"can_consume_all": True, "blocked_streams": []},
        }),
        encoding="utf-8",
    )

    report = build_readiness_report(tmp_path)

    assert next(g for g in report["gates"] if g["id"] == "private-content")["status"] == "green"
    assert next(g for g in report["gates"] if g["id"] == "run-flight-recorder")["status"] == "green"
    assert next(g for g in report["gates"] if g["id"] == "performance-ledger")["status"] == "green"
    assert next(g for g in report["gates"] if g["id"] == "reward-signals")["status"] == "green"
    assert next(g for g in report["gates"] if g["id"] == "release-secret-audit")["status"] == "green"
    assert next(g for g in report["gates"] if g["id"] == "maintainer-experiment-contract")["status"] == "red"
    assert report["status"] == "red"

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts import cos_lean_skillopt


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_skill(tmp_path: Path) -> Path:
    path = tmp_path / "skills/demo/SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text("---\nname: demo\n---\n\n# Demo\n\nOriginal rule.\n", encoding="utf-8")
    return path


def test_lean_audit_detects_yagni_dependency_and_writes_report(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"dependencies":{"left-pad":"1.0.0"}}\n', encoding="utf-8")
    src = tmp_path / "src/service.py"
    src.parent.mkdir()
    src.write_text("class PaymentManagerFactory:\n    pass\n", encoding="utf-8")
    rc = cos_lean_skillopt.main(["lean-audit", "--project-dir", str(tmp_path), "--json"])
    assert rc == 0
    report = read_json(tmp_path / ".cognitive-os/lean/audit-latest.json")
    tags = {f["tag"] for f in report["findings"]}
    assert "dependency" in tags
    assert "yagni" in tags


def test_lean_debt_requires_upgrade_trigger(tmp_path: Path) -> None:
    f = tmp_path / "src/a.py"
    f.parent.mkdir()
    f.write_text("# cos-lean: simple global cache; upgrade: concurrent writes appear\n# cos-lean: missing trigger\n", encoding="utf-8")
    rc = cos_lean_skillopt.main(["lean-debt", "--project-dir", str(tmp_path), "--strict", "--json"])
    assert rc == 2
    ledger = read_json(tmp_path / ".cognitive-os/lean/debt-ledger.json")
    assert ledger["count"] == 2
    assert ledger["missing_trigger_count"] == 1


def test_skill_proposal_stage_does_not_mutate_live_skill(tmp_path: Path) -> None:
    skill = write_skill(tmp_path)
    original = skill.read_text(encoding="utf-8")
    rc = cos_lean_skillopt.main([
        "skill-proposal-stage",
        "--project-dir",
        str(tmp_path),
        "--run-id",
        "r1",
        "--skill",
        str(skill),
        "--edit-add",
        "Always verify with a runnable command.",
        "--json",
    ])
    assert rc == 0
    assert skill.read_text(encoding="utf-8") == original
    manifest = read_json(tmp_path / ".cognitive-os/skill-opt/r1/staging/manifest.json")
    proposed = Path(manifest["proposed_skill_path"]).read_text(encoding="utf-8")
    assert "Always verify" in proposed
    assert "COS_SKILL_LEARNED_START" in proposed


def test_skill_edit_gate_accepts_only_strict_improvement(tmp_path: Path) -> None:
    assert cos_lean_skillopt.main(["skill-edit-gate", "--project-dir", str(tmp_path), "--run-id", "r1", "--baseline-score", "0.5", "--candidate-score", "0.5", "--json"]) == 2
    rejected = read_json(tmp_path / ".cognitive-os/skill-opt/r1/gate.json")
    assert rejected["accepted"] is False
    assert cos_lean_skillopt.main(["skill-edit-gate", "--project-dir", str(tmp_path), "--run-id", "r1", "--baseline-score", "0.5", "--candidate-score", "0.7", "--json"]) == 0
    accepted = read_json(tmp_path / ".cognitive-os/skill-opt/r1/gate.json")
    assert accepted["accepted"] is True


def test_skill_adopt_requires_gate_and_backs_up(tmp_path: Path) -> None:
    skill = write_skill(tmp_path)
    assert cos_lean_skillopt.main(["skill-proposal-stage", "--project-dir", str(tmp_path), "--run-id", "r1", "--skill", str(skill), "--edit-add", "New validated rule."]) == 0
    assert cos_lean_skillopt.main(["skill-adopt", "--project-dir", str(tmp_path), "--run-id", "r1", "--apply", "--json"]) == 2
    assert "New validated rule" not in skill.read_text(encoding="utf-8")
    assert cos_lean_skillopt.main(["skill-edit-gate", "--project-dir", str(tmp_path), "--run-id", "r1", "--baseline-score", "0.1", "--candidate-score", "0.2"]) == 0
    assert cos_lean_skillopt.main(["skill-adopt", "--project-dir", str(tmp_path), "--run-id", "r1", "--apply", "--json"]) == 0
    assert "New validated rule" in skill.read_text(encoding="utf-8")
    adopt = read_json(tmp_path / ".cognitive-os/skill-opt/r1/adopt.json")
    assert Path(adopt["backup_path"]).exists()


def test_rejected_buffer_records_and_reports(tmp_path: Path) -> None:
    assert cos_lean_skillopt.main(["skill-rejected-buffer", "--project-dir", str(tmp_path), "--run-id", "r1", "--edit", "bad edit", "--reason", "gate failed", "--json"]) == 0
    assert cos_lean_skillopt.main(["skill-rejected-buffer", "--project-dir", str(tmp_path), "--run-id", "r1", "--report", "--json"]) == 0
    rows = (tmp_path / ".cognitive-os/skill-opt/r1/rejected-edits.jsonl").read_text(encoding="utf-8")
    assert "bad edit" in rows


def test_slow_update_stages_protected_region(tmp_path: Path) -> None:
    skill = write_skill(tmp_path)
    assert cos_lean_skillopt.main(["skill-slow-update", "--project-dir", str(tmp_path), "--run-id", "slow", "--skill", str(skill), "--guidance", "Keep gates on by default.", "--json"]) == 0
    proposed = (tmp_path / ".cognitive-os/skill-opt/slow/staging/proposed_SKILL.md").read_text(encoding="utf-8")
    assert "COS_SKILL_SLOW_UPDATE_START" in proposed
    assert "Keep gates on" in proposed
    assert "Original rule" in proposed


def test_skill_opt_run_stages_and_gates(tmp_path: Path) -> None:
    skill = write_skill(tmp_path)
    rc = cos_lean_skillopt.main([
        "skill-opt-run",
        "--project-dir", str(tmp_path),
        "--run-id", "run",
        "--skill", str(skill),
        "--edit-add", "Use held-out validation.",
        "--baseline-score", "0.4",
        "--candidate-score", "0.6",
        "--json",
    ])
    assert rc == 0
    assert read_json(tmp_path / ".cognitive-os/skill-opt/run/gate.json")["accepted"] is True
    assert (tmp_path / ".cognitive-os/skill-opt/run/staging/proposal.diff").exists()


def test_skill_sleep_mines_traces_and_stages(tmp_path: Path) -> None:
    skill = write_skill(tmp_path)
    trace_dir = tmp_path / ".cognitive-os/process-loops/p"
    trace_dir.mkdir(parents=True)
    (trace_dir / "trace.jsonl").write_text('{"event":"verify","status":"failed"}\n', encoding="utf-8")
    assert cos_lean_skillopt.main(["skill-sleep", "--project-dir", str(tmp_path), "--run-id", "night", "--skill", str(skill), "--trace-dir", str(trace_dir), "--json"]) == 0
    report = read_json(tmp_path / ".cognitive-os/skill-opt/night/sleep-report.json")
    assert report["tasks_mined"] == 1
    proposed = (tmp_path / ".cognitive-os/skill-opt/night/staging/proposed_SKILL.md").read_text(encoding="utf-8")
    assert "Longitudinal Skill Guidance" in proposed


def test_skill_opt_run_json_is_single_object(tmp_path: Path) -> None:
    project = tmp_path / "project"
    skill = project / "skills" / "demo" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: demo\nversion: 0.1.0\ndescription: demo\ntriggers: [demo]\n---\n# Demo\n", encoding="utf-8")

    result = subprocess.run(
        [
            "scripts/cos-skill-opt-run",
            "--project-dir",
            str(project),
            "--run-id",
            "single-json",
            "--skill",
            str(skill),
            "--edit-add",
            "Add verification evidence.",
            "--baseline-score",
            "0.1",
            "--candidate-score",
            "0.2",
            "--json",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[2],
        text=True,
        capture_output=True,
    )

    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "cos.skill-opt-run.v1"
    assert payload["staged"] is True
    assert payload["gate_rc"] == 0

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cos_efficiency_primitives.py"
SO_IMPACT = ROOT / "scripts" / "cos_so_impact_eval.py"


def run_json(*args: str, cwd: Path | None = None, check: bool = True) -> dict:
    proc = subprocess.run([sys.executable, str(SCRIPT), *args, "--json"], cwd=cwd or ROOT, text=True, capture_output=True, check=False)
    if check and proc.returncode != 0:
        raise AssertionError(f"rc={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}")
    return json.loads(proc.stdout)


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)


def test_testing_capabilities_detects_node_python_go_rust(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"scripts":{"test":"vitest","lint":"eslint ."}}')
    (tmp_path / "tests").mkdir()
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n")
    (tmp_path / "go.mod").write_text("module example.com/x\n")
    (tmp_path / "Cargo.toml").write_text("[package]\nname='x'\nversion='0.1.0'\n")
    payload = run_json("testing-capabilities", "--project-dir", str(tmp_path))
    stacks = {c["stack"] for c in payload["capabilities"]}
    assert {"node", "python", "go", "rust"}.issubset(stacks)
    assert payload["strict_tdd_supported"] is True


def test_skill_registry_refresh_writes_path_index_without_skill_bodies(tmp_path: Path):
    skill = tmp_path / "skills" / "demo" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: demo\ndescription: Demo skill.\ntriggers: [/demo]\n---\n\n# Demo\n\nSECRET BODY SHOULD NOT BE IN REGISTRY\n")
    out = tmp_path / ".cognitive-os" / "skill-registry.md"
    payload = run_json("skill-registry-refresh", "--project-dir", str(tmp_path), "--output", str(out))
    assert payload["skill_count"] >= 1
    text = out.read_text()
    assert "demo" in text
    assert "Demo skill" in text
    assert "SECRET BODY" not in text
    assert (out.parent / ".skill-registry.cache.json").exists()


def test_context_plan_role_selection_and_review_workload_use_git_state(tmp_path: Path):
    init_repo(tmp_path)
    src = tmp_path / "src"
    src.mkdir()
    (src / "money.py").write_text("def format_money(value):\n    return f'${value}'\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=tmp_path, check=True)
    (src / "money.py").write_text("def format_money(value):\n    cents = int(value * 100)\n    return f'${cents / 100:.2f}'\n")
    ctx = run_json("context-plan", "--project-dir", str(tmp_path), "--goal", "fix format_money")
    assert ctx["selected_files"]
    assert ctx["selected_files"][0]["path"] == "src/money.py"
    roles = run_json("role-selection-report", "--project-dir", str(tmp_path), "--goal", "fix money bug")
    assert "planner" in {r["role"] for r in roles["roles"]}
    review = run_json("review-workload-forecast", "--project-dir", str(tmp_path))
    assert review["changed_file_count"] == 1
    assert review["risk"] == "low"


def test_tdd_evidence_verify_blocks_when_runner_exists_but_evidence_missing(tmp_path: Path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_demo.py").write_text("def test_demo():\n    assert True\n")
    proc = subprocess.run([sys.executable, str(SCRIPT), "tdd-evidence-verify", "--project-dir", str(tmp_path), "--json"], text=True, capture_output=True)
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["strict_tdd_required"] is True
    assert payload["passed"] is False


def test_projection_transaction_plan_and_status(tmp_path: Path):
    (tmp_path / "AGENTS.md").write_text("agents")
    payload = run_json("projection-transaction", "--project-dir", str(tmp_path), "--path", "AGENTS.md")
    assert payload["mode"] == "plan"
    assert payload["receipts"][0]["exists"] is True
    status = run_json("status", "--project-dir", str(tmp_path), "--goal", "organize context")
    assert status["schema"] == "cos.efficiency.status.v1"
    assert "generic" in status["summary"]["detected_adapters"]


def test_so_impact_catalog_exposes_expanded_families_and_metrics():
    proc = subprocess.run([sys.executable, str(SO_IMPACT), "catalog", "--json"], text=True, capture_output=True, check=True)
    payload = json.loads(proc.stdout)
    assert "bugfix" in payload["task_families"]
    assert "full-so-minus-graphify" in payload["modes"]
    assert "false_claims" in payload["metrics"]

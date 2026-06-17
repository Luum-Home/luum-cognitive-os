# SCOPE: os-only
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WRAPPERS = ["cos-claim-audit", "cos-evidence-rank", "cos-benchmark-gaming-audit"]
SKILL_PATHS = [
    ROOT / "skills" / "epistemic-review" / "SKILL.md",
    ROOT / ".cognitive-os" / "skills" / "epistemic-review" / "SKILL.md",
    ROOT / ".cognitive-os" / "skills" / "cos" / "epistemic-review" / "SKILL.md",
    ROOT / ".claude" / "skills" / "epistemic-review" / "SKILL.md",
    ROOT / ".codex" / "skills" / "epistemic-review" / "SKILL.md",
]


def run_wrapper(name: str, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(ROOT / "scripts" / name), *args], cwd=cwd, text=True, capture_output=True, timeout=30, check=False)


def test_epistemic_review_wrappers_exist_and_are_valid_bash() -> None:
    for name in WRAPPERS:
        artifact = ROOT / "scripts" / name
        assert artifact.exists(), name
        assert artifact.stat().st_mode & 0o111, name
        subprocess.run(["bash", "-n", str(artifact)], cwd=ROOT, check=True)


def test_epistemic_review_skill_projected_to_cli_and_ide_surfaces() -> None:
    canonical = SKILL_PATHS[0].read_text(encoding="utf-8")
    for path in SKILL_PATHS:
        assert path.exists(), str(path)
        assert path.read_text(encoding="utf-8") == canonical


def test_epistemic_review_wrappers_run_from_arbitrary_consumer_cwd(tmp_path: Path) -> None:
    project = tmp_path / "consumer"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (project / "src").mkdir()
    (project / "src" / "bench.py").write_text("if mode == 'benchmark':\n    return 'cheat benchmark'\n", encoding="utf-8")

    rank = run_wrapper("cos-evidence-rank", outside, "--evidence", "self-reported benchmark", "--evidence", "pytest output exit 0", "--json")
    assert rank.returncode == 0, rank.stderr + rank.stdout
    assert json.loads(rank.stdout)["ranked"][0]["tier"] == "source-code-tests-now"

    claim = run_wrapper(
        "cos-claim-audit",
        outside,
        "--project-dir",
        str(project),
        "--claim",
        "tests pass",
        "--source-interest",
        "neutral",
        "--evidence",
        "pytest command output exit 0",
        "--verification-command",
        "python3 -c 'raise SystemExit(0)'",
        "--json",
    )
    assert claim.returncode == 0, claim.stderr + claim.stdout
    assert json.loads(claim.stdout)["receipt_path"].startswith(str(project))

    bench = run_wrapper("cos-benchmark-gaming-audit", outside, "--project-dir", str(project), "--path", "src", "--json")
    assert bench.returncode == 2, bench.stderr + bench.stdout
    assert json.loads(bench.stdout)["verdict"] == "needs-refutation"

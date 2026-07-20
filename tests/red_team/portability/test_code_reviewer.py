# SCOPE: os-only
"""Portability proof for cos_lib/code_reviewer.py.

``code_reviewer`` backs ``hooks/code-review-on-commit.sh`` (SCOPE: both), a
consumer-facing pre-commit hook. This proof pins that the module imports and
its primary entry point (``CodeReviewer.review_files``) runs correctly from
an arbitrary working directory, reading only files under a ``project_root``
passed in by the caller — never anything that assumes it is running inside
the Cognitive OS source repo itself.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/code_reviewer.py"


def test_code_reviewer_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_code_reviewer", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_review_files_works_in_arbitrary_consumer_project(tmp_path: Path) -> None:
    """Falsification probe: exercise the real entry point in a throwaway project.

    Writes a source file with a hardcoded-secret pattern under ``tmp_path``
    (standing in for a consumer project that merely installed the OS — not
    the Cognitive OS source repo), and confirms ``review_files`` detects the
    BLOCKER finding and fails the review, run from an unrelated cwd via
    subprocess — proving the reviewer has no dependency on the OS repo tree.
    """
    project_dir = tmp_path / "consumer-project"
    project_dir.mkdir()
    (project_dir / "config.py").write_text(
        'API_KEY = "abcd1234efgh5678"\n'
    )

    unrelated_cwd = tmp_path / "somewhere-else"
    unrelated_cwd.mkdir()

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from cos_lib.code_reviewer import CodeReviewer\n"
        "reviewer = CodeReviewer(project_root=%r)\n"
        "report = reviewer.review_files(['config.py'])\n"
        "print(report.status.value)\n"
        "print(report.blocker_count)\n"
        "print(report.files_reviewed)\n"
    ) % (str(REPO_ROOT), str(project_dir))

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=unrelated_cwd,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    out_lines = result.stdout.strip().splitlines()
    assert out_lines[0] == "FAILED", result.stdout + result.stderr
    assert int(out_lines[1]) >= 1
    assert int(out_lines[2]) == 1


def test_review_files_enforces_adversarial_finding_on_clean_file(tmp_path: Path) -> None:
    """Falsification probe: a clean file still yields >=1 finding (adversarial
    review protocol), proving the module's own invariant holds outside the
    OS repo too — not just a hardcoded fixture path.
    """
    project_dir = tmp_path / "clean-consumer-project"
    project_dir.mkdir()
    (project_dir / "clean.py").write_text("def add(a, b):\n    return a + b\n")

    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_code_reviewer_clean", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    reviewer = module.CodeReviewer(project_root=str(project_dir))
    report = reviewer.review_files(["clean.py"])
    assert len(report.findings) >= 1
    assert report.status == module.ReviewStatus.PASSED

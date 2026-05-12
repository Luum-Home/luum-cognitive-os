# SCOPE: both
"""Portability probes for scripts/cos-adr-implementation-audit.py (ADR-281).

Bilateral: synthetic ADR + manifest combinations exercise the audit.

Falsification:
  1. ADR claims implemented + file exists -> no finding
  2. ADR claims implemented + file missing + not in allowlist -> warn finding
  3. ADR claims implemented + file missing + in allowlist -> no finding
  4. ADR claims partial -> ignored (audit only checks implemented)
  5. --strict exits 2 if any non-allowlisted overclaim present
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "cos-adr-implementation-audit.py"


def _run(project_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("COGNITIVE_OS_PROJECT_DIR", None)
    env.pop("CODEX_PROJECT_DIR", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    cmd = [sys.executable, str(SCRIPT), "--project-dir", str(project_dir), *extra]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=15)


def _seed_adr(
    project_dir: Path,
    num: int,
    *,
    status: str = "implemented",
    files: list[str] | None = None,
) -> None:
    adr_dir = project_dir / "docs" / "adrs"
    adr_dir.mkdir(parents=True, exist_ok=True)
    body = ["---", f"adr: {num}", f"title: test {num}", f"implementation_status: {status}"]
    if files is not None:
        body.append("implementation_files:")
        for f in files:
            body.append(f"  - {f}")
    body.append("---")
    body.append(f"# ADR-{num}\nbody")
    (adr_dir / f"ADR-{num:03d}-test.md").write_text("\n".join(body) + "\n")


def _seed_allowlist(project_dir: Path, patterns: list[str]) -> None:
    manifests = project_dir / "manifests"
    manifests.mkdir(parents=True, exist_ok=True)
    text = "schema_version: adr-implementation-runtime-allowlist/v1\nentries:\n"
    for p in patterns:
        text += f"  - pattern: '{p}'\n    rationale: test\n    owner: test\n"
    (manifests / "adr-implementation-runtime-allowlist.yaml").write_text(text)


def test_bilateral_all_files_exist_yields_no_findings(tmp_path: Path) -> None:
    """Bilateral: implemented ADR with all files present -> 0 findings."""
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "real.py").write_text("# present\n")
    _seed_adr(tmp_path, 100, files=["lib/real.py"])
    cp = _run(tmp_path)
    assert cp.returncode == 0, cp.stderr
    payload = json.loads(cp.stdout)
    assert payload["schema_version"] == "adr-implementation-audit/v1"
    assert payload["summary"]["missing_files"] == 0
    assert payload["findings"] == []


def test_falsification_missing_file_yields_warn(tmp_path: Path) -> None:
    """Falsification: implemented ADR with missing non-allowlisted file -> 1 finding."""
    _seed_adr(tmp_path, 101, files=["lib/missing.py"])
    cp = _run(tmp_path)
    payload = json.loads(cp.stdout)
    assert payload["summary"]["missing_files"] == 1
    f = payload["findings"][0]
    assert f["severity"] == "warn"
    assert f["code"] == "adr-implementation-file-missing"
    assert "lib/missing.py" in f["message"]
    assert f["stable_id"].startswith("adr-281/missing/")


def test_bilateral_allowlist_suppresses_missing(tmp_path: Path) -> None:
    """Bilateral: missing file matches allowlist -> NOT a finding."""
    _seed_adr(tmp_path, 102, files=[".cognitive-os/metrics/x.jsonl"])
    _seed_allowlist(tmp_path, [".cognitive-os/metrics/*.jsonl"])
    cp = _run(tmp_path)
    payload = json.loads(cp.stdout)
    assert payload["summary"]["missing_files"] == 0
    assert payload["summary"]["allowlisted_files"] == 1


def test_falsification_partial_status_ignored(tmp_path: Path) -> None:
    """Falsification: status: partial -> not audited (only implemented is)."""
    _seed_adr(tmp_path, 103, status="partial", files=["lib/missing.py"])
    cp = _run(tmp_path)
    payload = json.loads(cp.stdout)
    assert payload["summary"]["total_implemented_adrs"] == 0
    assert payload["summary"]["missing_files"] == 0


def test_strict_exits_2_on_overclaim(tmp_path: Path) -> None:
    _seed_adr(tmp_path, 104, files=["lib/missing.py"])
    cp = _run(tmp_path, "--strict")
    assert cp.returncode == 2


def test_strict_passes_when_clean(tmp_path: Path) -> None:
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "present.py").write_text("# present\n")
    _seed_adr(tmp_path, 105, files=["lib/present.py"])
    cp = _run(tmp_path, "--strict")
    assert cp.returncode == 0


def test_comment_in_implementation_file_entry_stripped(tmp_path: Path) -> None:
    """Bilateral: entries like `- lib/foo.py # comment` parse correctly."""
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "real.py").write_text("# present\n")
    _seed_adr(tmp_path, 106, files=["lib/real.py            # inline comment"])
    cp = _run(tmp_path)
    payload = json.loads(cp.stdout)
    assert payload["summary"]["missing_files"] == 0

# SCOPE: os-only
"""Portability probes for scripts/cos-subprocess-timeout-audit.py (ADR-278).

Bilateral: builds a synthetic project with timed/untimed/allowlisted calls
and verifies counts + findings shape.

Falsification:
  1. Empty project -> total=0, coverage=100, no findings
  2. All calls have timeout= -> coverage=100
  3. One untimed call -> 1 finding, severity warn
  4. Allowlisted untimed call -> NOT counted as finding
  5. --strict exits 2 when any untimed-non-allowlisted exists
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "cos-subprocess-timeout-audit.py"


def _run(project_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("COGNITIVE_OS_PROJECT_DIR", None)
    env.pop("CODEX_PROJECT_DIR", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    cmd = [sys.executable, str(SCRIPT), "--project-dir", str(project_dir), *extra]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=15)


def _seed(project_dir: Path, rel: str, content: str) -> None:
    p = project_dir / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_empty_project_yields_100pct(tmp_path: Path) -> None:
    cp = _run(tmp_path)
    assert cp.returncode == 0
    payload = json.loads(cp.stdout)
    assert payload["schema_version"] == "subprocess-timeout-audit/v1"
    assert payload["summary"]["total_calls"] == 0
    assert payload["summary"]["coverage_pct"] == 100.0
    assert payload["findings"] == []


def test_bilateral_all_timed_yields_full_coverage(tmp_path: Path) -> None:
    _seed(tmp_path, "scripts/x.py", textwrap.dedent("""
        import subprocess
        subprocess.run(['ls'], timeout=5)
        subprocess.run(['date'], capture_output=True, timeout=10)
    """))
    cp = _run(tmp_path)
    payload = json.loads(cp.stdout)
    s = payload["summary"]
    assert s["total_calls"] == 2
    assert s["timed_calls"] == 2
    assert s["untimed_calls"] == 0
    assert s["coverage_pct"] == 100.0
    assert payload["findings"] == []


def test_falsification_untimed_yields_warn(tmp_path: Path) -> None:
    _seed(tmp_path, "scripts/y.py", textwrap.dedent("""
        import subprocess
        subprocess.run(['sleep', 'forever'])
    """))
    cp = _run(tmp_path)
    payload = json.loads(cp.stdout)
    assert payload["summary"]["untimed_calls"] == 1
    assert len(payload["findings"]) == 1
    f = payload["findings"][0]
    assert f["severity"] == "warn"
    assert f["code"] == "subprocess-run-without-timeout"
    assert f["details"]["path"] == "scripts/y.py"
    assert f["stable_id"].startswith("adr-278/subprocess-timeout/")


def test_bilateral_allowlist_excludes_call(tmp_path: Path) -> None:
    _seed(tmp_path, "scripts/server.py", textwrap.dedent("""
        import subprocess
        subprocess.run(['/usr/bin/long-running-server'])
    """))
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    (manifests / "subprocess-timeout-allowlist.yaml").write_text(textwrap.dedent("""
        schema_version: subprocess-timeout-allowlist/v1
        owner_adr: ADR-278
        entries:
          - path: scripts/server.py
            line: 3
            rationale: long-running server, intentional
            owner: ops
    """))
    cp = _run(tmp_path)
    payload = json.loads(cp.stdout)
    assert payload["summary"]["untimed_calls"] == 0
    assert payload["summary"]["allowlisted_calls"] == 1
    assert payload["findings"] == []


def test_falsification_strict_exits_2(tmp_path: Path) -> None:
    _seed(tmp_path, "scripts/z.py", "import subprocess\nsubprocess.run(['x'])\n")
    cp = _run(tmp_path, "--strict")
    assert cp.returncode == 2


def test_strict_passes_when_clean(tmp_path: Path) -> None:
    _seed(tmp_path, "scripts/a.py", "import subprocess\nsubprocess.run(['x'], timeout=5)\n")
    cp = _run(tmp_path, "--strict")
    assert cp.returncode == 0


def test_findings_have_control_plane_shape(tmp_path: Path) -> None:
    _seed(tmp_path, "scripts/y.py", "import subprocess\nsubprocess.run(['x'])\n")
    cp = _run(tmp_path)
    payload = json.loads(cp.stdout)
    f = payload["findings"][0]
    for key in ("severity", "code", "message", "details", "stable_id", "adr"):
        assert key in f, f"missing {key}"
    assert f["adr"] == "ADR-278"

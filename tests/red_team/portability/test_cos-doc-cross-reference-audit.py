# SCOPE: both
"""Portability probes for scripts/cos-doc-cross-reference-audit.py (ADR-275).

Bilateral: builds a synthetic mini-project where some surfaces mention
known primitives and some don't; audit must detect missing references
deterministically.

Falsification:
  1. All surfaces mention required tokens -> 100% coverage, no findings
  2. One surface missing one token -> 1 finding, missing_count=1
  3. --strict exits 2 if any miss
  4. Missing surface file -> finding with surface_exists=False
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "cos-doc-cross-reference-audit.py"


def _run(project_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("COGNITIVE_OS_PROJECT_DIR", None)
    env.pop("CODEX_PROJECT_DIR", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    cmd = [sys.executable, str(SCRIPT), "--project-dir", str(project_dir), *extra]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)


def _seed_surface(project_dir: Path, rel: str, content: str) -> None:
    p = project_dir / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _load_contracts() -> list[dict]:
    """Import CONTRACTS from the audit script so tests track new contracts automatically."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("xref_audit", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CONTRACTS


def _seed_full_coverage(project_dir: Path) -> None:
    """Populate every surface listed in CONTRACTS with all required tokens.

    Derived dynamically so adding new contracts to the audit script does
    not silently break the test bilateral pass.
    """
    contracts = _load_contracts()
    blob = " ".join(c["grep"] for c in contracts) + "\n"
    surfaces: set[str] = set()
    for c in contracts:
        surfaces.update(c["required_in"])
    for rel in surfaces:
        _seed_surface(project_dir, rel, blob)


def test_falsification_empty_project_all_missing(tmp_path: Path) -> None:
    cp = _run(tmp_path)
    assert cp.returncode == 0
    payload = json.loads(cp.stdout)
    assert payload["schema_version"] == "doc-cross-reference-audit/v1"
    assert payload["missing_count"] > 0
    # All findings should mark surface_exists=False
    assert all(not f["details"]["surface_exists"] for f in payload["findings"])


def test_bilateral_full_coverage_yields_zero(tmp_path: Path) -> None:
    _seed_full_coverage(tmp_path)
    cp = _run(tmp_path)
    payload = json.loads(cp.stdout)
    assert payload["missing_count"] == 0
    assert payload["coverage_pct"] == 100.0
    assert payload["findings"] == []


def test_falsification_one_token_removed(tmp_path: Path) -> None:
    """Bilateral: drop one token from one surface, expect exactly 1 finding."""
    _seed_full_coverage(tmp_path)
    # Strip "cos-adr-close" from operations.md
    target = tmp_path / "docs/00-MOCs/operations.md"
    target.write_text(target.read_text().replace("cos-adr-close", "REDACTED"))
    cp = _run(tmp_path)
    payload = json.loads(cp.stdout)
    assert payload["missing_count"] == 1
    finding = payload["findings"][0]
    assert finding["details"]["primitive"] == "cos-adr-close"
    assert finding["details"]["surface"] == "docs/00-MOCs/operations.md"


def test_falsification_strict_exits_2(tmp_path: Path) -> None:
    """--strict on empty project (everything missing) -> exit 2."""
    cp = _run(tmp_path, "--strict")
    assert cp.returncode == 2


def test_strict_passes_on_full_coverage(tmp_path: Path) -> None:
    _seed_full_coverage(tmp_path)
    cp = _run(tmp_path, "--strict")
    assert cp.returncode == 0


def test_findings_have_control_plane_shape(tmp_path: Path) -> None:
    """Findings must carry the runner shape: severity/code/message/details/stable_id."""
    cp = _run(tmp_path)
    payload = json.loads(cp.stdout)
    for f in payload["findings"][:3]:
        assert f["severity"] in {"warn", "block"}
        assert f["code"] == "missing-cross-reference"
        assert "message" in f
        assert "details" in f
        assert f["stable_id"].startswith("adr-275/doc-xref/")
        assert f.get("adr") == "ADR-275"

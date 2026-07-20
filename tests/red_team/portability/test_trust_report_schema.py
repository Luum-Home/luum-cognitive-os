# SCOPE: os-only
"""Portability proof for cos_lib/trust_report_schema.py.

Pins that the ADR-038 ``TrustReport`` Pydantic model and ``build_trust_report``
factory import and validate a real report from an arbitrary working directory
and in a subprocess with no repo-relative filesystem access at all — the
module is pure in-memory validation logic (score/status banding), so a
consumer project can use it without any dependency on the Cognitive OS
source repo tree.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/trust_report_schema.py"


def test_trust_report_schema_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_trust_report_schema", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_build_trust_report_validates_from_arbitrary_consumer_project(tmp_path: Path) -> None:
    """Falsification probe: build and reject reports in a subprocess run from
    an arbitrary cwd with no filesystem access to the module beyond the
    import path — proves the schema has zero dependency on the OS repo tree.
    """
    consumer_cwd = tmp_path / "consumer_project"
    consumer_cwd.mkdir()

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from cos_lib.trust_report_schema import build_trust_report, score_to_status\n"
        "report = build_trust_report(\n"
        "    score=82,\n"
        "    verified=['tests pass', 'lint clean'],\n"
        "    unsure=['coverage not measured'],\n"
        "    human_should_check=['run integration tests'],\n"
        ")\n"
        "assert report.status == 'MEDIUM'\n"
        "assert report.evidence_count == 2\n"
        "assert report.uncertainty_count == 1\n"
        "assert score_to_status(95) == 'HIGH'\n"
        "assert 'TRUST_REPORT: SCORE=82 STATUS=MEDIUM' in report.header_line()\n"
        "print('TRUST_REPORT_OK')\n"
    ) % (str(REPO_ROOT),)

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=consumer_cwd,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "TRUST_REPORT_OK" in result.stdout, result.stdout + result.stderr


def test_band_mismatch_is_rejected_at_construction(monkeypatch, tmp_path: Path) -> None:
    """Falsification probe: a wrong status for the score band must raise,
    from an arbitrary cwd, without any repo-relative I/O.
    """
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    from cos_lib.trust_report_schema import TrustReport  # noqa: E402
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TrustReport(
            score=95,
            status="LOW",
            evidence_count=1,
            uncertainty_count=1,
            verified=["x"],
            unsure=["y"],
            human_should_check=[],
        )

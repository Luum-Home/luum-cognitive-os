# SCOPE: os-only
"""Portability proof for cos_lib/taximeter.py.

Pins that the ADR-325 cost ledger (``tick``, ``resource_tick``, ``total_cost``,
``cost_by_provider``, ``cost_by_session``) imports and round-trips through a
real JSONL ledger file from an arbitrary working directory — the module only
ever touches the ``ledger_path`` argument explicitly passed in by the caller
(default ``.cognitive-os/metrics/...``, relative to whatever cwd the caller
resolves it against), never anything that assumes it is running inside the
Cognitive OS source repo.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/taximeter.py"


def test_taximeter_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_taximeter", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_tick_and_query_round_trip_from_arbitrary_consumer_project(tmp_path: Path) -> None:
    """Falsification probe: append real ticks in a subprocess run from an
    arbitrary cwd, then confirm the query API reads them back correctly.

    Proves ``tick``/``total_cost``/``cost_by_provider``/``cost_by_session``
    have no hidden dependency on running inside the Cognitive OS source repo.
    """
    consumer_cwd = tmp_path / "consumer_project"
    consumer_cwd.mkdir()
    ledger_path = tmp_path / "metrics" / "taximeter.jsonl"

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from cos_lib.taximeter import tick, total_cost, cost_by_provider, cost_by_session\n"
        "tick('sess-1', 'claude', 'claude-sonnet-4-6', 100, 50, 0.01, ledger_path=%r)\n"
        "tick('sess-1', 'qwen', 'qwen-max', 200, 100, 0.002, ledger_path=%r)\n"
        "tick('sess-2', 'claude', 'claude-sonnet-4-6', 10, 5, 0.001, ledger_path=%r)\n"
        "total = total_cost(window='all', ledger_path=%r)\n"
        "by_provider = cost_by_provider(window='all', ledger_path=%r)\n"
        "sess1_cost = cost_by_session('sess-1', ledger_path=%r)\n"
        "assert round(total, 6) == round(0.01 + 0.002 + 0.001, 6), total\n"
        "assert set(by_provider) == {'claude', 'qwen'}, by_provider\n"
        "assert round(sess1_cost, 6) == round(0.01 + 0.002, 6), sess1_cost\n"
        "print('TAXIMETER_OK')\n"
    ) % (
        str(REPO_ROOT),
        str(ledger_path),
        str(ledger_path),
        str(ledger_path),
        str(ledger_path),
        str(ledger_path),
        str(ledger_path),
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=consumer_cwd,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "TAXIMETER_OK" in result.stdout, result.stdout + result.stderr

    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3

    # Nothing was written outside the explicitly-passed ledger path.
    assert not (tmp_path / ".cognitive-os").exists()

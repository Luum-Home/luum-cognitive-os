# SCOPE: os-only
"""El join entre "esta guarda nunca bloqueó" y "este test la hace bloquear".

QUÉ SE FIJA ACÁ, Y POR QUÉ CADA ASERCIÓN

    El join baja el bucket `unproven-guard` leyendo tests que ya existen. Su
    verde barato es obvio y está nombrado en `rules/gates-sin-trampa`: aceptar
    cualquier test que asierta `returncode == 2`. El contraejemplo es del propio
    repo — `adversarial-review-gate` tenía test verde con un dict escrito a mano
    que traía `.tool_result`, mientras el harness mandaba `.tool_response` y la
    guarda estaba ciega 186 invocaciones seguidas.

    Por eso la mitad de estos tests fija lo que el join tiene que NEGARSE a
    contar. Un join que sólo supiera contar sería indistinguible de mover el
    baseline.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from cos_lib.hook_firing_evidence import (  # noqa: E402
    firing_evidence_census,
    scan_firing_tests,
)

HANDWRITTEN_TEST = '''
import subprocess

def test_guard_blocks():
    payload = {"tool_name": "Bash", "tool_result": {"stdout": "secret"}}
    result = subprocess.run(["bash", "hooks/demo-guard.sh"], input=str(payload),
                            capture_output=True, text=True)
    assert result.returncode == 2
'''

CORPUS_TEST = '''
import json, subprocess
from pathlib import Path

CORPUS = Path("tests/fixtures/payload-corpus/harness-payloads.jsonl")

def test_guard_blocks_on_a_real_payload():
    record = json.loads(CORPUS.read_text().splitlines()[0])
    result = subprocess.run(["bash", "hooks/demo-guard.sh"],
                            input=json.dumps(record), capture_output=True, text=True)
    assert result.returncode == 2
'''

NO_ASSERTION_TEST = '''
import subprocess

def test_guard_runs():
    result = subprocess.run(["bash", "hooks/demo-guard.sh"], capture_output=True)
    assert result.returncode in (0, 2)
'''

STDERR_ONLY_TEST = '''
import subprocess

def test_guard_complains():
    result = subprocess.run(["bash", "hooks/demo-guard.sh"], capture_output=True, text=True)
    assert "BLOCKED" in result.stderr
'''


def _fixture_project(tmp_path: Path, files: dict[str, str]) -> Path:
    for rel, body in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Lo que el join tiene que NEGARSE a contar.
# ---------------------------------------------------------------------------


def test_handwritten_payload_never_proves_capacity(tmp_path: Path) -> None:
    """El caso adversarial-review-gate: test verde, producción ciega."""
    project = _fixture_project(tmp_path, {"tests/test_demo.py": HANDWRITTEN_TEST})
    evidence, _ = scan_firing_tests(project, known_hooks={"demo-guard"})

    assert "demo-guard" in evidence, "el test nombra el hook y asierta 2: debe verse"
    assert evidence["demo-guard"].payload_source == "handwritten"
    assert evidence["demo-guard"].capacity_proven is False
    assert evidence["demo-guard"].corpus_backed == ()


def test_an_assertion_that_is_not_exit_two_is_not_a_firing_test(tmp_path: Path) -> None:
    """`returncode in (0, 2)` pasa con la guarda apagada. No es prueba de nada."""
    project = _fixture_project(tmp_path, {"tests/test_demo.py": NO_ASSERTION_TEST})
    evidence, stats = scan_firing_tests(project, known_hooks={"demo-guard"})
    assert evidence == {}
    assert stats["test_files_asserting_exit_2"] == 0


def test_a_stderr_only_assertion_is_not_a_firing_test(tmp_path: Path) -> None:
    project = _fixture_project(tmp_path, {"tests/test_demo.py": STDERR_ONLY_TEST})
    evidence, _ = scan_firing_tests(project, known_hooks={"demo-guard"})
    assert evidence == {}


def test_unknown_hook_names_are_not_attributed(tmp_path: Path) -> None:
    """Sin el registro real, cualquier literal `*.sh` se leería como un hook."""
    project = _fixture_project(tmp_path, {"tests/test_demo.py": HANDWRITTEN_TEST})
    evidence, _ = scan_firing_tests(project, known_hooks={"some-other-hook"})
    assert evidence == {}


# ---------------------------------------------------------------------------
# Lo que el join SÍ cuenta.
# ---------------------------------------------------------------------------


def test_corpus_backed_payload_proves_capacity(tmp_path: Path) -> None:
    project = _fixture_project(tmp_path, {"tests/test_demo.py": CORPUS_TEST})
    evidence, _ = scan_firing_tests(project, known_hooks={"demo-guard"})

    assert evidence["demo-guard"].payload_source == "corpus"
    assert evidence["demo-guard"].capacity_proven is True


def test_the_two_kinds_of_evidence_do_not_collapse(tmp_path: Path) -> None:
    """Dos hooks, dos tests, misma aserción, distinta procedencia de payload."""
    project = _fixture_project(
        tmp_path,
        {
            "tests/test_a.py": HANDWRITTEN_TEST,
            "tests/test_b.py": CORPUS_TEST.replace("demo-guard", "real-guard"),
        },
    )
    evidence, _ = scan_firing_tests(
        project, known_hooks={"demo-guard", "real-guard"}
    )
    assert evidence["demo-guard"].capacity_proven is False
    assert evidence["real-guard"].capacity_proven is True


def test_census_declares_the_whole_population(tmp_path: Path) -> None:
    """Un conteo sin población es opinión con dígitos: `cos_lib.measurement`."""
    project = _fixture_project(
        tmp_path,
        {
            "tests/test_a.py": HANDWRITTEN_TEST,
            "tests/test_b.py": CORPUS_TEST.replace("demo-guard", "real-guard"),
        },
    )
    evidence, _ = scan_firing_tests(
        project, known_hooks={"demo-guard", "real-guard", "silent-guard"}
    )
    census = firing_evidence_census(
        ["demo-guard", "real-guard", "silent-guard"],
        evidence,
        sources=("fixture",),
        how=".venv/bin/python3 -m pytest tests/audit/test_hook_firing_evidence_join.py",
    )
    assert census.population == 3
    assert census.count("capacidad_probada_con_payload_del_corpus") == 1
    assert census.count("test_de_disparo_con_payload_inventado") == 1
    assert census.count("sin_test_de_disparo") == 1
    with pytest.raises(Exception):
        census.count("bucket_inexistente")


# ---------------------------------------------------------------------------
# El audit real: el join está cableado y no infla nada.
# ---------------------------------------------------------------------------


def _audit_report() -> dict:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "hook_vitality_audit.py"), "--json"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=300,
        check=False,
    )
    assert result.returncode in (0, 1), result.stderr[-2000:]
    return json.loads(result.stdout)


def test_audit_publishes_the_firing_evidence_census() -> None:
    report = _audit_report()
    census = report["firing_evidence"]["census"]
    assert census["population"] == report["registered_hook_scripts"]
    assert set(census["buckets"]) == {
        "capacidad_probada_con_payload_del_corpus",
        "test_de_disparo_con_payload_inventado",
        "sin_test_de_disparo",
    }


def test_no_registered_hook_is_promoted_on_a_handwritten_payload() -> None:
    """La afirmación que impide el verde barato en el árbol real: ningún hook
    llega a `capacity-proven` teniendo sólo tests con payload inventado."""
    report = _audit_report()
    for row in report["hooks"]:
        if row["bucket"] == "capacity-proven":
            assert row["firing_tests_corpus_backed"], row["hook"]
            assert row["firing_test_payload_source"] == "corpus", row["hook"]


def test_handwritten_firing_tests_exist_and_are_visibly_not_counted() -> None:
    """Si esto diera 0 el join sería inobservable: no habría nada que negarse a
    contar y el test anterior pasaría por vacuidad."""
    report = _audit_report()
    hand = [
        r for r in report["hooks"] if r["firing_test_payload_source"] == "handwritten"
    ]
    assert hand, "sin tests de disparo con payload inventado, el join no se ejerce"
    assert all(r["bucket"] != "capacity-proven" for r in hand)

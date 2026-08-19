# SCOPE: both
"""El ledger de claims tiene que distinguir trabajo, no solo sesiones.

Dos modos de falla reales, reproducidos el 2026-08-19 sobre el checkout del
operador (ver docs/06-Daily/reports/coordinacion-sesiones-concurrentes-2026-08-19.md):

A. FALSO POSITIVO — `task_fingerprint({})` colapsa a un unico hash constante
   (`ad863ddeda113b35ccb28498`) porque el hook que reclama no llena ningun
   campo de contenido. Con ese hash, dos tareas SIN relacion lanzadas desde
   dos sesiones distintas se leen como "el mismo trabajo" y la segunda queda
   bloqueada. Las 64 filas de `.cognitive-os/tasks/active-claims.json` comparten
   ese unico fingerprint.

B. FALSO NEGATIVO — el conflicto solo se evalua cuando `session_id` difiere.
   Dos sub-agentes de la MISMA sesion con el mismo trabajo y distinto task_id
   pasan los dos. Es lo que produjo los commits duplicados e0d975d91 y
   2f33c9095.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.cos_task_claims import (  # noqa: E402
    CONTENTLESS_FINGERPRINT as MODULE_CONTENTLESS_FINGERPRINT,
    claim_task,
    task_fingerprint,
)

CONTENTLESS_FINGERPRINT = "ad863ddeda113b35ccb28498"
SAME_WORK = "medir los hooks declarados que nunca llegan a un arnes"


def _task(task_id: str, description: str = "") -> dict[str, object]:
    return {"id": task_id, "description": description, "deliverable": ""}


def test_contentless_fingerprint_is_the_known_degenerate_hash() -> None:
    """El hash de una tarea sin contenido es constante: no discrimina nada."""
    assert task_fingerprint({}, []) == CONTENTLESS_FINGERPRINT
    assert MODULE_CONTENTLESS_FINGERPRINT == CONTENTLESS_FINGERPRINT
    assert task_fingerprint(_task("t-alpha"), []) == CONTENTLESS_FINGERPRINT
    assert task_fingerprint(_task("t-beta"), []) == CONTENTLESS_FINGERPRINT


def test_contentless_claims_across_sessions_do_not_block(tmp_path: Path) -> None:
    """MODO A: dos tareas sin relacion, dos sesiones -> las dos tienen que entrar."""
    ok_a, res_a = claim_task(tmp_path, _task("t-alpha"), session="sesA")
    assert ok_a, res_a
    ok_b, res_b = claim_task(tmp_path, _task("t-beta"), session="sesB")
    assert ok_b, (
        "un fingerprint vacio bloqueo trabajo no relacionado de otra sesion: "
        f"{res_b}"
    )
    # `**claim` pisa el status con "active": el flag `ok` es la señal real.
    assert res_b["task_id"] == "t-beta"


def test_same_task_id_across_sessions_still_conflicts(tmp_path: Path) -> None:
    """Regresion: el guard cross-session real sigue bloqueando (no verde barato)."""
    ok_a, _ = claim_task(tmp_path, _task("t-shared", SAME_WORK), session="sesA")
    assert ok_a
    ok_b, res_b = claim_task(tmp_path, _task("t-shared", SAME_WORK), session="sesB")
    assert not ok_b
    assert res_b["status"] == "conflict"
    assert res_b["held_by"] == "sesA"


def test_same_work_same_session_is_reported_as_duplicate(tmp_path: Path) -> None:
    """MODO B: mismo trabajo, misma sesion, task_id distinto -> se avisa."""
    ok_1, _ = claim_task(tmp_path, _task("t-1", SAME_WORK), session="default-session")
    assert ok_1
    ok_2, res_2 = claim_task(tmp_path, _task("t-2", SAME_WORK), session="default-session")
    assert ok_2, "por defecto no bloquea, avisa"
    assert res_2.get("duplicate_of") == ["t-1"], res_2
    events = (tmp_path / ".cognitive-os" / "sessions" / "events.jsonl").read_text(encoding="utf-8")
    assert "duplicate-work" in events


def test_duplicate_work_blocks_when_flag_is_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Con el flag encendido, el segundo agente con el mismo trabajo no arranca."""
    monkeypatch.setenv("COS_CLAIM_DUPLICATE_WORK_BLOCK", "1")
    ok_1, _ = claim_task(tmp_path, _task("t-1", SAME_WORK), session="default-session")
    assert ok_1
    ok_2, res_2 = claim_task(tmp_path, _task("t-2", SAME_WORK), session="default-session")
    assert not ok_2
    assert res_2["status"] == "duplicate-work"
    assert res_2["held_by_task_id"] == "t-1"


def test_distinct_work_same_session_is_not_flagged(tmp_path: Path) -> None:
    """Trabajo realmente distinto no genera ruido de duplicado."""
    ok_1, _ = claim_task(tmp_path, _task("t-1", "auditar cobertura de primitivas"), session="s1")
    ok_2, res_2 = claim_task(tmp_path, _task("t-2", "arreglar el guard de codex"), session="s1")
    assert ok_1 and ok_2
    assert "duplicate_of" not in res_2

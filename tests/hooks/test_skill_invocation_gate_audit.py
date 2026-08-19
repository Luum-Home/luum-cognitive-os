"""El gate de ADR-188 tiene que DEJAR RASTRO, no solo bloquear.

`hooks/orchestrator-skill-invocation-gate.sh` bloqueo 131 veces en este repo y
`.cognitive-os/metrics/skill-bypass.jsonl` nunca existio: `_emit_audit` solo se
llamaba en las ramas anotada y env-override, jamas en la rama que efectivamente
cuenta y bloquea. Consecuencia medida: `scripts/skill_adherence_loop.py`
reportaba `BYPASSED: 0` — un cero que no significaba "nadie bypasseo" sino "el
productor del log nunca escribio".

Esta suite corre el hook REAL contra un `COGNITIVE_OS_PROJECT_DIR` temporal y
despues le pasa el log producido al consumidor REAL. No hay fixtures de fila
escritas a mano en el camino critico: la fila la escribe el hook.

La asercion que cierra el lazo de punta a punta es la tercera:
`skill_adherence_loop.py` tiene que clasificar la sugerencia como ``BYPASSED``,
no como ``UNTRACED`` ni como ``UNMEASURABLE``. Sin ella el test probaria que se
escribio un archivo, no que el instrumento lo ve.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "hooks" / "orchestrator-skill-invocation-gate.sh"
LOOP = REPO / "scripts" / "skill_adherence_loop.py"

SESSION = "gate-audit-probe"
SKILL = "run-tests"
PROMPT_HASH = "0badc0de0badc0de"
CONFIDENCE = 0.95

# Campos que consume load_bypasses() en scripts/skill_adherence_loop.py.
# `reason` no vacio es lo que hace `audited=True`; sin eso la fila existe pero el
# consumidor no la aparea y el veredicto no cambia.
CONSUMER_FIELDS = ("ts", "suggested_skill", "reason", "prompt_hash")


def _project(tmp_path: Path) -> tuple[Path, Path]:
    """Arma un PROJECT_DIR sintetico. Devuelve (metrics_dir, events_file)."""
    metrics = tmp_path / ".cognitive-os" / "metrics"
    sessions = tmp_path / ".cognitive-os" / "sessions"
    metrics.mkdir(parents=True)
    sessions.mkdir(parents=True)

    ts = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
    (metrics / "skill-suggestion.jsonl").write_text(
        json.dumps(
            {
                "ts": ts,
                "session_id": SESSION,
                "prompt_hash": PROMPT_HASH,
                "skill_name": SKILL,
                "invoke_command": f"/{SKILL}",
                "confidence": CONFIDENCE,
                "threshold_met": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    # Logger de invocaciones vivo pero sin filas: obliga a que el unico camino a
    # BYPASSED sea la fila que escribe el gate.
    (metrics / "skill-invocations.jsonl").write_text("", encoding="utf-8")
    events = sessions / "events.jsonl"
    events.write_text("", encoding="utf-8")
    return metrics, events


def _run_hook(project_dir: Path, command: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
            "COGNITIVE_OS_SESSION_ID": SESSION,
            "DISABLE_HOOK_ORCHESTRATOR_SKILL_INVOCATION_GATE": "0",
        }
    )
    env.pop("COS_ALLOW_SKILL_BYPASS", None)
    payload = {
        "tool_name": "Bash",
        "session_id": SESSION,
        "tool_input": {"command": command, "description": "probe"},
    }
    return subprocess.run(
        ["/bin/bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        cwd=str(REPO),
        timeout=60,
        check=False,
    )


def _rows(metrics: Path) -> list[dict]:
    path = metrics / "skill-bypass.jsonl"
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _loop(metrics: Path, events: Path) -> tuple[int, dict]:
    proc = subprocess.run(
        [
            os.environ.get("COS_TEST_PYTHON", str(REPO / ".venv" / "bin" / "python3")),
            str(LOOP),
            "--metrics-dir",
            str(metrics),
            "--events-file",
            str(events),
            "--json",
        ],
        text=True,
        capture_output=True,
        cwd=str(REPO),
        timeout=90,
        check=False,
    )
    assert proc.stdout.strip(), f"el consumidor no emitio JSON: {proc.stderr}"
    return proc.returncode, json.loads(proc.stdout)


# --------------------------------------------------------------------------- #
# 1. Un bypass escribe una fila
# --------------------------------------------------------------------------- #
def test_unannotated_bypass_writes_an_audit_row(tmp_path: Path) -> None:
    metrics, _ = _project(tmp_path)

    proc = _run_hook(tmp_path, "echo hola")

    assert proc.returncode == 0, f"primer aviso no deberia bloquear: {proc.stderr}"
    assert "WARN" in proc.stderr, proc.stderr

    rows = _rows(metrics)
    assert rows, (
        "el gate evaluo, aviso y no escribio nada en skill-bypass.jsonl: una "
        "guarda que evalua y no emite es indistinguible de una guarda rota"
    )
    assert len(rows) == 1, rows


# --------------------------------------------------------------------------- #
# 2. La fila tiene los campos que consume skill_adherence_loop.py
# --------------------------------------------------------------------------- #
def test_audit_row_carries_the_consumer_contract(tmp_path: Path) -> None:
    metrics, _ = _project(tmp_path)
    _run_hook(tmp_path, "echo hola")

    rows = _rows(metrics)
    assert rows, "sin fila no hay contrato que verificar"
    row = rows[0]

    for field in CONSUMER_FIELDS:
        assert field in row, f"falta el campo {field!r} que consume load_bypasses()"

    assert row["suggested_skill"] == SKILL
    assert row["prompt_hash"] == PROMPT_HASH
    assert row["session_id"] == SESSION
    assert row["confidence"] == pytest.approx(CONFIDENCE)
    assert row["outcome"] == "bypass-unannotated"
    assert row["reason"].strip(), (
        "reason vacio => audited=False en load_bypasses() => la fila existe pero "
        "el consumidor no la aparea y el hueco sigue invisible"
    )
    # ts parseable por parse_ts() del consumidor.
    datetime.fromisoformat(row["ts"].replace("Z", "+00:00"))


# --------------------------------------------------------------------------- #
# 3. El consumidor la clasifica BYPASSED — cierre de punta a punta
# --------------------------------------------------------------------------- #
def test_consumer_classifies_the_row_as_bypassed(tmp_path: Path) -> None:
    metrics, events = _project(tmp_path)

    # Control: sin correr el gate, la sugerencia no es medible (logger mudo).
    _, before = _loop(metrics, events)
    assert before["result"]["totals"]["BYPASSED"] == 0
    assert before["result"]["totals"]["UNMEASURABLE"] == 1

    _run_hook(tmp_path, "echo hola")

    code, after = _loop(metrics, events)
    totals = after["result"]["totals"]
    assert totals["BYPASSED"] == 1, (
        f"el instrumento no ve la fila que escribio el gate: {totals}"
    )
    assert totals["UNTRACED"] == 0, totals
    assert totals["UNMEASURABLE"] == 0, totals
    assert after["sources"]["bypasses"]["exists"] is True
    assert code == 0, "una sugerencia con bypass auditado no es hallazgo"


# --------------------------------------------------------------------------- #
# 4. El BLOQUEO tambien deja rastro (es el caso que perdio 131 filas)
# --------------------------------------------------------------------------- #
def test_block_also_writes_its_row(tmp_path: Path) -> None:
    metrics, _ = _project(tmp_path)

    codes = [_run_hook(tmp_path, "echo hola").returncode for _ in range(3)]

    assert codes == [0, 0, 2], codes
    rows = _rows(metrics)
    assert len(rows) == 3, f"tres decisiones, tres filas; hay {len(rows)}"
    assert rows[-1]["outcome"] == "blocked"
    assert rows[-1]["reason"].strip()


# --------------------------------------------------------------------------- #
# 5. El caso positivo emite, pero NO se puede leer como bypass
# --------------------------------------------------------------------------- #
def test_invoked_emits_a_pass_row_that_is_not_counted_as_bypass(
    tmp_path: Path,
) -> None:
    metrics, events = _project(tmp_path)

    proc = _run_hook(tmp_path, f"/{SKILL} --quick")
    assert proc.returncode == 0, proc.stderr

    rows = _rows(metrics)
    assert len(rows) == 1, f"la rama positiva tampoco puede ser muda: {rows}"
    assert rows[0]["outcome"] == "invoked"
    assert rows[0]["reason"] == "", (
        "un pass con razon escrita se apearia como bypass e inflaria la "
        "adherencia: la razon vacia es lo que lo mantiene inocuo"
    )

    _, report = _loop(metrics, events)
    totals = report["result"]["totals"]
    assert totals["BYPASSED"] == 0, f"un pass no es un bypass: {totals}"


def test_pass_rows_are_deduplicated_per_prompt(tmp_path: Path) -> None:
    metrics, _ = _project(tmp_path)

    for _ in range(4):
        _run_hook(tmp_path, f"/{SKILL} --quick")

    rows = _rows(metrics)
    assert len(rows) == 1, (
        f"una decision por prompt, no una por tool call: {len(rows)} filas"
    )

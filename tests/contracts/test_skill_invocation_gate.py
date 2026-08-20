"""Contract tests for ADR-188: orchestrator-skill-invocation-gate.

Covers all five acceptance scenarios from the ADR.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]
# COS_SKILL_GATE_HOOK apunta el contrato a una COPIA mutada del hook. Lo usa
# scripts/mutation_check_skill_gate.py para probar que estos tests MATAN, y no
# solo cuentan.
HOOK = Path(os.environ.get("COS_SKILL_GATE_HOOK") or (REPO_ROOT / "hooks" / "orchestrator-skill-invocation-gate.sh"))


def _seed_suggestion(
    workdir: Path,
    *,
    session_id: str,
    skill: str,
    confidence: float,
    age_seconds: float = 0.0,
) -> str:
    """Write a skill-suggestion.jsonl entry and return the prompt_hash.

    2026-08-20 — la fecha dejo de ser una constante. Estos seeds decian
    `2026-05-06` y funcionaban porque el consumidor trataba TODO el log como
    vigente: ese era justamente el bug (una sugerencia de julio se exigio
    durante 48 dias). Con la ventana del turno + TTL, una fila sembrada en el
    pasado ya no obliga, asi que los casos que esperan enforcement siembran en
    el presente y `age_seconds` queda para probar lo contrario a proposito.
    """
    metrics = workdir / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=age_seconds)
    entry = {
        "ts": stamp.isoformat(),
        "session_id": session_id,
        "prompt_hash": "deadbeefcafebabe",
        "skill_name": skill,
        "invoke_command": f"/{skill}",
        "confidence": confidence,
        "threshold_met": confidence >= 0.80,
    }
    with (metrics / "skill-suggestion.jsonl").open("a") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry["prompt_hash"]


def _run_hook(workdir: Path, *, tool_name: str, tool_input: dict, env_extra=None) -> subprocess.CompletedProcess:
    payload = {"tool_name": tool_name, "tool_input": tool_input, "session_id": "test-session-188"}
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(workdir)
    env["CLAUDE_PROJECT_DIR"] = str(workdir)
    env["COGNITIVE_OS_SESSION_ID"] = "test-session-188"
    # Disable any inherited overrides
    env.pop("COS_ALLOW_SKILL_BYPASS", None)
    # Higiene de entorno heredado: el conftest de la raiz redirige COS_METRICS_DIR
    # a un sandbox para toda la suite. Este test mide el destino POR DEFECTO
    # (derivado de PROJECT_DIR), asi que descarta el redirect igual que ya
    # descarta COS_ALLOW_SKILL_BYPASS.
    env.pop("COS_METRICS_DIR", None)
    env.pop("COGNITIVE_OS_METRICS_DIR", None)
    env.pop("COS_SKILL_BYPASS_REASON", None)
    env.pop("DISABLE_HOOK_ORCHESTRATOR_SKILL_INVOCATION_GATE", None)
    env.pop("COS_SKILL_SUGGESTION_TTL_SECONDS", None)
    env.pop("COS_SKILL_GATE_INSIST_THRESHOLD", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
    )


@pytest.fixture
def workdir(tmp_path: Path):
    # Provide a project-shaped tmp dir with a symlink to the real lib/skill_router
    (tmp_path / "cos_lib").mkdir()
    real_router = REPO_ROOT / "cos_lib" / "skill_router.py"
    shutil.copy(real_router, tmp_path / "cos_lib" / "skill_router.py")
    # Empty __init__ so `from cos_lib.skill_router import ...` works
    (tmp_path / "cos_lib" / "__init__.py").write_text("")
    return tmp_path


def test_high_confidence_skill_invoked_passes(workdir: Path):
    _seed_suggestion(workdir, session_id="test-session-188", skill="repo-scout", confidence=0.95)
    # tool_input.prompt loads the skill explicitly
    res = _run_hook(
        workdir,
        tool_name="Agent",
        tool_input={"prompt": "Load skills/repo-scout/SKILL.md and proceed", "description": "x"},
    )
    assert res.returncode == 0, res.stderr
    # No counter file should be created (PASS)
    counter = workdir / ".cognitive-os" / "runtime" / "skill-bypass-counter-test-session-188"
    assert not counter.exists()


def test_high_confidence_bypass_annotation_passes_and_audits(workdir: Path):
    _seed_suggestion(workdir, session_id="test-session-188", skill="repo-scout", confidence=0.95)
    res = _run_hook(
        workdir,
        tool_name="Agent",
        tool_input={
            "prompt": "SKILL_BYPASS: repo-scout confidence=0.95 reason=already-evaluated\nProceed with bespoke task.",
            "description": "x",
        },
    )
    assert res.returncode == 0, res.stderr
    audit = workdir / ".cognitive-os" / "metrics" / "skill-bypass.jsonl"
    assert audit.exists()
    lines = [json.loads(l) for l in audit.read_text().splitlines() if l.strip()]
    assert len(lines) == 1
    assert lines[0]["suggested_skill"] == "repo-scout"
    assert lines[0]["actor"] == "orchestrator-annotation"
    assert lines[0]["confidence"] == 0.95


def test_high_confidence_bespoke_warns_then_blocks_after_three(workdir: Path):
    """Tres ENVIOS del mismo prompt, no tres tool calls.

    2026-08-20 — cambio la unidad. Antes este test lanzaba tres herramientas
    dentro de un mismo turno y esperaba BLOCK, porque el contador sumaba +1 por
    tool call de por vida: en produccion eso llego a 143 contra un umbral de 3,
    latcheado desde el 2026-05-18 y sin ningun camino de reset. Eso no medía
    insistencia, medía antiguedad. Ahora el contador avanza por ENVIO del mismo
    prompt_hash, asi que cada repeticion siembra su propia fila de sugerencia.
    """
    for i, (expect_rc, marker) in enumerate([(0, "1/3"), (0, "2/3"), (2, "BLOCK")]):
        _seed_suggestion(
            workdir, session_id="test-session-188", skill="repo-scout",
            confidence=0.95, age_seconds=-i,  # cada envio, un ts distinto
        )
        res = _run_hook(workdir, tool_name="Agent", tool_input={"prompt": f"bespoke {i}"})
        assert res.returncode == expect_rc, res.stderr
        assert marker in res.stderr, res.stderr


def test_low_confidence_no_enforcement(workdir: Path):
    _seed_suggestion(workdir, session_id="test-session-188", skill="repo-scout", confidence=0.70)
    res = _run_hook(workdir, tool_name="Agent", tool_input={"prompt": "do bespoke thing"})
    assert res.returncode == 0
    # No counter, no audit
    counter = workdir / ".cognitive-os" / "runtime" / "skill-bypass-counter-test-session-188"
    assert not counter.exists()
    audit = workdir / ".cognitive-os" / "metrics" / "skill-bypass.jsonl"
    assert not audit.exists()
    # No WARN emitted
    assert "WARN" not in res.stderr


def test_env_override_with_reason_passes_and_audits(workdir: Path):
    _seed_suggestion(workdir, session_id="test-session-188", skill="repo-scout", confidence=0.95)
    res = _run_hook(
        workdir,
        tool_name="Agent",
        tool_input={"prompt": "do bespoke"},
        env_extra={"COS_ALLOW_SKILL_BYPASS": "1", "COS_SKILL_BYPASS_REASON": "broken-skill-test"},
    )
    assert res.returncode == 0, res.stderr
    audit = workdir / ".cognitive-os" / "metrics" / "skill-bypass.jsonl"
    assert audit.exists()
    rec = json.loads(audit.read_text().splitlines()[-1])
    assert rec["actor"] == "env-override"
    assert "broken-skill-test" in rec["reason"]


def test_env_override_without_reason_blocks(workdir: Path):
    _seed_suggestion(workdir, session_id="test-session-188", skill="repo-scout", confidence=0.95)
    res = _run_hook(
        workdir,
        tool_name="Agent",
        tool_input={"prompt": "do bespoke"},
        env_extra={"COS_ALLOW_SKILL_BYPASS": "1"},
    )
    assert res.returncode == 2
    assert "COS_SKILL_BYPASS_REASON" in res.stderr


def test_killswitch_disables_hook(workdir: Path):
    _seed_suggestion(workdir, session_id="test-session-188", skill="repo-scout", confidence=0.95)
    res = _run_hook(
        workdir,
        tool_name="Agent",
        tool_input={"prompt": "do bespoke"},
        env_extra={"DISABLE_HOOK_ORCHESTRATOR_SKILL_INVOCATION_GATE": "1"},
    )
    assert res.returncode == 0
    assert "WARN" not in res.stderr


def test_last_suggestion_returns_highest_confidence_for_session():
    """Unit-style coverage of cos_lib.skill_router.last_suggestion().

    2026-08-20 — este test existia y no probaba nada de lo que fallaba: usaba
    marcas de mayo, no ejecutaba el hook y no cubria ni la identidad sentinela
    ni la ventana. Se le agregan las tres aserciones que si discriminan.
    """
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from cos_lib.skill_router import last_suggestion  # noqa

    # Use an isolated tmp project to avoid colliding with real metrics.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        m = tdp / ".cognitive-os" / "metrics"
        m.mkdir(parents=True)
        s = tdp / ".cognitive-os" / "sessions"
        s.mkdir(parents=True)
        now = dt.datetime.now(dt.timezone.utc)

        def _row(skill, conf, session, minutes_ago, ph):
            return json.dumps({
                "ts": (now - dt.timedelta(minutes=minutes_ago)).isoformat(),
                "session_id": session, "prompt_hash": ph, "skill_name": skill,
                "confidence": conf, "threshold_met": True,
            }) + "\n"

        with (m / "skill-suggestion.jsonl").open("w") as fh:
            # Turno actual: dos filas, gana la de mas confianza.
            fh.write(_row("a", 0.85, "S", 0, "h1"))
            fh.write(_row("b", 0.95, "S", 0, "h2"))
            # La trampa medida en produccion: una fila vieja con MAS confianza.
            fh.write(_row("vieja", 0.99, "S", 60 * 24 * 40, "h-vieja"))
            # Las 584 filas historicas sin identidad, en sus dos formas.
            fh.write(_row("anon-null", 0.99, None, 0, "h-anon"))
            fh.write(_row("anon-unknown", 0.99, "unknown", 0, "h-unk"))

        out = last_suggestion("S", project_root=tdp)
        assert out is not None
        assert out["skill"] == "b", "gana la mas confiable DEL TURNO, no del log"
        assert out["confidence"] == 0.95

        # Different session -> None
        assert last_suggestion("OTHER", project_root=tdp) is None

        # Una identidad sentinela no es una identidad: preguntar por `unknown`
        # no puede devolver la sugerencia de nadie. Esta era la clave que
        # compartian las 584 filas del log real.
        for sentinela in ("unknown", "UNKNOWN", "none", "null", "", "  "):
            assert last_suggestion(sentinela, project_root=tdp) is None, sentinela

        # Y con el log entero vencido, no hay sugerencia vigente.
        with (m / "skill-suggestion.jsonl").open("w") as fh:
            fh.write(_row("vieja", 0.99, "S", 60 * 24 * 40, "h-vieja"))
        assert last_suggestion("S", project_root=tdp) is None

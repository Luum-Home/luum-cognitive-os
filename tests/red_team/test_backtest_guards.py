# SCOPE: os-only
"""Prueba pareada de scripts/backtest_guards.py — el instrumento, no los guards.

Un backtest que nunca puede reportar rojo tiene el mismo defecto que los guards
que vino a medir: da sensacion de cobertura. Asi que lo que se prueba aca no es
si tal guard bloquea (eso lo dice el script), sino que el script **puede decir
las dos cosas** y que no colapsa el tercer estado.

Cada test corre codigo: hooks sinteticos de verdad, por subprocess, con el mismo
runner que usa el script.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from scripts.backtest_guards import (  # noqa: E402
    BLOQUEA,
    CASES,
    NO_BLOQUEA,
    NO_PROBADO,
    Case,
    Run,
    make_sandbox,
    run_case,
    run_hook,
    verdict,
)


def _hook(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text("#!/usr/bin/env bash\n" + body)
    p.chmod(p.stat().st_mode | stat.S_IXUSR)
    return p


# ─────────────────────────────────────────────────────────────────────────────
# El runner distingue rojo de verde
# ─────────────────────────────────────────────────────────────────────────────
def test_runner_sees_exit_2_as_a_block(tmp_path):
    h = _hook(tmp_path, "blocker.sh", 'cat >/dev/null; echo "nope" >&2; exit 2\n')
    sb = make_sandbox(tmp_path / "sb", None)
    r = run_hook(h, "{}", sb)
    assert r.exit_code == 2
    assert r.blocked is True


def test_runner_sees_exit_0_as_a_pass(tmp_path):
    h = _hook(tmp_path, "passer.sh", "cat >/dev/null; exit 0\n")
    sb = make_sandbox(tmp_path / "sb", None)
    r = run_hook(h, "{}", sb)
    assert r.exit_code == 0
    assert r.blocked is False


def test_runner_sees_permission_deny_json_as_a_block(tmp_path):
    """El arnes acepta tres formas de decir que no; mirar solo el exit code
    dejaria pasar por verde a un hook que denego via JSON."""
    h = _hook(tmp_path, "denier.sh",
              'cat >/dev/null; echo \'{"hookSpecificOutput":'
              '{"permissionDecision":"deny"}}\'; exit 0\n')
    sb = make_sandbox(tmp_path / "sb", None)
    r = run_hook(h, "{}", sb)
    assert r.exit_code == 0
    assert r.blocked is True


# ─────────────────────────────────────────────────────────────────────────────
# El tercer estado no se colapsa en el segundo
# ─────────────────────────────────────────────────────────────────────────────
def test_identical_branches_are_not_proven_rather_than_passing():
    """Positiva y negativa iguales -> NO_PROBADO, jamas NO_BLOQUEA.

    Es el defecto central: con las dos ramas indistinguibles no se puede separar
    'el guard es inerte' de 'el payload positivo no lo desperto'.
    """
    same = Run(0, "", "identical output")
    state, reason = verdict(same, Run(0, "", "identical output"), None, "")
    assert state == NO_PROBADO
    assert "no discrimina" in reason


def test_discriminating_but_non_blocking_is_a_proven_finding():
    pos = Run(0, "", "SCOPE CREEP: WARNING file out of scope")
    neg = Run(0, "", "")
    state, _ = verdict(pos, neg, None, "")
    assert state == NO_BLOQUEA


def test_blocking_only_the_positive_branch_is_the_only_pass():
    state, _ = verdict(Run(2, "", "blocked"), Run(0, "", ""), None, "")
    assert state == BLOQUEA


def test_blocking_both_branches_is_not_coverage():
    """Un guard que bloquea todo no probo que vea el input que vino a frenar."""
    state, reason = verdict(Run(2, "", "blocked"), Run(2, "", "blocked"), None, "")
    assert state == NO_PROBADO
    assert "las DOS" in reason


def test_inverted_polarity_is_reported_not_swallowed():
    """Bloquear lo inocuo y dejar pasar lo peligroso es un hallazgo, no un pase."""
    state, reason = verdict(Run(0, "", ""), Run(2, "", "blocked"), None, "")
    assert state == NO_PROBADO
    assert "INVERTIDA" in reason


def test_a_branch_that_failed_to_run_is_not_a_pass():
    state, _ = verdict(Run(-1, "", "", error="timeout tras 90s"), Run(0, "", ""), None, "")
    assert state == NO_PROBADO


# ─────────────────────────────────────────────────────────────────────────────
# La huella no puede volverse un si-a-todo
# ─────────────────────────────────────────────────────────────────────────────
def test_fingerprint_ignores_timestamps_uuids_and_tmpdirs():
    """Sin normalizar, dos corridas identicas difieren por el reloj y todo caso
    pareceria discriminar: la sonda diria 'NO_BLOQUEA' sobre guards que ni se
    enteraron del input."""
    a = Run(0, "", "run 2026-08-21T10:00:00Z id 3f2504e0-4f89-11d3-9a0c-0305e82c3301 in /tmp/x1")
    b = Run(0, "", "run 2026-08-21T23:59:59Z id 9f2504e0-4f89-11d3-9a0c-0305e82c3399 in /tmp/x2")
    assert a.fingerprint == b.fingerprint


def test_fingerprint_keeps_a_real_difference():
    a = Run(0, "", "SCOPE CREEP: WARNING")
    b = Run(0, "", "")
    assert a.fingerprint != b.fingerprint


# ─────────────────────────────────────────────────────────────────────────────
# Seguridad: los guards mutantes no se corren
# ─────────────────────────────────────────────────────────────────────────────
def test_a_mutating_gate_is_never_executed(tmp_path):
    """El hook deja un centinela si corre. Tiene que no existir."""
    sentinel = tmp_path / "IT-RAN"
    h = _hook(tmp_path, "mutator.sh", f'touch "{sentinel}"\nexit 0\n')
    # hook_path absoluto: Path("/hooks") / "/tmp/x" devuelve "/tmp/x", asi que
    # Case.path() apunta al hook sintetico sin depender del tmpdir.
    case = Case(gate="mutator", event="PreToolUse",
                why="guard sintetico con efecto irreversible",
                mutating="escribe fuera del sandbox",
                hook_path=str(h))
    assert case.path() == h
    res = run_case(case, tmp_path / "work", "reconstruction")
    assert res["state"] == NO_PROBADO
    assert "PROHIBIDO CORRERLO" in res["reason"]
    assert not sentinel.exists(), "el backtest ejecuto un guard marcado mutante"


def test_the_two_known_mutating_gates_stay_declared():
    """Si alguien les saca el motivo, el backtest empezaria a commitear y a
    reescribir settings.json en la proxima corrida."""
    declared = {c.gate for c in CASES if c.mutating}
    assert {"engram-auto-sync", "self-install"} <= declared


# ─────────────────────────────────────────────────────────────────────────────
# El sandbox aisla
# ─────────────────────────────────────────────────────────────────────────────
def test_sandbox_is_its_own_git_repo_on_main_not_the_operators(tmp_path):
    """Sin git propio, direct-main-guard sale por su fallback y un guard vivo
    se reporta como NO_PROBADO. Y si fuera el .git real, un guard que commitea
    tocaria el repo del operador."""
    sb = make_sandbox(tmp_path / "sb", None)
    assert (sb / ".git").is_dir()
    assert not (sb / ".git").is_symlink()
    branch = subprocess.run(["git", "-C", str(sb), "rev-parse", "--abbrev-ref", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    assert branch == "main"
    top = subprocess.run(["git", "-C", str(sb), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True).stdout.strip()
    assert Path(top).resolve() != REPO.resolve()


def test_sandbox_never_links_dot_claude_or_dot_git_from_the_repo(tmp_path):
    sb = make_sandbox(tmp_path / "sb", None)
    assert not (sb / ".claude").exists(), (
        "un sandbox con .claude enlazado deja que self-install reescriba "
        "settings.json del repo real")


def test_counterfactual_sandbox_actually_flips_the_phase(tmp_path):
    """La rama contrafactica es la que separa 'codigo inerte' de 'fase lo
    degrada'. Si la fase no cambia, esa distincion es decorativa."""
    import re
    sb = make_sandbox(tmp_path / "prod", "production")
    text = (sb / "cognitive-os.yaml").read_text()
    assert re.search(r"^\s*phase:\s*production", text, re.M)


# ─────────────────────────────────────────────────────────────────────────────
# Un guard que se apaga bajo test
# ─────────────────────────────────────────────────────────────────────────────
def _prod_env() -> dict:
    """El env del arnes real: sin el marcador que pone pytest.

    Ver el test de abajo. Correr el backtest heredando PYTEST_CURRENT_TEST mide
    un guard apagado y lo reporta como si el arnes lo dejara pasar.
    """
    e = dict(os.environ)
    e.pop("PYTEST_CURRENT_TEST", None)
    return e


def test_destructive_git_blocker_self_disables_under_pytest(tmp_path):
    """Caracteriza un verde barato ya presente en un guard `live`.

    Con PYTEST_CURRENT_TEST puesto, `git reset --hard HEAD~5` pasa. Cualquier
    test que corra este guard en proceso obtiene un verde que el arnes real no
    da. No se arregla aca; se deja medido para que no vuelva a pasar inadvertido
    y para que el backtest no lo herede.
    """
    hook = REPO / "hooks" / "destructive-git-blocker.sh"
    if not hook.exists():
        pytest.skip("destructive-git-blocker.sh no esta en este checkout")
    sb = make_sandbox(tmp_path / "sb", None)
    stdin = json.dumps({"session_id": "t", "transcript_path": "/dev/null",
                        "cwd": str(sb), "hook_event_name": "PreToolUse",
                        "tool_name": "Bash",
                        "tool_input": {"command": "git reset --hard HEAD~5"}})
    # payload-synthetic: el punto del test es el ENV, no la forma del payload.

    blocked_prod = run_hook(hook, stdin, sb).blocked

    p = subprocess.run([str(hook)], input=stdin, capture_output=True, text=True,
                       timeout=120, cwd=str(REPO),
                       env=dict(os.environ,
                                COGNITIVE_OS_PROJECT_DIR=str(sb),
                                CLAUDE_PROJECT_DIR=str(sb),
                                COS_METRICS_DIR=str(sb / ".cognitive-os/metrics"),
                                COGNITIVE_OS_METRICS_DIR=str(sb / ".cognitive-os/metrics"),
                                PYTEST_CURRENT_TEST="probe::test (call)"))
    blocked_under_pytest = p.returncode == 2

    assert blocked_prod is True, (
        "el guard ya no bloquea `git reset --hard` ni con el env de produccion; "
        "eso es un hallazgo mayor que el de este test")
    assert blocked_under_pytest is False, (
        "el guard dejo de auto-apagarse bajo pytest: buena noticia, actualiza "
        "este test y sacale el pop(PYTEST_CURRENT_TEST) al backtest")


# ─────────────────────────────────────────────────────────────────────────────
# Control end-to-end: los gates `live` salen rojos de verdad
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.slow
def test_live_gates_come_out_red_end_to_end():
    """La afirmacion que sostiene todo el informe.

    Si estos dos no dan BLOQUEA, ningun NO_BLOQUEA del reporte es creible:
    seria indistinguible de un arnes que no sabe reportar rojo.
    """
    p = subprocess.run([sys.executable, str(REPO / "scripts/backtest_guards.py"), "--json"],
                       capture_output=True, text=True, timeout=900, cwd=str(REPO),
                       env=_prod_env())
    assert p.returncode in (0, 1), f"el control del instrumento fallo: {p.stdout[-2000:]}"
    data = json.loads(p.stdout)
    assert data["controls_ok"] is True
    assert {c["gate"] for c in data["controls"]} == {"destructive-git-blocker",
                                                     "direct-main-guard"}
    for c in data["controls"]:
        assert c["state"] == BLOQUEA, f"{c['gate']}: {c['reason']}"


@pytest.mark.slow
def test_every_case_lands_in_one_of_the_three_states():
    p = subprocess.run([sys.executable, str(REPO / "scripts/backtest_guards.py"), "--json"],
                       capture_output=True, text=True, timeout=900, cwd=str(REPO),
                       env=_prod_env())
    data = json.loads(p.stdout)
    assert data["results"], "el backtest no corrio ningun caso"
    for r in data["results"]:
        assert r["state"] in (BLOQUEA, NO_BLOQUEA, NO_PROBADO)
        assert r["reason"], f"{r['gate']} sin motivo: un estado sin motivo no es evidencia"

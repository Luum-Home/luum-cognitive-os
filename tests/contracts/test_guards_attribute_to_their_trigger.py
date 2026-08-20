# SCOPE: os-only
"""Las tres corridas: un guard bloquea a quien lo dispara, y el bloqueado sale.

Este archivo mide DOS propiedades independientes, y una tercera que existe sólo
para que las dos primeras no se cobren con el verde barato de aflojar el guard.

  1. ATRIBUCIÓN — sesión A ensucia el índice compartido, sesión B commitea lo
     suyo. B pasa; A sigue bloqueada. Sin la segunda mitad, "arreglar" el gate
     sería tan fácil como hacerlo no bloquear nunca.
  2. ESCAPE — el cortado sigue el remedio del mensaje y funciona, dejando fila
     de auditoría. La vía tiene que ser una que se pueda ejecutar DESDE ADENTRO:
     un hook es hijo del arnés y no ve un prefijo `VAR=1` puesto al comando.
  3. EL GUARD SIGUE GUARDANDO — el caso que debe bloquear, bloquea.

Todo corre sobre repos de `tmp_path`: no se toca el checkout compartido, que es
justamente el recurso cuyo mal uso se está midiendo.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = REPO_ROOT / "hooks/scope-marker-portability-gate.sh"
BUDGET = REPO_ROOT / "hooks/subagent-budget-enforcer.sh"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "checkout"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "seed").write_text("seed\n")
    _git(repo, "add", "seed")
    _git(repo, "commit", "-qm", "seed")
    for sub in ("hooks", "rules", "tests/red_team/portability", "cos_lib"):
        (repo / sub).mkdir(parents=True, exist_ok=True)
    return repo


def _run_gate(repo: Path, command: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # El gate se ejecuta desde el repo real (sus `source` cuelgan de su dirname)
    # pero decide sobre el repo de prueba. Esa separación es la que permite
    # reproducir el índice compartido sin ensuciar el compartido de verdad.
    for key in ("COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        env[key] = str(repo)
    env["COS_METRICS_DIR"] = str(repo / ".cognitive-os" / "metrics")
    env.pop("COS_ALLOW_UNPROVEN_SCOPE_BOTH", None)
    env.pop("COS_BYPASS", None)
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    return subprocess.run(["bash", str(GATE)], input=json.dumps(payload),
                          text=True, capture_output=True, env=env,
                          cwd=str(repo), timeout=60, check=False)


def _dirty_neighbor(repo: Path) -> None:
    """La sesión A stagea una primitiva marcada y sin proof de portabilidad."""
    victim = repo / "hooks" / "vecino-sin-proof.sh"
    victim.write_text("#!/usr/bin/env bash\n# SCOPE: os-only\necho vecino\n")
    _git(repo, "add", "hooks/vecino-sin-proof.sh")


def _my_own_clean_file(repo: Path) -> None:
    """La sesión B stagea lo suyo, con su proof al lado."""
    mine = repo / "hooks" / "mio-con-proof.sh"
    mine.write_text("#!/usr/bin/env bash\n# SCOPE: os-only\necho mio\n")
    (repo / "tests/red_team/portability/test_mio-con-proof.py").write_text(
        "# SCOPE: os-only\ndef test_probe():\n    assert True\n")
    _git(repo, "add", "hooks/mio-con-proof.sh")


# --------------------------------------------------------------------------
# CORRIDA 1 — atribución, en sus dos direcciones
# --------------------------------------------------------------------------

def test_corrida1_el_vecino_sucio_no_bloquea_el_commit_acotado(tmp_path: Path) -> None:
    """B acota su commit con pathspec y pasa, aunque A tenga basura en el índice."""
    repo = _repo(tmp_path)
    _dirty_neighbor(repo)   # sesión A
    _my_own_clean_file(repo)  # sesión B

    res = _run_gate(repo, "git commit -F /tmp/msg -- hooks/mio-con-proof.sh")
    assert res.returncode == 0, (
        "B quedó bloqueada por el archivo de A pese a acotar el commit:\n"
        + res.stderr
    )


def test_corrida1_control_el_que_ensucio_sigue_bloqueado(tmp_path: Path) -> None:
    """El control que impide el verde barato: A, que sí es dueña, sigue bloqueada."""
    repo = _repo(tmp_path)
    _dirty_neighbor(repo)
    _my_own_clean_file(repo)

    res = _run_gate(repo, "git commit -F /tmp/msg -- hooks/vecino-sin-proof.sh")
    assert res.returncode == 2, (
        "A commiteó su propia primitiva sin proof y el gate la dejó pasar; "
        "el arreglo de atribución degeneró en 'no bloquea a nadie'.\n" + res.stdout
    )
    assert "vecino-sin-proof" in res.stderr


def test_corrida1_sin_pathspec_el_indice_entero_sigue_siendo_el_alcance(tmp_path: Path) -> None:
    """Sin `--`, el commit se lleva todo, así que mirarlo todo es lo correcto."""
    repo = _repo(tmp_path)
    _dirty_neighbor(repo)
    _my_own_clean_file(repo)

    res = _run_gate(repo, "git commit -m 'sin pathspec'")
    assert res.returncode == 2, (
        "Un commit sin pathspec incluye el archivo sin proof y debe bloquear; "
        "atribuir de más sería dejar pasar algo sin revisar."
    )


# --------------------------------------------------------------------------
# CORRIDA 2 — escape ejecutable desde adentro, con constancia
# --------------------------------------------------------------------------

def _run_budget(repo: Path, count: int, bypass_env: str | None,
                env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    for key in ("COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        env[key] = str(repo)
    env["COS_SUBAGENT_TOOL_CALL_BUDGET"] = "50"
    for key in ("COS_BYPASS", "COS_ALLOW_SUBAGENT_BUDGET_BYPASS",
                "COS_SUBAGENT_BUDGET_BYPASS_REASON"):
        env.pop(key, None)
    if env_extra:
        env.update(env_extra)

    runtime = repo / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    if bypass_env is not None:
        (runtime / "bypass.env").write_text(bypass_env)
    elif (runtime / "bypass.env").exists():
        (runtime / "bypass.env").unlink()

    agent = "agente-de-prueba"
    sess = repo / ".cognitive-os" / "sessions"
    payload = {"tool_name": "Bash", "tool_input": {"command": "echo hola"},
               "session_id": "sesion-de-prueba", "agent_id": agent}
    # Pre-cargar el contador al valor deseado: el hook incrementa y decide.
    res = subprocess.run(["bash", str(BUDGET)], input=json.dumps(payload),
                         text=True, capture_output=True, env=env,
                         cwd=str(repo), timeout=60, check=False)
    for d in sess.glob("*"):
        for f in d.glob("subagent-tool-calls-*"):
            f.write_text(str(count))
    return subprocess.run(["bash", str(BUDGET)], input=json.dumps(payload),
                          text=True, capture_output=True, env=env,
                          cwd=str(repo), timeout=60, check=False)


def test_corrida2_el_cortado_se_destraba_con_bypass_env_y_deja_auditoria(tmp_path: Path) -> None:
    """El remedio del mensaje se ejecuta desde adentro y funciona."""
    repo = _repo(tmp_path)
    sin_escape = _run_budget(repo, 60, bypass_env=None)
    if sin_escape.returncode != 2:
        pytest.skip("el contador no llegó al bloqueo; sin bloqueo no hay escape que medir")

    con_escape = _run_budget(
        repo, 60,
        bypass_env=("COS_BYPASS=subagent_budget\n"
                    "COS_SUBAGENT_BUDGET_BYPASS_REASON=cerrando el informe\n"),
    )
    assert con_escape.returncode == 0, (
        "El bloqueado siguió el remedio del mensaje y siguió bloqueado:\n"
        + con_escape.stderr
    )

    ledger = repo / ".cognitive-os" / "metrics" / "bypass-activation.jsonl"
    assert ledger.is_file(), "el escape no dejó fila de auditoría"
    rows = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    assert any(r["bypass_key"] == "subagent_budget"
               and r["reason"] == "cerrando el informe" for r in rows), rows


def test_corrida2_control_el_escape_sin_motivo_no_destraba(tmp_path: Path) -> None:
    """Un escape sin constancia no es escape: la clave sola no alcanza."""
    repo = _repo(tmp_path)
    res = _run_budget(repo, 60, bypass_env="COS_BYPASS=subagent_budget\n")
    assert res.returncode == 2, (
        "el bypass destrabó sin motivo declarado; eso lo vuelve decoración"
    )


# --------------------------------------------------------------------------
# CORRIDA 3 — el guard sigue guardando
# --------------------------------------------------------------------------

def test_corrida3_el_presupuesto_sigue_cortando_sin_bypass(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    res = _run_budget(repo, 60, bypass_env=None)
    assert res.returncode == 2, "el presupuesto dejó de cortar"


def test_corrida3_primitiva_nueva_sin_marcador_sigue_bloqueando(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    nueva = repo / "hooks" / "sin-marcador.sh"
    nueva.write_text("#!/usr/bin/env bash\necho sin marcador\n")
    _git(repo, "add", "hooks/sin-marcador.sh")
    res = _run_gate(repo, "git commit -F /tmp/msg -- hooks/sin-marcador.sh")
    assert res.returncode == 2, "una primitiva nueva sin SCOPE dejó de bloquear"
    assert "sin-marcador" in res.stderr

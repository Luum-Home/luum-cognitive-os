"""La identidad de sesion tiene que resolverse desde OTRO proceso.

hooks/session-init.sh:223 escribe `.current-session-$$` con su propio PID y
hooks/_lib/common.sh la leia con el PID DEL LECTOR. Como el PID del lector
nunca es el del escritor, ningun hook distinto de session-init podia resolver
la sesion: `resolve_session_dir` caia siempre al directorio global.

Medido el 2026-08-19 sobre el repo real: 8.887 eventos de hooks que llaman
`resolve_session_dir` cayeron a .cognitive-os/metrics/ ese dia, y 0 a los seis
.cognitive-os/sessions/*/metrics/ existentes (que estan vacios desde que
session-init.sh:21 los crea). Poblacion no nula -> el cero es "no segrego",
no "no hubo trafico".

Estos tests prueban el EFECTO, no el exit code: un proceso hook distinto del
escritor, alimentado con el payload del harness, tiene que escribir su metrica
DENTRO del directorio de la sesion correcta. Contra la ultima version de
common.sh anterior al fix el mismo escenario resuelve al global (direccion 1).
"""

from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
COMMON = REPO / "hooks" / "_lib" / "common.sh"
BASH = "/bin/bash"

SESSION_ID = "1787183298-51467-3fe05b4a"


def _fake_project(tmp_path: Path) -> Path:
    """Proyecto temporal con una sesion viva. Nunca toca el .cognitive-os real."""
    proj = tmp_path / "proj"
    (proj / ".cognitive-os" / "sessions" / SESSION_ID).mkdir(parents=True)
    (proj / ".cognitive-os" / "metrics").mkdir(parents=True)
    return proj


def _clean_env(proj: Path) -> dict:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(proj)
    for key in (
        "COGNITIVE_OS_PROJECT_DIR",
        "CODEX_PROJECT_DIR",
        "COGNITIVE_OS_SESSION_ID",
        # Se limpia porque el proceso de test HEREDA la del arnes real y, por
        # precedencia, ganaria sobre el payload. Que estos tests hayan fallado
        # con la sesion viva (93e6e34f-...) al agregar esta via es la prueba de
        # que la variable esta seteada de verdad en cada subproceso.
        "CLAUDE_CODE_SESSION_ID",
        "CLAUDE_SESSION_ID",
        "CODEX_SESSION_ID",
        "COS_SESSION_SCOPED_METRICS",
    ):
        env.pop(key, None)
    return env


def _run_hook(common_sh: Path, proj: Path, payload: dict, *, scoped) -> str:
    """Corre un 'hook' en un proceso PROPIO, con el payload por stdin.

    Reproduce el patron real de 10 de los 13 llamadores: read_stdin_json cachea
    el payload y recien despues se llama resolve_session_dir.
    """
    script = textwrap.dedent(
        f"""
        set -uo pipefail
        source "{common_sh}"
        read_stdin_json
        METRICS_DIR="$(resolve_session_dir)"
        echo '{{"probe":1}}' >> "$METRICS_DIR/probe-metric.jsonl"
        printf '%s' "$METRICS_DIR"
        """
    )
    env = _clean_env(proj)
    if scoped is not None:
        env["COS_SESSION_SCOPED_METRICS"] = scoped
    out = subprocess.run(
        [BASH, "-c", script],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        cwd=str(proj),
    )
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


def _pre_fix_common(tmp_path: Path) -> Path:
    """La ultima version commiteada de common.sh SIN cos_session_id.

    Se busca por contenido y no por posicion en el log, para que el test siga
    apuntando al codigo defectuoso despues de commitear el fix.
    """
    revs = subprocess.run(
        ["git", "log", "--format=%H", "-n", "40", "--", "hooks/_lib/common.sh"],
        cwd=str(REPO), capture_output=True, text=True, check=True,
    ).stdout.split()
    for rev in revs:
        blob = subprocess.run(
            ["git", "show", f"{rev}:hooks/_lib/common.sh"],
            cwd=str(REPO), capture_output=True, text=True,
        )
        if blob.returncode != 0:
            continue
        if "cos_session_id" not in blob.stdout:
            dst = tmp_path / "common-prefix.sh"
            dst.write_text(blob.stdout)
            return dst
    pytest.skip("no hay version historica de common.sh sin cos_session_id")


# ─── Direccion 1: el codigo previo al fix NO resuelve ────────────────────────

def test_codigo_previo_al_fix_no_resuelve_la_sesion(tmp_path):
    """Contrafactual: con el common.sh de antes del fix el hook cae al global."""
    proj = _fake_project(tmp_path)
    viejo = _pre_fix_common(tmp_path)
    resolved = _run_hook(
        viejo, proj, {"session_id": SESSION_ID, "tool_name": "Bash"}, scoped="1"
    )
    assert resolved == str(proj / ".cognitive-os" / "metrics"), (
        "el codigo historico no deberia poder resolver la sesion desde otro proceso"
    )
    assert not (proj / ".cognitive-os" / "sessions" / SESSION_ID / "metrics").exists()


# ─── Direccion 2: con el fix, resuelve y escribe donde corresponde ───────────

def test_hook_en_otro_proceso_resuelve_la_sesion_del_payload(tmp_path):
    proj = _fake_project(tmp_path)
    resolved = _run_hook(
        COMMON, proj, {"session_id": SESSION_ID, "tool_name": "Bash"}, scoped="1"
    )
    esperado = proj / ".cognitive-os" / "sessions" / SESSION_ID / "metrics"
    assert resolved == str(esperado), f"resolvio a {resolved}"
    assert (esperado / "probe-metric.jsonl").read_text().strip() == '{"probe":1}', (
        "la metrica tiene que aterrizar en el directorio de la sesion, no en el global"
    )
    assert not (proj / ".cognitive-os" / "metrics" / "probe-metric.jsonl").exists()


def test_resolve_session_dir_no_consume_stdin(tmp_path):
    """Los llamadores que hacen su propio `cat` DESPUES no se pueden romper.

    packages/prompt-quality-gate/hooks/prompt-quality.sh:27 y
    packages/verification-audit/hooks/result-truncator.sh:27 llaman
    resolve_session_dir ANTES de leer stdin. Si la libreria consumiera stdin
    ahi, esos hooks recibirian payload vacio.
    """
    proj = _fake_project(tmp_path)
    script = textwrap.dedent(
        f"""
        set -uo pipefail
        source "{COMMON}"
        METRICS_DIR="$(resolve_session_dir)"   # antes de leer stdin
        INPUT="$(cat)"
        printf '%s' "$(printf '%s' "$INPUT" | jq -r '.tool_name')"
        """
    )
    out = subprocess.run(
        [BASH, "-c", script],
        input=json.dumps({"session_id": SESSION_ID, "tool_name": "Edit"}),
        capture_output=True, text=True, env=_clean_env(proj), cwd=str(proj),
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "Edit", (
        "resolve_session_dir consumio stdin y dejo sin payload al hook"
    )


def test_hook_que_lee_su_propio_input_tambien_resuelve(tmp_path):
    proj = _fake_project(tmp_path)
    script = textwrap.dedent(
        f"""
        set -uo pipefail
        source "{COMMON}"
        INPUT="$(cat)"
        printf '%s' "$(cos_session_id)"
        """
    )
    out = subprocess.run(
        [BASH, "-c", script],
        input=json.dumps({"session_id": SESSION_ID}),
        capture_output=True, text=True, env=_clean_env(proj), cwd=str(proj),
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == SESSION_ID


# ─── Runtime: el default NO mueve una sola metrica ───────────────────────────

def test_default_sigue_escribiendo_al_global(tmp_path):
    """Sin COS_SESSION_SCOPED_METRICS el comportamiento en runtime no cambia.

    Encender la segregacion hoy pierde datos: el merge de vuelta al global vive
    en el hook de cleanup de sesion y resuelve la sesion con el mismo
    `.current-session-$$` imposible, asi que nunca corre. Ver el comentario de
    resolve_session_dir en hooks/_lib/common.sh.
    """
    proj = _fake_project(tmp_path)
    resolved = _run_hook(
        COMMON, proj, {"session_id": SESSION_ID, "tool_name": "Bash"}, scoped=None
    )
    assert resolved == str(proj / ".cognitive-os" / "metrics")
    assert (proj / ".cognitive-os" / "metrics" / "probe-metric.jsonl").exists()


def test_dos_sesiones_concurrentes_no_se_pisan(tmp_path):
    """El caso que el SO existe para cubrir.

    La alternativa 'escribir `.current-session` sin PID' colapsaria las dos
    sesiones en un mismo archivo. Resolver por payload las mantiene separadas.
    """
    proj = _fake_project(tmp_path)
    otra = "1787182710-78393-fbe796dd"
    (proj / ".cognitive-os" / "sessions" / otra).mkdir(parents=True)

    a = _run_hook(COMMON, proj, {"session_id": SESSION_ID}, scoped="1")
    b = _run_hook(COMMON, proj, {"session_id": otra}, scoped="1")

    assert a != b
    assert a.endswith(f"{SESSION_ID}/metrics")
    assert b.endswith(f"{otra}/metrics")
    assert (Path(a) / "probe-metric.jsonl").exists()
    assert (Path(b) / "probe-metric.jsonl").exists()


# ─── La via del arnes: sin payload, solo entorno ─────────────────────────────

def _run_hook_sin_payload(common_sh: Path, proj: Path, env_extra: dict) -> str:
    """Hook que NUNCA lee stdin. Es el caso de session-heartbeat y de cualquier
    llamador futuro: solo tiene su entorno."""
    script = textwrap.dedent(
        f"""
        set -uo pipefail
        source "{common_sh}"
        printf '%s' "$(resolve_session_dir)"
        """
    )
    env = _clean_env(proj)
    env.update(env_extra)
    out = subprocess.run(
        [BASH, "-c", script], input="", capture_output=True, text=True,
        env=env, cwd=str(proj),
    )
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


def test_claude_code_session_id_resuelve_sin_payload(tmp_path):
    """CLAUDE_CODE_SESSION_ID es la variable documentada del arnes.

    env-vars.md:339 — "Set automatically to the current session ID in Bash and
    PowerShell tool subprocesses, hook command subprocesses ... this matches the
    session_id field in the hook JSON input".

    Es lo que una funcion de LIBRERIA necesita: no ve el $INPUT del hook, pero
    si ve su propio entorno.
    """
    proj = _fake_project(tmp_path)
    resolved = _run_hook_sin_payload(
        COMMON, proj,
        {"CLAUDE_CODE_SESSION_ID": SESSION_ID, "COS_SESSION_SCOPED_METRICS": "1"},
    )
    assert resolved == str(proj / ".cognitive-os" / "sessions" / SESSION_ID / "metrics")


def test_claude_session_id_sin_code_no_es_la_variable_del_arnes(tmp_path):
    """`CLAUDE_SESSION_ID` (sin CODE) tiene 0 ocurrencias en env-vars.md.

    Este test no la prohibe -el repo la nombra en ~101 lugares- pero fija que la
    que resuelve de verdad es la otra: si alguien invierte la precedencia, esto
    falla.
    """
    proj = _fake_project(tmp_path)
    otra = "1787182710-78393-fbe796dd"
    (proj / ".cognitive-os" / "sessions" / otra).mkdir(parents=True)
    resolved = _run_hook_sin_payload(
        COMMON, proj,
        {
            "CLAUDE_CODE_SESSION_ID": SESSION_ID,
            "CLAUDE_SESSION_ID": otra,
            "COS_SESSION_SCOPED_METRICS": "1",
        },
    )
    assert resolved.endswith(f"{SESSION_ID}/metrics"), (
        "gano CLAUDE_SESSION_ID, que no existe en el arnes"
    )


def test_codigo_previo_al_fix_tampoco_lee_la_variable_del_arnes(tmp_path):
    """Direccion 1 para esta via: el codigo historico ignoraba la variable."""
    proj = _fake_project(tmp_path)
    viejo = _pre_fix_common(tmp_path)
    resolved = _run_hook_sin_payload(
        viejo, proj,
        {"CLAUDE_CODE_SESSION_ID": SESSION_ID, "COS_SESSION_SCOPED_METRICS": "1"},
    )
    assert resolved == str(proj / ".cognitive-os" / "metrics")

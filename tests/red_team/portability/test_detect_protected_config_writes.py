# SCOPE: os-only
"""Proof pareado de portabilidad del detector de escrituras protegidas.

Que custodia
------------
`hooks/protected-config-write-guard.sh` corre en PreToolUse e inspecciona el TEXTO
DEL COMANDO, asi que bloquea el camino corto y deja pasar el largo (medido
2026-08-20):

    echo x >> rules/RULES-COMPACT.md      -> exit 2  BLOQUEA
    python3 scripts/escritor.py           -> exit 0  PASA

El detector cierra esa brecha en PostToolUse. No previene -- la escritura ya
ocurrio -- pero garantiza que no pase sin verse.

Los DOS bugs que este archivo existe para que no vuelvan
--------------------------------------------------------
Los dos estaban en la primera version y los dos pasaban todas las pruebas de humo:

1. **La huella hasheaba solo el CONJUNTO DE RUTAS sucias.** Si un archivo ya estaba
   sucio --el caso normal en cualquier sesion de trabajo-- modificarlo otra vez
   dejaba el mismo conjunto y la misma huella. El detector era ciego justo cuando
   mas hace falta.

2. **Un `.strip()` defensivo de mas:**

       entry = entry.strip()   # ' M .claude/settings.json' -> 'M .claude/...'
       rel = entry[3:]         # -> 'claude/settings.json'  <- se comio el punto

   El formato porcelain son DOS caracteres de estado mas un espacio, y el PRIMERO
   PUEDE SER ESPACIO. Con el strip la ruta salia mutilada, ningun glob la matcheaba,
   y el detector quedaba ciego a TODO `.claude/`. git decia
   `M .claude/settings.json` y el detector reportaba `sin_cambios`.

Ninguno de los dos se ve leyendo el codigo. Los dos caen con la misma prueba de
tres ramas: sin cambios / con cambio sin aprobar / con cambio aprobado. Por eso lo
que se afirma abajo no es "el detector corre" sino que **DISCRIMINA**.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOK = REPO / "hooks" / "protected-config-write-detector.sh"
SCRIPT = REPO / "scripts" / "detect_protected_config_writes.py"
VICTIMA = REPO / ".claude" / "settings.json"


def _env(aprobado: bool = False) -> dict:
    env = dict(os.environ)
    for v in ("COS_ALLOW_PROTECTED_CONFIG_WRITE", "COS_BYPASS",
              "DISABLE_HOOK_PROTECTED_CONFIG_WRITE_DETECTOR"):
        env.pop(v, None)
    if aprobado:
        env["COS_ALLOW_PROTECTED_CONFIG_WRITE"] = "1"
    return env


def _hook(cmd: str, aprobado: bool = False) -> int:
    payload = json.dumps({
        "hook_event_name": "PostToolUse", "tool_name": "Bash",
        "tool_input": {"command": cmd}, "cwd": str(REPO), "session_id": "proof",
    })
    return subprocess.run(
        ["bash", str(HOOK)], input=payload, capture_output=True, text=True,
        timeout=180, cwd=str(REPO), env=_env(aprobado), check=False,
    ).returncode


@pytest.mark.parametrize("ruta", [HOOK, SCRIPT])
def test_declara_scope(ruta: Path):
    cabecera = ruta.read_text().splitlines()[:3]
    assert any("SCOPE:" in ln for ln in cabecera), f"{ruta.name} no declara SCOPE"


@pytest.fixture
def victima_restaurable():
    """Toca un archivo protegido REAL y lo restaura pase lo que pase.

    Se usa el archivo de verdad y no un fixture porque el detector consulta `git
    status` sobre el repo: un archivo inventado en tmp_path no aparece ahi, y la
    prueba pasaria sin ejercitar nada.
    """
    original = VICTIMA.read_bytes()
    try:
        yield VICTIMA
    finally:
        VICTIMA.write_bytes(original)
        _hook("echo restaurando la linea de base")
        assert VICTIMA.read_bytes() == original, "no se pudo restaurar el archivo protegido"


def test_las_tres_ramas_discriminan(victima_restaurable: Path):
    """LA PRUEBA. Las tres ramas tienen que dar veredictos DISTINTOS.

    Si las tres dieran lo mismo, el detector no discrimina y da igual lo que haga
    por dentro. Los dos bugs de la primera version colapsaban justamente aca.
    """
    original = victima_restaurable.read_bytes()

    _hook("echo linea de base")
    sin_cambios = _hook("echo nada cambio")

    victima_restaurable.write_bytes(original + b'\n{"proof": 1}\n')
    sin_aprobar = _hook("python3 algun/script/que/escribe.py")

    victima_restaurable.write_bytes(original + b'\n{"proof": 2}\n')
    aprobado = _hook("python3 algun/script/que/escribe.py", aprobado=True)

    assert sin_cambios == 0, f"reporto un cambio donde no lo hubo (exit {sin_cambios})"
    assert sin_aprobar == 2, (
        f"NO detecto una escritura protegida sin aprobacion (exit {sin_aprobar}). "
        "Es el agujero que este hook existe para cerrar: el guard de PreToolUse "
        "tampoco la ve, asi que nadie la veria."
    )
    assert aprobado == 0, (
        f"bloqueo una escritura APROBADA (exit {aprobado}). Un detector que no "
        "distingue aprobado de no aprobado se desactiva en una semana."
    )


def test_no_confunde_no_pude_con_no_hay(tmp_path: Path):
    """Corrido fuera de un checkout de git tiene que decir `unknown`, no `sin_cambios`.

    "No pude verificar" y "no hubo cambios" son estados distintos y producen
    acciones distintas. Colapsarlos es como fallaba la precondicion de la lane de
    chaos, el secret-detector y tres guards mas de esta misma jornada.
    """
    env = _env()
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_path)
    r = subprocess.run(
        [sys.executable, str(SCRIPT)], input=json.dumps({"tool_input": {"command": "x"}}),
        capture_output=True, text=True, timeout=120, cwd=str(tmp_path), env=env, check=False,
    )
    salida = json.loads(r.stdout.strip() or "{}")
    assert salida.get("status") == "unknown", (
        f"fuera de un checkout de git devolvio {salida.get('status')!r} en vez de "
        "'unknown': esta afirmando ausencia de cambios sobre algo que no pudo mirar"
    )
    assert salida.get("why"), "dijo unknown sin decir por que"


def test_la_huella_mira_el_contenido_y_no_solo_las_rutas(victima_restaurable: Path):
    """El BUG 1, fijado. Dos escrituras al MISMO archivo ya sucio tienen que diferir.

    Con la huella sobre el conjunto de rutas, la segunda escritura era invisible
    porque el conjunto no cambiaba. En una sesion real casi todo archivo protegido
    ya esta sucio, asi que el detector nacia ciego.
    """
    original = victima_restaurable.read_bytes()
    victima_restaurable.write_bytes(original + b"\n{}\n")
    _hook("echo primera, establece base con el archivo YA sucio")
    victima_restaurable.write_bytes(original + b"\n{}\n{}\n")
    segunda = _hook("python3 otro/script.py")
    assert segunda == 2, (
        "no detecto la SEGUNDA escritura sobre un archivo que ya estaba sucio: la "
        "huella volvio a mirar solo la lista de rutas"
    )


def test_el_kill_switch_existe_y_se_puede_nombrar():
    """Un guard sin escape se apaga entero la primera vez que estorba."""
    fuente = HOOK.read_text()
    assert "DISABLE_HOOK_PROTECTED_CONFIG_WRITE_DETECTOR" in fuente, (
        "no tiene kill-switch nombrable: el dia que moleste se lo va a desregistrar, "
        "y ahi se pierde la deteccion entera en vez de una corrida"
    )

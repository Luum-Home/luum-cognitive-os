"""Un kill-switch que no se puede activar es peor que no tenerlo.

QUÉ GATEA Y QUÉ NO, dicho al principio. Esto NO exige que todo hook lea su token
del texto del comando: hay tres vías de activación que funcionan sin eso —
``VAR=1 claude`` al LANZAR el arnés (hereda el entorno del shell que lo arranca),
``export VAR=1`` previo, y el bloque ``env`` de ``.claude/settings.json`` o el
archivo ``.cognitive-os/runtime/bypass.env``. Forzar la lectura del texto sería el
error simétrico: borraría la diferencia entre mentir y usar otra vía.

Lo que gatea es **la mentira**: un mensaje de bloqueo que ofrece
``VAR=1 <comando-que-corre-adentro-de-la-sesión>`` cuando el hook solo lee del
entorno. Esa forma no llega a NINGÚN hook de NINGÚN evento — el hook es hijo del
arnés, no del shell del Bash tool, y ya decidió antes de que ese shell existiera.
El lector la tipea, sigue bloqueado, y no tiene cómo saber que el problema es la
vía. Origen: 2026-08-19, un agente reportó tres veces seguidas no poder ejecutar
el bypass que el propio mensaje le ofrecía.

POR QUÉ HAY CUATRO FIXTURES Y NO UNA. Tomado de
``scripts/home-path-family-mutation-check.sh``: sin los controles, un gate que
rojea todo también pasa el caso rojo, y nadie se entera. ``honesto_texto``,
``honesto_export`` y ``ambiguo`` son los controles que mantienen interpretable a
``mentira``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "_ks_audit", REPO / "scripts" / "audit_killswitch_activation.py"
)
assert _SPEC and _SPEC.loader
_AUDIT = importlib.util.module_from_spec(_SPEC)
sys.modules["_ks_audit"] = _AUDIT
_SPEC.loader.exec_module(_AUDIT)


# ── Deuda declarada, medida 2026-08-19 ──────────────────────────────────────
# Cada entrada es `<hook>::<VARIABLE>`: la línea se mueve con cualquier edición
# de arriba, la variable no. Baseline de IGUALDAD EXACTA: no absorbe una mentira
# nueva, no lista una ya migrada, y no tiene asientos libres donde una regresión
# pueda aterrizar en silencio. Vaciarlo es el arreglo; agrandarlo es la trampa.
KNOWN_UNREACHABLE_KILLSWITCHES: set[str] = {
    "hooks/adoption-freeze-gate.sh::COS_ALLOW_ADOPTION_FREEZE_BYPASS",
    "hooks/adoption-freeze-gate.sh::COS_ALLOW_FREEZE_TOGGLE",
    "hooks/attribution-completeness-validator.sh::COS_ALLOW_INCOMPLETE_ATTRIBUTION",
    "hooks/clean-room-ast-similarity-gate.sh::COS_ALLOW_AST_SIMILARITY",
    "hooks/clean-room-ast-similarity-gate.sh::COS_ALLOW_CLEAN_ROOM_BYPASS",
    "hooks/external-cache-content-leak.sh::COS_ALLOW_VERBATIM_LEAK",
    "hooks/git-commit-scope-guard.sh::COS_BYPASS_COMMIT_GUARD",
    "hooks/legal-review-required-on-runtime-import.sh::COS_ALLOW_PRE_LEGAL_REVIEW_IMPORT",
    "hooks/lib-symlink-divergence-detector.sh::COS_ALLOW_LIB_DIVERGENCE",
    "hooks/spdx-header-required.sh::COS_ALLOW_MISSING_SPDX",
}


@pytest.fixture(scope="module")
def censo() -> list:
    rows = _AUDIT.collect()
    assert rows, "el censo quedó vacío: el gate pasaría por vacuidad"
    return rows


@pytest.fixture(scope="module")
def mentiras(censo) -> set[str]:
    return {f"{r.file}::{r.var}" for r in censo if r.verdict == "mentira"}


def test_el_censo_ve_mas_de_un_hook(censo) -> None:
    """Un rglob roto devuelve pocos archivos y el gate pasa por ceguera."""
    archivos = {r.file for r in censo}
    assert len(archivos) >= 50, (
        f"el censo solo vio {len(archivos)} hooks. `hooks/*.sh` es de un nivel y "
        "no ve _lib/ ni _archived/; este censo usa rglob a propósito."
    )


def test_ningun_killswitch_nuevo_promete_una_via_inejecutable(mentiras) -> None:
    nuevas = mentiras - KNOWN_UNREACHABLE_KILLSWITCHES
    assert not nuevas, (
        f"estos mensajes ofrecen `VAR=1 <comando>` desde adentro de la sesión, que "
        f"no llega a ningún hook, y el hook solo lee del entorno: {sorted(nuevas)}. "
        "Dos arreglos válidos: (a) leer también el token del texto del comando con "
        "el ancla de prefijo de hooks/protected-config-write-guard.sh, o (b) cambiar "
        "el mensaje a una vía que sí funciona (`export VAR=1` antes de lanzar, "
        "`VAR=1 claude` al lanzar, .claude/settings.json, .cognitive-os/runtime/"
        "bypass.env). Callar el mensaje sin darle vía real no es ninguna de las dos."
    )


def test_el_baseline_no_lista_hooks_ya_migrados(mentiras) -> None:
    """Un baseline por encima de la realidad acepta regresiones gratis."""
    rancios = KNOWN_UNREACHABLE_KILLSWITCHES - mentiras
    assert not rancios, (
        f"{sorted(rancios)} ya no mienten: sacalos de "
        "KNOWN_UNREACHABLE_KILLSWITCHES. Vaciar el baseline es el arreglo."
    )


def test_el_baseline_no_tiene_asientos_fantasma(censo) -> None:
    """Una entrada cuyo hook o variable ya no existe es un lugar libre."""
    vivos = {f"{r.file}::{r.var}" for r in censo}
    fantasmas = KNOWN_UNREACHABLE_KILLSWITCHES - vivos
    assert not fantasmas, (
        f"{sorted(fantasmas)} no corresponde a ningún kill-switch presente. Un "
        "asiento libre en un baseline es donde una regresión futura aterriza sin "
        "que el gate diga nada."
    )


# ── Las cuatro corridas del instrumento ─────────────────────────────────────
# Un fusible sin eval es una esperanza. Estas fixtures ejercitan el clasificador
# en las cuatro direcciones que importan; sin los tres controles, un gate que
# rojea todo también pasaría la primera.

_MENTIRA = """#!/usr/bin/env bash
if [ "${COS_ALLOW_DEMO_BYPASS:-0}" = "1" ]; then exit 0; fi
echo "BLOCKED. Bypass: COS_ALLOW_DEMO_BYPASS=1 git commit -m '...'" >&2
exit 2
"""

_HONESTO_TEXTO = """#!/usr/bin/env bash
CMD="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')"
if [ "${COS_ALLOW_DEMO_BYPASS:-0}" = "1" ]; then exit 0; fi
printf '%s' "$CMD" | grep -Eq '(^|[;&|(])[[:space:]]*COS_ALLOW_DEMO_BYPASS=1[[:space:]]' && exit 0
echo "BLOCKED. Bypass: COS_ALLOW_DEMO_BYPASS=1 git commit -m '...'" >&2
exit 2
"""

_HONESTO_EXPORT = """#!/usr/bin/env bash
if [ "${COS_ALLOW_DEMO_BYPASS:-0}" = "1" ]; then exit 0; fi
echo "BLOCKED. Bypass: export COS_ALLOW_DEMO_BYPASS=1 before launching the harness" >&2
exit 2
"""

_AMBIGUO = """#!/usr/bin/env bash
if [ "${COS_ALLOW_DEMO_BYPASS:-0}" = "1" ]; then exit 0; fi
echo "BLOCKED. Override only with COS_ALLOW_DEMO_BYPASS=1 and a written reason." >&2
exit 2
"""


def _veredicto(fuente: str) -> str:
    filas = [r for r in _AUDIT.classify_source("hooks/demo.sh", fuente) if r.verdict != "codigo"]
    assert filas, "el clasificador no vio la variable en el fixture"
    orden = {"mentira": 0, "ambiguo": 1, "honesto": 2}
    return sorted(filas, key=lambda r: orden[r.verdict])[0].verdict


@pytest.mark.parametrize(
    ("nombre", "fuente", "esperado"),
    [
        ("mentira", _MENTIRA, "mentira"),
        ("honesto_texto", _HONESTO_TEXTO, "honesto"),
        ("honesto_export", _HONESTO_EXPORT, "honesto"),
        ("ambiguo", _AMBIGUO, "ambiguo"),
    ],
)
def test_el_clasificador_distingue_las_cuatro_formas(nombre, fuente, esperado) -> None:
    assert _veredicto(fuente) == esperado, (
        f"fixture `{nombre}`: se esperaba {esperado} y dio {_veredicto(fuente)}"
    )


# ── La deuda de 4a9c2d4fc: el rojo que no se había conseguido reproducir ────


def _correr_research_guard(tmp: Path, comando: str) -> int:
    """Corre el guard real contra un repo git descartable. No toca este repo."""
    subprocess.run(["git", "init", "-q", str(tmp)], check=True, capture_output=True)
    docs = tmp / "docs"
    docs.mkdir()
    # Dispara la regla proprietary/unlicensed sin declarar frontera clean-room.
    (docs / "nota.md").write_text("Se revisó una fuente proprietary, all rights reserved.\n")
    subprocess.run(["git", "-C", str(tmp), "add", "docs/nota.md"], check=True, capture_output=True)
    env = dict(os.environ)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp)
    env.pop("COS_ALLOW_RESEARCH_COMPLIANCE_BYPASS", None)
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": comando}})
    return subprocess.run(
        ["/bin/bash", str(REPO / "hooks" / "research-compliance-guard.sh")],
        input=payload, text=True, capture_output=True, env=env, cwd=str(tmp),
    ).returncode


def test_research_guard_bloquea_sin_el_token(tmp_path) -> None:
    """El rojo. 4a9c2d4fc arregló el bypass 'por inspección' sin conseguir esto."""
    assert _correr_research_guard(tmp_path, "git commit -m 'wip'") == 2


def test_research_guard_acepta_el_token_desde_el_texto(tmp_path) -> None:
    """El verde, y por la vía que el mensaje ofrece: el token en el comando."""
    cmd = "COS_ALLOW_RESEARCH_COMPLIANCE_BYPASS=1 git commit -m 'wip'"
    assert _correr_research_guard(tmp_path, cmd) == 0


# ── La migración de hoy, ejercitada de verdad ───────────────────────────────
# hooks/symlink-mutation-guard.sh pasó de solo-entorno a leer también el token
# del texto, con ancla de prefijo. Un fusible sin eval es una esperanza: estas
# tres corridas son el eval. La tercera es la que separa el arreglo correcto del
# match-en-cualquier-lado que se auto-concede.

_LN_LOOP = "ln -sf realdir/x.py dirlink/x.py"


def _proyecto_con_dir_symlink(tmp: Path) -> Path:
    """Reproduce la topología del incidente 2026-05-02 en un árbol descartable.

    `dirlink` es un symlink de DIRECTORIO a `realdir`, así que `dirlink/x.py` y
    `realdir/x.py` resuelven al mismo archivo y el `ln -s` es un self-loop. Se
    construye acá y no se busca en el repo porque `lib/harness_adapter`, el par
    original, ya no existe: un control que depende de un árbol que cambió
    silencia el caso rojo sin avisar.
    """
    (tmp / "realdir").mkdir()
    (tmp / "realdir" / "x.py").write_text("# fixture\n")
    (tmp / "dirlink").symlink_to("realdir")
    return tmp


def _correr_symlink_guard(proyecto: Path, comando: str) -> int:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": comando}})
    env = dict(os.environ)
    env.pop("COS_ALLOW_SYMLINK_MUTATION", None)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(proyecto)
    return subprocess.run(
        ["/bin/bash", str(REPO / "hooks" / "symlink-mutation-guard.sh")],
        input=payload, text=True, capture_output=True, env=env, cwd=str(proyecto),
    ).returncode


def test_symlink_guard_bloquea_el_self_loop(tmp_path) -> None:
    """El control. Sin él, un hook que permite todo también pasa el verde."""
    assert _correr_symlink_guard(_proyecto_con_dir_symlink(tmp_path), _LN_LOOP) == 2


def test_symlink_guard_acepta_el_token_como_prefijo(tmp_path) -> None:
    """El verde por la vía que el mensaje ofrece: el token en el texto."""
    proy = _proyecto_con_dir_symlink(tmp_path)
    assert _correr_symlink_guard(proy, f"COS_ALLOW_SYMLINK_MUTATION=1 {_LN_LOOP}") == 0


def test_symlink_guard_no_se_auto_concede_por_mencion(tmp_path) -> None:
    """El token dentro del texto SIN ser una asignación no autoriza nada.

    Sin el ancla de prefijo, escribir un informe SOBRE la variable autorizaba la
    mutación que el informe describía. Es el defecto que
    hooks/protected-config-write-guard.sh documenta haber cometido primero.
    """
    proy = _proyecto_con_dir_symlink(tmp_path)
    cmd = f"echo 'usar COS_ALLOW_SYMLINK_MUTATION=1 si hace falta' >> nota.md && {_LN_LOOP}"
    assert _correr_symlink_guard(proy, cmd) == 2

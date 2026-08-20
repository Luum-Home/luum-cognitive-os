# SCOPE: os-only
"""El bypass de un agente no puede destrabar a sus hermanos.

El agujero, medido el 2026-08-20
--------------------------------
``_cos_bypass_runtime_file`` componia siempre ``.cognitive-os/runtime/bypass.env``,
de alcance PROYECTO. Consecuencia: el bypass que escribia UN sub-agente desactivaba
el guard para TODOS los concurrentes, y el motivo que quedaba en el archivo
pertenecia a un encargo que nada tenia que ver con el de ellos.

Un agente cansado de que un guard le estorbe apagaba, sin saberlo, la misma defensa
para sus cinco hermanos. Y en la telemetria eso se ve como cinco agentes que
trabajaron sin friccion, no como cinco defensas caidas.

Por que el operador SI conserva el alcance de proyecto
------------------------------------------------------
Desactivar un guard en tu propia maquina, para tu propia sesion, es una decision
legitima y con dueno visible: hay una persona que la tomo y que la puede revertir.
Lo que no puede pasar es que esa decision la tome un proceso que nadie esta mirando
y que ademas se la aplique a otros procesos que nadie esta mirando.

Por eso la regla no es "no hay bypass" sino "el bypass tiene dueno":
    con agente en contexto -> bypass-<agente>.env
    sin agente (operador)  -> bypass.env

Un guard sin escape no se respeta mas: se desregistra. Esa frase salio de otro
informe de la misma jornada y es la razon por la que este archivo prueba el
AISLAMIENTO del escape y no su ausencia.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
RESOLVER = REPO / "hooks" / "_lib" / "bypass-resolver.sh"

# Las tres variables de las que el resolver toma la identidad del agente.
VARS_AGENTE = ("COS_AGENT_ID", "CLAUDE_AGENT_ID", "CODEX_AGENT_ID")


def _archivo_para(agente: str | None, proyecto: Path, var: str = "COS_AGENT_ID") -> str:
    env = dict(os.environ)
    # Heredados, convierten cualquier guard en uno que aprueba todo.
    for v in ("COS_ALLOW_PROTECTED_CONFIG_WRITE", "COS_BYPASS", *VARS_AGENTE):
        env.pop(v, None)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(proyecto)
    if agente:
        env[var] = agente
    r = subprocess.run(
        ["bash", "-c", f'source "{RESOLVER}" && _cos_bypass_runtime_file'],
        capture_output=True, text=True, timeout=60, env=env, check=False,
    )
    assert r.returncode == 0, f"el resolver fallo: {r.stderr[-400:]}"
    salida = r.stdout.strip()
    assert salida, "el resolver no devolvio ninguna ruta: la sonda no esta midiendo nada"
    return Path(salida).name


@pytest.fixture
def proyecto():
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / ".cognitive-os" / "runtime").mkdir(parents=True)
        yield Path(d)


def test_dos_agentes_no_comparten_archivo(proyecto: Path):
    """EL HALLAZGO. Si A y B resuelven al mismo archivo, el bypass de A vale para B."""
    a = _archivo_para("agente-A", proyecto)
    b = _archivo_para("agente-B", proyecto)
    assert a != b, (
        f"los dos agentes resuelven al mismo archivo ({a!r}): el bypass de uno "
        "destraba al otro, que es exactamente el agujero que este test existe para cerrar"
    )
    assert "agente-A" in a and "agente-B" in b


def test_el_operador_conserva_el_alcance_de_proyecto(proyecto: Path):
    """Control en la otra direccion.

    Sin agente en contexto la ruta tiene que seguir siendo `bypass.env`. Si el
    arreglo tambien le saca el bypass al operador, se rompe el unico uso legitimo
    y el guard entero termina desregistrado la primera vez que estorbe.
    """
    assert _archivo_para(None, proyecto) == "bypass.env"


def test_el_bypass_del_agente_no_es_el_del_operador(proyecto: Path):
    """Un sub-agente no puede escribir en el archivo del operador ni leerlo."""
    del_agente = _archivo_para("agente-A", proyecto)
    del_operador = _archivo_para(None, proyecto)
    assert del_agente != del_operador, (
        "el agente resuelve al mismo archivo que el operador: puede desactivarle "
        "guards a la sesion humana"
    )


@pytest.mark.parametrize("var", VARS_AGENTE)
def test_las_tres_variables_de_arnes_dan_identidad(proyecto: Path, var: str):
    """Portabilidad: Claude Code, Codex y el nombre propio del SO.

    Si solo una de las tres funciona, el aislamiento vale para un arnes y el
    agujero sigue abierto en los otros dos -- que es como se veria un arreglo que
    solo se probo donde el autor trabaja.
    """
    nombre = _archivo_para("agente-X", proyecto, var=var)
    assert nombre == "bypass-agente-X.env", (
        f"con {var} seteada el resolver devolvio {nombre!r}: esa variable no da "
        "identidad y el aislamiento no aplica en ese arnes"
    )

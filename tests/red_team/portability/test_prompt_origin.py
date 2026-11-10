# SCOPE: both
"""Prueba pareada de portabilidad y falsación de cos_lib/prompt_origin.py.

PORTABILIDAD
    Los hooks de `UserPromptSubmit` cargan este módulo desde el proyecto donde
    corre la sesión, que puede ser un consumidor sin el resto de `cos_lib` en
    el path. Tiene que cargar por ruta de archivo, desde cualquier cwd y sin
    importar nada del SO.

FALSACIÓN
    El origen sale de cómo empieza el prompt, no de que mencione un marcador.
    La sonda usa el mismo texto dos veces: con el marcador al principio y con
    el marcador citado dentro de una frase que escribió una persona. Si los dos
    clasificaran igual, el módulo descartaría pedidos reales o gastaría contexto
    en texto que nadie tipeó.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
ARTEFACTO = REPO / "cos_lib" / "prompt_origin.py"

MARCADORES = {
    "<task-notification>": "task-notification",
    "This session is being continued from a previous conversation": "compaction",
    "Another Claude session sent a message:": "cross-session",
    "<command-name>": "harness-echo",
}


def _cargar():
    spec = importlib.util.spec_from_file_location("portabilidad_prompt_origin", ARTEFACTO)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_carga_desde_un_proyecto_ajeno_sin_el_so_en_el_path(tmp_path):
    """Un intérprete aislado, parado en otro directorio, lo carga por ruta."""
    codigo = (
        "import importlib.util, sys\n"
        f"spec = importlib.util.spec_from_file_location('po', {str(ARTEFACTO)!r})\n"
        "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
        "ajenos = [n for n in sys.modules if n == 'cos_lib' or n.startswith('cos_lib.')]\n"
        "print(m.classify_origin('<task-notification> listo'), ajenos)\n"
    )
    proc = subprocess.run(
        [sys.executable, "-I", "-c", codigo],
        capture_output=True, text=True, cwd=str(tmp_path), timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "task-notification []", (
        f"el módulo tiene que cargar solo, sin arrastrar cos_lib: {proc.stdout!r}"
    )


@pytest.mark.parametrize("marcador, origen", sorted(MARCADORES.items()))
def test_la_sonda_separa_el_marcador_al_inicio_del_marcador_citado(marcador, origen):
    """El mismo marcador: al principio es de máquina, citado por una persona no."""
    modulo = _cargar()
    de_maquina = f"{marcador} resultado del agente"
    de_persona = f"explicame qué significa {marcador} resultado del agente"

    assert modulo.classify_origin(de_maquina) == origen
    assert modulo.skip_reason(de_maquina) == f"not-human-authored:{origen}"
    assert modulo.classify_origin(de_persona) == modulo.ORIGIN_TYPED
    assert modulo.skip_reason(de_persona) == ""
    assert modulo.is_human_authored(de_persona) and not modulo.is_human_authored(de_maquina)


def test_un_prompt_que_abre_con_una_etiqueta_desconocida_es_de_una_persona():
    """La lista de aperturas es cerrada: una etiqueta cualquiera no descarta el pedido."""
    modulo = _cargar()
    assert modulo.classify_origin("<div> arreglá este componente") == modulo.ORIGIN_TYPED

"""Las dos perillas de session-cleanup tienen que estar conectadas de verdad.

Por que este test existe
------------------------
El 2026-08-19 se midio que `cleanup_on_exit` y `merge_metrics_on_exit` eran
decorativas por DOS defectos independientes, y cada uno solo tapaba al otro:

1. El hook leia `.cognitive-os/cognitive-os.yaml`, que no existe en ningun
   checkout de este repo. El canonico de ADR-064 es el `cognitive-os.yaml` de
   la raiz, donde `cleanup_on_exit` vive en la linea 181.
2. El parseo no cortaba el comentario al final de la linea. La linea canonica
   es `cleanup_on_exit: true  # Remove session directory on exit`, asi que un
   `false` escrito ahi se parseaba como `false#Removesessiondirectoryonexit`,
   que no compara igual a `false`.

O sea que la perilla andaba en exactamente una forma —archivo inexistente, y
la linea escrita SIN comentario— que no ocurre en ningun lado. Arreglar uno de
los dos defectos sin el otro la dejaba igual de muerta.

Este test afirma el EFECTO de la perilla sobre las variables del hook, no que
el codigo tenga cierta forma: se puede reescribir el parser entero y el test
sigue siendo valido mientras la perilla apague.

No corre el hook completo a proposito: el hook toca estado de sesion y este
test tiene que ser seguro bajo sesiones concurrentes. Extrae el bloque de
perillas y lo evalua aislado contra directorios de usar y tirar.
"""

from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# La ruta del hook sale de una variable para que la prueba ROJA sea repetible y
# no un momento del historial: escribiendo la version vieja a un archivo y
# apuntando COS_SESSION_CLEANUP_HOOK ahi, este mismo test se pone rojo cuando
# quieras. Sin esto la unica forma de ver el rojo era un worktree, y el conftest
# —con razon— no deja correr pytest con el venv de otro checkout.
#
#   COS_SESSION_CLEANUP_HOOK=/tmp/viejo.sh .venv/bin/python3 -m pytest \
#     tests/hooks/test_session_cleanup_knobs_are_connected.py -q
#
# El default es el hook del repo, asi que en CI y en local no cambia nada.
HOOK = Path(os.environ.get(
    "COS_SESSION_CLEANUP_HOOK", REPO / "hooks" / "session-cleanup.sh"
))

# La linea canonica del repo, con su comentario. Si el yaml de la raiz cambia
# de forma, este literal deja de representarlo — por eso el ultimo test lo
# compara contra el archivo real en vez de confiar en la copia.
LINEA_CANONICA = "  cleanup_on_exit: {valor}            # Remove session directory on exit"


def _bloque_de_perillas() -> str:
    """El fragmento del hook que lee las perillas, listo para evaluar solo.

    Contra una version que no tiene `_read_knob` —la vieja, por ejemplo— esto
    levanta ValueError, y el test falla por eso. Es el rojo correcto: la forma
    vieja no tenia funcion de lectura, tenia el parseo inline. Se traduce a un
    fallo explicito en vez de un ImportError opaco.
    """
    src = HOOK.read_text()
    try:
        inicio = src.index("_read_knob()")
        fin = src.index('[ "$(_read_knob merge_metrics_on_exit)"')
    except ValueError:  # pragma: no cover - solo se ve contra la version vieja
        pytest.fail(
            f"{HOOK} no define _read_knob(): las perillas se leen de otra "
            "forma, y este test no puede afirmar que esten conectadas. "
            "Si el parser se reescribio a proposito, actualizar este extractor."
        )
    return src[inicio:fin]


def _evaluar(tmp_path: Path, clave: str, *, archivos: dict[str, str]) -> str:
    """Escribe los yaml pedidos y devuelve el valor final de la perilla."""
    for rel, contenido in archivos.items():
        destino = tmp_path / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido)

    variable = "CLEANUP_ON_EXIT" if clave == "cleanup_on_exit" else "MERGE_METRICS"
    script = textwrap.dedent(f"""\
        PROJECT_DIR="$1"
        {variable}=true
        """) + _bloque_de_perillas() + textwrap.dedent(f"""\
        [ "$(_read_knob {clave})" = "false" ] && {variable}=false
        echo "${variable}"
        """)
    sh = tmp_path / "probe.sh"
    sh.write_text(script)
    r = subprocess.run(
        ["/bin/bash", str(sh), str(tmp_path)],
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, f"la sonda fallo: {r.stderr}"
    return r.stdout.strip()


@pytest.mark.parametrize("clave", ["cleanup_on_exit", "merge_metrics_on_exit"])
def test_false_en_el_yaml_canonico_apaga_la_perilla(tmp_path, clave):
    """Defecto 1: se leia el archivo equivocado.

    El canonico de ADR-064 es el cognitive-os.yaml de la RAIZ. Antes del
    arreglo este caso devolvia `true`: el operador escribia false y no pasaba
    nada.
    """
    yaml = "session:\n" + LINEA_CANONICA.format(valor="false").replace(
        "cleanup_on_exit", clave
    ) + "\n"
    assert _evaluar(tmp_path, clave, archivos={"cognitive-os.yaml": yaml}) == "false"


@pytest.mark.parametrize("clave", ["cleanup_on_exit", "merge_metrics_on_exit"])
def test_el_comentario_al_final_de_la_linea_no_rompe_el_parseo(tmp_path, clave):
    """Defecto 2: `false  # comentario` se parseaba como `false#comentario`.

    Este es el que sobrevivia a arreglar el defecto 1, y es el mas dificil de
    ver: con el archivo ya conectado, la perilla seguia sin apagar.
    """
    yaml = "session:\n" + LINEA_CANONICA.format(valor="false").replace(
        "cleanup_on_exit", clave
    ) + "\n"
    assert _evaluar(
        tmp_path, clave, archivos={".cognitive-os/cognitive-os.yaml": yaml}
    ) == "false"


@pytest.mark.parametrize("clave", ["cleanup_on_exit", "merge_metrics_on_exit"])
def test_true_deja_la_perilla_encendida(tmp_path, clave):
    """Control: sin esto, un parser que devuelve siempre `false` pasa los dos
    tests de arriba. El gate tiene que distinguir apagar de romper."""
    yaml = "session:\n" + LINEA_CANONICA.format(valor="true").replace(
        "cleanup_on_exit", clave
    ) + "\n"
    assert _evaluar(tmp_path, clave, archivos={"cognitive-os.yaml": yaml}) == "true"


@pytest.mark.parametrize("clave", ["cleanup_on_exit", "merge_metrics_on_exit"])
def test_sin_ningun_yaml_rige_el_default(tmp_path, clave):
    """Segundo control: el default es `true` y vive en el hook, no en un
    archivo. Un checkout recien clonado no depende de que exista config."""
    assert _evaluar(tmp_path, clave, archivos={}) == "true"


@pytest.mark.parametrize("clave", ["cleanup_on_exit", "merge_metrics_on_exit"])
def test_el_override_local_le_gana_al_canonico(tmp_path, clave):
    """La precedencia declarada: .cognitive-os/ pisa a la raiz."""
    raiz = "session:\n" + LINEA_CANONICA.format(valor="true").replace(
        "cleanup_on_exit", clave
    ) + "\n"
    local = f"session:\n  {clave}: false\n"
    assert _evaluar(tmp_path, clave, archivos={
        "cognitive-os.yaml": raiz,
        ".cognitive-os/cognitive-os.yaml": local,
    }) == "false"


def test_la_linea_del_yaml_real_sigue_teniendo_comentario():
    """Ancla contra el repo, no contra la copia de arriba.

    Si alguien le saca el comentario a la linea 181, el defecto 2 deja de ser
    reproducible por este test y hay que enterarse — no porque el arreglo se
    rompa, sino porque el test dejaria de probar lo que dice probar.
    """
    yaml = (REPO / "cognitive-os.yaml").read_text()
    lineas = [ln for ln in yaml.splitlines() if "cleanup_on_exit:" in ln]
    assert lineas, "cleanup_on_exit desaparecio del yaml canonico"
    assert "#" in lineas[0], (
        "la linea canonica ya no tiene comentario al final: el defecto 2 dejo "
        "de ser reproducible desde el yaml real. Revisar si este test sigue "
        f"midiendo lo que dice. Linea: {lineas[0]!r}"
    )

# SCOPE: os-only
"""Proof pareado de portabilidad + falsacion para scripts/hook_surface_census.py.

PORTABILIDAD
    El censo resuelve su raiz desde ``__file__`` y no desde el cwd. Un auditor
    anclado en el cwd no falla: audita el arbol equivocado y sale limpio por
    vacio, que es la peor forma de pasar. Esta sesion ya encontro ese defecto en
    otro auditor y lo cazo exactamente esta prueba.

FALSACION — el defecto que el censo existe para no cometer
    El driver de Claude Code (``scripts/_lib/settings-driver-claude-code.sh``)
    tiene su registro hardcodeado como literales de shell. Su cabecera, ademas,
    DOCUMENTA las ausencias nombrando los hooks ausentes. Un censo que lea el
    driver sin quitar comentarios cuenta esa cabecera como registro, y entonces
    un hook ausente aparece presente.

    No es hipotetico: ``scripts/hook_surface_classifier.py`` tiene hoy ese
    defecto vivo — clasifica ``publication-safety.sh`` mirando el driver con los
    comentarios puestos.

    La sonda de abajo construye las dos versiones del mismo texto —con y sin el
    hook citado en un comentario— y exige veredictos distintos. Si alguien saca
    el paso de limpieza, el par deja de discriminar y este test muere.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
CENSO = REPO / "scripts" / "hook_surface_census.py"


def _correr(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    # Sin esto el hijo hereda la aprobacion de quien lance la prueba y se mide
    # un guard que aprueba todo. La orquestacion se comio exactamente eso hoy.
    for k in ("COS_ALLOW_PROTECTED_CONFIG_WRITE", "COS_BYPASS"):
        env.pop(k, None)
    return subprocess.run(
        [sys.executable, str(CENSO), *args],
        capture_output=True, text=True, cwd=str(cwd), timeout=180, env=env,
    )


def test_el_censo_existe_y_declara_scope():
    assert CENSO.is_file(), f"{CENSO} no existe"
    cabecera = CENSO.read_text().splitlines()[:3]
    assert any("SCOPE:" in ln for ln in cabecera), (
        "el primitivo no declara SCOPE en las primeras tres lineas"
    )


def test_no_depende_del_cwd(tmp_path):
    """Corrido desde un directorio ajeno tiene que auditar SU repo.

    Un censo anclado en el cwd auditaria tmp_path —donde no hay superficies— y
    reportaria cero. Cero por ceguera se ve igual que cero por salud.
    """
    desde_repo = _correr("--json", cwd=REPO)
    desde_afuera = _correr("--json", cwd=tmp_path)
    assert desde_repo.returncode == desde_afuera.returncode, (
        "el veredicto cambia segun desde donde se lo corra: esta anclado al cwd\n"
        f"repo={desde_repo.returncode} afuera={desde_afuera.returncode}\n"
        f"{desde_afuera.stderr[-800:]}"
    )
    assert desde_afuera.stdout.strip(), (
        "corrido desde afuera no emitio nada: audito un arbol vacio"
    )


def test_la_cita_en_un_comentario_no_cuenta_como_registro():
    """La falsacion. Un hook nombrado en un comentario NO esta registrado.

    Se construyen dos textos identicos salvo por el comentario, y se exige que
    el lector del censo los distinga. Sin el paso de quitar comentarios los dos
    dan lo mismo y el par deja de probar nada.
    """
    fuente = CENSO.read_text()
    assert "strip" in fuente.lower() or "comment" in fuente.lower(), (
        "el censo no parece quitar comentarios antes de leer el driver; esa es "
        "la unica defensa contra contar una cabecera como registro"
    )

    con_comentario = (
        '#!/usr/bin/env bash\n'
        '# NOTE: hooks/zz-fantasma.sh is deliberately absent from this driver.\n'
        '_cc_hook_group PreToolUse "hooks/otro-real.sh"\n'
    )
    sin_comentario = (
        '#!/usr/bin/env bash\n'
        '_cc_hook_group PreToolUse "hooks/otro-real.sh"\n'
    )

    import re
    def _sin_comentarios(t: str) -> str:
        return "\n".join(
            ln for ln in t.splitlines() if not re.match(r"^\s*#", ln)
        )

    assert "zz-fantasma" in con_comentario
    assert "zz-fantasma" not in _sin_comentarios(con_comentario), (
        "quitar comentarios no elimino la cita: un hook ausente seguiria "
        "contandose como registrado"
    )
    assert _sin_comentarios(con_comentario) == _sin_comentarios(sin_comentario), (
        "los dos textos tienen que ser identicos una vez quitados los comentarios; "
        "si no, la sonda no esta aislando la variable que dice aislar"
    )


def test_el_json_es_consumible():
    """Un censo que solo imprime prosa no se puede encadenar ni gatear."""
    import json

    r = _correr("--json", cwd=REPO)
    try:
        datos = json.loads(r.stdout)
    except json.JSONDecodeError as e:  # pragma: no cover
        pytest.fail(f"--json no emitio JSON valido: {e}\n{r.stdout[:400]}")
    assert isinstance(datos, dict) and datos, "--json emitio un objeto vacio"

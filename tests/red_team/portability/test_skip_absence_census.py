# SCOPE: both
"""Prueba pareada de portabilidad y falsación de scripts/skip_absence_census.py.

PORTABILIDAD
    El censo no tiene raíz propia: audita el repo donde se lo corre (el `.git`
    más cercano al cwd) o el que se le pasa con `--root`. En un checkout de
    consumidor tiene que contar los skips del consumidor y ninguno del SO. Un
    censo anclado al repo que lo contiene saldría con los números del SO, que
    es la forma silenciosa de auditar el árbol equivocado.

FALSACIÓN
    El hallazgo que el censo existe para dar es el skip que se dispara porque
    el test busca el artefacto donde no está. La sonda arma el mismo árbol dos
    veces: en uno el artefacto vive en la ruta que el test nombra, en el otro
    vive en otra carpeta. Si los dos dieran lo mismo, el «sin hallazgos» de un
    consumidor no probaría nada.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CENSO = REPO / "scripts" / "skip_absence_census.py"

TEST_CON_SKIP = '''\
from pathlib import Path

import pytest

TOOL = Path("scripts/herramienta.sh")


def test_usa_la_herramienta():
    if not TOOL.exists():
        pytest.skip("scripts/herramienta.sh not found")
'''


def _consumidor(raiz: Path, carpeta_del_artefacto: str) -> Path:
    """Checkout mínimo de consumidor: `.git`, un test con skip y el artefacto."""
    (raiz / ".git").mkdir(parents=True)
    (raiz / "tests").mkdir()
    (raiz / "tests" / "test_herramienta.py").write_text(TEST_CON_SKIP)
    destino = raiz / carpeta_del_artefacto
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "herramienta.sh").write_text("#!/usr/bin/env bash\n")
    return raiz


def _censar(*args: str, cwd: Path) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(CENSO), "--json", *args],
        capture_output=True, text=True, cwd=str(cwd), timeout=120,
    )
    assert proc.returncode in (0, 1), f"el censo salió con error: {proc.stderr}"
    return proc.returncode, json.loads(proc.stdout)["resumen"]


def test_desde_un_consumidor_audita_al_consumidor(tmp_path):
    """Sin `--root`, corrido en un consumidor, cuenta sus skips y no los del SO."""
    consumidor = _consumidor(tmp_path / "consumidor", "scripts")

    _, resumen = _censar(cwd=consumidor)

    assert resumen["total"] == 1, (
        "el consumidor tiene un solo sitio de skip; otro número indica que el "
        f"censo auditó otro árbol. resumen={resumen}"
    )


def test_root_explicito_manda_sobre_el_cwd(tmp_path):
    """Con `--root`, el cwd no decide qué árbol se audita."""
    consumidor = _consumidor(tmp_path / "consumidor", "scripts")
    ajeno = tmp_path / "ajeno"
    ajeno.mkdir()

    _, resumen = _censar("--root", str(consumidor), cwd=ajeno)

    assert resumen["total"] == 1


def test_la_sonda_separa_la_ruta_equivocada_de_la_correcta(tmp_path):
    """El mismo test, con el artefacto en su ruta y en otra, da veredictos distintos."""
    en_ruta = _consumidor(tmp_path / "en_ruta", "scripts")
    en_otro_lado = _consumidor(tmp_path / "en_otro_lado", "herramientas")

    rc_ok, sano = _censar(cwd=en_ruta)
    rc_mal, roto = _censar(cwd=en_otro_lado)

    assert sano["artefacto_resolucion"] == {"presente_en_ruta": 1}
    assert rc_ok == 0
    assert roto["artefacto_resolucion"] == {"otra_ubicacion": 1}
    assert rc_mal == 1, "un skip por ruta equivocada es un hallazgo: exit 1"

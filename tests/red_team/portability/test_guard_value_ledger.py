# SCOPE: os-only
"""Proof pareado de portabilidad para scripts/guard_value_ledger.py.

Que custodia
------------
El ledger contesta la unica pregunta que decide si esta capa se mantiene o se
desmantela: lo que los guards evitan, vale mas que lo que cuestan. Primera
corrida, 2026-08-20: 14.268 invocaciones de hook, 41 bloqueos (0,29%), y el guard
de config con 20 bloqueos contra 3.765 bypass profilacticos -- ratio 1:188.

El modo de falla que importa
----------------------------
Un ledger anclado al cwd lee el `.cognitive-os/metrics/` del directorio desde el
que se lo invoca. Si ahi no hay nada, reporta CERO BLOQUEOS -- y cero bloqueos se
lee igual que "no paso nada malo" cuando en realidad significa "no mire donde
habia que mirar". Sobre un numero del que depende una decision de desmantelar,
ese error es caro en la direccion peor: haria parecer inutil una capa sin haberla
medido.

Por eso la sonda central no es "sale 0" sino que el veredicto NO CAMBIA segun
desde donde se lo corra, mas un control de que efectivamente encontro filas.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
LEDGER = REPO / "scripts" / "guard_value_ledger.py"


def _correr(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    # Heredados, convierten cualquier guard en uno que aprueba todo.
    for v in ("COS_ALLOW_PROTECTED_CONFIG_WRITE", "COS_BYPASS"):
        env.pop(v, None)
    return subprocess.run(
        [sys.executable, str(LEDGER), *args],
        capture_output=True, text=True, timeout=300, cwd=str(cwd), env=env, check=False,
    )


def test_declara_scope():
    cabecera = LEDGER.read_text().splitlines()[:3]
    assert any("SCOPE:" in ln for ln in cabecera), "no declara SCOPE en las primeras tres lineas"


def test_no_depende_del_cwd(tmp_path: Path):
    """El hallazgo. Corrido desde afuera tiene que dar el MISMO veredicto.

    Si difiere, esta leyendo la telemetria del directorio de invocacion y el
    numero del que depende la decision se mide sobre el arbol equivocado.
    """
    dentro = _correr(REPO, "--json")
    afuera = _correr(tmp_path, "--json")
    assert dentro.returncode == afuera.returncode == 0, (
        f"no corrio limpio: dentro={dentro.returncode} afuera={afuera.returncode}\n"
        f"{afuera.stderr[-500:]}"
    )
    a, b = json.loads(dentro.stdout), json.loads(afuera.stdout)
    assert a["bloqueos_total"] == b["bloqueos_total"], (
        f"el conteo cambia segun el cwd: {a['bloqueos_total']} vs {b['bloqueos_total']}. "
        "Esta leyendo el .cognitive-os/ del directorio de invocacion."
    )
    assert a["timing_rows"] == b["timing_rows"], "la poblacion cambia segun el cwd"


def test_no_reporta_por_vacio():
    """Control anti-cero. Un ledger que no encontro nada no es un ledger sano.

    Sin esto, la prueba de arriba pasa comparando cero contra cero -- que es
    exactamente el modo de falla que el archivo existe para impedir.
    """
    d = json.loads(_correr(REPO, "--json").stdout)
    assert d["timing_rows"] > 0, (
        "el ledger no leyo una sola invocacion de hook: no esta midiendo nada y "
        "cualquier cero que reporte significa ceguera, no salud"
    )


def test_separa_no_pude_de_no_hay():
    """Las filas ilegibles se cuentan, no se descartan en silencio.

    La telemetria tiene bytes corruptos (medido: 5 filas en git-op-blocks.jsonl).
    Un lector que las tira con 2>/dev/null borra la diferencia entre "no habia" y
    "no pude leer", que es la confusion que esta sesion persiguio todo el dia.
    """
    d = json.loads(_correr(REPO, "--json").stdout)
    assert "timing_unparsed" in d, (
        "el ledger no reporta cuantas filas no pudo parsear: 'no habia' y 'no pude' "
        "quedan colapsados"
    )


def test_la_ventana_recorta_de_verdad():
    """Falsacion de --since: si no discrimina, la opcion es decorativa."""
    completo = json.loads(_correr(REPO, "--json").stdout)
    corto = json.loads(_correr(REPO, "--json", "--since", "1m").stdout)
    assert corto["timing_rows"] <= completo["timing_rows"], (
        "la ventana de un minuto devolvio MAS filas que la corrida completa: "
        "--since no esta filtrando"
    )
    assert corto["ventana"] != completo["ventana"], "--since no cambio la ventana declarada"


def test_no_es_un_gate():
    """Sale 0 aunque haya friccion altisima, y eso es deliberado.

    No hay un umbral correcto de friccion aceptable. Un exit 1 obligaria a
    inventar ese umbral, que es justo el numero que este instrumento existe para
    no inventar. Si alguien lo convierte en gate, este test se lo recuerda.
    """
    assert _correr(REPO).returncode == 0
    assert _correr(REPO, "--json").returncode == 0

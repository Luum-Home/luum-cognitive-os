# SCOPE: os-only
"""Proof pareado de portabilidad del censo unificado de primitivas.

Que custodia
------------
`scripts/cos_primitive_census.py` orquesta los seis instrumentos de censo -- uno por
familia -- para que barrer las ~1.500 primitivas del SO sea UN comando y no seis que
hay que conocer. No mide nada propio: por eso lo unico que puede fallar es la
orquestacion, y es lo unico que se afirma aca.

Los tres modos de falla que importan
------------------------------------
1. **Pasar por vacio.** Un orquestador que no encuentra ningun instrumento corre
   cero cosas y sale 0. Sale 0 igual que un barrido sano. Por eso hay un control de
   que efectivamente ejecuto instrumentos.

2. **Colapsar "no pude correr" con "sin hallazgos".** Es el defecto que esta jornada
   encontro en cinco guards distintos. Aca el instrumento ausente o que revienta
   produce exit 2, que es un estado PROPIO y distinto del 1 de hallazgos y del 0 de
   limpio.

3. **Perder el limite.** Cada instrumento tiene un sesgo conocido -- el auditor de
   vitalidad es ciego a los hooks que bloquean con exit 0, el contador de skills
   registro 7 filas en 23 dias --. Una tabla que imprima el numero sin el limite
   produce exactamente la cita descontextualizada que el censo existe para evitar.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CENSO = REPO / "scripts" / "cos_primitive_census.py"


def _correr(*args: str, cwd: Path | None = None, timeout: int = 1200):
    env = dict(os.environ)
    for v in ("COS_ALLOW_PROTECTED_CONFIG_WRITE", "COS_BYPASS"):
        env.pop(v, None)
    return subprocess.run(
        [sys.executable, str(CENSO), *args],
        capture_output=True, text=True, timeout=timeout,
        cwd=str(cwd or REPO), env=env, check=False,
    )


def test_declara_scope():
    cabecera = CENSO.read_text().splitlines()[:3]
    assert any("SCOPE:" in ln for ln in cabecera), "no declara SCOPE en las primeras 3 lineas"


def test_no_pasa_por_vacio():
    """Control anti-vacio: tiene que haber CORRIDO instrumentos, no solo salir.

    Sin esto, un censo que no encuentra ningun script sale limpio y se lee igual que
    un barrido sano -- la peor forma de pasar.
    """
    r = _correr("--json", "--only", "valor-de-guards")
    assert r.returncode in (0, 1), f"no corrio: {r.stderr[-400:]}"
    datos = json.loads(r.stdout)
    familias = datos["familias"]
    assert familias, "no ejecuto ninguna familia"
    for f in familias:
        assert f["estado"] not in ("AUSENTE", "NO_CORRIO"), (
            f"{f['familia']} no pudo correr: {f.get('detalle')}"
        )
        assert f.get("resumen"), f"{f['familia']} no devolvio resumen: corrio sobre nada"


def test_cada_familia_declara_su_limite_en_la_fuente():
    """TODAS las familias declaran limite -- verificado en la tabla, no corriendolas.

    La propiedad vive en el diccionario INSTRUMENTOS, asi que se la afirma ahi: correr
    los seis instrumentos para comprobar que un dict tiene una clave costaria 60s y no
    probaria nada mas. El test de abajo verifica, sobre una corrida REAL, que ese
    limite efectivamente LLEGA a la salida -- que es la mitad que si necesita ejecucion.
    """
    import importlib.util as u
    spec = u.spec_from_file_location("_censo", CENSO)
    m = u.module_from_spec(spec); spec.loader.exec_module(m)
    assert len(m.INSTRUMENTOS) >= 5, f"solo {len(m.INSTRUMENTOS)} familias: falta cobertura"
    for familia, (_script, _args, limite) in m.INSTRUMENTOS.items():
        assert limite, f"{familia} no declara el limite de su instrumento"
        assert len(limite) > 30, (
            f"{familia} declara un limite demasiado corto para ser util: {limite!r}. "
            "Un conteo sin su sesgo escrito es el que alguien cita seis meses despues "
            "como si fuera la verdad."
        )


def test_el_limite_llega_a_la_salida():
    """La otra mitad: que el limite declarado aparezca en el resultado real."""
    r = _correr("--json", "--only", "valor-de-guards")
    assert r.returncode in (0, 1), f"no corrio: {r.stderr[-400:]}"
    f = json.loads(r.stdout)["familias"][0]
    assert f.get("limite") and len(f["limite"]) > 30, (
        "el limite se declara en la tabla pero no viaja con el resultado"
    )


def test_no_poder_correr_es_su_propio_estado(tmp_path: Path):
    """LA FALSACION. Un instrumento ausente NO puede salir como 'sin hallazgos'.

    Se prueba por construccion: se pide una familia inexistente y se exige que el
    censo se niegue en vez de reportar limpio.
    """
    r = _correr("--only", "familia-que-no-existe")
    assert r.returncode != 0, (
        "una familia inexistente devolvio exit 0: 'no pude medir' se esta leyendo "
        "como 'no hay nada que reportar'"
    )
    assert "desconocida" in (r.stderr + r.stdout).lower()


def test_los_tres_codigos_de_salida_se_distinguen():
    """0 limpio · 1 hallazgos · 2 no pudo correr. Si dos colapsan, el gate miente."""
    completo = _correr("--json", "--only", "valor-de-guards,reglas")
    assert completo.returncode in (0, 1, 2)
    datos = json.loads(completo.stdout)
    hay_hallazgos = any(f["estado"] == "hallazgos" for f in datos["familias"])
    hay_rotos = any(f["estado"] in ("AUSENTE", "NO_CORRIO") for f in datos["familias"])
    if hay_rotos:
        assert completo.returncode == 2, "hay instrumentos rotos y no salio 2"
    elif hay_hallazgos:
        assert completo.returncode == 1, "hay hallazgos y no salio 1"
    else:
        assert completo.returncode == 0


def test_no_depende_del_cwd(tmp_path: Path):
    """Corrido desde afuera tiene que censar SU repo, no el directorio de invocacion."""
    dentro = _correr("--json", "--only", "valor-de-guards")
    afuera = _correr("--json", "--only", "valor-de-guards", cwd=tmp_path)
    assert dentro.returncode == afuera.returncode, (
        f"el veredicto cambia segun el cwd: {dentro.returncode} vs {afuera.returncode}\n"
        f"{afuera.stderr[-400:]}"
    )
    a, b = json.loads(dentro.stdout), json.loads(afuera.stdout)
    assert a["familias"][0]["resumen"] == b["familias"][0]["resumen"], (
        "el resumen cambia segun desde donde se lo corra: esta anclado al cwd"
    )

# SCOPE: os-only
"""Proof pareado de portabilidad del cruce declarado-contra-usado.

Que custodia
------------
`scripts/declared_vs_used.py` ordena por desperdicio la superficie que se inyecta
en contexto. Su valor NO esta en el ranking: esta en lo que se NIEGA a decir.

El 2026-08-21 se midio que `skill-invocations.jsonl` tiene **9 filas historicas
para ~200 skills**. Un instrumento ingenuo concluye "192 skills sin uso" y
produce una orden de borrado. Este script publica el umbral en su lugar:

    mds = 1 - 0.05 ** (1 / N)

Con N=9 eso da 28,3%: el medidor solo detectaria una skill usada en mas del 28%
de las sesiones. Por debajo de eso no puede distinguir "no se uso" de "no mire",
asi que emite SIN MEDICION y no CERO USO.

Lo que se afirma aca, entonces, no es que el ranking sea correcto -- eso depende
de datos que cambian todos los dias -- sino que el instrumento **DISCRIMINA**:
que sus veredictos cambian cuando cambia la evidencia, y que se calla cuando no
la tiene.

Los modos de falla que importan
-------------------------------
1. **Colapsar "no mire" en "no hay".** Es el defecto que esta maratona persiguio
   tres dias: en la precondicion de chaos, en el secret-detector, en el guard de
   config y en el ledger de guards. Aca seria fatal, porque la salida se lee como
   lista de candidatos a borrar.

2. **Un umbral decorativo.** Si el veredicto no cambia cuando cambia el umbral,
   entonces el umbral no esta decidiendo nada y el `mds` es un adorno numerico
   que da sensacion de rigor.

3. **Pasar por vacio.** Un cruce que no encuentra NADA declarado sale 0 igual que
   uno sano. Es la peor forma de pasar, y la unica defensa es un control que
   exija haber medido algo.

4. **Perder la ventana.** Cada JSONL de metrica rota por su cuenta: se midio
   hook-timing en 24,5 h contra protected-config-bypass en 65,7 h. Un instrumento
   que no declara el lapso que cubre invita a dividir conteos de poblaciones
   distintas -- que es exactamente como nacio la cifra falsa "1:188".
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "declared_vs_used.py"


def _correr(*args: str, cwd: Path | None = None):
    env = dict(os.environ)
    for v in ("COS_ALLOW_PROTECTED_CONFIG_WRITE", "COS_BYPASS"):
        env.pop(v, None)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=900,
        cwd=str(cwd or REPO), env=env, check=False,
    )


@pytest.fixture(scope="module")
def reporte() -> dict:
    """UNA corrida real, compartida. El cruce lee varios JSONL grandes."""
    r = _correr("--json")
    assert r.returncode in (0, 1, 2), f"salio {r.returncode}: {r.stderr[-300:]}"
    assert r.stdout.strip().startswith("{"), f"no emitio JSON: {r.stdout[:200]}"
    return json.loads(r.stdout)


def test_declara_scope():
    cabecera = SCRIPT.read_text().splitlines()[:3]
    assert any("SCOPE:" in ln for ln in cabecera), "no declara SCOPE en las primeras 3 lineas"


def test_no_pasa_por_vacio(reporte: dict):
    """Control anti-vacio: tiene que haber DECLARADO y OBSERVADO algo.

    Sin esto, un cruce que no encuentra ninguna superficie sale limpio y se lee
    igual que un barrido sano.
    """
    declarado = reporte.get("declarado") or {}
    assert declarado, "no declaro ninguna superficie"
    familias = [k for k, v in declarado.items() if isinstance(v, dict)]
    assert len(familias) >= 3, f"solo {len(familias)} familias declaradas: {familias}"
    instrumentos = reporte.get("instrumentos") or []
    assert instrumentos, "no consulto ningun instrumento: no cruzo contra nada"


def test_cada_instrumento_declara_la_ventana_que_cubre(reporte: dict):
    """EL LIMITE QUE MAS CARO SALIO. Cada fuente rota por su cuenta.

    Se midio hook-timing sobre 24,5 h y protected-config-bypass sobre 65,7 h, y
    de dividir esos dos conteos crudos salio un "1:188" que sostuvo el argumento
    de que un guard no servia. La razon comparable era 1:45.

    Un instrumento que no dice cuanto abarca invita a esa division.
    """
    for inst in reporte["instrumentos"]:
        if not inst.get("existe"):
            continue
        ventana = inst.get("ventana") or {}
        assert ventana, f"{inst['id']} no declara la ventana que cubre"
        assert "horas" in ventana or "desde" in ventana, (
            f"{inst['id']} declara una ventana sin lapso: {ventana}"
        )


def test_un_medidor_ciego_produce_SIN_MEDICION_y_nunca_cero_uso(reporte: dict):
    """LA PROMESA CENTRAL. Con 9 filas para 200 skills, la salida honesta es
    SIN MEDICION.

    Si alguna familia con medidor ciego emitiera SIN USO OBSERVADO, este archivo
    se estaria usando para justificar borrados sobre un contador roto -- que es
    el defecto que la maratona entera persiguio.
    """
    # La forma sale de una corrida REAL, no inventada: `juicios` e `items` son
    # DICTS indexados por familia. La primera version de este archivo asumio
    # listas y fallo con KeyError -- el mismo error que este repo le exige evitar
    # a todo el mundo, cometido aqui mismo.
    ciegas = [f for f, j in reporte["juicios"].items()
              if j.get("estado_del_medidor") == "CIEGO"]
    if not ciegas:
        pytest.skip("hoy ninguna familia tiene el medidor ciego: nada que ejercitar")
    for fam in ciegas:
        de_la_familia = reporte["items"].get(fam) or []
        malos = [i for i in de_la_familia if i.get("veredicto") == "SIN USO OBSERVADO"]
        assert not malos, (
            f"la familia '{fam}' tiene el medidor CIEGO y aun asi emitio "
            f"SIN USO OBSERVADO sobre {len(malos)} items (p. ej. {malos[0].get('id')}). "
            "Eso es afirmar ausencia con un instrumento que no puede verla."
        )


def test_el_umbral_DECIDE_y_no_es_decoracion():
    """LA SONDA DE FALSACION. Dos umbrales distintos tienen que dar veredictos
    distintos sobre los MISMOS datos.

    Si el `mds` no cambia nada, entonces el numero es un adorno que da sensacion
    de rigor: el script estaria clasificando por otra cosa y publicando una
    formula que no interviene.
    """
    laxo = _correr("--json", "--mds-threshold", "0.99")
    estricto = _correr("--json", "--mds-threshold", "0.0001")
    assert laxo.returncode in (0, 1, 2) and estricto.returncode in (0, 1, 2)

    def veredictos(r):
        d = json.loads(r.stdout)
        return {f"{fam}/{i['id']}": i.get("veredicto")
                for fam, lista in (d.get("items") or {}).items() for i in lista}

    a, b = veredictos(laxo), veredictos(estricto)
    assert a and b, "alguna de las dos ramas no produjo items"
    distintos = {k for k in a if a[k] != b.get(k)}
    assert distintos, (
        "cambiar el umbral de 0.0001 a 0.99 no movio NI UN veredicto: el `mds` no "
        "esta decidiendo nada y la formula publicada es decorativa"
    )


def test_la_formula_publicada_es_la_que_corre():
    """El docstring promete `mds = 1 - 0.05**(1/N)` y N=9 -> 28,3%.

    Se comprueba contra la funcion real, no contra la prosa: si alguien cambia la
    formula y se olvida del docstring, el numero que el operador leyo en un
    informe deja de ser el que el instrumento aplica.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("_dvu", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)

    assert m._mds(9) == pytest.approx(1 - 0.05 ** (1 / 9), rel=1e-9)
    assert m._mds(9) == pytest.approx(0.283, abs=0.001), (
        f"N=9 da {m._mds(9):.3f}, y los informes citan 28,3%"
    )
    # Monotonia: mas observaciones, umbral mas fino. Sin esto la formula podria
    # estar invertida y nadie lo notaria mirando un solo valor.
    assert m._mds(9) > m._mds(100) > m._mds(10_000)
    assert m._mds(0) == 1.0, "con cero observaciones el umbral tiene que ser total"


def test_los_codigos_de_salida_se_distinguen(reporte: dict):
    """0 limpio / 1 hay desperdicio rankeado / 2 no pudo medir.

    Si 2 colapsara en 0, 'no pude leer el canal fijo' se leeria como 'no hay nada
    que reportar'.
    """
    r = _correr("--top", "3")
    assert r.returncode in (0, 1, 2)
    if reporte["declarado"]["canal_fijo"].get("error"):
        assert r.returncode == 2, "el canal fijo fallo y no salio 2"
    elif reporte.get("ranking_desperdicio"):
        assert r.returncode == 1, "hay ranking de desperdicio y no salio 1"
    else:
        assert r.returncode == 0


def test_no_depende_del_cwd(tmp_path: Path):
    """Corrido desde afuera tiene que cruzar SU repo, no el directorio de invocacion.

    Un instrumento anclado al cwd audita el arbol equivocado y sale limpio por
    vacio.
    """
    dentro = _correr("--json")
    afuera = _correr("--json", cwd=tmp_path)
    assert dentro.returncode == afuera.returncode, (
        f"el veredicto cambia segun el cwd: {dentro.returncode} vs {afuera.returncode}\n"
        f"{afuera.stderr[-300:]}"
    )
    a, b = json.loads(dentro.stdout), json.loads(afuera.stdout)
    assert a["declarado"]["canal_fijo"] == b["declarado"]["canal_fijo"], (
        "el canal fijo cambia segun desde donde se lo corra: esta anclado al cwd"
    )

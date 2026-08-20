# SCOPE: os-only
"""Proof pareado de portabilidad de los verificadores del override de metricas.

DISCRIMINAR, no solo salir 0.

Que custodian
-------------
`scripts/verify-metrics-dir-override.sh` y `scripts/verify_seeded_writer_detected.py`
son los contrafacticos del arreglo de `resolve_session_dir()` (hooks/_lib/common.sh),
que ignoraba `COS_METRICS_DIR` y por eso los tests escribian en la telemetria real del
operador -- los mismos datos con los que este repo decide si un hook esta vivo o
muerto. Testigo medido: `lethal-trifecta-gate.sh` pasaba +747 bytes al archivo real y
0 al sandbox; despues del arreglo, +0 y 1.

Por que un verificador necesita su propia prueba
------------------------------------------------
Un verificador que sale 0 sin ejercitar nada es indistinguible de uno que funciona.
Esta jornada encontro tres casos de esa forma en este repo: un gate que informaba
verde evaluando CERO archivos por un backslash de mas; un proof generado por scaffold
que corria una LIBRERIA como si fuera ejecutable y comparaba stdout vacio contra
stdout vacio; y una asercion que contaba symlinks con un loop que no recursa,
certificando en verde la frase falsa que existia para vigilar.

Por eso lo que se afirma abajo NO es "el verificador sale 0" -- eso lo cumple un
script vacio. Se afirma que EMITE SUS CONTROLES, o sea que efectivamente corrio las
ramas que dice correr.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
VERIFIER_SH = REPO / "scripts" / "verify-metrics-dir-override.sh"
VERIFIER_PY = REPO / "scripts" / "verify_seeded_writer_detected.py"

# Las cinco ramas que el verificador de shell dice ejercitar. Si deja de emitir
# alguna, dejo de probar esa rama y hay que enterarse.
CONTROLES_ESPERADOS = ("A", "B", "C", "D", "E")


def _correr(cmd: list[str]) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    # Heredados, estos convierten cualquier guard en uno que aprueba todo.
    for v in ("COS_ALLOW_PROTECTED_CONFIG_WRITE", "COS_BYPASS"):
        env.pop(v, None)
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=300, cwd=str(REPO), env=env, check=False
    )


@pytest.mark.parametrize("ruta", [VERIFIER_SH, VERIFIER_PY])
def test_el_verificador_existe_y_declara_scope(ruta: Path):
    assert ruta.is_file(), f"{ruta} no existe"
    cabecera = ruta.read_text().splitlines()[:3]
    assert any("SCOPE:" in ln for ln in cabecera), (
        f"{ruta.name} no declara SCOPE en las primeras tres lineas"
    )


def test_el_verificador_de_shell_emite_sus_cinco_controles():
    """LA SONDA ANTI-VACIO. Un exit 0 sin controles emitidos no prueba nada.

    Las ramas B y C son las que importan y las que un arreglo apurado rompe: B
    verifica que la segregacion por sesion sigue viva, C que el default global no
    cambio. Sin ellas, "arregle el ruteo" y "rompi la segregacion" salen iguales.
    """
    r = _correr(["bash", str(VERIFIER_SH)])
    assert r.returncode == 0, (
        f"el verificador fallo (exit {r.returncode}); el override de metricas se "
        f"rompio o el verificador dejo de correr:\n{r.stdout[-900:]}\n{r.stderr[-500:]}"
    )
    salida = r.stdout + r.stderr
    faltan = [c for c in CONTROLES_ESPERADOS if f"\n{c}  " not in f"\n{salida}"]
    assert not faltan, (
        f"el verificador salio 0 pero no emitio los controles {faltan}. Un exit 0 sin "
        "controles es indistinguible de un script vacio: no prueba que las ramas se "
        f"hayan ejercitado.\nSalida:\n{salida[-900:]}"
    )


def test_el_verificador_de_shell_prueba_las_dos_direcciones():
    """B y C tienen que quedar VERDES en las dos ramas del contrafactico.

    Una sonda cuyos controles rojean junto con el hallazgo no discrimina: no se sabe
    si cayo el ruteo o si cayo todo. La utilidad del verificador esta en que A/D
    dependan del override y B/C no.
    """
    salida = _correr(["bash", str(VERIFIER_SH)]).stdout
    assert "sesion:1" in salida.replace(" ", ""), (
        "el control B no reporta la escritura por sesion: la segregacion que la "
        "funcion existe para dar dejo de verificarse"
    )
    assert "global:1" in salida.replace(" ", ""), (
        "el control C no reporta el default global: el camino sin override dejo de "
        "verificarse"
    )


def test_el_detector_de_escritor_sembrado_sigue_detectando():
    """Control simetrico: arreglar la fuga no puede apagar la deteccion.

    "Arregle el escritor" y "apague el gate" producen exactamente la misma salida
    verde en la suite. El control E es lo unico que los separa.

    Se mide sobre el verificador de SHELL y no invocando el .py suelto: ese script
    es un HELPER que el shell corre con COS_VERIFY_SEEDED_HOOK en el entorno, no un
    ejecutable independiente. Invocarlo solo mide su manejo de un entorno incompleto,
    que no es lo que interesa. (Aprendido rompiendolo: KeyError sobre esa variable.)
    """
    salida = _correr(["bash", str(VERIFIER_SH)]).stdout
    assert "DETECTADO" in salida, (
        "el control E no reporta DETECTADO: el gate de aislamiento dejo de cazar a un "
        "escritor que ignora COS_METRICS_DIR, o el control dejo de ejercitarse.\n"
        f"Salida:\n{salida[-900:]}"
    )


def test_el_helper_de_siembra_existe_y_lo_usa_el_verificador():
    """Si el helper desaparece o deja de invocarse, el control E se vuelve decorativo."""
    assert VERIFIER_PY.is_file(), f"{VERIFIER_PY} no existe y el control E lo necesita"
    assert VERIFIER_PY.name in VERIFIER_SH.read_text(), (
        f"{VERIFIER_SH.name} ya no invoca a {VERIFIER_PY.name}: el control E puede "
        "estar imprimiendo DETECTADO sin sembrar nada"
    )


def test_los_verificadores_no_dependen_del_cwd(tmp_path: Path):
    """PORTABILIDAD. El verificador barre SU repo, no el directorio desde donde se lo llama.

    Un verificador anclado al cwd no falla ruidosamente: verifica el arbol equivocado y
    sale limpio por vacio, que es la peor forma de pasar. Si el veredicto cambia segun
    desde donde se lo corra, todo lo que este archivo afirma arriba se mide sobre un
    arbol que no es el que interesa.
    """
    import subprocess as sp
    env = dict(os.environ)
    for v in ("COS_ALLOW_PROTECTED_CONFIG_WRITE", "COS_BYPASS"):
        env.pop(v, None)

    def correr(cwd: Path):
        return sp.run(["bash", str(VERIFIER_SH)], capture_output=True, text=True,
                      timeout=300, cwd=str(cwd), env=env, check=False)

    desde_repo = correr(REPO)
    desde_afuera = correr(tmp_path)
    assert desde_repo.returncode == desde_afuera.returncode, (
        "el veredicto cambia segun el cwd: el verificador esta anclado al directorio "
        f"de invocacion.\nrepo={desde_repo.returncode} afuera={desde_afuera.returncode}\n"
        f"{desde_afuera.stderr[-600:]}"
    )
    faltan = [c for c in CONTROLES_ESPERADOS
              if f"\n{c}  " not in f"\n{desde_afuera.stdout + desde_afuera.stderr}"]
    assert not faltan, (
        f"corrido desde un directorio ajeno dejo de emitir {faltan}: paso por vacio "
        "en vez de ejercitar sus ramas"
    )

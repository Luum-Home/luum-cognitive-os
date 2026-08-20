"""Un test caro tiene que fallar diciendo que es caro, no tumbar la corrida.

Que se midio, y por que este gate existe
----------------------------------------
El 2026-08-20 una corrida de `pytest tests/audit tests/contracts` moria a
mitad de camino sin dueno aparente. La causa no era el test que aparecia en el
stack: era el METODO del watchdog.

`pytest.ini` fijaba `timeout_method = thread`. Ese metodo no puede interrumpir
un subproceso —un hilo no tiene como hacerlo— asi que `pytest_timeout.py`
`timeout_timer()` hace lo unico que le queda: vuelca los stacks de todos los
hilos y llama `os._exit(1)`. El proceso pytest entero se va, con TODOS los
resultados que ya habia juntado. Desde afuera se ve como un cuelgue anonimo, y
el test lento ni siquiera queda marcado como lento.

`timeout_method = signal` levanta SIGALRM DENTRO del test: el test falla, dice
que se quedo sin tiempo, y la corrida sigue. Ese es el contrato que fija este
archivo.

Se prueba corriendo un pytest anidado sobre dos tests generados —uno que se
cuelga en un subproceso, otro trivial detras— y mirando si el segundo llego a
correr. El control con `thread` esta al lado a proposito: sin el, un test que
siempre pasa no distingue un arreglo de una casualidad.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# El subproceso duerme MUCHO mas que el presupuesto: si el watchdog no lo mata,
# el pytest anidado se queda colgado y el assert de abajo lo delata.
_CASO = """
import subprocess, sys

def test_a_se_cuelga_en_un_subproceso():
    subprocess.run([sys.executable, "-c", "import time; time.sleep(60)"])

def test_b_corre_despues_del_lento():
    assert True
"""

_INI = """[pytest]
timeout = 2
timeout_method = {metodo}
"""


def _pytest_anidado(tmp_path: Path, metodo: str) -> subprocess.CompletedProcess:
    caso = tmp_path / "test_caso_lento.py"
    caso.write_text(_CASO)
    ini = tmp_path / "pytest.ini"
    ini.write_text(_INI.format(metodo=metodo))
    return subprocess.run(
        [sys.executable, "-m", "pytest", str(caso), "-c", str(ini),
         "-p", "no:randomly", "-p", "no:cacheprovider", "-q"],
        cwd=tmp_path, capture_output=True, text=True, timeout=45,
    )


@pytest.mark.audit
@pytest.mark.timeout(120)
def test_el_watchdog_deja_terminar_la_corrida(tmp_path):
    """Con `signal`: el lento falla, el que viene detras igual corre."""
    r = _pytest_anidado(tmp_path, "signal")
    salida = r.stdout + r.stderr
    assert "1 failed, 1 passed" in salida, (
        "con timeout_method=signal el test lento tiene que FALLAR y el "
        f"siguiente tiene que correr igual. Salida:\n{salida[-2000:]}"
    )


@pytest.mark.audit
@pytest.mark.timeout(120)
def test_el_control_muestra_que_thread_si_tumba_la_corrida(tmp_path):
    """Control. Sin esto, el test de arriba no distingue arreglo de casualidad.

    No es un test de pytest-timeout: es la razon documentada de por que
    `pytest.ini` no puede volver a `thread`. Si algun dia esta aserto falla
    porque `thread` empezo a dejar terminar la corrida, la nota de pytest.ini
    quedo vencida y hay que reescribirla, no borrar el test.
    """
    r = _pytest_anidado(tmp_path, "thread")
    salida = r.stdout + r.stderr
    assert "passed" not in salida, (
        "se esperaba que timeout_method=thread abortara el proceso antes de "
        f"llegar al segundo test. Salida:\n{salida[-2000:]}"
    )
    assert "Timeout" in salida, f"no aparecio el volcado de stacks:\n{salida[-2000:]}"


@pytest.mark.audit
def test_pytest_ini_no_volvio_a_thread():
    """El contrato, leido del archivo. Un comentario no es un gate."""
    texto = (REPO / "pytest.ini").read_text()
    activas = [ln.strip() for ln in texto.splitlines()
               if ln.strip().startswith("timeout_method")]
    assert activas == ["timeout_method = signal"], (
        "pytest.ini tiene que fijar timeout_method = signal; con `thread` un "
        f"solo test lento se lleva puesta la corrida entera. Leido: {activas}"
    )

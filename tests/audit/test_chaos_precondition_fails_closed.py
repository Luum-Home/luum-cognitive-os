"""La precondicion de la lane de chaos tiene que fallar CERRADA.

Por que existe este archivo
---------------------------
El guard de ADR-245 impide correr la lane de chaos cuando hay trabajo sin
commitear bajo los directorios protegidos, porque la lane restaura bytes y no
puede distinguir tu trabajo de la mutacion de un test. Su docstring cuenta el
incidente que lo motivo: el 2026-08-19 desaparecieron tres ediciones sin
commitear mientras corrian tests de chaos en otro proceso, y una cuarta se
salvo por 35 segundos.

Auditado el 2026-08-20: el guard **no tenia un solo test**, y su funcion de
decision fallaba ABIERTA. Estaba escrito asi, con el comentario incluido:

    except (OSError, subprocess.SubprocessError):
        return []      # not a git checkout, or git unavailable: nothing to
                       # assert against
    if proc.returncode != 0:
        return []

O sea que "no pude preguntarle a git" se convertia en "no hay nada sucio", el
guard dejaba pasar, y la lane restauraba archivos. En la unica direccion que
destruye trabajo, y sin dejar rastro: el archivo vuelve byte-identico a HEAD y
`git status` sobre el queda vacio.

Es la misma clase que esta sesion persiguio todo el dia: **"no hay" y "no pude"
son estados distintos y tienen que producir acciones distintas.** Un guard que
los colapsa protege solo mientras nada falle, que es cuando no hace falta.

Estos tests afirman el EFECTO —que la precondicion se niegue— y no la forma
interna, asi que la funcion se puede reescribir entera y siguen valiendo.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CONFTEST = REPO / "tests" / "chaos" / "conftest.py"


def _cargar():
    """Carga el conftest de chaos como modulo suelto, sin activar sus fixtures."""
    spec = importlib.util.spec_from_file_location("_chaos_conftest_probe", CONFTEST)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_chaos_conftest_probe"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_el_conftest_de_chaos_existe():
    assert CONFTEST.is_file(), f"{CONFTEST} no existe: el guard se movio o se borro"


def test_no_puedo_saber_no_es_no_hay(tmp_path, monkeypatch):
    """El hallazgo. Si git no se puede consultar, la precondicion NO puede
    devolver 'limpio'.

    Se simula con un directorio que no es un checkout de git: `git status` ahi
    sale distinto de cero. Antes esto devolvia [] y la lane arrancaba.
    """
    mod = _cargar()
    assert hasattr(mod, "_uncommitted_protected_paths"), (
        "la funcion de decision cambio de nombre; este test no puede afirmar "
        "que falle cerrada y hay que actualizarlo"
    )
    with pytest.raises(Exception) as exc:
        mod._uncommitted_protected_paths(tmp_path)
    nombre = type(exc.value).__name__
    assert "Unknown" in nombre or "Precondition" in nombre, (
        "la funcion no levanto un error de 'no pude establecerlo'; si devolvio "
        f"una lista vacia, volvio a fallar ABIERTA. Levanto: {nombre}: {exc.value}"
    )


def test_un_arbol_limpio_no_reporta_nada(tmp_path):
    """Control: sin esto, una funcion que levanta SIEMPRE pasa el test de
    arriba, y eso seria un guard que nunca deja correr la lane."""
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, timeout=60)
    mod = _cargar()
    for d in mod.PROTECTED_DIRS:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
        (tmp_path / d / ".gitkeep").write_text("")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True, timeout=60)
    subprocess.run(
        ["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "base"],
        check=True, timeout=60,
    )
    assert mod._uncommitted_protected_paths(tmp_path) == [], (
        "un arbol limpio reporto suciedad: el guard bloquearia siempre"
    )


def test_un_archivo_sin_commitear_si_se_reporta(tmp_path):
    """Segundo control: el guard tiene que ver lo que dice ver."""
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, timeout=60)
    mod = _cargar()
    protegido = mod.PROTECTED_DIRS[0]
    (tmp_path / protegido).mkdir(parents=True, exist_ok=True)
    (tmp_path / protegido / ".gitkeep").write_text("")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True, timeout=60)
    subprocess.run(
        ["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "base"],
        check=True, timeout=60,
    )
    (tmp_path / protegido / "trabajo_de_otro.py").write_text("# sin commitear\n")

    sucio = mod._uncommitted_protected_paths(tmp_path)
    assert any("trabajo_de_otro" in p for p in sucio), (
        f"el archivo sin commitear no aparecio en la lista: {sucio}. La lane lo "
        "habria restaurado sin dejar rastro."
    )


def test_el_escape_sigue_existiendo():
    """La salida deliberada tiene que seguir estando y ser nombrable.

    Un guard sin escape se apaga entero la primera vez que estorba, y ahi se
    pierde tambien la proteccion. El escape se acciona con una variable de
    entorno ANTES de lanzar pytest, que es una via que si llega.
    """
    texto = CONFTEST.read_text()
    assert "COS_ALLOW_CHAOS_DIRTY_TREE" in texto, (
        "desaparecio el escape documentado del guard"
    )

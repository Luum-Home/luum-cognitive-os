"""El binario `flock` no existe en macOS: invocarlo desnudo es un bug portable.

Que se midio, y por que este gate existe
----------------------------------------
`flock` es de util-linux. En macOS NO ESTA, y el shell devuelve 127. Un shell que
lo invoca sin guarda tiene uno de dos finales, y los dos son silenciosos:

    flock ... || { ...; return 0; }    -> se saltea el trabajo y avisa por stderr
    flock ... 2>&1 || true             -> hace el trabajo SIN LOCK

El primero se midio en produccion el 2026-08-20: el registro de sesiones salia
sin registrar en CADA sesion de esta maquina, y por eso active-sessions.json
estaba en {"sessions": []} con 25 directorios de sesion en disco. No era que las
entradas se podaran despues: nunca llegaban a escribirse. Contrafactico, sobre
un arbol de usar y tirar:

    version vieja  -> sesiones registradas: 0
    arreglada      -> sesiones registradas: 1, con el PID de vida larga

El segundo es peor bajo concurrencia —varias sesiones escribiendo el mismo
archivo sin exclusion— y es exactamente el escenario que el lock existia para
prevenir.

Que NO marca este gate, a proposito
-----------------------------------
  - `fcntl.flock` en Python: es una syscall POSIX, existe en macOS. Otro animal.
  - Archivos que solo NOMBRAN flock (comentarios, docs, tests como este).
  - Shell que ya se guarda con `command -v flock` y tiene camino alternativo.

El patron correcto: guarda con `command -v flock`, y si no esta, lock por
`mkdir`, que es atomico en POSIX y no necesita el binario.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Invocacion del BINARIO: `flock` seguido de una opcion, un fd, una comilla o una
# variable. No matchea `fcntl.flock(`, ni la palabra suelta en prosa.
_INVOCA = re.compile(r'(?:^|[^\w.$])flock\s+(?:-|\d|"|\$)', re.M)
_GUARDA = ("command -v flock", "which flock", "type flock", "HAS_FLOCK")

# Deuda conocida, con igualdad EXACTA. No es un colchon: si uno se arregla, el
# test exige sacarlo de aca; si aparece uno nuevo, falla.
#
# Los dos degradan a "sin lock" en silencio en macOS. No se arreglaron junto con
# el registro de sesiones porque viven en un paquete con su propio ciclo, y
# meter tres sitios mas habria mezclado dos alcances en un commit. Deuda
# escrita, no absorbida.
DEUDA = {
    "packages/agent-lifecycle/hooks/agent-checkpoint.sh",
    "packages/agent-lifecycle/hooks/agent-prelaunch.sh",
}


def _shell_que_invocan_flock() -> set[str]:
    salida = subprocess.run(
        ["grep", "-rl", r"\bflock\b", "hooks/", "scripts/", "packages/"],
        cwd=REPO, capture_output=True, text=True,
    ).stdout.split()
    encontrados = set()
    for rel in salida:
        p = REPO / rel
        if p.suffix == ".py" or not p.is_file():
            continue
        texto = p.read_text(errors="replace")
        if _INVOCA.search(texto) and not any(g in texto for g in _GUARDA):
            encontrados.add(rel)
    return encontrados


def test_ningun_shell_nuevo_invoca_flock_sin_guarda():
    nuevos = _shell_que_invocan_flock() - DEUDA
    assert not nuevos, (
        "estos shell invocan el binario `flock` sin guarda ni camino "
        "alternativo. En macOS sale 127 y el shell o se saltea el trabajo o lo "
        "hace sin lock, en los dos casos en silencio.\n  "
        + "\n  ".join(sorted(nuevos))
    )


def test_la_deuda_no_lista_archivos_ya_arreglados():
    """Un supresor que no suprime nada es un bug: da sensacion de cobertura."""
    vivos = _shell_que_invocan_flock()
    rancios = DEUDA - vivos
    assert not rancios, (
        "estas entradas de DEUDA ya no violan nada — sacalas, o el baseline "
        f"deja lugares libres sin que nadie se entere: {sorted(rancios)}"
    )


def test_la_deuda_no_lista_archivos_inexistentes():
    fantasmas = {f for f in DEUDA if not (REPO / f).is_file()}
    assert not fantasmas, f"DEUDA nombra archivos que no existen: {sorted(fantasmas)}"


def _viola(texto: str) -> bool:
    return bool(_INVOCA.search(texto)) and not any(g in texto for g in _GUARDA)


def test_el_gate_discrimina():
    """Control: sin esto, un detector que no matchea nunca pasa los de arriba."""
    desnudo = "( flock -w 5 200 || exit 1; echo hola ) 200>lock\n"
    guardado = (
        "if command -v flock; then\n"
        "  ( flock -w 5 200; echo hola ) 200>lock\n"
        'else\n  mkdir "$d" && { echo hola; rmdir "$d"; }\nfi\n'
    )
    prosa = "# usamos flock para el lock\necho hola\n"
    assert _viola(desnudo), "no detecto la invocacion desnuda"
    assert not _viola(guardado), "marco el patron correcto (falso positivo)"
    assert not _viola(prosa), "marco una mencion en prosa (falso positivo)"


def test_python_con_fcntl_no_cuenta():
    """fcntl.flock es una syscall POSIX y funciona en macOS: otro animal.

    Se excluye por sufijo, y este test fija esa decision para que quede escrita
    en vez de vivir en un `if` sin explicacion.
    """
    fuente = "import fcntl\nfcntl.flock(f, fcntl.LOCK_EX)\n"
    assert not _INVOCA.search(fuente), (
        "el patron matcheo fcntl.flock: marcaria como bug portable una syscall "
        "que funciona en macOS"
    )

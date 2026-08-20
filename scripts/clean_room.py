#!/usr/bin/env python3
# SCOPE: os-only
# SPDX-License-Identifier: MIT
"""Medir el SO desde un checkout donde el estado del SO no contamina la medicion.

El problema que resuelve
------------------------
Este repo se audita a si mismo con sus propios instrumentos, y eso es circular.
El 2026-08-20 esa circularidad costo tres veces:

  - el auditor de vitalidad decide que hook esta vivo y cuenta bloqueos SOLO por
    `exit_code == 2`, siendo ciego a los que bloquean con exit 0 + JSON en stdout
  - `skill-invocations.jsonl` registro 7 filas en 23 dias, asi que "146 skills sin
    uso" no dice nada sobre las skills: dice todo sobre el contador
  - una corrida de tests reporto 20 fallos, y 11 eran timeouts de una maquina con
    load 267 por 28 procesos huerfanos. El instrumento midio la MAQUINA

Que compra un clon, y que NO compra
-----------------------------------
NO compra "que los hooks no disparen": los hooks del arnes disparan sobre las
tool-calls del agente, no sobre un subproceso. Un `subprocess.run` ya no los
dispara, se corra donde se corra. Prometer eso seria vender humo.

Lo que SI compra, que es mas importante:

  1. ARBOL EN UN ESTADO CONOCIDO. Sin trabajo sin commitear contaminando. Permite
     el veredicto POR DIFERENCIA: "esto ya fallaba en HEAD" vs "esto lo rompi yo".
     Es lo que separo los 31 fallos del 2026-08-20 en sus causas reales.
  2. SIN `.cognitive-os/` VIVO. Los instrumentos no leen la telemetria de la sesion
     en curso. Hoy un test dio `65 passed` con EXIT=1 porque los hooks de la sesion
     del operador escribian en metrics mientras corria la suite.
  3. RAIZ DISTINTA. Un instrumento anclado al cwd, o con una ruta hardcodeada,
     falla RUIDOSAMENTE aca en vez de auditar el arbol equivocado en silencio.

La friccion que encapsula
-------------------------
`conftest.py` exige que `sys.prefix` cuelgue de la raiz del repo, asi que un clon
necesita su propio venv o pytest se niega a arrancar. Resolverlo a mano cuesta
varios intentos --se hizo el 2026-08-20 y quedo sin escribir--. Aca va hecho, con
un `.pth` al site-packages del venv principal para no reinstalar dependencias.

Uso
---
    scripts/clean_room.py --run 'pytest tests/audit -q'
    scripts/clean_room.py --at HEAD~5 --run 'python3 scripts/hook_vitality_audit.py --json'
    scripts/clean_room.py --run '...' --with-telemetry   # copia metrics/ y logs/
    scripts/clean_room.py --run '...' --keep             # no borra el clon al salir

Exit: el del comando corrido. 2 si el clean room no se pudo montar -- un fallo de
montaje NUNCA se confunde con un veredicto del comando.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

# Derivada de __file__ y no del cwd: un instrumento anclado al cwd no falla
# ruidosamente, audita el arbol equivocado y sale limpio por vacio.
REPO = Path(__file__).resolve().parent.parent

MONTAJE_FALLIDO = 2


def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(cwd or REPO),
        capture_output=True, text=True, timeout=600, check=False,
    )


def montar(destino: Path, ref: str, con_telemetria: bool) -> None:
    """Clona el repo en `destino` a la altura de `ref`.

    `--no-hardlinks` a proposito: con hardlinks, escribir en el clon puede tocar
    objetos del repo real. El punto entero de un clean room es que no pueda.
    """
    r = _git("clone", "-q", "--no-hardlinks", str(REPO), str(destino))
    if r.returncode != 0:
        raise SystemExit(f"clone fallo: {r.stderr.strip()[:400]}")

    r = _git("checkout", "-q", ref, cwd=destino)
    if r.returncode != 0:
        raise SystemExit(f"checkout de {ref!r} fallo: {r.stderr.strip()[:400]}")

    # Control anti-vacio: un clon vacio corre cualquier comando y devuelve un
    # veredicto sobre la nada. Es la peor forma de pasar.
    tracked = _git("ls-files", cwd=destino).stdout.count("\n")
    if tracked < 100:
        raise SystemExit(f"el clon tiene {tracked} archivos: no se monto bien")

    if con_telemetria:
        for sub in ("metrics", "logs"):
            src = REPO / ".cognitive-os" / sub
            if src.is_dir():
                shutil.copytree(src, destino / ".cognitive-os" / sub, dirs_exist_ok=True)


def preparar_venv(destino: Path) -> Path | None:
    """Venv propio en el clon, enlazado al site-packages del principal.

    `conftest.py` exige `sys.prefix` bajo la raiz del repo -- sin esto pytest se
    niega a arrancar en el clon con "COS tests must run from a venv rooted under
    the repo". Se enlaza en vez de instalar para no repetir la instalacion entera.
    """
    r = subprocess.run([sys.executable, "-m", "venv", str(destino / ".venv")],
                       capture_output=True, text=True, timeout=600, check=False)
    if r.returncode != 0:
        return None
    principal = sysconfig.get_paths()["purelib"]
    destino_sp = list((destino / ".venv" / "lib").glob("python*/site-packages"))
    if not destino_sp:
        return None
    (destino_sp[0] / "_cos_clean_room.pth").write_text(principal + "\n", encoding="utf-8")
    return destino / ".venv" / "bin" / "python3"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="comando a correr dentro del clean room")
    ap.add_argument("--at", default="HEAD", help="ref a checkoutear (default HEAD)")
    ap.add_argument("--with-telemetry", action="store_true",
                    help="copia .cognitive-os/{metrics,logs} para que no sea la variable")
    ap.add_argument("--keep", action="store_true", help="no borrar el clon al salir")
    ap.add_argument("--quiet", action="store_true", help="solo la salida del comando")
    a = ap.parse_args()

    destino = Path(tempfile.mkdtemp(prefix="cos-clean-room-"))
    try:
        try:
            montar(destino, a.at, a.with_telemetry)
        except SystemExit as e:
            print(f"clean-room: {e}", file=sys.stderr)
            return MONTAJE_FALLIDO

        py = preparar_venv(destino)
        sha = _git("rev-parse", "--short", "HEAD", cwd=destino).stdout.strip()
        if not a.quiet:
            print(f"clean-room: {destino}  @{sha}  venv={'si' if py else 'NO'}",
                  file=sys.stderr)
            if not py:
                print("clean-room: sin venv propio, pytest se va a negar a arrancar",
                      file=sys.stderr)

        env = dict(os.environ)
        # El clean room es su propio proyecto. Sin esto, los instrumentos que leen
        # estas variables resuelven al repo REAL y la medicion vuelve a contaminarse
        # -- exactamente lo que este script existe para impedir.
        env.update({
            "COGNITIVE_OS_PROJECT_DIR": str(destino),
            "CLAUDE_PROJECT_DIR": str(destino),
            "CODEX_PROJECT_DIR": str(destino),
            "COS_METRICS_DIR": str(destino / ".cognitive-os" / "metrics"),
        })
        # Heredadas, estas convierten cualquier guard en uno que aprueba todo: si
        # el comando mide un guard, mediria uno desarmado.
        for v in ("COS_ALLOW_PROTECTED_CONFIG_WRITE", "COS_BYPASS"):
            env.pop(v, None)
        if py:
            env["PATH"] = f"{py.parent}{os.pathsep}{env.get('PATH','')}"

        r = subprocess.run(a.run, shell=True, cwd=str(destino), env=env, check=False)
        return r.returncode
    finally:
        if a.keep:
            print(f"clean-room: conservado en {destino}", file=sys.stderr)
        else:
            shutil.rmtree(destino, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# SCOPE: os-only
# SPDX-License-Identifier: MIT
"""Detecta escrituras a rutas protegidas que el guard de PreToolUse no puede ver.

EL AGUJERO QUE CIERRA, medido el 2026-08-20
-------------------------------------------
`hooks/protected-config-write-guard.sh` corre en PreToolUse e inspecciona el TEXTO
DEL COMANDO. Un proceso puede escribir donde quiera sin que la ruta aparezca ahi:

    echo x >> rules/RULES-COMPACT.md                     -> exit 2  BLOQUEA
    python3 - <<EOF ... "rules/RULES-COMPACT.md" ... EOF -> exit 2  BLOQUEA
    python3 -c "...Path(d+chr(47)+f).write_text(...)"    -> exit 0  PASA
    python3 scripts/escritor.py                          -> exit 0  PASA

**Bloquea el camino corto y deja pasar el largo.** Quien escribe la ruta a la vista
es frenado; quien la mete en un script pasa sin dejar constancia. No es una fuga
marginal, es un incentivo: castiga a quien opera de frente. Explica los 3.765
desarmes profilacticos contra 20 bloqueos (1:188) que midio guard_value_ledger.py.

DETECCION, NO PREVENCION
------------------------
En PostToolUse la escritura YA OCURRIO. Un exit 2 no la deshace: descarta el
resultado de la herramienta. Esto NO promete impedir. Promete que ninguna escritura
a ruta protegida pase SIN QUE SE VEA, que es lo que un hook de arnes puede prometer
honestamente.

POR QUE EL LLAMADOR SALE 2 Y NO 0
---------------------------------
Medido sobre el dispatcher real: `_run_gate` DESCARTA stdout y stderr del hijo
cuando sale 0. Un aviso con exit 0 es invisible para el operador -- por eso
`hooks/skill-router-bash-gate.sh` nunca se ve. Un detector silencioso es un archivo
que se escribe a si mismo un informe que nadie lee.

"NO PUDE" NO ES "NO HAY"
------------------------
Si no puede calcular la huella --git ausente, policy ilegible-- devuelve `unknown`
y el llamador sale 2. No dice "sin cambios". Esa confusion es la que esta jornada
encontro en la precondicion de chaos, en el secret-detector y en tres guards mas.

Uso: recibe el payload del hook por stdin, emite una linea JSON por stdout.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

APPROVAL_ENV = "COS_ALLOW_PROTECTED_CONFIG_WRITE"
# Fallback solo si la policy no se puede leer; el camino normal la usa.
GLOBS_FALLBACK = [".claude/**", ".codex/**", "mcp.json", ".mcp/**"]


def _project_dir() -> Path:
    return Path(
        os.environ.get("CLAUDE_PROJECT_DIR")
        or os.environ.get("COGNITIVE_OS_PROJECT_DIR")
        # Derivada de __file__, nunca del cwd: un detector anclado al cwd audita el
        # arbol equivocado y sale limpio por vacio, la peor forma de pasar.
        or Path(__file__).resolve().parent.parent
    )


def cargar_globs(root: Path) -> tuple[list[str], str | None]:
    """Los globs de la MISMA policy que usa el guard de PreToolUse.

    Duplicar la lista garantizaria que las dos se separen: el dia que alguien
    agregue un glob, uno de los dos queda ciego y nadie se entera.
    """
    policy = root / "manifests" / "protected-config-write-policy.yaml"
    try:
        import yaml  # type: ignore
    except Exception:
        return GLOBS_FALLBACK, "yaml no disponible"
    if not policy.is_file():
        return GLOBS_FALLBACK, "policy ausente"
    try:
        data = yaml.safe_load(policy.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        return GLOBS_FALLBACK, f"policy ilegible: {exc}"
    globs = data.get("protected_globs")
    if not globs:
        return GLOBS_FALLBACK, "policy sin protected_globs"
    return list(globs), None


def esta_protegido(rel: str, globs: list[str]) -> bool:
    for g in globs:
        if fnmatch.fnmatch(rel, g):
            return True
        prefijo = g.rstrip("*").rstrip("/")
        if prefijo and fnmatch.fnmatch(rel, prefijo + "/*"):
            return True
    return False


def rutas_protegidas_sucias(root: Path, globs: list[str]) -> tuple[set[str], str | None]:
    """Rutas protegidas con cambios, segun git.

    Se usa git y no mtime: un `touch` cambia mtime sin cambiar contenido, y una
    escritura que restaura los mismos bytes no lo cambia. Interesa el CONTENIDO.
    """
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "-z"],
            cwd=str(root), capture_output=True, text=True, timeout=60, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return set(), f"git no respondio: {exc}"
    if proc.returncode != 0:
        return set(), f"git status salio {proc.returncode}"
    sucios: set[str] = set()
    for entry in proc.stdout.split("\0"):
        # NO se hace .strip() antes de cortar: el formato porcelain son DOS
        # caracteres de estado mas un espacio, y el primero puede ser espacio
        # (` M archivo`). Un strip defensivo corre el offset y devuelve
        # 'claude/settings.json' en vez de '.claude/settings.json' -- ruta
        # mutilada que ningun glob matchea, y el detector queda ciego a TODO
        # `.claude/`. Medido: git decia `M .claude/settings.json` y esto
        # reportaba `sin_cambios`.
        if len(entry) < 4:
            continue
        rel = entry[3:]
        if rel and esta_protegido(rel, globs):
            sucios.add(rel)
    return sucios, None


def evaluar(payload: dict, root: Path, fp_path: Path) -> dict:
    command = ((payload.get("tool_input") or {}).get("command")) or ""
    globs, aviso = cargar_globs(root)
    if aviso and globs is GLOBS_FALLBACK:
        return {"status": "unknown", "why": aviso}

    sucios, error = rutas_protegidas_sucias(root, globs)
    if error:
        return {"status": "unknown", "why": error}

    # La huella incluye el CONTENIDO, no solo la lista de rutas.
    #
    # La primera version hasheaba `sorted(sucios)` y no detectaba nada cuando el
    # archivo YA estaba sucio: modificarlo otra vez deja el mismo conjunto de rutas
    # y la misma huella. Lo caza la sonda de este mismo archivo -- que es para lo
    # que existe el contrafactico. Con `.claude/settings.json` ya modificado, que es
    # el caso normal en una sesion de trabajo, el detector era ciego justo cuando
    # mas hace falta.
    partes = []
    for rel in sorted(sucios):
        try:
            datos = (root / rel).read_bytes()
            partes.append(f"{rel}:{hashlib.sha256(datos).hexdigest()[:16]}")
        except OSError:
            # Borrado o ilegible: es un cambio, y se registra como tal en vez de
            # desaparecer del conjunto como si nada hubiera pasado.
            partes.append(f"{rel}:AUSENTE")
    huella = hashlib.sha256("\n".join(partes).encode()).hexdigest()[:16]
    try:
        previa = fp_path.read_text(encoding="utf-8").strip()
    except OSError:
        previa = ""
    try:
        fp_path.parent.mkdir(parents=True, exist_ok=True)
        fp_path.write_text(huella, encoding="utf-8")
    except OSError:
        pass

    # Primera corrida: linea de base. Reportar aca acusaria de un cambio a quien
    # solo encendio el detector.
    if not previa:
        return {"status": "baseline", "protected_dirty": len(sucios)}
    if huella == previa:
        return {"status": "sin_cambios", "protected_dirty": len(sucios)}

    aprobado = os.environ.get(APPROVAL_ENV) == "1" or APPROVAL_ENV in command
    return {
        "status": "aprobado" if aprobado else "SIN_APROBAR",
        "paths": sorted(sucios)[:12],
        "protected_dirty": len(sucios),
        "command_head": command[:160],
    }


def main() -> int:
    raw = sys.stdin.read() if not sys.stdin.isatty() else "{}"
    try:
        payload = json.loads(raw or "{}")
    except Exception:
        payload = {}
    root = _project_dir()
    fp = root / ".cognitive-os" / "runtime" / "protected-config-fingerprint.txt"
    print(json.dumps(evaluar(payload, root, fp), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

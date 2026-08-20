#!/usr/bin/env python3
# SCOPE: os-only
# SPDX-License-Identifier: MIT
"""Un comando que barre TODAS las familias de primitivas y devuelve una tabla.

Por que existe
--------------
El 2026-08-20 el operador pregunto como recorrer las 1.500 primitivas del SO -- 291
hooks, 220 skills, 506 scripts, 132 reglas, 132 manifiestos, 507 ADRs -- y saber
cuales sirven, "sin consumirnos tokens de investigacion".

La respuesta resulto ser que los instrumentos YA EXISTEN. Se construyo uno por
familia a lo largo de esa jornada, 1.811 lineas en total. Lo caro fue derivar el
CRITERIO de cada uno: que significa "conectado" para un script no es lo mismo que
para un hook, y aplicar el criterio equivocado produce cientos de falsos positivos
que terminan en un `git rm`. Correrlos, en cambio, cuesta segundos.

Lo unico que faltaba era que fueran UN comando en vez de seis que hay que conocer.
Eso es lo que hace este archivo. No mide nada nuevo: orquesta.

Lo que este censo NO puede decir
--------------------------------
Mide CONECTIVIDAD y RUIDO, no UTILIDAD. Una primitiva puede estar perfectamente
cableada y ser inutil; ninguno de los seis instrumentos lo detecta, y decir lo
contrario seria el tipo de afirmacion que esta jornada paso veinte horas
desmintiendo. La utilidad se cierra leyendo una muestra, no contando.

Y hereda el limite de cada instrumento: si el contador de invocaciones de skills
registro 7 filas en 23 dias --y eso fue lo medido-- entonces "sin uso observado" no
dice nada sobre la skill, dice todo sobre el contador. Cada fila de la tabla se lee
junto con el limite declarado de su instrumento.

Uso
---
    scripts/cos_primitive_census.py            # tabla
    scripts/cos_primitive_census.py --json     # para encadenar
    scripts/cos_primitive_census.py --only hooks,rules

Exit: 0 si todos los instrumentos corrieron (haya o no hallazgos) · 1 si alguno
reporto hallazgos · 2 si alguno NO PUDO CORRER. La tercera es distinta de la
segunda a proposito: "no pude medir" no es "no hay nada que reportar", y colapsar
esos dos estados es el defecto que esta jornada encontro en cinco guards distintos.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = str(REPO / ".venv" / "bin" / "python3")
if not Path(PY).exists():
    PY = sys.executable

NO_PUDO_CORRER = 2

# familia -> (script, args, limite declarado del instrumento)
#
# El limite NO es decorativo: se imprime con cada resultado. Un numero sin su
# limite es el que se cita seis meses despues como si fuera la verdad.
INSTRUMENTOS: dict[str, tuple[str, list[str], str]] = {
    "hooks": (
        "hook_vitality_audit.py", ["--json"],
        "cuenta bloqueos SOLO por exit_code==2; ciego a los que bloquean con "
        "exit 0 + JSON en stdout",
    ),
    "hooks-registro": (
        "audit_hook_registration.py", [],
        "no lee manifests/hook-registration-classification.yaml, donde viven 106 "
        "omisiones declaradas: puede acusar a un hook que esta en regla",
    ),
    "skills": (
        "audit_skill_reachability.py", [],
        "mide alcanzabilidad, no uso: el contador de invocaciones registro 7 filas "
        "en 23 dias",
    ),
    "scripts-y-manifiestos": (
        "audit_primitive_connectedness.py", ["--json"],
        "PARSED significa 'el archivo que lo nombra parsea algo', no 'parsea ESTE "
        "archivo'; el umbral de roster (20) es elegido, no derivado",
    ),
    "reglas": (
        "measure_rule_router_precision.py", ["--corpus", "user"],
        "mide frecuencia de emision, no si el consejo sirve",
    ),
    "valor-de-guards": (
        "guard_value_ledger.py", ["--json"],
        "un bloqueo que quedo en pie es un TECHO de valor: la telemetria no "
        "registra contrafacticos",
    ),
}


def correr(nombre: str) -> dict:
    script, args, limite = INSTRUMENTOS[nombre]
    ruta = REPO / "scripts" / script
    if not ruta.is_file():
        return {"familia": nombre, "estado": "AUSENTE", "detalle": str(ruta), "limite": limite}
    try:
        r = subprocess.run(
            [PY, str(ruta), *args], cwd=str(REPO),
            capture_output=True, text=True, timeout=900, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        # NO se degrada a "sin hallazgos": no poder correr es su propio estado.
        return {"familia": nombre, "estado": "NO_CORRIO", "detalle": str(exc)[:200],
                "limite": limite}

    salida = (r.stdout or "").strip()
    datos = None
    if salida.startswith("{"):
        try:
            datos = json.loads(salida)
        except Exception:
            datos = None

    return {
        "familia": nombre,
        "estado": "hallazgos" if r.returncode == 1 else ("ok" if r.returncode == 0 else f"exit {r.returncode}"),
        "exit": r.returncode,
        "resumen": _resumir(datos, salida),
        "limite": limite,
    }


def _resumir(datos: dict | None, salida: str) -> str:
    """Una linea legible, sin inventar estructura que el instrumento no dio."""
    if isinstance(datos, dict):
        for clave in ("counts", "summary", "by_status", "totals"):
            if isinstance(datos.get(clave), dict):
                items = list(datos[clave].items())[:5]
                return "  ".join(f"{k}={v}" for k, v in items)
        escalares = [f"{k}={v}" for k, v in datos.items()
                     if isinstance(v, (int, float, str)) and len(str(v)) < 40][:5]
        if escalares:
            return "  ".join(escalares)
    lineas = [l for l in salida.splitlines() if l.strip()]
    return (lineas[-1][:110] if lineas else "(sin salida)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--only", help="familias separadas por coma")
    a = ap.parse_args()

    familias = list(INSTRUMENTOS)
    if a.only:
        pedidas = [f.strip() for f in a.only.split(",") if f.strip()]
        desconocidas = [f for f in pedidas if f not in INSTRUMENTOS]
        if desconocidas:
            raise SystemExit(f"familia desconocida: {desconocidas}. Hay: {familias}")
        familias = pedidas

    filas = [correr(f) for f in familias]

    if a.json:
        print(json.dumps({"familias": filas}, indent=2, ensure_ascii=False))
    else:
        ancho = shutil.get_terminal_size((100, 20)).columns
        print("CENSO DE PRIMITIVAS")
        print("=" * min(ancho, 78))
        for f in filas:
            print(f"\n  {f['familia']}  [{f['estado']}]")
            if f.get("resumen"):
                print(f"      {f['resumen']}")
            print(f"      limite: {f['limite']}")
        print("\n" + "-" * min(ancho, 78))
        print("Mide CONECTIVIDAD y RUIDO, no UTILIDAD. Una primitiva puede estar")
        print("perfectamente cableada y ser inutil; ninguno de estos instrumentos lo ve.")
        print("Cada cifra se lee junto al limite de su instrumento, no sola.")

    if any(f["estado"] in ("NO_CORRIO", "AUSENTE") for f in filas):
        return NO_PUDO_CORRER
    return 1 if any(f["estado"] == "hallazgos" for f in filas) else 0


if __name__ == "__main__":
    sys.exit(main())

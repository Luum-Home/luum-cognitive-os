#!/usr/bin/env python3
# SCOPE: os-only
"""Clasificar los archivos GENERADOS que tocó un rango de commits.

PARA QUÉ EXISTE
Un arreglo hecho sobre un archivo generado se pierde en la próxima
regeneración, y hasta ese momento se ve idéntico a un arreglo real. Este
script separa cuatro casos que desde afuera no se distinguen:

  CASO 1  regeneración legítima  — la salida commiteada reproduce al generador.
  CASO 2  edición a mano         — la salida NO reproduce, y la salida fue lo
                                   último que se commiteó. El arreglo se pierde.
  CASO 3  generador sin correr   — el GENERADOR cambió después de la salida.
                                   El arreglo existe pero nadie lo ve todavía.
  CASO 4  deriva               — una ENTRADA cambió después de la salida.
                                   Nadie la tocó a propósito; es ruido, pero
                                   deja el gate en rojo.

CÓMO DECIDE
Primero pregunta si la salida reproduce (`verdict_cmd`, siempre read-only o
escribiendo a un temporal). Si reproduce: CASO 1, y termina.
Si NO reproduce, desempata con la historia de git:

  ¿el generador cambió después del último commit que tocó la salida?  -> CASO 3
  ¿alguna entrada declarada cambió después?                           -> CASO 4
  ninguna de las dos, y aun así no reproduce                          -> CASO 2

El CASO 2 es el hallazgo: la salida fue lo último escrito y no se puede
reconstruir, que es exactamente la firma de una edición a mano.

LÍMITE CONOCIDO (no es un bug, es el alcance)
El desempate 2-vs-4 depende de que `inputs` esté bien declarado. Un auditor que
camina el árbol entero tiene por entrada el árbol entero: se declara con
`inputs: ["."]` y entonces NUNCA puede dar CASO 2, solo CASO 4. Eso es honesto
—no se puede distinguir— y el reporte lo dice en la columna `caveat` en vez de
inventar un veredicto. Ver `--strict` para forzar el corte.

NORMALIZACIÓN
Solo se normaliza lo que está declarado en `volatile` por entrada, y el reporte
imprime qué se normalizó. Normalizar de más es la forma barata de que esta
auditoría no encuentre nada y parezca limpia.

USO
    python3 scripts/audit_generated_file_edits.py --range HEAD~81..HEAD
    python3 scripts/audit_generated_file_edits.py --range HEAD~10..HEAD --json

SALIDA
    exit 0 — ningún CASO 2 y ningún CASO 3
    exit 1 — hay CASO 2 y/o CASO 3 (algo que arreglar)
    exit 2 — error de ejecución
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CASE_LABEL = {
    1: "CASO 1 regeneracion-legitima",
    2: "CASO 2 EDICION-A-MANO",
    3: "CASO 3 generador-sin-correr",
    4: "CASO 4 deriva-de-entrada",
}


@dataclass(frozen=True)
class Entry:
    """Un archivo (o familia de archivos) generado, y cómo se lo verifica."""

    name: str
    patterns: tuple[str, ...]
    generator: str  # comando que lo PRODUCE (documental, no se ejecuta acá)
    verdict_cmd: tuple[str, ...]  # comando read-only: exit 0 == reproduce
    generator_paths: tuple[str, ...]  # archivos cuyo cambio implica CASO 3
    inputs: tuple[str, ...]  # archivos cuyo cambio implica CASO 4
    volatile: tuple[str, ...] = ()  # claves/regex normalizadas antes de comparar
    mode: str = "check"  # "check" | "regen-diff" | "json-cmp"
    regen_cmd: tuple[str, ...] = ()  # para mode=regen-diff/json-cmp, con {out} a sustituir
    committed: tuple[str, ...] = ()  # rutas commiteadas a comparar, en orden
    json_key: str = ""  # para mode=json-cmp: subclave a comparar


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRO
#
# Cada entrada se agregó después de VERIFICAR que el comando existe y corre.
# La cabecera "generated" NO se usa como criterio: ninguno de los generados de
# este repo la lleva. El criterio es el del encargo: ¿existe un comando que
# produzca este archivo?
# ─────────────────────────────────────────────────────────────────────────────
REGISTRY: tuple[Entry, ...] = (
    Entry(
        name="portable-ai-overlay",
        patterns=(".ai/*",),
        generator="python3 scripts/portable_ai_overlay.py",
        verdict_cmd=("python3", "scripts/portable_ai_overlay.py", "--check"),
        generator_paths=("scripts/portable_ai_overlay.py", "cos_lib/primitive_contracts.py"),
        inputs=("manifests/primitive-lifecycle.yaml", "cognitive-os.yaml", ".claude/settings.json"),
    ),
    Entry(
        name="claude-code-settings",
        patterns=(".claude/settings.json",),
        generator="bash scripts/_lib/settings-driver-claude-code.sh",
        verdict_cmd=("bash", "scripts/_lib/settings-driver-claude-code.sh", "--check"),
        generator_paths=("scripts/_lib/settings-driver-claude-code.sh", "scripts/_lib/settings-driver.sh"),
        inputs=("cognitive-os.yaml",),
    ),
    Entry(
        name="opencode-projection",
        patterns=(".opencode/cos-hooks.json", "opencode.json"),
        generator="bash scripts/_lib/settings-driver-opencode.sh",
        verdict_cmd=("bash", "scripts/_lib/settings-driver-opencode.sh", "--check"),
        generator_paths=("scripts/_lib/settings-driver-opencode.sh", "scripts/_lib/settings-driver.sh"),
        inputs=("cognitive-os.yaml",),
    ),
    Entry(
        name="codex-projection",
        patterns=(".codex/hooks.json",),
        generator="bash scripts/_lib/settings-driver-codex.sh",
        verdict_cmd=("bash", "scripts/_lib/settings-driver-codex.sh", "--check"),
        generator_paths=("scripts/_lib/settings-driver-codex.sh", "scripts/_lib/settings-driver.sh"),
        inputs=("cognitive-os.yaml",),
    ),
    Entry(
        name="hook-quality-manifest",
        # Se auto-declara generado: `generated_by: scripts/hook_quality_audit.py --sync`
        patterns=("manifests/hook-quality.yaml",),
        generator="python3 scripts/hook_quality_audit.py --sync",
        verdict_cmd=("python3", "scripts/hook_quality_audit.py", "--check"),
        generator_paths=("scripts/hook_quality_audit.py",),
        inputs=("cognitive-os.yaml", "hooks", "tests"),
    ),
    Entry(
        name="registry-lock",
        patterns=("manifests/agentic-primitive-registry.lock.yaml", "skills/REGISTRY.lock"),
        generator="scripts/cos-registry-lock --write",
        verdict_cmd=("scripts/cos-registry-lock",),
        generator_paths=("cos_lib/cross_instance_learning.py", "scripts/cos_cross_instance_learning.py"),
        inputs=(".",),
        volatile=(r"^generated_at:.*$",),
    ),
    Entry(
        name="primitive-row-audit",
        patterns=("docs/06-Daily/reports/primitive-row-audit-latest.*",),
        generator="python3 scripts/primitive_row_audit.py",
        verdict_cmd=(),
        mode="regen-diff",
        regen_cmd=(
            "python3",
            "scripts/primitive_row_audit.py",
            "--json-out",
            "{out}/primitive-row-audit-latest.json",
            "--md-out",
            "{out}/primitive-row-audit-latest.md",
        ),
        committed=(
            "docs/06-Daily/reports/primitive-row-audit-latest.json",
            "docs/06-Daily/reports/primitive-row-audit-latest.md",
        ),
        generator_paths=("scripts/primitive_row_audit.py",),
        inputs=(".",),
        volatile=(r'"generated_at":.*', r"^_Generado.*$"),
    ),
    Entry(
        name="reduction-backlog",
        patterns=("docs/06-Daily/reports/reduction-backlog-latest.*",),
        generator="python3 scripts/reduction_backlog.py",
        verdict_cmd=(),
        mode="regen-diff",
        regen_cmd=(
            "python3",
            "scripts/reduction_backlog.py",
            "--json-out",
            "{out}/reduction-backlog-latest.json",
            "--md-out",
            "{out}/reduction-backlog-latest.md",
        ),
        committed=(
            "docs/06-Daily/reports/reduction-backlog-latest.json",
            "docs/06-Daily/reports/reduction-backlog-latest.md",
        ),
        generator_paths=("scripts/reduction_backlog.py",),
        inputs=(".",),
        volatile=(r'"generated_at":.*', r"^_Generado.*$"),
    ),
    Entry(
        name="documentation-truth",
        patterns=("docs/06-Daily/reports/documentation-truth-latest.*",),
        generator="python3 scripts/documentation_truth_audit.py",
        verdict_cmd=(),
        mode="json-cmp",
        # --no-write mantiene el repo intacto; comparamos el payload contra el
        # .json commiteado. Se compara SOLO `rows`: el resto del envelope lleva
        # conteos de superficie que se mueven con cada archivo del arbol.
        regen_cmd=("python3", "scripts/documentation_truth_audit.py", "--no-write", "--json"),
        committed=("docs/06-Daily/reports/documentation-truth-latest.json",),
        json_key="rows",
        generator_paths=("scripts/documentation_truth_audit.py",),
        inputs=("manifests/documentation-truth-claims.yaml", "."),
        volatile=("generated_at",),
    ),
)


def sh(cmd: list[str] | tuple[str, ...], cwd: Path = ROOT) -> tuple[int, str]:
    """Correr un comando y devolver (exit_code, salida combinada)."""
    try:
        p = subprocess.run(
            list(cmd), cwd=str(cwd), capture_output=True, text=True, check=False
        )
    except OSError as exc:  # comando inexistente
        return 127, str(exc)
    return p.returncode, (p.stdout + p.stderr).strip()


def normalize(text: str, volatile: tuple[str, ...]) -> str:
    """Borrar SOLO las líneas declaradas volátiles. Nada más."""
    for pat in volatile:
        text = re.sub(pat, "<VOLATIL>", text, flags=re.MULTILINE)
    return text


def touched_files(rev_range: str) -> list[str]:
    code, out = sh(["git", "diff", "--name-only", *rev_range.split("..", 1)])
    if code != 0:
        print(f"error: no pude leer el rango {rev_range}: {out}", file=sys.stderr)
        raise SystemExit(2)
    return [line for line in out.splitlines() if line]


def matches(entry: Entry, path: str) -> bool:
    return any(
        fnmatch.fnmatch(path, pat) or path.startswith(pat.rstrip("*"))
        for pat in entry.patterns
    )


def last_commit(paths: tuple[str, ...], rev_range: str) -> str | None:
    """Último commit DENTRO del rango que tocó alguno de esos paths."""
    if not paths:
        return None
    code, out = sh(["git", "log", "--format=%H", "-1", rev_range, "--", *paths])
    return out.strip() or None if code == 0 else None


def is_ancestor(a: str, b: str) -> bool:
    """True si a es ancestro estricto de b (a vino ANTES)."""
    if a == b:
        return False
    code, _ = sh(["git", "merge-base", "--is-ancestor", a, b])
    return code == 0


def reproduces(entry: Entry) -> tuple[bool, str]:
    """¿La salida commiteada reproduce al generador? Nunca escribe en el repo."""
    if entry.mode == "check":
        code, out = sh(entry.verdict_cmd)
        return code == 0, out

    if entry.mode == "json-cmp":
        code, out = sh(entry.regen_cmd)
        if code not in (0, 1):
            return False, f"el generador falló (rc={code}): {out[:200]}"
        try:
            fresh = json.loads(out[out.index("{") :])
        except (ValueError, json.JSONDecodeError) as exc:
            return False, f"salida no parseable como JSON: {exc}"
        old = json.loads((ROOT / entry.committed[0]).read_text())
        a = old.get(entry.json_key)
        b = fresh.get(entry.json_key)
        if a == b:
            return True, f"`{entry.json_key}` reproduce ({len(a or [])} filas)"
        na, nb = len(a or []), len(b or [])
        return False, f"`{entry.json_key}` difiere: commiteado {na} filas vs regenerado {nb}"

    # regen-diff: generar a un temporal y comparar normalizado.
    with tempfile.TemporaryDirectory(prefix="genaudit-") as tmp:
        cmd = [part.replace("{out}", tmp) for part in entry.regen_cmd]
        code, out = sh(cmd)
        if code != 0:
            return False, f"el generador falló: {out}"
        diffs = []
        for committed in entry.committed:
            fresh = Path(tmp) / Path(committed).name
            old = ROOT / committed
            if not fresh.exists() or not old.exists():
                diffs.append(f"{committed}: falta un lado de la comparación")
                continue
            a = normalize(old.read_text(errors="replace"), entry.volatile)
            b = normalize(fresh.read_text(errors="replace"), entry.volatile)
            if a != b:
                n = sum(1 for x, y in zip(a.splitlines(), b.splitlines()) if x != y)
                delta = abs(len(a.splitlines()) - len(b.splitlines()))
                diffs.append(f"{committed}: difiere (~{n + delta} líneas)")
        return (not diffs), "; ".join(diffs) or "reproduce"


def classify(entry: Entry, rev_range: str, strict: bool) -> dict:
    ok, detail = reproduces(entry)
    row: dict = {
        "generado": entry.name,
        "patrones": list(entry.patterns),
        "generador": entry.generator,
        "veredicto_cmd": " ".join(entry.verdict_cmd or entry.regen_cmd),
        "normalizado": list(entry.volatile) or ["nada"],
        "detalle": detail,
        "caveat": "",
    }
    if ok:
        row["caso"] = 1
        return row

    out_c = last_commit(entry.patterns, rev_range)
    gen_c = last_commit(entry.generator_paths, rev_range)
    in_c = last_commit(entry.inputs, rev_range)

    if gen_c and out_c and is_ancestor(out_c, gen_c):
        row["caso"] = 3
        row["detalle"] += f" | generador movido después de la salida ({gen_c[:9]})"
        return row
    if in_c and out_c and is_ancestor(out_c, in_c):
        row["caso"] = 4
        row["detalle"] += f" | entrada movida después de la salida ({in_c[:9]})"
        if "." in entry.inputs and not strict:
            row["caveat"] = (
                "inputs='.' — con el árbol entero por entrada este archivo nunca "
                "puede dar CASO 2. Usar --strict para forzar el corte."
            )
        return row

    row["caso"] = 2
    row["detalle"] += " | la salida fue lo último commiteado y no reproduce"
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # OJO: bajo sesiones concurrentes HEAD se mueve. `HEAD~81..HEAD` NO es un
    # ancla estable: entre dos corridas puede describir ventanas distintas.
    # Para una auditoría citable, pasar SHAs explícitos (`<base>..<punta>`).
    ap.add_argument("--range", dest="rev_range", default="HEAD~1..HEAD", help="rango de commits; usar SHAs explícitos para que sea reproducible")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="no aceptar inputs='.' como coartada: forzar CASO 2 cuando no reproduce",
    )
    args = ap.parse_args(argv)

    files = touched_files(args.rev_range)
    hit = [e for e in REGISTRY if any(matches(e, f) for f in files)]

    rows = [classify(e, args.rev_range, args.strict) for e in hit]
    for r in rows:
        r["archivos_tocados"] = sorted(f for f in files if any(matches(e, f) for e in hit if e.name == r["generado"]))

    counts = {c: sum(1 for r in rows if r["caso"] == c) for c in (1, 2, 3, 4)}
    payload = {
        "rango": args.rev_range,
        "archivos_en_rango": len(files),
        "familias_generadas_tocadas": len(rows),
        "conteo_por_caso": counts,
        "filas": rows,
    }

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"rango {args.rev_range} — {len(files)} archivos, {len(rows)} familias generadas tocadas")
        for c in (1, 2, 3, 4):
            print(f"  {CASE_LABEL[c]}: {counts[c]}")
        print()
        for r in sorted(rows, key=lambda x: x["caso"]):
            print(f"[{CASE_LABEL[r['caso']]}] {r['generado']}")
            print(f"    archivos    : {', '.join(r['archivos_tocados']) or '-'}")
            print(f"    generador   : {r['generador']}")
            print(f"    veredicto   : {r['veredicto_cmd']}")
            print(f"    normalizado : {', '.join(r['normalizado'])}")
            print(f"    detalle     : {r['detalle']}")
            if r["caveat"]:
                print(f"    CAVEAT      : {r['caveat']}")
            print()

    return 1 if (counts[2] or counts[3]) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)

#!/usr/bin/env python3
"""Corrida de mutacion sobre hooks/orchestrator-skill-invocation-gate.sh.

Por que existe. Contar tests no dice nada sobre si defienden algo: el gate de
ADR-188 llego al 2026-08-20 con 41 tests verdes, cero verdaderos positivos en 94
dias y dos tests que no mataban ningun mutante (el unit de `last_suggestion`, que
no ejecuta el hook, y la sonda de portabilidad, que afirmaba `rc == 0` sobre un
payload donde TODOS los caminos devuelven 0).

Este script muta el hook a proposito y exige que la suite se ponga roja. Un
mutante que sobrevive es una conducta que nadie esta defendiendo.

Read-only sobre el repo: el hook se copia a un temporal, se muta la copia y los
tests la leen via `COS_SKILL_GATE_HOOK`. El original no se toca nunca.

Uso:
    python3 scripts/mutation_check_skill_gate.py [--verbose]

Exit codes:
    0  todos los mutantes mueren
    1  sobrevive al menos uno (hay conducta sin defensa)
    2  error de setup (no corrio la mutacion)
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / "hooks" / "orchestrator-skill-invocation-gate.sh"

SUITE = [
    "tests/contracts/test_skill_gate_identity_and_insistence.py",
    "tests/contracts/test_skill_invocation_gate.py",
    "tests/red_team/portability/test_orchestrator-skill-invocation-gate.py",
    "tests/hooks/test_skill_invocation_gate_audit.py",
]

ABSTAIN_HEAD = 'if [ -z "$SESSION_ID" ]; then'


def _replace_once(text: str, old: str, new: str, mid: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"[{mid}] ancla ausente o ambigua ({text.count(old)} matches): {old[:70]!r}")
    return text.replace(old, new, 1)


def _abstain_block_bounds(text: str) -> tuple[int, int]:
    """Devuelve (inicio, fin) del bloque `if [ -z "$SESSION_ID" ]; then ... fi`."""
    start = text.index(ABSTAIN_HEAD)
    end = text.index("\nfi\n", start) + len("\nfi\n")
    return start, end


# ─── Los mutantes ────────────────────────────────────────────────────────────
# M1..M3 son la conducta que se agrego el 2026-08-20 (la abstencion sin sesion) y
# que hasta hoy no tenia un solo test que la defendiera de su propia regresion.
# M4 es la mas vieja: el filtro de tool_name.

def m1_abstain_blocks(t: str) -> str:
    """La abstencion sin identidad se vuelve BLOQUEO."""
    start, end = _abstain_block_bounds(t)
    block = t[start:end]
    return t[:start] + _replace_once(block, "\n  exit 0\nfi\n", "\n  exit 2\nfi\n", "M1") + t[end:]


def m2_abstain_silent(t: str) -> str:
    """La abstencion no deja rastro: sale por el corto, sin fila anonima."""
    start, end = _abstain_block_bounds(t)
    return t[:start] + f'{ABSTAIN_HEAD}\n  exit 0\nfi\n' + t[end:]


def m3_unknown_sentinel(t: str) -> str:
    """Vuelve el bug de `unknown`: se fabrica la clave y la abstencion muere."""
    return _replace_once(
        t, ABSTAIN_HEAD,
        'SESSION_ID="${SESSION_ID:-unknown}"\n' + ABSTAIN_HEAD, "M3",
    )


def m4_no_tool_filter(t: str) -> str:
    """El gate deja de filtrar por tool_name y gobierna toda herramienta."""
    return _replace_once(
        t,
        "  Agent|Bash|task|delegate) ;;\n  *) exit 0 ;;\n",
        "  *) ;;\n",
        "M4",
    )


MUTANTS = [
    ("M1", "abstencion sin sesion BLOQUEA en vez de abstenerse", m1_abstain_blocks),
    ("M2", "abstencion sin sesion no deja rastro", m2_abstain_silent),
    ("M3", "vuelve el sentinela `unknown` (causa raiz documentada en la cabecera)", m3_unknown_sentinel),
    ("M4", "se quita el filtro de tool_name", m4_no_tool_filter),
]


def _pytest(hook_path: Path | None, tmp_metrics: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if hook_path is not None:
        env["COS_SKILL_GATE_HOOK"] = str(hook_path)
    else:
        env.pop("COS_SKILL_GATE_HOOK", None)
    # La suite no puede escribir en la telemetria del operador, y puede haber una
    # sesion viva escribiendo en paralelo: se redirige y se tolera.
    env["COS_METRICS_DIR"] = str(tmp_metrics)
    env["COS_ALLOW_OPERATOR_METRICS_WRITES"] = "1"
    python = REPO / ".venv" / "bin" / "python"
    exe = [str(python)] if python.exists() else [sys.executable]
    return subprocess.run(
        exe + ["-m", "pytest", *SUITE, "-q", "-p", "no:randomly", "-x"],
        cwd=REPO, env=env, capture_output=True, text=True, timeout=900,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if not HOOK.exists():
        print(f"ERROR: no existe {HOOK}", file=sys.stderr)
        return 2

    original = HOOK.read_text()
    resultados: list[tuple[str, str, bool]] = []

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        metrics = tmp / "metrics"
        metrics.mkdir()

        # Control: sin mutar, la suite tiene que estar verde. Si no, cualquier
        # "mutante muerto" de abajo seria un falso positivo.
        base = _pytest(None, metrics)
        if base.returncode != 0:
            print("ERROR: la suite ya esta roja SIN mutar; la corrida no significa nada.")
            print(base.stdout[-3000:])
            return 2
        print("control (hook sin mutar): VERDE\n")

        for mid, desc, fn in MUTANTS:
            mutant = tmp / f"gate-{mid}.sh"
            try:
                mutant.write_text(fn(original))
            except SystemExit as exc:
                print(f"{mid}  ERROR DE ANCLA  {exc}")
                resultados.append((mid, desc, False))
                continue
            shutil.copymode(HOOK, mutant)

            res = _pytest(mutant, metrics)
            muerto = res.returncode != 0
            resultados.append((mid, desc, muerto))
            estado = "MUERTO" if muerto else "SOBREVIVE"
            culpable = ""
            if muerto:
                for line in res.stdout.splitlines():
                    if line.startswith("FAILED"):
                        culpable = "  <- " + line.split()[1].split("::")[-1]
                        break
            print(f"{mid}  {estado:9}  {desc}{culpable}")
            if args.verbose and not muerto:
                print(res.stdout[-2000:])

    vivos = [m for m in resultados if not m[2]]
    print(f"\n{len(resultados) - len(vivos)}/{len(resultados)} mutantes muertos")
    if vivos:
        for mid, desc, _ in vivos:
            print(f"  SOBREVIVE {mid}: {desc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

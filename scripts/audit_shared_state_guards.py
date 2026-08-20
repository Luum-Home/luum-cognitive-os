#!/usr/bin/env python3
# SCOPE: os-only
"""¿Un guard bloquea por lo que hace quien lo dispara, o por lo que dejó el vecino?

EL DEFECTO QUE MIDE. Este checkout lo comparten varias sesiones a la vez, y
comparten con él un solo índice de git, un solo árbol de trabajo, un solo
``.cognitive-os/`` y una sola rama activa. Un guard que decide mirando ese
estado decide sobre trabajo que no es de quien lo disparó: la sesión A deja un
archivo staged, la sesión B corre un commit de otra cosa y se come el bloqueo.

DOS PROPIEDADES, MEDIDAS POR SEPARADO, porque son independientes y se arreglan
distinto:

  ATRIBUCIÓN — ¿el guard puede saber si el estado que lo hizo bloquear es de
  quien disparó? Un commit con pathspec (``git commit -- a b``) dice
  exactamente qué va a entrar; leer ``git diff --cached`` entero es leer también
  lo del vecino. Se marca ``attributes`` cuando el hook restringe su lectura a
  algo derivable del disparador (el pathspec del comando, su propio agent_id,
  su propio session_id), y ``shared_unscoped`` cuando lee el estado global.

  ESCAPE — ¿quien quedó bloqueado puede destrabarse SIN relanzar el arnés? Un
  hook es hijo del arnés: un prefijo ``VAR=1 <cmd>`` se lo come el shell del
  comando y el hook ya decidió. Las vías reales son cinco y sólo dos sirven a
  mitad de sesión (ver ``ESCAPES``).

QUÉ NO MIDE. No juzga si el bloqueo es correcto: un guard sin escape puede ser
la respuesta correcta cuando el bloqueo es siempre culpa de quien lo dispara.
Mide si el guard PUEDE atribuir y si el bloqueado TIENE salida; qué hacer con
eso es decisión del operador.

Exit: 0 sin hallazgos, 1 con hallazgos, 2 error.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Estado compartido por todas las sesiones del mismo checkout.
SHARED_READS = {
    "git_index": [r"diff\s+--cached", r"diff-index"],
    "worktree": [r"git\s+(-C\s+\S+\s+)?status\b", r"diff\s+--name-only(?!.*--cached)",
                 r"ls-files\s+-m"],
    "branch": [r"rev-parse\s+--abbrev-ref", r"symbolic-ref", r"branch\s+--show-current"],
}

# `.cognitive-os/` NO entra por el solo hecho de aparecer. Casi todos los hooks
# escriben ahí su telemetría, y escribir una métrica no es decidir. Se cuenta
# sólo la LECTURA de una ruta compartida: si el path lleva el session_id o el
# agent_id, el estado es propio y por definición atribuible.
COS_READ_RE = re.compile(
    r"""(?:\bcat\s+|\bgrep\b[^\n]*?|\[\s+-[fsdr]\s+|\bsource\s+|\bsed\s+-n[^\n]*?|
        \bhead\s+[^\n]*?|\btail\s+[^\n]*?|\bjq\b[^\n]*?|\bwc\s+-l\s+)
        ["'$]*[^"'\s]*\.cognitive-os/(?P<path>[^"'\s)]*)""",
    re.X)
COS_TELEMETRY = re.compile(r"^(metrics|logs|audit)/")
COS_PER_SESSION = re.compile(r"SESSION_ID|AGENT_ID|\$\{?SESSION|\$\{?AGENT")


def cos_shared_reads(text: str) -> list[str]:
    """Rutas de .cognitive-os/ que el hook LEE y que no son suyas por sesión."""
    out = []
    for m in COS_READ_RE.finditer(text):
        path = m.group("path")
        if not path or COS_TELEMETRY.match(path):
            continue
        if COS_PER_SESSION.search(m.group(0)):
            continue  # estado propio de la sesión: atribuible por construcción
        if path.startswith("runtime/bypass.env"):
            continue  # es la vía de escape, no un insumo de decisión
        out.append(path.split("/")[0] or path)
    return sorted(set(out))


# Señales de que el hook restringe la lectura a lo que trajo el disparador.
ATTRIBUTION_SIGNALS = [
    r"cos_git_commit_pathspec",      # pathspec del propio comando
    r"COS_SESSION_ID|SESSION_ID",    # su propia sesión
    r"AGENT_ID|agent_id",            # su propio agente
    r"sessions/\$\{?SESSION",
]

# Las cinco vías de activación conocidas. Sólo dos sirven a mitad de sesión.
ESCAPES = {
    "bypass_env_file": (r"cos_bypass_allows", True),        # relee bypass.env: mid-session
    "command_token": (r"COMMAND|command.*--allow-|_TOKEN_IN_COMMAND", True),
    "env_only": (r"^\s*if\s*\[\s*\"\$\{(COS_|DISABLE_HOOK_)", False),
}

BLOCK_RE = re.compile(r"^\s*exit\s+2\b", re.M)


def classify(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not BLOCK_RE.search(text):
        return None  # no bloquea: fuera de la población

    shared = [k for k, pats in SHARED_READS.items()
              if any(re.search(p, text) for p in pats)]
    cos_reads = cos_shared_reads(text)
    if cos_reads:
        shared.append("cos_dir:" + "|".join(cos_reads[:3]))
    if not shared:
        return None

    attributes = any(re.search(p, text) for p in ATTRIBUTION_SIGNALS)
    # Un hook que lee el índice entero no atribuye aunque conozca su session_id:
    # el índice no tiene dueño por sesión.
    index_unscoped = "git_index" in shared and not re.search(
        r"cos_git_commit_pathspec", text)

    escapes = []
    if re.search(r"cos_bypass_allows", text):
        escapes.append("bypass_env_file")
    if re.search(r"DISABLE_HOOK_[A-Z_]+|COS_ALLOW_[A-Z_]+|COS_BYPASS_[A-Z_]+", text):
        escapes.append("env_only")

    # Variable compañera obligatoria: un bypass que exige *_REASON no viaja por
    # bypass.env mientras el archivo transporte sólo COS_BYPASS.
    # Obligatoria = default vacío. Ver la nota en escape_census().
    companions = sorted(set(re.findall(r"\$\{(COS_[A-Z_]*REASON):-\}", text)))

    return {
        "hook": path.name,
        "shared_state": shared,
        "attributes": attributes and not index_unscoped,
        "index_unscoped": index_unscoped,
        "escapes": escapes,
        "mid_session_escape": "bypass_env_file" in escapes and not companions,
        "companion_vars": companions,
    }


def escape_census(paths) -> dict:
    """Segunda población, disjunta de la primera a propósito.

    La atribución se mide sobre los guards que deciden con estado compartido; el
    escape se mide sobre TODOS los que bloquean y ofrecen un bypass, comparta o
    no el estado. `subagent-budget-enforcer` cuenta acá y no allá: su contador es
    por agente (atribuye bien) y aun así el cortado no tiene cómo destrabarse.
    """
    rows = []
    for p in paths:
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not BLOCK_RE.search(text):
            continue
        keys = sorted(set(re.findall(r"cos_bypass_allows\s+[\"']?([a-z_]+)", text)))
        env_vars = sorted(set(re.findall(r"\$\{(COS_ALLOW_[A-Z_]+|COS_BYPASS_[A-Z_]+|DISABLE_HOOK_[A-Z_]+)[:\-]", text)))
        # Una compañera cuenta sólo si es OBLIGATORIA. `${VAR:-}` con default
        # vacío obliga a chequearla; `${VAR:-algo}` ya trae respuesta y no traba
        # a nadie. Sin esta distinción el censo contaba como "sin vía" a un hook
        # cuyo motivo es opcional, y se inflaba su propio hallazgo.
        companions = sorted(set(re.findall(r"\$\{(COS_[A-Z_]*REASON):-\}", text)))
        if not keys and not env_vars:
            continue
        rows.append({
            "hook": p.name,
            "resolver_keys": keys,
            "env_only_vars": env_vars,
            "companion_required": companions,
            # bypass.env transporta hoy sólo COS_BYPASS: una compañera obligatoria
            # deja al hook sin vía a mitad de sesión aunque su clave esté en el resolvedor.
            "mid_session": bool(keys) and not companions,
        })
    return {
        "blocking_hooks_with_bypass": len(rows),
        "mid_session_escape": sum(1 for r in rows if r["mid_session"]),
        "env_only_no_mid_session": [r["hook"] for r in rows if not r["mid_session"]],
        "blocked_by_companion": [r["hook"] for r in rows if r["companion_required"]],
        "rows": rows,
    }


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    reg_file = ROOT / ".cognitive-os" / "registered-hooks.txt"
    names = None
    if reg_file.is_file():
        names = [n.strip() for n in reg_file.read_text().splitlines() if n.strip()]
    rows = []
    hooks_dir = ROOT / "hooks"
    candidates = ([hooks_dir / n for n in names] if names
                  else sorted(hooks_dir.glob("*.sh")))
    for p in candidates:
        if not p.is_file():
            continue
        row = classify(p)
        if row:
            rows.append(row)

    rows.sort(key=lambda r: r["hook"])
    total = len(rows)
    attributable = sum(1 for r in rows if r["attributes"])
    with_mid = sum(1 for r in rows if r["mid_session_escape"])
    blocked_companion = sorted({c for r in rows for c in r["companion_vars"]})

    esc = escape_census(candidates)

    if as_json:
        print(json.dumps({
            "escape_census": esc,
            "total_shared_state_blockers": total,
            "attributable": attributable,
            "not_attributable": total - attributable,
            "with_mid_session_escape": with_mid,
            "companion_vars_without_transport": blocked_companion,
            "rows": rows,
        }, indent=2, sort_keys=True))
    else:
        print(f"guards que bloquean y deciden sobre estado compartido: {total}")
        print(f"  atribuyen al disparador: {attributable}")
        print(f"  NO atribuyen:            {total - attributable}")
        print(f"  con escape a mitad de sesión: {with_mid}")
        if blocked_companion:
            print(f"  variables compañeras sin transporte: {', '.join(blocked_companion)}")
        print()
        print(f"escape — guards que bloquean y ofrecen bypass: {esc['blocking_hooks_with_bypass']}")
        print(f"  con vía a mitad de sesión (bypass.env): {esc['mid_session_escape']}")
        print(f"  trabados por variable compañera: {len(esc['blocked_by_companion'])} "
              f"({', '.join(esc['blocked_by_companion']) or '-'})")
        print()
        for r in rows:
            flag = "ATRIB" if r["attributes"] else "  --  "
            esc = "esc:mid" if r["mid_session_escape"] else (
                "esc:env-only" if r["escapes"] else "esc:NINGUNO")
            print(f"  [{flag}] {r['hook']:<48} {','.join(r['shared_state']):<28} {esc}")

    return 1 if (total - attributable) or (total - with_mid) else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)

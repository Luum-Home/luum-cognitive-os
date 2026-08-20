#!/usr/bin/env python3
# SCOPE: os-only
"""¿El mensaje de un hook ofrece una salida que quien la lee puede ejecutar?

EL DEFECTO QUE MIDE. Un hook es hijo del arnés, no del shell del Bash tool. Un
prefijo ``VAR=1 <comando>`` le pone la variable a ``<comando>`` y nunca al hook,
que ya decidió antes de que ese shell existiera. Un mensaje de bloqueo que ofrece
esa forma promete una salida inejecutable: el lector la tipea, sigue bloqueado, y
no tiene forma de saber que el problema es la vía y no su comando.

QUÉ ES *NO* UN DEFECTO, dicho antes para no cometer el error simétrico. Hay dos
vías de activación que SÍ funcionan y no requieren que el hook lea nada del texto:

  * ``export VAR=1`` **antes** de lanzar el arnés (rules/hook-security-profiles.md:62);
  * el bloque ``env`` de ``.claude/settings.json``, que se reaplica al guardar.

Un hook que ofrece cualquiera de esas dos dice la verdad aunque solo lea del
entorno. Forzar a todos a leer del texto borraría esa distinción, así que el
criterio no es "todos deben leer del texto" sino **el mensaje no debe prometer
una vía que el hook no puede honrar**.

TRES DESENLACES Y UNA CEGUERA:

  mentira    — el mensaje ofrece la forma de prefijo en línea y el hook solo lee
               del entorno. Es lo único que el gate rojea.
  honesto    — ofrece prefijo en línea Y compensa leyendo el token del texto del
               comando, o bien ofrece ``export`` / ``settings.json``.
  ambiguo    — nombra la variable como salida sin nombrar ninguna vía ("set VAR=1",
               "override with VAR=1"). No miente explícitamente; tampoco alcanza.
               Va a ``blind``: el instrumento no puede decidirlo leyendo texto.

Uso:
    python3 scripts/audit_killswitch_activation.py            # resumen
    python3 scripts/audit_killswitch_activation.py --json     # filas crudas
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

HOW = "python3 scripts/audit_killswitch_activation.py --json"

# Una variable de kill-switch: DISABLE_HOOK_* o cualquier MAYUSCULA que lleve un
# verbo de permiso en el nombre. Se pide el `=1`/`=true` en el mismo lugar porque
# lo que se audita es la ACTIVACION escrita, no la mención del nombre.
KILLSWITCH_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(DISABLE_HOOK_[A-Z0-9_]+"
    r"|[A-Z][A-Z0-9_]*(?:ALLOW|BYPASS|DISABLE|SKIP|FORCE|OVERRIDE|SUPPRESS)[A-Z0-9_]*)"
    r"\s*=\s*(?:1|true|\"1\"|yes)"
    r"(?![A-Za-z0-9_])"
)

# Tokens que, puestos inmediatamente después del `=1`, hacen del texto una
# invocación: o son comandos reales, o son el hueco donde el lector pone el suyo.
_COMMAND_WORDS = {
    "git", "sed", "awk", "python3", "python", "bash", "sh", "jq", "cat", "echo",
    "mv", "cp", "rm", "ln", "mkdir", "touch", "tee", "grep", "find", "make", "go",
    "npm", "node", "curl", "cos", "pytest", "tar", "chmod", "gh", "ruff",
}
# El prefijo SÍ funciona en un lugar: al LANZAR el arnés, que hereda el entorno
# del shell que lo arrancó. `VAR=1 claude` es una instrucción correcta; lo que no
# existe es `VAR=1 git commit` desde adentro de la sesión ya lanzada. Contarlas
# juntas era mezclar dos poblaciones: "sin ruta ninguna" y "con ruta en arranque".
_LAUNCHER_WORDS = {"claude", "codex", "claude-code"}
_PLACEHOLDERS = {"...", "<cmd>", "<comando>", "<command>", "<tu-comando>", "<your-command>"}
_NEXT_TOKEN_RE = re.compile(r"^[ \t]+(\S+)")

# "prefix command with VAR=1" dice lo mismo que `VAR=1 <cmd>` sin escribirlo.
_PREFIX_PROSE_RE = re.compile(r"\bprefix(?:ed|ing)?\b|\bprefij", re.I)
# Las dos vías que sí funcionan.
_EXPORT_RE = re.compile(r"\bexport\b")
# Tercera vía ejecutable, encontrada leyendo el resolvedor de bypass compartido
# de _lib: el archivo .cognitive-os/runtime/bypass.env se lee en cada invocación,
# así que un agente puede escribirlo A MITAD DE SESIÓN y el próximo hook lo ve.
_SETTINGS_RE = re.compile(r"settings\.json|bypass\.env|COS_BYPASS=")

# El hook compensa si, cerca de la ocurrencia, tiene el texto del comando y un
# operador que compara texto. Ventana y no línea: el patrón canónico
# (protected-config-write-guard) parte el `printf | grep` en tres líneas.
_CMD_TEXT_RE = re.compile(r"tool_input\.command|\$\{?_?(?:CMD|COMMAND)\b|\$_cmd\b")
_TEXT_MATCH_RE = re.compile(r"\bgrep\b|==|=~|\bcase\b")
_WINDOW = 5

_HEREDOC_OPEN_RE = re.compile(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?")
_OUTPUT_RE = re.compile(r">&2|\becho\b|\bprintf\b")
# `printf '%s' "$COMMAND" | grep -q 'VAR=1'` lleva un printf y NO es un mensaje:
# es exactamente la compensación que buscamos. Un echo cuya salida se filtra o se
# captura es código; solo el que va a la terminal le habla a alguien.
_PIPED_RE = re.compile(r"\|\s*(grep|jq|sed|awk|python3?|head|tail|wc|tr|cut|xargs|read)\b")
_CAPTURED_RE = re.compile(r"=\s*\$\(|=\s*`")


@dataclass(frozen=True)
class Row:
    file: str
    line: int
    var: str
    verdict: str
    reason: str
    text: str


def _hook_files() -> list[Path]:
    """rglob, no glob: `hooks/*.sh` es ciego a `_lib/` y a `_archived/`."""
    seen: set[Path] = set()
    out: list[Path] = []
    for p in sorted(REPO.joinpath("hooks").rglob("*.sh")):
        real = p.resolve()
        if real in seen:
            continue
        seen.add(real)
        out.append(p)
    return out


def _message_lines(lines: list[str]) -> set[int]:
    """Índices (0-based) de líneas que son texto para una persona, no código.

    Comentario, línea con echo/printf/>&2, o cuerpo de heredoc. Se excluye el
    código real porque `VAR=1 python3 - <<PY` dentro de un hook es una invocación
    legítima, no una promesa a nadie.
    """
    msg: set[int] = set()
    terminator: str | None = None
    for i, raw in enumerate(lines):
        if terminator is not None:
            if raw.strip() == terminator:
                terminator = None
            else:
                msg.add(i)
            continue
        stripped = raw.lstrip()
        if stripped.startswith("#"):
            msg.add(i)
        elif _OUTPUT_RE.search(raw) and not (_PIPED_RE.search(raw) or _CAPTURED_RE.search(raw)):
            msg.add(i)
        m = _HEREDOC_OPEN_RE.search(raw)
        if m:
            terminator = m.group(1)
    return msg


def _reads_from_command_text(lines: list[str], msg_idx: set[int], var: str) -> bool:
    """¿En ALGUNA parte del archivo el hook busca este token en el texto del comando?

    Se barre el archivo entero, no un entorno de la ocurrencia: en el patrón
    canónico el mensaje que ofrece el prefijo vive a 30 líneas de la compensación
    que lo honra, y mirar solo alrededor del mensaje lo declaraba mentiroso.

    Las líneas de mensaje quedan EXCLUIDAS de la compensación. Sin eso,
    ``echo "  c) Allow bypass:  VAR=1 $COMMAND"`` se absolvía a sí mismo: el
    ``$COMMAND`` que imprime el mensaje se leía como si fuese el ``$COMMAND`` que
    lo inspecciona. Una promesa no puede ser su propia prueba.
    """
    for j, line in enumerate(lines):
        if var not in line or j in msg_idx:
            continue
        window = "\n".join(lines[max(0, j - _WINDOW) : min(len(lines), j + _WINDOW + 1)])
        if _CMD_TEXT_RE.search(window) and _TEXT_MATCH_RE.search(window):
            return True
    return False


def _next_token(line: str, end: int) -> str | None:
    m = _NEXT_TOKEN_RE.match(line[end:])
    return m.group(1).rstrip('".,;') if m else None


def _promises_launch_prefix(line: str, end: int) -> bool:
    """`VAR=1 claude` es la vía de arranque: el arnés hereda ese entorno."""
    tok = _next_token(line, end)
    return tok in _LAUNCHER_WORDS if tok else False


def _promises_inline_prefix(line: str, end: int) -> bool:
    """`VAR=1 <algo-que-corre-adentro>`: la forma que no llega a ningún hook."""
    tok = _next_token(line, end)
    if tok:
        if tok in _PLACEHOLDERS or tok in _COMMAND_WORDS:
            return True
        if tok.startswith(("./", "<", "$", ".venv/")):
            return True
    return bool(_PREFIX_PROSE_RE.search(line))


def _names_working_route(line: str, start: int) -> bool:
    """¿El mensaje nombra `export` o settings.json como la vía?"""
    return bool(_EXPORT_RE.search(line[:start]) or _SETTINGS_RE.search(line))


def classify_source(rel: str, text: str) -> list[Row]:
    """Clasifica un hook a partir de su TEXTO, no de su ruta.

    Separado de :func:`collect` para que la prueba pueda alimentarlo con hooks
    sintéticos y demostrar el rojo, el verde-por-compensación y el
    verde-por-vía-legítima sin tocar el árbol real.
    """
    rows: list[Row] = []
    lines = text.splitlines()
    msg_idx = _message_lines(lines)
    for i, line in enumerate(lines):
        for m in KILLSWITCH_RE.finditer(line):
            var = m.group(1)
            if i not in msg_idx:
                verdict, reason = "codigo", "invocación real del hook, no un mensaje"
            elif _names_working_route(line, m.start()):
                verdict, reason = "honesto", "ofrece export / settings.json / bypass.env"
            elif _promises_launch_prefix(line, m.end()):
                verdict, reason = "honesto", "prefijo sobre el lanzamiento del arnés"
            elif not _promises_inline_prefix(line, m.end()):
                verdict, reason = "ambiguo", "nombra la variable sin nombrar vía"
            elif _reads_from_command_text(lines, msg_idx, var):
                verdict, reason = "honesto", "ofrece prefijo y lo lee del texto"
            else:
                verdict, reason = "mentira", "ofrece prefijo en línea que no puede leer"
            rows.append(Row(rel, i + 1, var, verdict, reason, line.strip()[:160]))
    return rows


def collect() -> list[Row]:
    rows: list[Row] = []
    for path in _hook_files():
        rows.extend(
            classify_source(
                path.relative_to(REPO).as_posix(),
                path.read_text(encoding="utf-8", errors="ignore"),
            )
        )
    return rows


def census(rows: list[Row]):
    from cos_lib.measurement import Census

    counted = {"mentira": 0, "honesto": 0}
    blind = {"ambiguo: nombra la variable sin nombrar vía": 0, "código, no mensaje": 0}
    for r in rows:
        if r.verdict == "mentira":
            counted["mentira"] += 1
        elif r.verdict == "honesto":
            counted["honesto"] += 1
        elif r.verdict == "ambiguo":
            blind["ambiguo: nombra la variable sin nombrar vía"] += 1
        else:
            blind["código, no mensaje"] += 1
    return Census(
        subject="kill-switches de hooks con vía de activación ejecutable",
        sources=("hooks/**/*.sh (rglob, symlinks resueltos, _lib y _archived incluidos)",),
        buckets=counted,
        blind=blind,
        how=HOW,
        notes=(
            "VAR=1 <cmd-de-adentro> no llega al hook: el hook es hijo del arnés",
            "VAR=1 claude (al LANZAR), export previo, settings.json y bypass.env sí funcionan",
            "no distingue una oferta de la CITA de una oferta: un comentario que "
            "documenta la forma rota cuenta como mentira. Cuenta de más, no de menos.",
        ),
    )


def offenders(rows: list[Row]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for r in rows:
        if r.verdict == "mentira":
            out.setdefault(r.file, []).append(f"{r.var}@{r.line}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="filas crudas en JSON")
    args = ap.parse_args()
    rows = collect()
    if args.json:
        print(json.dumps([r.__dict__ for r in rows], ensure_ascii=False, indent=2))
        return 0
    c = census(rows)
    print(c.render() if hasattr(c, "render") else c)
    print()
    bad = offenders(rows)
    for f in sorted(bad):
        print(f"  MIENTE  {f}: {', '.join(sorted(bad[f]))}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

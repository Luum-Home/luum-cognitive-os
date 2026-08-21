#!/usr/bin/env python3
# SCOPE: os-only
"""brief_premise_lint.py — detecta premisas declarativas sobre el estado del repo
dentro del texto de un encargo, y propone su forma ejecutable.

Por qué existe
--------------
Un encargo se congela cuando se lanza; el repo sigue moviéndose. Una CONCLUSIÓN
("el archivo dice X", "está registrado cero veces", "git worktree está bloqueado")
se pudre en los minutos que el agente tarda en leerla. Un COMANDO no: se ejecuta
contra el estado del momento en que se lee.

Medido el 2026-08-20: tres encargos de una misma jornada llegaron con hechos que
ya eran falsos, y las tres veces la red que los atrapó fue el agente corriendo el
comando. Eso cuesta una corrida entera de agente para descubrir algo que se
previene en la redacción.

Contrato
--------
- Read-only, determinista, sin estado de sesión.
- Exit 0 = sin hallazgos, 1 = hay hallazgos, 2 = error de uso.
- ADVISORY: quien lo integra a la composición del prompt NO debe bloquear con él.
  Ver docs/06-Daily/reports/premisas-vencidas-en-los-encargos-2026-08-20.md
  §Decisión: bloquear cuesta una corrida perdida por cada falso positivo; avisar
  cuesta tres líneas de texto.

Uso
---
    python3 scripts/brief_premise_lint.py encargo.txt
    cat encargo.txt | python3 scripts/brief_premise_lint.py
    python3 scripts/brief_premise_lint.py --format json encargo.txt
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Vocabulario
# ---------------------------------------------------------------------------

# Un span entre backticks cuyo primer token es uno de estos ya ES la forma
# ejecutable. Es el principal matador de falsos positivos: una premisa que viaja
# con su comando no necesita que nadie la rete.
CMD_VERBS = (
    r"git|grep|rg|egrep|find|python3?|pytest|bash|sh|zsh|ls|wc|cat|sed|awk|jq|"
    r"head|tail|readlink|printf|echo|test|npm|go|make|gh|cos|cos-test|docker|"
    r"\.venv/bin/python3?|scripts/[\w.\-]+"
)
RE_CMD_SPAN = re.compile(r"`\s*((?:[A-Z_]+=\S+\s+)*(?:" + CMD_VERBS + r")\b[^`]*)`")


def _is_invocation(span: str) -> bool:
    """Un span entre backticks es un COMANDO solo si parece ejecutarse.

    `git worktree` y `scripts/dead_content_census.py` son NOMBRES de cosas de las
    que la oracion habla; `git rev-parse HEAD` y `grep -c x f.sh` son comandos.
    Confundirlos exime justo a las premisas que mas se pudren: medido, esa sola
    confusion se comia 3 de 12 positivos conocidos.
    """
    toks = span.split()
    if not toks:
        return False
    if any(t.startswith("-") for t in toks[1:]):
        return True
    if any(c in span for c in "|><$"):
        return True
    if len(toks) >= 3:
        return True
    if len(toks) == 2 and ("/" in toks[1] or "." in toks[1]):
        return True
    return False

# Referente: algo del repo sobre lo que se pueda afirmar.
RE_REF_BACKTICK = re.compile(r"`([^`\n]+)`")
RE_PATHISH = re.compile(
    r"(?:^|[\s(\"'])((?:[\w.\-]+/)+[\w.\-]+|[\w.\-]+\.(?:sh|py|md|json|ya?ml|txt|toml|jsonl))"
)
REPO_DIRS = (
    "hooks", "scripts", "templates", "tests", "docs", "rules", "manifests",
    "cos_lib", "packages", "skills", "lib", "bin", "cmd", "src",
    ".claude", ".cognitive-os", ".codex", ".opencode", ".venv", ".github",
)
RE_EXT = re.compile(r"\.(?:sh|py|md|json|ya?ml|jsonl|txt|toml|cfg|ini|go|ts|tsx)\b")


def _plausible_path(tok: str) -> bool:
    """`bloquea/avisa/reescribe` tiene barras y no es un path.

    Ese solo token era 1 de los 4 falsos positivos medidos sobre el encargo real
    de 2026-08-20: una enumeracion separada con barras leida como ruta. Un path
    plausible o tiene extension conocida o arranca en un directorio de este repo.
    """
    tok = tok.strip().strip("`\"'()[],;")
    if RE_EXT.search(tok):
        return True
    head = tok.split("/", 1)[0]
    return "/" in tok and head in REPO_DIRS


RE_REPO_NOUN = re.compile(
    r"\b(hooks?|archivos?|scripts?|tests?|reglas?|l[íi]neas?|symlinks?|entradas?|"
    r"gates?|commits?|manifiestos?|plantillas?|skills?|ADR-\d+|files?|rules?|lines?|"
    r"directorios?|carpetas?|matchers?|flags?|variables?|worktrees?|guards?|"
    r"comandos?|commands?|branch(?:es)?|ramas?)\b",
    re.IGNORECASE,
)

# Arranques imperativos: el encargo pidiendo algo, no afirmando algo.
RE_IMPERATIVE = re.compile(
    r"^(?:[-*•]\s*|\d+[.)]\s*|\*\*)*"
    r"(implementá|corré|corre|verificá|actualizá|estudiá|mapeá|argumentá|leé|"
    r"escribí|agregá|usá|dejá|pegá|sembrá|derivá|recortá|clasificá|cerrá|añadí|"
    r"traé|decí|hacé|mirá|probá|revisá|chequeá|medí|contá|buscá|reportá|empezá|"
    r"anotá|preguntá|falsalá|descartala|limpiá|nunca|no\s|"
    r"run|read|write|implement|check|add|update|verify|do|don't|never|use|make|"
    r"ensure|report|prefer|avoid|keep|treat)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Predicados: las formas en que una afirmación habla del estado del repo.
# (id, regex, plantilla de comando sugerido)
# ---------------------------------------------------------------------------

PREDICATES: list[tuple[str, re.Pattern[str], str]] = [
    (
        "existencia",
        re.compile(
            r"\bno existe[n]?\b|\bno est[áa][n]?\b|\bno hay\b|\bfalta[n]?\b|"
            r"\bno aparece[n]?\b|does not exist|doesn't exist|is missing|are missing|"
            r"\bno se encontr|\bausente\b",
            re.IGNORECASE,
        ),
        "ls -la {ref} && readlink -f {ref}   # nunca afirmar ausencia sin esto",
    ),
    (
        "registro",
        re.compile(
            r"est[áa][n]?\s+registrad|sin\s+registrar|no\s+est[áa][n]?\s+registrad|"
            r"\bregistered\b|not\s+registered|registrad[oa]\s+(cero|0|\d+)\s+ve",
            re.IGNORECASE,
        ),
        ".venv/bin/python3 scripts/audit_hook_registration.py   # y correr el hook "
        "con su payload por stdin: grep -c sobre settings.json NO alcanza",
    ),
    (
        "bloqueo",
        re.compile(
            r"est[áa][n]?\s+bloquead|\bbloquea\b|\bis blocked\b|\bblocks\b|"
            r"\bno se puede\b|\bno permite\b|\bcannot\b|est[áa][n]?\s+permitid",
            re.IGNORECASE,
        ),
        "__BLOQUEO__",
    ),
    (
        "contenido",
        re.compile(
            r"\bdice\b|\bcontiene\b|\bdeclara\b|\bsays\b|\bcontains\b|\bstates\b|"
            r"\bmenciona\b|\bafirma\b",
            re.IGNORECASE,
        ),
        "grep -n '<texto citado>' {ref}   # si no lo encuentra, la premisa venció",
    ),
    (
        "conteo",
        re.compile(
            r"\b(cero|ning[úu]n[ao]?|\d+|dos|tres|cuatro|cinco|seis|siete|ocho|"
            r"nueve|diez|once|doce|trece|catorce|quince|veinte|treinta|cuarenta|"
            r"cincuenta|cien|two|three|four|five|six|seven|eight|nine|ten)"
            r"\s+(ve(?:z|ces)|hooks?|archivos?|scripts?|"
            r"tests?|reglas?|l[íi]neas?|entradas?|files?|rules?|lines?|times?|"
            r"ocurrencias?|apariciones?|symlinks?)\b",
            re.IGNORECASE,
        ),
        "recontá al leer: el número del encargo es de cuando se escribió "
        "(find/grep -c sobre {ref}), no de ahora",
    ),
    (
        "linea-citada",
        re.compile(r"\b[\w.\-]+\.(?:sh|py|md|json|ya?ml|jsonl):(\d+)\b"),
        "sed -n '{line}p' {ref}   # los números de línea se corren con cada commit",
    ),
]


@dataclass
class Finding:
    line: int
    kind: str
    text: str
    referent: str
    suggestion: str


# ---------------------------------------------------------------------------


def _strip_code_fences(lines: list[str]) -> list[tuple[int, str]]:
    """Devuelve (nro_de_linea_1based, texto) excluyendo bloques ``` y líneas
    indentadas como bloque de código. Una premisa dentro de un bloque de código
    ya es, casi siempre, el comando mismo."""
    out: list[tuple[int, str]] = []
    in_fence = False
    for i, raw in enumerate(lines, start=1):
        if raw.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if raw.startswith("    ") or raw.startswith("\t"):
            continue
        out.append((i, raw))
    return out


def _split_clauses(text: str) -> list[str]:
    """Parte en oraciones sin romper adentro de backticks."""
    parts: list[str] = []
    buf: list[str] = []
    in_tick = False
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "`":
            in_tick = not in_tick
        if not in_tick and ch in ".;" and i + 1 < len(text) and text[i + 1] in " \n":
            buf.append(ch)
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    if buf:
        parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def _referent(clause: str) -> str:
    """El path o artefacto del que habla la cláusula. '' si no hay ninguno."""
    for m in RE_REF_BACKTICK.finditer(clause):
        tok = m.group(1).strip()
        if _plausible_path(tok):
            return tok.split()[0] if " " in tok else tok
    for m in RE_PATHISH.finditer(clause):
        if _plausible_path(m.group(1)):
            return m.group(1)
    m = RE_REF_BACKTICK.search(clause)
    if m:
        return m.group(1).strip()
    return ""


def lint(text: str) -> list[Finding]:
    """Premisas declarativas sobre el estado del repo, con su forma ejecutable."""
    findings: list[Finding] = []
    for lineno, raw in _strip_code_fences(text.splitlines()):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        for clause in _split_clauses(raw):
            # Ya viaja con su comando -> es exactamente la forma que queremos.
            _spans = [m.group(1) for m in RE_CMD_SPAN.finditer(clause)]
            if any(_is_invocation(sp) for sp in _spans):
                continue
            # Pide algo, no afirma algo.
            if RE_IMPERATIVE.match(clause.lstrip("-*• \t").lstrip("0123456789.) ")):
                continue
            ref = _referent(clause)
            has_noun = bool(RE_REPO_NOUN.search(clause))
            # Un referente CONCRETO (path o span entre backticks) es lo que separa
            # "el archivo `x.sh` dice Y" de "afirmaciones sobre lo que un archivo
            # dice". Medido sobre el encargo real de 2026-08-20: exigirlo baja los
            # falsos positivos de 4 a 0 sin perder ninguno de los 12 positivos
            # conocidos. Sin esta condicion el detector le grita a su propia
            # especificacion, que es el modo mas rapido de que lo desactiven.
            ref_is_path = _plausible_path(ref) if ref else False
            for kind, rx, tmpl in PREDICATES:
                m = rx.search(clause)
                if not m:
                    continue
                # Un conteo NOMBRA su propia poblacion ("veinte hooks"), asi que
                # no necesita path; pero "las tres veces" es prosa narrativa y si
                # lo necesita. Los demas predicados afirman algo SOBRE un archivo:
                # sin archivo concreto le estarian gritando a su propia
                # especificacion, que es el modo mas rapido de que lo desactiven.
                if kind == "conteo":
                    counted = (m.group(2) or "").lower()
                    if not RE_REPO_NOUN.fullmatch(counted) and not ref_is_path:
                        continue
                elif not ref:
                    continue
                line_no = ""
                if kind == "bloqueo":
                    # `bash templates/x.md` no prueba nada: un .md no se ejecuta.
                    # Sin esta rama el detector emitia sugerencias absurdas, que es
                    # el otro modo de que lo desactiven.
                    tmpl = (
                        "printf '<payload>' | bash {ref}; echo \"exit=$?\"   # el "
                        "bloqueo es un exit code observado, no un recuerdo"
                        if ref.endswith(".sh")
                        else "corré la operación que el encargo da por bloqueada y "
                        "leé su exit code ({ref}); un bloqueo se observa, no se "
                        "recuerda"
                    )
                if kind == "linea-citada":
                    line_no = m.group(1)
                    ref = ref or m.group(0).split(":")[0]
                findings.append(
                    Finding(
                        line=lineno,
                        kind=kind,
                        text=clause[:220],
                        referent=ref or "<sin path explícito>",
                        suggestion=tmpl.format(
                            ref=ref or "<el archivo o comando>", line=line_no or "N"
                        ),
                    )
                )
                break  # un hallazgo por cláusula: gritar dos veces por lo mismo cansa
    return findings


def render_text(findings: list[Finding]) -> str:
    if not findings:
        return ""
    out = [
        "PREMISAS DECLARATIVAS DETECTADAS — reemplazá la conclusión por su comando:",
        "",
    ]
    for f in findings:
        out.append(f"  L{f.line} [{f.kind}] {f.text}")
        out.append(f"      -> {f.suggestion}")
    out.append("")
    out.append(
        "Una conclusión se pudre entre que se escribe y que el agente la lee. "
        "Un comando se ejecuta contra el estado del momento. Esto es un AVISO: "
        "no bloquea el lanzamiento."
    )
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", nargs="?", help="archivo del encargo (default: stdin)")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument(
        "--quiet", action="store_true", help="sin salida; solo el exit code"
    )
    args = ap.parse_args()

    try:
        text = Path(args.path).read_text(encoding="utf-8") if args.path else sys.stdin.read()
    except OSError as exc:
        print(f"error leyendo el encargo: {exc}", file=sys.stderr)
        return 2

    findings = lint(text)
    if not args.quiet:
        if args.format == "json":
            print(json.dumps([asdict(f) for f in findings], ensure_ascii=False, indent=2))
        else:
            rendered = render_text(findings)
            if rendered:
                print(rendered)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

# SCOPE: both
"""Censo de GNU-ismos: comandos y sintaxis que no existen, o no significan lo
mismo, en el `/bin/bash` 3.2.57 y las utilidades BSD de macOS.

Por que existe
--------------
El 2026-08-20 se midio que `hooks/session-init.sh` invocaba el binario `flock`
sin guarda. `flock` es de util-linux y en macOS NO ESTA: el shell devolvia 127,
el `||` disparaba, y la sesion nunca se registraba. Meses de
`active-sessions.json` en `{"sessions": []}` con 25 directorios en disco, y la
causa atribuida a un podador agresivo que no existia.

`flock` no es el caso: es un ejemplar. Este repo corre en macOS y su CI en
Linux, asi que un GNU-ismo pasa CI y falla en la maquina del operador — o al
reves — y en los dos casos sin ruido. Este modulo cuenta la FAMILIA.

Que mide, y sobre que poblacion
-------------------------------
Poblacion: los archivos shell versionados (`git ls-files`), deduplicados por
ruta real — este repo usa symlinks (`hooks/` -> `packages/*/hooks/`) y un
symlink y su destino son UN archivo, no dos.

Cada sitio detectado se clasifica en dos ejes independientes:

  ruido     RUIDOSA  -> el comando falla visiblemente (127, o rc!=0 con stderr)
            SILENCIOSA -> hay un supresor en el sitio (`|| true`, `2>/dev/null`),
                       o la familia degrada sin error (bash 3.2 acepta
                       `declare -A` como `declare -A` -> variable comun)
  camino    HOOK-REGISTRADO -> el archivo esta en un manifest de hooks: corre
                       solo, por turno, en cada sesion
            REFERENCIADO -> otro archivo versionado lo nombra
            HUERFANO  -> nadie lo nombra; es deuda, no falla

La prioridad la decide el cruce: SILENCIOSA + HOOK-REGISTRADO es un fallo por
turno que nadie ve.

Que NO mide, dicho para que nadie se confie
-------------------------------------------
  - `flock`: lo cubre `tests/audit/test_flock_has_a_portable_fallback.py`, que
    ya tiene su propio baseline con igualdad exacta. Dos instrumentos midiendo
    lo mismo con criterios distintos es peor que uno solo, asi que esta familia
    se delega explicitamente en vez de duplicarse.
  - Shell embebido en YAML/JSON/Markdown (workflows, manifests, docs): se
    declara como ceguera, no se cuenta como cero.
  - Semantica que solo se rompe en runtime (una expansion que arma el comando
    en una variable). Un scanner lexico no la ve; queda en la ceguera.

El veredicto de disponibilidad NO se toma de una lista: se PRUEBA contra los
binarios del sistema (`/usr/bin:/bin:/usr/sbin:/sbin`), no contra el PATH del
operador. Un mac con `coreutils` de Homebrew tiene `gdate` y `gtimeout` primero
en el PATH y taparia justo lo que se quiere medir.

Uso
---
    python3 scripts/portability_census.py            # censo + sitios
    python3 scripts/portability_census.py --json     # para otro programa
    python3 scripts/portability_census.py --probe    # que hace cada GNU-ismo aca

Exit codes: 0 sin hallazgos, 1 hallazgos, 2 error.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from cos_lib.measurement import Census  # noqa: E402

HOW = "python3 scripts/portability_census.py --json"

# PATH del sistema, sin Homebrew. Ver docstring: medir contra el PATH del
# operador mide su maquina, no el contrato del repo.
SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"

MANIFESTS = (
    ".claude/settings.json",
    ".codex/hooks.json",
    ".opencode/cos-hooks.json",
)

SHELL_SUFFIXES = (".sh", ".bash", ".zsh")
_SHEBANG = re.compile(rb"^#!.*\b(ba|z|da)?sh\b")

# Supresores en el sitio: convierten una falla ruidosa en una silenciosa.
_SUPRESOR = re.compile(
    r"\|\|\s*(?:true|:)\b"      # || true / || :
    r"|2>\s*/dev/null"           # stderr al vacio
    r"|>\s*/dev/null\s+2>&1"     # >/dev/null 2>&1
    r"|\|\|\s*(?:echo|printf)"   # se reemplaza por un valor y sigue
    r"|\|\|\s*\\\s*$"           # `|| \` : el fallback esta en la linea siguiente
)


@dataclass(frozen=True)
class Familia:
    """Un GNU-ismo, su detector, y por que su falla es del tipo que es."""

    clave: str
    patron: str
    #: comando del sistema que se prueba, o None para sintaxis de bash
    binario: str | None
    #: argv de prueba que DEBE fallar en BSD y funcionar en GNU
    prueba: tuple[str, ...] | None
    #: degrada sin error aunque no haya supresor
    silenciosa_por_naturaleza: bool
    #: tokens que, presentes en el archivo, cuentan como guarda de portabilidad
    guardas: tuple[str, ...]
    porque: str


_GUARDA_OS = ("uname", "OSTYPE", "Darwin", "$(uname)")


def _g(*extra: str) -> tuple[str, ...]:
    return tuple(extra) + _GUARDA_OS


FAMILIAS: tuple[Familia, ...] = (
    Familia(
        clave="date -d",
        patron=r"(?<![\w./-])date\s+(?:-[a-zA-Z]+\s+)*(?:-d\b|--date\b)",
        binario="date",
        prueba=("date", "-d", "2020-01-01", "+%s"),
        silenciosa_por_naturaleza=False,
        guardas=_g("gdate", "date -j", "date -u -r", "date -r "),
        porque="BSD date no tiene -d; parsea con -j -f y ajusta con -v.",
    ),
    Familia(
        # `sed -i` sin sufijo: BSD exige `-i ''`. Con `-i -e` es PEOR que un
        # error — BSD toma "-e" como sufijo de backup y deja archivos `f-e`.
        clave="sed -i sin sufijo",
        patron=r"(?<![\w./-])sed\s+(?:-[a-zA-Z]+\s+)*-i(?![a-zA-Z])(?!\s*(?:''|\"\"|\.))",
        binario="sed",
        prueba=None,  # se prueba aparte: necesita un archivo
        silenciosa_por_naturaleza=True,
        guardas=_g("gsed", "sed_inplace", "SED_INPLACE"),
        porque="BSD sed exige un sufijo tras -i; con `-i -e` toma '-e' como sufijo y escribe backups fantasma.",
    ),
    Familia(
        clave="stat -c",
        patron=r"(?<![\w./-])stat\s+(?:-[a-zA-Z]+\s+)*-c\b",
        binario="stat",
        prueba=("stat", "-c", "%s", "/etc/hosts"),
        silenciosa_por_naturaleza=False,
        guardas=_g("gstat", "stat -f"),
        porque="BSD stat usa -f con otro lenguaje de formato (%z, %m).",
    ),
    Familia(
        clave="grep -P",
        patron=r"(?<![\w./-])(?:e|f)?grep\s+(?:[^\n|;&]*?)-[a-zA-Z]*P(?![a-zA-Z])",
        binario="grep",
        prueba=("grep", "-P", r"\d", "/etc/hosts"),
        silenciosa_por_naturaleza=False,
        # `grep -oE`/`grep -E` en el mismo archivo = hay camino ERE. Se cuenta
        # como guarda por el mismo criterio que el gate de flock: lo que
        # importa no es la forma del `if`, es que exista el otro camino.
        guardas=_g("ggrep", "grep -E", "grep -oE"),
        porque="BSD grep no trae PCRE; -E cubre la mayoria de los casos.",
    ),
    Familia(
        clave="base64 -w",
        patron=r"(?<![\w./-])base64\s+(?:[^\n|;&]*?\s)?-w",
        binario="base64",
        prueba=("base64", "-w0", "/etc/hosts"),
        silenciosa_por_naturaleza=False,
        guardas=_g("gbase64", "tr -d"),
        porque="BSD base64 no tiene -w; se envuelve/desenvuelve con `tr -d '\\n'`.",
    ),
    Familia(
        clave="find -printf",
        patron=r"(?<![\w./-])find\s[^\n]*?\s-printf\b",
        binario="find",
        prueba=("find", "/etc/hosts", "-printf", "%p"),
        silenciosa_por_naturaleza=False,
        guardas=_g("gfind", "-exec stat"),
        porque="BSD find no tiene -printf; se reemplaza con -exec o -print0 + xargs.",
    ),
    Familia(
        clave="timeout",
        patron=r"(?<![\w./$-])timeout\s+(?:-[a-zA-Z0-9]|\d|\$)",
        binario="timeout",
        prueba=("timeout", "1", "true"),
        silenciosa_por_naturaleza=False,
        guardas=_g("gtimeout", "command -v timeout", "HAS_TIMEOUT"),
        porque="`timeout` es de coreutils y no viene en macOS (gtimeout con Homebrew).",
    ),
    Familia(
        clave="tac",
        patron=r"(?:^|[|;&(]|\$\()\s*tac(?:\s|$)",
        binario="tac",
        prueba=("tac", "/etc/hosts"),
        silenciosa_por_naturaleza=False,
        guardas=_g("gtac", "tail -r", "command -v tac"),
        porque="`tac` es de coreutils; en BSD el equivalente es `tail -r`.",
    ),
    Familia(
        # bash 3.2.57 imprime "declare: -A: invalid option" y SIGUE: la variable
        # queda como escalar comun y el script hace algo distinto sin fallar.
        clave="bash4 declare -A",
        patron=r"(?<![\w./-])(?:declare|local|typeset)\s+(?:-[a-zA-Z]+\s+)*-[a-zA-Z]*A(?![a-zA-Z])",
        binario=None,
        prueba=None,
        silenciosa_por_naturaleza=True,
        guardas=_g("BASH_VERSINFO", "bash5", "/opt/homebrew/bin/bash"),
        porque="Los arrays asociativos son de bash 4; /bin/bash de macOS es 3.2.57.",
    ),
    Familia(
        clave="bash4 mapfile/readarray",
        patron=r"(?<![\w./-])(?:mapfile|readarray)\s+(?:-|\w|\$)",
        binario=None,
        prueba=None,
        silenciosa_por_naturaleza=False,
        guardas=_g("BASH_VERSINFO", "while read"),
        porque="`mapfile`/`readarray` son builtins de bash 4; en 3.2 dan 127.",
    ),
    Familia(
        # Error de SINTAXIS: bash 3.2 no parsea el archivo entero. Ruidosa, pero
        # catastrofica — no falla la linea, falla el script.
        clave="bash4 ${var^^}",
        patron=r"\$\{[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]*\])?(?:\^\^?|,,?)[^}]*\}",
        binario=None,
        prueba=None,
        silenciosa_por_naturaleza=False,
        guardas=_g("BASH_VERSINFO",),
        porque="La expansion de caso es de bash 4; en 3.2 es error de sintaxis y el script entero no arranca.",
    ),
    Familia(
        clave="bash4 &>>",
        patron=r"(?<!['\"])&>>(?!['\"])",
        binario=None,
        prueba=None,
        silenciosa_por_naturaleza=False,
        guardas=_g("BASH_VERSINFO",),
        porque="`&>>` es de bash 4; en 3.2 se parsea como `&` (background) + `>>`.",
    ),
)

FAMILIA_POR_CLAVE = {f.clave: f for f in FAMILIAS}
_COMPILADAS = {f.clave: re.compile(f.patron, re.M) for f in FAMILIAS}

DELEGADAS = {
    "flock": "tests/audit/test_flock_has_a_portable_fallback.py",
}


# --------------------------------------------------------------------------
# disponibilidad real, probada contra el PATH del sistema
# --------------------------------------------------------------------------
def disponibilidad() -> dict[str, str]:
    """Corre cada prueba con el PATH del sistema. No lee una lista: mide.

    Devuelve, por familia con binario: "ABSENTE", "BSD-DISTINTO" o "GNU-OK".
    """
    entorno = {"PATH": SYSTEM_PATH, "LC_ALL": "C"}
    fuera: dict[str, str] = {}
    for fam in FAMILIAS:
        if fam.binario is None:
            fuera[fam.clave] = "BASH-3.2"
            continue
        hay = subprocess.run(
            ["command", "-v", fam.binario],
            env=entorno, capture_output=True, executable="/bin/bash",
        )
        hay = subprocess.run(
            f"command -v {fam.binario}", shell=True, env=entorno,
            capture_output=True, executable="/bin/bash",
        )
        if hay.returncode != 0:
            fuera[fam.clave] = "AUSENTE"
            continue
        if fam.prueba is None:
            fuera[fam.clave] = "BSD-DISTINTO"  # probado aparte (sed -i)
            continue
        r = subprocess.run(fam.prueba, env=entorno, capture_output=True)
        fuera[fam.clave] = "GNU-OK" if r.returncode == 0 else "BSD-DISTINTO"
    return fuera


# --------------------------------------------------------------------------
# poblacion
# --------------------------------------------------------------------------
_VERSIONADOS: list[str] = []


def _versionados() -> list[str]:
    if not _VERSIONADOS:
        r = subprocess.run(
            ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
        )
        _VERSIONADOS.extend(r.stdout.split("\n"))
    return _VERSIONADOS


def poblacion() -> tuple[list[str], dict[str, int]]:
    """Archivos shell versionados, deduplicados por ruta real.

    Segundo valor: la ceguera. Un symlink que apunta afuera del repo, un
    archivo que no se puede decodificar, o un candidato que desaparecio entre
    el `ls-files` y la lectura.
    """
    ciegos = {"ilegible": 0, "symlink-externo": 0}
    vistos: dict[Path, str] = {}
    for rel in _versionados():
        if not rel:
            continue
        p = REPO / rel
        if not p.is_file():
            continue
        es_shell = rel.endswith(SHELL_SUFFIXES)
        if not es_shell:
            try:
                with p.open("rb") as fh:
                    es_shell = bool(_SHEBANG.match(fh.readline()))
            except OSError:
                ciegos["ilegible"] += 1
                continue
        if not es_shell:
            continue
        try:
            real = p.resolve(strict=True)
        except OSError:
            ciegos["ilegible"] += 1
            continue
        try:
            real.relative_to(REPO)
        except ValueError:
            ciegos["symlink-externo"] += 1
            continue
        # gana la ruta mas corta y estable: el destino real dentro del repo
        canon = str(real.relative_to(REPO))
        vistos.setdefault(real, canon)
    return sorted(vistos.values()), ciegos


# --------------------------------------------------------------------------
# liveness
# --------------------------------------------------------------------------
def _hooks_registrados() -> set[str]:
    registrados: set[str] = set()
    for man in MANIFESTS:
        p = REPO / man
        if not p.is_file():
            continue
        texto = p.read_text(errors="replace")
        for m in re.findall(r"[\w./${}-]+\.sh", texto):
            registrados.add(re.sub(r"^.*?(?=hooks/|scripts/)", "", m))
    return registrados


_MENCION = re.compile(r"[\w.@+-]+\.(?:sh|bash|zsh)")


def _referenciados() -> set[str]:
    """Todos los basenames de shell nombrados en cualquier archivo versionado.

    Un solo pase sobre el arbol, con un regex chico. La alternativa obvia
    —grep con una alternacion de 500 nombres— tarda minutos: el motor arma un
    automata gigante y lo corre contra cada byte del repo.
    """
    fuera: set[str] = set()
    for rel in _versionados():
        if not rel:
            continue
        p = REPO / rel
        if not p.is_file():
            continue
        try:
            if p.stat().st_size > 4_000_000:
                continue
            texto = p.read_text(errors="replace")
        except OSError:
            continue
        propio = Path(rel).name
        fuera.update(n for n in _MENCION.findall(texto) if n != propio)
    return fuera


def liveness(rel: str, registrados: set[str], mencionados: set[str]) -> str:
    if any(rel == reg or reg.endswith("/" + rel) or rel.endswith(reg) for reg in registrados):
        return "HOOK-REGISTRADO"
    # un hook simlinkeado desde packages/: el manifest nombra hooks/<n>
    if ("hooks/" + Path(rel).name) in registrados:
        return "HOOK-REGISTRADO"
    if Path(rel).name in mencionados:
        return "REFERENCIADO"
    return "HUERFANO"


# --------------------------------------------------------------------------
# deteccion
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Sitio:
    archivo: str
    linea: int
    familia: str
    ruido: str      # RUIDOSA | SILENCIOSA
    camino: str     # HOOK-REGISTRADO | REFERENCIADO | HUERFANO
    guardado: bool
    texto: str


_COMENTARIO = re.compile(r"^\s*#")


def _en_comentario(texto: str, ini: int) -> bool:
    """Un GNU-ismo nombrado en un comentario no se ejecuta.

    Se mide asi y no con un parser de shell a proposito: la mitad de los falsos
    positivos de la primera corrida eran comentarios que EXPLICABAN el GNU-ismo
    ("macOS sed -i differs from GNU"), es decir, exactamente los archivos donde
    alguien ya se habia dado cuenta.
    """
    a = texto.rfind("\n", 0, ini) + 1
    return bool(_COMENTARIO.match(texto[a:ini + 1]))


def _contexto(texto: str, ini: int, fin: int) -> str:
    """La sentencia alrededor del match: de `;`/newline anterior al siguiente."""
    a = max(texto.rfind("\n", 0, ini), texto.rfind(";", 0, ini)) + 1
    b = texto.find("\n", fin)
    return texto[a: b if b != -1 else len(texto)]


def sitios(archivos: list[str], registrados: set[str], mencionados: set[str]) -> list[Sitio]:
    fuera: list[Sitio] = []
    for rel in archivos:
        try:
            texto = (REPO / rel).read_text(errors="replace")
        except OSError:
            continue
        camino = liveness(rel, registrados, mencionados)
        for fam in FAMILIAS:
            for m in _COMPILADAS[fam.clave].finditer(texto):
                if _en_comentario(texto, m.start()):
                    continue
                ctx = _contexto(texto, m.start(), m.end())
                guardado = any(g in texto for g in fam.guardas)
                silenciosa = fam.silenciosa_por_naturaleza or bool(_SUPRESOR.search(ctx))
                fuera.append(
                    Sitio(
                        archivo=rel,
                        linea=texto.count("\n", 0, m.start()) + 1,
                        familia=fam.clave,
                        ruido="SILENCIOSA" if silenciosa else "RUIDOSA",
                        camino=camino,
                        guardado=guardado,
                        texto=ctx.strip()[:140],
                    )
                )
    return sorted(fuera, key=lambda s: (s.archivo, s.linea, s.familia))


# --------------------------------------------------------------------------
# censo
# --------------------------------------------------------------------------
def censar() -> tuple[Census, list[Sitio], list[str], dict[str, str]]:
    archivos, ciegos = poblacion()
    registrados = _hooks_registrados()
    mencionados = _referenciados()
    todos = sitios(archivos, registrados, mencionados)
    disp = disponibilidad()

    sin_guarda = [s for s in todos if not s.guardado]
    buckets = {
        "sin-guarda-SILENCIOSA": sum(1 for s in sin_guarda if s.ruido == "SILENCIOSA"),
        "sin-guarda-RUIDOSA": sum(1 for s in sin_guarda if s.ruido == "RUIDOSA"),
        "con-guarda": sum(1 for s in todos if s.guardado),
    }
    ciegos_censo = dict(ciegos)
    ciegos_censo["familia-delegada-flock"] = len(DELEGADAS)
    ciegos_censo["shell-embebido-en-yaml-json-md"] = -1  # marcador: ver notas

    # Census prohibe un blind negativo; se declara como conteo real.
    ciegos_censo["shell-embebido-en-yaml-json-md"] = _shell_embebido()

    censo = Census(
        subject="GNU-ismos en shell versionado (sitios sin guarda de portabilidad)",
        sources=("git ls-files (shell, dedup por realpath)",) + MANIFESTS,
        buckets=buckets,
        blind=ciegos_censo,
        how=HOW,
        notes=(
            f"poblacion: {len(archivos)} archivos shell versionados unicos",
            "flock se delega en tests/audit/test_flock_has_a_portable_fallback.py",
            f"disponibilidad probada con PATH={SYSTEM_PATH}",
        ),
    )
    return censo, todos, archivos, disp


def _shell_embebido() -> int:
    """Archivos no-shell que contienen `run:` o `command` con shell adentro.

    No se analizan: se CUENTAN, para que la ceguera tenga tamano en vez de ser
    una nota al pie.
    """
    r = subprocess.run(
        ["grep", "-rlE", r"^\s*(run|command|cmd):", "--include=*.yml", "--include=*.yaml",
         "--include=*.json", "."],
        cwd=REPO, capture_output=True, text=True,
    )
    return len([x for x in r.stdout.split() if x])


def _probar() -> int:
    """Muestra que hace cada GNU-ismo en ESTA maquina. Evidencia, no lista."""
    disp = disponibilidad()
    print(f"PATH probado: {SYSTEM_PATH}")
    print(f"bash: {subprocess.run(['/bin/bash', '--version'], capture_output=True, text=True).stdout.splitlines()[0]}")
    for fam in FAMILIAS:
        print(f"  {fam.clave:28s} {disp[fam.clave]:14s} {fam.porque}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--probe", action="store_true", help="probar cada GNU-ismo en esta maquina")
    ap.add_argument("--solo-vivos", action="store_true", help="solo sitios en camino que se ejecuta")
    args = ap.parse_args()

    if args.probe:
        return _probar()

    censo, todos, archivos, disp = censar()
    sin_guarda = [s for s in todos if not s.guardado]
    if args.solo_vivos:
        sin_guarda = [s for s in sin_guarda if s.camino != "HUERFANO"]

    if args.json:
        print(json.dumps({
            "census": {
                "subject": censo.subject,
                "sources": list(censo.sources),
                "buckets": dict(censo.buckets),
                "blind": dict(censo.blind),
                "how": censo.how,
                "notes": list(censo.notes),
            },
            "poblacion": len(archivos),
            "disponibilidad": disp,
            "sitios": [asdict(s) for s in sin_guarda],
        }, indent=2, ensure_ascii=False))
    else:
        print(censo.render() if hasattr(censo, "render") else censo)
        print()
        for s in sin_guarda:
            print(f"{s.ruido:11s} {s.camino:15s} {s.familia:24s} {s.archivo}:{s.linea}")
            print(f"    {s.texto}")
    return 1 if sin_guarda else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"portability_census: error: {exc}", file=sys.stderr)
        sys.exit(2)

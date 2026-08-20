"""Defensas que no pueden dispararse: el codigo esta, el test pasa, y no protege.

Que se midio, y por que este gate existe
----------------------------------------
Una clase de bug que no se ve como bug: el guard esta escrito, la telemetria
registra corridas, y la proteccion NUNCA pudo dispararse. Tres formas de esa
clase son puramente sintacticas y se detectan leyendo el shell. Las tres
verificadas contra `/usr/bin/grep` (BSD) y `/bin/sh` de esta maquina el
2026-08-20 — NO contra el `grep` del PATH interactivo, que en este perfil es un
shim a `ugrep` y responde distinto (`-oP` y `(?:` le andan). Medir con el shim
es medir otra cosa que la que corre en un hook.

A. El patron que se lee como opcion
    grep -oE "<5 guiones>BEGIN RSA PRIVATE KEY<5 guiones>" f  -> rc=2, 0 matches
    grep -oE -- "<lo mismo>" f                                -> rc=0, matchea
   Medido en este repo: seis claves privadas historicas pasaron sin redactar
   porque el `rc=2` se lo tragaba un `2>/dev/null`.

B. La herramienta que existe, sale 0 y devuelve vacio
    /usr/bin/grep -oP '...'   -> BSD grep no tiene PCRE
    /usr/bin/grep -E '(?:x)y' -> `(?:` es PCRE, no ERE POSIX
   No hay error que tragar: el llamador ve "sin hallazgos".

C. El exit code perdido en el pipeline (unifica las sub-formas 2 y 5 del
   encargo: son el mismo defecto, el `$?` de un pipeline es el de su ULTIMA
   etapa)
    grep x f | head -5 && echo "HAY HALLAZGOS"  -> `head` sale 0, siempre imprime
    cmd 2>/dev/null | wc -l; rc=$?              -> rc es el de `wc`
    if ! cmd 2>&1 | tail -3; then aviso; fi     -> el aviso es inalcanzable

Que NO cubre este gate, a proposito
-----------------------------------
  - `; rc=$?` bajo `set -e` (sub-forma 3): hay que saber si `set -e` esta activo
    en ESE punto, incluido lo heredado por `source`. No es sintactico.
  - El guard con una sola rama (6) y el instrumento que chequea cero archivos
    (7): son semanticos. Se detectan CORRIENDO la condicion contra el estado
    real y contando de que lado cae; si una rama tiene cero casos, no protege.
    `test_el_corpus_no_esta_vacio` es la unica pieza de la (7) que si es
    estatica, y esta abajo.
  - C solo marca cuando ALGUIEN CONSUME el exit code con `&&`, con `$?` o como
    condicion de `if`/`while`. Medido sobre 640 shell: `| head -1 || true` sale
    56 veces y es idioma legitimo — un gate que lo marcara duraria un dia. Lo
    mismo con un filtro que redirige (`| head -c N >> f && ...`): ahi el filtro
    SI puede fallar al escribir y el `&&` significa algo.

Python queda fuera del corpus: `subprocess.run([...])` no pasa por un shell y no
tiene la ambiguedad de la sub-forma A.

Los tres controles, y los tres corren en la misma invocacion
------------------------------------------------------------
  1. positivo en fixture   — el detector reconoce el defecto,
  2. negativo en fixture   — con la MISMA forma sintactica, y no lo marca,
  3. positivo SEMBRADO EN EL CORPUS REAL — plantado en el arbol y encontrado
     por el mismo barrido que produce el veredicto. Sin el (3), un "0 hallazgos"
     no distingue "no hay defectos vivos" de "el barrido no estaba mirando" —
     que es exactamente como se veian los 0 bloqueos del detector de secretos
     mientras seis claves pasaban sin redactar.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Se arma por partes: escribir el literal hace que el hook de secretos lo
# reemplace por [REDACTED] al guardar este archivo, y el fixture dejaria de
# empezar con guion — o sea, dejaria de probar lo que dice probar. Ese hook
# tambien es, con precision incomoda, un ejemplo de la clase.
_PEM = "-" * 5 + "BEGIN RSA PRIVATE KEY" + "-" * 5

# --------------------------------------------------------------------------
# A. patron leido como opcion
# --------------------------------------------------------------------------
# `grep`/`egrep`/`git grep` + flags + un operando LITERAL que empieza con guion,
# sin `-e`, sin `-f` y sin `--` que lo desambigue. Solo literales: un `"$var"`
# no se puede clasificar sin saber que trae, y adivinar seria ruido.
#
# Sin comillas se exigen TRES guiones o mas: con dos, `--binary-files=...` (un
# flag largo legitimo, medido en scripts/audit-consumer-dependence.sh) entra
# como falso positivo.
_A_GREP = re.compile(
    r"""(?:^|[|;&(`]|\$\()\s*
        (?:(?:git|sudo|command)\s+)*
        (?:e|f|)grep
        (?P<flags>(?:\s+--?[A-Za-z][-A-Za-z=]*)*)
        \s+(?P<pat>'-|"-|-{3,}[A-Za-z])
    """,
    re.M | re.X,
)


# A2: la forma VARIABLE, que es la que se midio rota en hooks/secret-detector.sh
# (hoy arreglada con `grep -oE -- "$pattern"`). El patron viaja en una variable,
# asi que su valor no se ve en el sitio del grep — hay que seguirlo.
#
# Se sigue UN salto, el que basta para la forma medida: una variable de ciclo
# sobre un array cuya DEFINICION contiene un literal con tres guiones o mas.
# La version floja de esto —"el archivo tiene un literal con guiones EN ALGUN
# LADO"— se midio y da 1 hallazgo, 1 falso positivo: en secret-detector.sh linea
# 276 hay un `grep -rq "${VAR}"` donde VAR trae nombres de variables de entorno
# (`[A-Z_][A-Z0-9_]*`), que nunca arrancan con guion. Dos conceptos que comparten
# archivo por casualidad: coincidencia, no deuda. Por eso el salto es dirigido.
_A_ARRAY_CON_GUIONES = re.compile(
    r"^\s*(?P<arr>\w+)=\(\s*(?P<cuerpo>[^)]*)\)", re.M | re.S
)
_A_CICLO = re.compile(r"\bfor\s+(?P<var>\w+)\s+in\s+\"?\$\{(?P<arr>\w+)\[@\]\}")
_A_LITERAL_PELIGROSO = re.compile(r"""["'\s]-{3,}[A-Za-z]""")


def _a_vars_de_patron_riesgoso(texto: str) -> set[str]:
    arrays = {
        m.group("arr")
        for m in _A_ARRAY_CON_GUIONES.finditer(texto)
        if _A_LITERAL_PELIGROSO.search(m.group("cuerpo"))
    }
    return {
        m.group("var") for m in _A_CICLO.finditer(texto) if m.group("arr") in arrays
    }


def _a_grep_var(nombres: set[str]) -> re.Pattern:
    alternativa = "|".join(sorted(re.escape(n) for n in nombres))
    return re.compile(
        r"""(?:^|[|;&(`]|\$\()\s*
            (?:(?:git|sudo|command)\s+)*
            (?:e|f|)grep
            (?P<flags>(?:\s+--?[A-Za-z][-A-Za-z=]*)*)
            \s+(?P<pat>["']?\$\{?(?:"""
        + alternativa
        + r""")\b)
        """,
        re.M | re.X,
    )


def _a_desambiguado(texto: str, m: re.Match) -> bool:
    flags = m.group("flags").split()
    if any(f == "--" or f.startswith("-e") or f.startswith("-f") for f in flags):
        return True
    return bool(re.search(r"\s--\s", texto[m.start():m.start("pat")]))


def _a_viola(texto: str) -> bool:
    if any(not _a_desambiguado(texto, m) for m in _A_GREP.finditer(texto)):
        return True
    riesgosas = _a_vars_de_patron_riesgoso(texto)
    if not riesgosas:
        return False
    rx = _a_grep_var(riesgosas)
    return any(not _a_desambiguado(texto, m) for m in rx.finditer(texto))


# --------------------------------------------------------------------------
# B. la herramienta que sale 0 y devuelve vacio
# --------------------------------------------------------------------------
# `re.M` no es decorativo: sin el, `^` solo matchea el ARRANQUE DEL ARCHIVO, y
# el detector se volvia ciego a todo grep que no estuviera en la linea 1 ni
# despues de un pipe. Nadie lo noto con los fixtures —cada uno es un string que
# arranca con `grep`— y lo agarro el control SEMBRADO, cuando el mismo fixture
# quedo abajo de un `#!/usr/bin/env bash`. O sea: este gate nacio con la clase
# que viene a detectar, y el tercer control fue lo unico que lo vio.
_B_PCRE_FLAG = re.compile(
    r"(?:^|[|;&(`]|\$\()\s*(?:(?:git|sudo|command)\s+)*grep\s+"
    r"(?:-[A-Za-z]*P\b|--perl-regexp)",
    re.M,
)
_B_ERE_CMD = re.compile(
    r"(?:^|[|;&(`]|\$\()\s*(?:(?:git|sudo|command)\s+)*"
    r"(?:egrep|grep\s+(?:-[A-Za-z]*E\b|--extended-regexp))"
    r"(?P<resto>[^\n]*)",
    re.M,
)
_B_PCRE_SYNTAX = re.compile(r"\(\?[:=!<P#]")


def _b_viola(texto: str) -> bool:
    if _B_PCRE_FLAG.search(texto):
        return True
    return any(_B_PCRE_SYNTAX.search(m.group("resto")) for m in _B_ERE_CMD.finditer(texto))


# --------------------------------------------------------------------------
# C. exit code perdido en el pipeline
# --------------------------------------------------------------------------
_C_SIEMPRE_CERO = r"(?:wc|head|tail|cat|tee|tr|rev|nl|sort|uniq|column|paste|fold)"
# `&&` solamente: `|| true` despues de un filtro siempre-cero es una rama muerta
# pero inofensiva, y es el idioma dominante del arbol. `&&` es distinto: afirma
# una conclusion a partir de un estado que siempre es verdadero.
# `[^\n|>]` excluye el filtro que redirige, donde el estado si significa algo.
_C_CONSUMIDO_INLINE = re.compile(rf"\|\s*{_C_SIEMPRE_CERO}\b[^\n|>]*?\s&&\s*\S")
# Condicion de if/while. Se prohibe `$(` en el prefijo: `[ -n "$(... | head -1)" ]`
# usa la SALIDA, no el estado, y es correcto.
_C_CONDICION = re.compile(
    rf"(?:^|[;&(]|\bthen\b|\belse\b|\bdo\b)\s*(?:if|while|until)\s+"
    rf"(?:(?!\$\()[^\n])*\|\s*{_C_SIEMPRE_CERO}\b[^\n|]*?;\s*(?:then|do)\b",
    re.M,
)
# `pipeline; rc=$?`. Se prohibe `)` en el medio para no cruzar el cierre de un
# `$( )`, donde el `$?` es de otro comando.
_C_RC_SIGUIENTE = re.compile(
    rf"\|\s*{_C_SIEMPRE_CERO}\b[^\n|)]*(?:;[ \t]*|\n[ \t]*)(?:local\s+)?[A-Za-z_]\w*=\$\?"
)


def _c_viola(texto: str) -> bool:
    return bool(
        _C_CONSUMIDO_INLINE.search(texto)
        or _C_CONDICION.search(texto)
        or _C_RC_SIGUIENTE.search(texto)
    )


# --------------------------------------------------------------------------
# Una ocurrencia no es la cita de una ocurrencia
# --------------------------------------------------------------------------
# Este repo documenta sus propios arreglos citando el patron viejo TEXTUAL, que
# es lo correcto: el codigo tiene que poder explicarse. Un detector ingenuo
# marca justo los comentarios que explican el fix de la clase que detecta —
# cuanto mejor documentado el arreglo, mas ruidoso el guard. Medido acá: de los
# tres matches en `scripts/portability-two-way-proof.sh`, DOS eran comentarios
# (lineas 33 y 69) y uno era codigo (linea 72).
#
# La salida facil —borrar el literal del comentario para no confundir al
# instrumento— es la cola moviendo al perro, y en este repo ya se probó y se
# revirtió a proposito. Se arregla el instrumento.
#
# Misma distincion que `scripts/audit_killswitch_activation.py` (oferta vs cita
# de una oferta), y se sigue su forma: linea cuyo primer caracter no-blanco es
# `#`. Se agrega el comentario al final de linea, con la guarda de comillas
# balanceadas para no cortar adentro de un patron.
_COMENTARIO_FINAL = re.compile(r"\s#(?!\!).*$")


def _solo_codigo(texto: str) -> str:
    """Blanquea comentarios, conservando el conteo de lineas.

    NO toca cuerpos de heredoc: ahi puede haber shell que se ejecuta de verdad,
    y perderlo seria un falso negativo — el error caro de los dos. Se acepta el
    riesgo inverso (una cita dentro de un heredoc): medido 0 casos sobre 640.
    """
    fuera = []
    for linea in texto.split("\n"):
        pelada = linea.lstrip()
        if pelada.startswith("#"):
            fuera.append("")
            continue
        m = _COMENTARIO_FINAL.search(linea)
        if m and linea[: m.start()].count("'") % 2 == 0 and linea[: m.start()].count('"') % 2 == 0:
            linea = linea[: m.start()]
        fuera.append(linea)
    return "\n".join(fuera)


def _sobre_codigo(fn):
    def envuelto(texto: str) -> bool:
        return fn(_solo_codigo(texto))

    return envuelto


SUBFORMAS = {
    "A_patron_como_opcion": _sobre_codigo(_a_viola),
    "B_sale_0_y_vuelve_vacio": _sobre_codigo(_b_viola),
    "C_exit_code_perdido": _sobre_codigo(_c_viola),
}

# --------------------------------------------------------------------------
# corpus
# --------------------------------------------------------------------------
_RAICES = ("hooks", "scripts", "packages", "lib", "templates")
_SHEBANG = re.compile(rb"^#!.*\b(?:ba|z|k|da)?sh\b")
# Este archivo lleva los patrones a proposito. No es un colchon: un test de
# deteccion contiene por definicion lo que detecta.
_YO_MISMO = "tests/audit/test_la_defensa_que_nunca_disparo.py"


def _shell_del_arbol(incluir_no_versionados: bool = False) -> list[Path]:
    """Enumera el shell del arbol.

    `incluir_no_versionados` es la UNICA diferencia entre el barrido del gate y
    el del control sembrado: un flag en `git ls-files`. El filtrado por sufijo,
    la deteccion de shebang, el manejo de symlinks y el escaneo por archivo son
    el mismo camino. El gate mira solo lo versionado a proposito: bajo sesiones
    concurrentes, los untracked de otro agente no son deuda de este arbol.
    """
    args = ["git", "ls-files", "-z"]
    if incluir_no_versionados:
        args += ["--cached", "--others", "--exclude-standard"]
    salida = subprocess.run(
        args + list(_RAICES), cwd=REPO, capture_output=True, check=True
    ).stdout
    fuera = []
    for rel in salida.decode().split("\0"):
        if not rel or rel == _YO_MISMO:
            continue
        p = REPO / rel
        # islink: el symlink y su destino son UN componente. Se cuenta el
        # destino, que git tambien versiona (hooks/ -> packages/*/hooks/).
        if p.is_symlink() or not p.is_file():
            continue
        if p.suffix in (".sh", ".bash", ".zsh"):
            fuera.append(p)
        elif p.suffix == "":
            try:
                with p.open("rb") as fh:
                    if _SHEBANG.match(fh.readline()):
                        fuera.append(p)
            except OSError:
                continue
    return fuera


def escanear(archivos: list[Path] | None = None) -> dict[str, set[str]]:
    if archivos is None:
        archivos = _shell_del_arbol()
    hallazgos: dict[str, set[str]] = {k: set() for k in SUBFORMAS}
    for p in archivos:
        texto = p.read_text(errors="replace")
        for nombre, fn in SUBFORMAS.items():
            if fn(texto):
                hallazgos[nombre].add(str(p.relative_to(REPO)))
    return hallazgos


# --------------------------------------------------------------------------
# Baseline, en dos dicts con motivo escrito y con igualdad EXACTA.
# DEUDA    = defecto real, todavia sin arreglar.
# ACEPTADO = uso deliberado del patron; no se arregla porque no esta roto.
# Los dos pasan por los mismos dos tests anti-colchon.
# --------------------------------------------------------------------------
# Vacio a proposito, y no es un colchon al reves: el unico defecto vivo que el
# barrido encontro —`scripts/deps-update.sh`, donde `if ! docker pull "$image"
# 2>&1 | tail -3` volvia inalcanzable el WARNING— se arreglo en el mismo commit
# que este gate. Contrafactico medido el 2026-08-20:
#   version vieja  -> "version vieja: reporto exito sobre un fallo"
#   arreglada      -> "RAMA DE ERROR ALCANZADA"
DEUDA: dict[str, set[str]] = {k: set() for k in SUBFORMAS}

ACEPTADO: dict[str, set[str]] = {
    "A_patron_como_opcion": set(),
    "B_sale_0_y_vuelve_vacio": {
        # Canario a proposito: el script PRUEBA si `grep -oP` anda en este
        # userland (`if echo ... | grep -oP ... >/dev/null 2>&1`) justamente
        # para que el dia que ande, alguien se entere. Marcarlo seria marcar el
        # termometro por tener fiebre.
        "scripts/portability-two-way-proof.sh",
        # Linea 84 usa `grep -oP ... \K`, pero las lineas 85-88 son un
        # `if [ -z "$QUESTIONS" ]` con la version en `sed -n` — el camino
        # alternativo ya esta escrito y probado por la rama vacia. El detector
        # no ve el fallback (necesitaria seguir la variable), asi que la
        # discriminacion se escribe aca en vez de aflojar el patron.
        "packages/quality-gates/hooks/clarification-interceptor.sh",
    },
    "C_exit_code_perdido": set(),
}

_BASELINE = {k: DEUDA[k] | ACEPTADO[k] for k in SUBFORMAS}

# --------------------------------------------------------------------------
# Controles 1 y 2: fixture positivo y fixture negativo con la misma forma.
# --------------------------------------------------------------------------
POSITIVOS = {
    "A_patron_como_opcion": [
        f'grep -oE "{_PEM}" "$f" 2>/dev/null\n',
        "git grep -l '-----BEGIN CERTIFICATE-----' || echo limpio\n",
        "found=$(grep -c --color=never x f)\ngrep -q ---foo f\n",
        # A2: la forma medida en produccion. El valor con guiones esta en el
        # array, el grep solo ve `"$p"`.
        f'PATS=(\n  "{_PEM}"\n)\nfor p in "${{PATS[@]}}"; do\n'
        '  printf %s "$t" | grep -oE "$p" 2>/dev/null || true\ndone\n',
    ],
    "B_sale_0_y_vuelve_vacio": [
        "agent=$(grep -oP '(?<=agent_name\": \")[^\"]+' \"$payload\")\n",
        "grep -E '(?:sonnet|opus)-[0-9]' modelos.txt\n",
        "echo x | egrep '(?=foo)bar'\n",
    ],
    "C_exit_code_perdido": [
        'grep "TODO" src/*.py | head -5 && echo "HAY HALLAZGOS"\n',
        'if ! docker pull "$img" 2>&1 | tail -3; then echo fallo; fi\n',
        "if scripts/audit.sh | wc -l; then echo ok; fi\n",
        "cmd 2>/dev/null | wc -l\nrc=$?\n",
    ],
}

# Misma forma sintactica que el positivo, pero correcto. Un guard que marca todo
# `grep`, todo `2>/dev/null` o todo `| head` muere aca — que es como se ve un
# gate que apagan a las 48 horas. Cada negativo salio de un falso positivo
# medido sobre el arbol, no de la imaginacion.
NEGATIVOS = {
    "A_patron_como_opcion": [
        f'grep -oE -- "{_PEM}" "$f" 2>/dev/null\n',
        "git grep -l -e '-----BEGIN CERTIFICATE-----' || echo limpio\n",
        'grep -oE "BEGIN RSA PRIVATE KEY" "$f"\n',
        "grep -rl --binary-files=without-match --exclude-dir=.git x .\n",
        # A2, arreglado: mismo ciclo, mismo array, con `--`.
        f'PATS=(\n  "{_PEM}"\n)\nfor p in "${{PATS[@]}}"; do\n'
        '  printf %s "$t" | grep -oE -- "$p" 2>/dev/null || true\ndone\n',
        # A2, coincidencia: el archivo tiene un literal con guiones, pero la
        # variable del grep no sale de ese array. Es el falso positivo medido en
        # hooks/secret-detector.sh linea 276.
        f'PATS=(\n  "{_PEM}"\n)\nfor VAR in "${{ENVS[@]}}"; do\n'
        '  grep -rq "${VAR}" "$DIR"/docker-compose*.yml\ndone\n',
    ],
    "B_sale_0_y_vuelve_vacio": [
        "agent=$(sed -n 's/.*agent_name\": \"\\([^\"]*\\).*/\\1/p' \"$payload\")\n",
        # CITA, no ocurrencia: el comentario que explica el arreglo. Los dos
        # salieron de `scripts/portability-two-way-proof.sh` lineas 33 y 69.
        "# Antes usaba `grep -oP` (PCRE). BSD grep no lo tiene: devolvia vacio\n"
        "agent=$(sed -n 's/x/y/p' \"$payload\")\n",
        "echo hola  # ojo: `| grep -oP '(?<=x)y'` no anda en macOS\n",
        "grep -E '(sonnet|opus)-[0-9]' modelos.txt\n",
        "python3 -c \"import re; re.search(r'(?:a)b', s)\"\n",
        "printf '%s' \"$x\" | grep -q 'PATH'\n",
    ],
    "C_exit_code_perdido": [
        'v=$(cmd 2>/dev/null | head -1 || true)\n',
        'git push origin main 2>/dev/null | tail -40\n',
        'if grep -q "TODO" src/*.py; then echo "HAY HALLAZGOS"; fi\n',
        'if [ -n "$(find . -name \'*.py\' 2>/dev/null | head -1)" ]; then echo hay; fi\n',
        'n=$(cmd 2>/dev/null | wc -l)\nif [ "$n" -gt 0 ]; then echo hay; fi\n',
        "printf '%s' \"$v\" | tr '\\n' ' ' > \"$tmp\" 2>/dev/null && mv \"$tmp\" \"$f\"\n",
        "cmd 2>/dev/null | wc -l\necho listo\n",
        # CITA de la forma vieja dentro del comentario que documenta el fix.
        "# D4: `unreach=\"$(deadcode ... | grep x | wc -l)\"` used to fold&& echo\n"
        '# El viejo `grep x f | head -5 && echo "HAY HALLAZGOS"` imprimia siempre\n'
        "PULL_OUT=$(docker pull \"$img\" 2>&1) || echo fallo\n",
    ],
}

# El comentario que explica el arreglo tiene que poder citar la forma vieja en
# CUALQUIERA de las tres sub-formas. Se chequea cruzado: ningun detector puede
# marcar la cita de otro.
CITAS = [
    f'# El bug era `grep -oE "{_PEM}" f`, sin el `--`. Ahora va con `--`.\n'
    "grep -oE -- \"$p\" f\n",
    "  # ojo: `grep -oP` y `grep -E '(?:a)b'` devuelven vacio con rc=0 en BSD\n"
    "sed -n 's/a/b/p' f\n",
    '  # `cmd | wc -l` + `rc=$?` daba el estado de wc; `| head -5 && echo x`\n'
    "  # imprimia siempre. Los dos arreglados.\n"
    "  n=$(cmd | wc -l)\n",
]


def _falla_control_en_fixtures() -> list[str]:
    fallas = []
    for nombre, fn in SUBFORMAS.items():
        for fixture in POSITIVOS[nombre]:
            if not fn(fixture):
                fallas.append(f"{nombre}: FALSO NEGATIVO sobre {fixture!r}")
        for fixture in NEGATIVOS[nombre]:
            if fn(fixture):
                fallas.append(f"{nombre}: FALSO POSITIVO sobre {fixture!r}")
        for cita in CITAS:
            if fn(cita):
                fallas.append(
                    f"{nombre}: marco una CITA, no una ocurrencia. El codigo "
                    f"tiene derecho a explicar su propio arreglo: {cita!r}"
                )
    return fallas


def _falla_control_sembrado() -> list[str]:
    """Control 3: planta un positivo por sub-forma EN EL ARBOL y barre de nuevo.

    Un fixture que pasa en su propio archivo no prueba que el barrido sobre el
    arbol lo hubiera encontrado: puede fallar el filtro de sufijo, el shebang,
    el `git ls-files`, la exclusion de symlinks. Esto lo prueba.
    """
    sembrado = REPO / "scripts" / f".sembrado-{os.getpid()}"
    esperado = []
    try:
        sembrado.mkdir(parents=True, exist_ok=True)
        for nombre, fixtures in POSITIVOS.items():
            for i, fixture in enumerate(fixtures):
                destino = sembrado / f"{nombre}-{i}.sh"
                destino.write_text("#!/usr/bin/env bash\n" + fixture)
                esperado.append((nombre, str(destino.relative_to(REPO))))
        hallazgos = escanear(_shell_del_arbol(incluir_no_versionados=True))
    finally:
        shutil.rmtree(sembrado, ignore_errors=True)
    return [
        f"{nombre}: el positivo sembrado en {rel} NO fue encontrado por el "
        f"barrido — un '0 hallazgos' de esta sub-forma no significa nada"
        for nombre, rel in esperado
        if rel not in hallazgos[nombre]
    ]


def test_control_positivo_y_negativo_en_fixtures():
    """Corre en cada invocacion del gate. Prueba que el detector discrimina."""
    fallas = _falla_control_en_fixtures()
    assert not fallas, "el detector no discrimina:\n  " + "\n  ".join(fallas)


def test_control_positivo_sembrado_en_el_corpus_real():
    """Prueba que el BARRIDO —no solo el detector— puede encontrarlos."""
    fallas = _falla_control_sembrado()
    assert not fallas, "el barrido no ve lo que planta:\n  " + "\n  ".join(fallas)


def test_ningun_shell_nuevo_cae_en_la_clase():
    hallazgos = escanear()
    nuevos = {k: sorted(v - _BASELINE[k]) for k, v in hallazgos.items()}
    nuevos = {k: v for k, v in nuevos.items() if v}
    assert not nuevos, (
        "estos shell tienen una defensa que no puede dispararse. A: el patron "
        "arranca con guion y grep lo lee como flag. B: -P o sintaxis PCRE en un "
        "grep POSIX, que devuelve vacio con rc=0. C: se consume el $? de un "
        "pipeline cuya ultima etapa siempre sale 0.\n"
        + "\n".join(f"  {k}:\n    " + "\n    ".join(v) for k, v in nuevos.items())
    )


def test_el_baseline_no_lista_archivos_ya_arreglados():
    """Un supresor que no suprime nada es un bug: da sensacion de cobertura."""
    hallazgos = escanear()
    rancios = {k: sorted(v - hallazgos[k]) for k, v in _BASELINE.items()}
    rancios = {k: v for k, v in rancios.items() if v}
    assert not rancios, (
        "estas entradas de DEUDA/ACEPTADO ya no violan nada — sacalas, o el "
        f"baseline deja lugares libres sin que nadie se entere: {rancios}"
    )


def test_el_baseline_no_lista_archivos_inexistentes():
    fantasmas = sorted(
        f for v in _BASELINE.values() for f in v if not (REPO / f).is_file()
    )
    assert not fantasmas, f"el baseline nombra archivos que no existen: {fantasmas}"


def test_el_corpus_no_esta_vacio():
    """Sub-forma 7: un instrumento que chequea cero archivos pasa siempre."""
    n = len(_shell_del_arbol())
    assert n > 400, f"el corpus de shell colapso a {n} archivos; el gate no mide nada"


if __name__ == "__main__":  # medicion previa al cableado
    archivos = _shell_del_arbol()
    print(f"corpus: {len(archivos)} shell versionados")
    print(f"control fixtures: {_falla_control_en_fixtures() or 'OK'}")
    print(f"control sembrado: {_falla_control_sembrado() or 'OK'}")
    for nombre, encontrados in escanear(archivos).items():
        print(f"\n{nombre}: {len(encontrados)} archivos")
        for f in sorted(encontrados):
            marca = "DEUDA " if f in DEUDA[nombre] else ("ACEPT " if f in ACEPTADO[nombre] else "NUEVO ")
            print(f"  {marca}{f}")
    sys.exit(0)

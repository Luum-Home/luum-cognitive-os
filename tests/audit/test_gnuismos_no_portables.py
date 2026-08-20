"""GNU-ismos en shell: lo que no existe, o no significa lo mismo, en macOS.

Que se midio, y por que este gate existe
----------------------------------------
`flock` fue el caso; esto es la clase. Este repo corre en macOS —Darwin 25.5,
`/bin/bash` 3.2.57, userland BSD— y su CI en Linux con coreutils. Un GNU-ismo
pasa CI y falla en la maquina del operador, o al reves, y en los dos casos sin
que nadie lo note.

Medido el 2026-08-20 contra el PATH del SISTEMA (`/usr/bin:/bin:/usr/sbin:/sbin`,
no el del operador, que con Homebrew tapa justo lo que se busca):

    timeout, tac              AUSENTES     -> 127
    date -d, stat -c,
    grep -P, base64 -w,
    find -printf, sed -i      BSD-DISTINTO -> rc!=0, o peor, salida distinta
    declare -A, ${v^^},
    mapfile, &>>              bash 3.2     -> "bad substitution" / 127

Dos que se arreglaron ese dia, con la falla reproducida antes:

    hooks/subagent-context-injector.sh   `grep -oP` -> BSD grep devuelve VACIO
        sin error, asi que `agent_name` quedaba "" en CADA spawn de esta
        maquina y la busqueda de sidecar no se intentaba nunca.
        Reproducido:  echo 'Identity: x' | /usr/bin/grep -oP 'Identity:\\s*(\\S+)'
                      -> salida vacia

    hooks/rule-md-routing-validator.sh   `${base^^}` -> bash 3.2 corta con
        "bad substitution" y el hook entero muere en esa linea.
        Reproducido:  /bin/bash -c 'base=a; echo "${base^^}"'
                      -> ${base^^}: bad substitution, rc=1

Las dos direcciones estan en `scripts/portability-two-way-proof.sh`: las mismas
aserciones sobre BSD/bash-3.2 y sobre GNU/bash-5 en un contenedor. Un arreglo
probado solo en macOS no es portable, es macOS-especifico con otro nombre.

Que NO mide este gate, a proposito
----------------------------------
  - `flock`: lo cubre `test_flock_has_a_portable_fallback.py`, que ya tiene su
    baseline con igualdad exacta. Dos instrumentos midiendo lo mismo con
    criterios distintos es peor que uno; ver `test_flock_no_se_mide_dos_veces`.
  - Shell embebido en YAML/JSON/Markdown: el censo lo cuenta como ceguera con
    tamano, no como cero.
  - Un comando que se arma en una variable en runtime. Un scanner lexico no lo
    ve, y decirlo es parte de medir.

El detector vive en `scripts/portability_census.py` — un solo lugar, para que
el gate y el censo que se publica no puedan discrepar.
"""

from __future__ import annotations

import functools
import sys

import pytest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from scripts.portability_census import (  # noqa: E402
    DELEGADAS,
    FAMILIA_POR_CLAVE,
    _COMPILADAS,
    _EMBEBIDO,
    _EMBEBIDO_SUFIJOS,
    _en_comentario,
    _referenciados,
    _shell_embebido,
    _versionados,
    censar,
)

# Deuda conocida, con igualdad EXACTA sobre pares (archivo, familia). No es un
# colchon: si uno se arregla, el test exige sacarlo; si aparece uno nuevo,
# falla. La granularidad es (archivo, familia) y no (archivo, linea) a
# proposito — mover una linea no es un hallazgo nuevo.
#
# Por que cada uno sigue vivo:
#
#   timeout en hooks/scripts: el arreglo correcto es `portable_timeout`, que ya
#     existe en hooks/_lib/portable.sh. Aplicarlo exige que el archivo sourcee
#     portable.sh, y portable.sh corre tres feature-tests + un mktemp al
#     cargarse. En un hook de cold-start (query-tailored-context-inject usa
#     `timeout 0.4` justamente porque esta en el camino caliente) eso es
#     latencia que no se midio. Un cambio que no se puede tasar no es un
#     arreglo: es una apuesta. Los dos que YA sourcean portable.sh se
#     convirtieron el 2026-08-20.
#
#   clarification-interceptor: el archivo trae un fallback a sed en la linea
#     siguiente al `grep -oP`. Falta verificar que el fallback produzca lo mismo
#     antes de tocar nada; sin ese rojo previo, el cambio seria una hipotesis.
#
#   benchmark-hooks: `declare -A ... 2>/dev/null || true  # bash 3.2 compat`.
#     La degradacion es deliberada y esta escrita al lado. Queda listado para
#     que se vea, no para que se arregle.
DEUDA = {
    ("hooks/adr-detector.sh", "timeout"),
    ("hooks/code-review-on-commit.sh", "timeout"),
    ("hooks/docker-drift-detector.sh", "timeout"),
    ("hooks/ecosystem-check.sh", "timeout"),
    ("hooks/mlflow-sync.sh", "timeout"),
    ("hooks/orchestrator-mode-detect.sh", "timeout"),
    ("hooks/query-tailored-context-inject.sh", "timeout"),
    ("hooks/session-hygiene.sh", "timeout"),
    ("hooks/usage-health-check.sh", "timeout"),
    ("packages/quality-gates/hooks/clarification-interceptor.sh", "grep -P"),
    ("scripts/benchmark-hooks.sh", "bash4 declare -A"),
    ("scripts/cos-update.sh", "timeout"),
    ("scripts/startup-benchmark.sh", "timeout"),
}


@functools.lru_cache(maxsize=1)
def _censo_cacheado():
    """Un solo barrido del arbol para los cuatro tests que lo necesitan."""
    return censar()


def _pares_vivos() -> set[tuple[str, str]]:
    _censo, sitios, _archivos, _disp = _censo_cacheado()
    return {(s.archivo, s.familia) for s in sitios if not s.guardado}


def test_ningun_gnuismo_nuevo_sin_guarda():
    nuevos = _pares_vivos() - DEUDA
    assert not nuevos, (
        "estos usan un GNU-ismo sin guarda de portabilidad ni camino "
        "alternativo. En macOS el comando no existe (127) o hace otra cosa, y "
        "en los dos casos el shell sigue como si nada.\n  "
        + "\n  ".join(f"{a} -> {f}" for a, f in sorted(nuevos))
        + "\n\nreproducir: python3 scripts/portability_census.py"
    )


def test_la_deuda_no_lista_lo_ya_arreglado():
    """Un supresor que no suprime nada es un bug: da sensacion de cobertura.

    Un baseline por encima de la realidad deja lugares libres con el gate
    diciendo "0 nuevos".
    """
    rancios = DEUDA - _pares_vivos()
    assert not rancios, (
        "estas entradas de DEUDA ya no violan nada — sacalas, o el baseline "
        f"acepta hallazgos nuevos sin que nadie se entere: {sorted(rancios)}"
    )


def test_la_deuda_no_lista_archivos_inexistentes():
    fantasmas = {a for a, _ in DEUDA if not (REPO / a).is_file()}
    assert not fantasmas, f"DEUDA nombra archivos que no existen: {sorted(fantasmas)}"


def test_el_censo_declara_su_ceguera_y_su_poblacion():
    """Un conteo sin poblacion es una opinion con digitos.

    `Census` no deja construir un censo perdiendo casos; esto fija que ademas
    lo publique: cuantos archivos se miraron y que no se pudo ver.
    """
    censo, _sitios, archivos, _disp = _censo_cacheado()
    assert archivos, "poblacion vacia: el censo no encontro ningun shell versionado"
    assert censo.blind, "el censo no declara ceguera"
    assert "familia-delegada-flock" in censo.blind
    assert censo.how.startswith("python3 scripts/portability_census.py")


def test_flock_no_se_mide_dos_veces():
    """La unificacion, escrita como aserto en vez de como buena intencion.

    `flock` tiene su propio gate con igualdad exacta. Si alguien agrega una
    familia `flock` aca, quedan dos instrumentos con criterios distintos sobre
    el mismo bug y el dia que discrepen nadie va a saber cual creer.
    """
    assert "flock" not in FAMILIA_POR_CLAVE, (
        "flock ya lo mide tests/audit/test_flock_has_a_portable_fallback.py; "
        "no lo dupliques con otro criterio"
    )
    assert DELEGADAS["flock"] == "tests/audit/test_flock_has_a_portable_fallback.py"
    assert (REPO / DELEGADAS["flock"]).is_file(), "la delegacion apunta a un test que no existe"


def _viola(clave: str, texto: str) -> bool:
    fam = FAMILIA_POR_CLAVE[clave]
    for m in _COMPILADAS[clave].finditer(texto):
        if _en_comentario(texto, m.start()):
            continue
        if not any(g in texto for g in fam.guardas):
            return True
    return False


def test_el_detector_discrimina():
    """Control: sin esto, un detector que no matchea nunca pasa todo lo de arriba.

    Cada par es (lo que tiene que marcar, lo que NO tiene que marcar). Los
    "no" no son inventados: son los falsos positivos reales de la primera
    corrida — comentarios que EXPLICAN el GNU-ismo, y el idioma portable
    BSD-primero-GNU-de-fallback, que es justamente el arreglo correcto.
    """
    casos = [
        ("timeout", "timeout 30 python3 -c 'x'\n", '# usamos timeout 30 aca\necho ok\n'),
        ("grep -P", "grep -oP 'x' f\n", "# grep -P no anda en BSD\ngrep -oE 'x' f\n"),
        ("bash4 ${var^^}", 'case "${base^^}" in\n', 'case "$base" in\n'),
        ("date -d", 'date -d "@$e" +%s\n', 'date -j -f "%s" "$e" +%s || date -d "@$e" +%s\n'),
        ("stat -c", "stat -c %s f\n", "# GNU es stat -c\nstat -f %z f\n"),
        ("bash4 &>>", "cmd &>> log\n", "REDIR={'&>','&>>'}\n"),
        ("sed -i sin sufijo", "sed -i 's/a/b/' f\n", "sed -i '' 's/a/b/' f\n"),
    ]
    for clave, positivo, negativo in casos:
        assert _viola(clave, positivo), f"{clave}: no detecto la invocacion desnuda"
        assert not _viola(clave, negativo), f"{clave}: falso positivo sobre el caso sano"


# 180 s y no los 30 del default por una razon medida, no para que pase: este
# test recorre los 8.770 archivos versionados DOS veces —una en bytes y otra
# en texto— porque compara los dos barridos. Un solo barrido cuesta ~7 s de
# reloj con la maquina a load 300 (`python3 scripts/portability_census.py
# --perfil`), y de eso solo el 37% es CPU. El presupuesto cubre el peor reloj
# observado, no el peor calculo.
@pytest.mark.timeout(180)
def test_referenciados_en_bytes_da_lo_mismo_que_en_texto():
    """El atajo de rendimiento, fijado como igualdad en vez de como comentario.

    `_referenciados()` matchea sobre bytes crudos para no decodificar 8.770
    archivos. El argumento es que el patron es ASCII puro y UTF-8 es
    auto-sincronizante, asi que el conjunto de aciertos no puede cambiar. Un
    argumento correcto sigue siendo un argumento: esto lo mide.
    """
    import re as _re

    patron_texto = _re.compile(r"[\w.@+-]+\.(?:sh|bash|zsh)")
    esperado = set()
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
        esperado.update(n for n in patron_texto.findall(texto) if n != propio)

    obtenido = _referenciados()
    assert obtenido == esperado, (
        "el barrido en bytes y el barrido en texto ven cosas distintas; el "
        f"atajo dejo de ser equivalente. Diferencia: {sorted(obtenido ^ esperado)[:20]}"
    )


def test_la_ceguera_se_mide_sobre_la_poblacion_declarada():
    """Un censo no puede declarar una poblacion y contar la ceguera sobre otra.

    La version anterior de `_shell_embebido()` corria `grep -rlE ... .` sobre
    el arbol de trabajo: de sus 40 aciertos, 14 estaban en `.claude/plugins/`
    —checkouts de terceros— y el numero cambiaba entre corridas sobre el MISMO
    commit segun que hubiera escrito otra sesion. Esto fija que solo se
    cuenten archivos versionados, que es lo que el censo dice medir.
    """
    versionados = {r for r in _versionados() if r}
    hallados = {
        rel for rel in versionados
        if rel.endswith(_EMBEBIDO_SUFIJOS)
        and _EMBEBIDO.search((REPO / rel).read_text(errors="replace"))
    }
    assert _shell_embebido() == len(hallados), "el conteo no coincide con el barrido versionado"
    assert hallados <= versionados
    assert not any(h.startswith(".claude/plugins/") for h in hallados), (
        "la ceguera volvio a contar checkouts de terceros"
    )

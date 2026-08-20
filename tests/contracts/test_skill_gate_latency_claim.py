"""Las cifras de latencia que ADR-188 escribe tienen que tener instrumento.

ADR-188 prometía `< 30 ms` y citaba, como prueba, una aserción de p99 en
`tests/contracts/test_skill_invocation_gate.py` que nunca existió. Una cita a
una aserción inexistente es peor que no citar nada: da sensación de cobertura.

Este archivo NO prueba el comportamiento del gate — eso es
`test_skill_invocation_gate.py`. Prueba la otra mitad: que lo que el documento
afirma sobre el gate siga siendo cierto, y que ninguna cifra viaje sin el
comando que la produce (`rules/procedencia-de-los-numeros.md`).
"""

from __future__ import annotations

import gzip
import json
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
ADR = REPO / "docs/02-Decisions/adrs/ADR-188-mandatory-skill-invocation-at-high-confidence.md"
RULE = REPO / "rules/skill-invocation-mandatory.md"
HOOK_NAME = "orchestrator-skill-invocation-gate"

# Debajo de esto no hay percentil que valga: se declara no medido en vez de
# afirmar un número sobre cuatro muestras.
_MUESTRAS_MINIMAS = 50
# Banda de deriva. No es "que nunca falle": 490 ms admite 245–980 ms. Una
# optimización real o una degradación real caen afuera y obligan a reescribir
# la cifra del ADR en vez de dejarla envejecer.
_BANDA = (0.5, 2.0)


@pytest.fixture(scope="module")
def adr() -> str:
    return ADR.read_text(encoding="utf-8")


def _percentil(valores: list[float], p: float) -> float:
    idx = int(round(p * (len(valores) - 1)))
    return valores[min(len(valores) - 1, max(0, idx))]


def _duraciones_del_gate() -> list[float]:
    """Vivo + rotados. Contar solo el vivo produce falsos (caso 1 de
    `rules/procedencia-de-los-numeros.md`)."""
    metrics = REPO / ".cognitive-os/metrics"
    fuentes: list[tuple[pathlib.Path, bool]] = []
    vivo = metrics / "hook-timing.jsonl"
    if vivo.exists():
        fuentes.append((vivo, False))
    fuentes.extend((p, True) for p in sorted((metrics / ".archive").glob("hook-timing-*.jsonl.gz")))

    vistas: set[str] = set()
    out: list[float] = []
    for path, comprimido in fuentes:
        abrir = gzip.open if comprimido else open
        try:
            with abrir(path, "rt", encoding="utf-8", errors="ignore") as fh:
                for linea in fh:
                    linea = linea.strip()
                    if HOOK_NAME not in linea or linea in vistas:
                        continue
                    vistas.add(linea)
                    try:
                        fila = json.loads(linea)
                    except json.JSONDecodeError:
                        continue
                    if fila.get("hook") != HOOK_NAME:
                        continue
                    dur = fila.get("duration_ms")
                    if isinstance(dur, (int, float)):
                        out.append(float(dur))
        except OSError:
            continue
    out.sort()
    return out


def test_el_adr_no_promete_un_presupuesto_de_30ms(adr: str) -> None:
    """El presupuesto `< 30 ms` no lo cumplió ninguna de las 245 invocaciones."""
    # §Latencia medida existe justamente para dejar por escrito qué promesa se
    # retiró y por qué; citarla ahí no es volver a prometerla. El resto del
    # documento sí: una cifra de 30 ms fuera de esa sección es una promesa.
    antes, _, resto = adr.partition("## Latencia medida")
    despues = resto.partition("\n## ")[2]
    ofensores = [
        f"{origen}: {linea.strip()}"
        for origen, bloque in (("antes", antes), ("después", despues))
        for linea in bloque.splitlines()
        if re.search(r"<\s*30\s*ms|~?10[–-]30\s*ms", linea)
    ]
    assert not ofensores, (
        f"{ofensores} vuelve a prometer 30 ms. El corpus completo de "
        "hook-timing (vivo + rotados) no tiene una sola invocación del gate "
        "por debajo de 30 ms. Si el presupuesto se recupera, que sea porque "
        "la medición lo respalda."
    )


def test_el_adr_no_cita_una_asercion_de_latencia_que_no_existe(adr: str) -> None:
    """Una cita a una aserción inexistente da sensación de cobertura."""
    citas = re.findall(r"`(tests/[\w/\-]+\.py)`[^\n]{0,80}?(p99|latency assertion)", adr)
    faltantes = []
    for rel, _ in citas:
        destino = REPO / rel
        if not destino.exists():
            faltantes.append(f"{rel} (no existe)")
            continue
        if "p99" not in destino.read_text(encoding="utf-8"):
            faltantes.append(f"{rel} (existe, pero no tiene ninguna aserción de p99)")
    assert not faltantes, (
        f"ADR-188 cita {faltantes} como prueba de latencia. O la aserción se "
        "escribe ahí, o la cita se retira: citar cobertura que no existe es "
        "peor que no citar nada."
    )


def test_la_seccion_de_latencia_trae_el_comando_que_produce_el_numero(adr: str) -> None:
    """Procedencia: ningún número viaja sin el comando que lo produce."""
    assert "## Latencia medida" in adr, "falta la sección con la medición real"
    seccion = adr.split("## Latencia medida", 1)[1].split("\n## ", 1)[0]
    for esperado in (
        "scripts/hook_timing_report.py",
        ".cognitive-os/metrics/.archive/hook-timing-",
        ".cognitive-os/metrics/hook-timing.jsonl",
        HOOK_NAME,
    ):
        assert esperado in seccion, (
            f"la sección de latencia no nombra `{esperado}`: sin los rotados y "
            "sin el instrumento, el número no se puede reproducir."
        )


def test_la_cifra_escrita_sigue_a_la_telemetria(adr: str) -> None:
    """Si la realidad se aleja de lo escrito, el ADR se actualiza — no envejece."""
    m = re.search(r"^\|\s*p50\s*\|\s*(\d+(?:\.\d+)?)\s*ms\s*\|", adr, re.M)
    assert m, "la sección de latencia no declara un p50 legible en su tabla"
    declarado = float(m.group(1))

    duraciones = _duraciones_del_gate()
    if len(duraciones) < _MUESTRAS_MINIMAS:
        pytest.skip(
            f"telemetría insuficiente ({len(duraciones)} < {_MUESTRAS_MINIMAS} "
            "invocaciones del gate en hook-timing vivo + rotados): no medido "
            "acá, no 'medido y correcto'."
        )

    medido = _percentil(duraciones, 0.50)
    lo, hi = declarado * _BANDA[0], declarado * _BANDA[1]
    assert lo <= medido <= hi, (
        f"ADR-188 declara p50={declarado:.0f} ms y la telemetría dice "
        f"{medido:.0f} ms sobre {len(duraciones)} invocaciones (banda aceptada "
        f"{lo:.0f}–{hi:.0f} ms). Actualizá la tabla de §Latencia medida con el "
        "número nuevo y su comando."
    )


def test_ningun_documento_ofrece_el_prefijo_de_override(adr: str) -> None:
    """`COS_ALLOW_SKILL_BYPASS=1 <comando>` no llega al hook.

    El hook lee la variable del entorno del proceso, y es hijo del arnés, no
    del comando que se está por correr. La forma de prefijo manda a tipear algo
    inerte y devuelve al mismo lugar.
    """
    # El valor, no `\\S+`: con greedy, "`VAR=1`+reason) work" pasa por prefijo.
    prefijo = re.compile(r"COS_ALLOW_SKILL_BYPASS=[A-Za-z0-9_'\"-]+[ \t]+[A-Za-z./<]")
    ofensores = []
    for path, texto in ((ADR, adr), (RULE, RULE.read_text(encoding="utf-8"))):
        for n, linea in enumerate(texto.splitlines(), 1):
            if prefijo.search(linea):
                ofensores.append(f"{path.relative_to(REPO)}:{n}: {linea.strip()[:90]}")
    assert not ofensores, (
        f"{ofensores} ofrece el override como prefijo del comando. La vía que "
        "el hook honra es `export` en la shell que LANZA el arnés; a mitad de "
        "sesión, la anotación `SKILL_BYPASS:` en el tool_input."
    )


def test_el_adr_prescribe_el_canal_que_el_hook_lee(adr: str) -> None:
    """PreToolUse corre antes de que el modelo escriba: la respuesta no se lee."""
    assert "annotation in the assistant response" not in adr, (
        "ADR-188 vuelve a prescribir la anotación `SKILL_BYPASS:` en la "
        "respuesta del asistente. El gate corre en PreToolUse y lee el "
        "`tool_input`: ese canal es invisible por construcción."
    )
    assert "`tool_input`" in adr, (
        "el ADR tiene que nombrar el canal que el hook sí lee (`tool_input`)."
    )

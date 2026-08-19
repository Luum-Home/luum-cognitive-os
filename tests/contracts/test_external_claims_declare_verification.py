"""Una afirmacion sobre un sistema AJENO que no dice cuando se verifico no se puede juzgar.

QUE VERIFICA Y QUE NO, dicho al principio. Chequea que toda afirmacion perecedera
nueva DECLARE su fecha de verificacion y su metodo. NO chequea que la afirmacion
sea verdadera: eso exige salir a la red y este contrato es determinista. Es un
contrato de declaracion, no de exactitud. Se dice aca porque confundir "declara
fecha" con "esta al dia" es la misma familia de error que el archivo previene.

POR QUE EL BASELINE ES POR ARCHIVO Y CON CONTEO. Un baseline de nombres de
archivo dejaria pasar una afirmacion perecedera nueva agregada DENTRO de un
archivo ya listado, que es la forma mas probable de que esto crezca (nadie crea
un manifest nuevo para sumar una dependencia). El conteo cierra ese hueco: el
archivo entra con el numero exacto de afirmaciones sin fecha que tiene hoy, y
cualquier movimiento -- una mas o una menos -- rompe. Un asiento libre en un
baseline es lugar donde una regresion aterriza sin que el gate diga nada.

Origen: 2026-08-19. manifests/harness-driver-capabilities.yaml declaraba
capacidades de un arnes ajeno sin una sola fecha de verificacion, y la practica
correcta ya existia al lado, en los *-hooks-schema.yaml, sin sistematizar.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _load_audit():
    path = REPO / "scripts" / "external_claim_freshness_audit.py"
    spec = importlib.util.spec_from_file_location("external_claim_freshness_audit", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ── Deuda declarada, medida 2026-08-19 ──────────────────────────────────────
# Comando: .venv/bin/python3 scripts/external_claim_freshness_audit.py --as-of 2026-08-19
# Cada entrada: cuantas afirmaciones sobre un sistema ajeno hace ese archivo sin
# declarar cuando se verificaron. Es un baseline de IGUALDAD EXACTA. Bajarlo es
# el arreglo; subirlo o dejarlo por encima de la realidad es la trampa.
KNOWN_UNDATED_EXTERNAL_CLAIMS: dict[str, int] = {
    "manifests/agent-orchestration-adapters.yaml": 4,
    "manifests/ai-agent-harness-landscape.yaml": 37,
    "manifests/claude-code-hooks-schema.yaml": 1,
    "manifests/dependencies.yaml": 119,
    "manifests/dependency-adoption-evidence.yaml": 17,
    "manifests/external-tool-adoption-freeze.yaml": 1,
    "manifests/external-tool-licenses.yaml": 13,
    "manifests/external-tools-adoption.yaml": 35,
    "manifests/feature-tool-due-diligence.yaml": 18,
    "manifests/harness-driver-capabilities.yaml": 2,  # 3 -> 2: el bloque codex fecho su afirmacion (2026-08-19)
    "manifests/harness-projection.yaml": 19,
    "manifests/opencode-hooks-schema.yaml": 1,
    "manifests/provider-profiles.yaml": 2,
    "manifests/remote-control-plane-alternatives.yaml": 16,
    "manifests/routing-benchmark-models.yaml": 8,
    "manifests/self-programming-agent-patterns.yaml": 5,
    "manifests/skill-router-retrieval.yaml": 5,
    "manifests/tool-discovery-preuse.yaml": 1,
}

# Afirmaciones que SI declaran fecha pero NO el comando que la produjo.
# Conteo exacto por el mismo motivo que el baseline de arriba: un archivo que
# suma una fecha sin su comando tiene que romper aca, aunque ya este listado.
# Nota incomoda y a proposito: claude-code-hooks-schema.yaml, el ejemplar de la
# practica correcta, aparece igual. De sus dos fuentes fechadas, una trae
# `how: curl -sSL ...` y la otra no. El ejemplar es mas delgado de lo que
# parece, y el baseline lo dice en vez de redondearlo.
KNOWN_DATED_WITHOUT_METHOD: dict[str, int] = {
    "manifests/claude-code-hooks-schema.yaml": 1,
    "manifests/codex-hooks-schema.yaml": 1,  # 2 -> 1: la fuente learn.chatgpt.com ya trae `how`
    "manifests/opencode-hooks-schema.yaml": 4,
}


@pytest.fixture(scope="module")
def censo():
    audit = _load_audit()
    records, unreadable = audit.collect_structured_claims(REPO)
    assert not unreadable, f"manifests ilegibles: {unreadable}"
    assert records, "el censo quedo vacio: el gate pasaria por vacuidad"
    undated: dict[str, int] = {}
    dated_without_how: dict[str, int] = {}
    for record in records:
        if record["verified"] is None:
            undated[record["file"]] = undated.get(record["file"], 0) + 1
        elif not record["how"]:
            dated_without_how[record["file"]] = dated_without_how.get(record["file"], 0) + 1
    return {"undated": undated, "dated_without_how": dated_without_how}


def test_ninguna_afirmacion_externa_nueva_omite_su_fecha(censo) -> None:
    """Un archivo nuevo, o uno que suma una afirmacion sin fecha, rompe aca."""
    actual = censo["undated"]
    nuevos = {
        name: count
        for name, count in actual.items()
        if KNOWN_UNDATED_EXTERNAL_CLAIMS.get(name, 0) < count
    }
    assert not nuevos, (
        "estas afirmaciones sobre sistemas AJENOS no declaran cuando se "
        f"verificaron (archivo: sin_fecha_ahora vs baseline): { {k: (v, KNOWN_UNDATED_EXTERNAL_CLAIMS.get(k, 0)) for k, v in sorted(nuevos.items())} }. "
        "Una afirmacion sobre nuestro arbol se deriva cuando uno quiere; una "
        "sobre un sistema ajeno solo se puede fechar. Agrega `verified: "
        "YYYY-MM-DD` y `how: <comando reproducible>` al lado de la fuente, como "
        "en manifests/claude-code-hooks-schema.yaml. NO pongas la fecha de hoy "
        "sin haber mirado la fuente: eso convierte el instrumento en su opuesto."
    )


def test_el_baseline_no_esta_por_encima_de_la_realidad(censo) -> None:
    """Un baseline con colchon acepta regresiones gratis y dice '0 nuevas'."""
    actual = censo["undated"]
    colchon = {
        name: (actual.get(name, 0), count)
        for name, count in KNOWN_UNDATED_EXTERNAL_CLAIMS.items()
        if actual.get(name, 0) < count
    }
    assert not colchon, (
        f"el baseline acepta mas de lo que hay (archivo: real vs baseline): "
        f"{dict(sorted(colchon.items()))}. Bajalo al numero real; cada unidad de "
        "diferencia es un lugar libre donde una afirmacion sin fecha aterriza "
        "con el gate diciendo '0 nuevas'."
    )


def test_el_baseline_no_lista_archivos_inexistentes(censo) -> None:
    fantasmas = set(KNOWN_UNDATED_EXTERNAL_CLAIMS) - set(censo["undated"])
    assert not fantasmas, (
        f"{sorted(fantasmas)} ya no tiene afirmaciones externas sin fecha (o no "
        "existe): sacalo del baseline. Vaciarlo es el arreglo, no moverlo."
    )


def test_toda_afirmacion_fechada_declara_su_metodo(censo) -> None:
    """Una fecha sin el comando que la produjo es una fecha que nadie puede repetir."""
    actual = censo["dated_without_how"]
    nuevos = {
        name: (count, KNOWN_DATED_WITHOUT_METHOD.get(name, 0))
        for name, count in actual.items()
        if KNOWN_DATED_WITHOUT_METHOD.get(name, 0) < count
    }
    assert not nuevos, (
        f"{dict(sorted(nuevos.items()))} declara `verified:` pero no COMO se "
        "verifico (archivo: real vs baseline). Una fecha sin su comando no es "
        "reproducible: el que la revise dentro de seis meses no sabe que correr. "
        "Agrega `how: <comando>` al lado, como la primera fuente de "
        "manifests/claude-code-hooks-schema.yaml."
    )


def test_el_baseline_de_metodo_no_esta_por_encima_de_la_realidad(censo) -> None:
    actual = censo["dated_without_how"]
    colchon = {
        name: (actual.get(name, 0), count)
        for name, count in KNOWN_DATED_WITHOUT_METHOD.items()
        if actual.get(name, 0) < count
    }
    assert not colchon, (
        f"el baseline de metodo acepta mas de lo que hay (archivo: real vs "
        f"baseline): {dict(sorted(colchon.items()))}. Bajalo al numero real."
    )

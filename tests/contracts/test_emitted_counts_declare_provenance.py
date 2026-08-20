"""Un conteo que llega sin su comando obliga a buscar el instrumento, y nadie lo busca.

QUE VERIFICA Y QUE NO, dicho al principio para que nadie confie de mas: chequea
que cada ledger generado bajo ``docs/06-Daily/reports/*-latest.json`` DECLARE el
comando que lo reproduce, y que ese comando tenga forma de orden ejecutable y
nombre un archivo que existe en el repo. NO chequea que correrlo devuelva el
mismo numero -- eso exigiria correr los 41 auditores dentro de un contrato
determinista. Es un contrato de PROCEDENCIA, no de exactitud. Se dice aca porque
confundir "declara como reproducirse" con "el numero es correcto" es la misma
familia de error que este archivo previene.

POR QUE ESTA POBLACION, y no la de ``test_shipped_audits_declare_population.py``.
Aquel gate eligio los 13 scripts que SHIPPEAN, con el argumento de que el dano
ocurre en el proyecto de un tercero que no leyo el codigo. La procedencia tiene
otro punto de dano: el consumidor de un ledger ``-latest.json`` es OTRA sesion de
este mismo repo, que lo abre porque es el resumen y no el instrumento. Los diez
errores del 2026-08-19 fueron todos puertas adentro. Asi que el corte no es
"lo que sale del repo" sino "lo que se lee sin abrir a quien lo produjo": los
ledgers ``-latest``, que son canonicos, regenerados y consumidos por nombre.

POR QUE JSON Y NO LOS 550 .md. Un ledger ``-latest.json`` es un artefacto
generado: si le falta la procedencia, la culpa es de su escritor y el arreglo es
una linea. Los .md de ``docs/06-Daily/reports`` son en su mayoria informes
escritos a mano, donde el patron equivalente ya existe (``verify:``) y donde el
gate correcto es el de ``scripts/volatile_number_audit.py``, que persigue otro
defecto: el numero congelado en prosa. Meter los dos en el mismo gate produciria
un baseline de cientos de asientos, que es el colchon que este proyecto trata
como bug.

El chequeo de forma se REUSA de ``cos_lib.measurement.looks_runnable``, el mismo
que impide construir un ``Census`` sin comando. Un solo criterio de "esto es un
comando" para el emisor y para el gate; dos criterios se desincronizan.

Origen: 2026-08-19. Diez lecturas falsas en una sesion de catorce horas, todas
de la misma forma: consumir un numero sin abrir el instrumento que lo produjo.
El diagnostico no fue falta de disciplina sino de economia -- leer el productor
cuesta una llamada y contexto, consumir el numero cuesta cero. La unica forma de
cambiarlo es que el comando venga pegado al numero.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cos_lib.measurement import looks_runnable  # noqa: E402

REPORTS = REPO / "docs" / "06-Daily" / "reports"
REPORTS_REL = "docs/06-Daily/reports"

# Claves aceptadas como declaracion de procedencia. `generated_by` ya lo usaba
# volatile-numbers-latest.json antes de este gate: se adopta el nombre existente
# en vez de imponer uno nuevo y dejar al unico que cumplia como incumplidor.
PROVENANCE_KEYS = ("reproduce", "generated_by", "how", "command")

# Un token del comando que apunta a un archivo del repo. Si el comando nombra
# uno, tiene que existir: un `verify:` que apunta a un script borrado es peor
# que ninguno, porque parece verificable.
_PATH_TOKEN = re.compile(r"(?:^|[\s'\"=])((?:\./)?[\w][\w./-]*\.(?:py|sh|bash|ts|js|go))")

# Claves cuyo valor entero no es una medicion: son metadatos del formato.
_NOT_A_COUNT = {"schema_version", "source_schema_version"}


def _emits_a_count(node: object, key: str | None = None) -> bool:
    """Un entero en cualquier nivel del arbol ya es un numero publicado."""
    if isinstance(node, bool):
        return False
    if isinstance(node, int):
        return key not in _NOT_A_COUNT
    if isinstance(node, dict):
        return any(_emits_a_count(v, k) for k, v in node.items())
    if isinstance(node, list):
        return any(_emits_a_count(v, key) for v in node)
    return False


def _declared_command(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in PROVENANCE_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _provenance_problem(path: Path) -> str | None:
    """``None`` si el ledger declara procedencia utilizable; si no, el motivo."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"ilegible: {exc}"
    if not _emits_a_count(payload):
        return None  # no publica ningun numero: no hay nada que reproducir
    command = _declared_command(payload)
    if command is None:
        return f"publica conteos y no declara ninguna de {PROVENANCE_KEYS}"
    if not looks_runnable(command):
        return f"{command!r} no tiene forma de comando ejecutable"
    for token in _PATH_TOKEN.findall(command):
        if not (REPO / token.lstrip("./")).exists():
            return f"el comando nombra {token!r}, que no existe en el repo"
    return None


# -- Deuda declarada, medida 2026-08-19 --------------------------------------
# Comando:
#   .venv/bin/python3 -m pytest tests/contracts/test_emitted_counts_declare_provenance.py \
#       -q -k censo -s
# Cada nombre es un ledger canonico que publica conteos sin decir como
# reproducirlos. Baseline de IGUALDAD EXACTA: no absorbe uno nuevo, no puede
# listar uno ya migrado, y no puede tener asientos apuntando a archivos
# inexistentes. Vaciarlo es el arreglo; agrandarlo es la trampa.
KNOWN_LEDGERS_WITHOUT_PROVENANCE: set[str] = {
    "adr-partial-backlog-latest.json",
    "capability-coverage-latest.json",
    "cos-falsification-benchmark-latest.json",
    "cos-install-scope-dev-smoke-latest.json",
    "cos-vs-ai-slop-two-repo-smoke-latest.json",
    "docs-duplicate-latest.json",
    # claim-proof y docs-execution: sus ESCRITORES ya estampan REPRODUCE
    # (scripts/claim_proof_audit.py, scripts/docs_execution_audit.py), pero el
    # artefacto regenerado no se pudo commitear: research-compliance-guard lo
    # bloquea por una frase que el propio ledger transcribe de los docs.
    # Salen del baseline en cuanto alguien los regenere sin ese bloqueo, y la
    # asercion "no lista ya migrados" obliga a sacarlos ese mismo dia.
    "claim-proof-latest.json",
    "docs-execution-latest.json",
    "documentation-truth-latest.json",
    "external-tool-adoption-audit-latest.json",
    "feature-tool-due-diligence-latest.json",
    "opencode-primitive-adapter-smoke-latest.json",
    "operational-guide-audit-latest.json",
    "pending-truth-latest.json",
    "portable-ai-consumer-impact-latest.json",
    "portable-ai-consumer-package-smoke-latest.json",
    "portable-ai-consumer-smoke-latest.json",
    "portable-ai-real-consumer-smoke-latest.json",
    "primitive-authority-latest.json",
    "primitive-coverage-latest.json",
    "primitive-duplication-latest.json",
    "primitive-fitness-ledger-latest.json",
    "primitive-gap-latest.json",
    "primitive-harness-coverage-latest.json",
    "primitive-harness-partials-latest.json",
    "primitive-projection-fidelity-latest.json",
    "primitive-readiness-ledger-hooks-latest.json",
    "primitive-readiness-ledger-rules-latest.json",
    "primitive-readiness-ledger-scripts-latest.json",
    "primitive-readiness-ledger-skills-latest.json",
    "primitive-readiness-ledger-templates-latest.json",
    "primitive-readiness-lifecycle-backlog-scripts-latest.json",
    "primitive-service-headless-smoke-latest.json",
    # primitive-surface-reduction-latest.json NO esta aca a proposito: hoy no
    # publica ningun entero (actions/applied/family/mode), asi que no hay numero
    # que reproducir. El dia que publique uno entra por la puerta de "nuevo".
    "primitive-usage-map-latest.json",
    "proof-drill-evidence-latest.json",
    "python-helper-duplication-latest.json",
    "test-skip-audit-latest.json",
}


@pytest.fixture(scope="module")
def censo() -> dict[str, str | None]:
    """Censo, no lista: se recalcula del arbol, asi que un ledger nuevo entra solo."""
    ledgers = sorted(REPORTS.glob("*-latest.json"))
    assert ledgers, f"el censo quedo vacio: {REPORTS_REL}/*-latest.json no matchea nada"
    resultado = {p.name: _provenance_problem(p) for p in ledgers}
    cumplen = sum(1 for v in resultado.values() if v is None)
    print(
        f"\nprocedencia de los ledgers canonicos: {cumplen}/{len(resultado)} declaran "
        f"como reproducirse ({len(resultado) - cumplen} en deuda)"
    )
    return resultado


def test_ningun_ledger_nuevo_publica_conteos_sin_su_comando(censo) -> None:
    infractores = {n for n, motivo in censo.items() if motivo is not None}
    nuevos = sorted(infractores - KNOWN_LEDGERS_WITHOUT_PROVENANCE)
    detalle = "; ".join(f"{n}: {censo[n]}" for n in nuevos)
    assert not nuevos, (
        f"estos ledgers de {REPORTS_REL} publican conteos que otra sesion va a "
        f"consumir sin abrir el instrumento: {detalle}. El arreglo es en el "
        "SCRIPT que los escribe, no en el archivo: agregale una constante "
        'REPRODUCE y volcala como "reproduce" en el payload (ver '
        "scripts/reduction_backlog.py). Un comando que otro pueda pegar en una "
        "terminal, no una descripcion de lo que hiciste."
    )


def test_el_baseline_no_lista_ledgers_ya_migrados(censo) -> None:
    """Un baseline por encima de la realidad acepta regresiones gratis."""
    rancios = sorted(n for n in KNOWN_LEDGERS_WITHOUT_PROVENANCE if censo.get(n) is None)
    assert not rancios, (
        f"{rancios} ya declaran su comando de reproduccion: sacalos de "
        "KNOWN_LEDGERS_WITHOUT_PROVENANCE. Vaciar el baseline es el arreglo."
    )


def test_el_baseline_no_lista_ledgers_inexistentes(censo) -> None:
    fantasmas = sorted(KNOWN_LEDGERS_WITHOUT_PROVENANCE - set(censo))
    assert not fantasmas, (
        f"{fantasmas} no existe en {REPORTS_REL}. Un asiento libre en un baseline "
        "es lugar donde una regresion futura aterriza sin que el gate diga nada."
    )


def test_el_criterio_de_comando_rechaza_prosa() -> None:
    """El gate no sirve si acepta texto libre: esa es su unica trampa posible."""
    assert not looks_runnable("lo verifique a mano")
    assert not looks_runnable("")
    assert looks_runnable(".venv/bin/python3 scripts/reduction_backlog.py")
    assert looks_runnable("scripts/volatile_number_audit.py --write-report")

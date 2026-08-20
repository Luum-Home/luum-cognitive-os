"""Un script de auditoría que le llega a un dev no puede publicar un número pelado.

QUÉ VERIFICA Y QUÉ NO, dicho al principio para que nadie confíe de más: esto
chequea que el instrumento **declare su población y su ceguera** construyendo un
``Census``. NO verifica que sus números sean correctos — eso lo prueban los tests
de cada script. Es un contrato de forma, no de exactitud. Se dice acá porque
confundir "chequeé la forma" con "chequeé el contenido" es la familia de errores
que produjo este archivo.

POR QUÉ SOLO LOS QUE SHIPPEAN. Hay ~70 scripts de auditoría en el repo. Un
baseline con 70 excepciones no es un trinquete, es un colchón, y este proyecto
trata un colchón como un bug. Los ``os-only`` no salen del repo y su lector es
quien los escribió. Los ``SCOPE: both`` se instalan en el proyecto de otra
persona, que no leyó el código y no tiene forma de saber que el 0 que ve en
pantalla significaba "no pude mirar". Ahí es donde un número deshonesto hace
daño real, así que ahí es donde va el gate.

Origen: 2026-08-19, cinco lecturas falsas en una sesión, todas de la misma
forma: contar un proxy sin declarar si su ausencia significaba *no* o *no puedo
ver*. Ver ``cos_lib/measurement.py``.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
_SCOPE_RE = re.compile(r"^#\s*SCOPE:\s*(\S+)", re.M)
# `census` faltaba, y la ausencia era exquisita: este gate obliga a declarar
# poblacion, y no veia OCHO scripts llamados *census* porque la palabra no
# estaba en su propio selector de corpus. Un gate sobre censos, ciego a los
# censos, invisible por su propio nombre. Medido el 2026-08-20: miraba 13 de 67
# scripts con SCOPE, y 4 de los 8 censos no declaran poblacion — dos de ellos
# commiteados ese mismo dia.
#
# `ledger` y `report` entran por la misma razon: nombran instrumentos que
# publican conteos. Si un nombre nuevo vuelve a quedar afuera, el sintoma es
# este mismo y la deteccion cuesta otro dia.
_AUDIT_NAME_RE = re.compile(r"audit|_scan|verify|check|census|ledger|report")


def _shipped_audit_scripts() -> list[Path]:
    """Censo, no lista: se recalcula del árbol, así que un script nuevo entra solo."""
    out = []
    for path in sorted(SCRIPTS.glob("*.py")):
        if not _AUDIT_NAME_RE.search(path.name):
            continue
        head = path.read_text(encoding="utf-8", errors="ignore")[:2000]
        m = _SCOPE_RE.search(head)
        if m and m.group(1) == "both":
            out.append(path)
    return out


def _declares_population(path: Path) -> bool:
    """¿Construye un Census? Chequeo por AST: un import sin uso no alcanza."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        return False
    importa = any(
        isinstance(n, ast.ImportFrom)
        and (n.module or "").endswith("measurement")
        and any(a.name == "Census" for a in n.names)
        for n in ast.walk(tree)
    )
    if not importa:
        return False
    return any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "Census"
        for n in ast.walk(tree)
    )


# ── Deuda declarada, medida 2026-08-19 ──────────────────────────────────────
# Estos scripts shippean y todavía publican conteos sin declarar su población.
# Es un baseline de IGUALDAD EXACTA: no puede contener un script ya migrado, y
# no absorbe uno nuevo. Vaciarlo es el arreglo; agrandarlo es la trampa.
KNOWN_BARE_COUNT_AUDITS: set[str] = {
    "ai_resource_economy_audit.py",
    "audit_hanging_processes.py",
    "check_absolute_paths.py",
    "check_test_quality.py",
    "check_test_ratchet.py",
    "cos-orphan-process-audit.py",
    "cos_test_quality_audit.py",
    "documentation_truth_audit.py",
    "dod_check.py",
    "invariant_check_helper.py",
    "provenance_scan.py",
    "python_stdin_antipattern_audit.py",
    "stash_quarantine_audit.py",
    # ── Ampliacion del corpus, 2026-08-20 ───────────────────────────────────
    # Estos cinco NO son deuda nueva: son deuda que este gate no podia ver.
    # Su selector de corpus era el regex `audit|_scan|verify|check`, asi que
    # miraba 13 de 67 scripts con SCOPE — y no veia OCHO llamados *census*
    # porque la palabra no estaba en su propio selector. Un gate sobre censos,
    # ciego a los censos, invisible por su propio nombre.
    #
    # Al agregar `census|ledger|report` al selector cayeron estos cinco. Se
    # declaran aca en vez de migrarlos en el mismo commit porque son cinco
    # instrumentos y la migracion a Census cambia lo que cada uno publica: eso
    # pide su propia prueba en las dos direcciones, no un renglon apurado.
    # El baseline sigue siendo de igualdad exacta y solo puede bajar.
    "adr_implementation_ledger.py",
    "agent_work_ledger.py",
    "approval_ledger.py",
    "hook_timing_report.py",
    "skip_absence_census.py",
}


@pytest.fixture(scope="module")
def censo() -> dict[str, bool]:
    scripts = _shipped_audit_scripts()
    assert scripts, "el censo quedó vacío: el gate pasaría por vacuidad"
    return {p.name: _declares_population(p) for p in scripts}


def test_ningun_script_nuevo_publica_conteos_sin_poblacion(censo) -> None:
    infractores = {n for n, ok in censo.items() if not ok}
    nuevos = infractores - KNOWN_BARE_COUNT_AUDITS
    assert not nuevos, (
        "estos scripts shippean a proyectos de terceros y publican conteos sin "
        f"declarar su población ni su ceguera: {sorted(nuevos)}. Usá "
        "cos_lib.measurement.Census: obliga a nombrar las fuentes leídas y a "
        "declarar qué casos el instrumento no puede juzgar, y devuelve None en "
        "vez de 0.0 cuando no hay nada medible."
    )


def test_el_baseline_no_lista_scripts_ya_migrados(censo) -> None:
    """Un baseline por encima de la realidad acepta regresiones gratis."""
    rancios = {n for n in KNOWN_BARE_COUNT_AUDITS if censo.get(n) is True}
    assert not rancios, (
        f"{sorted(rancios)} ya declaran su población: sacalos de "
        "KNOWN_BARE_COUNT_AUDITS. Vaciar el baseline es el arreglo, no moverlo."
    )


def test_el_baseline_no_lista_scripts_inexistentes(censo) -> None:
    fantasmas = KNOWN_BARE_COUNT_AUDITS - set(censo)
    assert not fantasmas, (
        f"{sorted(fantasmas)} no está entre los scripts que shippean. Un asiento "
        "libre en un baseline es lugar donde una regresión futura aterriza sin "
        "que el gate diga nada."
    )

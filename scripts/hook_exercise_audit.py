#!/usr/bin/env python3
# SCOPE: os-only
"""Mide cuantos hooks estan EJERCITADOS por un test y cuantos solo NOMBRADOS.

Tener un `behavior_test` asociado no prueba que el test haga algo con el hook.
`manifests/hook-quality.yaml` responde "hay un test que menciona este hook",
que es una pregunta distinta —y mas facil de contestar que si— a "hay un test
que lo corre". Este script separa las dos, en un escalon de tres niveles:

    EXERCISED   el nombre viaja como argumento dentro de un nodo ``Call``:
                algo lo invoca, lo alimenta o lo parametriza.
    NAMED_ONLY  el nombre existe como literal string en el test y no se le pasa
                a nada. Es una mencion, no una ejecucion.
    NO_TEST     ningun test lo nombra siquiera.

POR QUE HAY UNA CUARTA CUBETA Y NO TRES
---------------------------------------
La tecnica de arriba tiene un punto ciego conocido y no lo puede tapar: la
INDIRECCION. Un test que escribe

    CASES = ["hooks/x.sh", "hooks/y.sh"]
    ...
    run(CASES[0])

nombra el hook en un literal que NO es argumento de ningun ``Call``, y sin
embargo lo ejercita. Clasificarlo ``NAMED_ONLY`` seria acusar de mencion vacia
a un test que corre el hook. Un archivo de test que no parsea es el mismo caso
por otra via: el instrumento no puede leerlo.

Los dos caen en ``UNCLASSIFIABLE``, que no es un nivel de calidad sino una
declaracion sobre el instrumento: *esto no lo puedo juzgar*. Los porcentajes se
publican sobre el denominador medible (total menos ``UNCLASSIFIABLE``), la
ceguera se publica al lado sin mezclarse, y cuando la ceguera es alta el
reporte lo dice en voz alta: **un cero bajo ceguera alta no es un resultado,
es una no-observacion**.

DE DONDE SALE CADA COSA (reutilizado, no reimplementado)
--------------------------------------------------------
La pregunta "que tests cubren este hook" ya la contesta
``scripts/hook_quality_audit.py`` desde el commit 1395537c9, que descarta
docstrings y literales dentro de baselines de deuda (``KNOWN_*``,
``EXPECTED_FAIL*``, ``BASELINE*``...). Este script IMPORTA esas funciones
(``discover_behavior_tests``, ``discover_census_tests``, ``coverage_text``,
``registered_hooks``, ``classify_criticality``) en vez de reimplementarlas: el
conjunto ``NO_TEST`` de aca es, por construccion, el conjunto de hooks con
``behavior_tests`` vacio en ``manifests/hook-quality.yaml``. Si las dos
mediciones se separan, es un bug, no una diferencia de criterio.

SESGOS CONOCIDOS DE LA TECNICA (declarados, no escondidos)
-----------------------------------------------------------
  - Conservador: ``assert "hooks/x.sh" in salida`` es una verificacion real y
    cae en ``NAMED_ONLY``, porque el literal no es argumento de un ``Call``.
    La definicion de EXERCISED es deliberadamente la del encargo, y esta
    medicion la subestima antes que inflarla.
  - Optimista: ``Path("hooks/x.sh")`` cuenta como ``EXERCISED`` aunque solo
    construya una ruta. Es un ``Call`` con el nombre adentro.
  - Los tests censo (``HOOK_QUALITY_COVERAGE = "census"``) NO se cuentan como
    cobertura de ningun hook en particular —los excluye ``discover_behavior_tests``
    a proposito— pero se reportan aparte para que no parezcan inexistentes.

Solo lectura. Determinista para el mismo arbol. No depende del cwd ni del estado
de sesion: el repo se resuelve desde ``__file__``.

Exit codes:
  0  sin hallazgos
  1  hallazgos
  2  error
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
import warnings
from pathlib import Path
from typing import Any

# Parsear el corpus de tests con ``ast`` reemite los SyntaxWarning del propio
# corpus (secuencias de escape invalidas en literales). Son ruido del archivo
# leido, no de esta corrida, y ensucian una salida que tiene que ser estable.
warnings.filterwarnings("ignore", category=SyntaxWarning)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from hook_quality_audit import (  # noqa: E402  (import tras ajustar sys.path)
    QUALITY_MANIFEST,
    REQUIRED_BEHAVIOR_COVERAGE,
    TEST_ROOTS,
    _excluded_constant_ids,
    classify_criticality,
    discover_behavior_tests,
    discover_census_tests,
    load_yaml,
    registered_hooks,
    test_text_index,
)

EXERCISED = "EXERCISED"
NAMED_ONLY = "NAMED_ONLY"
NO_TEST = "NO_TEST"
UNCLASSIFIABLE = "UNCLASSIFIABLE"

LEVELS = (EXERCISED, NAMED_ONLY, UNCLASSIFIABLE, NO_TEST)

# Un nivel de evidencia mas alto gana sobre uno mas bajo cuando varios tests
# cubren el mismo hook: prueba positiva de ejecucion > ceguera > mencion.
_PRECEDENCE = {EXERCISED: 3, UNCLASSIFIABLE: 2, NAMED_ONLY: 1}

# Umbral a partir del cual la ceguera invalida la lectura de los otros numeros.
BLINDNESS_ALARM = 0.10

# Criticidades cuya falla es silenciosa: el hook no avisa que dejo de proteger.
CRITICALITY_WARRANTING_TEST = {"security", "quality"}
MATURITY_WARRANTING_TEST = {"block", "emergency"}


class AuditError(RuntimeError):
    """Error irrecuperable de lectura o de parseo estructural."""


# --------------------------------------------------------------------------- #
# Clasificacion a nivel de archivo
# --------------------------------------------------------------------------- #
def _string_constants(node: ast.AST) -> list[int]:
    """Ids de los literales string del subarbol de ``node``."""
    return [
        id(sub)
        for sub in ast.walk(node)
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str)
    ]


def file_evidence(path: Path, text: str) -> dict[str, Any]:
    """Parte el archivo en tres bolsas de texto, una por nivel de evidencia.

    Devuelve ``{"parsed": bool, "call": str, "indirect": str, "plain": str}``.
    Un archivo que no parsea devuelve ``parsed=False`` y bolsas vacias: no se
    puede afirmar nada sobre el, y eso es exactamente ``UNCLASSIFIABLE``.

    Las tres bolsas particionan exactamente el mismo conjunto de literales que
    ``hook_quality_audit.coverage_text`` considera testimonio valido: se comparte
    ``_excluded_constant_ids``, asi que la union de las tres es su contenido.
    Esa identidad es lo que hace que el conjunto ``NO_TEST`` de este script
    coincida con el de ``discover_behavior_tests``, y hay un test que lo prueba
    sobre el corpus real en vez de confiar en la lectura del codigo.

    Un solo recorrido del arbol: el corpus son ~1000 archivos y cada recorrido
    extra se paga mil veces.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {"parsed": False, "call": "", "indirect": "", "plain": ""}

    excluded = _excluded_constant_ids(tree)

    call_ids: set[int] = set()
    assignments: list[tuple[list[str], ast.AST]] = []
    loaded: set[str] = set()
    constants: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            constants.append((id(node), node.value))
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            loaded.add(node.id)
        elif isinstance(node, ast.Call):
            # Argumentos y keywords, nunca ``func``: `{...}.issubset(x)` menciona
            # el hook adentro del subarbol del Call pero no se lo pasa a nadie.
            for arg in list(node.args) + [kw.value for kw in node.keywords]:
                call_ids.update(_string_constants(arg))
        elif isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if targets and node.value is not None:
                assignments.append((targets, node.value))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None:
                assignments.append(([node.target.id], node.value))

    # Indireccion: el literal esta ligado a un nombre que despues SE LEE, y el uso
    # vive en otra linea atras de ese nombre. Si nadie lee el nombre, el literal
    # esta muerto y no hay indireccion que resolver.
    indirect_ids: set[int] = set()
    for targets, value in assignments:
        if any(name in loaded for name in targets):
            indirect_ids.update(_string_constants(value))

    call: list[str] = []
    indirect: list[str] = []
    plain: list[str] = []
    for node_id, value in constants:
        if node_id in excluded:
            continue
        if node_id in call_ids:
            call.append(value)
        elif node_id in indirect_ids:
            indirect.append(value)
        else:
            plain.append(value)
    return {
        "parsed": True,
        "call": "\n".join(call),
        "indirect": "\n".join(indirect),
        "plain": "\n".join(plain),
    }


def evidence_key(path: Path) -> str:
    """Clave estable de un archivo de test: ruta relativa al repo cuando existe.

    ``discover_behavior_tests`` devuelve rutas relativas; el indice se teclea
    igual para que las dos mediciones hablen del mismo archivo sin traducciones
    a mitad de camino. Un archivo fuera del repo (fixture sintetico en
    ``tmp_path``) conserva su ruta absoluta.
    """
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def build_evidence_index(sources: list[tuple[Path, str]]) -> dict[str, dict[str, Any]]:
    """Indice archivo -> bolsas de evidencia. Se construye una vez por corrida."""
    return {evidence_key(path): file_evidence(path, text) for path, text in sources}


def hook_needles(hook_id: str, script: str) -> set[str]:
    """Mismos needles que usa ``discover_behavior_tests``; si divergen, mienten."""
    base = Path(script).name
    return {n for n in (hook_id, base, base.removesuffix(".sh")) if n}


def classify_hook(
    needles: set[str],
    tests: list[str],
    evidence: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, list[str]]]:
    """Nivel de un hook a partir de los tests que lo cubren.

    ``tests`` son las claves que devuelve ``evidence_key`` (rutas relativas al
    repo, que es exactamente lo que emite ``discover_behavior_tests``).
    """
    if not tests:
        return NO_TEST, {}

    per_level: dict[str, list[str]] = {EXERCISED: [], NAMED_ONLY: [], UNCLASSIFIABLE: []}
    for rel in tests:
        bags = evidence.get(rel)
        if bags is None or not bags["parsed"]:
            per_level[UNCLASSIFIABLE].append(rel)
            continue
        if any(n in bags["call"] for n in needles):
            per_level[EXERCISED].append(rel)
        elif any(n in bags["indirect"] for n in needles):
            per_level[UNCLASSIFIABLE].append(rel)
        elif any(n in bags["plain"] for n in needles):
            per_level[NAMED_ONLY].append(rel)
        else:
            # discover_behavior_tests acredito el archivo y aca no aparece:
            # solo puede pasar si las dos tecnicas divergieron. No se adivina.
            per_level[UNCLASSIFIABLE].append(rel)

    level = max(
        (lv for lv in per_level if per_level[lv]),
        key=lambda lv: _PRECEDENCE[lv],
        default=UNCLASSIFIABLE,
    )
    return level, {k: v for k, v in per_level.items() if v}


# --------------------------------------------------------------------------- #
# Auditoria
# --------------------------------------------------------------------------- #
def maturity_index() -> tuple[dict[str, str], bool]:
    """maturity declarada por hook en manifests/hook-quality.yaml."""
    manifest = load_yaml(QUALITY_MANIFEST)
    hooks = manifest.get("hooks")
    if not isinstance(hooks, dict):
        return {}, False
    return {
        hook_id: str(entry.get("maturity") or "")
        for hook_id, entry in hooks.items()
        if isinstance(entry, dict)
    }, True


def warrants_test(hook_id: str, criticality: str, maturity: str) -> tuple[bool, str]:
    """Un hook SIN test, ¿es un hallazgo?

    Si. Cuando su falla es silenciosa: los que deciden sobre seguridad o
    calidad, los que ya bloquean trabajo (``block``/``emergency``), y los que
    RULES-COMPACT declara de cobertura obligatoria.

    No. Un hook ``standard``/``coordination``/``lifecycle`` en madurez
    ``observe``/``warn`` no bloquea a nadie: si se rompe, lo peor que hace es
    dejar de avisar, y eso se nota. Contarlo como hallazgo llenaria la salida
    de rojo permanente hasta volverla ruido —y un gate que siempre esta rojo
    no se lee, se apaga. Queda como deuda listada, no como hallazgo.
    """
    if hook_id in REQUIRED_BEHAVIOR_COVERAGE:
        return True, "declarado en REQUIRED_BEHAVIOR_COVERAGE"
    if criticality in CRITICALITY_WARRANTING_TEST:
        return True, f"criticality={criticality}"
    if maturity in MATURITY_WARRANTING_TEST:
        return True, f"maturity={maturity} (ya bloquea trabajo)"
    return False, ""


def audit() -> dict[str, Any]:
    try:
        registry = registered_hooks()
        sources = test_text_index()
    except (OSError, ValueError) as exc:  # pragma: no cover - depende del fs
        raise AuditError(f"no se pudo leer el registro de hooks o los tests: {exc}") from exc

    if not registry:
        raise AuditError(
            "cognitive-os.yaml no declara ningun hook en harness.hooks. Sin "
            "denominador no hay medicion; esto no es 'cero hallazgos'."
        )

    evidence = build_evidence_index(sources)
    unparsed = sorted(key for key, bags in evidence.items() if not bags["parsed"])
    census = discover_census_tests()
    maturities, manifest_present = maturity_index()

    rows: list[dict[str, Any]] = []
    for hook_id in sorted(registry):
        entry = registry[hook_id]
        script = entry["script"]
        tests = discover_behavior_tests(hook_id, script)
        level, detail = classify_hook(hook_needles(hook_id, script), tests, evidence)
        criticality = classify_criticality(hook_id, script)
        maturity = maturities.get(hook_id, "")
        finding, reason = (False, "")
        if level == NO_TEST:
            finding, reason = warrants_test(hook_id, criticality, maturity)
        elif hook_id in REQUIRED_BEHAVIOR_COVERAGE and level != EXERCISED:
            finding = True
            reason = f"cobertura obligatoria pero solo {level}"
        rows.append(
            {
                "hook": hook_id,
                "script": script,
                "criticality": criticality,
                "maturity": maturity,
                "level": level,
                "tests": tests,
                "evidence": detail,
                "finding": finding,
                "finding_reason": reason,
            }
        )

    totals = {level: sum(1 for r in rows if r["level"] == level) for level in LEVELS}
    total = len(rows)
    measurable = total - totals[UNCLASSIFIABLE]
    return {
        "schema": "hook-exercise-audit/1",
        "sources": {
            "registry": {
                "path": "cognitive-os.yaml (harness.hooks)",
                "hooks": total,
            },
            "tests": {
                # Leido de hook_quality_audit.TEST_ROOTS, no copiado: la lista de
                # raices cambia (2026-08-19 se le sumo `tests/hooks`) y un reporte
                # que la hardcodea declara un corpus que no es el que midio.
                "roots": [str(root.relative_to(PROJECT_ROOT)) for root in TEST_ROOTS],
                "files": len(sources),
                "unparseable": len(unparsed),
                "unparseable_paths": unparsed,
            },
            "quality_manifest": {
                "path": str(QUALITY_MANIFEST.relative_to(PROJECT_ROOT)),
                "present": manifest_present,
            },
            "census_tests": census,
        },
        "totals": totals,
        "denominator_total": total,
        "denominator_measurable": measurable,
        "exercised_over_measurable": (
            round(totals[EXERCISED] / measurable, 4) if measurable else None
        ),
        "blind_ratio": round(totals[UNCLASSIFIABLE] / total, 4) if total else None,
        "blindness_alarm_threshold": BLINDNESS_ALARM,
        "hooks": rows,
        "findings": [r for r in rows if r["finding"]],
    }


# --------------------------------------------------------------------------- #
# Salida
# --------------------------------------------------------------------------- #
def render(report: dict[str, Any]) -> str:
    out: list[str] = []
    add = out.append
    src = report["sources"]
    t = report["totals"]
    total = report["denominator_total"]
    measurable = report["denominator_measurable"]

    add("HOOKS EJERCITADOS POR UN TEST vs SOLO NOMBRADOS")
    add("=" * 68)
    add("FUENTES (cada numero declara de donde sale)")
    add(f"  registro de hooks : {src['registry']['hooks']:>4} hooks  {src['registry']['path']}")
    add(
        f"  corpus de tests   : {src['tests']['files']:>4} archivos "
        f"({src['tests']['unparseable']} no parsean)  {', '.join(src['tests']['roots'])}"
    )
    manifest = src["quality_manifest"]
    add(
        f"  manifest calidad  : {'presente' if manifest['present'] else 'AUSENTE'}"
        f"  {manifest['path']}"
        + ("" if manifest["present"] else "  <- sin maturity: el criterio de hallazgo se degrada")
    )
    add(
        f"  tests censo       : {len(src['census_tests']):>4} "
        "(recorren todos los hooks por enumeracion; no acreditan a ninguno en particular)"
    )
    add("")

    add("NIVELES")
    add(f"  {EXERCISED:<15} (nombre pasado como argumento de un Call) : {t[EXERCISED]:>4}")
    add(f"  {NAMED_ONLY:<15} (literal string, nunca pasado a nada)     : {t[NAMED_ONLY]:>4}")
    add(f"  {NO_TEST:<15} (ningun behavior_test lo nombra)          : {t[NO_TEST]:>4}")
    add(
        f"  {UNCLASSIFIABLE:<15} (indireccion / archivo que no parsea)     : "
        f"{t[UNCLASSIFIABLE]:>4}   <- ceguera"
    )
    add("")

    add("DENOMINADORES (ningun porcentaje sin el suyo al lado)")
    add(f"  total registrado  : {total}")
    add(f"  medible           : {measurable}  = {total} - {t[UNCLASSIFIABLE]} UNCLASSIFIABLE")
    if measurable:
        add(
            f"  ejercitados sobre lo medible : "
            f"{report['exercised_over_measurable']:.2%} ({t[EXERCISED]}/{measurable})"
        )
        add(
            f"  solo nombrados               : "
            f"{t[NAMED_ONLY] / measurable:.2%} ({t[NAMED_ONLY]}/{measurable})"
        )
        add(
            f"  sin test                     : "
            f"{t[NO_TEST] / measurable:.2%} ({t[NO_TEST]}/{measurable})"
        )
    else:
        add("  ejercitados sobre lo medible : NO CALCULABLE (denominador medible = 0)")
    if report["blind_ratio"] is not None:
        add(f"  ceguera                      : {report['blind_ratio']:.2%} ({t[UNCLASSIFIABLE]}/{total})")
    add("")

    if report["blind_ratio"] is not None and report["blind_ratio"] >= BLINDNESS_ALARM:
        add(
            f"  AVISO: la ceguera ({report['blind_ratio']:.2%}) supera el umbral "
            f"{BLINDNESS_ALARM:.0%}. Los numeros de arriba describen la porcion\n"
            "  del corpus que este instrumento SI puede juzgar. Un cero bajo ceguera\n"
            "  alta no es un resultado: es una no-observacion."
        )
        add("")

    no_test = [r for r in report["hooks"] if r["level"] == NO_TEST]
    add(f"HOOKS SIN NINGUN TEST ({len(no_test)})")
    for row in no_test:
        mark = "HALLAZGO" if row["finding"] else "deuda   "
        maturity = row["maturity"] or "?"
        add(f"  [{mark}] {row['hook']:<42} {row['criticality']:<12} maturity={maturity}")
    if not no_test:
        add("  (ninguno)")
    add("")

    blind = [r for r in report["hooks"] if r["level"] == UNCLASSIFIABLE]
    add(f"UNCLASSIFIABLE ({len(blind)}) — el instrumento no puede juzgar estos casos")
    for row in blind:
        why = ", ".join(row["evidence"].get(UNCLASSIFIABLE, [])) or "sin detalle"
        add(f"  {row['hook']:<42} {why}")
    if not blind:
        add("  (ninguno)")
    add("")

    findings = report["findings"]
    add(f"HALLAZGOS ({len(findings)})")
    for row in findings:
        add(f"  {row['hook']:<42} {row['finding_reason']}")
    if not findings:
        add("  ninguno")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Entrada
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="hook_exercise_audit.py",
        description=(
            "Mide cuantos hooks registrados estan EJERCITADOS por un test "
            "(nombre pasado como argumento de un Call), cuantos solo NOMBRADOS, "
            "cuantos SIN TEST, y cuantos el instrumento no puede juzgar."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parser.add_argument("--json", action="store_true", help="emitir JSON en vez de texto")
    args = parser.parse_args(argv)

    try:
        report = audit()
    except AuditError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - un error no puede leerse como "sin hallazgos"
        print(f"error: fallo inesperado en la auditoria: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=False))
    else:
        print(render(report))
    return 1 if report["findings"] else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:  # pragma: no cover
        sys.exit(2)

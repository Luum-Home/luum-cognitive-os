#!/usr/bin/env python3
# SCOPE: os-only
"""Mide cuantos hooks estan EJERCITADOS por un test y cuantos solo NOMBRADOS.

Tener un `behavior_test` asociado no prueba que el test haga algo con el hook.
`manifests/hook-quality.yaml` responde "hay un test que menciona este hook",
que es una pregunta distinta —y mas facil de contestar que si— a "hay un test
que lo corre". Este script separa las dos, en un escalon de tres niveles:

    EXERCISED   el nombre viaja como argumento dentro de un nodo ``Call``:
                algo lo invoca, lo alimenta o lo parametriza. Vale tanto si el
                literal esta escrito en el argumento como si llega ahi a traves
                del nombre al que esta ligado (``HOOK = ...`` / ``run(HOOK)``).
    NAMED_ONLY  el nombre existe como literal string en el test y no se le pasa
                a nada. Es una mencion, no una ejecucion.
    NO_TEST     ningun test lo nombra siquiera.

POR QUE HAY UNA CUARTA CUBETA Y NO TRES
---------------------------------------
El punto ciego de la tecnica es la INDIRECCION: el literal esta ligado a un
nombre y el uso vive en otra linea, atras de ese nombre. Buena parte de esa
ceguera se resuelve siguiendo el nombre (``_NameFlow``, mas abajo): si el
nombre entra como argumento de un ``Call``, el literal que transporta esta
siendo pasado a algo y eso es EXERCISED; si todos sus usos mueren en la
sentencia que lo lee (``assert BATERIA <= despachados``), es una mencion.

Lo que NO se resuelve es cuando el valor se escapa por una via que este
instrumento no sigue:

    CASES = ["hooks/x.sh", "hooks/y.sh"]
    ...
    run(CASES[0])              # ¿cual de los dos?

    faltantes = BATERIA - despachados   # el valor se muda a otro nombre

Ahi no se puede afirmar ni que se ejercita ni que no. Clasificarlo
``NAMED_ONLY`` seria acusar de mencion vacia a un test que quiza corre el hook;
clasificarlo ``EXERCISED`` seria inventar. Un archivo de test que no parsea es
el mismo caso por otra via: el instrumento no puede leerlo.

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
  - El seguimiento del nombre es de un salto y cobarde: subscript, alias,
    ``return``, desempaquetado y comprension cortan con ceguera en vez de con
    una conclusion. Seguir el alias de ``faltantes = BATERIA - despachados``,
    por ejemplo, terminaria en el ``sorted(faltantes)`` del MENSAJE del assert
    y devolveria EXERCISED por un texto de error.
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


# --------------------------------------------------------------------------- #
# Flujo de un literal a traves del nombre al que esta ligado
# --------------------------------------------------------------------------- #
# Clases de uso de un nombre, de mas a menos evidencia:
#   ARG       algun uso del nombre viaja como argumento de un Call. El literal
#             que ese nombre transporta ESTA siendo pasado a algo.
#   ESCAPE    el nombre se lee, pero el valor se va por una via que este
#             instrumento no sigue (subscript, return, alias, comprension).
#             No se puede afirmar ni que se pasa ni que no: es ceguera.
#   TERMINAL  todos los usos del nombre mueren en la sentencia que lo lee
#             (compare, assert, receptor de un metodo). El literal existe y no
#             se le pasa a nada: es una mencion.
#   NONE      nadie lee el nombre. Constante muerta = mencion, no cobertura.
_ARG = "arg"
_ESCAPE = "escape"
_TERMINAL = "terminal"
_NONE = "none"
_USE_RANK = {_ARG: 3, _ESCAPE: 2, _TERMINAL: 1, _NONE: 0}

# Un `for a in B: for c in a: run(c)` son dos saltos. Mas que eso deja de ser
# seguimiento y empieza a ser adivinanza: se corta y se declara ceguera.
_MAX_HOPS = 3


def _binding_targets(target: ast.AST) -> list[str] | None:
    """Nombres que liga un ``for ... in``. ``None`` si no es un Name simple.

    Un desempaquetado (``for a, b in PAIRS``) reparte partes del elemento entre
    varios nombres y este instrumento no sabe cual parte lleva el literal.
    Devolver ``None`` es lo que hace que ese caso termine en ceguera y no en
    una afirmacion inventada.
    """
    if isinstance(target, ast.Name):
        return [target.id]
    return None


class _NameFlow:
    """Responde: ¿lo que este nombre transporta se le pasa a algun Call?

    Camina hacia ARRIBA desde cada lectura del nombre hasta encontrar un nodo
    que decida. Es deliberadamente cobarde: cualquier via por la que el valor
    pueda escaparse sin que se vea (subscript, return, alias, comprension) corta
    el analisis con ``ESCAPE``, no con una conclusion.
    """

    def __init__(self, tree: ast.AST) -> None:
        self._parent: dict[int, ast.AST] = {}
        self._loads: dict[str, list[ast.Name]] = {}
        self.bindings: list[tuple[list[str] | None, ast.AST]] = []
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                self._parent[id(child)] = node
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                self._loads.setdefault(node.id, []).append(node)
            elif isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                if targets and node.value is not None:
                    self.bindings.append((targets, node.value))
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.value is not None:
                    self.bindings.append(([node.target.id], node.value))
            elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
                # Coleccion ANONIMA: un `for h in (<literal>, <literal>): run(h)`
                # liga cada literal a la variable del loop sin pasar por ningun
                # nombre de modulo. Sin esto el literal cae en `plain` y el hook
                # se reporta como mencion vacia cuando el test lo esta corriendo
                # —un falso NAMED_ONLY, tan mentira como un falso EXERCISED.
                self.bindings.append((_binding_targets(node.target), node.iter))
        self._cache: dict[str, str] = {}

    # -- posicion de UNA lectura ------------------------------------------- #
    def _position(self, node: ast.AST) -> tuple[str, list[str] | None]:
        """Clase de esta lectura. El segundo campo son los nombres del salto."""
        cur = node
        for _ in range(64):  # cota dura: un arbol no anida tanto
            parent = self._parent.get(id(cur))
            if parent is None:
                return _TERMINAL, None
            if isinstance(parent, ast.Subscript) and parent.value is cur:
                # `CASES[0]` elige UN elemento y no se sabe cual. Afirmar que
                # todos los literales de CASES se ejercitan seria inventar.
                return _ESCAPE, None
            if isinstance(parent, ast.Call):
                if cur is not parent.func:
                    return _ARG, None
                # Posicion ``func``: `X.issubset(y)` no pasa X a nadie. Pero el
                # RESULTADO puede escaparse (`p = X.resolve()`), asi que se
                # sigue subiendo en vez de cerrar en TERMINAL.
            elif isinstance(parent, (ast.For, ast.AsyncFor)) and parent.iter is cur:
                return "iter", _binding_targets(parent.target)
            elif isinstance(parent, ast.comprehension) and parent.iter is cur:
                return "iter", _binding_targets(parent.target)
            elif isinstance(parent, (ast.Return, ast.Yield, ast.YieldFrom, ast.Await)):
                return _ESCAPE, None
            elif isinstance(parent, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                return _ESCAPE, None
            elif isinstance(parent, ast.Lambda) and parent.body is cur:
                return _ESCAPE, None
            elif isinstance(parent, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
                if parent.elt is cur:
                    return _ESCAPE, None
            elif isinstance(parent, ast.DictComp):
                if parent.key is cur or parent.value is cur:
                    return _ESCAPE, None
            elif isinstance(parent, ast.withitem):
                return _ESCAPE, None
            elif isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                return _TERMINAL, None
            cur = parent
        return _ESCAPE, None

    # -- clase de UN nombre ------------------------------------------------- #
    def use_class(self, name: str, _hops: int = 0, _seen: frozenset[str] = frozenset()) -> str:
        if _hops == 0 and name in self._cache:
            return self._cache[name]
        if name in _seen or _hops > _MAX_HOPS:
            return _ESCAPE
        loads = self._loads.get(name)
        if not loads:
            return _NONE
        best = _TERMINAL
        for load in loads:
            kind, targets = self._position(load)
            if kind == "iter":
                if targets is None:
                    kind = _ESCAPE
                else:
                    hopped = [
                        self.use_class(t, _hops + 1, _seen | {name}) for t in targets
                    ]
                    # Un nombre de loop que nadie lee no transporta nada: el
                    # literal sigue sin pasarsele a nadie -> mencion.
                    hopped = [_TERMINAL if h == _NONE else h for h in hopped]
                    kind = max(hopped, key=lambda k: _USE_RANK[k])
            if _USE_RANK[kind] > _USE_RANK[best]:
                best = kind
            if best == _ARG:
                break
        if _hops == 0:
            self._cache[name] = best
        return best


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

    El corpus son ~1300 archivos y cada recorrido extra se paga mil veces: el
    arbol se recorre una vez para las constantes y los Call, y otra para armar
    el mapa de padres y las lecturas de cada nombre. Las clases de uso se
    cachean por nombre dentro del archivo, asi que una constante leida en
    veinte lugares se resuelve una sola vez.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {"parsed": False, "call": "", "indirect": "", "plain": ""}

    excluded = _excluded_constant_ids(tree)

    call_ids: set[int] = set()
    constants: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            constants.append((id(node), node.value))
        elif isinstance(node, ast.Call):
            # Argumentos y keywords, nunca ``func``: `{...}.issubset(x)` menciona
            # el hook adentro del subarbol del Call pero no se lo pasa a nadie.
            for arg in list(node.args) + [kw.value for kw in node.keywords]:
                call_ids.update(_string_constants(arg))

    # Indireccion: el literal esta ligado a un nombre y el uso vive atras de ese
    # nombre, en otra linea. La clase de uso del nombre decide en cual de las
    # tres bolsas cae el literal; ``_NameFlow`` solo devuelve ``_ARG`` cuando
    # ve el nombre entrar como argumento de un Call, y ante cualquier via que no
    # sabe seguir devuelve ``_ESCAPE``, que es la bolsa ciega.
    flow = _NameFlow(tree)
    literal_class: dict[int, str] = {}
    for targets, value in flow.bindings:
        if targets is None:
            # Desempaquetado (`for a, b in PAIRS`): no se sabe que parte del
            # elemento lleva el literal. Ceguera declarada, no conclusion.
            cls = _ESCAPE
        else:
            cls = max(
                (flow.use_class(name) for name in targets),
                key=lambda k: _USE_RANK[k],
                default=_NONE,
            )
        if cls == _NONE:
            continue
        for lit in _string_constants(value):
            if _USE_RANK[cls] > _USE_RANK[literal_class.get(lit, _NONE)]:
                literal_class[lit] = cls

    call: list[str] = []
    indirect: list[str] = []
    plain: list[str] = []
    for node_id, value in constants:
        if node_id in excluded:
            continue
        cls = literal_class.get(node_id, _NONE)
        if node_id in call_ids or cls == _ARG:
            call.append(value)
        elif cls == _ESCAPE:
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

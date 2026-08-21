# SCOPE: os-only
"""¿Qué guarda tiene un test que la hace bloquear de verdad, con un payload real?

POR QUÉ EXISTE

    `scripts/hook_vitality_audit.py` sólo sabe leer telemetría. Una guarda que
    corrió 11.662 veces sin emitir exit 2 queda en `unproven-guard`: la
    telemetría no puede separar "no hubo ocasión" de "ya no puede atrapar".

    La evidencia que sí separa esos dos casos ya existe en el repo: un test que
    invoca la guarda y asierta `returncode == 2`. Este módulo la busca por
    PARSING (ast), no por keyword, y la devuelve con su procedencia de payload
    pegada.

LA CONDICIÓN QUE HACE QUE ESTO NO SEA VERDE BARATO

    Contar cualquier test que asierta 2 sería mover el baseline, no reducir el
    problema. El contraejemplo está documentado en el propio repo:
    `adversarial-review-gate` leía `.tool_result` mientras el harness manda
    `.tool_response`. Su test pasaba —con un dict escrito a mano que sí traía
    `.tool_result`— y la producción estuvo ciega 186 invocaciones seguidas.

    Por eso la capacidad sólo se da por probada cuando el payload del test sale
    de `tests/fixtures/payload-corpus/`, que es la forma congelada de lo que el
    harness mandó de verdad. Un test con payload inventado se cuenta aparte,
    como `handwritten`, y NO cierra nada.

LÍMITES DE ESTE INSTRUMENTO, DECLARADOS

    1. La atribución hook -> test es por literal de string: el test tiene que
       nombrar `<hook>.sh`. Un test que arma el path por partes no se ve. Eso
       es ceguera, y se declara en el `Census`, no se cuenta como "sin test".
    2. La aserción reconocida es `X.returncode == 2` (y `assertEqual`). Un test
       que verifica el bloqueo por el texto de stderr no cuenta.
    3. La procedencia `corpus` se mide a nivel MÓDULO, que es lo permisivo:
       basta que el archivo mencione el corpus. Se eligió permisivo a
       propósito — si el número permisivo ya es 0, el estricto no puede ser
       mayor, y el hallazgo queda a salvo de la crítica de haber apretado la
       definición hasta conseguir el resultado.

Read-only. Sin efectos.
"""

from __future__ import annotations

import ast
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path

from cos_lib.measurement import Census

__all__ = [
    "FiringEvidence",
    "PAYLOAD_CORPUS_DIR",
    "scan_firing_tests",
    "firing_evidence_census",
]

PAYLOAD_CORPUS_DIR = "tests/fixtures/payload-corpus"

# Referencias que prueban que el archivo lee el corpus congelado.
_CORPUS_RE = re.compile(r"payload-corpus|harness-payloads")
# `<name>.sh` dentro de cualquier literal del test.
_HOOK_RE = re.compile(r"([A-Za-z0-9_-]+)\.sh")
# Atributos que representan el código de salida de un proceso.
_RETURNCODE_ATTRS = frozenset({"returncode", "exit_code"})
_BLOCKING_EXIT_CODE = 2


@dataclass(frozen=True)
class FiringEvidence:
    """Los tests que hacen bloquear a un hook, partidos por procedencia."""

    hook: str
    corpus_backed: tuple[str, ...] = ()
    handwritten: tuple[str, ...] = ()

    @property
    def capacity_proven(self) -> bool:
        """Sólo el payload real prueba capacidad. Ver el docstring del módulo."""
        return bool(self.corpus_backed)

    @property
    def payload_source(self) -> str:
        if self.corpus_backed:
            return "corpus"
        if self.handwritten:
            return "handwritten"
        return "none"


class _ModuleScan(ast.NodeVisitor):
    """Un pase por el AST del módulo: literales, y si alguna función asierta 2."""

    def __init__(self) -> None:
        self.strings: list[str] = []
        self.asserts_blocking_exit = False

    # -- literales -------------------------------------------------------
    def visit_Constant(self, node: ast.Constant) -> None:  # noqa: N802
        if isinstance(node.value, str):
            self.strings.append(node.value)
        self.generic_visit(node)

    # -- aserciones ------------------------------------------------------
    @staticmethod
    def _is_returncode(node: ast.expr) -> bool:
        return isinstance(node, ast.Attribute) and node.attr in _RETURNCODE_ATTRS

    @staticmethod
    def _is_blocking_literal(node: ast.expr) -> bool:
        return (
            isinstance(node, ast.Constant)
            and not isinstance(node.value, bool)
            and node.value == _BLOCKING_EXIT_CODE
        )

    def visit_Compare(self, node: ast.Compare) -> None:  # noqa: N802
        if len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left, right = node.left, node.comparators[0]
            if (self._is_returncode(left) and self._is_blocking_literal(right)) or (
                self._is_blocking_literal(left) and self._is_returncode(right)
            ):
                self.asserts_blocking_exit = True
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func = node.func
        name = (
            func.attr
            if isinstance(func, ast.Attribute)
            else (func.id if isinstance(func, ast.Name) else "")
        )
        if name in {"assertEqual", "assert_equal"} and len(node.args) == 2:
            a, b = node.args
            if (self._is_returncode(a) and self._is_blocking_literal(b)) or (
                self._is_blocking_literal(a) and self._is_returncode(b)
            ):
                self.asserts_blocking_exit = True
        self.generic_visit(node)


@dataclass
class _Accumulator:
    corpus: set[str] = field(default_factory=set)
    hand: set[str] = field(default_factory=set)


def scan_firing_tests(
    project_dir: Path,
    known_hooks: set[str] | None = None,
    tests_dir: str = "tests",
) -> tuple[dict[str, FiringEvidence], dict[str, int]]:
    """Recorre los tests y devuelve (evidencia por hook, contadores de ceguera).

    ``known_hooks`` acota la atribución: sin él, cualquier literal ``*.sh`` de
    un test se leería como un hook. Con él, sólo se atribuye a hooks que
    realmente existen en el registro que pasó el llamador.
    """
    root = Path(project_dir)
    base = root / tests_dir
    acc: dict[str, _Accumulator] = {}
    blind = {"tests_no_parseables": 0}
    scanned = 0
    firing_files = 0

    for path in sorted(base.rglob("*.py")):
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            blind["tests_no_parseables"] += 1
            continue
        try:
            # Parsing someone else's source must not emit their SyntaxWarnings
            # into a governance tool's stdout.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                tree = ast.parse(source)
        except SyntaxError:
            blind["tests_no_parseables"] += 1
            continue
        scanned += 1

        scan = _ModuleScan()
        scan.visit(tree)
        if not scan.asserts_blocking_exit:
            continue
        firing_files += 1

        blob = "\n".join(scan.strings)
        from_corpus = bool(_CORPUS_RE.search(blob))
        rel = str(path.relative_to(root))

        named: set[str] = set()
        for literal in scan.strings:
            for match in _HOOK_RE.finditer(literal):
                name = match.group(1)
                if known_hooks is None or name in known_hooks:
                    named.add(name)
        for hook in named:
            slot = acc.setdefault(hook, _Accumulator())
            (slot.corpus if from_corpus else slot.hand).add(rel)

    evidence = {
        hook: FiringEvidence(
            hook=hook,
            corpus_backed=tuple(sorted(slot.corpus)),
            handwritten=tuple(sorted(slot.hand)),
        )
        for hook, slot in sorted(acc.items())
    }
    stats = {
        "test_files_scanned": scanned,
        "test_files_asserting_exit_2": firing_files,
        **blind,
    }
    return evidence, stats


def firing_evidence_census(
    hooks: list[str],
    evidence: dict[str, FiringEvidence],
    sources: tuple[str, ...],
    how: str,
    window: str | None = None,
) -> Census:
    """Censo de una población de hooks contra la evidencia de disparo.

    No hay ceguera declarable acá: cada hook de ``hooks`` cae exactamente en un
    desenlace. La ceguera del INSTRUMENTO (tests que no se pudieron parsear,
    tests que arman el path del hook por partes) la reporta ``scan_firing_tests``
    y el llamador la vuelca en ``notes``.

    ``how`` lo pone el LLAMADOR y no tiene default a propósito: esta función es
    una librería, no un CLI. El comando que reproduce el número es el del
    consumidor (``scripts/hook_vitality_audit.py`` hoy), y un default acá
    publicaría un comando que nadie corrió.
    """
    corpus = sum(1 for h in hooks if h in evidence and evidence[h].capacity_proven)
    hand = sum(
        1
        for h in hooks
        if h in evidence and not evidence[h].capacity_proven and evidence[h].handwritten
    )
    return Census(
        subject="hooks con test de disparo (returncode == 2)",
        sources=sources,
        buckets={
            "capacidad_probada_con_payload_del_corpus": corpus,
            "test_de_disparo_con_payload_inventado": hand,
            "sin_test_de_disparo": len(hooks) - corpus - hand,
        },
        blind={"ninguna": 0},
        how=how,
        window=window,
    )

#!/usr/bin/env python3
# SCOPE: os-only
"""Censo estático: ¿los tests versionados pueden importar lo que importan?

Un test versionado que no puede correr en el entorno que el repo instala es un
defecto invisible: no aparece como rojo, aparece como error de colección meses
después. Este censo lo hace visible ANTES, sin ejecutar la suite: parsea el AST
de cada archivo de test, extrae los imports absolutos de primer nivel y le
pregunta a ``importlib.util.find_spec`` si el intérprete actual puede
resolverlos.

Dos defectos distintos, con arreglos distintos:

* **declarado y no instalado** — el import está en las dependencias de algún
  ``pyproject.toml`` del repo, pero el camino de instalación no lo trae. El
  arreglo va en la instalación.
* **no declarado en ningún lado** — nadie prometió nunca esa dependencia. El
  arreglo va en el paquete que la usa.

Lo que NO es un defecto, y por eso no se cuenta como tal:

* un import dentro de ``try/except ImportError`` — es una dependencia opcional
  declarada en código;
* ``pytest.importorskip("x")`` — es la declaración explícita de "esto puede
  faltar";
* ``importlib.util.find_spec("x")`` usado como guarda de un ``skipif``.

Uso::

    python3 scripts/audit_test_import_resolvability.py            # texto
    python3 scripts/audit_test_import_resolvability.py --json     # JSON
    python3 scripts/audit_test_import_resolvability.py --gate     # exit 1 si hay defectos

Exit codes: 0 sin hallazgos (o sin ``--gate``), 1 con hallazgos bajo ``--gate``,
2 error del propio instrumento.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cos_lib.measurement import Census  # noqa: E402

HOW = "python3 scripts/audit_test_import_resolvability.py --json"

EXCEPTIONS_MANIFEST = REPO_ROOT / "manifests" / "test-import-exceptions.yaml"

#: Nombres que ``find_spec`` resuelve como paquete del repo pero que en realidad
#: son directorios sueltos sin ``__init__.py``. No hace falta listarlos: el
#: propio ``find_spec`` con la raíz del repo en ``sys.path`` los ve igual que
#: los ve pytest, que inserta el rootdir.

_EXEMPT_CALLS = frozenset({"importorskip", "find_spec", "import_module"})


def tracked_test_files() -> list[Path]:
    """Archivos de test VERSIONADOS. El árbol de trabajo no es la población.

    Lo que no está versionado no viaja al checkout de nadie más, así que no
    puede fallar en el checkout de nadie más — y lo que estaba versionado sin
    su ``conftest.py`` fue exactamente el caso que originó este censo.
    """
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    files: list[Path] = []
    for rel in out.split("\0"):
        if not rel:
            continue
        p = Path(rel)
        name = p.name
        is_test_name = name.startswith("test_") or name.endswith("_test.py")
        in_test_dir = any(part in {"tests", "test"} for part in p.parts)
        if not (is_test_name or (in_test_dir and name == "conftest.py")):
            continue
        if not in_test_dir and not is_test_name:
            continue
        files.append(p)
    return sorted(files)


@dataclass
class FileScan:
    path: Path
    required: set[str] = field(default_factory=set)
    optional: set[str] = field(default_factory=set)
    deferred: set[str] = field(default_factory=set)
    parse_error: str | None = None
    relative_beyond: int = 0


class _ImportCollector(ast.NodeVisitor):
    """Separa imports exigidos de imports declarados como opcionales."""

    def __init__(self) -> None:
        self.required: set[str] = set()
        self.optional: set[str] = set()
        self.deferred: set[str] = set()
        self.relative_beyond = 0
        self._guard_depth = 0
        self._func_depth = 0

    # -- guardas -----------------------------------------------------------
    def visit_Try(self, node: ast.Try) -> None:
        guards = _handles_import_error(node)
        for child in node.body:
            if guards:
                self._guard_depth += 1
                self.visit(child)
                self._guard_depth -= 1
            else:
                self.visit(child)
        for handler in node.handlers:
            # Un import dentro de `except ImportError:` es el fallback de un
            # import opcional (`import tomli as tomllib`). Nunca es exigido.
            if guards:
                self._guard_depth += 1
                self.generic_visit(handler)
                self._guard_depth -= 1
            else:
                self.generic_visit(handler)
        for child in node.orelse + node.finalbody:
            self.visit(child)

    def _visit_function(self, node: ast.AST) -> None:
        # Un import dentro de una función no corre en la colección: corre si el
        # test corre, y casi siempre va con un marker de skip. No es la falla
        # que este censo persigue.
        self._func_depth += 1
        self.generic_visit(node)
        self._func_depth -= 1

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function
    visit_Lambda = _visit_function

    def visit_Call(self, node: ast.Call) -> None:
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
        if name in _EXEMPT_CALLS:
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    self.optional.add(arg.value.split(".")[0])
        self.generic_visit(node)

    # -- imports -----------------------------------------------------------
    def _record(self, top: str) -> None:
        if self._guard_depth:
            self.optional.add(top)
        elif self._func_depth:
            self.deferred.add(top)
        else:
            self.required.add(top)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._record(alias.name.split(".")[0])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level:
            # Import relativo: qué resuelve depende del rootdir y de los
            # conftest, no del entorno. Fuera del alcance de este instrumento.
            self.relative_beyond += 1
            return
        if node.module:
            self._record(node.module.split(".")[0])


def _handles_import_error(node: ast.Try) -> bool:
    for handler in node.handlers:
        exc = handler.type
        names: list[str] = []
        if isinstance(exc, ast.Name):
            names = [exc.id]
        elif isinstance(exc, ast.Attribute):
            names = [exc.attr]
        elif isinstance(exc, ast.Tuple):
            for elt in exc.elts:
                if isinstance(elt, ast.Name):
                    names.append(elt.id)
                elif isinstance(elt, ast.Attribute):
                    names.append(elt.attr)
        elif exc is None:
            return True  # bare except
        if any(n in {"ImportError", "ModuleNotFoundError", "Exception"} for n in names):
            return True
    return False


def scan(path: Path) -> FileScan:
    result = FileScan(path=path)
    try:
        src = (REPO_ROOT / path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        result.parse_error = f"{type(exc).__name__}: {exc}"
        return result
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError as exc:
        result.parse_error = f"SyntaxError: {exc}"
        return result
    collector = _ImportCollector()
    collector.visit(tree)
    result.required = collector.required
    result.optional = collector.optional
    result.deferred = collector.deferred
    result.relative_beyond = collector.relative_beyond
    # Un módulo declarado opcional en cualquier punto del archivo lo es para
    # todo el archivo: el idioma habitual es `try: import x / except: x = None`
    # arriba y usarlo abajo.
    result.required -= result.optional
    return result


_FIRST_PARTY: set[str] | None = None


def first_party_modules() -> set[str]:
    """Módulos que VIVEN en el repo, resueltos por ``sys.path``, no por el entorno.

    Muchísimos tests hacen ``sys.path.insert(0, str(ROOT / "cos_lib"))`` y después
    ``from claude_executor import ...``. Ese import no lo satisface ninguna
    dependencia instalada: lo satisface un archivo del propio repo. Contarlo como
    dependencia faltante mandaría a instalar un paquete de PyPI que no existe —
    el error caro. Se detecta por presencia del archivo entre los trackeados, no
    por adivinar qué hace cada manipulación de ``sys.path``.
    """
    global _FIRST_PARTY
    if _FIRST_PARTY is not None:
        return _FIRST_PARTY
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    names: set[str] = set()
    for rel in out.split("\0"):
        if not rel or not rel.endswith(".py"):
            continue
        path = Path(rel)
        if path.name == "__init__.py":
            if path.parent.name:
                names.add(path.parent.name)
        else:
            names.add(path.stem)
        # `sys.path.insert(<dir>)` + `from <subdir> import x` para paquetes
        # namespace sin __init__.py.
        for part in path.parent.parts:
            names.add(part)
    _FIRST_PARTY = names
    return names


_RESOLVE_CACHE: dict[str, bool] = {}


def resolvable(module: str) -> bool:
    if module in _RESOLVE_CACHE:
        return _RESOLVE_CACHE[module]
    ok = module in sys.stdlib_module_names or module in sys.builtin_module_names
    if not ok:
        try:
            ok = importlib.util.find_spec(module) is not None
        except (ImportError, ValueError, AttributeError, TypeError):
            ok = False
    _RESOLVE_CACHE[module] = ok
    return ok


def _norm(name: str) -> str:
    return name.lower().replace("_", "-")


def declared_dependencies() -> dict[str, list[str]]:
    """``{distribución normalizada: [pyproject que la declara, ...]}``."""
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", "*pyproject.toml"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    declared: dict[str, list[str]] = {}
    for rel in out.split("\0"):
        if not rel:
            continue
        try:
            data = tomllib.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        project = data.get("project", {})
        specs: list[str] = list(project.get("dependencies", []) or [])
        for group in (project.get("optional-dependencies", {}) or {}).values():
            specs.extend(group or [])
        for spec in specs:
            dist = _norm(
                spec.split(";")[0]
                .split("[")[0]
                .split("=")[0]
                .split(">")[0]
                .split("<")[0]
                .split("!")[0]
                .split("~")[0]
                .strip()
            )
            if dist:
                declared.setdefault(dist, []).append(rel)
    return declared


#: Módulos de import cuyo nombre no coincide con el de la distribución que los
#: provee. Sin este mapa, un import declarado se contaría como no declarado —
#: que es el error caro de los dos, porque manda a arreglar el paquete
#: equivocado.
IMPORT_TO_DIST = {
    "yaml": "pyyaml",
    "dotenv": "python-dotenv",
    "attr": "attrs",
    "dateutil": "python-dateutil",
    "PIL": "pillow",
    "sklearn": "scikit-learn",
    "lingua": "lingua-language-detector",
    "git": "gitpython",
    "jwt": "pyjwt",
    "bs4": "beautifulsoup4",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "serial": "pyserial",
    "OpenSSL": "pyopenssl",
    "zmq": "pyzmq",
}


def dist_candidates(module: str) -> list[str]:
    cands = [_norm(module)]
    mapped = IMPORT_TO_DIST.get(module)
    if mapped:
        cands.append(_norm(mapped))
    return cands


def build_census() -> tuple[Census, dict]:
    files = tracked_test_files()
    declared = declared_dependencies()

    buckets = {
        "resuelve": 0,
        "declarado-no-instalado": 0,
        "no-declarado": 0,
    }
    blind = {
        "no-parsea": 0,
        "solo-falta-primera-parte": 0,
        "solo-falta-en-cuerpo-de-funcion": 0,
    }
    detail_declared: dict[str, dict] = {}
    detail_undeclared: dict[str, dict] = {}
    dirs_affected: set[str] = set()
    relative_imports = 0

    for path in files:
        scanned = scan(path)
        if scanned.parse_error:
            blind["no-parsea"] += 1
            continue
        relative_imports += scanned.relative_beyond
        missing_all = sorted(m for m in scanned.required if not resolvable(m))
        if not missing_all:
            if any(
                m not in first_party_modules()
                for m in (scanned.deferred - scanned.required - scanned.optional)
                if not resolvable(m)
            ):
                blind["solo-falta-en-cuerpo-de-funcion"] += 1
            else:
                buckets["resuelve"] += 1
            continue
        deferred_missing = sorted(
            m
            for m in (scanned.deferred - scanned.required - scanned.optional)
            if not resolvable(m)
        )
        fp = first_party_modules()
        missing = [m for m in missing_all if m not in fp]
        if not missing:
            # Todo lo que falta vive en el repo: lo resuelve un `sys.path.insert`
            # que este instrumento no modela. No es un defecto de dependencias y
            # tampoco es una resolución verificada — es ceguera declarada.
            blind["solo-falta-primera-parte"] += 1
            continue
        rel_dir = str(path.parent)
        dirs_affected.add(rel_dir)
        mods_declared: dict[str, list[str]] = {}
        mods_undeclared: list[str] = []
        for mod in missing:
            owners: list[str] = []
            for cand in dist_candidates(mod):
                owners.extend(declared.get(cand, []))
            if owners:
                mods_declared[mod] = sorted(set(owners))
            else:
                mods_undeclared.append(mod)
        entry = {
            "dir": rel_dir,
            "declared": mods_declared,
            "undeclared": mods_undeclared,
        }
        if mods_undeclared:
            buckets["no-declarado"] += 1
            detail_undeclared[str(path)] = entry
        else:
            buckets["declarado-no-instalado"] += 1
            detail_declared[str(path)] = entry

    census = Census(
        subject="tests versionados cuyos imports el entorno actual no resuelve",
        sources=(
            "git ls-files -- '*.py' (solo trackeados)",
            f"importlib.util.find_spec bajo {sys.executable}",
            "dependencies + optional-dependencies de todo pyproject.toml versionado",
        ),
        buckets=buckets,
        blind=blind,
        how=HOW,
        notes=(
            "Los imports dentro de try/except ImportError, los de "
            "pytest.importorskip() y los guardados por find_spec() NO se "
            "cuentan como defecto: son dependencias opcionales declaradas.",
            f"{relative_imports} imports relativos ignorados: qué resuelven "
            "depende del rootdir y de los conftest, no del entorno.",
            "Los imports dentro de cuerpos de función no cuentan: no corren en "
            "la colección. Los archivos a los que SOLO les falta eso quedan "
            "declarados ciegos, no resueltos.",
            "Los módulos que existen entre los archivos trackeados del repo se "
            "consideran de primera parte: los resuelve un sys.path.insert, no "
            "una dependencia instalada. Un archivo al que SOLO le falta eso "
            "cuenta como ciego, no como resuelto.",
        ),
    )
    payload = {
        "census": {
            "subject": census.subject,
            "how": census.how,
            "population": census.population,
            "measurable": census.measurable,
            "buckets": dict(census.buckets),
            "blind": dict(census.blind),
            "notes": list(census.notes),
        },
        "interpreter": sys.executable,
        "dirs_affected": sorted(dirs_affected),
        "declared_not_installed": detail_declared,
        "undeclared_anywhere": detail_undeclared,
    }
    return census, payload


def load_exceptions() -> dict[str, str]:
    """Excepciones aceptadas: ``{ruta: motivo}``. Igualdad exacta, sin colchón."""
    if not EXCEPTIONS_MANIFEST.exists():
        return {}
    try:
        import yaml
    except ImportError:  # pragma: no cover - pyyaml es dependencia del core
        return {}
    data = yaml.safe_load(EXCEPTIONS_MANIFEST.read_text(encoding="utf-8")) or {}
    entries = data.get("accepted", []) or []
    return {e["path"]: e.get("reason", "") for e in entries if isinstance(e, dict)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="salida JSON")
    parser.add_argument(
        "--gate",
        action="store_true",
        help="exit 1 si hay archivos no cubiertos por manifests/test-import-exceptions.yaml",
    )
    args = parser.parse_args(argv)

    census, payload = build_census()
    offenders = set(payload["declared_not_installed"]) | set(payload["undeclared_anywhere"])
    accepted = load_exceptions()
    payload["accepted_exceptions"] = sorted(accepted)
    payload["unaccepted"] = sorted(offenders - set(accepted))
    payload["stale_exceptions"] = sorted(set(accepted) - offenders)

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"Censo: {census.subject}")
        print(f"  población (tests versionados): {census.population}")
        for name in ("resuelve", "declarado-no-instalado", "no-declarado"):
            print(f"  {name}: {census.describe(name)}")
        print(f"  ciegos: {dict(census.blind)}")
        print(f"  directorios afectados: {len(payload['dirs_affected'])}")
        for d in payload["dirs_affected"]:
            print(f"    - {d}")
        if payload["unaccepted"]:
            print(f"\nSIN ACEPTAR ({len(payload['unaccepted'])}):")
            for p in payload["unaccepted"]:
                entry = payload["declared_not_installed"].get(p) or payload[
                    "undeclared_anywhere"
                ][p]
                mods = sorted(set(entry["declared"]) | set(entry["undeclared"]))
                print(f"  {p}: falta {', '.join(mods)}")
        if payload["stale_exceptions"]:
            print(f"\nEXCEPCIONES VENCIDAS ({len(payload['stale_exceptions'])}):")
            for p in payload["stale_exceptions"]:
                print(f"  {p} ya resuelve; sacala de {EXCEPTIONS_MANIFEST.name}")

    if args.gate and (payload["unaccepted"] or payload["stale_exceptions"]):
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - exit 2 reservado al error del instrumento
        print(f"error del instrumento: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)

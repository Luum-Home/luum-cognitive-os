#!/usr/bin/env python3
# SCOPE: os-only
"""Audit whether each primitive's paired proof actually EXECUTES that primitive.

Orthogonal to both `primitive_scope_health.py` (which counts proof *levels*
derived from the test FILE NAME) and `primitive_behavior_depth_audit.py` (which
derives depth from name tokens too). Both of those measure the manifest against
itself: a test called `..._scope_family.py` is `family` because of the substring,
not because of what it runs.

This audit reads the paired test's SOURCE and answers one mechanical question:
does an execution site inside that test reference this primitive?

Discriminator (Python tests, AST-based):
  1. Collect execution sites: subprocess.*, runpy.*, os.system/popen,
     importlib.util.spec_from_file_location, importlib.import_module, pytest.main,
     plus local helper functions that transitively contain one.
  2. Constant-fold the arguments of those sites into a set of string fragments,
     resolving module/function-level assignments, `for` targets, and
     `pytest.mark.parametrize` payloads.
  3. A row is `executes` iff the primitive's repo-relative path (or its basename,
     when unambiguous across the registry) appears among those fragments.

Paths that merely appear in the file — a hardcoded list walked with
`path.exists()` — are NOT execution sites, which is exactly the case this audit
exists to separate. Shell/bats proofs fall back to a line-level heuristic
(execution marker and basename on the same line); the JSON reports how many rows
took that path so the fallback's weight is visible.

Classes:
  executes                 execution site references the primitive
  not-executed             executable artifact, no execution site references it
  non-executable-artifact  artifact that cannot be executed (.md/.yaml/.json/...)
  missing-test             paired test does not exist on disk
  no-test                  no paired test at all

Budget: `proof_execution_budget.max_rows_without_execution` in
manifests/primitive-scope-classification.yaml. Ratchet: measured reality, may
only go down.

Exit codes: 0 no findings, 1 findings, 2 error.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_HEALTH_PATH = ROOT / "scripts" / "primitive_scope_health.py"
_SPEC = importlib.util.spec_from_file_location("primitive_scope_health", _HEALTH_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - install error
    raise RuntimeError(f"cannot load scope health from {_HEALTH_PATH}")
primitive_scope_health = importlib.util.module_from_spec(_SPEC)
sys.modules["primitive_scope_health"] = primitive_scope_health
_SPEC.loader.exec_module(primitive_scope_health)

# Artifact suffixes that a test can actually run. Everything else is prose or
# data: the strongest honest proof for those is parsing, not execution.
EXECUTABLE_SUFFIXES = {".sh", ".bash", ".py", ".bats", ".js", ".mjs", ".ts", ".rb", ".pl"}

EXEC_FUNCS = {
    "run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput",
    "run_path", "run_module", "system", "popen", "execv", "execvp", "spawn",
    "spec_from_file_location", "import_module", "main", "source_from_cache",
}
EXEC_MODULES = {"subprocess", "runpy", "os", "pytest", "importlib", "util", "sh"}

SHELL_EXEC_RE = re.compile(
    r"(^|[\s;|&(`$])(run|bash|sh|zsh|source|\.|exec|python3?|env|timeout|command)\s|[$`]\(|\./"
)


@dataclass(frozen=True)
class ExecRow:
    path: str
    kind: str
    scope: str
    proof_level: str
    paired_portability_test: str | None
    execution_class: str
    evidence: str


@dataclass(frozen=True)
class Finding:
    subject: str
    severity: str
    code: str
    detail: str


def _load_policy(root: Path) -> dict[str, Any]:
    path = root / "manifests" / "primitive-scope-classification.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


# --------------------------------------------------------------------------
# Python discriminator
# --------------------------------------------------------------------------

def _fragments(node: ast.AST, env: dict[str, list[ast.AST]], depth: int = 0) -> set[str]:
    """Constant-fold an expression into the string fragments it can produce."""
    out: set[str] = set()
    if depth > 6 or node is None:
        return out
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            out.add(node.value)
        return out
    if isinstance(node, ast.JoinedStr):
        for part in node.values:
            out |= _fragments(part, env, depth + 1)
        return out
    if isinstance(node, ast.FormattedValue):
        return _fragments(node.value, env, depth + 1)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        for elt in node.elts:
            out |= _fragments(elt, env, depth + 1)
        return out
    if isinstance(node, ast.Starred):
        return _fragments(node.value, env, depth + 1)
    if isinstance(node, ast.BinOp):
        out |= _fragments(node.left, env, depth + 1)
        out |= _fragments(node.right, env, depth + 1)
        return out
    if isinstance(node, ast.Subscript):
        return _fragments(node.value, env, depth + 1)
    if isinstance(node, (ast.Attribute,)):
        return _fragments(node.value, env, depth + 1)
    if isinstance(node, ast.Name):
        for bound in env.get(node.id, [])[:8]:
            out |= _fragments(bound, env, depth + 1)
        return out
    if isinstance(node, ast.Call):
        for arg in list(node.args) + [kw.value for kw in node.keywords]:
            out |= _fragments(arg, env, depth + 1)
        return out
    if isinstance(node, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
        out |= _fragments(node.elt, env, depth + 1)
        for gen in node.generators:
            out |= _fragments(gen.iter, env, depth + 1)
        return out
    if isinstance(node, ast.IfExp):
        out |= _fragments(node.body, env, depth + 1)
        out |= _fragments(node.orelse, env, depth + 1)
        return out
    return out


def _bind(env: dict[str, list[ast.AST]], target: ast.AST, value: ast.AST) -> None:
    if isinstance(target, ast.Name):
        env.setdefault(target.id, []).append(value)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            _bind(env, elt, value)


def _build_env(tree: ast.AST) -> dict[str, list[ast.AST]]:
    env: dict[str, list[ast.AST]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Parameter defaults: `def _run(hook=FULL_HOOK)` executes FULL_HOOK
            # on every call site that omits the argument.
            spec = node.args
            params = list(spec.posonlyargs) + list(spec.args)
            for arg, default in zip(reversed(params), reversed(list(spec.defaults))):
                env.setdefault(arg.arg, []).append(default)
            for arg, default in zip(spec.kwonlyargs, spec.kw_defaults):
                if default is not None:
                    env.setdefault(arg.arg, []).append(default)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                _bind(env, target, node.value)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and node.value is not None:
            _bind(env, node.target, node.value)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            _bind(env, node.target, node.iter)
        elif isinstance(node, ast.comprehension):
            _bind(env, node.target, node.iter)
        elif isinstance(node, ast.withitem) and node.optional_vars is not None:
            _bind(env, node.optional_vars, node.context_expr)
    # pytest.mark.parametrize("a,b", [...]) -> bind each declared param name.
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in node.decorator_list:
            if not isinstance(deco, ast.Call) or not deco.args:
                continue
            name = deco.func.attr if isinstance(deco.func, ast.Attribute) else getattr(deco.func, "id", "")
            if name != "parametrize":
                continue
            spec = deco.args[0]
            payload = deco.args[1] if len(deco.args) > 1 else None
            names: list[str] = []
            if isinstance(spec, ast.Constant) and isinstance(spec.value, str):
                names = [p.strip() for p in spec.value.replace(" ", ",").split(",") if p.strip()]
            elif isinstance(spec, (ast.List, ast.Tuple)):
                names = [e.value for e in spec.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            if payload is not None:
                for pname in names:
                    env.setdefault(pname, []).append(payload)
    return env


def _call_name(call: ast.Call) -> tuple[str, str]:
    func = call.func
    if isinstance(func, ast.Attribute):
        base = func.value
        base_name = base.id if isinstance(base, ast.Name) else (
            base.attr if isinstance(base, ast.Attribute) else ""
        )
        return base_name, func.attr
    if isinstance(func, ast.Name):
        return "", func.id
    return "", ""


def _is_exec_call(call: ast.Call, local_exec_helpers: set[str]) -> bool:
    base, attr = _call_name(call)
    if attr in local_exec_helpers or base in local_exec_helpers:
        return True
    if attr not in EXEC_FUNCS:
        return False
    if base:
        return base in EXEC_MODULES or base.lower().endswith("subprocess")
    # bare name: only accept the unambiguous ones
    return attr in {"run_path", "run_module", "spec_from_file_location", "import_module"}


def _local_exec_helpers(tree: ast.AST) -> set[str]:
    """Function names in this module whose body (transitively) executes something."""
    bodies: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bodies[node.name] = node
    helpers: set[str] = set()
    for _ in range(3):  # fixpoint, bounded
        grew = False
        for name, node in bodies.items():
            if name in helpers:
                continue
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call) and _is_exec_call(sub, helpers):
                    helpers.add(name)
                    grew = True
                    break
        if not grew:
            break
    return helpers


def _import_fragments(tree: ast.AST) -> set[str]:
    """Static imports execute the imported module's top level.

    `from scripts import cos_test_slow_report` and
    `import scripts.precommit_content_hash as dedupe` both run the primitive.
    Rendered as repo-relative candidate paths so path matching stays the same.
    """
    out: set[str] = set()

    def emit(dotted: str) -> None:
        if not dotted:
            return
        rel = dotted.replace(".", "/")
        out.add(rel + ".py")
        out.add(rel + "/__init__.py")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                emit(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import: cannot resolve to a repo path
                continue
            base = node.module or ""
            emit(base)
            for alias in node.names:
                emit(f"{base}.{alias.name}" if base else alias.name)
    return out


def _python_fragments(source: str) -> tuple[set[str], set[str]] | None:
    """Return (call-site fragments, static-import fragments)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    return _python_exec_fragments_inner(source), _import_fragments(ast.parse(source))


def _python_exec_fragments_inner(source: str) -> set[str]:
    tree = ast.parse(source)
    env = _build_env(tree)
    helpers = _local_exec_helpers(tree)
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_exec_call(node, helpers):
            for arg in list(node.args) + [kw.value for kw in node.keywords]:
                out |= _fragments(arg, env)
    return out


_SHELL_ASSIGN_RE = re.compile(r"""^\s*(?:local\s+|export\s+|declare\s+-\w+\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.+)$""")


def _shell_exec_lines(source: str) -> list[str]:
    """Execution lines, with shell variable indirection resolved one hop.

    A bats proof writes `HOOK="hooks/x.sh"` on one line and `bash "$HOOK"` on
    another; neither line alone carries both the execution marker and the path.
    Every exec line that references a known variable is expanded with that
    variable's literal value before matching.
    """
    lines = source.splitlines()
    assigns: dict[str, str] = {}
    for line in lines:
        m = _SHELL_ASSIGN_RE.match(line)
        if m:
            assigns[m.group(1)] = m.group(2).strip().strip('"\'')
    out: list[str] = []
    for line in lines:
        if not SHELL_EXEC_RE.search(line):
            continue
        expanded = line
        for name, value in assigns.items():
            if f"${name}" in line or f"${{{name}}}" in line:
                expanded += " " + value
        out.append(expanded)
    return out


# --------------------------------------------------------------------------
# Row classification
# --------------------------------------------------------------------------

def _matches(fragments: set[str], rel_path: str, basename_unique: bool) -> str | None:
    base = Path(rel_path).name
    for frag in fragments:
        if not frag:
            continue
        norm = frag.strip().lstrip("./")
        # Strong: the fragment IS the row path (possibly absolute).
        if norm == rel_path or norm.endswith("/" + rel_path):
            return frag
        # Weak: the fragment is only a tail of the row path (bare basename, or a
        # partial suffix). Accepted only when no other registry row shares that
        # basename, otherwise `import yaml` would prove scripts/yaml.py.
        if basename_unique and (norm == base or norm.endswith("/" + base) or rel_path.endswith("/" + norm)):
            return frag
    return None


def build_rows(root: Path) -> list[ExecRow]:
    health_rows = primitive_scope_health.build_rows(root)
    base_counts = Counter(Path(r.path).name for r in health_rows)

    cache: dict[str, tuple[str, set[str] | None, set[str], list[str]]] = {}

    def analyze(test_rel: str) -> tuple[str, set[str] | None, set[str], list[str]]:
        if test_rel in cache:
            return cache[test_rel]
        tpath = root / test_rel
        if not tpath.exists():
            result: tuple[str, set[str] | None, set[str], list[str]] = ("missing", None, set(), [])
        else:
            source = tpath.read_text(encoding="utf-8", errors="replace")
            parsed = _python_fragments(source) if tpath.suffix == ".py" else None
            if parsed is not None:
                result = ("python", parsed[0], parsed[1], [])
            else:
                result = ("shell", None, set(), _shell_exec_lines(source))
        cache[test_rel] = result
        return result

    rows: list[ExecRow] = []
    for hrow in health_rows:
        test_rel = hrow.paired_portability_test
        executable = Path(hrow.path).suffix.lower() in EXECUTABLE_SUFFIXES or Path(hrow.path).suffix == ""
        if not test_rel:
            rows.append(ExecRow(hrow.path, hrow.kind, hrow.scope, hrow.proof_level, None, "no-test", "no paired test"))
            continue
        mode, frags, imports, lines = analyze(test_rel)
        if mode == "missing":
            rows.append(ExecRow(hrow.path, hrow.kind, hrow.scope, hrow.proof_level, test_rel, "missing-test", "paired test not on disk"))
            continue
        unique = base_counts[Path(hrow.path).name] == 1
        hit: str | None = None
        evidence = ""
        if frags is not None:
            hit = _matches(frags, hrow.path, unique)
            if hit:
                evidence = f"ast-exec-arg:{hit}"
            else:
                # Import matching is FULL PATH only: `import yaml` (PyYAML) must
                # not be read as proof for scripts/yaml.py. Measured false
                # positive, fixed here — see the 2026-08-18 budget report.
                hit = _matches(imports, hrow.path, False)
                if hit:
                    evidence = f"static-import:{hit}"
        if hit is None and lines:
            base = Path(hrow.path).name
            for line in lines:
                if hrow.path in line or base in line:
                    hit, evidence = line.strip()[:120], f"shell-exec-line:{line.strip()[:80]}"
                    break
        if hit:
            rows.append(ExecRow(hrow.path, hrow.kind, hrow.scope, hrow.proof_level, test_rel, "executes", evidence))
        elif executable:
            rows.append(ExecRow(hrow.path, hrow.kind, hrow.scope, hrow.proof_level, test_rel, "not-executed", "no execution site references this artifact"))
        else:
            rows.append(ExecRow(hrow.path, hrow.kind, hrow.scope, hrow.proof_level, test_rel, "non-executable-artifact", "artifact cannot be executed; proof can only parse it"))
    return rows


def without_execution(rows: list[ExecRow]) -> list[ExecRow]:
    return [r for r in rows if r.execution_class != "executes"]


def budget_findings(root: Path, rows: list[ExecRow]) -> list[Finding]:
    policy = (_load_policy(root).get("proof_execution_budget") or {})
    findings: list[Finding] = []
    if not rows:
        findings.append(Finding("population", "block", "proof-execution-empty-population",
                                "registry scan produced zero rows; the audit cannot be green on an empty set"))
        return findings
    cap = policy.get("max_rows_without_execution")
    count = len(without_execution(rows))
    if cap is None:
        findings.append(Finding("budget", "review", "proof-execution-budget-missing",
                                "manifests/primitive-scope-classification.yaml has no proof_execution_budget.max_rows_without_execution"))
        return findings
    if count > int(cap):
        findings.append(Finding("rows_without_execution", "block", "proof-execution-budget-exceeded",
                                f"{count} registry rows have a proof that never executes the primitive, above budget {cap}"))
    return findings


def summarize(rows: list[ExecRow], findings: list[Finding]) -> dict[str, Any]:
    missing = without_execution(rows)
    by_test: Counter[str] = Counter()
    for row in missing:
        by_test[row.paired_portability_test or "(none)"] += 1
    return {
        "total": len(rows),
        "rows_without_execution": len(missing),
        "by_execution_class": dict(sorted(Counter(r.execution_class for r in rows).items())),
        "without_execution_by_scope": dict(sorted(Counter(r.scope for r in missing).items())),
        "without_execution_by_proof_level": dict(sorted(Counter(r.proof_level for r in missing).items())),
        "executes_by_evidence_kind": dict(sorted(Counter(
            r.evidence.split(":", 1)[0] for r in rows if r.execution_class == "executes").items())),
        "top_tests_without_execution": [{"test": t, "rows": n} for t, n in by_test.most_common(15)],
        "findings": len(findings),
        "findings_by_code": dict(sorted(Counter(f.code for f in findings).items())),
    }


def build_payload(root: Path) -> dict[str, Any]:
    rows = build_rows(root)
    findings = budget_findings(root, rows)
    return {
        "schema_version": "primitive-proof-execution-audit/v1",
        "summary": summarize(rows, findings),
        "rows": [asdict(r) for r in rows],
        "findings": [asdict(f) for f in findings],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit whether paired proofs execute their primitive.")
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true", help="print the full payload instead of the summary")
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--list", action="store_true", help="print the rows whose proof never executes them")
    parser.add_argument("--strict", action="store_true", help="exit 1 when there are findings")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.project_dir.resolve()
    payload = build_payload(root)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.list:
        for row in payload["rows"]:
            if row["execution_class"] != "executes":
                print(f"{row['execution_class']}\t{row['scope']}\t{row['path']}\t{row['paired_portability_test']}")
    elif args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload["summary"], sort_keys=True))
    if args.strict and payload["findings"]:
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # pragma: no cover - operator-facing error path
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)

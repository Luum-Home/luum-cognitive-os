#!/usr/bin/env python3
# SCOPE: both
"""Post-install self-check: does the install satisfy its own dependencies?

The Cognitive OS installer ships an allowlisted SUBSET of this repo into a
consumer project. Nothing verified that the subset was closed under its own
imports, and every consumer-side reference sits inside `try/except: pass`, so a
missing module produced no error at all — just a feature that silently never
ran. Three separate defects reached every install that way.

This module is the check that would have caught all three. It reads only the
INSTALLED tree (plus the source tree for classification) and fails loudly.

Checks
------
1. `cos_lib.*` closure — every `cos_lib.<mod>` referenced by a shipped entry
   point (`hooks/cos/*.sh`, `hooks/cos/_lib/*.py`, `bin/*.py`) must resolve to
   `.cognitive-os/cos_lib/<mod>.py` in the install.
2. Shell sibling dependencies — every `"$SCRIPT_DIR/<name>"` invocation in a
   shipped shell script must resolve to a file that also shipped.
3. Confidentiality config — `.cognitive-os/confidentiality.yaml` must exist and
   contain only keys the scanner actually reads.

Exit codes
----------
0  no findings
1  findings (install is incomplete)
2  usage / infrastructure error

Findings are classified so the operator knows which fix applies:

  missing_shipped   module exists in source and is consumer-scoped -> the
                    installer failed to ship it. Fix the installer.
  scope_conflict    module exists in source but is `SCOPE: os-only` -> a
                    consumer-scoped file depends on something that can never
                    ship. Fix the dependency, do not leak the module.
  dangling          module does not exist in source at all -> a dead import.
                    Remove the import; do not ship a stub.

Acknowledged exceptions live in `manifests/install-selfcheck-allowlist.yaml`
and REQUIRE a written reason. An empty allowlist is the correct default.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

try:  # optional; the parser degrades to a line reader without it
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

# Same three embedding forms lib_closure.py recognises. Kept inline so this
# checker is self-contained and can run from inside a consumer install where
# scripts/lib_closure.py is not projected.
_LIB_IMPORT_RE = re.compile(
    r"(?:from cos_lib\.|import cos_lib\.|-m cos_lib\.|python3 -m cos_lib\.)([A-Za-z0-9_]+)"
)

# `"$SCRIPT_DIR/name"` / `$SCRIPT_DIR/name` — a sibling-file dependency.
_SIBLING_RE = re.compile(r"\$(?:\{)?SCRIPT_DIR(?:\})?/([A-Za-z0-9_.-]+)")

# Keys cos_lib/confidentiality_scanner.py::load_protected_terms actually reads.
CONFIDENTIALITY_KEYS = {"project_names", "client_names", "repo_urls", "org_names"}


def _names_from_import(node: ast.AST) -> Set[str]:
    mods: Set[str] = set()
    if isinstance(node, ast.Import):
        for alias in node.names:
            parts = alias.name.split(".")
            if parts[0] == "cos_lib" and len(parts) > 1:
                mods.add(parts[1])
    elif isinstance(node, ast.ImportFrom) and node.module:
        parts = node.module.split(".")
        if parts[0] == "cos_lib" and len(parts) > 1:
            mods.add(parts[1])
    return mods


def _extract_ast(source: str) -> Set[str]:
    """Every cos_lib.* import anywhere in the file (module level or not)."""
    mods: Set[str] = set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return mods
    for node in ast.walk(tree):
        mods |= _names_from_import(node)
    return mods


def _extract_ast_import_time(source: str) -> Set[str]:
    """Only imports that run when the module is imported AND are unguarded.

    This is the precise property "this module can be imported at all":

      - imports nested in a function/class body are deferred, so they do not
        break import; they only break the code path that calls them.
      - imports inside `try:` are guarded — the author already declared the
        dependency optional.

    Everything else executes at import time and will raise if unsatisfied.
    Distinguishing these matters: without it, a correctly-deferred os-only
    import looks identical to the module-level one that actually killed the
    circuit breaker.
    """
    mods: Set[str] = set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return mods

    def walk(body: Iterable[ast.AST]) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue  # deferred
            if isinstance(node, ast.Try):
                continue  # guarded
            mods.update(_names_from_import(node))
            for attr in ("body", "orelse", "finalbody"):
                nested = getattr(node, attr, None)
                if isinstance(nested, list):
                    walk(nested)

    walk(tree.body)
    return mods


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def extract_lib_refs(path: Path, import_time_only: bool = False) -> Set[str]:
    """`cos_lib.<mod>` names referenced by one shipped entry point.

    `import_time_only` narrows Python files to unguarded module-level imports —
    used for already-projected `cos_lib/*.py` members, where the question is
    "does this module import?" rather than "what might it reach?".
    """
    text = _read(path)
    if path.suffix == ".py":
        if import_time_only:
            return _extract_ast_import_time(text)
        return set(_LIB_IMPORT_RE.findall(text)) | _extract_ast(text)
    return set(_LIB_IMPORT_RE.findall(text))


def shipped_entry_points(install_root: Path) -> List[Path]:
    """Every shipped file that can import `cos_lib.*` at runtime."""
    cos = install_root / ".cognitive-os"
    found: List[Path] = []
    for pattern in (
        "hooks/cos/*.sh",
        "hooks/cos/_lib/*.py",
        "hooks/cos/_lib/*.sh",
        "bin/*.py",
        "scripts/cos/*.py",
        # A projected cos_lib module must itself be importable. Without this,
        # a shipped module whose own top-level import is missing (or is
        # os-only) still fails at runtime — which is exactly how
        # record_completion -> learning_pipeline kept the circuit breaker dead
        # even once record_completion was being shipped.
        "cos_lib/*.py",
    ):
        found.extend(sorted(p for p in cos.glob(pattern) if p.is_file()))
    return found


def _source_scope(path: Path) -> str:
    """Read the `# SCOPE:` tag from a source file header (default 'both')."""
    text = _read(path)
    for line in text.splitlines()[:20]:
        m = re.match(r"^#\s*SCOPE:\s*([a-z-]+)", line.strip())
        if m:
            return m.group(1)
    return "both"


def load_allowlist(source_root: Path) -> Dict[str, str]:
    """Acknowledged exceptions: {"<kind>:<name>": reason}. Reason required."""
    path = source_root / "manifests" / "install-selfcheck-allowlist.yaml"
    if not path.exists():
        return {}
    text = _read(path)
    raw: dict = {}
    if yaml is not None:
        try:
            raw = yaml.safe_load(text) or {}
        except Exception:  # noqa: BLE001
            return {}
    else:
        # Minimal fallback: `key: reason` pairs under `exceptions:`.
        in_block = False
        for line in text.splitlines():
            stripped = line.split("#", 1)[0].rstrip()
            if not stripped.strip():
                continue
            if stripped.rstrip(":") == "exceptions":
                in_block = True
                raw["exceptions"] = {}
                continue
            if in_block and stripped.startswith(" ") and ":" in stripped:
                k, v = stripped.strip().split(":", 1)
                raw["exceptions"][k.strip()] = v.strip().strip('"').strip("'")
    entries = raw.get("exceptions") or {}
    # An exception with no written reason is not an exception.
    return {k: v for k, v in entries.items() if isinstance(v, str) and v.strip()}


def check_lib_closure(
    install_root: Path, source_root: Path, allowlist: Dict[str, str]
) -> List[Tuple[str, str, str]]:
    """Returns [(kind, name, detail)] for every unsatisfied cos_lib import."""
    findings: List[Tuple[str, str, str]] = []
    installed_lib = install_root / ".cognitive-os" / "cos_lib"
    source_lib = source_root / "cos_lib"

    for entry in shipped_entry_points(install_root):
        rel_entry = entry.relative_to(install_root)
        # Already-projected cos_lib members are judged on importability only.
        import_time_only = entry.parent.name == "cos_lib"
        for mod in sorted(extract_lib_refs(entry, import_time_only=import_time_only)):
            if import_time_only and mod == entry.stem:
                continue  # self-reference
            if (installed_lib / f"{mod}.py").is_file():
                continue  # satisfied
            src_mod = source_lib / f"{mod}.py"
            if not src_mod.is_file():
                kind = "dangling"
                detail = f"cos_lib.{mod} does not exist in the source repo either"
            elif _source_scope(src_mod) == "os-only":
                kind = "scope_conflict"
                detail = f"cos_lib/{mod}.py is SCOPE: os-only and can never ship"
            else:
                kind = "missing_shipped"
                detail = f"cos_lib/{mod}.py exists in source but was not installed"
            if allowlist.get(f"{kind}:{mod}") or allowlist.get(f"module:{mod}"):
                continue
            findings.append((kind, f"cos_lib.{mod}", f"{rel_entry}: {detail}"))
    return findings


def check_shell_siblings(
    install_root: Path, allowlist: Dict[str, str]
) -> List[Tuple[str, str, str]]:
    """Every `$SCRIPT_DIR/<name>` in a shipped shell script must have shipped.

    This is the generic form of the `hook-timing-wrapper.sh` -> `cos-root`
    defect: the installer re-homed a script away from a sibling it needs.
    """
    findings: List[Tuple[str, str, str]] = []
    cos = install_root / ".cognitive-os"
    for script in sorted(cos.glob("hooks/cos/**/*.sh")):
        if not script.is_file():
            continue
        text = _read(script)
        for name in sorted(set(_SIBLING_RE.findall(text))):
            # Skip obvious non-file interpolations.
            if name in {"..", "."}:
                continue
            if (script.parent / name).exists():
                continue
            rel = script.relative_to(install_root)
            if allowlist.get(f"sibling:{name}"):
                continue
            findings.append(
                (
                    "missing_sibling",
                    name,
                    f"{rel}: references $SCRIPT_DIR/{name} but it did not ship",
                )
            )
    return findings


def check_confidentiality_config(install_root: Path) -> List[Tuple[str, str, str]]:
    """The scanner's config must exist and use keys the scanner reads."""
    findings: List[Tuple[str, str, str]] = []
    cfg = install_root / ".cognitive-os" / "confidentiality.yaml"
    if not cfg.is_file():
        findings.append(
            (
                "missing_config",
                "confidentiality.yaml",
                ".cognitive-os/confidentiality.yaml did not ship; the "
                "protected_term, repo_url and attribution_phrase detectors are dark",
            )
        )
        return findings

    text = _read(cfg)
    if yaml is not None:
        try:
            raw = yaml.safe_load(text) or {}
        except Exception as exc:  # noqa: BLE001
            findings.append(
                ("bad_config", "confidentiality.yaml", f"does not parse as YAML: {exc}")
            )
            return findings
    else:
        raw = {}
        for line in text.splitlines():
            stripped = line.split("#", 1)[0].rstrip()
            if stripped and not stripped.startswith(" ") and ":" in stripped:
                raw[stripped.split(":", 1)[0].strip()] = []

    unknown = sorted(set(raw) - CONFIDENTIALITY_KEYS)
    if unknown:
        findings.append(
            (
                "bad_config",
                "confidentiality.yaml",
                "contains keys the scanner never reads (they do nothing): "
                + ", ".join(unknown)
                + "; valid keys are "
                + ", ".join(sorted(CONFIDENTIALITY_KEYS)),
            )
        )
    return findings


_HOOK_SCRIPT_RE = re.compile(r"([^\s\"']*\.cognitive-os/hooks/cos/[A-Za-z0-9_./-]+\.sh)")


def _settings_files(install_root: Path) -> List[Path]:
    candidates = [
        install_root / ".claude" / "settings.json",
        install_root / ".codex" / "hooks.json",
    ]
    return [p for p in candidates if p.is_file()]


def _expand(path_str: str, install_root: Path) -> Path:
    """Resolve a hook command path with the vars the harness substitutes."""
    for var in (
        "${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$PWD}}",
        "$CLAUDE_PROJECT_DIR",
        "${CLAUDE_PROJECT_DIR}",
        "$COGNITIVE_OS_PROJECT_DIR",
        "${COGNITIVE_OS_PROJECT_DIR}",
        "$PWD",
    ):
        path_str = path_str.replace(var, str(install_root))
    return Path(path_str)


def check_registered_paths(install_root: Path) -> List[Tuple[str, str, str]]:
    """Every hook path REGISTERED in settings must exist after install.

    A registration pointing at a path that does not exist is a ghost: the
    harness runs it, the shell fails, and the failure is indistinguishable
    from a hook that chose not to act. This also catches origin-layout paths
    (`hooks/...`, `scripts/...`) leaking into a consumer whose real layout is
    `.cognitive-os/hooks/cos/...`.

    It additionally reports the same hook script registered more than once for
    the same event, which is how upgrades silently multiply a hook's cost:
    merge-settings.sh dedupes by EXACT command string, so a version that
    changes the command's shape (e.g. adding a wrapper prefix) appends a second
    registration instead of replacing the first.
    """
    findings: List[Tuple[str, str, str]] = []
    for settings_path in _settings_files(install_root):
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            findings.append(
                ("bad_settings", settings_path.name, f"does not parse: {exc}")
            )
            continue
        rel_settings = settings_path.relative_to(install_root)
        seen: Dict[Tuple[str, str], int] = {}
        for event, groups in (data.get("hooks") or {}).items():
            if not isinstance(groups, list):
                continue
            for group in groups:
                for hook in (group or {}).get("hooks", []) or []:
                    cmd = (hook or {}).get("command", "")
                    if not cmd:
                        continue
                    referenced = _HOOK_SCRIPT_RE.findall(cmd)
                    for raw in referenced:
                        resolved = _expand(raw, install_root)
                        if not resolved.exists():
                            findings.append(
                                (
                                    "ghost_registration",
                                    resolved.name,
                                    f"{rel_settings} [{event}] registers "
                                    f"{raw} but that file does not exist",
                                )
                            )
                    if referenced:
                        key = (event, Path(referenced[-1]).name)
                        seen[key] = seen.get(key, 0) + 1
        for (event, script), count in sorted(seen.items()):
            if count > 1:
                findings.append(
                    (
                        "duplicate_registration",
                        script,
                        f"{rel_settings}: registered {count}x for {event}; "
                        "each run costs the full hook a second time",
                    )
                )
    return findings


def run(install_root: Path, source_root: Path) -> Tuple[int, List[Tuple[str, str, str]]]:
    allowlist = load_allowlist(source_root)
    findings: List[Tuple[str, str, str]] = []
    findings += check_lib_closure(install_root, source_root, allowlist)
    findings += check_shell_siblings(install_root, allowlist)
    findings += check_confidentiality_config(install_root)
    findings += check_registered_paths(install_root)
    return (1 if findings else 0), findings


def format_report(findings: List[Tuple[str, str, str]]) -> str:
    if not findings:
        return "install self-check: OK — every shipped entry point resolves its imports."
    lines = [
        "",
        "=" * 72,
        "INSTALL SELF-CHECK FAILED — the install cannot satisfy its own imports.",
        "=" * 72,
        "",
    ]
    by_kind: Dict[str, List[Tuple[str, str]]] = {}
    for kind, name, detail in findings:
        by_kind.setdefault(kind, []).append((name, detail))
    guidance = {
        "missing_shipped": "Installer bug: ship these modules (extend the closure seed set).",
        "scope_conflict": "Dependency bug: a consumer-scoped file needs an os-only module.",
        "dangling": "Dead import: remove it. Do NOT ship a stub.",
        "missing_sibling": "Re-homing bug: script separated from a file it invokes.",
        "missing_config": "Template not shipped by the installer.",
        "bad_config": "Config schema does not match what the scanner parses.",
        "ghost_registration": "Registered hook path does not exist (layout mismatch).",
        "duplicate_registration": "Same hook registered twice for one event.",
        "bad_settings": "Harness settings file does not parse.",
    }
    for kind in sorted(by_kind):
        lines.append(f"[{kind}] {guidance.get(kind, '')}")
        for name, detail in sorted(by_kind[kind]):
            lines.append(f"    {name}")
            lines.append(f"        {detail}")
        lines.append("")
    lines.append(f"{len(findings)} finding(s).")
    lines.append(
        "Acknowledge a genuine exception (with a written reason) in "
        "manifests/install-selfcheck-allowlist.yaml."
    )
    lines.append("")
    return "\n".join(lines)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--install-root", required=True, help="Installed project root.")
    parser.add_argument("--source-root", required=True, help="Cognitive OS source root.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args(argv)

    install_root = Path(args.install_root).resolve()
    source_root = Path(args.source_root).resolve()
    if not (install_root / ".cognitive-os").is_dir():
        print(f"error: no .cognitive-os/ under {install_root}", file=sys.stderr)
        return 2

    code, findings = run(install_root, source_root)
    if args.json:
        print(
            json.dumps(
                [{"kind": k, "name": n, "detail": d} for k, n, d in findings],
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(format_report(findings), file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())

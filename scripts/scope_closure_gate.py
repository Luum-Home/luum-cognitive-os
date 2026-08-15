#!/usr/bin/env python3
# SCOPE: os-only
"""Scope closure gate — verifies what the consumer projection actually publishes.

WHY THIS EXISTS (2026-08-15)
----------------------------
`cos_lib/` is not projected by directory. It is projected by the transitive
import closure of the seed hooks listed in
`manifests/primitive-install-boundary.yaml`. `scope_allows()` is a *subtractive*
filter over that closure: it can veto, never select.

Consequence, measured: ~69 unmarked modules in `cos_lib/` never reach a consumer
— not because a scope control stops them, but because no seed hook happens to
import them. That protection is an emergent property of the import graph. A
single new `import` in any allowlisted hook publishes any of them, and until
this gate existed nothing turned red.

The symmetric failure already happened and cost a control: `record_completion`
declares `SCOPE: both` and imports `learning_pipeline`, which is `os-only`, at
module level. In every consumer install that raises `ImportError`, and
`hooks/_lib/dispatch_gate_check.py` swallows it in an `except Exception` shared
with `CircuitBreaker` — so the agent circuit breaker has been dead in every
consumer, leaving only a string in an `error` field nobody reads.

DESIGN CONSTRAINT
-----------------
This gate calls the REAL `compute_closure()` from `scripts/lib_closure.py` and
mirrors the REAL marker parser from `scripts/cos_init.py:scope_allows()`,
including its two sharp edges (first-3-lines-only, uppercase-`SCOPE:`-only). It
deliberately does not model the projection itself. A gate with its own model of
the thing it guards proves the wrong property — the same defect as the 206
portability tests that `sys.path.insert(0, REPO_ROOT)` and therefore verify
independence from the working directory rather than survival of projection.

FINDING CLASSES
---------------
scope_conflict     A published file imports a module marked `os-only`. Ships
                   broken. This is the class that killed the circuit breaker.
unmarked_published A module the closure publishes carries no marker at all. It
                   ships by the fail-open default, i.e. by accident.
os_only_published  A module marked `os-only` is in the closure anyway — the
                   filter is being bypassed on some path.
dangling_import    A shipped file imports a `cos_lib` module that is NOT in the
                   closure and is NOT os-only: nothing forbids shipping it, the
                   closure simply never proposed it, so the consumer receives
                   the importer without the import. Same failure as the circuit
                   breaker from a different cause — and the known cause is
                   scripts/lib_closure.py:92-96, whose ImportFrom branch drops
                   `from cos_lib import x` entirely (it requires a dotted module
                   and never reads node.names).
marker_invisible   A marker exists but the real parser cannot see it: lowercase
                   `# scope:`, or placed past line 3. Silently fail-open, and a
                   trap the day someone writes `# scope: os-only` in lowercase.

RATCHET
-------
Baseline lives in `manifests/scope-closure-baseline.yaml`, one count per class.
The gate fails when a count EXCEEDS its baseline. It also fails when a count is
BELOW its baseline: a baseline above reality is a cushion that silently accepts
new debt while reporting "0 new", which is the failure mode this repo has
already shipped elsewhere. Fixing findings therefore requires lowering the
baseline in the same change — the ratchet only descends.

Exit codes: 0 clean · 1 findings (over or under baseline) · 2 error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Set

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

BOUNDARY_MANIFEST = REPO_ROOT / "manifests" / "primitive-install-boundary.yaml"
BASELINE_FILE = REPO_ROOT / "manifests" / "scope-closure-baseline.yaml"

FINDING_CLASSES = (
    "scope_conflict",
    "unmarked_published",
    "os_only_published",
    "marker_invisible",
    "dangling_import",
)

# Mirrors scripts/cos_init.py:284 exactly — uppercase only, whitespace required.
_REAL_MARKER_RE = re.compile(r"(?:# SCOPE:|<!-- SCOPE:)\s+([a-zA-Z_/-]+)")
# Deliberately looser: finds markers the real parser would miss.
_LOOSE_MARKER_RE = re.compile(r"(?:#\s*scope\s*:|<!--\s*scope\s*:)\s*([a-zA-Z_/-]+)", re.IGNORECASE)
# `[ \t]*`, never `\s*`: `\s` matches newlines, so a module-level import preceded
# by a blank line would capture "\n" as its indent and be misread as deferred —
# which would have reported the one defect this gate exists to catch as benign.
_IMPORT_RE = re.compile(r"^([ \t]*)(?:from|import)\s+cos_lib\.([a-z_0-9]+)", re.M)
# `from cos_lib import x, y` binds modules just as `import cos_lib.x` does, and
# missing it undercounts the closure. scripts/lib_closure.py:92-96 has this exact
# blind spot — its ImportFrom branch requires a dotted module and never inspects
# node.names — so this gate would inherit the undercount from the very function
# it calls if it only mirrored that shape.
_FROM_PKG_RE = re.compile(r"^([ \t]*)from\s+cos_lib\s+import\s+([^\n#]+)", re.M)


@dataclass
class Finding:
    kind: str
    subject: str
    detail: str

    def as_dict(self) -> dict:
        return {"kind": self.kind, "subject": self.subject, "detail": self.detail}


@dataclass
class Report:
    profile: str
    seed_hooks: int
    closure_size: int
    findings: List[Finding] = field(default_factory=list)

    def counts(self) -> Dict[str, int]:
        return {k: sum(1 for f in self.findings if f.kind == k) for k in FINDING_CLASSES}


def _read_head(path: Path, n: int = 3) -> List[str]:
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            return [fh.readline() for _ in range(n)]
    except OSError:
        return []


def real_marker(path: Path) -> str:
    """The marker the installer actually sees. '' means fail-open."""
    for line in _read_head(path, 3):
        m = _REAL_MARKER_RE.search(line)
        if m:
            return m.group(1).strip()
    return ""


def invisible_marker(path: Path) -> str:
    """A marker a human would call present but the installer cannot see."""
    if real_marker(path):
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    for lineno, line in enumerate(text.splitlines()[:40], start=1):
        m = _LOOSE_MARKER_RE.search(line)
        if m:
            why = "lowercase key" if lineno <= 3 else f"past line 3 (line {lineno})"
            return f"{m.group(1).strip()} — {why}"
    return ""


def imported_modules(path: Path) -> Dict[str, bool]:
    """Map `cos_lib` module -> True when imported at module level.

    The distinction is the whole difference between two failure modes. A
    module-level import of something that cannot ship raises `ImportError` the
    moment the file is loaded, taking the whole caller with it. A deferred
    import inside a function fails only when that path runs — which reads as a
    feature that quietly does nothing, and is the harder of the two to notice.
    Both are reported; only the first is fatal on load.
    """
    out: Dict[str, bool] = {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for indent, mod in _IMPORT_RE.findall(text):
        module_level = indent == ""
        out[mod] = out.get(mod, False) or module_level
    for indent, names in _FROM_PKG_RE.findall(text):
        module_level = indent == ""
        for raw in names.replace("(", "").replace(")", "").split(","):
            name = raw.strip().split(" as ")[0].strip()
            if name and name != "*" and re.fullmatch(r"[a-z_0-9]+", name):
                out[name] = out.get(name, False) or module_level
    return out


def shipped_lib_helpers() -> List[Path]:
    """Files under `hooks/_lib/` — they ship, and their imports are unaudited.

    `cos_init.py` builds the closure seed from `hooks/*.sh` only, while
    `hooks/_lib/` is copied wholesale by an unfiltered `copytree`. Everything in
    there therefore reaches consumers without ever entering the closure, which
    is precisely how `dispatch_gate_check.py` came to import a module that could
    not ship. Seeding from them is not belt-and-braces: it is the difference
    between this gate seeing the known defect and reporting green on it.
    """
    lib_helpers = REPO_ROOT / "hooks" / "_lib"
    if not lib_helpers.is_dir():
        return []
    return sorted(p for p in lib_helpers.rglob("*") if p.is_file() and p.suffix in (".py", ".sh"))


def load_seed_hooks(profile: str) -> List[Path]:
    """Seed hooks for a profile, from the canonical boundary manifest."""
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(BOUNDARY_MANIFEST.read_text(encoding="utf-8")) or {}
        hooks = data.get("profiles", {}).get(profile, {}).get("primitives", {}).get("hooks", [])
    except ImportError:
        # Degraded parse: indented "- hooks/x.sh" entries under the profile.
        hooks, in_profile = [], False
        for line in BOUNDARY_MANIFEST.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if re.match(rf"^{re.escape(profile)}:\s*$", stripped):
                in_profile = True
                continue
            if in_profile and stripped.endswith(":") and not line.startswith((" ", "\t")):
                break
            if in_profile and stripped.startswith("- hooks/"):
                hooks.append(stripped[2:].strip())
    return [REPO_ROOT / h for h in hooks]


def analyse(profile: str) -> Report:
    from lib_closure import compute_closure  # real projection logic, not a copy

    seeds = [p for p in load_seed_hooks(profile) if p.is_file()] + shipped_lib_helpers()
    closure = compute_closure(seeds, REPO_ROOT)
    report = Report(profile=profile, seed_hooks=len(seeds), closure_size=len(closure))

    lib_dir = REPO_ROOT / "cos_lib"
    marker_of: Dict[str, str] = {}
    for mod in closure:
        p = lib_dir / f"{mod}.py"
        marker_of[mod] = real_marker(p) if p.is_file() else ""

    for mod, entry in sorted(closure.items()):
        path = Path(entry.source_real_path)
        if not path.is_absolute():
            path = REPO_ROOT / path
        rel = f"cos_lib/{mod}.py"
        marker = marker_of.get(mod, "")

        if marker == "os-only":
            report.findings.append(
                Finding("os_only_published", rel, "marked os-only yet present in the closure")
            )
        elif not marker:
            hidden = invisible_marker(path) if path.is_file() else ""
            if hidden:
                report.findings.append(Finding("marker_invisible", rel, hidden))
            else:
                report.findings.append(
                    Finding("unmarked_published", rel, "no marker — ships via the fail-open default")
                )

        if path.is_file():
            for dep, module_level in sorted(imported_modules(path).items()):
                if dep == mod:
                    continue  # self-reference (re-export / __main__ guard), not a conflict
                dep_path = lib_dir / f"{dep}.py"
                if dep_path.is_file() and dep not in closure and real_marker(dep_path) != "os-only":
                    how = "module-level" if module_level else "deferred"
                    report.findings.append(
                        Finding(
                            "dangling_import",
                            rel,
                            f"imports cos_lib.{dep}, which the closure never proposes ({how})",
                        )
                    )
                if dep_path.is_file() and real_marker(dep_path) == "os-only":
                    how = (
                        "module-level — ImportError on load"
                        if module_level
                        else "deferred — silently disabled feature"
                    )
                    report.findings.append(
                        Finding("scope_conflict", rel, f"imports cos_lib.{dep} (os-only), {how}")
                    )

    # Seed hooks themselves ship; their direct os-only imports break the same way.
    for hook in seeds:
        for dep, module_level in sorted(imported_modules(hook).items()):
            dep_path = lib_dir / f"{dep}.py"
            if dep_path.is_file() and real_marker(dep_path) == "os-only":
                how = (
                    "module-level — ImportError on load"
                    if module_level
                    else "deferred — silently disabled feature"
                )
                report.findings.append(
                    Finding(
                        "scope_conflict",
                        str(hook.relative_to(REPO_ROOT)),
                        f"imports cos_lib.{dep} (os-only), {how}",
                    )
                )
    return report


def load_baseline() -> Dict[str, int]:
    if not BASELINE_FILE.is_file():
        return {}
    text = BASELINE_FILE.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
    except ImportError:
        data = {}
        for line in text.splitlines():
            m = re.match(r"^\s*([a-z_]+):\s*(\d+)\s*$", line)
            if m:
                data[m.group(1)] = int(m.group(2))
    return {k: int(v) for k, v in data.items() if k in FINDING_CLASSES}


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--profile", default="default", help="boundary profile (default|full)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument(
        "--write-baseline",
        action="store_true",
        help="write the CURRENT counts as the baseline (ratchet down only)",
    )
    args = ap.parse_args(list(argv) if argv is not None else None)

    try:
        report = analyse(args.profile)
    except Exception as exc:  # noqa: BLE001 — a crashed gate must not read as green
        print(f"scope-closure-gate: ERROR: {exc}", file=sys.stderr)
        return 2

    counts = report.counts()
    baseline = load_baseline()

    if args.write_baseline:
        body = [
            "# Scope closure gate baseline — ratchet DESCENDS only.",
            "# Regenerate with: python3 scripts/scope_closure_gate.py --write-baseline",
            "# Raising any number here is not a fix. Lower it as findings are resolved.",
            f"# Written from profile: {args.profile}",
            "",
        ]
        body += [f"{k}: {counts[k]}" for k in FINDING_CLASSES]
        BASELINE_FILE.write_text("\n".join(body) + "\n", encoding="utf-8")
        print(f"scope-closure-gate: baseline written to {BASELINE_FILE.relative_to(REPO_ROOT)}")
        return 0

    if args.json:
        print(
            json.dumps(
                {
                    "profile": report.profile,
                    "seed_hooks": report.seed_hooks,
                    "closure_size": report.closure_size,
                    "counts": counts,
                    "baseline": baseline,
                    "findings": [f.as_dict() for f in report.findings],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(f"scope-closure-gate · profile={report.profile} · seeds={report.seed_hooks} · closure={report.closure_size}")
        for kind in FINDING_CLASSES:
            hits = [f for f in report.findings if f.kind == kind]
            base = baseline.get(kind)
            mark = "" if base is None else f"  (baseline {base})"
            print(f"\n{kind}: {len(hits)}{mark}")
            for f in hits:
                print(f"    {f.subject}: {f.detail}")

    if not baseline:
        print(
            "\nscope-closure-gate: no baseline yet — run --write-baseline to pin today's counts.",
            file=sys.stderr,
        )
        return 1 if report.findings else 0

    # `.get(k, 0)` on both sides: a finding class added after the baseline was
    # written must read as new debt, not crash the gate. A gate that raises is
    # indistinguishable from a gate that is broken, and both stop guarding.
    over = {k: (counts[k], baseline.get(k, 0)) for k in FINDING_CLASSES if counts[k] > baseline.get(k, 0)}
    under = {k: (counts[k], baseline.get(k, 0)) for k in FINDING_CLASSES if counts[k] < baseline.get(k, 0)}

    if over:
        print("\nFAIL — new scope debt:", file=sys.stderr)
        for k, (now, base) in over.items():
            print(f"  {k}: {now} > baseline {base}", file=sys.stderr)
    if under:
        print("\nFAIL — baseline is above reality (a cushion that accepts silent debt):", file=sys.stderr)
        for k, (now, base) in under.items():
            print(f"  {k}: {now} < baseline {base} — lower it: --write-baseline", file=sys.stderr)

    return 1 if (over or under) else 0


if __name__ == "__main__":
    raise SystemExit(main())

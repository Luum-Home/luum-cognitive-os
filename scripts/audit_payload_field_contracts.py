#!/usr/bin/env python3
"""Audit hook reads of harness-owned payload fields for blind defaults.

A hook that reads a payload field with a *permissive* default — a value that is
also a legal reading, like ``0``, ``"0"``, ``true`` or ``false`` — cannot tell
"the harness said everything is fine" from "the field is not there".  When the
harness renames or moves the field, the hook silently degrades into a no-op and
keeps reporting green.  This is the family of ``.exit_code // "0"``
(error-pipeline / error-learning), ``.ok // true`` (claim-validator) and
``.cb_blocked // false`` (dispatch-gate).

Two halves:

* ``--lint`` (default): static scan of every registered hook for payload reads
  and classification of their defaults.
* ``--canary``: compares the payload fields hooks depend on against the fields
  the harness actually sent.  Fires when the harness moves a field, before the
  hook silently rots.

The canary reads payloads from one of three sources, in this order of
determinism:

1. the in-repo corpus (default) — ``tests/fixtures/payload-corpus/``, redacted
   keys-and-types captured by ``scripts/capture_payload_corpus.py``.  Same
   answer on every machine, so this is the source a test can gate on.
2. ``--live`` — this machine's harness transcripts, auto-detected.  Answers the
   question the corpus cannot: *did the harness change since we captured?*
3. ``--transcripts <dir>`` — an explicit directory of transcripts.

Read-only.  Deterministic.  Restores nothing because it changes nothing.

Exit codes: 0 = no blind reads / no drift, 1 = findings, 2 = error.

Usage:
    scripts/audit_payload_field_contracts.py
    scripts/audit_payload_field_contracts.py --json
    scripts/audit_payload_field_contracts.py --canary
    scripts/audit_payload_field_contracts.py --canary --live
    scripts/audit_payload_field_contracts.py --canary --transcripts <dir>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ── Payload ownership ────────────────────────────────────────────────────────
# Top-level keys the *harness* owns.  Everything else in a jq expression is
# either OS-owned state (a file the OS itself writes) or a derived value, and is
# out of scope: the OS can change its own schema and its own readers together.
HARNESS_OWNED_ROOTS = {
    "tool_name",
    "tool_input",
    "tool_response",
    "tool_result",
    "tool_use_id",
    "session_id",
    "transcript_path",
    "cwd",
    "hook_event_name",
    "prompt",
    "stop_hook_active",
    "exit_code",  # historically read at top level; see report 2026-08-15
    "permission_mode",
}

# A default is PERMISSIVE when it is itself a legal reading of the field, so the
# consumer cannot distinguish absence from that reading.  INERT defaults (empty
# string, null) force the consumer to branch on emptiness, which is safe.
INERT_DEFAULTS = {"", "empty", "null"}
PERMISSIVE_LITERALS = {
    "0", "1", "true", "false", "ok", "pass", "passed", "none", "unknown",
    "noop", "sonnet", "opus", "haiku", "info", "INFO", "success",
}

# Field-name shapes whose value is a *verdict*: absence read as a verdict is the
# dangerous case, because a wrong verdict propagates as a decision.
VERDICT_FIELD_RE = re.compile(
    r"(exit_code|is_error|error|ok|success|status|blocked|failed|failure"
    r"|passed|valid|allowed|denied|triggered|result)$",
    re.IGNORECASE,
)

# ── Extraction patterns ──────────────────────────────────────────────────────
# jq -r '.some.path // <default>'  (quote style either way)
JQ_READ_RE = re.compile(
    r"""jq\s+(?:-[a-zA-Z]+\s+)*(?:'(?P<sq>[^']*)'|"(?P<dq>[^"]*)")"""
)
ALT_RE = re.compile(
    r"""(?P<path>\.[A-Za-z_][A-Za-z0-9_.\[\]]*)\s*//\s*"""
    r"""(?P<def>"[^"]*"|'[^']*'|[A-Za-z0-9_.]+)"""
)
# stdin_field '.path' 'default'  /  hook_get_field '.path' 'default'
HELPER_RE = re.compile(
    r"""(?P<fn>stdin_field|hook_get_field)\s+(?P<q1>['"])(?P<path>\.[^'"]+)(?P=q1)"""
    r"""(?:\s+(?P<q2>['"])(?P<def>[^'"]*)(?P=q2))?"""
)

# The jq input has to be the payload, not an OS-owned file.  These are the
# variables that carry harness stdin across the hook corpus.
PAYLOAD_VARS = ("$INPUT", "$_STDIN_JSON", "$HOOK_RAW_INPUT", "$RAW_INPUT", "$PAYLOAD")


def _hook_files() -> list[Path]:
    """Every hook script, symlinks resolved, deduplicated by real path."""
    seen: dict[Path, Path] = {}
    globs = [
        ROOT / "hooks",
        *(ROOT / "packages").glob("*/hooks"),
    ]
    for d in globs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.sh")):
            if "_archived" in f.parts:
                continue
            real = f.resolve()
            seen.setdefault(real, f)
    return sorted(seen.values(), key=lambda p: str(p))


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return p.name


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def _root_of(path: str) -> str:
    return path.lstrip(".").split(".")[0].split("[")[0]


def _classify(path: str, default: str) -> str:
    """BLIND / GUARDED / INERT."""
    if default in INERT_DEFAULTS:
        return "INERT"
    if default in PERMISSIVE_LITERALS:
        return "BLIND" if VERDICT_FIELD_RE.search(path) else "GUARDED"
    return "GUARDED"


def scan() -> list[dict]:
    findings: list[dict] = []
    for f in _hook_files():
        try:
            lines = f.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for lineno, line in enumerate(lines, 1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue

            # jq reads — only when the input is the harness payload
            if "jq" in line and any(v in line for v in PAYLOAD_VARS):
                for m in JQ_READ_RE.finditer(line):
                    expr = m.group("sq") if m.group("sq") is not None else m.group("dq")
                    for a in ALT_RE.finditer(expr or ""):
                        path = a.group("path")
                        if _root_of(path) not in HARNESS_OWNED_ROOTS:
                            continue
                        default = _strip_quotes(a.group("def"))
                        findings.append(
                            {
                                "file": _rel(f),
                                "line": lineno,
                                "field": path,
                                "default": default,
                                "form": "jq",
                                "verdict": _classify(path, default),
                            }
                        )

            # helper reads — stdin is implicit, so no payload-var check
            for h in HELPER_RE.finditer(line):
                path = h.group("path")
                if _root_of(path) not in HARNESS_OWNED_ROOTS:
                    continue
                default = h.group("def")
                if default is None:
                    default = ""
                findings.append(
                    {
                        "file": _rel(f),
                        "line": lineno,
                        "field": path,
                        "default": default,
                        "form": h.group("fn"),
                        "verdict": _classify(path, default),
                    }
                )
    # deterministic order
    findings.sort(key=lambda r: (r["file"], r["line"], r["field"]))
    return findings


# ── Canary: do the fields hooks depend on exist in real payloads? ───────────
# The harness records each tool result in its transcript.  For Claude Code the
# transcript's `toolUseResult` is the same object delivered to hooks as
# `tool_response`, so the transcript is a payload capture the OS did not have to
# instrument for.
TRANSCRIPT_MAP = {
    "tool_response": "toolUseResult",
}

# In-repo corpus: transcript-shaped records with every value redacted, so the
# canary runs the same code path on fixtures as on live transcripts.
CORPUS_DIR = ROOT / "tests" / "fixtures" / "payload-corpus"

# A tool result reaches a hook in one of three states, all three observed in
# real transcripts.  Kept in sync with scripts/capture_payload_corpus.py by
# tests/audit/test_payload_field_contracts.py.
_EXIT_CODE_RE = re.compile(r"^Error: Exit code (\d+)")


def result_state(value: object) -> str:
    """Classify a tool result into the state a hook would have to handle."""
    if isinstance(value, str):
        if _EXIT_CODE_RE.match(value):
            return "error_w_code"
        if value.startswith("Error:"):
            return "error_no_code"
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _default_transcript_dir() -> Path | None:
    base = Path.home() / ".claude" / "projects"
    if not base.is_dir():
        return None
    slug = str(ROOT).replace("/", "-")
    cand = base / slug
    if cand.is_dir():
        return cand
    # the harness slugifies dots too
    alt = base / slug.replace(".", "-")
    return alt if alt.is_dir() else None


def observed_fields(tdir: Path) -> tuple[dict[str, set[str]], int]:
    """Field names observed per top-level payload area, plus rows scanned."""
    seen: dict[str, set[str]] = {"toolUseResult": set(), "_types": set(), "_states": set()}
    rows = 0
    for tf in sorted(tdir.glob("*.jsonl")):
        try:
            with tf.open(errors="replace") as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        rec = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    tur = rec.get("toolUseResult")
                    if tur is None:
                        continue
                    rows += 1
                    seen["_types"].add(type(tur).__name__)
                    seen["_states"].add(result_state(tur))
                    if isinstance(tur, dict):
                        seen["toolUseResult"].update(tur.keys())
        except OSError:
            continue
    return seen, rows


def canary(tdir: Path, findings: list[dict]) -> tuple[list[dict], int, dict]:
    seen, rows = observed_fields(tdir)
    missing: list[dict] = []
    for r in findings:
        parts = r["field"].lstrip(".").split(".")
        root = parts[0]
        if root == "exit_code" and len(parts) == 1:
            missing.append({**r, "reason": "no top-level exit_code in any payload"})
            continue
        if root in TRANSCRIPT_MAP and len(parts) > 1:
            area = TRANSCRIPT_MAP[root]
            leaf = parts[1].split("[")[0]
            if leaf not in seen.get(area, set()):
                missing.append(
                    {**r, "reason": f"{root}.{leaf} never observed in {rows} payloads"}
                )
    return missing, rows, {k: sorted(v) for k, v in seen.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--canary", action="store_true", help="check fields against real payloads")
    ap.add_argument("--transcripts", help="directory of harness transcripts")
    ap.add_argument(
        "--live",
        action="store_true",
        help="use this machine's transcripts instead of the in-repo corpus",
    )
    ap.add_argument("--all", action="store_true", help="show GUARDED/INERT rows too")
    args = ap.parse_args()

    try:
        findings = scan()
    except Exception as exc:  # pragma: no cover - defensive
        print(f"ERROR: scan failed: {exc}", file=sys.stderr)
        return 2

    blind = [r for r in findings if r["verdict"] == "BLIND"]

    canary_missing: list[dict] = []
    canary_rows = 0
    canary_schema: dict = {}
    source = "none"
    if args.canary:
        if args.transcripts:
            tdir = Path(args.transcripts)
            source = "transcripts"
        elif args.live:
            tdir = _default_transcript_dir()
            source = "live"
        else:
            tdir = CORPUS_DIR
            source = "corpus"
        if tdir is None or not tdir.is_dir():
            print("ERROR: no payload source found; pass --transcripts", file=sys.stderr)
            return 2
        canary_missing, canary_rows, canary_schema = canary(tdir, findings)

    if args.json:
        print(
            json.dumps(
                {
                    "total_payload_reads": len(findings),
                    "blind": blind,
                    "counts": {
                        v: sum(1 for r in findings if r["verdict"] == v)
                        for v in ("BLIND", "GUARDED", "INERT")
                    },
                    "rows": findings if args.all else blind,
                    "canary": {
                        "enabled": args.canary,
                        "source": source,
                        "payloads_scanned": canary_rows,
                        "observed": canary_schema,
                        "missing": canary_missing,
                    },
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(f"payload reads scanned: {len(findings)}")
        for v in ("BLIND", "GUARDED", "INERT"):
            print(f"  {v:<8} {sum(1 for r in findings if r['verdict'] == v)}")
        print()
        rows = findings if args.all else blind
        if not rows:
            print("no blind payload reads")
        else:
            print("BLIND — default is itself a legal reading; absence is unobservable")
            for r in rows:
                print(f"  {r['file']}:{r['line']}  {r['field']} // {r['default']!r}  [{r['verdict']}]")
        if args.canary:
            print()
            print(f"canary [{source}]: {canary_rows} payloads scanned")
            if canary_missing:
                print("FIELDS HOOKS DEPEND ON THAT NO PAYLOAD EVER CARRIED:")
                for r in canary_missing:
                    print(f"  {r['file']}:{r['line']}  {r['field']} — {r['reason']}")
            else:
                print("  every depended-on field observed at least once")

    return 1 if (blind or canary_missing) else 0


if __name__ == "__main__":
    sys.exit(main())

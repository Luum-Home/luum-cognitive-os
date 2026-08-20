#!/usr/bin/env python3
"""Hook payload fidelity: what the harness sends vs what the hooks read vs what the tests invent.

Three questions, three modes, one source of truth per question.

``--census``
    The measurement that decides the design.  Three sets per event:

    * ``SENT``  — top-level fields the harness really puts on a hook's stdin,
      reconstructed from this machine's transcripts (``--live``) or from the
      frozen envelope (default).
    * ``READ``  — top-level fields the repo's hooks actually read out of the
      payload, extracted statically from every hook script.
    * intersection, ``READ \\ SENT`` (phantom reads — a hook consuming a field
      nobody sends) and ``SENT \\ READ`` (surplus — fields no hook looks at).

``--capture``
    Rewrites ``tests/fixtures/hook-payload-envelope/envelope.json`` from this
    machine's transcripts.  The envelope carries **key sets and value kinds**,
    never operator values: no path, no username, no project name, no command
    text ever reaches the fixture.  See the fixture README.

``--gate``
    Scans the hook-exercising tests for hand-fabricated payload dicts and
    compares the set against ``manifests/hook-payload-fabrication-baseline.txt``
    with *exact equality* — a migrated file that stays listed fails just as
    loudly as a new offender that is not.

Why the transcript and not the documentation: a payload transcribed from docs
agrees with whoever transcribed it.  The transcript is what the harness wrote
down while it was running, and the hook payload is a documented projection of
exactly those fields (``session_id`` = ``sessionId``, ``cwd`` = ``cwd``,
``tool_name``/``tool_input`` = the assistant ``tool_use`` block, ``tool_response``
= the matching ``toolUseResult``).

Read-only in every mode except ``--capture``.  Deterministic per input set.
Exit codes: 0 = clean, 1 = findings, 2 = error.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENVELOPE_PATH = ROOT / "tests" / "fixtures" / "hook-payload-envelope" / "envelope.json"
BASELINE_PATH = ROOT / "manifests" / "hook-payload-fabrication-baseline.txt"
SETTINGS_PATH = ROOT / ".claude" / "settings.json"

# ── What counts as a harness-owned top-level field ───────────────────────────
# Union of: the three harness schema manifests, and the reconstruction below.
# Anything else a hook reads out of stdin is OS-owned state and out of scope.
HARNESS_ROOTS = {
    "session_id", "transcript_path", "cwd", "hook_event_name", "permission_mode",
    "tool_name", "tool_input", "tool_response", "tool_result", "tool_use_id",
    "prompt", "message", "stop_hook_active", "agent_id", "agent_type",
    "task_id", "task_subject", "source", "trigger", "custom_instructions",
    "exit_code", "reason", "matcher",
}

PAYLOAD_VARS = ("$INPUT", "$_STDIN_JSON", "$HOOK_RAW_INPUT", "$RAW_INPUT", "$PAYLOAD",
                "$STDIN_JSON", "$HOOK_INPUT", "$json_input", "$INPUT_JSON")

JQ_EXPR_RE = re.compile(r"""jq\s+(?:-[a-zA-Z-]+\s+)*(?:'(?P<sq>[^']*)'|"(?P<dq>[^"]*)")""")
HELPER_RE = re.compile(
    r"""(?:stdin_field|hook_get_field)\s+(['"])(?P<path>\.[^'"]+)\1"""
)
# A jq path expression, leading segment first.  Only the LEADING segment is a
# top-level payload field: in `.tool_input.prompt` the field is `tool_input`,
# and counting `prompt` too would invent a phantom read that no hook performs.
PATH_RE = re.compile(r"(?<![A-Za-z0-9_\]])\.(?P<root>[A-Za-z_][A-Za-z0-9_]*)")


# ─────────────────────────────────────────────────────────────────────────────
# READ: the fields the hooks pull out of the payload
# ─────────────────────────────────────────────────────────────────────────────
def hook_files() -> list[Path]:
    seen: dict[Path, Path] = {}
    for d in [ROOT / "hooks", *(ROOT / "packages").glob("*/hooks")]:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.sh")):
            if "_archived" in f.parts:
                continue
            seen.setdefault(f.resolve(), f)
    return sorted(seen.values(), key=str)


def hook_event_map() -> dict[str, set[str]]:
    """hook script basename -> set of events it is registered on."""
    out: dict[str, set[str]] = defaultdict(set)
    try:
        settings = json.loads(SETTINGS_PATH.read_text())
    except OSError:
        return out
    for event, matchers in (settings.get("hooks") or {}).items():
        for matcher in matchers:
            for h in matcher.get("hooks", []):
                cmd = h.get("command", "")
                for m in re.finditer(r"([A-Za-z0-9_.-]+\.sh)", cmd):
                    out[m.group(1)].add(event)
    return out


def reads_by_hook() -> dict[str, set[str]]:
    """hook path (repo-relative) -> harness-owned top-level fields it reads."""
    out: dict[str, set[str]] = {}
    for f in hook_files():
        try:
            text = f.read_text(errors="replace")
        except OSError:
            continue
        fields: set[str] = set()
        for line in text.splitlines():
            s = line.lstrip()
            if s.startswith("#"):
                continue
            if "jq" in line and any(v in line for v in PAYLOAD_VARS):
                for m in JQ_EXPR_RE.finditer(line):
                    expr = m.group("sq") if m.group("sq") is not None else m.group("dq")
                    for p in PATH_RE.finditer(expr or ""):
                        if p.group("root") in HARNESS_ROOTS:
                            fields.add(p.group("root"))
            for m in HELPER_RE.finditer(line):
                for p in PATH_RE.finditer(m.group("path")):
                    if p.group("root") in HARNESS_ROOTS:
                        fields.add(p.group("root"))
                    break
        if fields:
            rel = str(f.resolve().relative_to(ROOT)) if str(f.resolve()).startswith(str(ROOT)) else f.name
            out[rel] = fields
    return out


def read_sets_by_event() -> dict[str, set[str]]:
    ev_map = hook_event_map()
    per_hook = reads_by_hook()
    out: dict[str, set[str]] = defaultdict(set)
    for path, fields in per_hook.items():
        base = Path(path).name
        for event in ev_map.get(base, {"<unregistered>"}):
            out[event] |= fields
    return dict(out)


# ─────────────────────────────────────────────────────────────────────────────
# SENT: the fields the harness really puts on stdin
# ─────────────────────────────────────────────────────────────────────────────
def transcript_dir() -> Path | None:
    """This machine's transcript directory for THIS repo, or None."""
    base = Path.home() / ".claude" / "projects"
    if not base.is_dir():
        return None
    # The harness slugifies the project path by replacing every non-alphanumeric
    # run with a single dash, so a username with a dot in it lands as a dash.
    slug = re.sub(r"[^A-Za-z0-9]+", "-", str(ROOT))
    cand = base / slug
    return cand if cand.is_dir() else None


def _kind(value) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, str):
        return "str"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    return "null"


def live_envelope(limit_files: int = 6, limit_lines: int = 400000) -> dict:
    """Reconstruct per-event payload envelopes from this machine's transcripts.

    Values never leave this function: only key names, value kinds, and, for
    ``tool_input``, the per-tool key set (a key name is a schema fact; a key
    *value* is the operator's data).
    """
    d = transcript_dir()
    if d is None:
        raise SystemExit("no transcript directory for this repo on this machine")

    events: dict[str, dict[str, str]] = defaultdict(dict)
    tool_input_keys: dict[str, dict[str, str]] = defaultdict(dict)
    counts: dict[str, int] = defaultdict(int)
    files = sorted(d.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit_files]

    for f in files:
        pending: dict[str, dict] = {}
        seen_lines = 0
        with f.open(errors="replace") as fh:
            for line in fh:
                seen_lines += 1
                if seen_lines > limit_lines:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                typ = rec.get("type")

                if typ == "assistant":
                    msg = rec.get("message") or {}
                    for block in msg.get("content") or []:
                        if not isinstance(block, dict) or block.get("type") != "tool_use":
                            continue
                        tool = block.get("name", "")
                        tin = block.get("input") or {}
                        # PreToolUse payload projection
                        payload = {
                            "session_id": rec.get("sessionId"),
                            "transcript_path": str(f),
                            "cwd": rec.get("cwd"),
                            "permission_mode": rec.get("permissionMode"),
                            "hook_event_name": "PreToolUse",
                            "tool_name": tool,
                            "tool_input": tin,
                        }
                        for k, v in payload.items():
                            if v is None:
                                continue
                            events["PreToolUse"][k] = _kind(v)
                        counts["PreToolUse"] += 1
                        for k, v in (tin or {}).items():
                            tool_input_keys[tool][k] = _kind(v)
                        tuid = block.get("id")
                        if tuid:
                            pending[tuid] = {"tool": tool, "input": tin, "cwd": rec.get("cwd"),
                                             "sid": rec.get("sessionId")}

                elif typ == "user":
                    tur = rec.get("toolUseResult")
                    if tur is None:
                        # UserPromptSubmit projection
                        msg = rec.get("message") or {}
                        if isinstance(msg.get("content"), str):
                            payload = {
                                "session_id": rec.get("sessionId"),
                                "transcript_path": str(f),
                                "cwd": rec.get("cwd"),
                                "permission_mode": rec.get("permissionMode"),
                                "hook_event_name": "UserPromptSubmit",
                                "prompt": msg.get("content"),
                            }
                            for k, v in payload.items():
                                if v is None:
                                    continue
                                events["UserPromptSubmit"][k] = _kind(v)
                            counts["UserPromptSubmit"] += 1
                        continue
                    # PostToolUse projection
                    src = None
                    msg = rec.get("message") or {}
                    for block in msg.get("content") or []:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            src = pending.get(block.get("tool_use_id"))
                            break
                    payload = {
                        "session_id": rec.get("sessionId"),
                        "transcript_path": str(f),
                        "cwd": rec.get("cwd"),
                        "permission_mode": rec.get("permissionMode"),
                        "hook_event_name": "PostToolUse",
                        "tool_name": (src or {}).get("tool"),
                        "tool_input": (src or {}).get("input"),
                        "tool_response": tur,
                    }
                    for k, v in payload.items():
                        if v is None:
                            continue
                        events["PostToolUse"][k] = _kind(v)
                    counts["PostToolUse"] += 1

    return {
        "schema_version": 1,
        "source": "reconstructed from harness transcripts (values discarded, kinds kept)",
        "events": {k: dict(sorted(v.items())) for k, v in sorted(events.items())},
        "tool_input_keys": {k: dict(sorted(v.items())) for k, v in sorted(tool_input_keys.items())},
        "observed": dict(sorted(counts.items())),
    }


def load_envelope(live: bool = False) -> dict:
    if live:
        return live_envelope()
    try:
        return json.loads(ENVELOPE_PATH.read_text())
    except OSError as exc:  # pragma: no cover - operator error path
        raise SystemExit(f"envelope fixture missing: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# GATE: tests that fabricate their own payload
# ─────────────────────────────────────────────────────────────────────────────
# A dict literal is a fabricated payload when it carries a harness-owned root
# key that only ever appears on a hook payload.  `cwd` alone is not enough
# (subprocess kwargs use it); `tool_name`/`hook_event_name`/`tool_input` are.
FABRICATION_MARKERS = {"tool_name", "hook_event_name", "tool_input", "tool_response",
                       "transcript_path", "stop_hook_active"}
PRAGMA = "payload-synthetic:"


def gate_scan() -> tuple[set[str], dict[str, list[int]]]:
    """Return (offending files, {file: [line numbers]}).

    A file is exempt when the fabricating line, or the three lines above it,
    carries a ``# payload-synthetic: <reason>`` pragma — the escape hatch for
    the tests that must feed a hook something the harness would never send
    (malformed JSON, truncated payload, missing field).
    """
    offenders: dict[str, list[int]] = defaultdict(list)
    roots = [ROOT / "tests", *(ROOT / "packages").glob("*/tests")]
    seen: set[Path] = set()
    for r in roots:
        if not r.is_dir():
            continue
        for f in sorted(r.rglob("test_*.py")):
            real = f.resolve()
            if real in seen:
                continue
            seen.add(real)
            try:
                text = f.read_text(errors="replace")
            except OSError:
                continue
            if not any(m in text for m in FABRICATION_MARKERS):
                continue
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            lines = text.splitlines()
            for node in ast.walk(tree):
                if not isinstance(node, ast.Dict):
                    continue
                keys = {k.value for k in node.keys
                        if isinstance(k, ast.Constant) and isinstance(k.value, str)}
                if not (keys & FABRICATION_MARKERS):
                    continue
                lineno = node.lineno
                window = lines[max(0, lineno - 4):lineno]
                if any(PRAGMA in w for w in window):
                    continue
                rel = str(real.relative_to(ROOT)) if str(real).startswith(str(ROOT)) else str(real)
                offenders[rel].append(lineno)
    return set(offenders), dict(offenders)


def load_baseline() -> set[str]:
    if not BASELINE_PATH.exists():
        return set()
    return {
        ln.strip()
        for ln in BASELINE_PATH.read_text().splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    }


# ─────────────────────────────────────────────────────────────────────────────
def cmd_census(args) -> int:
    env = load_envelope(live=args.live)
    read = read_sets_by_event()
    all_reads: set[str] = set()
    for v in read.values():
        all_reads |= v

    out = {"source": "live" if args.live else "envelope", "events": {}}
    for event, sent_kinds in env["events"].items():
        sent = set(sent_kinds)
        r = read.get(event, set())
        out["events"][event] = {
            "sent": sorted(sent),
            "read": sorted(r),
            "intersection": sorted(sent & r),
            "read_not_sent": sorted(r - sent),
            "sent_not_read": sorted(sent - r),
            "observed": env.get("observed", {}).get(event, 0),
        }
    out["read_anywhere"] = sorted(all_reads)
    out["hooks_reading_payload"] = len(reads_by_hook())

    if args.json:
        print(json.dumps(out, indent=2, sort_keys=True))
    else:
        for event, d in sorted(out["events"].items()):
            print(f"── {event}  (payloads observed: {d['observed']})")
            print(f"   SENT ({len(d['sent'])}): {', '.join(d['sent'])}")
            print(f"   READ ({len(d['read'])}): {', '.join(d['read']) or '—'}")
            print(f"   ∩    ({len(d['intersection'])}): {', '.join(d['intersection']) or '—'}")
            print(f"   READ\\SENT (phantom, {len(d['read_not_sent'])}): {', '.join(d['read_not_sent']) or '—'}")
            print(f"   SENT\\READ (surplus, {len(d['sent_not_read'])}): {', '.join(d['sent_not_read']) or '—'}")
            print()
        print(f"hooks that read the payload at all: {out['hooks_reading_payload']}")
    return 0


def cmd_capture(args) -> int:
    env = live_envelope()
    blob = json.dumps(env, indent=2, sort_keys=True)
    # Privacy invariant, enforced here and re-checked by the fixture test:
    # a captured envelope must not carry an absolute path or a home directory.
    for needle in (str(Path.home()), str(ROOT), os.environ.get("USER", "\0")):
        if needle and needle in blob:
            print(f"REFUSING to write envelope: it contains {needle!r}", file=sys.stderr)
            return 2
    ENVELOPE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENVELOPE_PATH.write_text(blob + "\n")
    print(f"wrote {ENVELOPE_PATH.relative_to(ROOT)}: "
          f"{len(env['events'])} events, {len(env['tool_input_keys'])} tools, "
          f"{sum(env['observed'].values())} payloads observed")
    return 0


def cmd_gate(args) -> int:
    offenders, detail = gate_scan()
    baseline = load_baseline()
    new = sorted(offenders - baseline)
    stale = sorted(baseline - offenders)
    if args.json:
        print(json.dumps({"offenders": sorted(offenders), "new": new, "stale": stale,
                          "detail": {k: v for k, v in sorted(detail.items())}}, indent=2))
    else:
        print(f"files fabricating hook payloads: {len(offenders)} (baseline {len(baseline)})")
        for f in new:
            print(f"  NEW    {f}: lines {detail[f]}")
        for f in stale:
            print(f"  STALE  {f}: in baseline but no longer fabricates")
    return 1 if (new or stale) else 0


def cmd_write_baseline(args) -> int:
    offenders, _ = gate_scan()
    header = (
        "# Tests that build a hook payload by hand instead of asking\n"
        "# tests/utils/harness_payload.py for the shape the harness really sends.\n"
        "#\n"
        "# EXACT-EQUALITY baseline: audit_hook_payload_fidelity.py --gate fails on a\n"
        "# NEW entry and equally on a STALE one, so a migrated file must leave this\n"
        "# list in the same commit.  Do not add a line to silence a red gate; migrate\n"
        "# the test, or mark the payload `# payload-synthetic: <reason>` when the test\n"
        "# genuinely needs something the harness would never send.\n"
        "#\n"
        "# Regenerate: scripts/audit_hook_payload_fidelity.py --write-baseline\n"
    )
    BASELINE_PATH.write_text(header + "\n".join(sorted(offenders)) + "\n")
    print(f"wrote {BASELINE_PATH.relative_to(ROOT)}: {len(offenders)} files")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--census", action="store_true", help="sent vs read field census")
    ap.add_argument("--capture", action="store_true", help="rewrite the envelope fixture")
    ap.add_argument("--gate", action="store_true", help="fabricated-payload gate")
    ap.add_argument("--write-baseline", action="store_true")
    ap.add_argument("--live", action="store_true", help="census against this machine's transcripts")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        if args.capture:
            return cmd_capture(args)
        if args.write_baseline:
            return cmd_write_baseline(args)
        if args.gate:
            return cmd_gate(args)
        return cmd_census(args)
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

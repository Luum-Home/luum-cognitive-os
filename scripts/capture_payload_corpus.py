#!/usr/bin/env python3
"""Capture an anonymised corpus of harness tool-result payloads.

The payload canary in ``audit_payload_field_contracts.py`` answers one
question: *do the payload fields our hooks depend on actually exist in what the
harness sends?*  Answering it needs real payloads, and real payloads live in
harness transcripts — outside the repo, different on every machine.  A test
that reads them straight is non-deterministic and fails on someone else's
laptop.

This script freezes the *shape* of those payloads into a fixture the repo can
own: one representative record per (tool, result state, key shape), with every
scalar value replaced by a type token.  What the canary consumes is keys and
types; the values are exactly the part that must not be committed.

Anti-cheap-green note: the corpus is grouped by what the *harness emitted*
(every key of every ``toolUseResult``), never by what hooks read.  A corpus
derived from hook reads would validate by construction and catch nothing.

Read-only with respect to transcripts.  Deterministic: same transcripts in,
byte-identical corpus out.

Exit codes: 0 = corpus written, 1 = nothing captured, 2 = error.

Usage:
    scripts/capture_payload_corpus.py                 # this project's transcripts
    scripts/capture_payload_corpus.py --transcripts DIR [--transcripts DIR ...]
    scripts/capture_payload_corpus.py --stdout        # inspect without writing
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "tests" / "fixtures" / "payload-corpus" / "harness-payloads.jsonl"

# A key is kept verbatim only when it is a plain identifier.  Anything else
# (a path used as a key, a hostname, an id with punctuation) is replaced: keys
# are structure, but a key can smuggle a value.
SAFE_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
REDACTED_KEY = "<key>"
STR_TOKEN = "<str>"

# Result-state classification.  These three states were all observed in real
# transcripts and each one reaches hooks differently:
#   object        — the tool succeeded and the harness sent a structured result
#   error_w_code  — the command failed; the harness prefixed the exit code
#   error_no_code — a gate of this OS blocked the call; no exit code at all
EXIT_CODE_RE = re.compile(r"^Error: Exit code (\d+)")

MAX_LIST_SAMPLE = 2


def result_state(value: object) -> str:
    """Classify a ``toolUseResult`` into the state a hook would have to handle."""
    if isinstance(value, str):
        m = EXIT_CODE_RE.match(value)
        if m:
            return "error_w_code"
        if value.startswith("Error:"):
            return "error_no_code"
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def redact(value: object, *, top: bool = False) -> object:
    """Keep keys and types; drop every value.

    At the top level a string keeps just enough prefix to stay classifiable
    (``Error:`` / ``Error: Exit code N``) — that prefix is machine-readable
    shape, not content.
    """
    if isinstance(value, dict):
        return {
            (k if SAFE_KEY_RE.match(str(k)) else REDACTED_KEY): redact(v)
            for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))
        }
    if isinstance(value, list):
        return [redact(v) for v in value[:MAX_LIST_SAMPLE]]
    if isinstance(value, bool):
        return value  # a bool is shape, not content
    if isinstance(value, int):
        return 0
    if isinstance(value, float):
        return 0.0
    if value is None:
        return None
    if isinstance(value, str):
        if top:
            m = EXIT_CODE_RE.match(value)
            if m:
                return f"Error: Exit code {m.group(1)}\n{STR_TOKEN}"
            if value.startswith("Error:"):
                return f"Error: {STR_TOKEN}"
        return STR_TOKEN
    return STR_TOKEN


def shape(value: object, prefix: str = "") -> tuple:
    """Recursive key/type signature, used to keep one record per distinct shape."""
    if isinstance(value, dict):
        out: list = [("{}", prefix)]
        for k in sorted(value, key=str):
            key = k if SAFE_KEY_RE.match(str(k)) else REDACTED_KEY
            out.extend(shape(value[k], f"{prefix}.{key}"))
        return tuple(out)
    if isinstance(value, list):
        head = value[0] if value else None
        return (("[]", prefix), *shape(head, f"{prefix}[]"))
    return ((type(value).__name__, prefix),)


def default_transcript_dir() -> Path | None:
    base = Path.home() / ".claude" / "projects"
    if not base.is_dir():
        return None
    slug = str(ROOT).replace("/", "-")
    for cand in (base / slug, base / slug.replace(".", "-")):
        if cand.is_dir():
            return cand
    return None


def harvest(dirs: list[Path]) -> tuple[list[dict], int]:
    """One redacted record per (tool, state, shape).  Returns (records, scanned)."""
    keep: dict[tuple, dict] = {}
    scanned = 0
    for d in dirs:
        for tf in sorted(d.glob("*.jsonl")):
            names: dict[str, str] = {}
            try:
                fh = tf.open(errors="replace")
            except OSError:
                continue
            with fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        rec = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    msg = rec.get("message") or {}
                    content = msg.get("content")
                    if rec.get("type") == "assistant" and isinstance(content, list):
                        for b in content:
                            if isinstance(b, dict) and b.get("type") == "tool_use":
                                names[str(b.get("id"))] = str(b.get("name"))
                    tur = rec.get("toolUseResult")
                    if tur is None:
                        continue
                    scanned += 1
                    tool = "?"
                    if isinstance(content, list):
                        for b in content:
                            if isinstance(b, dict) and b.get("type") == "tool_result":
                                tool = names.get(str(b.get("tool_use_id")), "?")
                    state = result_state(tur)
                    key = (tool, state, shape(tur))
                    if key in keep:
                        keep[key]["_corpus"]["seen"] += 1
                        continue
                    keep[key] = {
                        "_corpus": {
                            "tool": tool,
                            "state": state,
                            "event": "PostToolUse",
                            "seen": 1,
                        },
                        "toolUseResult": redact(tur, top=True),
                    }
    records = sorted(
        keep.values(),
        key=lambda r: (
            r["_corpus"]["tool"],
            r["_corpus"]["state"],
            json.dumps(r["toolUseResult"], sort_keys=True),
        ),
    )
    return records, scanned


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--transcripts", action="append", help="transcript dir (repeatable)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--stdout", action="store_true", help="print instead of writing")
    args = ap.parse_args()

    if args.transcripts:
        dirs = [Path(p) for p in args.transcripts]
    else:
        d = default_transcript_dir()
        if d is None:
            print("ERROR: no transcript dir found; pass --transcripts", file=sys.stderr)
            return 2
        dirs = [d]
    for d in dirs:
        if not d.is_dir():
            print(f"ERROR: not a directory: {d.name}", file=sys.stderr)
            return 2

    records, scanned = harvest(dirs)
    if not records:
        print("ERROR: no toolUseResult payloads found", file=sys.stderr)
        return 1

    body = "".join(json.dumps(r, sort_keys=True) + "\n" for r in records)
    if args.stdout:
        sys.stdout.write(body)
    else:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body)
        print(f"wrote {len(records)} records from {scanned} payloads -> {out.name}")

    tools = sorted({r["_corpus"]["tool"] for r in records})
    states = sorted({r["_corpus"]["state"] for r in records})
    print(f"tools: {len(tools)}  states: {states}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

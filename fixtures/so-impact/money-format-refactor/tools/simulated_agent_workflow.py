#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path.cwd()
MODE = os.environ.get("COS_SO_IMPACT_MODE", "vanilla")
TRACE = Path(os.environ.get("COS_SO_IMPACT_TRACE", ROOT / "trace.jsonl"))
USAGE = Path(os.environ.get("COS_SO_IMPACT_USAGE", ROOT / "usage.json"))


def trace(event: dict) -> None:
    TRACE.parent.mkdir(parents=True, exist_ok=True)
    with TRACE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")


def write(path: str, body: str) -> None:
    (ROOT / path).write_text(body, encoding="utf-8")
    trace({"event": "tool_call", "tool": "write", "path": path, "phase": "implementation"})


if MODE == "vanilla":
    # Baseline does broader grep/read fan-out and leaves duplicated formatting in place.
    trace({"event": "tool_call", "tool": "grep", "phase": "discovery", "context_lines_read": 42, "relevant_files_found": 2})
    trace({"event": "tool_call", "tool": "read", "phase": "discovery", "context_lines_read": 24})
    write("src/catalog.py", 'def format_catalog_price(cents: int) -> str:\n    return f"${cents / 100:.2f}"\n')
    write("src/checkout.py", 'def format_checkout_price(cents: int) -> str:\n    return f"${cents / 100:.2f}"\n')
    trace({"event": "false_claim", "message": "claimed consolidation before shared module existed"})
    usage = {"real_usage_available": True, "total_tokens": 1200, "input_tokens": 900, "output_tokens": 300}
elif MODE in {"full-so", "full-so-minus-process-loop", "full-so-minus-graphify", "context-token-optimization-only", "graphify-only"}:
    # SO-like modes use targeted discovery and a shared module.
    trace({"event": "tool_call", "tool": "graph/query", "phase": "discovery", "context_lines_read": 16, "relevant_files_found": 2})
    write("src/money.py", 'def format_money(cents: int) -> str:\n    return f"${cents / 100:.2f}"\n')
    write("src/catalog.py", 'from src.money import format_money\n\n\ndef format_catalog_price(cents: int) -> str:\n    return format_money(cents)\n')
    write("src/checkout.py", 'from src.money import format_money\n\n\ndef format_checkout_price(cents: int) -> str:\n    return format_money(cents)\n')
    trace({"event": "quality_oracle", "score": "shared-module"})
    usage = {"real_usage_available": True, "total_tokens": 900, "input_tokens": 680, "output_tokens": 220}
else:
    # Other ablations are correct but do not improve discovery as strongly.
    trace({"event": "tool_call", "tool": "grep", "phase": "discovery", "context_lines_read": 30, "relevant_files_found": 2})
    write("src/money.py", 'def format_money(cents: int) -> str:\n    return f"${cents / 100:.2f}"\n')
    write("src/catalog.py", 'from src.money import format_money\n\n\ndef format_catalog_price(cents: int) -> str:\n    return format_money(cents)\n')
    write("src/checkout.py", 'from src.money import format_money\n\n\ndef format_checkout_price(cents: int) -> str:\n    return format_money(cents)\n')
    usage = {"real_usage_available": True, "total_tokens": 1040, "input_tokens": 790, "output_tokens": 250}

USAGE.parent.mkdir(parents=True, exist_ok=True)
USAGE.write_text(json.dumps(usage, indent=2, sort_keys=True) + "\n", encoding="utf-8")

#!/usr/bin/env python3
# SCOPE: os-only
"""Generate human-reviewed dispatch routing proposals for ADR-053."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.dispatch_optimizer import analyze, propose_routing, write_proposal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", default=".cognitive-os/metrics/llm-dispatch.jsonl")
    parser.add_argument("--output", default=".cognitive-os/routing/auto-tuned.yaml")
    parser.add_argument("--min-samples", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    proposals = propose_routing(analyze(Path(args.metrics), min_samples_per_tuple=args.min_samples))
    write_proposal(proposals, Path(args.output))
    print(json.dumps(proposals, indent=2, sort_keys=True) if args.json else f"wrote {args.output} ({len(proposals['proposals'])} proposals)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

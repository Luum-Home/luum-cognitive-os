#!/usr/bin/env python3
"""Process pending ADR-096 background review markers.

Markers live in .cognitive-os/runtime/review-pending-*.json and are created by
hooks/review-spawner.sh when review.async=true.  The sweeper is intentionally
small and idempotent: each marker is rewritten as completed/failed by
lib.review_agent.process_review_request().
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _project_dir(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    for env in ("COGNITIVE_OS_PROJECT_DIR", "CLAUDE_PROJECT_DIR", "CODEX_PROJECT_DIR"):
        value = os.environ.get(env)
        if value:
            return Path(value).resolve()
    return Path.cwd().resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Process pending review-agent markers")
    parser.add_argument("--project-dir", default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", action="store_true", help="emit JSON summary")
    args = parser.parse_args()

    project = _project_dir(args.project_dir)
    sys.path.insert(0, str(project))

    from lib.review_agent import process_review_request  # noqa: PLC0415

    runtime = project / ".cognitive-os" / "runtime"
    findings = project / ".cognitive-os" / "metrics" / "review-findings.jsonl"
    markers = sorted(runtime.glob("review-pending-*.json"))
    processed = []

    for marker in markers:
        if len(processed) >= max(0, args.limit):
            break
        try:
            payload = json.loads(marker.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("status") not in (None, "pending"):
            continue
        result = process_review_request(marker, findings_jsonl=findings)
        processed.append({"marker": str(marker), **result})

    summary = {"processed": len(processed), "results": processed}
    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print(f"review-pending-sweeper: processed={len(processed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

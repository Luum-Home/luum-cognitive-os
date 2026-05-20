#!/usr/bin/env python3
# SCOPE: os-only
"""Explain adaptive COS profile selection."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.adaptive_profile import resolve_profile  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd())
    parser.add_argument("--landing-intent", action="store_true")
    parser.add_argument("--override", choices=("lean", "standard", "strict"))
    parser.add_argument("--override-ttl-seconds", type=int, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = resolve_profile(
        Path(args.project_dir),
        landing_intent=args.landing_intent,
        override=args.override,
        override_ttl_seconds=args.override_ttl_seconds,
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"profile: {payload['profile']}")
        print("reasons:")
        for reason in payload["reasons"]:
            print(f"  - {reason}")
        guard_policy = payload.get("guard_policy") or {}
        print(f"blocking_posture: {guard_policy.get('blocking_posture', 'unknown')}")
        if payload.get("override"):
            print(f"override_scope: {payload.get('override_scope')}")
            if payload.get("override_expires_at") is not None:
                print(f"override_expires_at: {payload.get('override_expires_at')}")
        protections = guard_policy.get("minimum_protections") or []
        if protections:
            print("minimum protections:")
            for protection in protections:
                print(f"  - {protection.get('risk')}: {protection.get('hook')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

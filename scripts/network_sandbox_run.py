#!/usr/bin/env python3
# SCOPE: os-only
"""Run commands in a no-network sandbox when Docker is available.

This is a real egress boundary only in `docker-none` mode. Dry-run is provided
for CI/tests and does not claim isolation.
"""
from __future__ import annotations
import argparse, json, shutil, subprocess
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]

def docker_command(command: list[str], image: str, workdir: Path) -> list[str]:
    return ['docker','run','--rm','--network','none','--workdir','/workspace','-v',f'{workdir.resolve()}:/workspace:ro',image,*command]

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['docker-none'], default='docker-none')
    ap.add_argument('--image', default='python:3.12-slim')
    ap.add_argument('--workdir', default='.')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('command', nargs=argparse.REMAINDER)
    args=ap.parse_args()
    command=args.command[1:] if args.command[:1]==['--'] else args.command
    if not command:
        raise SystemExit('command required after --')
    cmd=docker_command(command, args.image, Path(args.workdir))
    payload={'schema_version':'network-sandbox-run.v1','mode':args.mode,'network':'none','command':cmd,'dry_run':args.dry_run}
    if args.dry_run:
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else ' '.join(cmd))
        return 0
    if not shutil.which('docker'):
        raise SystemExit('docker is required for real network sandbox mode')
    proc=subprocess.run(cmd, text=True, timeout=30)  # timeout per ADR-278 (default - review)
    return proc.returncode
if __name__=='__main__':
    raise SystemExit(main())

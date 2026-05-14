#!/usr/bin/env python3
# SCOPE: os-only
"""Detect active high-risk Cognitive OS env flags without reading secrets."""
from __future__ import annotations
import argparse, json, os
from pathlib import Path
import yaml

REPO=Path(__file__).resolve().parents[1]
MANIFEST=REPO/'manifests'/'runtime-env-flags.yaml'

def _truthy(value: str) -> bool:
    return value.lower() in {'1','true','yes','on'}

def detect(env: dict[str,str] | None=None, manifest: Path=MANIFEST) -> dict:
    env = dict(os.environ if env is None else env)
    data=yaml.safe_load(manifest.read_text())
    dangerous=[]
    for flag in data.get('flags',[]):
        name=flag['name']
        names=[]
        if name.endswith('*'):
            prefix=name[:-1]
            names=[k for k in env if k.startswith(prefix)]
        else:
            names=[name] if name in env else []
        for actual in sorted(names):
            value=env.get(actual,'')
            active=value not in {'','0','false','False','FALSE','no','off','unset'}
            if active and (flag.get('risk_level')=='high' or flag.get('bypasses_safety_primitive')):
                dangerous.append({'name':actual,'family':flag.get('family'),'risk_level':flag.get('risk_level'),'bypasses_safety_primitive':bool(flag.get('bypasses_safety_primitive'))})
    return {'schema_version':'dangerous-env-flags.v1','dangerous_flags':dangerous,'status':'warn' if dangerous else 'pass'}

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--fail-on-dangerous', action='store_true')
    args=ap.parse_args()
    result=detect()
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else f"dangerous-env-flags: status={result['status']} count={len(result['dangerous_flags'])}")
    return 2 if args.fail_on_dangerous and result['dangerous_flags'] else 0
if __name__=='__main__':
    raise SystemExit(main())

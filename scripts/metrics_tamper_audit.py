#!/usr/bin/env python3
# SCOPE: os-only
"""Detect malformed or suspicious metrics rows without reading secrets."""
from __future__ import annotations
import argparse, json
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]

def audit_file(path: Path) -> dict:
    malformed=[]; suspicious=[]; total=0
    if not path.exists():
        return {'path':str(path),'total':0,'malformed':[],'suspicious':[],'status':'missing'}
    for idx,line in enumerate(path.read_text(encoding='utf-8', errors='ignore').splitlines(), start=1):
        if not line.strip(): continue
        total+=1
        try: row=json.loads(line)
        except Exception:
            malformed.append(idx); continue
        provider=str(row.get('provider_used',''))
        if path.name=='llm-dispatch.jsonl':
            if provider and provider not in {'qwen','alibaba_qwen','qwen-code','claude','codex','offline_dispatch_smoke','unknown'}:
                suspicious.append({'line':idx,'reason':'unknown_provider','provider_used':provider})
            if provider in {'qwen','alibaba_qwen','qwen-code'} and row.get('provider_label')=='offline_dispatch_smoke':
                suspicious.append({'line':idx,'reason':'qwen_claim_with_offline_label'})
    return {'path':str(path),'total':total,'malformed':malformed,'suspicious':suspicious,'status':'fail' if malformed or suspicious else 'pass'}

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('path', nargs='?', default=str(REPO/'.cognitive-os/metrics/llm-dispatch.jsonl'))
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--fail-on-tamper', action='store_true')
    args=ap.parse_args()
    result=audit_file(Path(args.path))
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else f"metrics-tamper-audit: status={result['status']} malformed={len(result['malformed'])} suspicious={len(result['suspicious'])}")
    return 2 if args.fail_on_tamper and result['status']=='fail' else 0
if __name__=='__main__':
    raise SystemExit(main())

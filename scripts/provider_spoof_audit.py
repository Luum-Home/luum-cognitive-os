#!/usr/bin/env python3
# SCOPE: os-only
"""Detect provider proof rows that spoof live provider delegation."""
from __future__ import annotations
import argparse, json
from pathlib import Path

LIVE_PROVIDERS={'qwen','alibaba_qwen','qwen-code','claude','codex'}
OFFLINE_LABELS={'offline_dispatch_smoke','fixture','mock'}

def audit(path: Path) -> dict:
    issues=[]; total=0
    if not path.exists(): return {'schema_version':'provider-spoof-audit.v1','status':'missing','issues':[],'total':0}
    for idx,line in enumerate(path.read_text(encoding='utf-8', errors='ignore').splitlines(), start=1):
        if not line.strip(): continue
        total+=1
        try: row=json.loads(line)
        except Exception: continue
        provider=str(row.get('provider_used',''))
        label=str(row.get('provider_label',''))
        mode=str(row.get('mode',''))
        if provider in LIVE_PROVIDERS and (label in OFFLINE_LABELS or mode in OFFLINE_LABELS):
            issues.append({'line':idx,'provider_used':provider,'reason':'live_provider_claim_marked_offline'})
        if provider in {'qwen','alibaba_qwen','qwen-code'} and not any(k in row for k in ['dispatch_id','request_id','audit_id','credential_mode']):
            issues.append({'line':idx,'provider_used':provider,'reason':'live_provider_row_lacks_audit_identifier'})
    return {'schema_version':'provider-spoof-audit.v1','status':'fail' if issues else 'pass','issues':issues,'total':total}

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('path'); ap.add_argument('--json', action='store_true'); ap.add_argument('--fail-on-spoof', action='store_true'); args=ap.parse_args()
    result=audit(Path(args.path))
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else f"provider-spoof-audit: status={result['status']} issues={len(result['issues'])}")
    return 2 if args.fail_on_spoof and result['issues'] else 0
if __name__=='__main__': raise SystemExit(main())

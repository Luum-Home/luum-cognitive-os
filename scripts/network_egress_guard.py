#!/usr/bin/env python3
# SCOPE: os-only
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from urllib.parse import urlparse
import yaml

def analyze(command: str, policy_path: Path) -> dict:
    default={'allowed_domains':['localhost','127.0.0.1','::1'], 'provider_allowed_domains':[], 'exfil_indicators':['.env','secrets/','.git/config','--data','--data-binary','--upload-file','-X POST','-X PUT','-X PATCH','-X DELETE','API_KEY','TOKEN','PASSWORD','SECRET']}
    policy=yaml.safe_load(policy_path.read_text()) if policy_path.exists() else default
    urls=re.findall(r"https?://[^\s\"'<>]+", command)
    domains=[]
    for u in urls:
        try: domains.append(urlparse(u).hostname or '')
        except Exception: pass
    allowed=set(policy.get('allowed_domains',[])+policy.get('provider_allowed_domains',[]))
    external=[d for d in domains if d and d not in allowed and not d.endswith('.local')]
    indicators=[i for i in policy.get('exfil_indicators',[]) if i.lower() in command.lower()]
    network_cmd=bool(re.search(r'(^|[;&|\s])(curl|wget|nc|ncat|netcat|ssh|scp|rsync|ftp|sftp)\b', command))
    return {'block': bool(network_cmd and external and indicators), 'warn': bool(network_cmd and external and not indicators), 'external': external, 'indicators': indicators}

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--policy', required=True)
    ap.add_argument('--command', required=True)
    args=ap.parse_args()
    print(json.dumps(analyze(args.command, Path(args.policy)), separators=(',',':')))
    return 0
if __name__=='__main__':
    raise SystemExit(main())

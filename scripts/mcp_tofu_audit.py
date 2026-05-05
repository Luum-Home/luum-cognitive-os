#!/usr/bin/env python3
"""Audit MCP server definitions against trust-on-first-use pins.

Fingerprints include server name, command, args, env key names, and config path;
secret env values are never serialized or hashed.
"""
from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path
from typing import Any
import yaml

REPO=Path(__file__).resolve().parents[1]
SETTINGS=[Path('.claude/settings.json'),Path('.claude/settings.local.json'),Path('.codex/config.toml'),Path('.cursor/mcp.json'),Path('mcp.json')]
PIN_MANIFEST=REPO/'manifests'/'mcp-trust-pins.yaml'

def _json(path: Path) -> dict[str, Any]:
    try: return json.loads(path.read_text(encoding='utf-8'))
    except Exception: return {}

def _tool_description_hashes(cfg: dict[str, Any]) -> dict[str, str]:
    tools = cfg.get("tools", [])
    hashes: dict[str, str] = {}
    if not isinstance(tools, list):
        return hashes
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        name = str(tool.get("name", ""))
        if not name:
            continue
        description = str(tool.get("description", ""))
        hashes[name] = hashlib.sha256(description.encode("utf-8")).hexdigest()
    return dict(sorted(hashes.items()))


def discover(root: Path=REPO) -> list[dict[str, Any]]:
    found=[]
    for rel in SETTINGS:
        path=root/rel
        if not path.exists() or path.suffix.lower()!='.json':
            continue
        data=_json(path)
        servers=data.get('mcpServers') or data.get('mcp_servers') or {}
        if not isinstance(servers, dict):
            continue
        for name, cfg in servers.items():
            if not isinstance(cfg, dict):
                continue
            env=cfg.get('env') if isinstance(cfg.get('env'), dict) else {}
            rec={
                'name': str(name),
                'config_path': rel.as_posix(),
                'command': str(cfg.get('command','')),
                'args': [str(x) for x in cfg.get('args',[]) if x is not None],
                'env_keys': sorted(str(k) for k in env.keys()),
                'tool_description_hashes': _tool_description_hashes(cfg),
            }
            rec['fingerprint']=fingerprint(rec)
            found.append(rec)
    return found

def fingerprint(rec: dict[str, Any]) -> str:
    material={k:rec[k] for k in ['name','config_path','command','args','env_keys'] if k in rec}
    material["tool_description_hashes"] = rec.get("tool_description_hashes", {})
    return hashlib.sha256(json.dumps(material, sort_keys=True, separators=(',',':')).encode()).hexdigest()

def audit(root: Path=REPO, pins_path: Path=PIN_MANIFEST) -> dict[str, Any]:
    servers=discover(root)
    pins_data=yaml.safe_load(pins_path.read_text(encoding='utf-8')) if pins_path.exists() else {'pins':[]}
    pins={(p.get('name'),p.get('config_path')):p.get('fingerprint') for p in pins_data.get('pins',[])}
    unpinned=[]; mismatched=[]
    for s in servers:
        key=(s['name'],s['config_path'])
        expected=pins.get(key)
        if expected is None:
            unpinned.append({k:s[k] for k in ['name','config_path','command','args','env_keys','tool_description_hashes','fingerprint']})
        elif expected != s['fingerprint']:
            mismatched.append({'name':s['name'],'config_path':s['config_path'],'expected':expected,'actual':s['fingerprint']})
    return {'schema_version':'mcp-tofu-audit.v1','servers':servers,'unpinned':unpinned,'mismatched':mismatched,'status':'fail' if unpinned or mismatched else 'pass'}

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--fail-on-unpinned', action='store_true')
    args=ap.parse_args()
    result=audit()
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else f"mcp-tofu-audit: status={result['status']} servers={len(result['servers'])} unpinned={len(result['unpinned'])} mismatched={len(result['mismatched'])}")
    return 2 if args.fail_on_unpinned and result['status']=='fail' else 0
if __name__=='__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
# SCOPE: os-only
"""Audit and safely reap bounded Cognitive OS state surfaces."""
from __future__ import annotations

import argparse, fcntl, fnmatch, json, os, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
try:
    import yaml  # type: ignore[import]
except Exception:  # standalone projected script fallback
    class _MiniYaml:
        class YAMLError(Exception):
            pass
        @staticmethod
        def _scalar(value):
            value = str(value).strip()
            if value == "": return ""
            if value.lower() == "true": return True
            if value.lower() == "false": return False
            if value.isdigit(): return int(value)
            if value.startswith("[") and value.endswith("]"):
                inner = value[1:-1].strip()
                return [] if not inner else [x.strip().strip("\"'") for x in inner.split(",")]
            if value.startswith('"') and value.endswith('"'):
                return value[1:-1].replace("\\\\", "\\")
            if value.startswith("'") and value.endswith("'"):
                return value[1:-1]
            return value
        @classmethod
        def safe_load(cls, text):
            lines=[]
            for raw in str(text).splitlines():
                clean=raw.split('#',1)[0].rstrip()
                if not clean.strip():
                    continue
                indent=len(clean)-len(clean.lstrip(' ')); stripped=clean.strip()
                if ':' not in stripped and not stripped.startswith('- ') and lines:
                    pi, pt = lines[-1]; lines[-1] = (pi, pt + ' ' + stripped)
                else:
                    lines.append((indent, stripped))
            if not lines: return None
            root=[] if lines[0][1].startswith('- ') else {}
            stack=[(-1, root)]
            def parent_for(indent, seq=False):
                while stack and (stack[-1][0] > indent or (stack[-1][0] == indent and not seq)):
                    stack.pop()
                if seq:
                    while stack and stack[-1][0] == indent and not isinstance(stack[-1][1], list):
                        stack.pop()
                if not stack: raise cls.YAMLError('invalid indentation')
                return stack[-1][1]
            for idx,(indent,stripped) in enumerate(lines):
                parent=parent_for(indent, stripped.startswith('- '))
                next_is_list=idx+1 < len(lines) and lines[idx+1][0] >= indent and lines[idx+1][1].startswith('- ')
                if stripped.startswith('- '):
                    if not isinstance(parent, list): raise cls.YAMLError('list item under non-list parent')
                    item=stripped[2:].strip(); value={}
                    if ':' in item:
                        k,v=item.split(':',1); child=cls._scalar(v) if v.strip() else ([] if next_is_list else {})
                        value={k.strip(): child}; parent.append(value); stack.append((indent,value))
                        if isinstance(child,(dict,list)): stack.append((indent+1, child))
                    elif item:
                        parent.append(cls._scalar(item))
                    else:
                        parent.append(value); stack.append((indent,value))
                    continue
                if ':' not in stripped: continue
                k,v=stripped.split(':',1); value=cls._scalar(v) if v.strip() else ([] if next_is_list else {})
                if isinstance(parent, dict): parent[k.strip()]=value
                else: parent.append({k.strip(): value})
                if isinstance(value,(dict,list)): stack.append((indent,value))
            return root
    yaml = _MiniYaml()

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "manifests" / "state-retention.yaml"
REQUIRED = {"id","kind","path","max_age","max_count","reaper","retention_mode","tombstone","owner_pid","owner_files","documentation"}
TERMINAL = {"released","completed","completed-by-watermark","cancelled-zombie","cancelled-stale","stale"}

def duration(v: Any) -> int | None:
    if v in (None, "persistent"): return None
    t = str(v).strip().upper()
    if not t.startswith("P") or len(t) < 3: raise ValueError(f"invalid duration {v!r}")
    n, u = t[1:-1], t[-1]
    if not n.isdigit(): raise ValueError(f"invalid duration {v!r}")
    if u == "H": return int(n) * 3600
    if u == "D": return int(n) * 86400
    raise ValueError(f"invalid duration {v!r}")

def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def git(project: Path, args: Sequence[str], check: bool=False) -> subprocess.CompletedProcess[str]:
    r = subprocess.run(["git","-C",str(project),*args], text=True, capture_output=True, timeout=60)
    if check and r.returncode != 0: raise RuntimeError(r.stderr or r.stdout)
    return r

def load_manifest(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

def validate_manifest(data: dict[str, Any]) -> list[dict[str, Any]]:
    out=[]; seen=set(); surfaces=data.get("surfaces", [])
    if not isinstance(surfaces, list): return [{"level":"BLOCK","code":"manifest-surfaces-invalid","message":"surfaces must be a list"}]
    for i,s in enumerate(surfaces):
        if not isinstance(s, dict):
            out.append({"level":"BLOCK","code":"surface-invalid","surface":f"#{i}","message":"surface must be a mapping"}); continue
        sid=str(s.get("id") or f"#{i}")
        if sid in seen: out.append({"level":"BLOCK","code":"surface-duplicate-id","surface":sid,"message":"duplicate surface id"})
        seen.add(sid)
        missing=sorted(REQUIRED-set(s))
        if missing: out.append({"level":"BLOCK","code":"surface-missing-fields","surface":sid,"message":"missing fields: "+", ".join(missing)})
        try: duration(s.get("max_age"))
        except ValueError as e: out.append({"level":"BLOCK","code":"surface-invalid-max-age","surface":sid,"message":str(e)})
    return out

def stash_entries(project: Path) -> list[dict[str, Any]]:
    r=git(project,["stash","list","--format=%gd%x1f%ct%x1f%gs"])
    if r.returncode != 0: return []
    now=int(datetime.now(timezone.utc).timestamp()); entries=[]
    for line in r.stdout.splitlines():
        parts=line.split("\x1f")
        if len(parts)!=3: continue
        ref, raw_epoch, subject=parts
        try: epoch=int(raw_epoch)
        except ValueError: epoch=0
        sha=git(project,["rev-parse",ref]).stdout.strip()
        files=[x for x in git(project,["stash","show","--name-only",ref]).stdout.splitlines() if x.strip()]
        entries.append({"ref":ref,"epoch":epoch,"age_seconds":max(0,now-epoch),"subject":subject,"sha":sha,"files":files,"file_count":len(files)})
    return entries

def selected_stashes(project: Path, surface: dict[str, Any]) -> list[dict[str, Any]]:
    patterns=surface.get("selector",{}).get("subjects",[])
    return [e for e in stash_entries(project) if any(p in e["subject"] for p in patterns)]

def as_int(v: Any) -> int | None:
    try: return int(v)
    except (TypeError, ValueError): return None

def audit_stashes(project: Path, surface: dict[str, Any]) -> dict[str, Any]:
    max_age=duration(surface.get("max_age")); max_count=as_int(surface.get("max_count")); entries=selected_stashes(project,surface)
    stale=[e for e in entries if max_age is not None and e["age_seconds"]>max_age]
    findings=[]
    if stale: findings.append({"level":"BLOCK","code":"auto-stash-stale","count":len(stale)})
    if max_count is not None and len(entries)>max_count: findings.append({"level":"WARN","code":"auto-stash-count","count":len(entries),"max_count":max_count})
    return {"surface":surface["id"],"kind":surface["kind"],"count":len(entries),"stale_count":len(stale),"items":[{k:e[k] for k in ("ref","sha","age_seconds","subject","file_count")} for e in entries],"findings":findings}

def read_json(path: Path, fallback: Any) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return fallback

def row_ts(row: dict[str, Any]) -> str | None:
    for k in ("released_at","completed_at","stale_at","completedAt","updated_at"):
        if isinstance(row.get(k), str): return row[k]
    return None

def iso_age(value: str | None) -> int | None:
    if not value: return None
    try: dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError: return None
    return max(0,int((datetime.now(timezone.utc)-dt).total_seconds()))

def ledger_rows(data: dict[str, Any]) -> tuple[str|None, list[Any]]:
    if isinstance(data.get("claims"), list): return "claims", data["claims"]
    if isinstance(data.get("tasks"), list): return "tasks", data["tasks"]
    return None, []

def audit_json_ledger(project: Path, surface: dict[str, Any]) -> dict[str, Any]:
    path=project/surface["path"]; data=read_json(path,{}); _, rows=ledger_rows(data)
    statuses=set(surface.get("selector",{}).get("terminal_statuses", list(TERMINAL)))
    terminal=[r for r in rows if isinstance(r,dict) and r.get("status") in statuses]
    max_age=duration(surface.get("max_age")); max_count=as_int(surface.get("max_count")); old=[]
    if max_age is not None:
        old=[r for r in terminal if (iso_age(row_ts(r)) or 0)>max_age]
    findings=[]
    if old: findings.append({"level":"WARN","code":"terminal-ledger-aged","count":len(old)})
    if max_count is not None and len(rows)>max_count: findings.append({"level":"WARN","code":"ledger-count","count":len(rows),"max_count":max_count})
    return {"surface":surface["id"],"kind":surface["kind"],"path":str(path),"count":len(rows),"terminal_count":len(terminal),"old_terminal_count":len(old),"findings":findings}

def audit_glob(project: Path, surface: dict[str, Any]) -> dict[str, Any]:
    paths=sorted(project.glob(surface["path"])); max_count=as_int(surface.get("max_count")); findings=[]
    if max_count is not None and len(paths)>max_count: findings.append({"level":"WARN","code":"surface-count","count":len(paths),"max_count":max_count})
    return {"surface":surface["id"],"kind":surface["kind"],"path":surface["path"],"count":len(paths),"sample":[str(p.relative_to(project)) for p in paths[:10]],"findings":findings}

def audit_worktrees(project: Path, surface: dict[str, Any]) -> dict[str, Any]:
    r=git(project,["worktree","list","--porcelain"]); patterns=surface.get("selector",{}).get("branch_patterns",[]); branches=[]
    for line in r.stdout.splitlines():
        if line.startswith("branch "):
            b=line.split(" ",1)[1].removeprefix("refs/heads/")
            if any(fnmatch.fnmatch(b, f"{p}*") or b.startswith(p) for p in patterns): branches.append(b)
    return {"surface":surface["id"],"kind":surface["kind"],"count":len(branches),"branches":branches,"findings":[]}

def audit_surface(project: Path, surface: dict[str, Any]) -> dict[str, Any]:
    p=str(surface.get("path",""))
    if p=="git:refs/stash": return audit_stashes(project,surface)
    if p=="git:worktree": return audit_worktrees(project,surface)
    if p.endswith(".json"): return audit_json_ledger(project,surface)
    return audit_glob(project,surface)

def archive_stash(project: Path, entry: dict[str, Any], archive: Path, index: int, execute: bool) -> dict[str, Any]:
    ref_name=f"refs/cos-preserved-stash/{archive.name}-{index}"; patch=archive/f"stash-{index}.patch"; ns=archive/f"stash-{index}.name-status.txt"; meta=archive/f"stash-{index}.json"
    if execute:
        archive.mkdir(parents=True, exist_ok=True)
        ns.write_text(git(project,["stash","show","--name-status",entry["sha"]]).stdout, encoding="utf-8")
        patch.write_text(git(project,["stash","show","-p",entry["sha"]]).stdout, encoding="utf-8")
        meta.write_text(json.dumps({"ref":entry["ref"],"sha":entry["sha"],"subject":entry["subject"],"preserved_ref":ref_name,"files":entry["files"]}, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        git(project,["update-ref",ref_name,entry["sha"]],check=True)
    return {"sha":entry["sha"],"subject":entry["subject"],"preserved_ref":ref_name,"patch":str(patch.relative_to(project)),"name_status":str(ns.relative_to(project))}

def ref_by_sha(project: Path, sha: str) -> str | None:
    for e in stash_entries(project):
        if e["sha"]==sha: return e["ref"]
    return None

def reap_stashes(project: Path, surface: dict[str, Any], execute: bool) -> dict[str, Any]:
    max_age=duration(surface.get("max_age")); entries=[e for e in selected_stashes(project,surface) if max_age is not None and e["age_seconds"]>max_age]
    archive=project/".cognitive-os"/"recovery"/f"stashes-{stamp()}"; actions=[]
    for i,e in enumerate(entries):
        a=archive_stash(project,e,archive,i,execute); drop_ref=e["ref"]; dropped=False
        if execute:
            drop_ref=ref_by_sha(project,e["sha"]) or e["ref"]
            git(project,["stash","drop",drop_ref],check=True); dropped=True
        actions.append({"action":"drop-auto-stash","execute":execute,"original_ref":e["ref"],"drop_ref":drop_ref,"dropped":dropped,**a})
    return {"surface":surface["id"],"candidate_count":len(entries),"archive_dir":str(archive.relative_to(project)),"actions":actions}

def atomic_json(path: Path, data: Any) -> None:
    tmp=path.with_name(f".{path.name}.{os.getpid()}.tmp"); tmp.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8"); os.replace(tmp,path)

def compact_ledger(project: Path, surface: dict[str, Any], execute: bool) -> dict[str, Any]:
    path=project/surface["path"]; data=read_json(path,{}); key, rows=ledger_rows(data)
    if key is None: return {"surface":surface["id"],"removed":0,"execute":execute}
    statuses=set(surface.get("selector",{}).get("terminal_statuses", list(TERMINAL))); max_age=duration(surface.get("max_age")); max_count=as_int(surface.get("max_count"))
    kept=[]; removed=[]
    for r in rows:
        if not isinstance(r,dict) or r.get("status") not in statuses: kept.append(r); continue
        age=iso_age(row_ts(r))
        if max_age is not None and age is not None and age>max_age: removed.append(r)
        else: kept.append(r)
    if max_count is not None and len(kept)>max_count:
        overflow=len(kept)-max_count; terminal=[r for r in kept if isinstance(r,dict) and r.get("status") in statuses][:overflow]; ids={id(r) for r in terminal}; kept=[r for r in kept if id(r) not in ids]; removed.extend(terminal)
    if execute and removed:
        archive=project/".cognitive-os"/"recovery"/"ledgers"; archive.mkdir(parents=True,exist_ok=True); f=archive/f"{surface['id']}-{stamp()}.json"; f.write_text(json.dumps(removed,indent=2,sort_keys=True)+"\n",encoding="utf-8"); data[key]=kept; data["updated_at"]=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"); atomic_json(path,data); return {"surface":surface["id"],"removed":len(removed),"execute":True,"archive":str(f.relative_to(project))}
    return {"surface":surface["id"],"removed":len(removed),"execute":execute}

def reap_bus(project: Path, surface: dict[str, Any], execute: bool) -> dict[str, Any]:
    paths=[p for p in sorted(project.glob(surface["path"])) if p.is_dir()]; max_age=duration(surface.get("max_age")); max_count=as_int(surface.get("max_count")); now=datetime.now(timezone.utc).timestamp(); stale=[]
    if max_age is not None: stale=[p for p in paths if now-p.stat().st_mtime>max_age]
    if max_count is not None and len(paths)-len(stale)>max_count: stale.extend(sorted([p for p in paths if p not in stale], key=lambda p:p.stat().st_mtime)[:len(paths)-len(stale)-max_count])
    archive=project/".cognitive-os"/"archive"/"agent-bus"/stamp(); archived=[]
    if execute and stale:
        archive.mkdir(parents=True,exist_ok=True)
        for p in stale:
            dest=archive/p.name
            if dest.exists(): shutil.rmtree(dest)
            shutil.move(str(p),str(dest)); archived.append(str(dest.relative_to(project)))
    return {"surface":surface["id"],"candidate_count":len(stale),"execute":execute,"archive_dir":str(archive.relative_to(project)),"archived":archived}

def reap_surface(project: Path, surface: dict[str, Any], execute: bool) -> dict[str, Any] | None:
    if surface.get("id")=="auto-pre-agent-stashes": return reap_stashes(project,surface,execute)
    if str(surface.get("path","")).endswith(".json"): return compact_ledger(project,surface,execute)
    if surface.get("id")=="agent-bus-directories": return reap_bus(project,surface,execute)
    return None

def write_metrics(project: Path, payload: dict[str, Any]) -> None:
    path=project/".cognitive-os"/"metrics"/"state-retention-audit.jsonl"; path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as fh: fh.write(json.dumps({"timestamp":datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),**payload},sort_keys=True)+"\n")


SAFE_AUTO_MODES = {"repair-safe"}
REPAIR_BEFORE_BLOCK_MODES = {"repair-before-block"}


def retention_mode(surface: dict[str, Any]) -> str:
    return str(surface.get("retention_mode") or "observe")


def auto_safe_surfaces(surfaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [s for s in surfaces if retention_mode(s) in SAFE_AUTO_MODES]


def repair_before_block_surfaces(surfaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [s for s in surfaces if retention_mode(s) in REPAIR_BEFORE_BLOCK_MODES]


def acquire_controller_lock(project: Path):
    lock_path = project / ".cognitive-os" / "runtime" / "state-retention.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = lock_path.open("w", encoding="utf-8")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        fh.close()
        return None
    return fh


def cooldown_allows(project: Path, mode: str, cooldown_seconds: int) -> tuple[bool, int]:
    if cooldown_seconds <= 0:
        return True, 0
    path = project / ".cognitive-os" / "runtime" / f"state-retention-{mode}.last-run"
    now = int(datetime.now(timezone.utc).timestamp())
    try:
        previous = int(path.read_text(encoding="utf-8").strip())
    except Exception:
        previous = 0
    remaining = cooldown_seconds - (now - previous)
    if remaining > 0:
        return False, remaining
    return True, 0


def mark_cooldown(project: Path, mode: str) -> None:
    path = project / ".cognitive-os" / "runtime" / f"state-retention-{mode}.last-run"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(int(datetime.now(timezone.utc).timestamp())) + "\n", encoding="utf-8")

def parser() -> argparse.ArgumentParser:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project-dir",default=os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd())
    p.add_argument("--manifest",default=str(DEFAULT_MANIFEST))
    p.add_argument("--json",action="store_true")
    p.add_argument("--strict",action="store_true")
    p.add_argument("--reap",action="store_true")
    p.add_argument("--execute",action="store_true")
    p.add_argument("--surface",action="append")
    p.add_argument("--no-metrics",action="store_true")
    p.add_argument("--auto-safe",action="store_true", help="select only retention_mode=repair-safe surfaces; requires --reap for cleanup")
    p.add_argument("--repair-before-block",action="store_true", help="select only retention_mode=repair-before-block surfaces")
    p.add_argument("--cooldown-seconds",type=int,default=int(os.environ.get("COS_STATE_RETENTION_COOLDOWN_SECONDS","300")))
    return p

def main(argv: Sequence[str] | None=None) -> int:
    args=parser().parse_args(argv)
    project=Path(args.project_dir).resolve()
    manifest=load_manifest(Path(args.manifest))
    mf=validate_manifest(manifest)
    wanted=set(args.surface or [])
    all_surfaces=[s for s in manifest.get("surfaces",[]) if isinstance(s,dict)]
    if args.auto_safe:
        selected=auto_safe_surfaces(all_surfaces)
    elif args.repair_before_block:
        selected=repair_before_block_surfaces(all_surfaces)
    else:
        selected=all_surfaces
    surfaces=[s for s in selected if not wanted or s.get("id") in wanted]

    lock_fh = None
    cooldown_skipped = False
    cooldown_remaining = 0
    mode = "auto-safe" if args.auto_safe else "repair-before-block" if args.repair_before_block else "manual"
    if args.reap and args.execute and mode != "manual":
        allowed, cooldown_remaining = cooldown_allows(project, mode, args.cooldown_seconds)
        if not allowed:
            cooldown_skipped = True
        else:
            lock_fh = acquire_controller_lock(project)
            if lock_fh is None:
                cooldown_skipped = True

    audits=[audit_surface(project,s) for s in surfaces if not REQUIRED-set(s)]
    reaped=[]
    if args.reap and not cooldown_skipped:
        for s in surfaces:
            if not REQUIRED-set(s):
                r=reap_surface(project,s,args.execute)
                if r is not None: reaped.append(r)
        if args.execute and mode != "manual":
            mark_cooldown(project, mode)
    if lock_fh is not None:
        fcntl.flock(lock_fh, fcntl.LOCK_UN)
        lock_fh.close()
    count=len(mf)+sum(len(a.get("findings",[])) for a in audits)
    payload={"schema_version":"state-retention-audit.v1","project_dir":str(project),"execute":bool(args.execute),"mode":mode,"cooldown_skipped":cooldown_skipped,"cooldown_remaining_seconds":cooldown_remaining,"manifest_findings":mf,"surfaces":audits,"reap":reaped,"summary":{"surface_count":len(audits),"finding_count":count}}
    if not args.no_metrics: write_metrics(project,{"summary":payload["summary"],"execute":bool(args.execute),"mode":mode,"cooldown_skipped":cooldown_skipped})
    if args.json: print(json.dumps(payload,indent=2,sort_keys=True))
    else:
        print(f"State retention: surfaces={len(audits)} findings={count} execute={bool(args.execute)} mode={mode}")
        if cooldown_skipped: print(f"- skipped: retention controller cooldown/lock active ({cooldown_remaining}s remaining)")
        for a in audits:
            if a.get("findings"): print(f"- {a['surface']}: {a['findings']}")
        for r in reaped: print(f"- reap {r['surface']}: candidates={r.get('candidate_count', r.get('removed',0))} execute={r.get('execute')}")
    return 2 if args.strict and count else 0

if __name__ == "__main__":
    raise SystemExit(main())

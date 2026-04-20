#!/usr/bin/env bash
# so-vitals.sh — ADR-028 D1.D unified SO runtime dashboard
# Usage: scripts/so-vitals.sh [--json]
set -uo pipefail

MODE="${1:-human}"
PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
cd "$PROJECT_DIR" || exit 0

python3 - <<PYEOF
import json, os, sys, time, subprocess
from pathlib import Path

sys.path.insert(0, ".")

ROOT = Path("$PROJECT_DIR")
MODE = "$MODE"

try:
    from lib.metric_event import MetricEvent, append_event
except ImportError:
    print("so-vitals: lib.metric_event not importable", file=sys.stderr)
    sys.exit(1)

# Agents in flight (graceful fallback if D1.C not landed)
agents = []
try:
    from lib.agent_heartbeat import list_live, scan_stale
    for hb in list_live(max_age_seconds=300):
        agents.append({"agent_id": hb.agent_id, "state": hb.state, "age_s": int(time.time() - hb.timestamp), "pid": hb.pid})
    for hb in scan_stale(max_age_seconds=300):
        agents.append({"agent_id": hb.agent_id, "state": "STALE", "age_s": int(time.time() - hb.timestamp), "pid": hb.pid})
except ImportError:
    agents = []  # D1.C not ready yet

# Registered processes + TTL (D1.B)
processes = []
try:
    from lib.process_registry import list_live as reg_live
    now = time.time()
    for rec in reg_live():
        processes.append({
            "pid": rec.pid, "owner": rec.owner, "kind": rec.kind,
            "ttl_s": rec.ttl_seconds,
            "expires_in_s": int(rec.expires_at() - now),
        })
except ImportError:
    processes = []

# Orphan suspects — dry scan (no side-effect events, unlike detect_orphans())
orphans = []
try:
    registered_pids = set()
    try:
        from lib.process_registry import list_live as _live
        registered_pids = {r.pid for r in _live()}
    except Exception:
        pass
    hook_names = []
    hooks_dir = ROOT / "hooks"
    if hooks_dir.is_dir():
        hook_names = [p.name for p in hooks_dir.glob("*.sh")]
    if hook_names:
        try:
            out = subprocess.run(["ps", "-eo", "pid,ppid,command"], capture_output=True, text=True, timeout=10)
            for line in out.stdout.splitlines()[1:]:
                parts = line.strip().split(None, 2)
                if len(parts) < 3:
                    continue
                try:
                    pid, ppid = int(parts[0]), int(parts[1])
                except ValueError:
                    continue
                cmd = parts[2]
                if any(h in cmd for h in hook_names) and pid not in registered_pids:
                    orphans.append({"pid": pid, "ppid": ppid, "command": cmd[:120]})
        except Exception:
            pass
except Exception:
    pass

# JSONL sizes + rotation flags
metrics_dir = ROOT / ".cognitive-os" / "metrics"
jsonl_files = []
ROTATE_BYTES = 1024 * 1024  # 1 MiB (ADR-028 D1.A)
for p in sorted(metrics_dir.glob("*.jsonl")) if metrics_dir.is_dir() else []:
    try:
        size = p.stat().st_size
        age_d = (time.time() - p.stat().st_mtime) / 86400.0
        will_rotate = size >= ROTATE_BYTES or age_d >= 7
        jsonl_files.append({
            "file": p.name,
            "size_bytes": size,
            "size_kib": round(size / 1024, 1),
            "age_days": round(age_d, 1),
            "will_rotate": will_rotate,
        })
    except OSError:
        continue

# Disk usage of .cognitive-os
disk_bytes = 0
try:
    out = subprocess.run(["du", "-sk", str(ROOT / ".cognitive-os")], capture_output=True, text=True, timeout=10)
    if out.returncode == 0:
        disk_bytes = int(out.stdout.split()[0]) * 1024
except Exception:
    pass

payload = {
    "agents_in_flight": len([a for a in agents if a["state"] not in ("STALE", "hung")]),
    "agents_stale": len([a for a in agents if a["state"] == "STALE"]),
    "agents_detail": agents,
    "processes_registered": len(processes),
    "processes_detail": processes,
    "orphan_suspects_count": len(orphans),
    "orphan_suspects": orphans[:20],
    "jsonl_files": len(jsonl_files),
    "jsonl_detail": jsonl_files,
    "jsonl_needs_rotation": len([j for j in jsonl_files if j["will_rotate"]]),
    "disk_bytes": disk_bytes,
    "disk_mib": round(disk_bytes / (1024*1024), 2),
}

event = MetricEvent(
    source="so-vitals",
    event_type="so.vitals",
    payload=payload,
)

# Always persist the snapshot to so-vitals.jsonl (ADR-028 line 234)
out_path = ROOT / ".cognitive-os" / "metrics" / "so-vitals.jsonl"
append_event(str(out_path), event)

if MODE == "--json":
    print(json.dumps(event.to_dict()))
else:
    # Human-readable
    print("=== SO Vitals ===")
    print(f"Disk:         {payload['disk_mib']} MiB under .cognitive-os/")
    print(f"Agents:       {payload['agents_in_flight']} in flight, {payload['agents_stale']} stale")
    print(f"Processes:    {payload['processes_registered']} registered, {payload['orphan_suspects_count']} orphan suspects")
    print(f"JSONL files:  {payload['jsonl_files']} total, {payload['jsonl_needs_rotation']} need rotation")
    if agents:
        print()
        print("Agents:")
        for a in agents[:10]:
            print(f"  {a['agent_id'][:40]:<40} {a['state']:<10} age={a['age_s']}s pid={a['pid']}")
    if processes:
        print()
        print("Registered processes:")
        for p in processes[:10]:
            print(f"  pid={p['pid']:<7} kind={p['kind']:<16} ttl_remaining={p['expires_in_s']}s owner={p['owner']}")
    if orphans:
        print()
        print(f"Orphan suspects (first 5 of {len(orphans)}):")
        for o in orphans[:5]:
            print(f"  pid={o['pid']:<7} ppid={o['ppid']:<7} {o['command']}")
    if jsonl_files:
        print()
        print(f"JSONL files needing rotation ({payload['jsonl_needs_rotation']}):")
        for j in jsonl_files:
            if j["will_rotate"]:
                print(f"  {j['file']:<40} {j['size_kib']} KiB  age={j['age_days']}d")
PYEOF

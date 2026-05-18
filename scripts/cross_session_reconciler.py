#!/usr/bin/env python3
# SCOPE: both
"""Read-only cross-session reconciler for concurrent-agent safety state."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
from typing import Any, cast
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.concurrency_safety import load_concurrency_safety_config, project_runtime_dir
from lib.project_paths import project_dir_from_args as project_dir
from lib.script_io import read_jsonl

def read_json_files(path: Path) -> list[dict[str, Any]]:
    if not path.exists(): return []
    items = []
    for file in sorted(path.glob("*.json")):
        try: items.append(json.loads(file.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError): items.append({"file": str(file), "status": "unreadable"})
    return items

def preserve_summary(project: Path) -> dict[str, Any]:
    script = ROOT / "scripts" / "cos-doctor-preserve.sh"
    if not script.exists() or not (project / ".git").exists():
        return {"available": False, "reason": "not-a-git-project-or-script-missing"}
    proc = subprocess.run(["bash", str(script), "--project-dir", str(project), "--json"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30)  # timeout per ADR-278 (default - review)
    try:
        parsed_payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        parsed_payload = {"raw_stdout": proc.stdout, "raw_stderr": proc.stderr}
    payload: dict[str, Any]
    if isinstance(parsed_payload, dict):
        payload = cast(dict[str, Any], parsed_payload)
    else:
        payload = {"raw_payload": parsed_payload}
    payload["available"] = True; payload["exit_code"] = proc.returncode; return payload

def reconcile(args: argparse.Namespace) -> int:
    project = project_dir(args); runtime = project_runtime_dir(project); cfg = load_concurrency_safety_config(str(project / "cognitive-os.yaml"))
    report = {"project_dir": str(project), "config": cfg.to_dict(), "resource_leases": read_json_files(runtime / "resource-leases"), "agent_work_events": read_jsonl(runtime / "agent-work-ledger.jsonl"), "approval_events": read_jsonl(runtime / "approval-ledger.jsonl"), "edit_locks": read_json_files(runtime / "edit-locks"), "preserve_branches": preserve_summary(project)}
    print(json.dumps(report, sort_keys=True)); return 0

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--project-dir"); parser.add_argument("--json", action="store_true"); parser.set_defaults(func=reconcile); return parser

def main() -> int:
    args = build_parser().parse_args(); return int(args.func(args))
if __name__ == "__main__": raise SystemExit(main())

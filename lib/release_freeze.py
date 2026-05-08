"""ADR-246 release transaction freeze substrate.

Slice A is intentionally conservative and read-only except for creating/removing
release-freeze receipt files. It gives destructive/public operations a stable
transaction id without killing agents or mutating git state.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "release-freeze/v1"
DEFAULT_MANIFEST = Path("manifests/release-freeze.yaml")


@dataclass(frozen=True)
class FreezeFinding:
    severity: str
    code: str
    message: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"severity": self.severity, "code": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compact_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def git(project_dir: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(project_dir), *args], text=True, capture_output=True, check=False)


def git_root(start: Path) -> Path:
    proc = git(start, ["rev-parse", "--show-toplevel"])
    if proc.returncode == 0 and proc.stdout.strip():
        return Path(proc.stdout.strip()).resolve()
    return start.resolve()


def load_manifest(project_dir: Path, manifest_path: Path | None = None) -> dict[str, Any]:
    path = manifest_path or (project_dir / DEFAULT_MANIFEST)
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def rel(project_dir: Path, path: Path | str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else project_dir / p


def runtime_dir(project_dir: Path, manifest: dict[str, Any]) -> Path:
    return rel(project_dir, manifest.get("runtime_dir", ".cognitive-os/runtime/release-freeze"))


def report_dir(project_dir: Path, manifest: dict[str, Any]) -> Path:
    return rel(project_dir, manifest.get("report_dir", ".cognitive-os/reports/release-freeze"))


def active_marker_path(project_dir: Path, manifest: dict[str, Any]) -> Path:
    return rel(project_dir, manifest.get("active_marker", ".cognitive-os/runtime/release-freeze/active.json"))


def active_transaction(project_dir: Path, manifest: dict[str, Any] | None = None) -> dict[str, Any] | None:
    root = project_dir.resolve()
    data = manifest or load_manifest(root)
    marker = active_marker_path(root, data)
    if not marker.exists():
        return None
    try:
        return json.loads(marker.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"schema_version": SCHEMA_VERSION, "status": "corrupt", "path": str(marker)}


def _status_clean_worktree(project_dir: Path, manifest: dict[str, Any]) -> tuple[dict[str, Any], list[FreezeFinding]]:
    check = ((manifest.get("checks") or {}).get("clean_worktree") or {})
    if check.get("enabled", True) is False:
        return {"name": "clean_worktree", "status": "skipped"}, []
    proc = git(project_dir, ["status", "--porcelain"])
    if proc.returncode != 0:
        finding = FreezeFinding("block", "git-status-failed", "git status failed during freeze prepare.", {"stderr": proc.stderr[:500]})
        return {"name": "clean_worktree", "status": "block"}, [finding]
    allowlisted = set(str(p) for p in check.get("allowlisted_paths", []) or [])
    dirty = []
    for line in proc.stdout.splitlines():
        path = line[3:] if len(line) > 3 else line
        if path and path not in allowlisted:
            dirty.append(line)
    if dirty:
        return {"name": "clean_worktree", "status": "block", "dirty_count": len(dirty), "dirty_sample": dirty[:20]}, [
            FreezeFinding("block", "working-tree-dirty", "Release freeze requires a clean working tree unless paths are explicitly allowlisted.", {"dirty_count": len(dirty), "sample": dirty[:20]})
        ]
    return {"name": "clean_worktree", "status": "pass"}, []


def _status_branch(project_dir: Path, manifest: dict[str, Any]) -> tuple[dict[str, Any], list[FreezeFinding]]:
    check = ((manifest.get("checks") or {}).get("branch") or {})
    if check.get("enabled", True) is False:
        return {"name": "branch", "status": "skipped"}, []
    expected = str(manifest.get("expected_branch", "main"))
    proc = git(project_dir, ["branch", "--show-current"])
    branch = proc.stdout.strip() if proc.returncode == 0 else ""
    if branch != expected:
        return {"name": "branch", "status": "block", "current": branch, "expected": expected}, [
            FreezeFinding("block", "wrong-release-branch", "Release freeze must start on the expected release branch.", {"current": branch, "expected": expected})
        ]
    return {"name": "branch", "status": "pass", "current": branch}, []


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _claims_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("claims", "active_claims", "tasks", "items"):
            if isinstance(payload.get(key), list):
                return [item for item in payload[key] if isinstance(item, dict)]
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _claim_is_active(claim: dict[str, Any]) -> bool:
    for key in ("released_at", "completed_at", "ended_at", "closed_at"):
        if claim.get(key):
            return False
    status = str(claim.get("status", claim.get("state", "active"))).lower()
    return status not in {"released", "complete", "completed", "closed", "done", "expired"}


def _status_task_claims(project_dir: Path, manifest: dict[str, Any]) -> tuple[dict[str, Any], list[FreezeFinding]]:
    check = ((manifest.get("checks") or {}).get("task_claims") or {})
    if check.get("enabled", True) is False:
        return {"name": "task_claims", "status": "skipped"}, []
    active: list[dict[str, Any]] = []
    scanned: list[str] = []
    for raw in check.get("paths", []) or []:
        path = rel(project_dir, raw)
        if not path.exists():
            continue
        scanned.append(str(Path(raw)))
        payload = _load_json(path)
        active.extend([claim for claim in _claims_from_payload(payload) if _claim_is_active(claim)])
    if active:
        return {"name": "task_claims", "status": "block", "active_count": len(active), "scanned": scanned}, [
            FreezeFinding("block", "active-task-claims", "Release freeze refuses while active task claims are present.", {"active_count": len(active), "sample": active[:5]})
        ]
    return {"name": "task_claims", "status": "pass", "scanned": scanned}, []


def _parse_jsonl_tail(path: Path, limit: int = 200) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    except FileNotFoundError:
        return []
    items: list[dict[str, Any]] = []
    for line in lines:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            items.append(payload)
    return items


def _parse_ts(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None


def _status_agent_heartbeats(project_dir: Path, manifest: dict[str, Any]) -> tuple[dict[str, Any], list[FreezeFinding]]:
    check = ((manifest.get("checks") or {}).get("agent_heartbeats") or {})
    if check.get("enabled", True) is False:
        return {"name": "agent_heartbeats", "status": "skipped"}, []
    stale_after = float(check.get("stale_after_seconds", 900))
    now = time.time()
    active: list[dict[str, Any]] = []
    for raw in check.get("paths", []) or []:
        path = rel(project_dir, raw)
        for item in _parse_jsonl_tail(path):
            status = str(item.get("status", item.get("state", "active"))).lower()
            if status in {"done", "completed", "closed", "stopped", "released"}:
                continue
            ts = _parse_ts(item.get("timestamp") or item.get("ts") or item.get("heartbeat_at") or item.get("updated_at"))
            if ts is None:
                continue
            if now - ts <= stale_after:
                active.append(item)
    if active:
        return {"name": "agent_heartbeats", "status": "block", "active_count": len(active)}, [
            FreezeFinding("block", "active-agent-heartbeats", "Release freeze refuses while recent agent heartbeats are present.", {"active_count": len(active), "sample": active[:5]})
        ]
    return {"name": "agent_heartbeats", "status": "pass"}, []


def _run_optional_command(project_dir: Path, name: str, check: dict[str, Any]) -> tuple[dict[str, Any], list[FreezeFinding]]:
    if check.get("enabled", False) is False:
        return {"name": name, "status": "skipped", "rationale": check.get("rationale")}, []
    cmd = [str(part) for part in check.get("command", [])]
    if not cmd:
        return {"name": name, "status": "block"}, [FreezeFinding("block", f"{name}-command-missing", f"{name} check is enabled but has no command.")]
    proc = subprocess.run(cmd, cwd=str(project_dir), text=True, capture_output=True, check=False, timeout=float(check.get("timeout_seconds", 60)))
    status = "pass" if proc.returncode == 0 else "block"
    findings: list[FreezeFinding] = []
    if proc.returncode != 0:
        findings.append(FreezeFinding("block", f"{name}-failed", f"{name} command failed during release freeze prepare.", {"returncode": proc.returncode, "stderr": proc.stderr[:500], "stdout": proc.stdout[:500]}))
    return {"name": name, "status": status, "returncode": proc.returncode}, findings


def prepare(project_dir: Path, manifest_path: Path | None = None) -> dict[str, Any]:
    root = git_root(project_dir)
    manifest = load_manifest(root, manifest_path)
    checks: list[dict[str, Any]] = []
    findings: list[FreezeFinding] = []
    for fn in (_status_clean_worktree, _status_branch, _status_task_claims, _status_agent_heartbeats):
        result, new_findings = fn(root, manifest)
        checks.append(result)
        findings.extend(new_findings)
    manifest_checks = manifest.get("checks") or {}
    for name in ("pre_public_risk_audit", "primitive_coherence"):
        result, new_findings = _run_optional_command(root, name, manifest_checks.get(name, {}) or {})
        checks.append(result)
        findings.extend(new_findings)
    head_proc = git(root, ["rev-parse", "HEAD"])
    branch_proc = git(root, ["branch", "--show-current"])
    status = "block" if any(f.severity == "block" for f in findings) else "warn" if any(f.severity == "warn" for f in findings) else "pass"
    return {
        "schema_version": SCHEMA_VERSION,
        "operation": "prepare",
        "status": status,
        "project_dir": str(root),
        "branch": branch_proc.stdout.strip() if branch_proc.returncode == 0 else None,
        "head": head_proc.stdout.strip() if head_proc.returncode == 0 else None,
        "checks": checks,
        "findings": [f.to_dict() for f in findings],
        "policy": "Release freeze prepare is read-only and blocks destructive/public windows until the repo is stable.",
    }


def _transaction_id() -> str:
    return f"rel-{compact_ts()}-{uuid.uuid4().hex[:8]}"


def _write_markdown_report(path: Path, receipt: dict[str, Any]) -> None:
    lines = [
        f"# Release Freeze {receipt['transaction_id']}",
        "",
        f"- Status: `{receipt['status']}`",
        f"- Created at: `{receipt['created_at']}`",
        f"- Reason: `{receipt.get('reason', '')}`",
        f"- Branch: `{receipt.get('branch', '')}`",
        f"- HEAD: `{receipt.get('head', '')}`",
        "",
        "## Checks",
        "",
    ]
    for check in receipt.get("prepare", {}).get("checks", []):
        lines.append(f"- `{check.get('name')}`: `{check.get('status')}`")
    lines.extend(["", "## Policy", "", "Destructive/public operations must cite this release transaction id while the freeze is active.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def begin(project_dir: Path, *, reason: str, manifest_path: Path | None = None) -> dict[str, Any]:
    root = git_root(project_dir)
    manifest = load_manifest(root, manifest_path)
    existing = active_transaction(root, manifest)
    if existing and existing.get("status") == "active":
        return {
            "schema_version": SCHEMA_VERSION,
            "operation": "begin",
            "status": "block",
            "findings": [FreezeFinding("block", "release-freeze-already-active", "A release freeze is already active.", {"transaction_id": existing.get("transaction_id")}).to_dict()],
            "active": existing,
        }
    prep = prepare(root, manifest_path)
    if prep["status"] == "block":
        return {"schema_version": SCHEMA_VERSION, "operation": "begin", "status": "block", "prepare": prep, "findings": prep.get("findings", [])}
    tid = _transaction_id()
    created_at = utc_now()
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "operation": "begin",
        "status": "active",
        "transaction_id": tid,
        "created_at": created_at,
        "reason": reason,
        "project_dir": str(root),
        "branch": prep.get("branch"),
        "head": prep.get("head"),
        "allowed_operations": manifest.get("allowed_operations", []),
        "prepare": prep,
    }
    rdir = runtime_dir(root, manifest)
    rdir.mkdir(parents=True, exist_ok=True)
    receipt_path = rdir / f"{tid}.json"
    receipt["receipt_path"] = str(receipt_path)
    marker = active_marker_path(root, manifest)
    receipt["active_marker"] = str(marker)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    marker.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    mdir = report_dir(root, manifest)
    mdir.mkdir(parents=True, exist_ok=True)
    report_path = mdir / f"{tid}.md"
    _write_markdown_report(report_path, receipt)
    receipt["report_path"] = str(report_path)
    # Rewrite files with final report_path included.
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    marker.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def status(project_dir: Path, manifest_path: Path | None = None) -> dict[str, Any]:
    root = git_root(project_dir)
    manifest = load_manifest(root, manifest_path)
    active = active_transaction(root, manifest)
    return {
        "schema_version": SCHEMA_VERSION,
        "operation": "status",
        "status": "active" if active and active.get("status") == "active" else "inactive",
        "project_dir": str(root),
        "active": active,
    }


def end(project_dir: Path, *, transaction_id: str, manifest_path: Path | None = None) -> dict[str, Any]:
    root = git_root(project_dir)
    manifest = load_manifest(root, manifest_path)
    active = active_transaction(root, manifest)
    if not active or active.get("status") != "active":
        return {"schema_version": SCHEMA_VERSION, "operation": "end", "status": "block", "findings": [FreezeFinding("block", "no-active-release-freeze", "No active release freeze exists.").to_dict()]}
    if active.get("transaction_id") != transaction_id:
        return {"schema_version": SCHEMA_VERSION, "operation": "end", "status": "block", "findings": [FreezeFinding("block", "release-transaction-mismatch", "Active release transaction id does not match.", {"active": active.get("transaction_id"), "provided": transaction_id}).to_dict()]}
    ended = dict(active)
    ended["operation"] = "end"
    ended["status"] = "ended"
    ended["ended_at"] = utc_now()
    path = Path(str(active.get("receipt_path", runtime_dir(root, manifest) / f"{transaction_id}.json")))
    path.write_text(json.dumps(ended, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    marker = active_marker_path(root, manifest)
    if marker.exists():
        marker.unlink()
    return ended


def assert_history_sanitize_allowed(project_dir: Path) -> None:
    """Raise RuntimeError if history sanitize is inside a mismatched freeze.

    No active freeze means legacy/non-release execution remains allowed. If a
    freeze exists, destructive history rewrite must cite the active transaction.
    """
    root = git_root(project_dir)
    manifest = load_manifest(root)
    active = active_transaction(root, manifest)
    if not active or active.get("status") != "active":
        return
    env_name = ((manifest.get("guards") or {}).get("history_sanitization") or {}).get("require_transaction_env", "COS_RELEASE_TRANSACTION_ID")
    provided = os.environ.get(str(env_name))
    expected = active.get("transaction_id")
    if provided != expected:
        raise RuntimeError(f"history sanitize requires {env_name}={expected} while release freeze is active")

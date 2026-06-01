#!/usr/bin/env python3
# SCOPE: os-only
"""Audit Bun package-manager and lifecycle-script hardening.

Bun's `install.ignoreScripts = true` disables preinstall/install/postinstall/
prepare lifecycle scripts for the project, workspaces, installed packages, and
trustedDependencies. This guard keeps tracked JavaScript package roots explicit
about that behavior so `bun install` / `bun add` cannot execute arbitrary
lifecycle hooks by accident.

Cognitive OS uses Bun as the canonical JavaScript package manager. Tracked
JavaScript package roots must declare `packageManager: bun@...`, use Bun
lockfiles for dependency-bearing packages, and must not commit npm, pnpm, or
Yarn lockfiles.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

LIFECYCLE_SCRIPTS = {
    "preinstall",
    "install",
    "postinstall",
    "preprepare",
    "prepare",
    "postprepare",
}
FORBIDDEN_LOCKFILES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock"}
DEPENDENCY_FIELDS = {"dependencies", "devDependencies", "optionalDependencies", "peerDependencies"}
IGNORED_TRACKED_PARTS = {
    ".claude/plugins",
    "reference",
}


def is_ignored_tracked_path(path: Path) -> bool:
    posix = path.as_posix()
    return any(posix == part or posix.startswith(f"{part}/") for part in IGNORED_TRACKED_PARTS)


def tracked_files(root: Path) -> list[Path]:
    proc = subprocess.run(["git", "ls-files"], cwd=root, text=True, capture_output=True, check=False, timeout=10)
    if proc.returncode != 0:
        return [p.relative_to(root) for p in root.rglob("package.json") if "node_modules" not in p.parts]
    return [Path(line) for line in proc.stdout.splitlines() if line.strip()]


def parse_bunfig_ignore_scripts(path: Path) -> bool | None:
    if not path.exists():
        return None
    in_install = False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            in_install = line == "[install]"
            continue
        if in_install and line.startswith("ignoreScripts"):
            _, _, value = line.partition("=")
            return value.strip().lower() == "true"
    return None


def nearest_bunfig(package_dir: Path, root: Path) -> Path | None:
    cur = package_dir.resolve()
    root_resolved = root.resolve()
    while True:
        candidate = cur / "bunfig.toml"
        if candidate.exists():
            return candidate
        if cur == root_resolved or cur.parent == cur:
            return None
        cur = cur.parent


def package_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    tracked = tracked_files(root)
    package_paths = sorted(path for path in tracked if path.name == "package.json" and not is_ignored_tracked_path(path))
    for rel in package_paths:
        full = root / rel
        try:
            data = json.loads(full.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            rows.append({"path": rel.as_posix(), "status": "fail", "reason": f"invalid package.json: {exc}"})
            continue
        package_dir = full.parent
        bunfig = nearest_bunfig(package_dir, root)
        ignore_scripts = parse_bunfig_ignore_scripts(bunfig) if bunfig else None
        scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
        lifecycle = {name: scripts[name] for name in sorted(LIFECYCLE_SCRIPTS) if name in scripts}
        trusted = data.get("trustedDependencies")
        package_manager = data.get("packageManager")
        package_manager_ok = isinstance(package_manager, str) and package_manager.startswith("bun@")
        has_dependency_fields = any(isinstance(data.get(field), dict) and bool(data.get(field)) for field in DEPENDENCY_FIELDS)
        bun_lock = package_dir / "bun.lock"
        legacy_bun_lock = package_dir / "bun.lockb"
        has_bun_lock = bun_lock.exists() or legacy_bun_lock.exists()
        required_bun_lock = has_dependency_fields
        failures: list[str] = []
        if ignore_scripts is not True:
            failures.append("missing bunfig.toml [install] ignoreScripts = true")
        if not package_manager_ok:
            failures.append("packageManager must be bun@<version>")
        if required_bun_lock and not has_bun_lock:
            failures.append("dependency-bearing package must commit bun.lock")
        status = "pass" if not failures else "fail"
        reason = "bun package-manager and install.ignoreScripts policy is in effect" if status == "pass" else "; ".join(failures)
        rows.append(
            {
                "path": rel.as_posix(),
                "status": status,
                "reason": reason,
                "bunfig": bunfig.relative_to(root).as_posix() if bunfig else None,
                "ignoreScripts": ignore_scripts,
                "packageManager": package_manager,
                "packageManager_ok": package_manager_ok,
                "bun_lock": (bun_lock if bun_lock.exists() else legacy_bun_lock).relative_to(root).as_posix()
                if has_bun_lock
                else None,
                "bun_lock_required": required_bun_lock,
                "lifecycle_scripts_blocked": lifecycle,
                "trustedDependencies_ignored_by_policy": trusted or [],
                "impact": "preinstall/install/postinstall/prepare hooks will not run during bun install/add",
            }
        )
    return rows


def forbidden_lockfile_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rel in sorted(tracked_files(root)):
        if rel.name not in FORBIDDEN_LOCKFILES or is_ignored_tracked_path(rel):
            continue
        if not (root / rel).exists():
            continue
        rows.append(
            {
                "path": rel.as_posix(),
                "status": "fail",
                "reason": "Cognitive OS uses Bun; commit bun.lock instead of npm/pnpm/yarn lockfiles",
            }
        )
    return rows


def build_report(root: Path) -> dict[str, Any]:
    rows = package_rows(root)
    forbidden_lockfiles = forbidden_lockfile_rows(root)
    failures = [row for row in rows if row["status"] != "pass"]
    lifecycle_rows = [row for row in rows if row["lifecycle_scripts_blocked"]]
    return {
        "schema_version": "bun-install-policy-audit/v2",
        "status": "pass" if not failures and not forbidden_lockfiles else "fail",
        "package_count": len(rows),
        "failure_count": len(failures) + len(forbidden_lockfiles),
        "lifecycle_impact_count": len(lifecycle_rows),
        "forbidden_lockfile_count": len(forbidden_lockfiles),
        "canonical_package_manager": "bun",
        "rows": rows,
        "forbidden_lockfiles": forbidden_lockfiles,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    report = build_report(root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"bun-install-policy: {report['status']} packages={report['package_count']} failures={report['failure_count']}")
        for row in report["rows"]:
            marker = "OK" if row["status"] == "pass" else "FAIL"
            print(
                f"  [{marker}] {row['path']} packageManager={row['packageManager']} "
                f"bunfig={row['bunfig']} bun_lock={row['bun_lock']} "
                f"lifecycle_blocked={sorted(row['lifecycle_scripts_blocked'])}"
            )
        for row in report["forbidden_lockfiles"]:
            print(f"  [FAIL] {row['path']} {row['reason']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

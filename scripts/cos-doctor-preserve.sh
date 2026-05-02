#!/usr/bin/env bash
# SCOPE: both
# Read-only doctor for codex/preserve-* branch governance (ADR-110).
set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
BRANCH_PATTERN="codex/preserve-*"
BASE_REF="HEAD"
JSON=false
STRICT=false

usage() {
  cat <<'EOF'
Usage: bash scripts/cos-doctor-preserve.sh [--project-dir PATH] [--branch-pattern GLOB] [--base-ref REF] [--json] [--strict]

Read-only governance report for preserve branches. Detects missing manifests,
mixed-scope branches, already-integrated branches, commits that exist but are
not ancestors of the active base ref, and delete candidates.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --project-dir)
      PROJECT_DIR="${2:-}"; [ -n "$PROJECT_DIR" ] || { echo "--project-dir requires value" >&2; exit 2; }; shift ;;
    --project-dir=*) PROJECT_DIR="${1#--project-dir=}" ;;
    --branch-pattern)
      BRANCH_PATTERN="${2:-}"; [ -n "$BRANCH_PATTERN" ] || { echo "--branch-pattern requires value" >&2; exit 2; }; shift ;;
    --branch-pattern=*) BRANCH_PATTERN="${1#--branch-pattern=}" ;;
    --base-ref)
      BASE_REF="${2:-}"; [ -n "$BASE_REF" ] || { echo "--base-ref requires value" >&2; exit 2; }; shift ;;
    --base-ref=*) BASE_REF="${1#--base-ref=}" ;;
    --json) JSON=true ;;
    --strict) STRICT=true ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown flag: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

python3 - "$PROJECT_DIR" "$BRANCH_PATTERN" "$BASE_REF" "$JSON" "$STRICT" <<'PY'
from __future__ import annotations

import fnmatch
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

project = Path(sys.argv[1]).resolve()
pattern = sys.argv[2]
base_ref = sys.argv[3]
json_mode = sys.argv[4] == "true"
strict = sys.argv[5] == "true"


def git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project), *args],
        text=True,
        capture_output=True,
        check=check,
    )


def safe_branch_name(branch: str) -> str:
    return branch.replace("/", "__") + ".json"


def manifest_path(branch: str) -> Path:
    return project / ".cognitive-os" / "preserve-manifests" / safe_branch_name(branch)


def load_manifest(branch: str) -> dict[str, Any] | None:
    path = manifest_path(branch)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # read-only doctor: report corrupt, do not mutate
        return {"_corrupt": str(exc)}
    return data if isinstance(data, dict) else {"_corrupt": "manifest is not a JSON object"}


def branch_tip(branch: str) -> str:
    return git(["rev-parse", branch]).stdout.strip()


def is_ancestor(commit: str, ref: str) -> bool:
    return git(["merge-base", "--is-ancestor", commit, ref], check=False).returncode == 0


def changed_files(branch: str) -> list[str]:
    # Prefer the branch's own commit range relative to base_ref. For unrelated
    # histories or odd preserve refs, fall back to the tip tree.
    result = git(["diff", "--name-only", f"{base_ref}...{branch}"], check=False)
    if result.returncode == 0:
        files = [line for line in result.stdout.splitlines() if line.strip()]
    else:
        files = []
    if not files:
        result = git(["show", "--name-only", "--format=", branch], check=False)
        files = [line for line in result.stdout.splitlines() if line.strip()]
    return sorted(set(files))


def category_for(path: str) -> str:
    if path.startswith(("docs/", "README", "CHANGELOG")):
        return "docs"
    if path.startswith("tests/"):
        return "tests"
    if path.startswith("hooks/"):
        return "hooks"
    if path.startswith("scripts/"):
        return "scripts"
    if path.startswith("lib/"):
        return "lib"
    if path.startswith("packages/"):
        return "packages"
    if path.startswith((".cognitive-os/", ".claude/", ".codex/")) or path in {"cognitive-os.yaml", "Makefile", "pyproject.toml", "pytest.ini"}:
        return "config"
    return "other"


def list_branches() -> list[str]:
    raw = git(["for-each-ref", "--format=%(refname:short)", "refs/heads"]).stdout.splitlines()
    return sorted(branch for branch in raw if fnmatch.fnmatch(branch, pattern))

rows: list[dict[str, Any]] = []
for branch in list_branches():
    tip = branch_tip(branch)
    manifest = load_manifest(branch)
    files = changed_files(branch)
    categories = sorted({category_for(path) for path in files})
    tip_is_ancestor = is_ancestor(tip, base_ref)
    status = manifest.get("status") if isinstance(manifest, dict) and not manifest.get("_corrupt") else None
    manifest_exists = manifest is not None and not (isinstance(manifest, dict) and manifest.get("_corrupt"))
    mixed_scope = len(categories) > 1
    candidate_delete = tip_is_ancestor or status in {"integrated", "obsolete", "delete-approved"}
    findings: list[str] = []
    if manifest is None:
        findings.append("missing-manifest")
    elif isinstance(manifest, dict) and manifest.get("_corrupt"):
        findings.append("corrupt-manifest")
    if mixed_scope:
        findings.append("mixed-scope")
    if tip_is_ancestor:
        findings.append("already-integrated")
    else:
        findings.append("tip-exists-not-ancestor-of-base")
    if candidate_delete:
        findings.append("candidate-delete")

    rows.append(
        {
            "branch": branch,
            "tip": tip[:12],
            "base_ref": base_ref,
            "manifest_exists": manifest_exists,
            "manifest_path": str(manifest_path(branch).relative_to(project)),
            "manifest_status": status,
            "mixed_scope": mixed_scope,
            "categories": categories,
            "file_count": len(files),
            "tip_is_ancestor_of_head": tip_is_ancestor,
            "tip_exists_not_ancestor_of_head": not tip_is_ancestor,
            "candidate_delete": candidate_delete,
            "findings": findings,
        }
    )

payload = {"project": str(project), "branch_pattern": pattern, "base_ref": base_ref, "preserve_branches": rows}
if json_mode:
    print(json.dumps(payload, indent=2, sort_keys=True))
else:
    print(f"Project: {project}")
    print(f"Base ref: {base_ref}")
    if not rows:
        print(f"PASS no preserve branches matching {pattern}")
    for row in rows:
        level = "WARN" if row["findings"] else "PASS"
        print(
            f"{level} {row['branch']} tip={row['tip']} "
            f"manifest={row['manifest_exists']} categories={','.join(row['categories']) or '-'} "
            f"ancestor={row['tip_is_ancestor_of_head']} delete_candidate={row['candidate_delete']} "
            f"findings={','.join(row['findings']) or '-'}"
        )
    print(f"Result: {'WARN' if any(row['findings'] for row in rows) else 'PASS'} ({len(rows)} branch(es))")

has_findings = any(row["findings"] for row in rows)
raise SystemExit(1 if strict and has_findings else 0)
PY

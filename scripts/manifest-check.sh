#!/usr/bin/env bash
# SCOPE: os-only
# manifest-check.sh — Report status of declared dependencies vs reality.
#
# Reads manifests/dependencies.yaml via lib/manifest_loader.py, then for the
# selected profile reports each tool/MCP/python-group as OK / MISSING / SKIP.
#
# Exit codes:
#   0 — all required items present
#   1 — at least one required item missing
#   2 — invalid invocation (bad flag) or manifest validation error
#
# Usage:
#   bash scripts/manifest-check.sh                    # default profile
#   bash scripts/manifest-check.sh --profile full     # full profile
#   bash scripts/manifest-check.sh --json             # machine-readable
#   bash scripts/manifest-check.sh --manifest PATH    # override manifest path
set -euo pipefail

PROFILE="default"
OUTPUT="text"
MANIFEST_OVERRIDE=""

usage() {
  cat <<'EOF'
Usage: manifest-check.sh [--profile NAME] [--json] [--manifest PATH]

Reports status of dependencies declared in manifests/dependencies.yaml.

Options:
  --profile NAME    Profile to check: default | full (default: default)
  --json            Emit machine-readable JSON instead of human text
  --manifest PATH   Override path to manifest (default: manifests/dependencies.yaml)
  -h, --help        Show this help

Exit codes:
  0  all required items present
  1  at least one required item missing
  2  invalid invocation or manifest validation error
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      [[ -z "${2:-}" ]] && { echo "Error: --profile requires a value" >&2; exit 2; }
      PROFILE="$2"; shift 2 ;;
    --profile=*)
      PROFILE="${1#--profile=}"; shift ;;
    --json)
      OUTPUT="json"; shift ;;
    --manifest)
      [[ -z "${2:-}" ]] && { echo "Error: --manifest requires a value" >&2; exit 2; }
      MANIFEST_OVERRIDE="$2"; shift 2 ;;
    --manifest=*)
      MANIFEST_OVERRIDE="${1#--manifest=}"; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Error: unknown argument: $1" >&2
      usage >&2
      exit 2 ;;
  esac
done

case "${BASH_SOURCE[0]}" in
  */*)
    SCRIPT_DIR="${BASH_SOURCE[0]%/*}"
    ;;
  *)
    SCRIPT_DIR="."
    ;;
esac
SCRIPT_DIR="$(cd "$SCRIPT_DIR" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -n "$MANIFEST_OVERRIDE" ]]; then
  export COS_MANIFEST_PATH="$MANIFEST_OVERRIDE"
fi

cd "$REPO_ROOT"

# Delegate the actual work to a helper Python script so we get the parsed
# manifest with full validation. The shell script is the user-facing entry
# point and handles the env/exit-code contract.
PROFILE="$PROFILE" OUTPUT="$OUTPUT" python3 - <<'PYEOF'
import json
import os
import shutil
import sys

sys.path.insert(0, os.getcwd())

from lib.manifest_loader import ManifestError, load_manifest

profile_name = os.environ["PROFILE"]
output_mode = os.environ["OUTPUT"]

try:
    manifest = load_manifest()
except ManifestError as e:
    print(f"manifest-check: {e}", file=sys.stderr)
    sys.exit(2)

try:
    profile = manifest.profile(profile_name)
except ManifestError as e:
    print(f"manifest-check: {e}", file=sys.stderr)
    sys.exit(2)


def tool_status(name: str) -> str:
    return "ok" if shutil.which(name) else "missing"


report = {
    "profile": profile_name,
    "tools": [],
    "mcp_servers": [],
    "python_groups": list(profile.python_groups),
}

required_missing = 0

for tname in profile.tools_required:
    status = tool_status(tname)
    tool = manifest.tool(tname)
    report["tools"].append({
        "name": tname,
        "criticality": "required",
        "status": status,
        "install": tool.install if tool else {},
    })
    if status == "missing":
        required_missing += 1

for tname in profile.tools_recommended:
    status = tool_status(tname)
    tool = manifest.tool(tname)
    report["tools"].append({
        "name": tname,
        "criticality": "recommended",
        "status": status,
        "install": tool.install if tool else {},
    })

for mname in profile.mcp_servers_recommended:
    mcp = manifest.mcp_server(mname)
    if mcp is None:
        continue
    requires = mcp.requires_tool
    status = "ok" if (requires is None or shutil.which(requires)) else "missing"
    report["mcp_servers"].append({
        "name": mname,
        "criticality": mcp.criticality,
        "status": status,
        "requires_tool": requires,
        "register_to": mcp.register_to,
    })

if output_mode == "json":
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
else:
    print(f"Cognitive OS — manifest check (profile: {profile_name})")
    print()
    print("Tools:")
    for entry in report["tools"]:
        marker = "OK     " if entry["status"] == "ok" else "MISSING"
        crit = entry["criticality"]
        print(f"  [{marker}] {entry['name']:<14} ({crit})")
        if entry["status"] == "missing":
            install = entry["install"].get("any") or entry["install"].get("macos") or entry["install"].get("debian") or "(no install hint)"
            print(f"           install: {install}")
    print()
    print("MCP servers:")
    if not report["mcp_servers"]:
        print("  (none in this profile)")
    for entry in report["mcp_servers"]:
        marker = "OK     " if entry["status"] == "ok" else "MISSING"
        print(f"  [{marker}] {entry['name']:<14} (requires: {entry['requires_tool'] or 'none'})")
    print()
    print(f"Python groups in profile: {report['python_groups'] or '(none)'}")
    print()
    if required_missing == 0:
        print("Result: PASS — all required items present.")
    else:
        print(f"Result: FAIL — {required_missing} required item(s) missing.")

sys.exit(1 if required_missing > 0 else 0)
PYEOF

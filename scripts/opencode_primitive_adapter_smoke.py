#!/usr/bin/env python3
# SCOPE: both
"""Smoke the native OpenCode COS primitive guard plugin without model calls.

The smoke verifies the installed OpenCode binary version, loads the project-level
plugin module in Node's ESM runtime, invokes the documented `tool.execute.before`
event shape with synthetic tool metadata, and asserts that blocking primitives
write content-free `primitive-interventions.jsonl` rows.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "packages" / "opencode-adapter" / "plugins" / "cos-primitive-guard.js"
DEFAULT_JSON = ROOT / "docs" / "reports" / "opencode-primitive-adapter-smoke-latest.json"
DEFAULT_MD = ROOT / "docs" / "reports" / "opencode-primitive-adapter-smoke-latest.md"


def _opencode_version() -> tuple[str | None, str | None]:
    binary = shutil.which("opencode")
    if not binary:
        return None, None
    result = subprocess.run([binary, "--version"], text=True, capture_output=True, check=False, timeout=10)
    version = (result.stdout or result.stderr).strip().splitlines()[-1] if (result.stdout or result.stderr).strip() else "unknown"
    return binary, version


def _run_node_smoke(tmp: Path) -> dict[str, Any]:
    project = tmp / "consumer"
    plugin_dir = project / ".opencode" / "plugins"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "cos-primitive-guard.js").write_text(PLUGIN.read_text(encoding="utf-8"), encoding="utf-8")
    (plugin_dir / "package.json").write_text('{"type":"module"}\n', encoding="utf-8")
    large_file = project / "large-private-file.txt"
    large_file.write_text("x" * 41000, encoding="utf-8")

    node_script = tmp / "smoke.mjs"
    node_script.write_text(
        """
import { CosPrimitiveGuard } from './consumer/.opencode/plugins/cos-primitive-guard.js';
const root = process.env.COGNITIVE_OS_PROJECT_DIR;
const plugin = await CosPrimitiveGuard({ directory: root, worktree: root });
const blocked = {};
for (const [key, command, marker] of [
  ['destructive-git-blocker', 'git reset --hard private-branch-name', 'destructive-git-blocker'],
  ['destructive-rm-blocker', 'rm -rf private-target-dir', 'destructive-rm-blocker'],
  ['skill-router', 'pip install --upgrade private-package-name', 'skill-router'],
]) {
  try {
    await plugin['tool.execute.before'](
      { tool: 'bash', args: { command } },
      { args: { command } }
    );
    blocked[key] = false;
  } catch (err) {
    blocked[key] = String(err.message || err).includes(marker);
  }
}
await plugin['tool.execute.before'](
  { tool: 'read', args: { filePath: `${root}/large-private-file.txt` } },
  { args: { filePath: `${root}/large-private-file.txt` } }
);
console.log(JSON.stringify({ blocked }));
""".strip()
        + "\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.update({
        "COGNITIVE_OS_PROJECT_DIR": str(project),
        "COGNITIVE_OS_SESSION_ID": "opencode-smoke-session",
        "COGNITIVE_OS_TOOL_USE_ID": "opencode-smoke-tool",
    })
    result = subprocess.run(["node", str(node_script)], text=True, capture_output=True, check=False, env=env, timeout=15)
    ledger = project / ".cognitive-os" / "metrics" / "primitive-interventions.jsonl"
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()] if ledger.exists() else []
    leaked = "private-branch-name" in json.dumps(rows) or "large-private-file" in json.dumps(rows)
    return {
        "node_returncode": result.returncode,
        "node_stdout": result.stdout.strip(),
        "node_stderr_tail": result.stderr[-500:],
        "blocked": json.loads(result.stdout or "{}" ).get("blocked", {}) if result.returncode == 0 and result.stdout.strip() else {},
        "ledger_rows": rows,
        "ledger_row_count": len(rows),
        "content_free": not leaked,
    }


def build_report() -> dict[str, Any]:
    binary, version = _opencode_version()
    with tempfile.TemporaryDirectory(prefix="cos-opencode-plugin-smoke-") as td:
        node = _run_node_smoke(Path(td)) if binary else {"ledger_rows": [], "ledger_row_count": 0, "blocked": False, "content_free": False, "node_returncode": None}
    rows = node.get("ledger_rows", [])
    has_git_block = any(row.get("primitive_id") == "destructive-git-blocker" and row.get("action_kind") == "block" for row in rows)
    has_large_advise = any(row.get("primitive_id") == "large-file-advisor" and row.get("action_kind") == "advise" for row in rows)
    blocked = node.get("blocked", {}) if isinstance(node.get("blocked"), dict) else {}
    has_rm_block = any(row.get("primitive_id") == "destructive-rm-blocker" and row.get("action_kind") == "block" for row in rows)
    has_skill_block = any(row.get("primitive_id") == "skill-router" and row.get("action_kind") == "block" for row in rows)
    status = "pass" if binary and node.get("node_returncode") == 0 and all(blocked.get(key) for key in ("destructive-git-blocker", "destructive-rm-blocker", "skill-router")) and has_git_block and has_rm_block and has_skill_block and has_large_advise and node.get("content_free") else "fail"
    return {
        "schema_version": "opencode-primitive-adapter-smoke.v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "opencode": {"binary": binary, "version": version},
        "plugin": {"path": str(PLUGIN.relative_to(ROOT)), "event": "tool.execute.before"},
        "checks": {
            "plugin_loaded": node.get("node_returncode") == 0,
            "blocking_event_threw": all(blocked.get(key) for key in ("destructive-git-blocker", "destructive-rm-blocker", "skill-router")),
            "destructive_git_ledger_row": has_git_block,
            "destructive_rm_ledger_row": has_rm_block,
            "skill_router_ledger_row": has_skill_block,
            "large_file_advisory_ledger_row": has_large_advise,
            "content_free_rows": bool(node.get("content_free")),
        },
        "supported_primitives": ["destructive-git-blocker", "destructive-rm-blocker", "large-file-advisor", "skill-router"],
        "ledger_row_count": node.get("ledger_row_count", 0),
        "node_stderr_tail": node.get("node_stderr_tail", ""),
    }


def render_markdown(report: dict[str, Any]) -> str:
    checks = report["checks"]
    return "\n".join([
        "# OpenCode Primitive Adapter Smoke — Latest",
        "",
        f"Generated: {report['generated_at']}",
        f"Status: `{report['status']}`",
        f"OpenCode: `{report['opencode'].get('version')}` at `{report['opencode'].get('binary')}`",
        f"Plugin: `{report['plugin']['path']}`",
        "",
        "## Checks",
        "",
        *[f"- {key}: `{value}`" for key, value in checks.items()],
        "",
        "This smoke invokes the documented OpenCode project-plugin `tool.execute.before` event shape without model calls. It does not run a paid LLM session.",
        "",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    report = build_report()
    if not args.no_write:
        DEFAULT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        DEFAULT_MD.write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"opencode-primitive-adapter-smoke: {report['status']} version={report['opencode'].get('version')}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

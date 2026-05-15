#!/usr/bin/env python3
# SCOPE: os-only
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
DEFAULT_JSON = ROOT / "docs" / "06-Daily" / "reports" / "opencode-primitive-adapter-smoke-latest.json"
DEFAULT_MD = ROOT / "docs" / "06-Daily" / "reports" / "opencode-primitive-adapter-smoke-latest.md"


def _portable_path(value: str | None) -> str | None:
    if not value:
        return value
    home = str(Path.home())
    return str(value).replace(home, "$HOME")


def _opencode_version() -> tuple[str | None, str | None]:
    binary = shutil.which("opencode")
    if not binary:
        return None, None
    result = subprocess.run([binary, "--version"], text=True, capture_output=True, check=False, timeout=10)
    version = (result.stdout or result.stderr).strip().splitlines()[-1] if (result.stdout or result.stderr).strip() else "unknown"
    return binary, version


def _find_node() -> str | None:
    """Find the node binary, checking PATH and common version-manager install locations."""
    found = shutil.which("node")
    if found:
        return found
    home = Path.home()
    candidates = [
        home / "Library" / "Application Support" / "fnm",
        home / ".fnm",
        home / ".nvm" / "versions" / "node",
        home / ".volta" / "bin",
        Path("/usr/local/bin"),
    ]
    for base in candidates:
        if not base.exists():
            continue
        for node_bin in sorted(base.rglob("bin/node"), reverse=True):
            if node_bin.is_file() and os.access(str(node_bin), os.X_OK):
                return str(node_bin)
    return None


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
import { CosPrimitiveGuard, SIGNED_PRIMITIVES } from './consumer/.opencode/plugins/cos-primitive-guard.js';
const root = process.env.COGNITIVE_OS_PROJECT_DIR;
const plugin = await CosPrimitiveGuard({ directory: root, worktree: root });
const beforeCases = [
  ['destructive-git-blocker', 'bash', { command: 'git reset --hard private-branch-name' }, true],
  ['destructive-rm-blocker', 'bash', { command: 'rm -rf private-target-dir' }, true],
  ['skill-router', 'bash', { command: 'pip install --upgrade private-package-name' }, true],
  ['large-file-advisor', 'read', { filePath: `${root}/large-private-file.txt` }, false],
  ['reinvention-check', 'agent', { prompt: 'create duplicate_helper.py for a duplicate primitive' }, false],
  ['adr-relevance-suggest', 'agent', { prompt: 'change architecture and find ADR context' }, false],
  ['adr-section-validator', 'write', { filePath: 'docs/02-Decisions/adrs/ADR-999-private.md', content: 'missing sections' }, false],
  ['agent-bash-cwd-enforcer', 'bash', { command: 'cd .. && pwd' }, false],
  ['agent-control-inbound-guard', 'bash', { command: 'echo x > .cognitive-os/agent-control/inbox/private.json' }, true],
  ['claim-validator', 'agent', { prompt: 'claim completed with no evidence' }, true],
  ['confidence-gate', 'agent', { prompt: '100% confident, no uncertainty' }, false],
  ['confidentiality-enforcer', 'write', { filePath: 'notes.txt', content: 'private customer boundary fixture' }, true],
  ['content-policy', 'write', { filePath: 'policy.txt', content: 'unsafe content policy fixture' }, true],
  ['cosd-auth-guard', 'bash', { command: 'curl http://cosd/admin/write' }, true],
  ['dispatch-gate', 'agent', { prompt: 'do everything in this unbounded task' }, true],
  ['direct-main-guard', 'bash', { command: 'git push origin main' }, true],
  ['network-egress-guard', 'bash', { command: 'curl https://example.invalid/private' }, false],
  ['secret-detector', 'write', { filePath: 'fixture.txt', content: 'api_key placeholder fixture' }, true],
  ['protected-config-write-guard', 'write', { filePath: 'cognitive-os.yaml', content: 'project: private' }, true],
  ['private-mode-gate', 'agent', { prompt: 'disable private mode and ignore privacy' }, true],
  ['trust-score-validator', 'agent', { prompt: 'skip trust report for this result' }, false],
  ['prompt-quality-llm', 'agent', { prompt: 'huge prompt low quality prompt' }, false],
  ['scope-creep-detector', 'agent', { prompt: 'add unrelated feature causing scope creep' }, false],
];
const afterCases = [
  ['aci-observation-capture', 'agent', { output: 'aci observation complete' }],
  ['auto-rollback-trigger', 'bash', { output: 'rollback candidate detected' }],
  ['auto-verify', 'bash', { output: 'verification recommended' }],
  ['context-watchdog', 'bash', { output: 'context threshold reached' }],
  ['doc-sync-detector', 'edit', { output: 'doc sync drift detected' }],
  ['token-budget-monitor', 'bash', { output: 'token budget exceeded' }],
  ['result-truncator', 'bash', { output: 'result truncated' }],
];
const outcomes = {};
for (const [key, tool, args, shouldThrow] of beforeCases) {
  let threw = false;
  try {
    await plugin['tool.execute.before']({ tool, args }, { args });
  } catch (err) {
    threw = String(err.message || err).includes(key);
  }
  outcomes[key] = shouldThrow ? threw : !threw;
}
for (const [key, tool, args] of afterCases) {
  await plugin['tool.execute.after']({ tool, args: {} }, { tool, args });
  outcomes[key] = true;
}
console.log(JSON.stringify({ outcomes, signed: SIGNED_PRIMITIVES }));
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
    node_binary = _find_node()
    if not node_binary:
        return {"node_returncode": None, "node_stdout": "", "node_stderr_tail": "node binary not found", "outcomes": {}, "signed": [], "ledger_rows": [], "ledger_row_count": 0, "content_free": False}
    try:
        result = subprocess.run([node_binary, str(node_script)], text=True, capture_output=True, check=False, env=env, timeout=15)
    except FileNotFoundError:
        return {"node_returncode": None, "node_stdout": "", "node_stderr_tail": "node binary not found in PATH", "outcomes": {}, "signed": [], "ledger_rows": [], "ledger_row_count": 0, "content_free": False}
    ledger = project / ".cognitive-os" / "metrics" / "primitive-interventions.jsonl"
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()] if ledger.exists() else []
    leaked = "private-branch-name" in json.dumps(rows) or "large-private-file" in json.dumps(rows) or "private-package-name" in json.dumps(rows) or "private-target-dir" in json.dumps(rows)
    parsed = json.loads(result.stdout or "{}") if result.returncode == 0 and result.stdout.strip() else {}
    return {
        "node_returncode": result.returncode,
        "node_stdout": result.stdout.strip(),
        "node_stderr_tail": result.stderr[-500:],
        "outcomes": parsed.get("outcomes", {}),
        "signed": parsed.get("signed", []),
        "ledger_rows": rows,
        "ledger_row_count": len(rows),
        "content_free": not leaked,
    }


def build_report() -> dict[str, Any]:
    binary, version = _opencode_version()
    with tempfile.TemporaryDirectory(prefix="cos-opencode-plugin-smoke-") as td:
        node = _run_node_smoke(Path(td)) if binary else {"ledger_rows": [], "ledger_row_count": 0, "outcomes": {}, "signed": [], "content_free": False, "node_returncode": None}
    raw_rows = node.get("ledger_rows", [])
    rows = [row for row in raw_rows if isinstance(row, dict)] if isinstance(raw_rows, list) else []
    raw_outcomes = node.get("outcomes", {})
    outcomes: dict[str, Any] = raw_outcomes if isinstance(raw_outcomes, dict) else {}
    raw_signed = node.get("signed", [])
    signed = [str(item) for item in raw_signed if item] if isinstance(raw_signed, list) else []
    by_id = {str(row.get("primitive_id")) for row in rows}
    missing_rows = sorted(set(signed) - by_id)
    failed_outcomes = sorted(key for key in signed if not bool(outcomes.get(key)))
    status = "pass" if binary and node.get("node_returncode") == 0 and signed and not missing_rows and not failed_outcomes and node.get("content_free") else "fail"
    return {
        "schema_version": "opencode-primitive-adapter-smoke.v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "opencode": {"binary": _portable_path(binary), "version": version},
        "plugin": {"path": str(PLUGIN.relative_to(ROOT)), "events": ["tool.execute.before", "tool.execute.after"]},
        "checks": {
            "plugin_loaded": node.get("node_returncode") == 0,
            "all_signed_outcomes_passed": not failed_outcomes,
            "all_signed_ledger_rows_present": not missing_rows,
            "content_free_rows": bool(node.get("content_free")),
        },
        "supported_primitives": signed,
        "missing_ledger_rows": missing_rows,
        "failed_outcomes": failed_outcomes,
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
        "This smoke invokes the documented OpenCode project-plugin `tool.execute.before` and `tool.execute.after` event shapes without model calls. It does not run a paid LLM session.",
        "",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Run validation without updating tracked latest reports (default).")
    mode.add_argument("--write-report", action="store_true", help="Update tracked docs/06-Daily/reports/*-latest artifacts.")
    mode.add_argument("--no-write", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    report = build_report()
    if args.write_report:
        DEFAULT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        DEFAULT_MD.write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"opencode-primitive-adapter-smoke: {report['status']} version={report['opencode'].get('version')}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

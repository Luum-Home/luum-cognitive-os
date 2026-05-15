#!/usr/bin/env python3
# SCOPE: os-only
"""Audit filtered installs for dangling or scope-excluded projected hook commands.

ADR-320 guardrail: SCOPE classification is not enough. Every generated harness
projection must satisfy: if a hook is registered, the filtered install copied it
and its source SCOPE is allowed by the same install scope.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import contextlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

VALID_SCOPES = ("project", "both", "all")
VALID_HARNESSES = ("codex", "claude")
VALID_MODES = ("default", "full")


@dataclass(frozen=True)
class Finding:
    scope: str
    harness: str
    mode: str
    kind: str
    detail: str
    command: str = ""
    hook: str = ""


def _scope_allows(root: Path, rel: str, install_scope: str) -> bool:
    if install_scope == "all":
        return True
    path = root / rel
    if not path.is_file():
        return True
    head = "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:3])
    match = re.search(r"(?:# SCOPE:|<!-- SCOPE:)\s+([a-zA-Z_/-]+)", head)
    if not match:
        return True
    return match.group(1).strip() != "os-only"


def _walk_commands(node: Any) -> Iterable[str]:
    if isinstance(node, dict):
        command = node.get("command")
        if isinstance(command, str):
            yield command
        for value in node.values():
            yield from _walk_commands(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_commands(item)


def _hook_filenames_from_command(command: str) -> list[str]:
    """Return COS hook filenames referenced by a generated command string."""
    filenames: list[str] = []
    patterns = [
        r"\.cognitive-os/hooks/cos/([A-Za-z0-9_.-]+\.sh)",
        r"\$CLAUDE_PROJECT_DIR/hooks/([A-Za-z0-9_.-]+\.sh)",
        r"\$PWD/hooks/([A-Za-z0-9_.-]+\.sh)",
        r"/hooks/([A-Za-z0-9_.-]+\.sh)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, command):
            filename = match.group(1)
            if filename not in filenames:
                filenames.append(filename)
    return filenames


def _settings_path(project: Path, harness: str) -> Path:
    if harness == "codex":
        return project / ".codex" / "hooks.json"
    return project / ".claude" / "settings.json"


def _run_install(root: Path, project: Path, scope: str, harness: str, mode: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "COS_SOURCE_DIR": str(root),
            "COS_INSTALL_SCOPE": scope,
            "COGNITIVE_OS_HARNESS": harness,
            "COS_REGISTRY_FILE": str(project / ".cos-install-projection-audit-registry.json"),
        }
    )
    cmd = [sys.executable, str(root / "scripts" / "cos_init.py"), f"--{mode}", "--harness", harness]
    return subprocess.run(cmd, cwd=project, env=env, text=True, capture_output=True, timeout=120, check=False)


def _tmpdir(prefix: str, keep_tmp: bool) -> contextlib.AbstractContextManager[str]:
    if keep_tmp:
        return contextlib.nullcontext(tempfile.mkdtemp(prefix=prefix))
    return tempfile.TemporaryDirectory(prefix=prefix)


def audit_combo(root: Path, scope: str, harness: str, mode: str, keep_tmp: bool = False) -> tuple[list[Finding], dict[str, Any]]:
    findings: list[Finding] = []
    with _tmpdir("cos-install-projection-audit-", keep_tmp) as tmp:
        project = Path(tmp) / f"fixture-{scope}-{harness}-{mode}"
        project.mkdir(parents=True)
        (project / "README.md").write_text("# fixture\n", encoding="utf-8")
        result = _run_install(root, project, scope, harness, mode)
        if result.returncode != 0:
            findings.append(
                Finding(
                    scope=scope,
                    harness=harness,
                    mode=mode,
                    kind="install-failed",
                    detail=(result.stderr or result.stdout)[-2000:],
                )
            )
            return findings, {"project": str(project), "install_returncode": result.returncode}

        settings = _settings_path(project, harness)
        if not settings.is_file():
            findings.append(Finding(scope, harness, mode, "settings-missing", str(settings)))
            return findings, {"project": str(project), "install_returncode": result.returncode}

        try:
            data = json.loads(settings.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            findings.append(Finding(scope, harness, mode, "settings-invalid-json", str(exc)))
            return findings, {"project": str(project), "install_returncode": result.returncode}

        commands = list(_walk_commands(data))
        hook_refs: list[str] = []
        for command in commands:
            if "$CLAUDE_PROJECT_DIR/hooks/" in command or "$PWD/hooks/" in command:
                findings.append(
                    Finding(
                        scope,
                        harness,
                        mode,
                        "source-layout-hook-path",
                        "projected hook command points at source-layout hooks/",
                        command=command,
                    )
                )
            for filename in _hook_filenames_from_command(command):
                if filename not in hook_refs:
                    hook_refs.append(filename)
                installed = project / ".cognitive-os" / "hooks" / "cos" / filename
                if not installed.is_file():
                    findings.append(
                        Finding(
                            scope,
                            harness,
                            mode,
                            "registered-hook-missing",
                            f"registered hook is not installed at {installed.relative_to(project)}",
                            command=command,
                            hook=filename,
                        )
                    )
                source_rel = f"hooks/{filename}"
                if not (root / source_rel).is_file():
                    findings.append(
                        Finding(
                            scope,
                            harness,
                            mode,
                            "source-hook-missing",
                            f"registered hook has no source file at {source_rel}",
                            command=command,
                            hook=filename,
                        )
                    )
                if not _scope_allows(root, source_rel, scope):
                    findings.append(
                        Finding(
                            scope,
                            harness,
                            mode,
                            "registered-hook-scope-excluded",
                            f"{source_rel} is excluded by COS_INSTALL_SCOPE={scope}",
                            command=command,
                            hook=filename,
                        )
                    )

        return findings, {
            "project": str(project),
            "install_returncode": result.returncode,
            "settings": str(settings.relative_to(project)),
            "commands": len(commands),
            "hook_refs": sorted(hook_refs),
        }


def parse_csv(value: str, valid: tuple[str, ...], label: str) -> list[str]:
    items = [item.strip() for item in value.split(",") if item.strip()]
    invalid = [item for item in items if item not in valid]
    if invalid:
        raise SystemExit(f"invalid {label}: {', '.join(invalid)}; valid: {', '.join(valid)}")
    return items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=".", help="COS source checkout root")
    parser.add_argument("--scopes", default="project,both,all", help="comma-separated install scopes")
    parser.add_argument("--harnesses", default="codex,claude", help="comma-separated harnesses")
    parser.add_argument("--modes", default="default,full", help="comma-separated modes")
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    parser.add_argument("--keep-tmp", action="store_true", help="keep temporary fixture projects for debugging")
    args = parser.parse_args(argv)

    root = Path(args.project_dir).resolve()
    scopes = parse_csv(args.scopes, VALID_SCOPES, "scope")
    harnesses = parse_csv(args.harnesses, VALID_HARNESSES, "harness")
    modes = parse_csv(args.modes, VALID_MODES, "mode")

    all_findings: list[Finding] = []
    runs: list[dict[str, Any]] = []
    for scope in scopes:
        for harness in harnesses:
            for mode in modes:
                findings, summary = audit_combo(root, scope, harness, mode, keep_tmp=args.keep_tmp)
                summary.update({"scope": scope, "harness": harness, "mode": mode, "findings": len(findings)})
                runs.append(summary)
                all_findings.extend(findings)

    payload = {
        "status": "fail" if all_findings else "pass",
        "summary": {
            "runs": len(runs),
            "findings": len(all_findings),
            "scopes": scopes,
            "harnesses": harnesses,
            "modes": modes,
        },
        "runs": runs,
        "findings": [asdict(finding) for finding in all_findings],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload["summary"], indent=2, sort_keys=True))
        for finding in all_findings:
            print(f"{finding.kind}: scope={finding.scope} harness={finding.harness} mode={finding.mode} hook={finding.hook} {finding.detail}", file=sys.stderr)
    return 1 if all_findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

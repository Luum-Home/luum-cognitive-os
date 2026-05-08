#!/usr/bin/env python3
"""Audit cross-primitive ownership, registration, and ordering coherence.

Slice A is intentionally read-only. It detects contradictions but does not fix
settings, manifests, hooks, or state.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "primitive-coherence-audit/v1"
DEFAULT_MANIFEST = Path("manifests/primitive-coherence.yaml")


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    primitive: str | None = None
    surface: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.primitive:
            payload["primitive"] = self.primitive
        if self.surface:
            payload["surface"] = self.surface
        if self.details:
            payload["details"] = self.details
        return payload


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def repo_root(start: Path) -> Path:
    proc = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return start.resolve()
    return Path(proc.stdout.strip()).resolve()


def hook_name(path: str) -> str:
    return Path(path).name


def hook_chain(settings: dict[str, Any], event: str, matcher: str | None) -> list[str]:
    chain: list[str] = []
    for group in settings.get("hooks", {}).get(event, []) or []:
        group_matcher = group.get("matcher")
        if matcher and group_matcher not in {matcher, None, "*"}:
            continue
        for hook in group.get("hooks", []) or []:
            command = str(hook.get("command", ""))
            for match in re.findall(r"/hooks/([A-Za-z0-9_.-]+\.sh)", command):
                chain.append(f"hooks/{match}")
            for match in re.findall(r"\bhooks/([A-Za-z0-9_.-]+\.sh)", command):
                candidate = f"hooks/{match}"
                if candidate not in chain:
                    chain.append(candidate)
    return chain




def registered_hooks(settings: dict[str, Any]) -> set[str]:
    hooks: set[str] = set()
    for groups in (settings.get("hooks", {}) or {}).values():
        for group in groups or []:
            for hook in group.get("hooks", []) or []:
                command = str(hook.get("command", ""))
                for match in re.findall(r"/hooks/([A-Za-z0-9_.-]+\.sh)", command):
                    hooks.add(match)
                for match in re.findall(r"\bhooks/([A-Za-z0-9_.-]+\.sh)", command):
                    hooks.add(match)
    return hooks


def check_ordering(repo: Path, manifest: dict[str, Any]) -> list[Finding]:
    settings = load_yaml(repo / ".claude" / "settings.json")
    findings: list[Finding] = []
    for constraint in manifest.get("ordering_constraints", []) or []:
        event = str(constraint.get("event", ""))
        matcher = constraint.get("matcher")
        after = str(constraint.get("after", ""))
        before = str(constraint.get("before", ""))
        severity = str(constraint.get("severity", "block"))
        chain = hook_chain(settings, event, str(matcher) if matcher else None)
        if after not in chain or before not in chain:
            findings.append(
                Finding(
                    "warn",
                    "ordering-hook-missing",
                    "Ordering constraint references a hook absent from the configured hook chain.",
                    primitive=str(constraint.get("id")),
                    details={"event": event, "matcher": matcher, "after": after, "before": before, "chain": chain},
                )
            )
            continue
        if chain.index(after) > chain.index(before):
            findings.append(
                Finding(
                    severity,
                    "ordering-mutator-before-blocker",
                    "Hook ordering violates primitive coherence constraint.",
                    primitive=str(constraint.get("id")),
                    details={"event": event, "matcher": matcher, "after": after, "before": before, "chain": chain},
                )
            )
    return findings


def check_surfaces(manifest: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for surface in manifest.get("surfaces", []) or []:
        sid = str(surface.get("id", "unknown"))
        writers = [str(w) for w in surface.get("writers", []) or []]
        allowed = bool(surface.get("allowed_multi_writer", False))
        protocol = surface.get("write_protocol")
        owner = surface.get("owner")
        if not owner:
            findings.append(Finding("block", "surface-owner-missing", "Mutable surface has no owner.", surface=sid))
        if len(writers) > 1 and not allowed:
            findings.append(
                Finding(
                    "block",
                    "surface-multi-writer-without-allowance",
                    "Surface declares multiple writers but allowed_multi_writer is false.",
                    surface=sid,
                    details={"writers": writers},
                )
            )
        if len(writers) > 1 and not protocol:
            findings.append(
                Finding(
                    "block",
                    "surface-multi-writer-without-protocol",
                    "Surface declares multiple writers without a write_protocol.",
                    surface=sid,
                    details={"writers": writers},
                )
            )
    return findings


def classification_map(repo: Path, manifest: dict[str, Any]) -> dict[str, str]:
    reg = manifest.get("registration") or {}
    path = repo / str(reg.get("classification_manifest", "manifests/hook-registration-classification.yaml"))
    payload = load_yaml(path)
    return {Path(str(entry.get("path", ""))).name: str(entry.get("status", "")) for entry in payload.get("entries", []) or []}


def legacy_unregistered(repo: Path, manifest: dict[str, Any]) -> set[str]:
    reg = manifest.get("registration") or {}
    checker = repo / str(reg.get("legacy_checker", "scripts/check_hook_registration.py"))
    if not checker.exists():
        return set()
    proc = subprocess.run([sys.executable, str(checker)], cwd=str(repo), text=True, capture_output=True, check=False)
    text = proc.stdout + "\n" + proc.stderr
    return set(re.findall(r"-\s+([A-Za-z0-9_.-]+\.sh)\s+\(missing:", text))


def check_registration_disagreement(repo: Path, manifest: dict[str, Any]) -> list[Finding]:
    reg = manifest.get("registration") or {}
    intentional = set(reg.get("intentional_absent_statuses", []) or [])
    classes = classification_map(repo, manifest)
    missing = legacy_unregistered(repo, manifest)
    findings: list[Finding] = []
    for name in sorted(missing):
        status = classes.get(name)
        if status in intentional:
            findings.append(
                Finding(
                    "warn",
                    "registration-checker-classification-disagreement",
                    "Legacy registration checker reports a hook as missing even though the classification manifest marks it intentionally absent.",
                    primitive=f"hooks/{name}",
                    details={"classification_status": status},
                )
            )
        elif not status:
            findings.append(
                Finding(
                    "block",
                    "unclassified-unregistered-hook",
                    "Legacy registration checker reports an unregistered hook that has no classification entry.",
                    primitive=f"hooks/{name}",
                )
            )
    return findings




def _cycle_path(graph: dict[str, list[str]]) -> list[str] | None:
    """Return one directed cycle from graph, if present."""
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def dfs(node: str) -> list[str] | None:
        visiting.add(node)
        stack.append(node)
        for nxt in graph.get(node, []):
            if nxt in visiting:
                idx = stack.index(nxt)
                return stack[idx:] + [nxt]
            if nxt not in visited:
                found = dfs(nxt)
                if found:
                    return found
        visiting.remove(node)
        visited.add(node)
        stack.pop()
        return None

    for node in sorted(graph):
        if node not in visited:
            found = dfs(node)
            if found:
                return found
    return None




def check_classification_projection(repo: Path, manifest: dict[str, Any]) -> list[Finding]:
    """Detect classification/settings contradictions directly.

    This closes the inverse of the legacy-checker disagreement: an active hook
    must be projected, and a manual/opt-in hook must not silently appear in
    lifecycle settings unless classified as projected_elsewhere/active.
    """
    reg = manifest.get("registration") or {}
    settings = load_yaml(repo / ".claude" / "settings.json")
    registered = registered_hooks(settings)
    classes = classification_map(repo, manifest)
    active_statuses = set(reg.get("active_statuses", ["active"]) or [])
    inactive_statuses = set(reg.get("must_not_be_registered_statuses", ["manual_trigger", "future", "deprecated", "demoted"]) or [])
    findings: list[Finding] = []
    for name, status in sorted(classes.items()):
        if status in active_statuses and name not in registered:
            findings.append(
                Finding(
                    "block",
                    "active-hook-not-registered",
                    "Classification manifest marks hook active, but settings do not register it.",
                    primitive=f"hooks/{name}",
                    details={"classification_status": status},
                )
            )
        if status in inactive_statuses and name in registered:
            findings.append(
                Finding(
                    "block",
                    "inactive-hook-registered",
                    "Classification manifest marks hook manual/future/deprecated/demoted, but settings register it automatically.",
                    primitive=f"hooks/{name}",
                    details={"classification_status": status},
                )
            )
    return findings


def check_primitive_graph(manifest: dict[str, Any]) -> list[Finding]:
    """Detect declared primitive invocation cycles.

    This is intentionally based on a manifest, not a speculative shell parser.
    Static code scanning can be added later, but Slice B starts with explicit
    edges so recursion contracts are reviewable.
    """
    edges = manifest.get("primitive_edges", []) or []
    graph: dict[str, list[str]] = {}
    findings: list[Finding] = []
    for edge in edges:
        src = str(edge.get("from", "")).strip()
        dst = str(edge.get("to", "")).strip()
        if not src or not dst:
            findings.append(
                Finding(
                    "block",
                    "primitive-edge-incomplete",
                    "Primitive graph edge must declare both from and to.",
                    details={"edge": edge},
                )
            )
            continue
        if edge.get("recursion_allowed", False):
            continue
        graph.setdefault(src, []).append(dst)
        graph.setdefault(dst, graph.get(dst, []))
    cycle = _cycle_path(graph)
    if cycle:
        findings.append(
            Finding(
                "block",
                "primitive-recursion-cycle",
                "Declared primitive invocation graph contains a recursion cycle without an explicit recursion boundary.",
                primitive=cycle[0],
                details={"cycle": cycle},
            )
        )
    return findings


def check_external_tool_boundaries(manifest: dict[str, Any]) -> list[Finding]:
    """Validate third-party tool boundaries declared in the coherence manifest."""
    findings: list[Finding] = []
    required = {"tool", "owner", "license_spdx", "adapter", "recursion_boundary", "failure_policy"}
    for boundary in manifest.get("external_tool_boundaries", []) or []:
        missing = sorted(field for field in required if not boundary.get(field))
        tool = str(boundary.get("tool", "unknown"))
        if missing:
            findings.append(
                Finding(
                    "block",
                    "external-tool-boundary-incomplete",
                    "External tool boundary is missing required fields; do not consume third-party tools as implicit primitives.",
                    primitive=tool,
                    details={"missing": missing, "boundary": boundary},
                )
            )
        allowed_callers = boundary.get("allowed_callers", []) or []
        if not allowed_callers:
            findings.append(
                Finding(
                    "warn",
                    "external-tool-boundary-has-no-callers",
                    "External tool boundary declares no allowed_callers; adoption may be documented but unused.",
                    primitive=tool,
                )
            )
    return findings


def audit(repo: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = load_yaml(manifest_path)
    findings: list[Finding] = []
    findings.extend(check_ordering(repo, manifest))
    findings.extend(check_surfaces(manifest))
    findings.extend(check_registration_disagreement(repo, manifest))
    findings.extend(check_classification_projection(repo, manifest))
    findings.extend(check_primitive_graph(manifest))
    findings.extend(check_external_tool_boundaries(manifest))
    block_count = sum(1 for f in findings if f.severity == "block")
    warn_count = sum(1 for f in findings if f.severity == "warn")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "block" if block_count else "warn" if warn_count else "pass",
        "repo": str(repo),
        "manifest": str(manifest_path),
        "summary": {"block": block_count, "warn": warn_count, "findings": len(findings)},
        "findings": [f.to_dict() for f in findings],
        "policy": "Read-only. Detect contradictions; do not auto-repair primitives.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit primitive coherence across hooks, manifests, and ownership surfaces.")
    parser.add_argument("--project-dir", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    args = parser.parse_args()
    repo = repo_root(args.project_dir)
    manifest = args.manifest or (repo / DEFAULT_MANIFEST)
    report = audit(repo, manifest)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"primitive coherence audit: {report['status']}")
        for finding in report["findings"]:
            print(f"[{finding['severity']}] {finding['code']}: {finding['message']}")
    if report["summary"]["block"]:
        return 1
    if args.strict and report["summary"]["warn"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# SCOPE: os-only
"""Subagent launch preflight — ADR-203.

Validates selected subagent type against prompt-required output capabilities.
Exits:
  0 pass
  2 block / incompatible launch
  1 usage/config error
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import]
except Exception:  # pragma: no cover - exercised only in minimal envs
    yaml = None


@dataclass(frozen=True)
class PreflightResult:
    status: str
    selected_type: str
    canonical_type: str | None
    prompt_requires_write: bool
    parent_persistence_declared: bool
    write_capability: bool | None
    classification: str
    message: str
    safe_alternatives: list[str]
    matched_patterns: list[str]
    hook_payload_seen: bool = False
    tool_name: str | None = None

    @property
    def exit_code(self) -> int:
        return 0 if self.status == "pass" else 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "selected_type": self.selected_type,
            "canonical_type": self.canonical_type,
            "prompt_requires_write": self.prompt_requires_write,
            "parent_persistence_declared": self.parent_persistence_declared,
            "write_capability": self.write_capability,
            "classification": self.classification,
            "message": self.message,
            "safe_alternatives": self.safe_alternatives,
            "matched_patterns": self.matched_patterns,
            "hook_payload_seen": self.hook_payload_seen,
            "tool_name": self.tool_name,
        }


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"subagent capability manifest not found: {path}")
    text = path.read_text(encoding="utf-8")
    if yaml is None:
        raise RuntimeError("PyYAML is required to read subagent capability manifest")
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict) or "subagent_types" not in data:
        raise ValueError(f"invalid subagent capability manifest: {path}")
    return data


def normalize_type(selected_type: str, manifest: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
    wanted = selected_type.strip().lower()
    types = manifest.get("subagent_types", {}) or {}
    for name, cfg in types.items():
        aliases = [str(a).lower() for a in (cfg or {}).get("aliases", [])]
        if wanted == str(name).lower() or wanted in aliases:
            return str(name), cfg or {}
    return None, None


def find_artifact_requirements(prompt: str, manifest: dict[str, Any]) -> list[str]:
    patterns = manifest.get("artifact_requirement_patterns", []) or []
    matched: list[str] = []
    for pattern in patterns:
        try:
            if re.search(str(pattern), prompt, re.IGNORECASE):
                matched.append(str(pattern))
        except re.error:
            continue
    return matched


def has_parent_persistence(prompt: str, manifest: dict[str, Any]) -> bool:
    lowered = prompt.lower()
    for marker in manifest.get("parent_persistence_markers", []) or []:
        if str(marker).lower() in lowered:
            return True
    return False


def pass_without_type(tool_name: str | None, message: str) -> PreflightResult:
    return PreflightResult(
        status="pass",
        selected_type="",
        canonical_type=None,
        prompt_requires_write=False,
        parent_persistence_declared=False,
        write_capability=None,
        classification="no_selected_subagent_type",
        message=message,
        safe_alternatives=[],
        matched_patterns=[],
        hook_payload_seen=True,
        tool_name=tool_name,
    )


def _first_text(tool_input: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _first_type(tool_input: dict[str, Any]) -> str:
    for key in ("subagent_type", "agent_type", "type", "subagentType", "agentType"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def evaluate_hook_payload(payload: dict[str, Any], manifest: dict[str, Any]) -> PreflightResult:
    tool_name = str(payload.get("tool_name") or payload.get("tool") or "")
    if tool_name and tool_name not in {"Agent", "task", "delegate"}:
        return pass_without_type(tool_name, "Not an Agent launch payload; subagent capability preflight skipped.")
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    selected_type = _first_type(tool_input)
    if not selected_type:
        return pass_without_type(tool_name or None, "Agent launch did not expose selected subagent type; capability preflight passed advisory-only.")
    prompt = _first_text(tool_input, ["prompt", "description", "task", "instructions", "message"] )
    result = evaluate(selected_type, prompt, manifest)
    return PreflightResult(
        status=result.status,
        selected_type=result.selected_type,
        canonical_type=result.canonical_type,
        prompt_requires_write=result.prompt_requires_write,
        parent_persistence_declared=result.parent_persistence_declared,
        write_capability=result.write_capability,
        classification=result.classification,
        message=result.message,
        safe_alternatives=result.safe_alternatives,
        matched_patterns=result.matched_patterns,
        hook_payload_seen=True,
        tool_name=tool_name or None,
    )


def evaluate(selected_type: str, prompt: str, manifest: dict[str, Any]) -> PreflightResult:
    canonical, cfg = normalize_type(selected_type, manifest)
    matched = find_artifact_requirements(prompt, manifest)
    requires_write = bool(matched)
    parent_persistence = has_parent_persistence(prompt, manifest)

    if cfg is None:
        policy = (manifest.get("default_policy", {}) or {}).get("unknown_type", "block")
        status = "block" if policy == "block" else "pass"
        return PreflightResult(
            status=status,
            selected_type=selected_type,
            canonical_type=None,
            prompt_requires_write=requires_write,
            parent_persistence_declared=parent_persistence,
            write_capability=None,
            classification="unknown_subagent_type",
            message=f"Unknown subagent type '{selected_type}'. Declare it in manifests/subagent-capabilities.yaml before launch.",
            safe_alternatives=["general-purpose", "worker"],
            matched_patterns=matched,
        )

    can_write = bool(cfg.get("can_write", False))
    alternatives = [str(x) for x in cfg.get("safe_alternatives", []) or []]
    parent_allowed = bool(cfg.get("parent_persistence_allowed", False))

    if requires_write and not can_write:
        if parent_persistence and parent_allowed:
            return PreflightResult(
                status="pass",
                selected_type=selected_type,
                canonical_type=canonical,
                prompt_requires_write=True,
                parent_persistence_declared=True,
                write_capability=False,
                classification="parent_persistence_declared",
                message=(
                    f"{selected_type} is read-only, but launch is allowed because parent/orchestrator "
                    "persistence is explicitly declared. Child must return result_only."
                ),
                safe_alternatives=alternatives,
                matched_patterns=matched,
            )
        return PreflightResult(
            status="block",
            selected_type=selected_type,
            canonical_type=canonical,
            prompt_requires_write=True,
            parent_persistence_declared=parent_persistence,
            write_capability=False,
            classification="capability_contract_mismatch",
            message=(
                f"BLOCK launch: {selected_type} cannot write artifacts. "
                f"Use {'/'.join(alternatives) if alternatives else 'a writer-capable subagent'} "
                "or change output mode to result_only with explicit parent persistence."
            ),
            safe_alternatives=alternatives,
            matched_patterns=matched,
        )

    return PreflightResult(
        status="pass",
        selected_type=selected_type,
        canonical_type=canonical,
        prompt_requires_write=requires_write,
        parent_persistence_declared=parent_persistence,
        write_capability=can_write,
        classification="compatible_launch",
        message="Subagent launch capability contract satisfied.",
        safe_alternatives=alternatives,
        matched_patterns=matched,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preflight subagent type against prompt output requirements.")
    parser.add_argument("--type", "--subagent-type", dest="subagent_type")
    parser.add_argument("--prompt", default="")
    parser.add_argument("--prompt-file")
    parser.add_argument("--hook-json-file", type=Path, help="Evaluate a native hook payload containing tool_name/tool_input")
    parser.add_argument("--manifest", type=Path, default=repo_root() / "manifests" / "subagent-capabilities.yaml")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    prompt = args.prompt
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    try:
        manifest = load_manifest(args.manifest)
        if args.hook_json_file:
            hook_payload = json.loads(args.hook_json_file.read_text(encoding="utf-8"))
            result = evaluate_hook_payload(hook_payload, manifest)
        else:
            if not args.subagent_type:
                raise ValueError("--type is required unless --hook-json-file is provided")
            result = evaluate(args.subagent_type, prompt, manifest)
    except Exception as exc:
        payload = {"status": "error", "message": str(exc)}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        stream = sys.stderr if result.status == "block" else sys.stdout
        print(result.message, file=stream)
        if result.status == "block" and result.safe_alternatives:
            print(f"Safe alternatives: {', '.join(result.safe_alternatives)}", file=stream)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())

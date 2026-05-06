#!/usr/bin/env python3
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
    parser.add_argument("--type", "--subagent-type", dest="subagent_type", required=True)
    parser.add_argument("--prompt", default="")
    parser.add_argument("--prompt-file")
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

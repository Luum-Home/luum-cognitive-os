#!/usr/bin/env python3
# SCOPE: both
"""Project Cognitive OS shell/CI command surfaces into a consumer project."""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any

import yaml

COS_SOURCE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = COS_SOURCE_DIR / "manifests" / "shell-ci-projection.yaml"


def rel_symlink_target(driver: Path, canonical: Path) -> str:
    return os.path.relpath(canonical, start=driver.parent)


def load_manifest(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def project_command(source_root: Path, project_dir: Path, command: dict[str, Any], canonical_root: Path, driver_root: Path) -> dict[str, str]:
    source_rel = command["path"]
    source = source_root / source_rel
    if not source.is_file():
        raise FileNotFoundError(source_rel)
    canonical = canonical_root / source.name
    driver = driver_root / source.name
    canonical.parent.mkdir(parents=True, exist_ok=True)
    driver.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, canonical)
    if command.get("executable", False):
        canonical.chmod(canonical.stat().st_mode | 0o111)
    if driver.exists() or driver.is_symlink():
        driver.unlink()
    driver.symlink_to(rel_symlink_target(driver, canonical))
    return {
        "source": source_rel,
        "canonical_path": canonical.relative_to(project_dir).as_posix(),
        "driver_path": driver.relative_to(project_dir).as_posix(),
    }


def render_workflow(commands: list[str]) -> str:
    syntax_lines = []
    for command in commands:
        if command.endswith(".sh") or command == "scripts/cos":
            syntax_lines.append(f"bash -n {command}")
        elif command.endswith(".py"):
            syntax_lines.append(f"python3 -m py_compile {command}")
    syntax = "\n          ".join(syntax_lines) if syntax_lines else "echo no shell-ci commands"
    return f"""name: Cognitive OS Shell CI

on:
  workflow_dispatch:
  pull_request:

jobs:
  cognitive-os-shell-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: '3.x'
      - name: Validate projected Cognitive OS shell/CI commands
        run: |
          {syntax}
"""


def project_shell_ci(project_dir: Path, profile: str, manifest_path: Path = DEFAULT_MANIFEST, source_root: Path = COS_SOURCE_DIR) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    profile_data = manifest.get("profiles", {}).get(profile)
    if not profile_data:
        raise ValueError(f"unknown shell/CI projection profile: {profile}")
    canonical_root = project_dir / profile_data.get("canonical_root", ".cognitive-os/scripts/cos")
    driver_root = project_dir / profile_data.get("driver_root", "scripts")
    projected = [project_command(source_root, project_dir, command, canonical_root, driver_root) for command in manifest.get("commands", [])]

    workflow_root = project_dir / profile_data.get("workflow_root", ".github/workflows")
    workflow_root.mkdir(parents=True, exist_ok=True)
    workflows = []
    for workflow in manifest.get("workflows", []):
        path = project_dir / workflow["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_workflow(workflow.get("required_commands", [])), encoding="utf-8")
        workflows.append(path.relative_to(project_dir).as_posix())

    meta = {
        "profile": profile,
        "commands_projected": len(projected),
        "projected": projected,
        "workflows": workflows,
    }
    meta_path = project_dir / ".cognitive-os" / "shell-ci-projection.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return meta


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Project Cognitive OS shell/CI command surfaces into a consumer project")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--profile", choices=("default", "full"), default="default")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    meta = project_shell_ci(Path(args.project_dir).resolve(), args.profile, Path(args.manifest).resolve())
    print(json.dumps(meta if args.json else {"projected": meta["commands_projected"], "workflows": meta["workflows"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

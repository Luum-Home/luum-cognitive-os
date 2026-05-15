#!/usr/bin/env python3
"""Generate the shared harness projection registry used by Bash/Python/Go UX.

Input:  manifests/harness-projection.yaml
Output: manifests/harness-projection-registry.json
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "manifests" / "harness-projection.yaml"
TARGET = REPO_ROOT / "manifests" / "harness-projection-registry.json"

# Keep first-run UX order stable while the YAML also carries planned/provider items.
IMPLEMENTED_ORDER = [
    "claude",
    "codex",
    "agents-md",
    "opencode",
    "vscode-copilot",
    "cursor",
    "qwen-code",
    "kimi-code",
    "gemini-cli",
    "warp",
    "amp-code",
    "jetbrains-junie",
    "qoder",
    "factory-droid",
    "cline",
    "continue-dev",
    "kilo-code",
    "zed-ai",
    "augment-code",
    "goose",
    "aider",
    "shell-ci",
]

RUNTIME_SMOKE_COMMANDS = {
    "cursor": ["cursor", "--version"],
    "qwen-code": ["qwen", "--version"],
    "gemini-cli": ["gemini", "--version"],
    "opencode": ["opencode", "--version"],
}


def main() -> int:
    source = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    by_id: dict[str, dict[str, Any]] = {str(row["id"]): row for row in source.get("harnesses", [])}
    missing = [hid for hid in IMPLEMENTED_ORDER if hid not in by_id]
    if missing:
        raise SystemExit(f"implemented order references missing harnesses: {missing}")

    ordered_ids = IMPLEMENTED_ORDER + sorted(hid for hid in by_id if hid not in IMPLEMENTED_ORDER)
    harnesses = []
    for hid in ordered_ids:
        row = by_id[hid]
        settings_paths = [str(path) for path in (row.get("settings_paths") or [])]
        harnesses.append(
            {
                "id": hid,
                "display_name": row.get("display_name", hid),
                "status": row.get("status", "unsupported"),
                "projection_mode": row.get("projection_mode", "unknown"),
                "proof_level": row.get("proof_level", "none"),
                "settings_paths": settings_paths,
                "primary_settings_path": settings_paths[0] if settings_paths else ".cognitive-os/install-meta.json",
                "runtime_smoke_command": RUNTIME_SMOKE_COMMANDS.get(hid, []),
                "next_action": row.get("next_action", ""),
            }
        )

    payload = {
        "schema_version": "harness-projection-registry.v1",
        "source": SOURCE.relative_to(REPO_ROOT).as_posix(),
        "implemented_order": IMPLEMENTED_ORDER,
        "harnesses": harnesses,
    }
    TARGET.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"wrote {TARGET.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

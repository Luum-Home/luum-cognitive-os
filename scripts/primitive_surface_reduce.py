#!/usr/bin/env python3
# SCOPE: os-only
"""Plan and apply safe surface reductions for COS agentic primitives.

The reducer is deliberately conservative. It never deletes implementation
files. In `--apply-safe` mode for hooks it only archives unregistered root-level
hook aliases/files that are explicitly demoted in `manifests/reduction-demotions.json`
and have no test coverage signal. Everything else is reported as a plan item.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.script_io import load_json_or_empty as load_json
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.script_io import read_text as read_text


@dataclass(frozen=True)
class ReductionAction:
    family: str
    path: str
    action: str
    safe_to_apply: bool
    reason: str
    destination: str | None = None


def repo_files(root: Path, pattern: str) -> list[Path]:
    return sorted(path for path in root.glob(pattern) if path.is_file() or path.is_symlink())


def load_registered_hooks(root: Path) -> set[str]:
    data = load_json(root / ".claude" / "settings.json")
    registered: set[str] = set()
    for entries in data.get("hooks", {}).values():
        for entry in entries or []:
            for hook in entry.get("hooks", []) or []:
                for match in re.findall(r"hooks/([A-Za-z0-9_.-]+\.sh)", hook.get("command", "")):
                    registered.add(match)
    return registered


def load_demotions(root: Path) -> set[tuple[str, str]]:
    data = load_json(root / "manifests" / "reduction-demotions.json")
    rows: set[tuple[str, str]] = set()
    for item in data.get("demotions", []):
        if isinstance(item, dict) and item.get("family") and item.get("path"):
            rows.add((str(item["family"]), str(item["path"])))
    return rows


def load_optional_aliases(root: Path) -> set[tuple[str, str]]:
    data = load_json(root / "manifests" / "optional-hook-aliases.json")
    rows: set[tuple[str, str]] = set()
    for item in data.get("aliases", []):
        if isinstance(item, dict) and item.get("family") and item.get("path"):
            rows.add((str(item["family"]), str(item["path"])))
    return rows


def test_corpus(root: Path) -> str:
    chunks: list[str] = []
    for path in repo_files(root, "tests/**/*.py"):
        chunks.append(path.as_posix())
        chunks.append(read_text(path))
    return "\n".join(chunks)


def has_test_signal(corpus: str, name: str, rel_path: str) -> bool:
    name_pattern = rf"(?<![A-Za-z0-9_.-]){re.escape(name)}(?![A-Za-z0-9_.-])"
    path_pattern = rf"(?<![A-Za-z0-9_./-]){re.escape(rel_path)}(?![A-Za-z0-9_./-])"
    return bool(re.search(name_pattern, corpus) or re.search(path_pattern, corpus))


def archive_destination(root: Path, rel_path: str) -> Path:
    return root / "archive" / "primitive-surface" / rel_path


def is_cognitive_os_root(root: Path) -> bool:
    """Return True only for the Cognitive OS source repo, not installed projects.

    Installed target projects can legitimately contain `cognitive-os.yaml`,
    `.claude/settings.json`, and symlinked hooks. Surface reduction is a
    maintainer operation over the OS primitive source itself, so the CLI also
    requires source-repo-only files.
    """
    required = (
        root / "cognitive-os.yaml",
        root / "scripts" / "primitive_surface_reduce.py",
        root / "scripts" / "primitive_gap_snapshot.py",
        root / "manifests" / "reduction-demotions.json",
        root / "manifests" / "optional-hook-aliases.json",
        root / "docs" / "business" / "durable-product-master-plan.md",
    )
    return all(path.exists() for path in required)


def plan_hooks(root: Path) -> list[ReductionAction]:
    registered = load_registered_hooks(root)
    demotions = load_demotions(root)
    optional_aliases = load_optional_aliases(root)
    tests = test_corpus(root)
    actions: list[ReductionAction] = []
    for path in repo_files(root, "hooks/*.sh"):
        rel = path.relative_to(root).as_posix()
        name = path.name
        is_registered = name in registered
        is_demoted = ("hooks", rel) in demotions
        is_tested = has_test_signal(tests, name, rel)
        is_symlink = path.is_symlink()
        is_optional_alias = ("hooks", rel) in optional_aliases

        if is_registered or is_optional_alias:
            continue
        if is_demoted and not is_tested:
            dest = archive_destination(root, rel).relative_to(root).as_posix()
            actions.append(
                ReductionAction(
                    family="hooks",
                    path=rel,
                    action="archive-demoted-hook",
                    safe_to_apply=True,
                    reason="unregistered root hook is explicitly demoted and has no test coverage signal",
                    destination=dest,
                )
            )
        elif is_demoted:
            actions.append(
                ReductionAction(
                    family="hooks",
                    path=rel,
                    action="keep-demoted-tested-hook",
                    safe_to_apply=False,
                    reason="demoted hook has test coverage signal; keep implementation until owner reviews tests",
                )
            )
        elif is_symlink:
            actions.append(
                ReductionAction(
                    family="hooks",
                    path=rel,
                    action="review-optional-alias",
                    safe_to_apply=False,
                    reason="unregistered symlink may be an optional package alias; review package ownership before removing alias",
                )
            )
    return actions


def apply_actions(root: Path, actions: list[ReductionAction]) -> list[ReductionAction]:
    applied: list[ReductionAction] = []
    for action in actions:
        if not action.safe_to_apply or not action.destination:
            continue
        src = root / action.path
        dst = root / action.destination
        if not src.exists() and not src.is_symlink():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() or dst.is_symlink():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            dst = dst.with_name(f"{dst.stem}-{stamp}{dst.suffix}")
        shutil.move(str(src), str(dst))
        applied.append(
            ReductionAction(
                family=action.family,
                path=action.path,
                action=action.action,
                safe_to_apply=True,
                reason=action.reason,
                destination=dst.relative_to(root).as_posix(),
            )
        )
    return applied


def write_markdown(actions: list[ReductionAction], applied: list[ReductionAction], path: Path) -> None:
    lines = [
        "# Primitive Surface Reduction Plan — Latest",
        "",
        f"Generated actions: {len(actions)}",
        f"Applied safe actions: {len(applied)}",
        "",
        "| Family | Path | Action | Safe | Destination | Reason |",
        "|---|---|---|---:|---|---|",
    ]
    for action in actions:
        reason = action.reason.replace("|", "\\|")
        lines.append(
            f"| {action.family} | `{action.path}` | {action.action} | {str(action.safe_to_apply).lower()} | "
            f"{action.destination or ''} | {reason} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan/apply safe primitive surface reductions")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--family", choices=("hooks",), default="hooks")
    parser.add_argument("--plan", action="store_true", help="Generate a plan only. This is the default.")
    parser.add_argument("--apply-safe", action="store_true", help="Apply only mechanically safe reductions.")
    parser.add_argument("--json-out", default="docs/reports/primitive-surface-reduction-latest.json")
    parser.add_argument("--md-out", default="docs/reports/primitive-surface-reduction-latest.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_dir).resolve()
    if not is_cognitive_os_root(root):
        print(
            json.dumps(
                {
                    "error": "primitive_surface_reduce.py is os-only; refusing to run outside the Cognitive OS source repo",
                    "project_dir": str(root),
                },
                sort_keys=True,
            )
        )
        return 2
    actions = plan_hooks(root)
    applied: list[ReductionAction] = []
    if args.apply_safe:
        applied = apply_actions(root, actions)
    payload = {
        "family": args.family,
        "mode": "apply-safe" if args.apply_safe else "plan",
        "actions": [asdict(action) for action in actions],
        "applied": [asdict(action) for action in applied],
    }
    json_path = root / args.json_out
    md_path = root / args.md_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(actions, applied, md_path)
    print(json.dumps({"actions": len(actions), "applied": len(applied), "json": str(json_path), "markdown": str(md_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# SCOPE: os-only
"""Run an isolated smoke test for the skill lifecycle promotion ladder.

The smoke simulates a real sandbox skill that crosses the promotion threshold,
then proves the doctrine proposer writes reviewable artifacts and logs metrics
without moving the skill into the canon.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.doctrine_proposer import build_doctrine_proposals, write_markdown


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def run_smoke() -> dict[str, object]:
    tmp = Path(tempfile.mkdtemp(prefix="cos-skill-lifecycle-smoke-"))
    try:
        skill_path = tmp / ".cognitive-os" / "skills" / "auto-generated" / "realistic-sandbox" / "SKILL.md"
        _write(
            skill_path,
            """---
name: realistic-sandbox
auto-generated: true
status: sandbox
---
# Realistic sandbox

Smoke-only sandbox skill.
""",
        )
        _write_jsonl(
            tmp / ".cognitive-os" / "metrics" / "skill-invocations.jsonl",
            [
                {"timestamp": "2026-05-05T12:00:00+00:00", "payload": {"skill_name": "realistic-sandbox"}}
                for _ in range(50)
            ],
        )
        _write_jsonl(
            tmp / ".cognitive-os" / "metrics" / "skill-feedback.jsonl",
            [{"timestamp": "2026-05-05T12:01:00Z", "skill": "realistic-sandbox", "success": True} for _ in range(5)],
        )

        proposals = build_doctrine_proposals(project_root=tmp, boring_reliability={}, self_improvement_plan={})
        written = write_markdown(tmp, proposals)
        markdown = written.read_text(encoding="utf-8")
        log_path = tmp / ".cognitive-os" / "metrics" / "lifecycle-promotion-proposals.jsonl"
        canon_path = tmp / ".cognitive-os" / "skills" / "cos" / "realistic-sandbox" / "SKILL.md"
        lifecycle = next((p for p in proposals if p.proposal_id == "activate-skill-lifecycle-promotion-ladder"), None)
        checks = {
            "proposal_generated": lifecycle is not None,
            "proposal_mentions_skill": "realistic-sandbox" in markdown,
            "runtime_effect_none": "runtime_effect: none" in markdown,
            "proposal_logged": log_path.exists() and "activate-skill-lifecycle-promotion-ladder" in log_path.read_text(encoding="utf-8"),
            "sandbox_skill_still_exists": skill_path.exists(),
            "canon_not_mutated": not canon_path.exists(),
        }
        return {
            "status": "pass" if all(checks.values()) else "fail",
            "tmpdir": str(tmp),
            "written_to": str(written),
            "checks": checks,
        }
    finally:
        if "--keep-tmp" not in sys.argv:
            shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    report = run_smoke()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

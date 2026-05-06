from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from lib.skill_lifecycle_promoter import build_skill_lifecycle_report


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _append_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_sandbox_skill_crossing_threshold_generates_advisory_proposal(tmp_path: Path) -> None:
    _write(
        tmp_path / ".cognitive-os" / "skills" / "auto-generated" / "triage-flaky-tests" / "SKILL.md",
        """---
name: triage-flaky-tests
auto-generated: true
status: sandbox
---
# Triage flaky tests
""",
    )
    invocations = [
        {
            "timestamp": "2026-05-05T12:00:00+00:00",
            "source": "skill-invocation-logger",
            "event_type": "skill.invoked",
            "payload": {"skill_name": "triage-flaky-tests"},
        }
        for _ in range(50)
    ]
    feedback = [
        {"timestamp": "2026-05-05T12:01:00Z", "skill": "triage-flaky-tests", "success": True}
        for _ in range(5)
    ]
    _append_jsonl(tmp_path / ".cognitive-os" / "metrics" / "skill-invocations.jsonl", invocations)
    _append_jsonl(tmp_path / ".cognitive-os" / "metrics" / "skill-feedback.jsonl", feedback)

    report = build_skill_lifecycle_report(tmp_path, now=datetime(2026, 5, 6, tzinfo=timezone.utc))

    assert report.status == "proposals_available"
    assert len(report.promotion_candidates) == 1
    candidate = report.promotion_candidates[0]
    assert candidate.skill_name == "triage-flaky-tests"
    assert candidate.from_state == "sandbox"
    assert candidate.proposed_state == "advisory"
    assert candidate.invocation_count == 50
    assert candidate.success_rate == 1.0


def test_sandbox_skill_without_judged_usefulness_does_not_promote(tmp_path: Path) -> None:
    _write(
        tmp_path / "skills" / "auto-generated" / "no-feedback" / "SKILL.md",
        """---
name: no-feedback
auto-generated: true
---
# No feedback
""",
    )
    _append_jsonl(
        tmp_path / ".cognitive-os" / "metrics" / "skill-invocations.jsonl",
        [
            {
                "timestamp": "2026-05-05T12:00:00+00:00",
                "payload": {"skill_name": "no-feedback"},
            }
            for _ in range(50)
        ],
    )

    report = build_skill_lifecycle_report(tmp_path, now=datetime(2026, 5, 6, tzinfo=timezone.utc))

    assert report.promotion_candidates == []


def test_stale_advisory_skill_generates_demotion_proposal(tmp_path: Path) -> None:
    _write(
        tmp_path / "skills" / "old-advisory" / "SKILL.md",
        """---
name: old-advisory
lifecycle_state: advisory
---
# Old advisory
""",
    )

    report = build_skill_lifecycle_report(tmp_path, now=datetime(2026, 5, 6, tzinfo=timezone.utc))

    assert len(report.demotion_candidates) == 1
    assert report.demotion_candidates[0].proposed_state == "demoted"


def test_advisory_skill_used_inside_demotion_window_is_not_demoted(tmp_path: Path) -> None:
    _write(
        tmp_path / "skills" / "recent-advisory" / "SKILL.md",
        """---
name: recent-advisory
lifecycle_state: advisory
---
# Recent advisory
""",
    )
    _append_jsonl(
        tmp_path / ".cognitive-os" / "metrics" / "skill-invocations.jsonl",
        [
            {
                "timestamp": "2026-03-07T12:00:00+00:00",
                "payload": {"skill_name": "recent-advisory"},
            }
        ],
    )

    report = build_skill_lifecycle_report(tmp_path, now=datetime(2026, 5, 6, tzinfo=timezone.utc))

    assert report.demotion_candidates == []


def test_advisory_skill_used_outside_demotion_window_is_demoted(tmp_path: Path) -> None:
    _write(
        tmp_path / "skills" / "stale-advisory" / "SKILL.md",
        """---
name: stale-advisory
lifecycle_state: advisory
---
# Stale advisory
""",
    )
    _append_jsonl(
        tmp_path / ".cognitive-os" / "metrics" / "skill-invocations.jsonl",
        [
            {
                "timestamp": "2026-01-01T12:00:00+00:00",
                "payload": {"skill_name": "stale-advisory"},
            }
        ],
    )

    report = build_skill_lifecycle_report(tmp_path, now=datetime(2026, 5, 6, tzinfo=timezone.utc))

    assert [candidate.skill_name for candidate in report.demotion_candidates] == ["stale-advisory"]


def test_malformed_skill_frontmatter_does_not_break_scan(tmp_path: Path) -> None:
    _write(
        tmp_path / "skills" / "bad-frontmatter" / "SKILL.md",
        '---\nname: bad-frontmatter\ntrigger: "\\s"\n---\n# Bad frontmatter\n',
    )

    report = build_skill_lifecycle_report(tmp_path, now=datetime(2026, 5, 6, tzinfo=timezone.utc))

    assert report.status == "pass"

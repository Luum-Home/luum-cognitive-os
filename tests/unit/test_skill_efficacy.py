from lib.skill_efficacy import SkillRun, format_markdown, summarize_runs, task_fingerprint


def test_task_fingerprint_is_stable() -> None:
    assert task_fingerprint(" Fix   Auth ") == task_fingerprint("fix auth")


def test_summarize_runs_computes_paired_delta() -> None:
    fp = task_fingerprint("fix bug")
    summaries = summarize_runs(
        [
            SkillRun("debug-skill", fp, True, cost_usd=0.2, latency_seconds=10, tool_calls=4, skill_enabled=True),
            SkillRun("debug-skill", fp, False, cost_usd=0.1, latency_seconds=8, tool_calls=3, skill_enabled=False),
        ]
    )

    summary = summaries[0]
    assert summary.skill_name == "debug-skill"
    assert summary.paired_baselines == 1
    assert summary.task_success_delta == 1.0
    assert summary.cost_delta_usd == 0.1
    assert summary.verdict == "high-value"


def test_format_markdown_handles_no_data() -> None:
    report = format_markdown([])

    assert "Skill Efficacy Report" in report
    assert "no-data" in report

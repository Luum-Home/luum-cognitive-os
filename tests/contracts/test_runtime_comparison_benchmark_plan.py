from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PLAN = PROJECT_ROOT / "docs" / "architecture" / "plans" / "runtime-comparison-benchmark-plan.md"


def _table_rows(markdown: str, heading: str) -> list[list[str]]:
    lines = markdown.splitlines()
    start = lines.index(heading)
    rows: list[list[str]] = []
    for line in lines[start + 1 :]:
        if line.startswith("## ") or line.startswith("### "):
            break
        if not line.startswith("|") or "---" in line:
            continue
        rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


def test_benchmark_plan_covers_required_runtime_surfaces() -> None:
    text = PLAN.read_text(encoding="utf-8")
    rows = _table_rows(text, "### Environments")
    environments = {row[0] for row in rows[1:]}

    assert environments == {
        "Developer workstation",
        "EC2 / VM",
        "Container",
        "Kubernetes pod",
        "Clustered workers",
    }


def test_benchmark_plan_compares_vanilla_and_cos_harnesses() -> None:
    text = PLAN.read_text(encoding="utf-8")
    rows = _table_rows(text, "### Tool Configurations")
    configs = {row[0] for row in rows[1:]}

    assert {
        "Claude Code vanilla",
        "Codex vanilla",
        "Claude Code + Cognitive OS",
        "Codex + Cognitive OS",
        "OpenCode vanilla / OpenCode + COS",
        "Agent Zero",
        "OpenClaw / Pi",
        "Hermes Agent",
        "GGA",
    }.issubset(configs)


def test_benchmark_plan_requires_outcome_not_speed_only() -> None:
    text = PLAN.read_text(encoding="utf-8")

    speed_index = text.index("### Speed and Cost")
    quality_index = text.index("### Quality")
    confidence_index = text.index("### Operational Confidence")
    durability_index = text.index("### Durability")

    assert speed_index < quality_index < confidence_index < durability_index
    assert "Do not benchmark only cold-start speed and call it product value" in text
    assert "quality_gates_passed" in text
    assert "path_portability_passed" in text


def test_benchmark_plan_is_linked_from_runtime_plan_and_docs() -> None:
    runtime_plan = (
        PROJECT_ROOT / "docs" / "architecture" / "plans" / "headless-clustered-runtime-plan.md"
    ).read_text(encoding="utf-8")
    docs_readme = (PROJECT_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    checklist = (PROJECT_ROOT / "docs" / "business" / "master-plan-checklist.md").read_text(
        encoding="utf-8"
    )

    assert runtime_plan.count("runtime-comparison-benchmark-plan.md") == 1
    assert docs_readme.count("runtime-comparison-benchmark-plan.md") == 1
    assert checklist.count("runtime-comparison-benchmark-plan.md") == 1

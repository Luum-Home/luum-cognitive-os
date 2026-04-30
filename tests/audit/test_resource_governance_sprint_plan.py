from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "docs" / "architecture" / "plans" / "test-resource-governance-sprint.md"
ADR_073 = ROOT / "docs" / "adrs" / "ADR-073-test-architecture-role-registry.md"


def _section_lines(markdown: str, heading: str) -> list[str]:
    lines = markdown.splitlines()
    try:
        start = lines.index(heading) + 1
    except ValueError:
        return []
    out: list[str] = []
    for line in lines[start:]:
        if line.startswith("## ") or line.startswith("### "):
            break
        if line.strip():
            out.append(line.strip())
    return out


def _numbered_items(markdown: str, heading: str) -> list[str]:
    items: list[str] = []
    for line in _section_lines(markdown, heading):
        if ". **" not in line:
            continue
        _, rest = line.split(". **", 1)
        label, _ = rest.split("**", 1)
        items.append(label)
    return items


def _implementation_phase_ids(markdown: str) -> list[str]:
    return [
        line.split(" — ", 1)[0].replace("### ", "").strip()
        for line in markdown.splitlines()
        if line.startswith("### RG-")
    ]


def test_resource_governance_sprint_plan_has_expected_execution_model() -> None:
    text = PLAN.read_text(encoding="utf-8")

    assert _numbered_items(text, "## Resource dimensions") == [
        "CPU / worker count",
        "Wall-clock time",
        "Docker / testcontainers",
        "Memory pressure",
        "Cost-bearing evals",
        "Artifact growth",
    ]
    assert _implementation_phase_ids(text) == ["RG-1", "RG-2", "RG-3", "RG-4"]


def test_resource_governance_sprint_plan_keeps_role_boundaries() -> None:
    text = PLAN.read_text(encoding="utf-8")
    non_goals = "\n".join(_section_lines(text, "## Non-goals"))
    ownership = "\n".join(_section_lines(text, "## Canonical ownership"))

    assert "Do not reintroduce lane selection in bash" in non_goals
    assert "Do not make optional/cost-bearing lanes part of the default broad sweep" in non_goals
    assert "Lane selection | `.cognitive-os/test-lanes.yaml` + `cos-test`" in ownership
    assert "Persistent reporting | `scripts/pytest-with-summary.sh`" in ownership


def test_adr_073_links_resource_governance_sprint() -> None:
    text = ADR_073.read_text(encoding="utf-8")
    assert "docs/architecture/plans/test-resource-governance-sprint.md" in text
    assert "Resource governance is intentionally not solved in this ADR" in text

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ADR = PROJECT_ROOT / "docs" / "architecture" / "adrs" / "027-headless-clustered-runtime-direction.md"
PLAN = PROJECT_ROOT / "docs" / "architecture" / "plans" / "headless-clustered-runtime-plan.md"


def _headings(markdown: str, level: int) -> list[str]:
    prefix = "#" * level + " "
    return [line.removeprefix(prefix).strip() for line in markdown.splitlines() if line.startswith(prefix)]


def _extract_mermaid_edges(markdown: str) -> list[tuple[str, str]]:
    in_mermaid = False
    edges: list[tuple[str, str]] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped == "```mermaid":
            in_mermaid = True
            continue
        if in_mermaid and stripped == "```":
            break
        if in_mermaid and " --> " in stripped:
            left, right = stripped.split(" --> ", 1)
            edges.append((left.split("[", 1)[0].strip(), right.split("[", 1)[0].strip()))
    return edges


def test_headless_runtime_direction_encodes_runtime_flow() -> None:
    text = ADR.read_text(encoding="utf-8")

    edges = _extract_mermaid_edges(text)

    assert edges == [
        ("A", "B"),
        ("B", "C"),
        ("C", "D"),
        ("D", "E"),
        ("E", "F"),
        ("F", "G"),
        ("G", "H"),
        ("B", "I"),
    ]


def test_headless_runtime_plan_orders_phases_by_maturity() -> None:
    text = PLAN.read_text(encoding="utf-8")

    phases = [heading for heading in _headings(text, 2) if heading.startswith("Phase ")]

    assert phases == [
        "Phase 0 — Current Local Harness Runtime",
        "Phase 1 — Headless Single-Node Runtime",
        "Phase 2 — Queue-Backed Worker Runtime",
        "Phase 3 — Container Runtime",
        "Phase 4 — Kubernetes Runtime",
        "Phase 5 — Autonomous Repair / Product Factory",
    ]


def test_headless_runtime_claims_have_explicit_boundary_sections() -> None:
    text = ADR.read_text(encoding="utf-8")
    headings = set(_headings(text, 2))

    assert {
        "Current Enablers",
        "Requirements Before Cluster-Ready Claims",
        "Non-Goals For Now",
        "Product Positioning",
        "Guardrails",
    }.issubset(headings)
    assert text.index("Approved positioning") < text.index("Disallowed until implemented and tested")


def test_headless_runtime_docs_are_linked_from_entrypoints() -> None:
    docs_readme = (PROJECT_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    checklist = (PROJECT_ROOT / "docs" / "business" / "master-plan-checklist.md").read_text(
        encoding="utf-8"
    )

    assert docs_readme.count("headless-clustered-runtime-plan.md") == 1
    assert checklist.count("027-headless-clustered-runtime-direction.md") == 1

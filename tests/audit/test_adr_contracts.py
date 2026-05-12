"""ADR-067 Phase 2 — Audit tests for docs/02-Decisions/adrs/ADR-*.md section contracts.

Enforces the field contract defined in ADR-067 Phase 2 for ADR-067 and later.
Pre-067 ADRs are explicitly grandfathered (cutoff per operator decision #2).

Run:
    uv run pytest tests/audit/test_adr_contracts.py -v

Marker: @pytest.mark.audit on every test.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

# ─── Repo roots ──────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
ADRS_DIR = REPO_ROOT / "docs" / "adrs"

# ADR number cutoff: only ADR-067+ are enforced (operator decision #2).
ENFORCEMENT_CUTOFF = 67

# Required top-level sections for ADR-067+.
REQUIRED_SECTIONS = [
    "Status",
    "Context",
    "Decision",
    "Consequences",
    "Alternatives rejected",
    "Verification",
]


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _all_adr_files() -> list[Path]:
    return sorted(ADRS_DIR.glob("ADR-*.md"))


def _adr_number(path: Path) -> int:
    """Extract numeric ADR number from filename. Returns 0 if unparseable."""
    m = re.match(r"ADR-0*([0-9]+)", path.name)
    return int(m.group(1)) if m else 0


def _first_heading_number(text: str) -> int | None:
    """Return the ADR number claimed by the first Markdown heading."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            m = re.search(r"\bADR[- ]0*([0-9]+)\b", stripped, re.IGNORECASE)
            return int(m.group(1)) if m else None
    return None


def _is_lettered_variant(path: Path) -> bool:
    """Return True if the filename is a lettered ADR variant (e.g., ADR-027a, ADR-028b-foo).

    Lettered variants share a base number intentionally and are NOT duplicates.
    Pattern: ADR-NNN<letter>... where <letter> is [a-z].
    """
    return bool(re.match(r"ADR-0*[0-9]+[a-z]", path.name))


def _adr_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _section_body(text: str, section: str) -> str | None:
    """Return the body of a ## section, or None if section not present."""
    m = re.search(
        rf"^## {re.escape(section)}\b(.+?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return m.group(1) if m else None


def _has_alternatives_content(body: str) -> bool:
    """Return True if the Alternatives rejected body has >= 1 substantive item.

    Accepts EITHER:
    - A Markdown table with >= 1 data row (line starting with | that is not a
      header separator), OR
    - A numbered list with >= 1 item (line starting with a digit and '.'), OR
    - A bulleted list with >= 1 item (line starting with '-' or '*')

    This handles both the table format prescribed by the template and the
    numbered-list format used in ADR-067/068.
    """
    lines = body.splitlines()

    # Table data rows: | ... | but not |---|...
    table_rows = [
        l for l in lines
        if l.strip().startswith("|") and not re.match(r"^\s*\|[-| ]+\|\s*$", l)
    ]
    # Remove the header row (first non-separator row = column names)
    table_data_rows = table_rows[1:] if table_rows else []

    # Numbered list items
    numbered_items = [l for l in lines if re.match(r"^\s*\d+\.", l)]

    # Bulleted list items (- or *)
    bulleted_items = [l for l in lines if re.match(r"^\s*[-*] ", l)]

    return bool(table_data_rows or numbered_items or bulleted_items)


def _has_fenced_code_block(body: str) -> bool:
    """Return True if the body contains >= 1 fenced code block (>= 2 ``` markers)."""
    fences = re.findall(r"^```", body, re.MULTILINE)
    return len(fences) >= 2


def _adr_verification_audit_module():
    import importlib.util
    module_path = REPO_ROOT / "scripts" / "adr_verification_audit.py"
    spec = importlib.util.spec_from_file_location("adr_verification_audit", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("adr_verification_audit", module)
    spec.loader.exec_module(module)
    return module


# ─── Parameterization ────────────────────────────────────────────────────────

ALL_ADRS = _all_adr_files()
ALL_ADR_IDS = [p.name for p in ALL_ADRS]

ENFORCED_ADRS = [p for p in ALL_ADRS if _adr_number(p) >= ENFORCEMENT_CUTOFF]
ENFORCED_ADR_IDS = [p.name for p in ENFORCED_ADRS]


# ─── Tests ───────────────────────────────────────────────────────────────────


@pytest.mark.audit
def test_adrs_directory_not_empty() -> None:
    """Sanity: docs/02-Decisions/adrs/ contains at least 10 ADR files."""
    assert len(ALL_ADRS) >= 10, (
        f"Expected >= 10 ADR files in {ADRS_DIR}, found {len(ALL_ADRS)}"
    )


@pytest.mark.audit
@pytest.mark.parametrize("adr_path", ALL_ADRS, ids=ALL_ADR_IDS)
def test_non_lettered_adr_heading_number_matches_filename(adr_path: Path) -> None:
    """Canonical ADR files must not claim a different number in the first heading.

    Lettered addenda such as ADR-027a intentionally share a base number and are
    excluded from this check. Non-lettered ADRs are namespace anchors, so a file
    named ADR-086 with a heading claiming ADR-085 is a collision.
    """
    if _is_lettered_variant(adr_path):
        return

    filename_number = _adr_number(adr_path)
    heading_number = _first_heading_number(_adr_text(adr_path))

    assert heading_number == filename_number, (
        f"{adr_path.name}: first heading claims "
        f"{'no ADR number' if heading_number is None else f'ADR-{heading_number:03d}'}, "
        f"but filename claims ADR-{filename_number:03d}. "
        "Rename the file or correct the heading; do not leave contested ADR "
        "slots ambiguous."
    )


@pytest.mark.audit
def test_known_adr_collision_clusters_have_explicit_relationships() -> None:
    """Known historical overlap clusters must declare their canonical hierarchy."""
    required_relationships = {
        "ADR-084-headless-clustered-runtime-shape.md": [
            "Superseded by ADR-091",
            "## Relationship to ADR-091",
        ],
        "ADR-091-headless-clustered-runtime-direction.md": [
            "ADR-091 supersedes ADR-084",
        ],
        "ADR-049-llm-gateway-selection-and-overflow-providers.md": [
            "## Relationship to ADR-011 and ADR-018",
            "ADR-049 is canonical for LLM dispatch",
        ],
        "ADR-080-hermes-cross-harness-adoption.md": [
            "## Relationship to memory ADRs",
            "does not reopen the accepted Engram and memory decisions",
        ],
        "ADR-108-concurrent-agent-safety-layer.md": [
            "## Relationship to adjacent safety ADRs",
            "ADR-108 is the umbrella layer",
        ],
        "ADR-106-multi-session-safety-primitives.md": [
            "## Relationship to ADR-108 and ADR-111",
            "concrete primitive specification",
        ],
        "ADR-110-preserve-branch-governance.md": [
            "## Relationship to ADR-108 and ADR-111",
            "preserve-branch primitive",
        ],
        "ADR-111-core-consumer-concurrency-safety-boundary.md": [
            "## Relationship to ADR-106, ADR-108, and ADR-110",
            "boundary decision",
        ],
    }

    missing: list[str] = []
    for filename, required_snippets in required_relationships.items():
        text = _adr_text(ADRS_DIR / filename)
        for snippet in required_snippets:
            if snippet not in text:
                missing.append(f"{filename}: {snippet}")

    assert not missing, (
        "Known ADR overlap clusters must keep explicit relationship text:\n"
        + "\n".join(f"  - {item}" for item in missing)
    )


@pytest.mark.audit
@pytest.mark.parametrize("adr_path", ENFORCED_ADRS, ids=ENFORCED_ADR_IDS)
def test_adr_067_onwards_has_required_sections(adr_path: Path) -> None:
    """ADR-067+ must have all required top-level sections.

    Required: Status, Context, Decision, Consequences, Alternatives rejected,
    Verification.

    Pre-067 ADRs are grandfathered (not in ENFORCED_ADRS parameter set).
    """
    text = _adr_text(adr_path)
    missing = [
        s for s in REQUIRED_SECTIONS
        if not re.search(rf"^## {re.escape(s)}\b", text, re.MULTILINE)
    ]
    assert not missing, (
        f"{adr_path.name}: missing required section(s): {missing}. "
        f"ADR-{ENFORCEMENT_CUTOFF}+ must have all of: {REQUIRED_SECTIONS}."
    )


@pytest.mark.audit
@pytest.mark.parametrize("adr_path", ENFORCED_ADRS, ids=ENFORCED_ADR_IDS)
def test_adr_067_onwards_has_alternatives_rejected(adr_path: Path) -> None:
    """ADR-067+ ## Alternatives rejected must have >= 1 substantive item.

    Accepts table rows, numbered list items, or bulleted list items.
    An empty section with only a header is not sufficient.
    """
    text = _adr_text(adr_path)
    body = _section_body(text, "Alternatives rejected")
    if body is None:
        pytest.fail(
            f"{adr_path.name}: ## Alternatives rejected section is missing entirely. "
            f"Add it with at least one alternative and why it was rejected."
        )

    assert _has_alternatives_content(body), (
        f"{adr_path.name}: ## Alternatives rejected section has no substantive items "
        f"(need >= 1 table data row, numbered list item, or bullet). "
        f"Add at least one alternative with a rejection rationale."
    )


@pytest.mark.audit
@pytest.mark.parametrize("adr_path", ENFORCED_ADRS, ids=ENFORCED_ADR_IDS)
def test_adr_067_onwards_verification_has_code_block(adr_path: Path) -> None:
    """ADR-067+ ## Verification must contain >= 1 fenced code block.

    A fenced code block (``` ... ```) proves the verification is a runnable
    assertion, not just narrative prose.
    """
    text = _adr_text(adr_path)
    body = _section_body(text, "Verification")
    if body is None:
        pytest.fail(
            f"{adr_path.name}: ## Verification section is missing entirely."
        )

    assert _has_fenced_code_block(body), (
        f"{adr_path.name}: ## Verification has no fenced code block. "
        f"Add at least one ``` ... ``` block with a runnable assertion that "
        f"proves the decision is in effect."
    )




@pytest.mark.audit
@pytest.mark.parametrize("adr_path", ENFORCED_ADRS, ids=ENFORCED_ADR_IDS)
def test_adr_067_onwards_verification_evidence_is_not_grep_only(adr_path: Path) -> None:
    """ADR-067+ verification must not pass with grep-only documentation theater."""
    audit = _adr_verification_audit_module()
    row = audit.audit_adr_file(adr_path, root=REPO_ROOT)

    assert row.status == "pass", (
        f"{adr_path.name}: weak ADR verification evidence: {row.message}. "
        "Use pytest, smoke, audit --fail, py_compile, bash -n, or explicit "
        "implementation_files checks plus behavior evidence instead of generic grep."
    )

@pytest.mark.audit
def test_adr_numbering_monotonic_warn() -> None:
    """ADR numbers should be roughly monotonic; gaps emit warnings (not failures).

    Legitimate gaps exist (e.g., ADR-040 missing, ADR-027a/b/c lettered).
    This test WARNS about unexpected gaps but does NOT fail CI.
    Per operator decision #13: WARN, not BLOCK.
    """
    # Collect numbers from non-lettered ADRs only for gap detection.
    # Lettered variants (ADR-027a, ADR-028b) are intentional and not gaps.
    numbers: list[int] = []
    for p in ALL_ADRS:
        if _is_lettered_variant(p):
            continue
        n = _adr_number(p)
        if n > 0:
            numbers.append(n)

    if not numbers:
        return

    numbers_sorted = sorted(set(numbers))
    min_n, max_n = numbers_sorted[0], numbers_sorted[-1]
    number_set = set(numbers_sorted)

    gaps: list[int] = []
    for n in range(min_n, max_n + 1):
        if n not in number_set:
            gaps.append(n)

    if gaps:
        # Per operator decision #13: WARN (advisory), not BLOCK. Print to stderr
        # rather than warnings.warn to avoid pytest -W error mode failures.
        print(
            f"\n[audit-warn] ADR numbering gaps (may be intentional): {gaps}. "
            f"Expected if ADRs were removed or use lettered variants (e.g., ADR-027a).",
            file=sys.stderr,
        )

    # Duplicate ADR numbers from non-lettered variants are an error.
    # Lettered variants (ADR-027a, ADR-028b, etc.) share a base number intentionally
    # and are excluded from the duplicate check.
    non_lettered_adrs = [p for p in ALL_ADRS if not _is_lettered_variant(p) and _adr_number(p) > 0]
    non_lettered_numbers = [_adr_number(p) for p in non_lettered_adrs]
    if len(non_lettered_numbers) != len(set(non_lettered_numbers)):
        from collections import Counter
        dupes = [n for n, count in Counter(non_lettered_numbers).items() if count > 1]
        pytest.fail(
            f"Duplicate ADR numbers found in non-lettered ADR files: {dupes}. "
            f"Each canonical (non-lettered) ADR must have a unique number."
        )


@pytest.mark.audit
def test_adr_105_reflects_implemented_claim_verification_primitives() -> None:
    """ADR-105 must not drift back to policy-only while gates exist."""
    adr = ADRS_DIR / "ADR-105-claim-verification-contract.md"
    text = _adr_text(adr)
    assert "Accepted" in text and "Implemented" in text
    assert "Policy definition only" not in text
    required_refs = [
        "hooks/claim-validator.sh",
        "hooks/plan-claim-validator.sh",
        "hooks/orchestrator-claim-gate.sh",
        "scripts/orchestrator_claim_gate.py",
        "lib/orchestrator_verify.py",
        "docs/04-Concepts/architecture/claim-verification-matrix.md",
    ]
    missing = [ref for ref in required_refs if ref not in text]
    assert not missing, f"ADR-105 missing implemented primitive refs: {missing}"

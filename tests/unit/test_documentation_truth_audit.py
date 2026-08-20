from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
MODULE = REPO / "scripts" / "documentation_truth_audit.py"
spec = importlib.util.spec_from_file_location("documentation_truth_audit_unit", MODULE)
assert spec and spec.loader
documentation_truth_audit = importlib.util.module_from_spec(spec)
sys.modules["documentation_truth_audit_unit"] = documentation_truth_audit
spec.loader.exec_module(documentation_truth_audit)


def write_fixture(root: Path, doc_text: str, block_text: str | None = None) -> Path:
    (root / "docs" / "04-Concepts" / "architecture").mkdir(parents=True)
    (root / "docs" / "06-Daily" / "reports").mkdir(parents=True)
    (root / "manifests").mkdir(parents=True)
    (root / "docs" / "06-Daily" / "reports" / "source.json").write_text(json.dumps({"status": "pass", "summary": {}}), encoding="utf-8")
    doc_body = doc_text
    if block_text is not None:
        doc_body += "\n\n" + block_text + "\n"
    (root / "docs" / "04-Concepts" / "architecture" / "doc.md").write_text(doc_body, encoding="utf-8")
    manifest = {
        "schema_version": "documentation-truth-claims.v1",
        "claims": {
            "sample_claim": {
                "severity": "high",
                "source_reports": ["docs/06-Daily/reports/source.json"],
                "required_docs": ["docs/04-Concepts/architecture/doc.md"],
                "required_phrases": ["current phrase"],
                "forbidden_phrases": ["stale phrase"],
                "generated_block": {"doc": "docs/04-Concepts/architecture/doc.md", "marker": "sample_claim", "required": True},
            }
        },
    }
    manifest_path = root / "manifests" / "documentation-truth-claims.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return manifest_path


def test_audit_blocks_forbidden_stale_phrase(tmp_path: Path) -> None:
    block = documentation_truth_audit.render_block(tmp_path, "sample_claim", "sample_claim")
    manifest = write_fixture(tmp_path, "current phrase but also stale phrase", block)

    report = documentation_truth_audit.build_report(tmp_path, manifest)

    assert report["status"] == "block"
    assert any(row["check"] == "forbidden_phrase" and row["status"] == "block" for row in report["rows"])


def test_audit_blocks_stale_generated_block(tmp_path: Path) -> None:
    stale = "<!-- GENERATED:documentation-truth:sample_claim:start -->\nstale\n<!-- GENERATED:documentation-truth:sample_claim:end -->"
    manifest = write_fixture(tmp_path, "current phrase", stale)

    report = documentation_truth_audit.build_report(tmp_path, manifest)

    assert report["status"] == "block"
    assert any(row["check"] == "generated_block" and row["message"] == "Generated truth block is stale" for row in report["rows"])


def test_update_generated_repairs_block(tmp_path: Path) -> None:
    manifest = write_fixture(tmp_path, "current phrase")

    changed = documentation_truth_audit.update_block(tmp_path, "docs/04-Concepts/architecture/doc.md", "sample_claim", "sample_claim")
    report = documentation_truth_audit.build_report(tmp_path, manifest)

    assert changed is True
    assert report["status"] == "pass"


# --- forbidden-phrase scan surface (the "where you did not look" defect) ---
#
# Regression guard for 2026-08-19: a claim declared a forbidden phrase with no
# required_docs, the phrase was therefore searched in ZERO files, the audit went
# green, and three live copies kept shipping the lie.

SCAN_PHRASE = "the canonical hook registry is `cognitive-os.yaml > harness.hooks`"


def scan_fixture(root: Path, claim: dict, files: dict[str, str]) -> Path:
    (root / "manifests").mkdir(parents=True, exist_ok=True)
    for rel, body in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    manifest_path = root / "manifests" / "documentation-truth-claims.yaml"
    manifest_path.write_text(
        yaml.safe_dump({"schema_version": "documentation-truth-claims.v1", "claims": {"scan_claim": claim}}, sort_keys=False),
        encoding="utf-8",
    )
    return manifest_path


def rows_for(report: dict, check: str) -> list[dict]:
    return [row for row in report["rows"] if row["check"] == check]


def test_forbidden_phrase_is_found_outside_required_docs(tmp_path: Path) -> None:
    """The claim declares no docs at all; the lie lives in a shell hook."""
    manifest = scan_fixture(
        tmp_path,
        {"severity": "high", "forbidden_phrases": [SCAN_PHRASE]},
        {
            "hooks/inject-phase-context.sh": "#!/bin/bash\necho ok\n"
            "NOTE: .claude/settings.json is GENERATED (ADR-064): "
            "the canonical hook registry is cognitive-os.yaml > harness.hooks (entries).\n",
        },
    )

    report = documentation_truth_audit.build_report(tmp_path, manifest)

    blocked = [r for r in rows_for(report, "forbidden_phrase") if r["status"] == "block"]
    assert report["status"] == "block"
    assert blocked, report["rows"]
    assert "hooks/inject-phase-context.sh:3" in blocked[0]["evidence"]


def test_phrase_matches_through_backtick_decoration(tmp_path: Path) -> None:
    """Declared with single backticks, shipped bare and in rst double backticks."""
    manifest = scan_fixture(
        tmp_path,
        {"severity": "high", "forbidden_phrases": [SCAN_PHRASE]},
        {"cos_lib/wiring_validator.py": 'x = 1\n"""ADR-064: the canonical hook registry is ``cognitive-os.yaml > harness.hooks``."""\n'},
    )

    report = documentation_truth_audit.build_report(tmp_path, manifest)

    blocked = [r for r in rows_for(report, "forbidden_phrase") if r["status"] == "block"]
    assert blocked, report["rows"]
    assert "cos_lib/wiring_validator.py:2" in blocked[0]["evidence"]


def test_phrase_is_not_matched_as_a_substring(tmp_path: Path) -> None:
    """"plan-only Claude/Codex" is not the phrase "only Claude/Codex"."""
    manifest = scan_fixture(
        tmp_path,
        {"severity": "high", "forbidden_phrases": ["only Claude/Codex"]},
        {"docs/checklist.md": "- ADR-234 ... plan-only Claude/Codex settings projection.\n"},
    )

    report = documentation_truth_audit.build_report(tmp_path, manifest)

    assert report["status"] == "pass", [r for r in report["rows"] if r["status"] == "block"]


def test_date_anchored_report_citing_the_phrase_stays_green(tmp_path: Path) -> None:
    """Anti-paranoia control: the historical record quotes old claims on purpose."""
    manifest = scan_fixture(
        tmp_path,
        {"severity": "high", "forbidden_phrases": [SCAN_PHRASE]},
        {
            "docs/06-Daily/reports/hallazgo-2026-08-19.md": (
                "# Hallazgo\n\nEl gotcha afirmaba que "
                "the canonical hook registry is `cognitive-os.yaml > harness.hooks`, "
                "y era falso.\n"
            ),
            "docs/live.md": "Registering a hook takes six surfaces kept in step by hand.\n",
        },
    )

    report = documentation_truth_audit.build_report(tmp_path, manifest)

    assert report["status"] == "pass", [r for r in report["rows"] if r["status"] == "block"]
    surface = rows_for(report, "forbidden_phrase_surface")[0]
    assert any(e.startswith("checked_files:") and e != "checked_files:0" for e in surface["evidence"])


def test_claim_with_forbidden_phrase_and_no_surface_is_rejected(tmp_path: Path) -> None:
    """A scope that resolves to nothing checks zero files: that is the defect."""
    manifest = scan_fixture(
        tmp_path,
        {
            "severity": "high",
            "forbidden_phrases": [
                {"phrase": SCAN_PHRASE, "scope": ["docs/does-not-exist.md"], "scope_reason": "declared but the file is gone"}
            ],
        },
        {"docs/live.md": "nothing stale here\n"},
    )

    report = documentation_truth_audit.build_report(tmp_path, manifest)

    blocked = [r for r in rows_for(report, "forbidden_phrase_surface") if r["status"] == "block"]
    assert report["status"] == "block"
    assert blocked and "checked_files:0" in blocked[0]["evidence"]
    assert "no surface to check it against" in blocked[0]["message"]


def test_narrowed_scope_without_a_written_reason_is_rejected(tmp_path: Path) -> None:
    manifest = scan_fixture(
        tmp_path,
        {"severity": "high", "forbidden_phrases": [{"phrase": "not implemented yet", "scope": ["docs/live.md"]}]},
        {"docs/live.md": "all good\n"},
    )

    report = documentation_truth_audit.build_report(tmp_path, manifest)

    blocked = [r for r in rows_for(report, "forbidden_phrase_scope") if r["status"] == "block"]
    assert report["status"] == "block"
    assert blocked and "without a written reason" in blocked[0]["message"]


def test_required_phrases_without_required_docs_are_rejected(tmp_path: Path) -> None:
    manifest = scan_fixture(
        tmp_path,
        {"severity": "high", "required_phrases": ["Claude Code is the exception"]},
        {"docs/live.md": "Claude Code is the exception\n"},
    )

    report = documentation_truth_audit.build_report(tmp_path, manifest)

    blocked = [r for r in rows_for(report, "required_phrase_surface") if r["status"] == "block"]
    assert report["status"] == "block"
    assert blocked and "no existing required_docs" in blocked[0]["message"]


def test_required_docs_are_scanned_even_when_globally_excluded(tmp_path: Path) -> None:
    """A dated report is historical, unless a claim names it as its own surface."""
    manifest = scan_fixture(
        tmp_path,
        {
            "severity": "high",
            "required_docs": ["docs/06-Daily/reports/numeros-2026-08-15.md"],
            "forbidden_phrases": ["Component counts: 57 hooks"],
        },
        {"docs/06-Daily/reports/numeros-2026-08-15.md": "Component counts: 57 hooks and more.\n"},
    )

    report = documentation_truth_audit.build_report(tmp_path, manifest)

    blocked = [r for r in rows_for(report, "forbidden_phrase") if r["status"] == "block"]
    assert blocked, report["rows"]


def test_forbidden_phrase_rows_report_the_file_count(tmp_path: Path) -> None:
    """N=0 was the defect, so N is in every row."""
    manifest = scan_fixture(
        tmp_path,
        {"severity": "high", "forbidden_phrases": ["stale wording"]},
        {"docs/a.md": "fine\n", "docs/b.md": "also fine\n", "scripts/x.sh": "echo fine\n"},
    )

    report = documentation_truth_audit.build_report(tmp_path, manifest)
    row = [r for r in rows_for(report, "forbidden_phrase")][0]

    assert "checked against 3 files" in row["message"]
    assert "checked_files:3" in row["evidence"]
    assert report["summary"]["forbidden_phrase_scan"]["surface_files"] == 3

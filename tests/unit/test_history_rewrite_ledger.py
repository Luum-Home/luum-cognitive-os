"""Unit tests for lib.history_rewrite_ledger (ADR-269 Primitive 1)."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from lib.history_rewrite_ledger import (
    LedgerEntry,
    LedgerError,
    SCHEMA_VERSION,
    append_entry,
    find_orphan_bundles,
    find_orphan_entries,
    list_entries,
    load_ledger,
    validate_adr_accepted,
)


def _bootstrap(project_dir: Path, *, with_adr: bool = True, ledger_seed: dict | None = None) -> None:
    (project_dir / "manifests").mkdir(parents=True, exist_ok=True)
    (project_dir / ".cognitive-os/recovery").mkdir(parents=True, exist_ok=True)
    (project_dir / "docs/adrs").mkdir(parents=True, exist_ok=True)
    if with_adr:
        (project_dir / "docs/adrs/ADR-999-test.md").write_text(
            "---\nadr: 999\ntitle: Test ADR\nstatus: accepted\n---\n\n# ADR-999\n",
            encoding="utf-8",
        )
    if ledger_seed is not None:
        (project_dir / "manifests/history-rewrite-ledger.yaml").write_text(
            yaml.safe_dump(ledger_seed, sort_keys=False), encoding="utf-8"
        )


def test_empty_ledger_returns_no_entries(tmp_path: Path) -> None:
    _bootstrap(tmp_path)
    assert list_entries(tmp_path) == []


def test_append_entry_writes_and_round_trips(tmp_path: Path) -> None:
    _bootstrap(tmp_path)
    entry = LedgerEntry(
        timestamp="",
        operator="alice",
        adr_ref="ADR-999",
        reason="test rewrite",
        bundle_path=".cognitive-os/recovery/pre-history-sanitization-20260101T000000Z.bundle",
        sha_before="aaaa",
        sha_after="bbbb",
        rewrite_scope="commit-messages-only",
        tool="git-filter-repo",
        invocation="pytest",
    )
    path = append_entry(tmp_path, entry)
    assert path.exists()
    data = load_ledger(tmp_path)
    assert data["schema_version"] == SCHEMA_VERSION
    assert len(data["entries"]) == 1
    assert data["entries"][0]["adr_ref"] == "ADR-999"
    assert data["entries"][0]["timestamp"]  # auto-filled


def test_append_duplicate_bundle_rejected(tmp_path: Path) -> None:
    _bootstrap(tmp_path)
    e = LedgerEntry(
        timestamp="",
        operator="alice",
        adr_ref="ADR-999",
        reason="r",
        bundle_path=".cognitive-os/recovery/pre-history-sanitization-20260101T000000Z.bundle",
        sha_before="a",
        sha_after="b",
        rewrite_scope="commit-messages-only",
        tool="git-filter-repo",
        invocation="t",
    )
    append_entry(tmp_path, e)
    with pytest.raises(LedgerError) as exc:
        append_entry(tmp_path, e)
    assert exc.value.code == "bundle-already-registered"


def test_append_requires_reason(tmp_path: Path) -> None:
    _bootstrap(tmp_path)
    e = LedgerEntry(
        timestamp="", operator="a", adr_ref="ADR-999", reason="   ",
        bundle_path="x.bundle", sha_before="a", sha_after="b",
        rewrite_scope="x", tool="y", invocation="z",
    )
    with pytest.raises(LedgerError) as exc:
        append_entry(tmp_path, e)
    assert exc.value.code == "reason-required"


def test_append_rejects_unaccepted_adr(tmp_path: Path) -> None:
    _bootstrap(tmp_path, with_adr=False)
    e = LedgerEntry(
        timestamp="", operator="a", adr_ref="ADR-999", reason="r",
        bundle_path="x.bundle", sha_before="a", sha_after="b",
        rewrite_scope="x", tool="y", invocation="z",
    )
    with pytest.raises(LedgerError) as exc:
        append_entry(tmp_path, e, validate_adr=True)
    assert exc.value.code == "adr-not-accepted"


def test_validate_adr_accepted_status_field(tmp_path: Path) -> None:
    _bootstrap(tmp_path, with_adr=True)
    ok, _ = validate_adr_accepted(tmp_path, "ADR-999")
    assert ok is True


def test_validate_adr_accepted_status_section(tmp_path: Path) -> None:
    (tmp_path / "docs/adrs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs/adrs/ADR-500-section.md").write_text(
        "# ADR-500\n\n## Status\n\nAccepted (2026-01-01).\n",
        encoding="utf-8",
    )
    ok, _ = validate_adr_accepted(tmp_path, "ADR-500")
    assert ok is True


def test_validate_adr_missing(tmp_path: Path) -> None:
    (tmp_path / "docs/adrs").mkdir(parents=True, exist_ok=True)
    ok, _ = validate_adr_accepted(tmp_path, "ADR-001")
    assert ok is False


def test_validate_adr_malformed_ref(tmp_path: Path) -> None:
    ok, why = validate_adr_accepted(tmp_path, "not-an-adr")
    assert ok is False
    assert "format" in why


def test_find_orphan_bundles_detects_unregistered(tmp_path: Path) -> None:
    _bootstrap(tmp_path)
    bundle = tmp_path / ".cognitive-os/recovery/pre-history-sanitization-20260101T000000Z.bundle"
    bundle.write_bytes(b"fake bundle")
    orphans = find_orphan_bundles(tmp_path)
    assert len(orphans) == 1
    assert orphans[0].name == bundle.name


def test_find_orphan_bundles_excludes_registered(tmp_path: Path) -> None:
    _bootstrap(tmp_path)
    bundle = tmp_path / ".cognitive-os/recovery/pre-history-sanitization-20260101T000000Z.bundle"
    bundle.write_bytes(b"x")
    e = LedgerEntry(
        timestamp="", operator="a", adr_ref="ADR-999", reason="r",
        bundle_path=".cognitive-os/recovery/pre-history-sanitization-20260101T000000Z.bundle",
        sha_before="a", sha_after="b", rewrite_scope="x", tool="y", invocation="z",
    )
    append_entry(tmp_path, e)
    assert find_orphan_bundles(tmp_path) == []


def test_find_orphan_entries_detects_missing_bundles(tmp_path: Path) -> None:
    _bootstrap(tmp_path)
    e = LedgerEntry(
        timestamp="", operator="a", adr_ref="ADR-999", reason="r",
        bundle_path=".cognitive-os/recovery/does-not-exist.bundle",
        sha_before="a", sha_after="b", rewrite_scope="x", tool="y", invocation="z",
    )
    append_entry(tmp_path, e)
    orphans = find_orphan_entries(tmp_path)
    assert len(orphans) == 1
    assert orphans[0].bundle_path.endswith("does-not-exist.bundle")

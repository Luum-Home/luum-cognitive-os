from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "adr_verification_audit.py"
spec = importlib.util.spec_from_file_location("adr_verification_audit", MODULE_PATH)
assert spec and spec.loader
adr_verification_audit = importlib.util.module_from_spec(spec)
sys.modules["adr_verification_audit"] = adr_verification_audit
spec.loader.exec_module(adr_verification_audit)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def adr_text(*, impl_status: str = "implemented", verification: str) -> str:
    return f"""---
adr: 999
title: Test ADR
status: accepted
implementation_status: {impl_status}
classification_basis: "implemented: test fixture"
implementation_files:
  - lib/example.py
tier: maintainer
tags: [test]
---
# ADR-999: Test ADR

## Status

Accepted.

## Context

Context.

## Decision

Decision.

## Consequences

Consequences.

## Alternatives rejected

- Alternative rejected.

## Verification

```bash
{verification}
```
"""


def test_grep_only_verification_fails_for_implemented_adr(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write(root / "lib" / "example.py", "print('ok')\n")
    path = root / "docs" / "02-Decisions" / "adrs" / "ADR-999-test.md"
    write(path, adr_text(verification="grep -rn 'ADR-999' docs/ scripts/ tests/ | head -20"))

    row = adr_verification_audit.audit_adr_file(path, root=root)

    assert row.status == "fail"
    assert "generic_adr_grep_only" in row.message
    assert "implemented_without_strong_verification" in row.message


def test_pytest_verification_passes_for_implemented_adr(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write(root / "lib" / "example.py", "print('ok')\n")
    path = root / "docs" / "02-Decisions" / "adrs" / "ADR-999-test.md"
    write(path, adr_text(verification="python3 -m pytest tests/unit/test_example.py -q"))

    row = adr_verification_audit.audit_adr_file(path, root=root)

    assert row.status == "pass"
    assert row.derived_level == "strong"


def test_missing_implementation_file_fails_even_with_strong_command(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    path = root / "docs" / "02-Decisions" / "adrs" / "ADR-999-test.md"
    write(path, adr_text(verification="python3 -m pytest tests/unit/test_example.py -q"))

    row = adr_verification_audit.audit_adr_file(path, root=root)

    assert row.status == "fail"
    assert row.missing_implementation_files == ["lib/example.py"]

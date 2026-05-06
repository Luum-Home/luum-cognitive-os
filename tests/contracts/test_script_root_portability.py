from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
FORBIDDEN = "git rev-parse --show-toplevel"


def test_product_scripts_do_not_depend_on_git_checkout_root() -> None:
    offenders: list[str] = []
    for path in sorted((REPO / "scripts").iterdir()):
        if not path.is_file() or path.name.startswith("__"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if FORBIDDEN in text:
            offenders.append(str(path.relative_to(REPO)))
    assert offenders == []


def test_cos_root_documents_install_safe_precedence() -> None:
    text = (REPO / "scripts" / "cos-root").read_text(encoding="utf-8")
    assert "COGNITIVE_OS_PROJECT_DIR" in text
    assert "CODEX_PROJECT_DIR" in text
    assert "CLAUDE_PROJECT_DIR" in text
    assert "install_root" in text

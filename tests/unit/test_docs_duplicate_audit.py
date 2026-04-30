from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "docs_duplicate_audit.py"
spec = importlib.util.spec_from_file_location("docs_duplicate_audit", MODULE_PATH)
assert spec and spec.loader
docs_duplicate_audit = importlib.util.module_from_spec(spec)
sys.modules["docs_duplicate_audit"] = docs_duplicate_audit
spec.loader.exec_module(docs_duplicate_audit)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def repeated_doc(title: str, extra: str = "") -> str:
    body = " ".join(["governance verification portability runtime primitive evidence"] * 40)
    return f"# {title}\n\n{body} {extra}\n"


def test_detects_near_duplicate_docs(tmp_path: Path) -> None:
    write(tmp_path / "docs/a.md", repeated_doc("A"))
    write(tmp_path / "docs/b.md", repeated_doc("B"))

    data = docs_duplicate_audit.audit(tmp_path, ["docs"], min_tokens=20, shingle_size=5, threshold=0.70, baseline_path=None)

    assert data["duplicate_pairs"] == 1
    finding = data["findings"][0]
    assert finding["left"] == "docs/a.md"
    assert finding["right"] == "docs/b.md"


def test_baseline_suppresses_existing_pairs(tmp_path: Path) -> None:
    write(tmp_path / "docs/a.md", repeated_doc("A"))
    write(tmp_path / "docs/b.md", repeated_doc("B"))
    first = docs_duplicate_audit.audit(tmp_path, ["docs"], min_tokens=20, shingle_size=5, threshold=0.70, baseline_path=None)
    write(tmp_path / "baseline.json", docs_duplicate_audit.json.dumps(first))

    second = docs_duplicate_audit.audit(
        tmp_path, ["docs"], min_tokens=20, shingle_size=5, threshold=0.70, baseline_path=tmp_path / "baseline.json"
    )

    assert second["duplicate_pairs"] == 1
    assert second["new_duplicate_pairs"] == 0


def test_cli_fails_on_new_duplicate(tmp_path: Path, monkeypatch) -> None:
    write(tmp_path / "baseline.json", '{"pair_keys": []}')
    write(tmp_path / "docs/a.md", repeated_doc("A"))
    write(tmp_path / "docs/b.md", repeated_doc("B"))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docs_duplicate_audit.py",
            "--project-root",
            str(tmp_path),
            "--baseline",
            "baseline.json",
            "--threshold",
            "0.70",
            "--min-tokens",
            "20",
            "--shingle-size",
            "5",
            "--markdown",
            "docs/report.md",
            "--fail-new",
        ],
    )

    assert docs_duplicate_audit.main() == 1
    assert "New duplicate pairs" in (tmp_path / "docs/report.md").read_text(encoding="utf-8")

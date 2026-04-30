from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "docs_execution_audit.py"
spec = importlib.util.spec_from_file_location("docs_execution_audit", MODULE_PATH)
assert spec and spec.loader
docs_execution_audit = importlib.util.module_from_spec(spec)
sys.modules["docs_execution_audit"] = docs_execution_audit
spec.loader.exec_module(docs_execution_audit)

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def test_classifies_done_stale_planned_and_proposed(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write(root / "scripts" / "done_feature.py", "def done_feature(): return True\n")
    write(root / "tests" / "test_done_feature.py", "def test_done_feature(): assert 'done_feature'\n")
    write(root / "docs" / "plan.md", """# Plan

- [x] Implement done_feature in `scripts/done_feature.py` with behavior test.
- [x] Implement missing_feature in `scripts/missing_feature.py`.
- [ ] Add future dashboard primitive.
- Proposed: add optional graph backend later.
""")
    rows = docs_execution_audit.audit(root)
    by_item = {row.item: row.inferred_status for row in rows}
    assert by_item["Implement done_feature in `scripts/done_feature.py` with behavior test."] == "done_with_proof"
    assert by_item["Implement missing_feature in `scripts/missing_feature.py`."] == "stale"
    assert by_item["Add future dashboard primitive."] == "planned"
    assert by_item["Proposed: add optional graph backend later."] == "proposed"

def test_cli_writes_reports_and_can_fail_on_unproved_done(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write(root / "docs" / "plan.md", "# Plan\n\n- [x] Completed invisible magic system.\n")
    result = subprocess.run([sys.executable, str(MODULE_PATH), "--project-dir", str(root), "--json-out", "reports/docs-execution.json", "--md-out", "reports/docs-execution.md", "--fail-claimed-done-no-proof"], text=True, capture_output=True, check=False)
    assert result.returncode == 2
    payload = json.loads((root / "reports" / "docs-execution.json").read_text())
    assert payload["summary"]["statuses"]["claimed_done_no_proof"] == 1
    assert "Documentation Execution Audit" in (root / "reports" / "docs-execution.md").read_text()

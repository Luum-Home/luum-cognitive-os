from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MODULE = REPO / "scripts" / "acc_pipeline.py"
spec = importlib.util.spec_from_file_location("acc_pipeline_doc_truth_unit", MODULE)
assert spec and spec.loader
acc_pipeline = importlib.util.module_from_spec(spec)
sys.modules["acc_pipeline_doc_truth_unit"] = acc_pipeline
spec.loader.exec_module(acc_pipeline)


def test_acc_loads_documentation_truth_report(tmp_path: Path) -> None:
    report = tmp_path / "docs" / "reports" / "documentation-truth-latest.json"
    report.parent.mkdir(parents=True)
    report.write_text(
        json.dumps(
            {
                "status": "pass",
                "summary": {"block_count": 0},
                "rows": [
                    {"claim_id": "sample", "check": "required_doc_exists", "status": "pass", "severity": "medium", "doc": "docs/x.md", "message": "ok", "evidence": [], "next_action": "keep"}
                ],
            }
        ),
        encoding="utf-8",
    )

    status, capabilities, findings = acc_pipeline.load_documentation_truth(tmp_path)

    assert status.status == "ok"
    assert status.summary["block_count"] == 0
    assert len(capabilities) == 1
    assert capabilities[0].id == "documentation_truth:sample"
    assert capabilities[0].mapping_status == "aligned"
    assert findings == []

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MODULE = Path(__file__).resolve().parents[2] / "scripts" / "acc_pipeline.py"
spec = importlib.util.spec_from_file_location("acc_pipeline_authority_test", MODULE)
assert spec and spec.loader
acc_pipeline = importlib.util.module_from_spec(spec)
sys.modules["acc_pipeline_authority_test"] = acc_pipeline
spec.loader.exec_module(acc_pipeline)


def test_acc_loads_authority_write_effects_report(tmp_path: Path) -> None:
    report = tmp_path / "docs" / "06-Daily" / "reports" / "primitive-authority-latest.json"
    report.parent.mkdir(parents=True)
    report.write_text(
        json.dumps(
            {
                "schema_version": "primitive-authority-audit.v1",
                "status": "pass",
                "summary": {"total_scripts": 1, "block_count": 0},
                "items": [
                    {
                        "path": "scripts/x.py",
                        "status": "pass",
                        "authority_mode": "observe-only",
                        "authority_source": "derived:shared-default",
                        "scope": "both",
                        "consumer_accessibility": "so-local-only",
                        "detected_write_surfaces": [],
                    }
                ],
                "dynamic_smokes": [{"id": "demo", "status": "pass", "returncode": 0}],
            }
        ),
        encoding="utf-8",
    )

    status, capabilities, findings = acc_pipeline.load_authority_write_effects(tmp_path)

    assert status.status == "ok"
    assert status.summary["total_scripts"] == 1
    assert not findings
    ids = {cap.id for cap in capabilities}
    assert "authority_write_effects:scripts/x.py" in ids
    assert "authority_write_effects:dynamic:demo" in ids

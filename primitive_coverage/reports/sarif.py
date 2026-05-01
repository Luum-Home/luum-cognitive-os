from __future__ import annotations

import json
from primitive_coverage.model import CoverageReport


def render_sarif(report: CoverageReport) -> str:
    results = []
    for row in report.rows:
        if not row.actionable_gaps:
            continue
        level = "error" if row.status in {"orphan", "dormant"} else "warning"
        results.append(
            {
                "ruleId": "primitive-coverage-gap",
                "level": level,
                "message": {"text": f"{row.primitive_id} has actionable gaps: {', '.join(row.actionable_gaps)}"},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": row.path},
                            "region": {"startLine": 1},
                        }
                    }
                ],
                "properties": {"primitive_id": row.primitive_id, "status": row.status, "score": row.score},
            }
        )
    payload = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "primitive-coverage",
                        "informationUri": "https://github.com/luum-ai/luum-agent-os",
                        "rules": [
                            {
                                "id": "primitive-coverage-gap",
                                "name": "Primitive coverage gap",
                                "shortDescription": {"text": "Primitive is missing coverage evidence"},
                            }
                        ],
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"

from __future__ import annotations

import json
from primitive_coverage.model import CoverageReport


def render_json(report: CoverageReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"

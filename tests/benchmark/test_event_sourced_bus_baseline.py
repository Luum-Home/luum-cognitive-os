from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from lib.session_bus import append_session_event  # noqa: E402


@pytest.mark.benchmark
def test_event_sourced_bus_slice_a_records_latency_baseline(tmp_path: Path) -> None:
    samples_ms: list[float] = []
    for idx in range(60):
        start = time.perf_counter()
        append_session_event("coordination-claim", {"idx": idx}, project_dir=tmp_path, session_id="perf-session")
        samples_ms.append((time.perf_counter() - start) * 1000)

    sorted_samples = sorted(samples_ms)
    p50 = statistics.median(sorted_samples)
    p95 = sorted_samples[int(len(sorted_samples) * 0.95) - 1]
    p99 = sorted_samples[int(len(sorted_samples) * 0.99) - 1]

    report = tmp_path / ".cognitive-os" / "reports" / "event-sourced-session-bus-baseline.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        '{'
        f'"schema_version":"event-sourced-session-bus-baseline/v1",'
        f'"sample_count":{len(samples_ms)},'
        f'"p50_ms":{p50:.6f},'
        f'"p95_ms":{p95:.6f},'
        f'"p99_ms":{p99:.6f}'
        '}\n',
        encoding="utf-8",
    )

    assert report.is_file()
    assert p50 >= 0
    assert p95 >= p50
    assert p99 >= p95

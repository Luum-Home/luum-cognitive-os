#!/usr/bin/env python3
"""Run an automated live ADR-100 headroom validation.

This is intentionally an on-demand proof, not a default unit test fixture. It
runs the real pytest wrapper against a generated CPU-work test file, then checks
that the wrapper:

- selected adaptive workers through scripts/detect_runner_capacity.py;
- left local headroom on non-CI machines when the default row fires;
- emitted capacity/resource-policy artifacts;
- ran pytest through nice/resource governance; and
- used xdist loadgroup when parallel workers were selected.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WRAPPER = PROJECT_ROOT / "scripts" / "pytest-with-summary.sh"
DETECTOR = PROJECT_ROOT / "scripts" / "detect_runner_capacity.py"


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_cpu_test(path: Path, *, test_count: int, work_seconds: float) -> None:
    path.write_text(
        textwrap.dedent(
            f"""
            import time
            import pytest

            pytestmark = pytest.mark.unit

            def _burn(seconds: float) -> int:
                deadline = time.perf_counter() + seconds
                value = 0
                while time.perf_counter() < deadline:
                    value = (value * 1315423911 + 2654435761) & 0xFFFFFFFF
                return value

            @pytest.mark.parametrize("idx", range({test_count}))
            def test_cpu_workload(idx):
                assert _burn({work_seconds!r}) >= 0
            """
        ).lstrip(),
        encoding="utf-8",
    )


def _parse_workers(value: str) -> int | None:
    if value == "auto":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def run_live_check(args: argparse.Namespace) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="adr100-live-") as tmp_raw:
        tmp = Path(tmp_raw)
        test_file = tmp / "test_adr100_live_cpu.py"
        reports = tmp / "reports"
        metrics = tmp / "metrics"
        reports.mkdir()
        metrics.mkdir()
        _write_cpu_test(test_file, test_count=args.tests, work_seconds=args.work_seconds)

        env = os.environ.copy()
        env["COS_TEST_REPORT_DIR"] = str(reports)
        env["COS_METRICS_DIR"] = str(metrics)
        env["COGNITIVE_OS_SESSION_ID"] = "adr100-live-headroom-check"
        env.setdefault("COS_PYTEST_NO_RERUN", "1")
        env.setdefault("COS_TEST_REPORT_KEEP", "5")
        if args.headroom is not None:
            env["COS_PYTEST_HEADROOM"] = str(args.headroom)
        if args.no_nice:
            env["COS_PYTEST_NO_NICE"] = "1"

        detector = _run([sys.executable, str(DETECTOR), "--json"], cwd=PROJECT_ROOT, env=env, timeout=15)
        if detector.returncode != 0:
            raise RuntimeError(detector.stderr + detector.stdout)
        detector_payload = json.loads(detector.stdout)

        cmd = [
            "bash",
            str(WRAPPER),
            "--lane",
            "adr100-live",
            "--timeout-seconds",
            str(args.timeout_seconds),
            "--docker-policy",
            "forbidden",
            "--cost-policy",
            "free_only",
            "--artifact-policy",
            "keep_summary",
            "--",
            str(test_file),
            "-q",
        ]
        result = _run(cmd, cwd=PROJECT_ROOT, env=env, timeout=args.timeout_seconds)
        if result.returncode != 0:
            raise RuntimeError(result.stdout + result.stderr)

        latest = reports / "latest"
        capacity_files = sorted(metrics.rglob("capacity.json"))
        if not capacity_files:
            raise AssertionError(f"No capacity.json found under {metrics}")
        capacity = _load_json(capacity_files[-1])
        resource_policy = _load_json(latest / "resource-policy.json")
        metadata = (latest / "metadata.txt").read_text(encoding="utf-8")
        full_output = (latest / "full-output.txt").read_text(encoding="utf-8")

        workers_chosen = str(capacity.get("workers_chosen", ""))
        rule_fired = str(capacity.get("rule_fired", ""))
        cores = int(capacity.get("cores") or detector_payload.get("cores") or 1)
        headroom = max(0, int(env.get("COS_PYTEST_HEADROOM", "2")))
        ci = bool(capacity.get("ci"))
        parsed_workers = _parse_workers(workers_chosen)

        if resource_policy.get("outcome") != "ok":
            raise AssertionError(f"resource-policy outcome is not ok: {resource_policy}")
        if resource_policy.get("lane") != "adr100-live":
            raise AssertionError(f"resource-policy lane mismatch: {resource_policy}")
        wrapper_output = result.stdout + result.stderr
        if "Resource governance: nice=" not in wrapper_output and args.no_nice is False:
            raise AssertionError("wrapper did not report nice/resource governance")

        if not ci and rule_fired == "default_headroom":
            expected = max(2, cores - headroom)
            if workers_chosen == "auto":
                raise AssertionError("local default_headroom must not choose xdist auto")
            if parsed_workers != expected:
                raise AssertionError(
                    f"default_headroom chose workers={workers_chosen}, expected cores-headroom={expected}"
                )

        if parsed_workers and parsed_workers > 0:
            if "--dist loadgroup" not in metadata and "--dist loadgroup" not in full_output and "--dist loadgroup" not in wrapper_output:
                raise AssertionError("parallel run did not include --dist loadgroup")

        if parsed_workers is not None and parsed_workers < 0:
            raise AssertionError(f"invalid workers_chosen={workers_chosen}")

        summary = {
            "status": "pass",
            "rule_fired": rule_fired,
            "workers_chosen": workers_chosen,
            "cores": cores,
            "headroom": headroom,
            "ci": ci,
            "pytest_exit": result.returncode,
            "report_dir": str(latest.resolve()),
            "capacity_json": str(capacity_files[-1].resolve()),
            "resource_policy": resource_policy,
            "detector": detector_payload,
        }
        if args.keep_artifacts:
            keep_root = PROJECT_ROOT / ".cognitive-os" / "reports" / "adr100-live-headroom"
            keep_root.mkdir(parents=True, exist_ok=True)
            out = keep_root / "latest.json"
            out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            summary["kept_summary"] = str(out)
        return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tests", type=int, default=16, help="number of generated CPU-work tests")
    parser.add_argument("--work-seconds", type=float, default=0.15, help="CPU work seconds per generated test")
    parser.add_argument("--timeout-seconds", type=int, default=120, help="overall wrapper timeout")
    parser.add_argument("--headroom", type=int, default=None, help="override COS_PYTEST_HEADROOM for this proof")
    parser.add_argument("--no-nice", action="store_true", help="disable nice assertion and wrapper nice mode")
    parser.add_argument("--keep-artifacts", action="store_true", help="write latest proof summary under .cognitive-os/reports/adr100-live-headroom/")
    ns = parser.parse_args()

    if ns.tests < 1:
        parser.error("--tests must be >= 1")
    if ns.work_seconds < 0:
        parser.error("--work-seconds must be >= 0")

    try:
        summary = run_live_check(ns)
    except Exception as exc:  # noqa: BLE001
        print(f"ADR-100 live headroom check FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

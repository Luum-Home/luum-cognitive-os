from pathlib import Path

from lib.runtime_benchmark import RuntimeBenchmarkResult, append_result, format_leaderboard, load_results, validate_result


def test_runtime_benchmark_result_schema_accepts_valid_row() -> None:
    row = RuntimeBenchmarkResult(
        benchmark_id="b1",
        system="cos",
        profile="standard",
        task_id="t1",
        result="pass",
        tests_passed=True,
        security_events=1,
    ).to_dict()

    assert validate_result(row) == []


def test_runtime_benchmark_result_schema_rejects_invalid_result() -> None:
    row = RuntimeBenchmarkResult("b1", "cos", "standard", "t1", "weird").to_dict()

    assert "invalid:result" in validate_result(row)


def test_runtime_benchmark_jsonl_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "results.jsonl"
    append_result(path, RuntimeBenchmarkResult("b1", "cos", "standard", "t1", "pass", tests_passed=True))

    rows = load_results(path)
    assert rows[0]["system"] == "cos"
    assert "Runtime Benchmark Leaderboard" in format_leaderboard(rows)

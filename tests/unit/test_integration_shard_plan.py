from __future__ import annotations

from lib.integration_shard_plan import plan_shards


def test_integration_shard_plan_covers_each_file_once(project_root) -> None:
    shards = plan_shards(project_root, 4)
    files = [path for shard in shards for path in shard["files"]]
    assert files
    assert len(files) == len(set(files))
    assert all(path.startswith("tests/integration/test_") for path in files)


def test_integration_shard_plan_balances_non_empty_shards(project_root) -> None:
    shards = plan_shards(project_root, 4)
    assert all(shard["file_count"] > 0 for shard in shards)
    weights = [shard["weight"] for shard in shards]
    assert max(weights) - min(weights) <= max(weights) * 0.35

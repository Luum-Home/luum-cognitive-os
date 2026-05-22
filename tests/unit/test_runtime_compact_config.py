from __future__ import annotations

from pathlib import Path

import yaml

from scripts.generate_runtime_compact_config import build_compact_config, write_compact_config


def test_runtime_compact_config_keeps_budget_and_drops_hook_registry(tmp_path: Path) -> None:
    source = tmp_path / "cognitive-os.yaml"
    source.write_text(
        """
project: {name: demo, phase: reconstruction}
context_budget: {static_max_tokens: 4000, user_max_tokens: 12000}
models: {routing: {default: sonnet}, gateways: {heavy: true}, providers: {openrouter: {enabled: true}}}
resources: {budget: {monthly_limit_usd: 200}, infrastructure: {large: true}, tokens: {result_truncation: {enabled: true}}}
harness: {hooks: {many: entries}}
""",
        encoding="utf-8",
    )

    compact = build_compact_config(source)

    assert compact["context_budget"]["static_max_tokens"] == 4000
    assert compact["models"] == {"routing": {"default": "sonnet"}, "providers": {"openrouter": {"enabled": True}}}
    assert compact["resources"] == {"budget": {"monthly_limit_usd": 200}, "tokens": {"result_truncation": {"enabled": True}}}
    assert "harness" not in compact
    assert "gateways" not in compact["models"]
    assert "infrastructure" not in compact["resources"]


def test_write_runtime_compact_config_is_smaller_than_source(tmp_path: Path) -> None:
    source = tmp_path / "cognitive-os.yaml"
    source.write_text(
        "context_budget:\n  user_max_tokens: 12000\n" + "# long historical comment\n" * 100,
        encoding="utf-8",
    )
    output = tmp_path / ".cognitive-os/generated/runtime-config.compact.yaml"

    write_compact_config(source, output)

    assert output.exists()
    assert output.stat().st_size < source.stat().st_size
    data = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert data["context_budget"]["user_max_tokens"] == 12000

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_hook(hook: str, *, cwd: Path, payload: dict | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(REPO_ROOT / "hooks" / hook)],
        cwd=cwd,
        input=json.dumps(payload or {}),
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(cwd), "COGNITIVE_OS_PROJECT_DIR": str(cwd), **(env or {})},
    )


def test_dequeue_notify_emits_dispatch_and_metric_when_slot_available(tmp_path: Path) -> None:
    (tmp_path / ".cognitive-os" / "tasks").mkdir(parents=True)
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True)
    (tmp_path / "cognitive-os.yaml").write_text("resources:\n  compute:\n    max_parallel_agents: 2\n")
    (tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json").write_text(
        json.dumps({"tasks": [{"status": "in_progress"}]})
    )
    (tmp_path / ".cognitive-os" / "metrics" / "dispatch-gate.jsonl").write_text(
        json.dumps({"action": "block", "description": "queued agent"}) + "\n"
    )

    result = run_hook("dequeue-notify.sh", cwd=tmp_path, payload={"tool_name": "Agent"}, env={"TOOL_NAME": "Agent"})

    assert result.returncode == 0
    assert "DISPATCH: Slot freed" in result.stderr
    metric = tmp_path / ".cognitive-os" / "metrics" / "dequeue-notify.jsonl"
    assert metric.exists()
    assert "queued agent" in metric.read_text()


def test_memory_prefetch_writes_cache_when_provider_returns_context(tmp_path: Path) -> None:
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "memory_manager.py").write_text(
        "class EngramMemoryProvider:\n"
        "    def is_available(self): return True\n"
        "class MemoryManager:\n"
        "    def __init__(self): self.providers=[]\n"
        "    def add_provider(self, provider): self.providers.append(provider)\n"
        "    def prefetch_all(self, query): return 'memory for ' + query\n"
    )

    result = run_hook(
        "memory-prefetch.sh",
        cwd=tmp_path,
        env={"CLAUDE_TOOL_INPUT": json.dumps({"prompt": "auth context"})},
    )

    assert result.returncode == 0
    assert (tmp_path / ".cognitive-os" / "memory-prefetch-cache.txt").read_text() == "memory for auth context"


def test_profile_drift_autoapply_runs_profile_once_and_records_hash(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    marker = tmp_path / "applied.txt"
    profile = scripts / "apply-efficiency-profile.sh"
    profile.write_text(f"#!/usr/bin/env bash\necho applied >> {marker}\n")
    profile.chmod(0o755)

    first = run_hook("profile-drift-autoapply.sh", cwd=tmp_path)
    second = run_hook("profile-drift-autoapply.sh", cwd=tmp_path)

    assert first.returncode == 0
    assert second.returncode == 0
    assert marker.read_text().splitlines() == ["applied"]
    assert (tmp_path / ".cognitive-os" / "runtime" / "last-applied-profile.sha").exists()


def test_skill_frontmatter_validator_warns_and_strict_blocks_bad_skill(tmp_path: Path) -> None:
    skill = tmp_path / "skills" / "bad" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("# Missing frontmatter\n")
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(skill)}}

    warn = run_hook("skill-frontmatter-validator.sh", cwd=tmp_path, payload=payload)
    strict = run_hook("skill-frontmatter-validator.sh", cwd=tmp_path, payload=payload, env={"COS_STRICT_SKILL_VALIDATION": "1"})

    assert warn.returncode == 0
    assert "frontmatter incomplete" in warn.stderr
    assert strict.returncode == 2
    assert (tmp_path / ".cognitive-os" / "metrics" / "skill-frontmatter-warnings.jsonl").exists()

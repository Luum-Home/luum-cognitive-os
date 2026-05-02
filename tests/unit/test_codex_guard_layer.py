"""Contracts for the Codex governed-tool fallback layer."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENERIC_RUNNER = PROJECT_ROOT / "scripts" / "cos_governed_runner.py"
RUNNER = PROJECT_ROOT / "scripts" / "cos_codex_guard.py"


def _listed(action: str) -> list[str]:
    result = subprocess.run(
        ["python3", str(RUNNER), action, "--project-dir", str(PROJECT_ROOT), "--list"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)["scripts"]


def test_pre_agent_chain_covers_codex_omitted_agent_gates() -> None:
    scripts = set(_listed("pre-agent"))
    expected = {
        "hooks/session-heartbeat.sh",
        "hooks/lethal-trifecta-gate.sh",
        "hooks/dispatch-gate.sh",
        "hooks/clarification-gate.sh",
        "hooks/blast-radius.sh",
        "hooks/inject-phase-context.sh",
        "hooks/agent-working-dir-inject.sh",
        "hooks/query-tailored-context-inject.sh",
        "hooks/pre-agent-snapshot.sh",
        "hooks/agent-prelaunch.sh",
        "hooks/error-pattern-detector.sh",
        "hooks/predev-completeness-check.sh",
        "hooks/reinvention-check.sh",
        "hooks/native-agent-heartbeat.sh",
    }
    assert expected.issubset(scripts)


def test_post_agent_chain_covers_codex_omitted_quality_closure() -> None:
    scripts = set(_listed("post-agent"))
    expected = {
        "hooks/context-watchdog.sh",
        "hooks/rate-limit-detector.sh",
        "hooks/tool-sequence-capture.sh",
        "hooks/aci-observation-capture.sh",
        "hooks/claim-validator.sh",
        "hooks/completion-gate.sh",
        "hooks/agent-checkpoint.sh",
        "hooks/post-agent-snapshot-restore.sh",
        "hooks/trust-score-validator.sh",
        "hooks/confidence-gate.sh",
        "hooks/auto-rollback-trigger.sh",
        "hooks/work-queue-sync.sh",
        "hooks/skill-feedback-tracker.sh",
        "hooks/auto-repair-dispatcher.sh",
        "hooks/dequeue-notify.sh",
        "hooks/state-heartbeat.sh",
        "hooks/review-spawner.sh",
    }
    assert expected.issubset(scripts)


def test_pre_agent_snapshot_runs_after_blocking_agent_gates() -> None:
    scripts = _listed("pre-agent")
    assert scripts.index("hooks/pre-agent-snapshot.sh") > scripts.index("hooks/agent-prelaunch.sh")
    assert scripts.index("hooks/pre-agent-snapshot.sh") > scripts.index("hooks/reinvention-check.sh")


def test_edit_write_chain_covers_codex_omitted_file_gates() -> None:
    pre = set(_listed("pre-edit"))
    post = set(_listed("post-write"))
    assert {
        "hooks/session-heartbeat.sh",
        "hooks/lethal-trifecta-gate.sh",
        "hooks/secret-detector.sh",
        "hooks/project-docs-convention.sh",
        "hooks/edit-lock-pre-tool.sh",
    }.issubset(pre)
    assert {
        "hooks/context-watchdog.sh",
        "hooks/rate-limit-detector.sh",
        "hooks/tool-sequence-capture.sh",
        "hooks/aci-observation-capture.sh",
        "hooks/auto-checkpoint.sh",
        "hooks/content-policy.sh",
        "hooks/skill-frontmatter-validator.sh",
        "hooks/rule-frontmatter-validator.sh",
        "hooks/hook-header-validator.sh",
        "hooks/adr-section-validator.sh",
        "hooks/confidentiality-enforcer.sh",
        "hooks/surface-fix-detector.sh",
        "hooks/doc-sync-detector.sh",
        "hooks/edit-lock-drain-parked.sh",
    }.issubset(post)


def test_runner_executes_synthetic_chain_with_canonical_env(tmp_path: Path) -> None:
    hook = tmp_path / "hooks" / "capture.sh"
    metrics = tmp_path / "out.json"
    hook.parent.mkdir()
    hook.write_text(
        "#!/usr/bin/env bash\n"
        "payload=$(cat)\n"
        f"OUT_PATH={str(metrics)!r} PAYLOAD=\"$payload\" python3 -c '\n"
        "import json, os, pathlib\n"
        "payload = json.loads(os.environ[\"PAYLOAD\"])\n"
        "pathlib.Path(os.environ[\"OUT_PATH\"]).write_text(json.dumps({\"event\": payload[\"hook_event_name\"], \"tool\": payload[\"tool_name\"], \"root\": os.environ[\"COGNITIVE_OS_PROJECT_DIR\"], \"harness\": os.environ[\"COGNITIVE_OS_HARNESS\"]}))\n"
        "'\n"
    )
    hook.chmod(0o755)
    (tmp_path / "cognitive-os.yaml").write_text(
        "harness:\n"
        "  hooks:\n"
        "    capture:\n"
        "      script: hooks/capture.sh\n"
        "      event: PreToolUse\n"
        "      matcher: Agent\n"
        "      scope: os-only\n"
    )
    result = subprocess.run(
        [
            "python3",
            str(GENERIC_RUNNER),
            "--harness",
            "codex",
            "pre-agent",
            "--project-dir",
            str(tmp_path),
            "--prompt",
            "implement governed layer",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    captured = json.loads(metrics.read_text())
    assert captured == {
        "event": "PreToolUse",
        "tool": "Agent",
        "root": str(tmp_path.resolve()),
        "harness": "codex",
    }


def test_codex_wrapper_delegates_to_generic_runner() -> None:
    result = subprocess.run(
        ["python3", str(RUNNER), "pre-agent", "--project-dir", str(PROJECT_ROOT), "--list"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    listed = json.loads(result.stdout)
    assert listed["harness"] == "codex"
    assert listed["event"] == "PreToolUse"
    assert listed["matcher"] == "Agent"


def test_generic_runner_supports_future_harness_env(tmp_path: Path) -> None:
    hook = tmp_path / "hooks" / "capture.sh"
    metrics = tmp_path / "cursor-env.json"
    hook.parent.mkdir()
    hook.write_text(
        "#!/usr/bin/env bash\n"
        "payload=$(cat)\n"
        f"OUT_PATH={str(metrics)!r} PAYLOAD=\"$payload\" python3 -c '\n"
        "import json, os, pathlib\n"
        "payload = json.loads(os.environ[\"PAYLOAD\"])\n"
        "pathlib.Path(os.environ[\"OUT_PATH\"]).write_text(json.dumps({\"payload_harness\": payload[\"harness\"], \"env_harness\": os.environ[\"COGNITIVE_OS_HARNESS\"], \"cursor_root\": os.environ[\"CURSOR_PROJECT_DIR\"]}))\n"
        "'\n"
    )
    hook.chmod(0o755)
    (tmp_path / "cognitive-os.yaml").write_text(
        "harness:\n"
        "  hooks:\n"
        "    capture:\n"
        "      script: hooks/capture.sh\n"
        "      event: PostToolUse\n"
        "      matcher: Write\n"
        "      scope: os-only\n"
    )
    result = subprocess.run(
        [
            "python3",
            str(GENERIC_RUNNER),
            "--harness",
            "cursor",
            "post-write",
            "--project-dir",
            str(tmp_path),
            "--file-path",
            "x.txt",
            "--content",
            "hello",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    captured = json.loads(metrics.read_text())
    assert captured == {
        "payload_harness": "cursor",
        "env_harness": "cursor",
        "cursor_root": str(tmp_path.resolve()),
    }

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COS = PROJECT_ROOT / "scripts" / "cos"


def run_cos_team(tmp_path: Path, *args: str) -> dict:
    result = subprocess.run(
        [str(COS), "team", "--json", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    return json.loads(result.stdout)


@pytest.mark.behavior
def test_cos_team_cli_task_message_and_handoff_flow(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    joined = run_cos_team(
        project,
        "--project-dir",
        str(project),
        "join",
        "--team",
        "release",
        "--session-id",
        "lead",
        "--role",
        "lead",
        "--worktree-path",
        str(project),
    )
    assert joined["status"] == "joined"

    created = run_cos_team(
        project,
        "--project-dir",
        str(project),
        "task",
        "create",
        "--team",
        "release",
        "--task-id",
        "audit",
        "--title",
        "Audit release notes",
    )
    assert created["task"]["task_id"] == "audit"

    claimed = run_cos_team(
        project,
        "--project-dir",
        str(project),
        "task",
        "claim-next",
        "--team",
        "release",
        "--session-id",
        "worker",
    )
    assert claimed["status"] == "task_claimed"
    assert claimed["task"]["claimed_by"] == "worker"

    completed = run_cos_team(
        project,
        "--project-dir",
        str(project),
        "task",
        "complete",
        "--team",
        "release",
        "--task-id",
        "audit",
        "--session-id",
        "worker",
        "--output-summary",
        "clean",
    )
    assert completed["task"]["status"] == "completed"

    sent = run_cos_team(
        project,
        "--project-dir",
        str(project),
        "message",
        "send",
        "--team",
        "release",
        "--sender",
        "lead",
        "--recipient",
        "worker",
        "--text",
        "continue",
    )
    assert sent["status"] == "message_sent"

    handoff = run_cos_team(
        project,
        "--project-dir",
        str(project),
        "handoff",
        "send",
        "--team",
        "release",
        "--from-agent",
        "lead",
        "--to-agent",
        "worker",
        "--text",
        "take over docs",
        "--handoff-id",
        "handoff-1",
    )
    assert handoff["status"] == "handoff_sent"
    assert handoff["handoff"]["handoff_id"] == "handoff-1"

    inbox = run_cos_team(
        project,
        "--project-dir",
        str(project),
        "inbox",
        "--team",
        "release",
        "--session-id",
        "worker",
    )
    texts = [message["text"] for message in inbox["messages"]]
    assert "continue" in texts
    handoff_payloads = [json.loads(text) for text in texts if text.startswith('{"handoff"') or '"type": "handoff"' in text]
    assert handoff_payloads[0]["type"] == "handoff"
    assert handoff_payloads[0]["handoff"]["to_agent"] == "worker"

@pytest.mark.behavior
def test_cos_team_handoff_receive_executes_once(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    output = project / "received.txt"
    run_cos_team(
        project,
        "--project-dir", str(project),
        "handoff", "send",
        "--team", "release",
        "--from-agent", "lead",
        "--to-agent", "worker",
        "--text", "hello receiver",
        "--handoff-id", "receive-1",
    )
    received = run_cos_team(
        project,
        "--project-dir", str(project),
        "handoff", "receive",
        "--team", "release",
        "--session-id", "worker",
        "--exec-command-template", f"printf '{{text}}' > {output}",
        "--once",
    )
    assert received["received"][0]["executed"] is True
    assert output.read_text() == "hello receiver"

    second = run_cos_team(
        project,
        "--project-dir", str(project),
        "handoff", "receive",
        "--team", "release",
        "--session-id", "worker",
        "--once",
    )
    assert second["received"] == []

@pytest.mark.behavior
def test_cos_team_handoff_receive_runs_external_hook_with_env_and_stdin(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    hook = project / "hook.py"
    out = project / "hook-output.json"
    hook.write_text(
        "import json, os, sys\n"
        f"json.dump({{'id': os.environ['COS_HANDOFF_ID'], 'to': os.environ['COS_HANDOFF_TO_AGENT'], 'stdin': json.loads(sys.stdin.read())}}, open({str(out)!r}, 'w'))\n"
    )
    run_cos_team(
        project,
        "--project-dir", str(project),
        "handoff", "send",
        "--team", "release",
        "--from-agent", "lead",
        "--to-agent", "worker",
        "--text", "external hook",
        "--handoff-id", "hook-1",
    )
    received = run_cos_team(
        project,
        "--project-dir", str(project),
        "handoff", "receive",
        "--team", "release",
        "--session-id", "worker",
        "--hook-command", f"python3 {hook}",
        "--once",
    )
    assert received["received"][0]["executed"] is True
    payload = json.loads(out.read_text())
    assert payload["id"] == "hook-1"
    assert payload["to"] == "worker"
    assert payload["stdin"]["handoff_id"] == "hook-1"


@pytest.mark.behavior
def test_cos_team_handoff_receive_timeout_writes_receipt_in_strict_mode(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    run_cos_team(
        project,
        "--project-dir", str(project),
        "handoff", "send",
        "--team", "release",
        "--from-agent", "lead",
        "--to-agent", "worker",
        "--text", "timeout",
        "--handoff-id", "timeout-1",
    )
    result = subprocess.run(
        [
            str(COS), "team", "--json",
            "--project-dir", str(project),
            "handoff", "receive",
            "--team", "release",
            "--session-id", "worker",
            "--hook-command", "python3 -c 'import time; time.sleep(2)'",
            "--timeout-seconds", "1",
            "--strict",
            "--once",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 2
    receipt = project / ".cognitive-os/teams/release/handoff-receipts/timeout-1.json"
    data = json.loads(receipt.read_text())
    assert data["exit_code"] == 124
    assert data["error"] == "receiver_timeout"

@pytest.mark.behavior
def test_cos_team_transport_plan_cli_exposes_nats_upgrade_mapping(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    result = run_cos_team(
        project,
        "--project-dir", str(project),
        "transport-plan",
        "--team", "release",
        "--backend", "nats",
    )
    assert result["transport_plan"]["status"] == "upgrade_target"
    assert result["transport_plan"]["subject_mapping"]["handoffs"] == "cos.teams.release.handoffs.<session_id>"

@pytest.mark.behavior
def test_cos_team_transport_send_a2a_http_posts_message(tmp_path: Path) -> None:
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    received: dict[str, object] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers["Content-Length"])
            received.update(json.loads(self.rfile.read(length)))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *args):  # noqa: ANN001
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    project = tmp_path / "project"
    project.mkdir()
    try:
        result = run_cos_team(
            project,
            "--project-dir", str(project),
            "transport-send",
            "--team", "release",
            "--backend", "a2a",
            "--session-id", "worker",
            "--sender", "lead",
            "--text", "hello a2a",
            "--endpoint", f"http://127.0.0.1:{server.server_port}/a2a",
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert result["status"] == "sent"
    assert received["recipient"] == "worker"
    assert received["message_part"]["text"] == "hello a2a"


@pytest.mark.behavior
def test_cos_team_transport_send_nats_dry_run_plan(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    result = run_cos_team(
        project,
        "--project-dir", str(project),
        "transport-send",
        "--team", "release",
        "--backend", "nats",
        "--session-id", "worker",
        "--sender", "lead",
        "--text", "hello nats",
        "--allow-missing-nats",
    )
    assert result["status"] == "planned"
    assert result["transport_send"]["destination"] == "cos.teams.release.inbox.worker"

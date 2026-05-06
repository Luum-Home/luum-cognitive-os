from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO = Path(__file__).resolve().parents[2]
COSD = REPO / "scripts" / "cosd"
HOOK = REPO / "hooks" / "cosd-intent-submit.sh"


def run_cosd(project: Path, *args: str) -> dict:
    result = subprocess.run(
        ["bash", str(COSD), "--project-dir", str(project), "--json", *args],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


def wait_result(project: Path, intent_id: str) -> dict:
    path = project / ".cognitive-os" / "cosd" / "results" / f"{intent_id}.json"
    deadline = time.time() + 5
    while time.time() < deadline:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        time.sleep(0.05)
    raise AssertionError(f"missing result for {intent_id}")


def test_cosd_start_arbitrates_competing_adr_numbers_and_stops(tmp_path: Path) -> None:
    adrs = tmp_path / "docs" / "adrs"
    adrs.mkdir(parents=True)
    (adrs / "ADR-001-existing.md").write_text("# ADR-001: Existing\n", encoding="utf-8")

    try:
        started = run_cosd(tmp_path, "start", "--interval-seconds", "0.05")
        assert started["status"] == "running"
        assert isinstance(started["pid"], int)

        run_cosd(
            tmp_path,
            "submit-intent",
            "--kind",
            "adr-number-request",
            "--intent-id",
            "intent-a",
            "--session-id",
            "s1",
            "--topic",
            "Alpha surface",
            "--filename-stem",
            "alpha-surface",
        )
        run_cosd(
            tmp_path,
            "submit-intent",
            "--kind",
            "adr-number-request",
            "--intent-id",
            "intent-b",
            "--session-id",
            "s2",
            "--topic",
            "Beta surface",
            "--filename-stem",
            "beta-surface",
        )

        a = wait_result(tmp_path, "intent-a")
        b = wait_result(tmp_path, "intent-b")
        assert {a["decision"]["adr_number"], b["decision"]["adr_number"]} == {2, 3}

        status = run_cosd(tmp_path, "status")
        assert status["intent_queue_depth"] == 0
        assert len(status["last_arbitrations"]) >= 2
    finally:
        stopped = run_cosd(tmp_path, "stop")
        assert stopped["status"] == "stopped"


def test_cosd_rejects_tombstone_for_active_adr(tmp_path: Path) -> None:
    adrs = tmp_path / "docs" / "adrs"
    adrs.mkdir(parents=True)
    (adrs / "ADR-171-active-decision.md").write_text("# ADR-171: Active\n", encoding="utf-8")

    try:
        run_cosd(tmp_path, "start", "--interval-seconds", "0.05")
        run_cosd(
            tmp_path,
            "submit-intent",
            "--kind",
            "adr-tombstone-request",
            "--intent-id",
            "intent-tombstone",
            "--session-id",
            "s3",
            "--adr-number",
            "171",
            "--candidate-filename",
            "ADR-171-tombstone.md",
        )
        result = wait_result(tmp_path, "intent-tombstone")
        assert result["status"] == "rejected"
        assert result["decision"]["adr_number"] == 171
    finally:
        run_cosd(tmp_path, "stop")


def test_cosd_intent_submit_hook_uses_daemon_cli(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            "bash",
            str(HOOK),
            "submit-intent",
            "--kind",
            "adr-number-request",
            "--intent-id",
            "hook-intent",
            "--session-id",
            "hook-session",
            "--topic",
            "Hook submitted",
        ],
        cwd=REPO,
        env={"CLAUDE_PROJECT_DIR": str(tmp_path), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / ".cognitive-os" / "cosd" / "intents" / "hook-intent.json").exists()


def test_cosd_local_http_api_submits_and_processes_intent(tmp_path: Path) -> None:
    adrs = tmp_path / "docs" / "adrs"
    adrs.mkdir(parents=True)
    api_file = tmp_path / ".cognitive-os" / "cosd" / "runtime" / "cosd-api.json"
    proc = subprocess.Popen(
        ["bash", str(COSD), "--project-dir", str(tmp_path), "serve", "--host", "127.0.0.1", "--port", "0"],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.time() + 5
        while time.time() < deadline and not api_file.exists():
            if proc.poll() is not None:
                stdout, stderr = proc.communicate(timeout=1)
                raise AssertionError(f"cosd api exited early: {stdout} {stderr}")
            time.sleep(0.05)
        assert api_file.exists(), "cosd API did not publish runtime endpoint metadata"
        api = json.loads(api_file.read_text(encoding="utf-8"))
        base_url = api["base_url"]

        from urllib import request

        with request.urlopen(f"{base_url}/healthz", timeout=5) as response:
            assert response.status == 200
            assert json.loads(response.read().decode("utf-8"))["status"] == "ok"

        payload = json.dumps(
            {
                "kind": "adr-number-request",
                "intent_id": "api-intent",
                "session_id": "api-session",
                "context": {"topic": "API intent", "filename_stem": "api-intent"},
            }
        ).encode("utf-8")
        req = request.Request(f"{base_url}/submit-intent", data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with request.urlopen(req, timeout=5) as response:
            submitted = json.loads(response.read().decode("utf-8"))
        assert submitted["status"] == "submitted"

        req = request.Request(f"{base_url}/process-once", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        with request.urlopen(req, timeout=5) as response:
            processed = json.loads(response.read().decode("utf-8"))
        assert processed["processed_count"] == 1

        result = wait_result(tmp_path, "api-intent")
        assert result["status"] == "granted"
        assert result["decision"]["reserved_filename"] == "ADR-001-api-intent.md"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def _unix_http_json(socket_path: Path, request_text: str) -> dict:
    import socket

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(5)
        client.connect(str(socket_path))
        client.sendall(request_text.encode("utf-8"))
        chunks: list[bytes] = []
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
    raw = b"".join(chunks).decode("utf-8")
    _, body = raw.split("\r\n\r\n", 1)
    return json.loads(body)


def test_cosd_unix_socket_api_submits_and_processes_intent(tmp_path: Path) -> None:
    (tmp_path / "docs" / "adrs").mkdir(parents=True)
    socket_path = Path("/tmp") / f"cosd-{tmp_path.name}.sock"
    try:
        socket_path.unlink()
    except FileNotFoundError:
        pass
    proc = subprocess.Popen(
        ["bash", str(COSD), "--project-dir", str(tmp_path), "serve-unix", "--socket", str(socket_path)],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.time() + 5
        while time.time() < deadline and not socket_path.exists():
            if proc.poll() is not None:
                stdout, stderr = proc.communicate(timeout=1)
                raise AssertionError(f"cosd unix api exited early: {stdout} {stderr}")
            time.sleep(0.05)
        assert socket_path.exists(), "cosd Unix socket was not created"

        health = _unix_http_json(socket_path, "GET /healthz HTTP/1.1\r\nHost: cosd\r\nConnection: close\r\n\r\n")
        assert health["status"] == "ok"

        body = json.dumps(
            {
                "kind": "adr-number-request",
                "intent_id": "unix-intent",
                "session_id": "unix-session",
                "context": {"topic": "Unix API intent", "filename_stem": "unix-api-intent"},
            }
        )
        submitted = _unix_http_json(
            socket_path,
            "POST /submit-intent HTTP/1.1\r\n"
            "Host: cosd\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(body.encode('utf-8'))}\r\n"
            "Connection: close\r\n\r\n"
            f"{body}",
        )
        assert submitted["status"] == "submitted"

        processed = _unix_http_json(
            socket_path,
            "POST /process-once HTTP/1.1\r\nHost: cosd\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}",
        )
        assert processed["processed_count"] == 1
        result = wait_result(tmp_path, "unix-intent")
        assert result["decision"]["reserved_filename"] == "ADR-001-unix-api-intent.md"
    finally:
        proc.terminate()
        try:
            socket_path.unlink()
        except FileNotFoundError:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

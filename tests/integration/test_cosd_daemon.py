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
    adrs = tmp_path / "docs" / "02-Decisions" / "adrs"
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
    adrs = tmp_path / "docs" / "02-Decisions" / "adrs"
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
    adrs = tmp_path / "docs" / "02-Decisions" / "adrs"
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
    (tmp_path / "docs" / "02-Decisions" / "adrs").mkdir(parents=True)
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


def _read_http_error(req: object) -> tuple[int, dict]:
    from urllib import error, request

    try:
        request.urlopen(req, timeout=5)
    except error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))
    raise AssertionError("expected HTTPError")


def test_cosd_remote_bind_requires_allow_remote_and_token(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(COSD), "--project-dir", str(tmp_path), "--json", "serve", "--host", "0.0.0.0", "--port", "0"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert "--allow-remote" in payload["reason"]

    result = subprocess.run(
        ["bash", str(COSD), "--project-dir", str(tmp_path), "--json", "serve", "--host", "0.0.0.0", "--port", "0", "--allow-remote"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert "token" in payload["reason"]


def test_cosd_token_auth_protects_status_and_write_endpoints(tmp_path: Path) -> None:
    (tmp_path / "docs" / "02-Decisions" / "adrs").mkdir(parents=True)
    token_file = tmp_path / "cosd.token"
    token_file.write_text("secret-token\n", encoding="utf-8")
    api_file = tmp_path / ".cognitive-os" / "cosd" / "runtime" / "cosd-api.json"
    proc = subprocess.Popen(
        ["bash", str(COSD), "--project-dir", str(tmp_path), "serve", "--host", "127.0.0.1", "--port", "0", "--token-file", str(token_file)],
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
        api = json.loads(api_file.read_text(encoding="utf-8"))
        assert api["auth_required"] is True
        base_url = api["base_url"]

        from urllib import request

        with request.urlopen(f"{base_url}/healthz", timeout=5) as response:
            assert response.status == 200

        code, unauthorized = _read_http_error(f"{base_url}/status")
        assert code == 401
        assert unauthorized["status"] == "unauthorized"

        wrong = request.Request(f"{base_url}/status", headers={"Authorization": "Bearer wrong"})
        code, unauthorized = _read_http_error(wrong)
        assert code == 401
        assert unauthorized["status"] == "unauthorized"

        ok = request.Request(f"{base_url}/status", headers={"Authorization": "Bearer secret-token"})
        with request.urlopen(ok, timeout=5) as response:
            assert response.status == 200
            assert json.loads(response.read().decode("utf-8"))["ok"] is True

        body = json.dumps(
            {
                "kind": "adr-number-request",
                "intent_id": "secure-intent",
                "session_id": "secure-session",
                "context": {"topic": "Secure API intent", "filename_stem": "secure-api-intent"},
            }
        ).encode("utf-8")
        no_auth = request.Request(f"{base_url}/submit-intent", data=body, headers={"Content-Type": "application/json"}, method="POST")
        code, unauthorized = _read_http_error(no_auth)
        assert code == 401
        assert unauthorized["status"] == "unauthorized"

        authed = request.Request(
            f"{base_url}/submit-intent",
            data=body,
            headers={"Content-Type": "application/json", "Authorization": "Bearer secret-token"},
            method="POST",
        )
        with request.urlopen(authed, timeout=5) as response:
            submitted = json.loads(response.read().decode("utf-8"))
        assert submitted["status"] == "submitted"

        process_req = request.Request(
            f"{base_url}/process-once",
            data=b"{}",
            headers={"Content-Type": "application/json", "Authorization": "Bearer secret-token"},
            method="POST",
        )
        with request.urlopen(process_req, timeout=5) as response:
            assert json.loads(response.read().decode("utf-8"))["processed_count"] == 1
        assert wait_result(tmp_path, "secure-intent")["decision"]["reserved_filename"] == "ADR-001-secure-api-intent.md"

        audit_path = tmp_path / ".cognitive-os" / "cosd" / "api-audit.jsonl"
        rows = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
        assert any(row["status"] == "unauthorized" for row in rows)
        assert any(row.get("intent_id") == "secure-intent" for row in rows)
        assert "secret-token" not in audit_path.read_text(encoding="utf-8")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_cosd_allow_remote_starts_only_with_token(tmp_path: Path) -> None:
    token_file = tmp_path / "cosd.token"
    token_file.write_text("remote-token\n", encoding="utf-8")
    api_file = tmp_path / ".cognitive-os" / "cosd" / "runtime" / "cosd-api.json"
    proc = subprocess.Popen(
        [
            "bash",
            str(COSD),
            "--project-dir",
            str(tmp_path),
            "serve",
            "--host",
            "0.0.0.0",
            "--port",
            "0",
            "--allow-remote",
            "--token-file",
            str(token_file),
        ],
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
                raise AssertionError(f"cosd remote api exited early: {stdout} {stderr}")
            time.sleep(0.05)
        api = json.loads(api_file.read_text(encoding="utf-8"))
        assert api["remote_allowed"] is True
        assert api["auth_required"] is True
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_cosd_task_api_submits_runs_and_guards_provider_calls(tmp_path: Path) -> None:
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
                raise AssertionError(f"cosd task api exited early: {stdout} {stderr}")
            time.sleep(0.05)
        api = json.loads(api_file.read_text(encoding="utf-8"))
        base_url = api["base_url"]

        from urllib import request

        with request.urlopen(f"{base_url}/tasks", timeout=5) as response:
            drained = json.loads(response.read().decode("utf-8"))
        assert drained["status"] == "drained"

        submit_body = json.dumps(
            {
                "kind": "local-command",
                "task_id": "api-task",
                "command": "printf task-ok",
                "requested_by": "test",
            }
        ).encode("utf-8")
        submit_req = request.Request(f"{base_url}/tasks/submit", data=submit_body, headers={"Content-Type": "application/json"}, method="POST")
        with request.urlopen(submit_req, timeout=5) as response:
            submitted = json.loads(response.read().decode("utf-8"))
        assert submitted["status"] == "submitted"
        assert submitted["task"]["approval_policy"] == "propose-only"

        run_req = request.Request(f"{base_url}/tasks/run-once", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        with request.urlopen(run_req, timeout=5) as response:
            executed = json.loads(response.read().decode("utf-8"))
        assert executed["status"] == "completed"
        assert executed["task_id"] == "api-task"

        provider_body = json.dumps(
            {
                "kind": "provider",
                "task_id": "provider-task",
                "executor": "codex-cli-host",
                "prompt": "summarize status",
            }
        ).encode("utf-8")
        provider_req = request.Request(f"{base_url}/tasks/submit", data=provider_body, headers={"Content-Type": "application/json"}, method="POST")
        code, rejected = _read_http_error(provider_req)
        assert code == 400
        assert "dry_run=true" in rejected["reason"]

        provider_run = request.Request(
            f"{base_url}/tasks/run-once",
            data=json.dumps({"allow_provider_call": True}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        code, rejected = _read_http_error(provider_run)
        assert code == 400
        assert "does not allow provider calls" in rejected["reason"]
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

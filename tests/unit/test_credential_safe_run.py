"""Unit tests for credential-safe script runner."""

from __future__ import annotations

import json
import base64
import hashlib
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts.cos_credential_safe_run import run_credential_safe

REPO = Path(__file__).resolve().parents[2]


def _write_executable(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _project(tmp_path: Path, script_body: str) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    _write_executable(project / "scripts" / "smoke-qwen-fallback.sh", script_body)
    return project


def _manifest_for(project: Path) -> Path:
    data = yaml.safe_load((REPO / "manifests" / "credential-safe-scripts.yaml").read_text(encoding="utf-8"))
    smoke = project / "scripts" / "smoke-qwen-fallback.sh"
    data["scripts"][0]["command_integrity"]["sha256"] = hashlib.sha256(smoke.read_bytes()).hexdigest()
    path = project / "credential-safe-scripts.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _run(project: Path, *, env_file: Path = Path(".env"), approved: bool = True):
    return run_credential_safe(
        "qwen-fallback-smoke",
        project_dir=project,
        env_file=env_file,
        approved=approved,
        manifest_path=_manifest_for(project),
    )


def test_requires_explicit_approval(tmp_path: Path) -> None:
    project = _project(tmp_path, "#!/usr/bin/env bash\necho ok\n")
    (project / ".env").write_text("ALIBABA_QWEN_API_KEY=sk-secret1234567890\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="requires --approve"):
        _run(project, approved=False)


def test_redacts_allowed_secret_values_from_stdout_stderr_and_audit(tmp_path: Path) -> None:
    secret = "sk-qwenSECRET1234567890"
    base_url = "https://workspace-secret.example/v1"
    project = _project(
        tmp_path,
        "#!/usr/bin/env bash\n"
        "echo stdout-key=$ALIBABA_QWEN_API_KEY\n"
        "echo stderr-url=$ALIBABA_QWEN_BASE_URL >&2\n"
        "echo skip=$COS_SKIP_DOTENV\n",
    )
    (project / ".env").write_text(
        f"ALIBABA_QWEN_API_KEY={secret}\nALIBABA_QWEN_BASE_URL={base_url}\n",
        encoding="utf-8",
    )

    result = _run(project)

    combined = result.stdout + result.stderr
    assert secret not in combined
    assert base_url not in combined
    assert "[REDACTED]" in combined
    assert "skip=1" in result.stdout
    audit = Path(result.audit_path).read_text(encoding="utf-8")
    assert secret not in audit
    assert base_url not in audit
    assert "ALIBABA_QWEN_API_KEY" in audit
    assert "redaction_count" in audit


def test_only_allowlisted_env_file_keys_are_passed(tmp_path: Path) -> None:
    project = _project(
        tmp_path,
        "#!/usr/bin/env bash\n"
        "echo qwen=${ALIBABA_QWEN_API_KEY:-missing}\n"
        "echo other=${OTHER_SECRET:-missing}\n"
        "echo token=${API_TOKEN:-missing}\n",
    )
    (project / ".env").write_text(
        "ALIBABA_QWEN_API_KEY=sk-allowedsecret123456\nOTHER_SECRET=do-not-pass\nAPI_TOKEN=also-do-not-pass\n",
        encoding="utf-8",
    )

    result = _run(project)

    assert "do-not-pass" not in result.stdout
    assert "also-do-not-pass" not in result.stdout
    assert "other=missing" in result.stdout
    assert "token=missing" in result.stdout


def test_parent_non_allowlisted_env_keys_are_removed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OTHER_SECRET", "parent-secret")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-parent-secret")
    monkeypatch.setenv("UNLISTED_TOKEN", "unlisted-parent-token")
    project = _project(
        tmp_path,
        "#!/usr/bin/env bash\n"
        "echo other=${OTHER_SECRET:-missing}\n"
        "echo aws=${AWS_SECRET_ACCESS_KEY:-missing}\n"
        "echo token=${UNLISTED_TOKEN:-missing}\n",
    )
    (project / ".env").write_text("ALIBABA_QWEN_API_KEY=sk-allowedsecret123456\n", encoding="utf-8")

    result = _run(project)

    assert "parent-secret" not in result.stdout
    assert "aws-parent-secret" not in result.stdout
    assert "unlisted-parent-token" not in result.stdout
    assert "other=missing" in result.stdout
    assert "aws=missing" in result.stdout
    assert "token=missing" in result.stdout


def test_allowlisted_parent_env_value_is_passed_and_redacted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    secret = "sk-parentSECRET1234567890"
    monkeypatch.setenv("ALIBABA_QWEN_API_KEY", secret)
    project = _project(tmp_path, "#!/usr/bin/env bash\necho parent=$ALIBABA_QWEN_API_KEY\n")
    (project / ".env").write_text("", encoding="utf-8")

    result = _run(project)

    assert secret not in result.stdout
    assert "parent=[REDACTED]" in result.stdout


def test_redacts_encoded_secret_variants(tmp_path: Path) -> None:
    secret = "sk-encodedSECRET1234567890"
    encoded = base64.b64encode(secret.encode("utf-8")).decode("ascii")
    project = _project(tmp_path, f"#!/usr/bin/env bash\necho encoded={encoded}\n")
    (project / ".env").write_text(f"ALIBABA_QWEN_API_KEY={secret}\n", encoding="utf-8")

    result = _run(project)

    assert secret not in result.stdout
    assert encoded not in result.stdout
    assert "encoded=[REDACTED]" in result.stdout


def test_truncates_model_visible_output(tmp_path: Path) -> None:
    project = _project(tmp_path, "#!/usr/bin/env bash\npython3 - <<'PY'\nprint('x' * 25000)\nPY\n")
    (project / ".env").write_text("ALIBABA_QWEN_API_KEY=sk-allowedsecret123456\n", encoding="utf-8")

    result = _run(project)

    assert "[TRUNCATED " in result.stdout
    assert len(result.stdout) < 20200


def test_rejects_modified_allowlisted_script(tmp_path: Path) -> None:
    project = _project(tmp_path, "#!/usr/bin/env bash\necho ok\n")
    manifest = _manifest_for(project)
    (project / "scripts" / "smoke-qwen-fallback.sh").write_text("#!/usr/bin/env bash\necho pwned\n", encoding="utf-8")
    (project / ".env").write_text("ALIBABA_QWEN_API_KEY=sk-allowedsecret123456\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="command integrity mismatch"):
        run_credential_safe(
            "qwen-fallback-smoke",
            project_dir=project,
            env_file=Path(".env"),
            approved=True,
            manifest_path=manifest,
        )


def test_rejects_non_allowlisted_env_file(tmp_path: Path) -> None:
    project = _project(tmp_path, "#!/usr/bin/env bash\necho ok\n")
    (project / "secrets.env").write_text("ALIBABA_QWEN_API_KEY=sk-secret123456\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="env file is not allowlisted"):
        _run(project, env_file=Path("secrets.env"))


def test_rejects_env_file_outside_project(tmp_path: Path) -> None:
    project = _project(tmp_path, "#!/usr/bin/env bash\necho ok\n")
    outside = tmp_path / ".env"
    outside.write_text("ALIBABA_QWEN_API_KEY=sk-secret123456\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="inside the project directory"):
        _run(project, env_file=outside)


def test_unknown_script_id_is_rejected(tmp_path: Path) -> None:
    project = _project(tmp_path, "#!/usr/bin/env bash\necho ok\n")
    with pytest.raises(SystemExit, match="unsupported credential-safe script id"):
        run_credential_safe("arbitrary", project_dir=project, env_file=Path(".env"), approved=True)


def test_cli_json_output_is_redacted(tmp_path: Path) -> None:
    secret = "sk-jsonSECRET1234567890"
    project = _project(tmp_path, "#!/usr/bin/env bash\necho $ALIBABA_QWEN_API_KEY\n")
    (project / ".env").write_text(f"ALIBABA_QWEN_API_KEY={secret}\n", encoding="utf-8")

    proc = subprocess.run(
        [
            "python3",
            str(REPO / "scripts" / "cos_credential_safe_run.py"),
            "qwen-fallback-smoke",
            "--project-dir",
            str(project),
            "--manifest",
            str(_manifest_for(project)),
            "--approve",
            "--json",
        ],
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert proc.returncode == 0
    assert secret not in proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["stdout"].strip() == "[REDACTED]"
    assert payload["loaded_keys"] == ["ALIBABA_QWEN_API_KEY"]

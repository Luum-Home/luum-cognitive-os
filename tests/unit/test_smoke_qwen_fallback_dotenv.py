"""Tests for scripts/smoke-qwen-fallback.sh dotenv loading controls."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "smoke-qwen-fallback.sh"


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _make_fake_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / "scripts").mkdir(parents=True)
    shutil.copy2(SCRIPT, project / "scripts" / "smoke-qwen-fallback.sh")
    (project / "bin").mkdir()

    _write_executable(
        project / "bin" / "python3",
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            if [[ "$1" == "scripts/cos-config-audit.sh" ]]; then
              echo 'meta.llm_providers_reachable [ IMPL  ] fake'
              exit 0
            fi
            echo 'unexpected python3 invocation: $*' >&2
            exit 9
            """
        ),
    )
    _write_executable(
        project / "bin" / "uv",
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            joined="$*"
            if [[ "$joined" == *"qwen_provider"* ]]; then
              if [[ -n "${ALIBABA_QWEN_API_KEY:-}" ]]; then
                echo 'SUCCESS=True ERROR='
              else
                echo 'UNCONFIGURED'
              fi
              exit 0
            fi
            if [[ "$joined" == *"_try_qwen_primary"* ]]; then
              echo 'FALLBACK_RESULT success=True provider=qwen'
              exit 0
            fi
            if [[ "$joined" == *"_fallback_disabled"* ]]; then
              echo 'SWITCH_RESPECTED'
              exit 0
            fi
            echo "unexpected uv invocation: $joined" >&2
            exit 9
            """
        ),
    )
    return project


def _run_smoke(project: Path, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{project / 'bin'}:{env.get('PATH', '')}",
            "ALIBABA_QWEN_API_KEY": "",
            "ALIBABA_QWEN_BASE_URL": "",
            "_COS_QWEN_DOTENV_LOADED": "",
        }
    )
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", "scripts/smoke-qwen-fallback.sh"],
        cwd=project,
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
    )


def test_default_loads_project_dotenv_when_present(tmp_path: Path) -> None:
    project = _make_fake_project(tmp_path)
    (project / ".env").write_text("ALIBABA_QWEN_API_KEY=from-dotenv\n", encoding="utf-8")

    result = _run_smoke(project)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "ALL 4 CHECKS PASS" in result.stdout


def test_cos_skip_dotenv_does_not_load_project_dotenv(tmp_path: Path) -> None:
    project = _make_fake_project(tmp_path)
    (project / ".env").write_text("ALIBABA_QWEN_API_KEY=from-dotenv\n", encoding="utf-8")

    result = _run_smoke(project, {"COS_SKIP_DOTENV": "1"})

    assert result.returncode == 2
    assert "UNCONFIGURED" not in result.stdout
    assert "COS_SKIP_DOTENV=1 requires exported env credentials" in result.stderr


def test_cos_skip_dotenv_allows_exported_credentials(tmp_path: Path) -> None:
    project = _make_fake_project(tmp_path)
    (project / ".env").write_text("ALIBABA_QWEN_API_KEY=from-dotenv\n", encoding="utf-8")

    result = _run_smoke(
        project,
        {"COS_SKIP_DOTENV": "1", "ALIBABA_QWEN_API_KEY": "from-exported-env"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "ALL 4 CHECKS PASS" in result.stdout

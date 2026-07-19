"""Hermetic smoke tests for dod-check stack detection in consumer-like projects."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
DOD_SCRIPT = REPO_ROOT / "packages" / "quality-gates" / "skills" / "dod-check" / "scripts" / "check_dod.py"


def _write(root: Path, rel: str, content: str = "") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _init_project(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)


def _run_dod(root: Path) -> dict:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(root)
    proc = subprocess.run(
        [sys.executable, str(DOD_SCRIPT), "--format", "json"],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(proc.stdout)


def test_smoke_node_next_storybook_ui_project(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _write(
        tmp_path,
        "package.json",
        json.dumps(
            {
                "dependencies": {"next": "1.0.0", "react": "1.0.0", "@storybook/nextjs": "1.0.0"},
                "devDependencies": {"vitest": "1.0.0", "typescript": "1.0.0"},
            }
        ),
    )
    _write(tmp_path, "pnpm-lock.yaml", "lockfileVersion: '9.0'\n")
    _write(tmp_path, "tsconfig.json", "{}")
    (tmp_path / ".storybook").mkdir()
    _write(tmp_path, "src/ui/buttons/button.tsx", "export const Button = () => null\n")
    _write(tmp_path, "src/stories/buttons/button.stories.tsx", "export default {}\n")

    report = _run_dod(tmp_path)

    assert {"ui-component", "storybook-docs"}.issubset(report["dod_profiles"])
    assert {"node", "nextjs", "react", "storybook", "typescript", "vitest", "pnpm"}.issubset(report["stack_signals"])
    assert report["verdict"] in {"PASS", "WARN"}


def test_smoke_python_fastapi_backend_project(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _write(
        tmp_path,
        "pyproject.toml",
        '[project]\ndependencies = ["fastapi", "pytest", "ruff", "mypy"]\n',
    )
    _write(tmp_path, "src/api/users.py", "def handler():\n    return {'ok': True}\n")

    report = _run_dod(tmp_path)

    assert "backend-api" in report["dod_profiles"]
    assert {"python", "fastapi", "pytest", "ruff", "mypy"}.issubset(report["stack_signals"])


def test_smoke_go_backend_project(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _write(tmp_path, "go.mod", "module example.com/app\n\ngo 1.23\n")
    _write(tmp_path, "internal/server/http.go", "package server\n")

    report = _run_dod(tmp_path)

    assert "backend-api" in report["dod_profiles"]
    assert "go" in report["stack_signals"]


def test_smoke_rust_backend_project(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _write(tmp_path, "Cargo.toml", '[package]\nname = "demo"\nversion = "0.1.0"\n')
    _write(tmp_path, "src/server/mod.rs", "pub fn run() {}\n")

    report = _run_dod(tmp_path)

    assert "backend-api" in report["dod_profiles"]
    assert "rust" in report["stack_signals"]


def test_smoke_unknown_stack_still_reports_base_dod_uncertainty(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _write(tmp_path, "docs/spec.txt", "plain text only\n")

    report = _run_dod(tmp_path)
    checks = {check["name"]: check for check in report["checks"]}

    assert report["dod_profiles"] == []
    assert report["stack_signals"] == []
    assert checks["dod_profiles"]["status"] == "PASS"
    assert checks["stack_signals"]["status"] == "WARN"


@pytest.mark.parametrize(
    ("manifest", "manifest_content", "changed_path", "expected_signal"),
    [
        ("pom.xml", "<project></project>\n", "src/main/java/com/example/server/App.java", "maven"),
        ("build.gradle", "plugins { id 'java' }\n", "src/main/kotlin/com/example/server/App.kt", "gradle"),
        ("App.csproj", "<Project Sdk=\"Microsoft.NET.Sdk.Web\"></Project>\n", "src/server/Program.cs", "dotnet"),
        ("Gemfile", "source 'https://rubygems.org'\n", "app/api/users.rb", "ruby"),
        ("composer.json", "{\"require\":{}}\n", "src/api/users.php", "php"),
        ("mix.exs", "defmodule Demo.MixProject do\nend\n", "cos_lib/server/handler.ex", "elixir"),
        ("deno.json", "{}\n", "src/server/main.ts", "deno"),
        ("Dockerfile", "FROM scratch\n", "src/server/main.py", "docker"),
        ("docker-compose.yml", "services: {}\n", "src/server/main.py", "docker-compose"),
    ],
)
def test_smoke_backend_stack_manifest_matrix(
    tmp_path: Path,
    manifest: str,
    manifest_content: str,
    changed_path: str,
    expected_signal: str,
) -> None:
    _init_project(tmp_path)
    _write(tmp_path, manifest, manifest_content)
    _write(tmp_path, changed_path, "placeholder\n")

    report = _run_dod(tmp_path)

    assert "backend-api" in report["dod_profiles"]
    assert expected_signal in report["stack_signals"]

#!/usr/bin/env python3
# SCOPE: os-only
"""Evaluate Python-to-Rust transpilers on selected scripts without replacing source files."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_CANDIDATES = [
    "scripts/agentic_mastery_summary.py",
    "scripts/regen_catalog_bullets.py",
    "scripts/backfill_cost_events.py",
]
DEFAULT_TOOLS = ["py2many", "tnk"]


@dataclass(frozen=True)
class RunResult:
    tool: str
    candidate: str
    exit_code: int | None
    generated_files: list[str]
    elapsed_ms: int
    stdout_excerpt: str
    stderr_excerpt: str
    compile_exit_code: int | None
    compile_excerpt: str
    manual_fix_cost: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "candidate": self.candidate,
            "exit_code": self.exit_code,
            "generated_files": self.generated_files,
            "elapsed_ms": self.elapsed_ms,
            "stdout_excerpt": self.stdout_excerpt,
            "stderr_excerpt": self.stderr_excerpt,
            "compile_exit_code": self.compile_exit_code,
            "compile_excerpt": self.compile_excerpt,
            "manual_fix_cost": self.manual_fix_cost,
            "status": self.status,
        }



def _candidate_label(project_dir: Path, candidate: Path) -> str:
    return str(candidate.relative_to(project_dir)) if candidate.is_relative_to(project_dir) else str(candidate)

def _run(cmd: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def _excerpt(text: str, limit: int = 2000) -> str:
    text = text.strip()
    return text[:limit]


def _sanitize(text: str, project_dir: Path) -> str:
    text = text.replace(str(project_dir), "<repo-root>")
    text = re.sub(r"/private/var/folders/[^\s)]+", "<tmp>", text)
    text = re.sub(r"/var/folders/[^\s)]+", "<tmp>", text)
    text = re.sub(r"/tmp/[^\s)]+", "<tmp>", text)
    return text


def _manual_fix_cost(exit_code: int | None, generated: list[str], compile_exit_code: int | None, stdout: str, stderr: str) -> tuple[str, str]:
    combined = f"{stdout}\n{stderr}".lower()
    if exit_code is None:
        return "blocked", "tool-missing"
    if exit_code == 0 and compile_exit_code == 0:
        return "low", "generated-and-compiles"
    if exit_code == 0 and generated and compile_exit_code not in (0, None):
        return "medium", "generated-but-compile-fails"
    if generated and any(token in combined for token in ["unsupported", "parse", "cannot", "error"]):
        return "high", "partial-output-with-tool-errors"
    if generated:
        return "medium", "partial-output"
    return "blocked", "no-usable-output"



def _cargo_check_project(project_output: Path, timeout: int) -> tuple[int, str]:
    with tempfile.TemporaryDirectory(prefix="cos-rust-transpiler-project-") as tmp:
        probe = Path(tmp) / "project"
        shutil.copytree(project_output, probe)
        result = _run(["cargo", "check"], probe, timeout)
        return result.returncode, _excerpt(result.stdout + result.stderr)

def _compile_single_rust(source: Path, timeout: int) -> tuple[int | None, str]:
    if not source.exists() or source.stat().st_size == 0 or source.read_text(errors="ignore").strip() == "FAILED":
        return None, ""
    with tempfile.TemporaryDirectory(prefix="cos-rust-transpiler-compile-") as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "src").mkdir()
        shutil.copy2(source, tmp_path / "src" / "main.rs")
        (tmp_path / "Cargo.toml").write_text(
            "[package]\nname = \"cos_transpiler_probe\"\nversion = \"0.1.0\"\nedition = \"2021\"\n\n"
            "[dependencies]\nanyhow = \"1\"\npathlib = \"0.1\"\n",
            encoding="utf-8",
        )
        result = _run(["cargo", "check"], tmp_path, timeout)
        return result.returncode, _excerpt(result.stdout + result.stderr)


def eval_py2many(project_dir: Path, candidate: Path, out_dir: Path, timeout: int) -> RunResult:
    tool_path = shutil.which("py2many")
    if not tool_path:
        return RunResult("py2many", _candidate_label(project_dir, candidate), None, [], 0, "", "py2many not found on PATH", None, "", "blocked", "tool-missing")
    start = time.monotonic()
    output_dir = out_dir / "py2many"
    output_dir.mkdir(parents=True, exist_ok=True)
    result = _run([tool_path, "--rust", "--outdir", str(output_dir), str(candidate)], project_dir, timeout)
    elapsed = int((time.monotonic() - start) * 1000)
    expected = output_dir / (candidate.stem + ".rs")
    generated = [str(expected.relative_to(out_dir))] if expected.exists() else []
    compile_code, compile_excerpt = _compile_single_rust(expected, timeout)
    cost, status = _manual_fix_cost(result.returncode, generated, compile_code, result.stdout, result.stderr)
    return RunResult(
        "py2many",
        _candidate_label(project_dir, candidate),
        result.returncode,
        generated,
        elapsed,
        _sanitize(_excerpt(result.stdout), project_dir),
        _sanitize(_excerpt(result.stderr), project_dir),
        compile_code,
        _sanitize(compile_excerpt, project_dir),
        cost,
        status,
    )


def eval_tnk(project_dir: Path, candidate: Path, out_dir: Path, timeout: int) -> RunResult:
    tool_path = shutil.which("tnk")
    if not tool_path:
        return RunResult("tnk", _candidate_label(project_dir, candidate), None, [], 0, "", "tnk not found on PATH", None, "", "blocked", "tool-missing")
    start = time.monotonic()
    output_dir = out_dir / "tnk"
    output_dir.mkdir(parents=True, exist_ok=True)
    direct_output = output_dir / f"{candidate.stem}.rs"
    result = _run([tool_path, str(candidate), "-o", str(direct_output)], project_dir, timeout)
    generated: list[str] = []
    compile_code: int | None = None
    compile_excerpt = ""
    stdout = result.stdout
    stderr = result.stderr
    if direct_output.exists():
        generated.append(str(direct_output.relative_to(out_dir)))
        compile_code, compile_excerpt = _compile_single_rust(direct_output, timeout)
    elif "--project" in stderr or "--project" in stdout:
        project_output = output_dir / f"{candidate.stem}_project"
        project_result = _run([tool_path, str(candidate), "--project", str(project_output)], project_dir, timeout)
        stdout = f"{stdout}\n--- project retry ---\n{project_result.stdout}"
        stderr = f"{stderr}\n--- project retry ---\n{project_result.stderr}"
        if project_output.exists():
            generated = sorted(str(path.relative_to(out_dir)) for path in project_output.rglob("*") if path.is_file())
            if (project_output / "Cargo.toml").exists():
                compile_code, compile_excerpt = _cargo_check_project(project_output, timeout)
    elapsed = int((time.monotonic() - start) * 1000)
    cost, status = _manual_fix_cost(result.returncode, generated, compile_code, stdout, stderr)
    return RunResult(
        "tnk",
        _candidate_label(project_dir, candidate),
        result.returncode,
        generated,
        elapsed,
        _sanitize(_excerpt(stdout), project_dir),
        _sanitize(_excerpt(stderr), project_dir),
        compile_code,
        _sanitize(compile_excerpt, project_dir),
        cost,
        status,
    )


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Rust Transpiler Evaluation Report",
        "",
        f"Schema: `{payload['schema_version']}`  ",
        f"Project: `{payload['project_dir']}`  ",
        "",
        "## Summary",
        "",
        "| Tool | Candidate | Status | Exit | Compile | Manual fix cost | Generated files |",
        "|---|---|---:|---:|---:|---|---:|",
    ]
    for row in payload["results"]:
        lines.append(
            "| {tool} | `{candidate}` | {status} | {exit_code} | {compile_exit_code} | {manual_fix_cost} | {generated} |".format(
                tool=row["tool"],
                candidate=row["candidate"],
                status=row["status"],
                exit_code="n/a" if row["exit_code"] is None else row["exit_code"],
                compile_exit_code="n/a" if row["compile_exit_code"] is None else row["compile_exit_code"],
                manual_fix_cost=row["manual_fix_cost"],
                generated=len(row["generated_files"]),
            )
        )
    lines.extend([
        "",
        "## Decision Rule",
        "",
        "A transpiler can become an official migration assistant only when it produces compiling Rust with low or medium manual-fix cost on representative fixtures and the Python↔Rust golden parity lane passes.",
        "",
        "No generated Rust from this lane replaces source code automatically.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=Path.cwd())
    parser.add_argument("--candidate", action="append", default=[])
    parser.add_argument("--tool", choices=DEFAULT_TOOLS, action="append", default=[])
    parser.add_argument("--out-dir", type=Path, default=Path(".cognitive-os/transpiler-eval/latest"))
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    candidates = [project_dir / path for path in (args.candidate or DEFAULT_CANDIDATES)]
    tools = args.tool or DEFAULT_TOOLS
    out_dir = args.out_dir if args.out_dir.is_absolute() else project_dir / args.out_dir
    for tool_dir in (out_dir / "py2many", out_dir / "tnk"):
        if tool_dir.exists():
            shutil.rmtree(tool_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[RunResult] = []
    for candidate in candidates:
        if "py2many" in tools:
            results.append(eval_py2many(project_dir, candidate, out_dir, args.timeout))
        if "tnk" in tools:
            results.append(eval_tnk(project_dir, candidate, out_dir, args.timeout))

    payload = {
        "schema_version": "rust-transpiler-eval/v1",
        "project_dir": "<repo-root>",
        "candidates": [str(path.relative_to(project_dir)) if path.is_relative_to(project_dir) else str(path) for path in candidates],
        "tools": tools,
        "results": [result.to_dict() for result in results],
    }
    if args.json_out:
        json_out = args.json_out if args.json_out.is_absolute() else project_dir / args.json_out
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.md_out:
        md_out = args.md_out if args.md_out.is_absolute() else project_dir / args.md_out
        md_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Portable publication-safety primitive.

Executes project-declared publication/readiness gates and emits a neutral
receipt. The primitive is intentionally project-configured: Cognitive OS owns
execution, normalization, and receipt shape; consumer repositories own their
publication commands and policy details.
"""
from __future__ import annotations
from lib.time_utils import now_iso as utc_now

import hashlib
import json
import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal

try:  # Optional because JSON manifests are supported without PyYAML.
    import yaml  # type: ignore[import]
except Exception:  # pragma: no cover - exercised only in minimal envs
    yaml = None  # type: ignore[assignment]

SCHEMA_VERSION = "publication-safety-receipt/v0"
CONFIG_SCHEMA_VERSION = "publication-safety-config/v0"
DEFAULT_CONFIG = Path("manifests/publication-safety.yaml")
DEFAULT_RECEIPT = Path(".cognitive-os/receipts/publication-safety/summary.json")
PASS_STATUSES = {"pass", "ok", "success", "skipped"}
WARN_STATUSES = {"warn", "warning"}
FAIL_STATUSES = {"fail", "failed", "block", "blocked", "error"}

Status = Literal["pass", "warn", "fail", "skipped"]


@dataclass(frozen=True)
class GateCommand:
    """One configured project publication gate."""

    id: str
    argv: tuple[str, ...]
    required: bool = True
    timeout_seconds: float = 300.0
    cwd: str | None = None
    parse_json: bool = True
    expected_statuses: tuple[str, ...] = ("pass", "ok", "success", "skipped")
    env: tuple[tuple[str, str], ...] = ()


class PublicationSafetyConfigError(ValueError):
    """Raised when the publication-safety config is invalid."""




def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _load_structured_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"publication-safety config not found: {path}")
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        if yaml is None:
            # Minimal dependency-free fallback for the shipped disabled template.
            # Enabled YAML configs with commands still require PyYAML or JSON; the
            # default template must not break `cos publication safety` on systems
            # where only stdlib Python is available.
            lines = [line.split("#", 1)[0].rstrip() for line in text.splitlines()]
            stripped = "\n".join(line for line in lines if line.strip())
            if "commands: []" in stripped:
                return {
                    "schema_version": CONFIG_SCHEMA_VERSION,
                    "enabled": "enabled: true" in stripped,
                    "mode": "strict",
                    "commands": [],
                }
            raise PublicationSafetyConfigError("PyYAML is required for enabled YAML config with commands; use .json or install PyYAML")
        data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise PublicationSafetyConfigError(f"publication-safety config must be a mapping: {path}")
    return data


def load_config(path: Path) -> dict[str, Any]:
    data = _load_structured_file(path)
    schema = data.get("schema_version", CONFIG_SCHEMA_VERSION)
    if schema != CONFIG_SCHEMA_VERSION:
        raise PublicationSafetyConfigError(f"invalid publication-safety schema_version: {schema}")
    return data


def _command_argv(raw: dict[str, Any]) -> tuple[str, ...]:
    if "command" in raw:
        command = raw["command"]
    else:
        command = raw.get("run")
    if isinstance(command, list) and all(isinstance(item, str) for item in command):
        argv = tuple(command)
    elif isinstance(command, str) and command.strip():
        # Config is project-owned, but avoid shell=True by default. This supports
        # the harness style commands while keeping argv explicit in receipts.
        argv = tuple(shlex.split(command))
    else:
        raise PublicationSafetyConfigError("gate command must provide non-empty command/run")
    if not argv:
        raise PublicationSafetyConfigError("gate command resolves to empty argv")
    return argv


def parse_commands(config: dict[str, Any]) -> list[GateCommand]:
    commands = config.get("commands", [])
    if not isinstance(commands, list):
        raise PublicationSafetyConfigError("publication-safety commands must be a list")
    parsed: list[GateCommand] = []
    seen: set[str] = set()
    for index, item in enumerate(commands):
        if not isinstance(item, dict):
            raise PublicationSafetyConfigError(f"command #{index} must be a mapping")
        command_id = str(item.get("id") or item.get("name") or "").strip()
        if not command_id:
            raise PublicationSafetyConfigError(f"command #{index} missing id")
        if command_id in seen:
            raise PublicationSafetyConfigError(f"duplicate publication-safety command id: {command_id}")
        seen.add(command_id)
        env_items = item.get("env", {}) or {}
        if not isinstance(env_items, dict):
            raise PublicationSafetyConfigError(f"command {command_id} env must be a mapping")
        expected = item.get("expected_statuses", item.get("expected_status", list(PASS_STATUSES)))
        if isinstance(expected, str):
            expected_statuses = (expected,)
        elif isinstance(expected, list) and all(isinstance(value, str) for value in expected):
            expected_statuses = tuple(expected)
        else:
            raise PublicationSafetyConfigError(f"command {command_id} expected_statuses must be string or list")
        parsed.append(
            GateCommand(
                id=command_id,
                argv=_command_argv(item),
                required=bool(item.get("required", True)),
                timeout_seconds=float(item.get("timeout_seconds", config.get("default_timeout_seconds", 300))),
                cwd=str(item["cwd"]) if item.get("cwd") else None,
                parse_json=bool(item.get("parse_json", True)),
                expected_statuses=tuple(status.lower() for status in expected_statuses),
                env=tuple((str(key), str(value)) for key, value in sorted(env_items.items())),
            )
        )
    return parsed


def _project_cwd(project_dir: Path, configured: str | None) -> Path:
    if configured is None:
        return project_dir
    cwd = Path(configured)
    return cwd if cwd.is_absolute() else project_dir / cwd


def _parse_json_stdout(stdout: str) -> dict[str, Any] | None:
    text = stdout.strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else {"json_type": type(payload).__name__}
    except json.JSONDecodeError:
        # Some aggregate gates print progress before their final receipt. Accept
        # the last JSON object if one can be decoded from line boundaries.
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for start in range(len(lines)):
            candidate = "\n".join(lines[start:])
            try:
                payload = json.loads(candidate)
                return payload if isinstance(payload, dict) else {"json_type": type(payload).__name__}
            except json.JSONDecodeError:
                continue
    return None


def _normalized_payload_status(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    for key in ("status", "result", "decision"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return None


def _step_status(exit_code: int, payload_status: str | None, expected: Iterable[str], required: bool) -> Status:
    expected_set = {item.lower() for item in expected}
    if exit_code != 0:
        return "fail" if required else "warn"
    if payload_status is None:
        return "pass"
    if payload_status in expected_set or payload_status in PASS_STATUSES:
        return "pass"
    if payload_status in WARN_STATUSES:
        return "warn"
    if payload_status in FAIL_STATUSES:
        return "fail" if required else "warn"
    return "fail" if required else "warn"


def run_gate(project_dir: Path, command: GateCommand, *, write_step_logs: bool, output_dir: Path | None) -> dict[str, Any]:
    started = time.monotonic()
    env = os.environ.copy()
    env.update(dict(command.env))
    cwd = _project_cwd(project_dir, command.cwd)
    stdout = ""
    stderr = ""
    timed_out = False
    exit_code = 1
    try:
        proc = subprocess.run(
            list(command.argv),
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=command.timeout_seconds,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        exit_code = int(proc.returncode)
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        exit_code = 124
    except OSError as exc:
        stderr = str(exc)
        exit_code = 127

    payload = _parse_json_stdout(stdout) if command.parse_json else None
    payload_status = _normalized_payload_status(payload)
    status = _step_status(exit_code, payload_status, command.expected_statuses, command.required)
    duration_ms = int((time.monotonic() - started) * 1000)

    step: dict[str, Any] = {
        "id": command.id,
        "status": status,
        "required": command.required,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "duration_ms": duration_ms,
        "cwd": str(cwd),
        "argv": list(command.argv),
        "stdout_sha256": sha256_text(stdout),
        "stderr_sha256": sha256_text(stderr),
        "stdout_bytes": len(stdout.encode("utf-8", errors="replace")),
        "stderr_bytes": len(stderr.encode("utf-8", errors="replace")),
    }
    if payload_status is not None:
        step["payload_status"] = payload_status
    if isinstance(payload, dict):
        schema = payload.get("schema") or payload.get("schema_version")
        if isinstance(schema, str):
            step["payload_schema"] = schema

    if write_step_logs and output_dir is not None:
        step_dir = output_dir / "steps"
        step_dir.mkdir(parents=True, exist_ok=True)
        safe_id = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in command.id)
        stdout_path = step_dir / f"{safe_id}.stdout"
        stderr_path = step_dir / f"{safe_id}.stderr"
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        step["stdout_path"] = str(stdout_path)
        step["stderr_path"] = str(stderr_path)

    if status != "pass":
        reason = "timeout" if timed_out else "exit_code" if exit_code != 0 else "payload_status"
        step["reason_code"] = reason
    return step


def aggregate_status(steps: list[dict[str, Any]]) -> Status:
    if not steps:
        return "skipped"
    if any(step.get("status") == "fail" for step in steps):
        return "fail"
    if any(step.get("status") == "warn" for step in steps):
        return "warn"
    return "pass"


def build_receipt(
    project_dir: Path,
    config_path: Path,
    *,
    write_step_logs: bool = False,
    output_path: Path | None = None,
) -> dict[str, Any]:
    config = load_config(config_path)
    enabled = bool(config.get("enabled", True))
    commands = parse_commands(config) if enabled else []
    output_dir = output_path.parent if output_path is not None else None
    steps = [run_gate(project_dir, command, write_step_logs=write_step_logs, output_dir=output_dir) for command in commands]
    status = aggregate_status(steps)
    required_failed = [step["id"] for step in steps if step.get("required") and step.get("status") == "fail"]
    warnings = [step["id"] for step in steps if step.get("status") == "warn"]
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "project_dir": str(project_dir),
        "config": str(config_path),
        "status": status,
        "enabled": enabled,
        "mode": str(config.get("mode", "strict")),
        "summary": {
            "total": len(steps),
            "pass": sum(1 for step in steps if step.get("status") == "pass"),
            "warn": len(warnings),
            "fail": len(required_failed),
            "required_failed": required_failed,
            "warnings": warnings,
        },
        "steps": steps,
        "claim": {
            "public_release_ready": status == "pass",
            "claim_ceiling": "public_release_ready" if status == "pass" else "not_public_release_ready",
            "reason": "all_required_publication_gates_passed" if status == "pass" else "publication_gates_not_all_passed",
        },
        "raw_output_policy": "hashes_only_by_default; use --write-step-logs for local diagnostics",
    }
    return receipt


def write_receipt(receipt: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def default_config_for(project_dir: Path) -> Path:
    return project_dir / DEFAULT_CONFIG

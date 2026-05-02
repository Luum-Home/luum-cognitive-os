# SCOPE: os-only
"""Cognitive OS Agent-Computer Interface observation normalizer."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ACIObservation:
    tool: str
    command_class: str
    exit_code: int
    status: str
    summary: str
    output_excerpt: str
    truncated: bool
    output_sha256: str
    retryable: bool
    suspected_cause: str
    next_action: str
    risk_tags: list[str] = field(default_factory=list)
    artifact_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_command(command: str) -> str:
    c = command.strip().lower()
    if "pytest" in c or "go test" in c or "npm test" in c or "cargo test" in c:
        return "test"
    if c.startswith(("git ", "gh ")):
        return "vcs"
    if c.startswith(("curl", "wget", "ssh", "scp", "rsync")):
        return "external_io"
    if c.startswith(("sed ", "awk ", "grep ", "rg ", "find ", "cat ", "ls ")):
        return "inspect"
    if c.startswith(("python", "uv ", "go ", "node ", "npm ", "pnpm ", "bun ")):
        return "build_or_script"
    return "shell" if c else "unknown"


def infer_risk_tags(command: str, output: str = "") -> list[str]:
    text = f"{command}\n{output}".lower()
    tags: set[str] = set()
    if any(marker in text for marker in [".env", "secret", "credential", "token", "private key"]):
        tags.add("private")
    if any(marker in text for marker in ["http://", "https://", "github issue", "clipboard", "untrusted"]):
        tags.add("untrusted")
    if any(marker in text for marker in ["curl ", "wget ", "ssh ", "scp ", "git push", "webhook", "slack"]):
        tags.add("external-capable")
    return sorted(tags)


def _diagnose(exit_code: int, command_class: str, output: str) -> tuple[bool, str, str]:
    lower = output.lower()
    if exit_code == 0:
        return False, "none", "continue"
    if "syntaxerror" in lower or "parse error" in lower:
        return False, "syntax_error", "fix syntax before retrying"
    if "modulenotfounderror" in lower or "command not found" in lower:
        return False, "missing_dependency", "verify environment or install optional dependency explicitly"
    if "timeout" in lower or "temporarily unavailable" in lower:
        return True, "transient_failure", "retry once with bounded timeout"
    if command_class == "test":
        return False, "test_failure", "inspect failing test and patch minimal cause"
    return False, "command_failed", "inspect output and choose a different action"


def normalize_observation(
    *,
    tool: str,
    command: str = "",
    output: str = "",
    exit_code: int = 0,
    max_chars: int = 4000,
    artifact_dir: str | Path | None = None,
) -> ACIObservation:
    command_class = classify_command(command)
    output = output or ""
    if exit_code == 0 and not output.strip():
        output = "[ACI] Command completed successfully with no output."
    digest = hashlib.sha256(output.encode("utf-8")).hexdigest()
    truncated = len(output) > max_chars
    excerpt = output[:max_chars]
    artifact_path = ""
    if truncated and artifact_dir is not None:
        directory = Path(artifact_dir)
        directory.mkdir(parents=True, exist_ok=True)
        artifact = directory / f"aci-output-{digest[:12]}.log"
        artifact.write_text(output, encoding="utf-8")
        artifact_path = str(artifact)
    retryable, cause, next_action = _diagnose(exit_code, command_class, output)
    status = "success" if exit_code == 0 else "failure"
    summary = f"{tool}:{command_class}:{status}:exit={exit_code}"
    if truncated:
        summary += f":truncated:{len(output)}chars"
    return ACIObservation(
        tool=tool,
        command_class=command_class,
        exit_code=int(exit_code),
        status=status,
        summary=summary,
        output_excerpt=excerpt,
        truncated=truncated,
        output_sha256=digest,
        retryable=retryable,
        suspected_cause=cause,
        next_action=next_action,
        risk_tags=infer_risk_tags(command, output),
        artifact_path=artifact_path,
    )

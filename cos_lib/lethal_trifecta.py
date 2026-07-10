# SCOPE: os-only
"""Deterministic Lethal Trifecta classifier for agent/tool actions."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import PurePosixPath
from typing import Any, Iterable, Mapping

_PRIVATE_PATTERNS = [
    r"(^|[\s:/\\])\.env(\.|$|[\s/\\])",
    r"(^|[\s:/\\])secrets?([/\\]|$)",
    r"\.pem\b|\.key\b|\.p12\b|id_rsa\b|credentials?\b|passwords?\b",
    r"api[_-]?key|access[_-]?token|refresh[_-]?token|private[_-]?key",
    r"engram.*personal|personal.*memory|private\s+(data|repo|document|memory)",
]

_UNTRUSTED_PATTERNS = [
    r"https?://",
    r"\b(untrusted|third[- ]party|external\s+content|web\s+page|downloaded)\b",
    r"\b(github\s+(issue|pr|pull request|comment)|user[- ]submitted|clipboard)\b",
    r"\b(mcp\s+(tool|server|description)|tool\s+poisoning|prompt\s+injection)\b",
    r"ignore\s+(all\s+)?previous\s+instructions|developer\s+mode|dan\s+mode",
]

_EXTERNAL_ACTION_PATTERNS = [
    r"\b(git\s+push|gh\s+pr\s+create|gh\s+release|npm\s+publish|twine\s+upload)\b",
    r"\b(curl|wget|nc|netcat|ssh|scp|rsync|ftp|sftp)\b",
    r"\b(http\s+post|webhook|send\s+(email|mail|message)|slack|gmail|calendar)\b",
    r"\b(kubectl\s+apply|terraform\s+apply|aws\s+|gcloud\s+|az\s+)\b",
]


_RESEARCH_DOC_WRITE_PREFIXES = (
    PurePosixPath("docs/03-PoCs/research"),
    PurePosixPath("docs/06-Daily/reports"),
    PurePosixPath("docs/02-Decisions/adrs"),
)

_EXTERNAL_TOOL_NAMES = {
    "web",
    "fetch",
    "http",
    "gmail",
    "slack",
    "teams",
    "google-calendar",
    "outlook-email",
    "outlook-calendar",
    "mcp",
}


@dataclass(frozen=True)
class TrifectaDecision:
    """Risk decision for one action."""

    private_data: bool
    untrusted_content: bool
    external_communication: bool
    decision: str
    severity: str
    score: int
    reasons: list[str] = field(default_factory=list)

    @property
    def dimension_count(self) -> int:
        """Return the number of detected dimensions."""
        return sum((self.private_data, self.untrusted_content, self.external_communication))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the decision."""
        row = asdict(self)
        row["dimension_count"] = self.dimension_count
        return row


def _normalized_parts(path: str) -> tuple[str, ...]:
    normalized = path.replace("\\", "/")
    return tuple(part for part in PurePosixPath(normalized).parts if part not in {"", "."})


def _is_under_doc_research_exemption(file_path: Any) -> bool:
    if not isinstance(file_path, str) or not file_path.strip():
        return False
    parts = _normalized_parts(file_path.strip())
    for prefix in _RESEARCH_DOC_WRITE_PREFIXES:
        prefix_parts = prefix.parts
        for index in range(0, len(parts) - len(prefix_parts) + 1):
            if parts[index : index + len(prefix_parts)] == prefix_parts:
                return True
    return False


def _is_exempt_research_write(tool_name: str, merged: Mapping[str, Any]) -> bool:
    return tool_name.lower() == "write" and _is_under_doc_research_exemption(merged.get("file_path"))


def _flatten(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return "\n".join(f"{key}: {_flatten(val)}" for key, val in value.items())
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return "\n".join(_flatten(item) for item in value)
    return str(value)


def _matches(patterns: list[str], text: str) -> list[str]:
    return [pattern for pattern in patterns if re.search(pattern, text, re.IGNORECASE)]


def classify_action(payload: Mapping[str, Any] | None) -> TrifectaDecision:
    """Classify a Claude/Codex hook payload or direct action dictionary."""
    payload = payload or {}
    tool_name = str(payload.get("tool_name") or payload.get("tool") or "")
    raw_tool_input = payload.get("tool_input")
    tool_input = dict(raw_tool_input) if isinstance(raw_tool_input, Mapping) else {}
    merged = {**payload, **tool_input}
    text = _flatten(merged)
    tags = {str(tag).lower() for tag in merged.get("risk_tags", []) or []}

    if _is_exempt_research_write(tool_name, merged):
        return TrifectaDecision(False, False, False, "allow", "debug", 0, [])

    private_hits = _matches(_PRIVATE_PATTERNS, text)
    untrusted_hits = _matches(_UNTRUSTED_PATTERNS, text)
    external_hits = _matches(_EXTERNAL_ACTION_PATTERNS, text)

    private_data = bool(private_hits) or bool({"private", "secret", "credential", "personal-data"} & tags) or bool(
        merged.get("private_data")
    )
    untrusted_content = bool(untrusted_hits) or bool({"untrusted", "external-content", "third-party"} & tags) or bool(
        merged.get("untrusted_content")
    )
    external_communication = (
        bool(external_hits)
        or any(name in tool_name.lower() for name in _EXTERNAL_TOOL_NAMES)
        or bool({"external", "network", "side-effect"} & tags)
        or bool(merged.get("external_communication"))
    )

    reasons: list[str] = []
    if private_data:
        reasons.append("private-data:" + (private_hits[0] if private_hits else "explicit-tag"))
    if untrusted_content:
        reasons.append("untrusted-content:" + (untrusted_hits[0] if untrusted_hits else "explicit-tag"))
    if external_communication:
        reasons.append("external-communication:" + (external_hits[0] if external_hits else tool_name or "explicit-tag"))

    dimensions = sum((private_data, untrusted_content, external_communication))
    if dimensions == 3:
        decision = "block"
        severity = "critical"
        score = 100
    elif dimensions == 2:
        decision = "warn"
        severity = "warn"
        score = 65
    elif dimensions == 1:
        decision = "allow"
        severity = "info"
        score = 25
    else:
        decision = "allow"
        severity = "debug"
        score = 0

    return TrifectaDecision(private_data, untrusted_content, external_communication, decision, severity, score, reasons)


def classify_json(payload_json: str) -> dict[str, Any]:
    """Classify JSON and return a serializable dict."""
    try:
        payload = json.loads(payload_json or "{}")
    except json.JSONDecodeError:
        payload = {"raw": payload_json}
    return classify_action(payload).to_dict()

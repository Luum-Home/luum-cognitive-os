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
    # La palabra suelta NO cuenta cuando es parte del nombre de un subcomando o
    # de una clave de configuracion: `git-credential`, `credential.helper` y
    # `gh auth git-credential` son plomeria de git, no datos privados. Medido el
    # 2026-08-21: un push legitimo quedaba marcado priv=1 solo por nombrar esa
    # plomeria, y con eso completaba la trifecta.
    r"\.pem\b|\.key\b|\.p12\b|id_rsa\b|passwords?\b",
    r"(?<![-.\w])credentials?\b(?![-.]?(helper|store|cache|approve|reject|fill))",
    r"api[_-]?key|access[_-]?token|refresh[_-]?token|private[_-]?key",
    r"engram.*personal|personal.*memory|private\s+(data|repo|document|memory)",
]

# LO INGERIDO NO SE VE EN EL TEXTO DE UN COMANDO.
#
# La trifecta letal es una propiedad del CONTEXTO del agente: datos privados que
# puede leer, contenido de origen ajeno que YA ENTRO a su contexto, y capacidad
# de comunicar hacia afuera. El riesgo es que ese contenido le dicte exfiltrar.
#
# Una URL escrita en un comando es exactamente lo contrario: es un destino que
# el operador eligio. Tomarla como evidencia de ingestion invierte el sentido.
# Medido el 2026-08-21: con ese patron, empujar a nuestro propio remoto y una
# exfiltracion real daban IDENTICO -- score 100 las dos, las tres banderas
# encendidas en las dos. Un gate que no distingue el caso legitimo del ataque no
# protege: se desactiva la primera semana, y ahi se pierde tambien el caso que
# si importaba.
#
# Quedan los marcadores de contenido REALMENTE ingerido (texto de inyeccion,
# menciones explicitas de origen ajeno) mas la via declarada: `risk_tags` o el
# campo del payload, que es como lo informa un llamador que SI sabe.
#
# El caso peligroso de verdad --leer un secreto y mandarlo a un host externo--
# lo sigue agarrando `hooks/network-egress-guard.sh`, que mira destino e
# indicadores en vez de contar palabras. Verificado: bloquea.
_UNTRUSTED_PATTERNS = [
    # Una URL cuenta SOLO si el comando la va a TRAER. `curl`, `wget` y amigos
    # ingieren; `git push` a una URL manda y no trae nada.
    #
    # La primera version de este arreglo saco el patron de URL entero y se paso
    # de largo: dejo de avisar sobre `curl https://...`, que si va a meter
    # contenido ajeno en el contexto. Lo agarro el test de contrato que ya
    # existia -- por eso el arreglo correcto es afinar la distincion, no borrar
    # la señal.
    r"\b(curl|wget|http|fetch|lynx|links|w3m)\b[^\n]*https?://",
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

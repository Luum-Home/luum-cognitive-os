# SCOPE: both
"""Context-budget accounting and verdicts for UserPromptSubmit/context hooks (ADR-186)."""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

VerdictName = Literal["PASS", "WARN", "BLOCK"]

DEFAULT_BUDGETS = {
    "static": 4000,
    "turn": 8000,
    "user": 12000,
    "cache": 32000,
}


@dataclass(frozen=True)
class BudgetVerdict:
    verdict: VerdictName
    ratio_used: float
    used_tokens: int
    budget_token_max: int
    layer: str
    allowed: bool
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def count_tokens(text: str, model: str = "heuristic") -> int:
    """Return token estimate. Default heuristic is len(text)//4, minimum 1 for non-empty."""
    if not text:
        return 0
    if os.environ.get("COS_USE_REAL_TOKENIZER") == "1":
        try:
            import tiktoken  # type: ignore

            enc = tiktoken.encoding_for_model(model) if model and model != "heuristic" else tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            pass
    return max(1, (len(text) + 3) // 4)


def _parse_int_from_yaml_line(text: str, key: str) -> int | None:
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped.startswith(f"{key}:"):
            continue
        value = stripped.split(":", 1)[1].split("#", 1)[0].strip().strip('"\'')
        try:
            return int(value)
        except ValueError:
            return None
    return None


def read_budget(config_path: str | Path | None = None) -> dict[str, int]:
    """Read context budgets from cognitive-os.yaml, falling back to ADR-186 defaults."""
    budgets = dict(DEFAULT_BUDGETS)
    path = Path(config_path) if config_path else Path(os.environ.get("COGNITIVE_OS_PROJECT_DIR", os.getcwd())) / "cognitive-os.yaml"
    if not path.is_file():
        return budgets
    text = path.read_text(encoding="utf-8", errors="replace")
    mapping = {
        "static_max_tokens": "static",
        "turn_max_tokens": "turn",
        "user_max_tokens": "user",
        "cache_max_tokens": "cache",
    }
    for yaml_key, layer in mapping.items():
        value = _parse_int_from_yaml_line(text, yaml_key)
        if value and value > 0:
            budgets[layer] = value
    return budgets


def evaluate(layer: str, used_tokens: int, budgets: dict[str, int] | None = None) -> BudgetVerdict:
    """Evaluate usage against ADR-186 thresholds."""
    budget_map = budgets or dict(DEFAULT_BUDGETS)
    max_tokens = int(budget_map.get(layer, DEFAULT_BUDGETS.get(layer, DEFAULT_BUDGETS["turn"])))
    ratio = used_tokens / max_tokens if max_tokens else 0.0
    if ratio <= 1.0:
        verdict: VerdictName = "PASS"
    elif ratio <= 1.2:
        verdict = "WARN"
    elif ratio > 1.5:
        verdict = "BLOCK"
    else:
        verdict = "WARN"
    allowed = verdict != "BLOCK" or os.environ.get("COS_ALLOW_CONTEXT_BUDGET_OVERRUN") == "1"
    reason = "override" if verdict == "BLOCK" and allowed else ""
    return BudgetVerdict(verdict, ratio, used_tokens, max_tokens, layer, allowed, reason)


def metrics_path(project_dir: str | Path) -> Path:
    return Path(project_dir) / ".cognitive-os" / "metrics" / "context-budget.jsonl"


def append_metric(project_dir: str | Path, row: dict[str, Any]) -> Path:
    path = metrics_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def record_usage(
    project_dir: str | Path,
    *,
    source: str,
    layer: str,
    text: str,
    session_id: str = "unknown",
    model: str = "heuristic",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Count, evaluate, and append one context-budget metric row."""
    used = count_tokens(text, model=model)
    verdict = evaluate(layer, used, read_budget(Path(project_dir) / "cognitive-os.yaml"))
    row = {
        "schema_version": 1,
        "timestamp_epoch": time.time(),
        "session_id": session_id,
        "source": source,
        "layer": layer,
        "chars": len(text or ""),
        "tokens_estimate": used,
        "budget_token_max": verdict.budget_token_max,
        "ratio_used": round(verdict.ratio_used, 4),
        "verdict": verdict.verdict,
        "allowed": verdict.allowed,
        "reason": verdict.reason,
        "metadata": metadata or {},
    }
    append_metric(project_dir, row)
    return row


def filter_hook_output(
    project_dir: str | Path,
    *,
    source: str,
    hook_json: str,
    session_id: str = "unknown",
    layer: str = "static",
) -> str:
    """Return hook JSON unchanged if budget allows, else empty string after logging.

    The hook output shape is expected to contain
    hookSpecificOutput.additionalContext. Non-JSON or no-context outputs pass
    through unchanged.
    """
    if not hook_json.strip():
        return ""
    try:
        data = json.loads(hook_json)
    except json.JSONDecodeError:
        return hook_json
    ctx = ""
    if isinstance(data, dict):
        hso = data.get("hookSpecificOutput")
        if isinstance(hso, dict):
            ctx = str(hso.get("additionalContext") or "")
        else:
            ctx = str(data.get("additionalContext") or "")
    if not ctx:
        return hook_json
    row = record_usage(project_dir, source=source, layer=layer, text=ctx, session_id=session_id)
    if row["verdict"] == "BLOCK" and not row["allowed"]:
        return ""
    return hook_json

# SCOPE: both
"""Record agent completion to learning pipeline.

Reads a JSON object from stdin with the shape produced by completion-gate.sh:
  {
    "tool_call_id": "toolu_xxx",
    "tool_name": "Agent",
    "tool_input": { "prompt": "...", "description": "..." },
    "tool_response": { "result": "...", "output": "..." }
  }

Extracts real data (skill_name, trust_score, tokens_used, task_type) and
feeds it into the learning pipeline + cost-events.jsonl.

Real token usage is read from Claude Code session JSONL files at
~/.claude/projects/{project-hash}/{session-id}.jsonl when available.
"""
import sys
import json
import os
import re
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

logger = logging.getLogger(__name__)

# Langfuse integration — graceful if not installed or not configured
_langfuse_client = None
try:
    from langfuse import Langfuse as _LangfuseClass
    _langfuse_client = _LangfuseClass()
except Exception:
    pass  # Langfuse not installed or not configured — skip silently

from lib.learning_pipeline import LearningPipeline
from lib.metric_event import MetricEvent, append_event
from lib.paths import runtime_project_root_or_cwd, runtime_session_id


def extract_skill_name(data: dict) -> str:
    """Extract skill/agent name from tool_input.description or prompt."""
    tool_input = data.get("tool_input", {})
    if isinstance(tool_input, dict):
        description = tool_input.get("description", "")
        if description and description.strip():
            return description.strip()[:100]
        prompt = tool_input.get("prompt", "")
        if prompt and prompt.strip():
            first_line = prompt.strip().splitlines()[0]
            return first_line[:100]
    return "unknown"


def extract_trust_score(output: str) -> int:
    """Extract trust score from agent output using 3 patterns. Default: 50."""
    patterns = [
        r'TRUST_REPORT:\s+SCORE=(\d+)',
        r'Score:\s*(\d+)/100',
        r'SCORE=(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            score = int(match.group(1))
            return max(0, min(100, score))
    return 50  # honest default: unknown -> triggers WARN in consequence engine


def estimate_tokens(output: str) -> int:
    """Rough chars-to-tokens estimate."""
    return len(output) // 4


# ---------------------------------------------------------------------------
# Real token usage — reads Claude Code session JSONL files
# ---------------------------------------------------------------------------

# Pricing per 1M tokens (as of 2026-04)
_MODEL_PRICING: dict[str, dict[str, float]] = {
    # claude-opus-4-6 family
    "claude-opus-4-6": {"input": 15.0, "output": 75.0, "cache_read": 1.50, "cache_write": 3.75},
    "claude-opus-4":   {"input": 15.0, "output": 75.0, "cache_read": 1.50, "cache_write": 3.75},
    "opus":            {"input": 15.0, "output": 75.0, "cache_read": 1.50, "cache_write": 3.75},
    # claude-sonnet-4 family
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 0.75},
    "claude-sonnet-4":   {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 0.75},
    "sonnet":            {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 0.75},
    # claude-haiku family
    "claude-haiku-4-5": {"input": 0.25, "output": 1.25, "cache_read": 0.025, "cache_write": 0.0625},
    "claude-haiku-3-5": {"input": 0.25, "output": 1.25, "cache_read": 0.025, "cache_write": 0.0625},
    "haiku":            {"input": 0.25, "output": 1.25, "cache_read": 0.025, "cache_write": 0.0625},
}
_DEFAULT_PRICING = {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 0.75}


def _get_pricing(model: str) -> dict[str, float]:
    """Return pricing dict for the given model (or default sonnet pricing)."""
    model_lower = model.lower()
    # Try exact match first, then prefix match
    if model_lower in _MODEL_PRICING:
        return _MODEL_PRICING[model_lower]
    for key, pricing in _MODEL_PRICING.items():
        if key in model_lower:
            return pricing
    return _DEFAULT_PRICING


def calculate_cost_usd(
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int,
    cache_write_tokens: int,
    model: str,
) -> float:
    """Calculate cost in USD from token counts and model name."""
    pricing = _get_pricing(model)
    cost = (
        input_tokens * pricing["input"]
        + output_tokens * pricing["output"]
        + cache_read_tokens * pricing["cache_read"]
        + cache_write_tokens * pricing["cache_write"]
    ) / 1_000_000
    return round(cost, 8)


def get_real_token_usage(session_jsonl_path: str, tool_call_id: str) -> Optional[dict]:
    """Read actual token usage from a Claude Code session JSONL file.

    Searches for the assistant message that triggered ``tool_call_id`` and
    returns the usage block from that message.

    Returns a dict with keys:
      input_tokens, output_tokens, cache_read_input_tokens,
      cache_creation_input_tokens, total_cost_usd, model
    or None if the record cannot be found.
    """
    path = Path(session_jsonl_path)
    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as fh:
            for raw_line in fh:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    record = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue

                if record.get("type") != "assistant":
                    continue

                message = record.get("message", {})
                usage = message.get("usage")
                if not usage:
                    continue

                # Check if this assistant message contains the tool call we want
                content = message.get("content", [])
                found = False
                if isinstance(content, list):
                    for block in content:
                        if (
                            isinstance(block, dict)
                            and block.get("type") == "tool_use"
                            and block.get("id") == tool_call_id
                        ):
                            found = True
                            break

                if not found:
                    continue

                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                cache_read = usage.get("cache_read_input_tokens", 0)
                cache_write = usage.get("cache_creation_input_tokens", 0)
                model = message.get("model", "sonnet")

                return {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cache_read_input_tokens": cache_read,
                    "cache_creation_input_tokens": cache_write,
                    "total_cost_usd": calculate_cost_usd(
                        input_tokens, output_tokens, cache_read, cache_write, model
                    ),
                    "model": model,
                }
    except OSError:
        pass

    return None


def find_session_jsonl(project_dir: str, session_id: Optional[str] = None) -> Optional[str]:
    """Locate the Claude Code session JSONL file for the current project.

    Claude Code encodes the project path as a directory under ~/.claude/projects/
    using hyphens in place of slashes.  If ``session_id`` is given, we target
    that specific file; otherwise we return the most recently modified one.
    """
    projects_root = Path.home() / ".claude" / "projects"
    if not projects_root.exists():
        return None

    # Convert project_dir path to the Claude hash-directory name
    norm = os.path.realpath(project_dir)
    encoded = norm.replace("/", "-").replace("\\", "-")
    # Claude Code uses leading hyphen for absolute paths: /Users/... -> -Users-...
    project_hash_dir = projects_root / encoded

    if not project_hash_dir.exists():
        # Try scanning all project dirs for a matching suffix (fallback)
        candidates = []
        for d in projects_root.iterdir():
            if d.is_dir() and encoded.endswith(d.name.lstrip("-")):
                candidates.append(d)
        if not candidates:
            return None
        project_hash_dir = candidates[0]

    if session_id:
        target = project_hash_dir / f"{session_id}.jsonl"
        return str(target) if target.exists() else None

    # Return most recently modified JSONL
    jsonl_files = list(project_hash_dir.glob("*.jsonl"))
    if not jsonl_files:
        return None
    return str(max(jsonl_files, key=lambda p: p.stat().st_mtime))


def classify_task_type(description: str) -> str:
    """Classify task type by keywords in description."""
    desc_lower = description.lower()
    if any(kw in desc_lower for kw in ("implement", "create", "build", "add")):
        return "implementation"
    if any(kw in desc_lower for kw in ("review", "verify", "audit", "check")):
        return "review"
    if any(kw in desc_lower for kw in ("debug", "fix", "repair", "error")):
        return "debugging"
    if any(kw in desc_lower for kw in ("doc", "readme", "document")):
        return "documentation"
    if any(kw in desc_lower for kw in ("archive", "cleanup", "format")):
        return "archiving"
    return "general"


def detect_success(output: str, data: dict) -> bool:
    """Detect if agent completed successfully."""
    failure_keywords = ["FAIL", "ERROR", "BLOCKED", "BUILD FAILED", "COMPILATION ERROR"]
    if any(kw in output.upper() for kw in failure_keywords):
        return False
    tool_response = data.get("tool_response", {})
    if isinstance(tool_response, dict):
        if tool_response.get("error") or tool_response.get("is_error"):
            return False
    return True


_MODEL_PRICE_PER_TOKEN = {
    "opus": 0.000075,    # $75/1M output tokens (worst case — output is more expensive)
    "sonnet": 0.000015,  # $15/1M output tokens
    "haiku": 0.00000125, # $1.25/1M output tokens
}


def detect_model(data: dict) -> str:
    """Detect which model was used from tool_input fields."""
    tool_input = data.get("tool_input", {})
    if isinstance(tool_input, dict):
        for field in ("model", "description", "prompt"):
            val = str(tool_input.get(field, "")).lower()
            if "opus" in val:
                return "opus"
            if "haiku" in val:
                return "haiku"
    return "sonnet"


def append_cost_event(
    metrics_dir: str,
    description: str,
    tokens_estimated: int,
    model: str = "sonnet",
    real_usage: Optional[dict] = None,
) -> None:
    """Append a cost event to cost-events.jsonl (ADR-028 D1.A MetricEvent schema).

    When ``real_usage`` is provided (from ``get_real_token_usage``), actual
    token counts and cost are used and ``is_estimate`` is set to False.
    Otherwise the legacy char-based estimate is used.
    """
    if real_usage:
        input_tokens = real_usage.get("input_tokens", 0)
        output_tokens = real_usage.get("output_tokens", 0)
        cache_read = real_usage.get("cache_read_input_tokens", 0)
        cache_write = real_usage.get("cache_creation_input_tokens", 0)
        cost_usd = real_usage.get("total_cost_usd", 0.0)
        real_model = real_usage.get("model", model)
        payload: dict = {
            "agent": description[:200],
            "model": real_model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_input_tokens": cache_read,
            "cache_creation_input_tokens": cache_write,
            "actual_cost_usd": round(cost_usd, 8),
            "is_estimate": False,
        }
    else:
        price_per_token = _MODEL_PRICE_PER_TOKEN.get(model, _MODEL_PRICE_PER_TOKEN["sonnet"])
        cost_usd = tokens_estimated * price_per_token
        payload = {
            "agent": description[:200],
            "model": model,
            "estimated_cost_usd": round(cost_usd, 6),
            "tokens_estimated": tokens_estimated,
            "is_estimate": True,
        }
    cost_file = os.path.join(metrics_dir, "cost-events.jsonl")
    try:
        event = MetricEvent(
            source="record_completion",
            event_type="cost.recorded",
            payload=payload,
        )
        append_event(cost_file, event)
    except OSError:
        pass


def _send_langfuse_trace(
    skill_name: str,
    task_type: str,
    trust_score: int,
    tokens_used: int,
    success: bool,
    task_id: str,
) -> None:
    """Send agent completion trace to Langfuse v3 (OTEL-based). Silent on failure."""
    if _langfuse_client is None:
        return
    try:
        # v3 API: start_as_current_span creates trace + span
        with _langfuse_client.start_as_current_span(name=skill_name) as span:
            trace_id = _langfuse_client.get_current_trace_id()
            _langfuse_client.update_current_trace(
                metadata={
                    "task_type": task_type,
                    "trust_score": trust_score,
                    "tokens_used": tokens_used,
                    "success": success,
                    "task_id": task_id,
                },
            )
            with _langfuse_client.start_as_current_generation(
                name="agent-completion",
                input={"task_id": task_id, "task_type": task_type},
                metadata={"tokens": tokens_used},
            ) as gen:
                _langfuse_client.update_current_generation(
                    output={"trust_score": trust_score, "success": success},
                    usage_details={"input": tokens_used // 2, "output": tokens_used // 2},
                )

        # Record trust score as a first-class Langfuse Score via REST-backed method
        if trace_id:
            _langfuse_client.create_score(
                name="trust-score",
                value=trust_score / 100.0,
                trace_id=trace_id,
                comment=f"{'success' if success else 'failure'}: {skill_name}",
            )
        _langfuse_client.flush()
    except Exception:
        pass  # Never block completion recording for observability


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}

    tool_response = data.get("tool_response", {})
    if isinstance(tool_response, dict):
        output = str(
            tool_response.get("result")
            or tool_response.get("output")
            or tool_response.get("content")
            or ""
        )
    elif isinstance(tool_response, str) and tool_response:
        # Claude Code sends tool_response as a plain string for Agent PostToolUse
        output = tool_response
    else:
        output = str(data.get("tool_output", data.get("result", "")))

    skill_name = extract_skill_name(data)
    trust_score = extract_trust_score(output)
    tokens_used = estimate_tokens(output)
    success = detect_success(output, data)
    task_id = data.get("tool_call_id") or "unknown"
    model = detect_model(data)

    # Attempt to read real token usage from Claude Code session JSONL
    project_dir = str(runtime_project_root_or_cwd())
    session_id = runtime_session_id() or data.get("session_id")
    session_jsonl = find_session_jsonl(project_dir, session_id)
    real_usage: Optional[dict] = None
    if session_jsonl and task_id and task_id != "unknown":
        real_usage = get_real_token_usage(session_jsonl, task_id)
    if real_usage:
        tokens_used = real_usage["input_tokens"] + real_usage["output_tokens"]
        model = real_usage.get("model", model)

    pipeline = LearningPipeline()
    result = pipeline.record_agent_completion(
        task_id=task_id,
        success=success,
        trust_score=trust_score,
        skill_name=skill_name,
        tokens_used=tokens_used,
    )

    metrics_dir = os.path.join(project_dir, ".cognitive-os", "metrics")
    append_cost_event(metrics_dir, skill_name, tokens_used, model=model, real_usage=real_usage)

    # Send trace to Langfuse (if available)
    _send_langfuse_trace(
        skill_name=skill_name,
        task_type=classify_task_type(skill_name),
        trust_score=trust_score,
        tokens_used=tokens_used,
        success=success,
        task_id=task_id,
    )

    print(json.dumps({
        "action": str(result),
        "skill_name": skill_name,
        "trust_score": trust_score,
        "tokens_used": tokens_used,
        "success": success,
        "task_type": classify_task_type(skill_name),
    }))


if __name__ == "__main__":
    main()

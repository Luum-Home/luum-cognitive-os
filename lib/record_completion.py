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
"""
import sys
import json
import os
import re
import logging
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

logger = logging.getLogger(__name__)

# Langfuse integration — graceful if not installed or not configured
_langfuse_client = None
try:
    from langfuse import get_client as _get_langfuse_client
    _langfuse_client = _get_langfuse_client()
except Exception:
    pass  # Langfuse not installed or not configured — skip silently

from lib.learning_pipeline import LearningPipeline


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


def append_cost_event(metrics_dir: str, description: str, tokens_estimated: int) -> None:
    """Append a cost event to cost-events.jsonl."""
    cost_usd = tokens_estimated * 0.000015
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "agent": description[:200],
        "model": "sonnet",
        "estimated_cost_usd": round(cost_usd, 6),
        "tokens_estimated": tokens_estimated,
    }
    cost_file = os.path.join(metrics_dir, "cost-events.jsonl")
    try:
        os.makedirs(metrics_dir, exist_ok=True)
        with open(cost_file, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")
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
    """Send agent completion trace to Langfuse. Silent on failure."""
    if _langfuse_client is None:
        return
    try:
        trace = _langfuse_client.trace(
            name=skill_name,
            metadata={
                "task_type": task_type,
                "trust_score": trust_score,
                "tokens_used": tokens_used,
                "success": success,
                "cost_usd": round(tokens_used * 0.000015, 6),
            },
            tags=["cos-agent", task_type, "success" if success else "failure"],
        )
        trace.span(
            name="agent-completion",
            input={"task_id": task_id, "task_type": task_type},
            output={"trust_score": trust_score, "success": success},
            metadata={"tokens": tokens_used},
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
    else:
        output = str(data.get("tool_output", data.get("result", "")))

    skill_name = extract_skill_name(data)
    trust_score = extract_trust_score(output)
    tokens_used = estimate_tokens(output)
    success = detect_success(output, data)
    task_id = data.get("tool_call_id") or "unknown"

    pipeline = LearningPipeline()
    result = pipeline.record_agent_completion(
        task_id=task_id,
        success=success,
        trust_score=trust_score,
        skill_name=skill_name,
        tokens_used=tokens_used,
    )

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    metrics_dir = os.path.join(project_dir, ".cognitive-os", "metrics")
    append_cost_event(metrics_dir, skill_name, tokens_used)

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

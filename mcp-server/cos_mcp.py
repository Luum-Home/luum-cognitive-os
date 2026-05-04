"""Cognitive OS MCP Server — Expose COS knowledge to any MCP-compatible editor.

Makes Cognitive OS accessible from VS Code, Cursor, Windsurf, and any other
editor that supports the Model Context Protocol. Exposes Engram memory, task
state, rules, metrics, quality checks, and skill suggestions as MCP tools.

Requirements:
    pip install fastmcp

Usage:
    python mcp-server/cos_mcp.py

Configure in .claude/settings.json (or equivalent MCP config):
    {
        "mcpServers": {
            "cos": {
                "command": "python",
                "args": ["mcp-server/cos_mcp.py"],
                "cwd": "/path/to/luum-agent-os"
            }
        }
    }

Author: luum
Python 3.10+ (FastMCP requirement)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Resolve project root (the directory containing this mcp-server/ folder)
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _THIS_DIR.parent

# Add project root to sys.path so we can import lib/
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# FastMCP import with graceful degradation
# ---------------------------------------------------------------------------

try:
    from fastmcp import FastMCP
except ImportError:
    if __name__ == "__main__":
        print(
            "ERROR: fastmcp is not installed. Install with: pip install fastmcp",
            file=sys.stderr,
        )
        sys.exit(1)

    class _FastMCPCompat:
        """Tiny import-time stub used for direct tool tests when fastmcp is absent."""

        def __init__(self, name: str, **kwargs):
            self.name = name
            self.kwargs = kwargs

        def tool(self, *decorator_args, **decorator_kwargs):
            if decorator_args and callable(decorator_args[0]) and not decorator_kwargs:
                return decorator_args[0]

            def _decorator(func):
                return func

            return _decorator

        def run(self):
            raise RuntimeError("fastmcp is required to run the MCP server transport")


    FastMCP = _FastMCPCompat

# ---------------------------------------------------------------------------
# Lazy imports for COS libraries (they may not all exist)
# ---------------------------------------------------------------------------


def _try_import_skill_router():
    """Lazy import of SkillRouter."""
    try:
        from lib.skill_router import SkillRouter
        return SkillRouter()
    except Exception:
        return None


def _try_import_prompt_classifier():
    """Lazy import of prompt_classifier."""
    try:
        from lib.prompt_classifier import classify_prompt
        return classify_prompt
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_jsonl(path: Path, max_lines: int = 100) -> List[Dict[str, Any]]:
    """Read a JSONL file, returning the last max_lines entries."""
    if not path.is_file():
        return []
    entries: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        return []
    return entries[-max_lines:]


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    """Read a JSON file, returning None on failure."""
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _read_yaml_simple(path: Path) -> Optional[Dict[str, Any]]:
    """Read a YAML file using PyYAML if available, otherwise return None."""
    if not path.is_file():
        return None
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def _count_files(pattern: str, base: Path) -> int:
    """Count files matching a glob pattern."""
    return len(list(base.glob(pattern)))


def _engram_search(query: str, project: str = "", limit: int = 10) -> str:
    """Search Engram with hybrid FTS5+Jaccard retrieval when available.

    Priority: MemoryRetriever (hybrid) -> engram Python API -> engram CLI.
    Always returns valid JSON (object or array).
    """
    # Try hybrid retrieval first (FTS5 + Jaccard reranking)
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from lib.memory_retriever import MemoryRetriever
        retriever = MemoryRetriever()
        results = retriever.search(query, limit=limit, project=project or None)
        if results:
            return json.dumps([{
                "id": r.id, "title": r.title, "content": r.content,
                "topic_key": r.topic_key, "project": r.project,
                "score": round(r.combined_score, 3)
            } for r in results], indent=2)
    except Exception:
        pass

    # Fallback: try the engram Python package
    try:
        from engram.api import search  # type: ignore
        results = search(query=query, project=project or None, limit=limit)
        return json.dumps(results, indent=2, default=str)
    except Exception:
        pass

    # Fallback: try engram CLI
    cmd = ["engram", "search", query]
    if project:
        cmd.extend(["--project", project])
    cmd.extend(["--limit", str(limit)])
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            try:
                json.loads(output)
                return output
            except (json.JSONDecodeError, ValueError):
                return json.dumps({"results": [], "message": output})
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return json.dumps({"error": "Engram not available. Install engram or configure the MCP server."})


def _engram_save(title: str, content: str, type_: str = "manual",
                 project: str = "", topic_key: str = "") -> str:
    """Scan content for threats then save to Engram via CLI.

    Returns an error JSON string if the content is blocked by the
    memory scanner or if the engram CLI is unavailable.
    """
    # --- Memory scanner gate -------------------------------------------
    try:
        from lib.safe_engram import safe_save, SafeEngramResult
        result: SafeEngramResult = safe_save(
            title=title,
            content=content,
            type_=type_,
            project=project,
            topic_key=topic_key,
        )
        if result.blocked:
            return json.dumps({
                "error": "Content blocked by memory scanner.",
                "reasons": result.reasons,
            })
        if result.returncode == 127:
            return json.dumps({
                "error": (
                    "engram binary not found on PATH — memory features disabled. "
                    "Install via 'npx -y @anthropic/engram' (see manifests/dependencies.yaml)."
                )
            })
        if result.returncode is not None and result.returncode != 0:
            return json.dumps({"error": "Engram CLI not available. Install engram."})
        return result.engram_output or "Saved successfully."
    except ImportError:
        pass  # safe_engram not available — fall back to direct CLI call

    # --- Direct CLI fallback (safe_engram unavailable) ------------------
    cmd = ["engram", "save", title, content, "--type", type_]
    if project:
        cmd.extend(["--project", project])
    if topic_key:
        cmd.extend(["--topic", topic_key])
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip() or "Saved successfully."
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return json.dumps({"error": "Engram CLI not available. Install engram."})


# ---------------------------------------------------------------------------
# Build contextual trigger index from cognitive-os.yaml
# ---------------------------------------------------------------------------


def _load_contextual_triggers() -> Dict[str, str]:
    """Load rule -> trigger pattern mapping from cognitive-os.yaml."""
    config = _read_yaml_simple(PROJECT_ROOT / "cognitive-os.yaml")
    if not config:
        return {}
    try:
        return config["rules"]["loading"]["contextual_triggers"]
    except (KeyError, TypeError):
        return {}


# ---------------------------------------------------------------------------
# MCP Server Definition
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "Cognitive OS",
    instructions=(
        "Cognitive OS (COS) MCP server. Provides access to persistent memory, "
        "task state, rules, metrics, quality checks, and skill suggestions for "
        "AI-assisted development projects."
    ),
)


# ---- Tool 1: Search COS Memory ----


@mcp.tool()
def cos_search_memory(query: str, project: str = "", limit: int = 10) -> str:
    """Search Engram for past decisions, discoveries, bugs, and patterns.

    Args:
        query: Natural language search query (e.g., "auth middleware", "JWT bug fix").
        project: Optional project name filter.
        limit: Maximum number of results (default 10).
    """
    return _engram_search(query, project=project, limit=limit)


# ---- Tool 2: Get Current Task State ----


@mcp.tool()
def cos_get_tasks(status: str = "all") -> str:
    """Get current tasks from active-tasks.json.

    Args:
        status: Filter by status: all, pending, in_progress, completed, failed.
    """
    # Check multiple possible locations
    candidates = [
        PROJECT_ROOT / ".claude" / "tasks" / "active-tasks.json",
        PROJECT_ROOT / ".cognitive-os" / "tasks" / "active-tasks.json",
    ]

    tasks_data = None
    for path in candidates:
        tasks_data = _read_json(path)
        if tasks_data is not None:
            break

    if tasks_data is None:
        return json.dumps({"tasks": [], "message": "No active-tasks.json found."})

    tasks = tasks_data.get("tasks", [])
    if status != "all":
        tasks = [t for t in tasks if t.get("status") == status]

    return json.dumps({
        "total": len(tasks_data.get("tasks", [])),
        "filtered": len(tasks),
        "filter": status,
        "tasks": tasks,
    }, indent=2, default=str)


# ---- Tool 3: Get Relevant Rules ----


@mcp.tool()
def cos_get_rules(context: str) -> str:
    """Given a context description, return the most relevant COS rules.

    Uses contextual triggers from cognitive-os.yaml to match rules, then
    reads the matched rule files and returns their content.

    Args:
        context: Description of what you're working on (e.g., "security audit",
                 "cost optimization", "writing tests").
    """
    triggers = _load_contextual_triggers()
    if not triggers:
        return json.dumps({"error": "Could not load contextual triggers from cognitive-os.yaml."})

    context_lower = context.lower()
    matched_rules: List[Dict[str, Any]] = []

    for rule_name, pattern_str in triggers.items():
        # Patterns use dots as separators in the YAML, convert to regex
        patterns = pattern_str.split("|")
        for pat in patterns:
            # Replace dots with flexible separators for matching
            regex_pat = pat.strip().replace(".", "[.\\s_-]?")
            try:
                if re.search(regex_pat, context_lower):
                    # Read the rule file
                    rule_path = PROJECT_ROOT / "rules" / f"{rule_name}.md"
                    # Also check package rules
                    if not rule_path.is_file():
                        pkg_matches = list(PROJECT_ROOT.glob(f"packages/*/rules/{rule_name}.md"))
                        if pkg_matches:
                            rule_path = pkg_matches[0]

                    summary = ""
                    if rule_path.is_file():
                        try:
                            text = rule_path.read_text(encoding="utf-8")
                            # Extract first 500 chars as summary
                            lines = text.split("\n")
                            summary_lines = []
                            chars = 0
                            for line in lines:
                                if chars > 500:
                                    break
                                summary_lines.append(line)
                                chars += len(line)
                            summary = "\n".join(summary_lines)
                        except OSError:
                            summary = "(could not read file)"

                    matched_rules.append({
                        "rule": rule_name,
                        "file": str(rule_path) if rule_path.is_file() else f"rules/{rule_name}.md",
                        "matched_pattern": pat.strip(),
                        "summary": summary,
                    })
                    break  # Only match once per rule
            except re.error:
                continue

    if not matched_rules:
        return json.dumps({
            "matched": 0,
            "message": f"No rules matched context '{context}'. Try broader terms.",
            "available_triggers": list(triggers.keys()),
        }, indent=2)

    return json.dumps({
        "matched": len(matched_rules),
        "rules": matched_rules,
    }, indent=2, default=str)


# ---- Tool 4: Check Quality Gates ----


@mcp.tool()
def cos_check_quality(code: str, file_path: str = "") -> str:
    """Run COS quality checks on a piece of code.

    Checks for: prohibited terms from content-policy.yaml, credential leaks
    (API keys, passwords, tokens), TODO/FIXME/HACK comments, and stub
    implementations.

    Args:
        code: The code content to check.
        file_path: Optional file path for context-aware checks.
    """
    findings: List[Dict[str, str]] = []

    # 1. Check content policy (prohibited terms)
    policy = _read_yaml_simple(PROJECT_ROOT / ".cognitive-os" / "content-policy.yaml")
    if policy:
        for item in policy.get("prohibited_terms", []):
            term = item.get("term", "")
            if term and term.lower() in code.lower():
                findings.append({
                    "severity": "BLOCKER",
                    "type": "content_policy",
                    "message": f"Prohibited term found: '{term}'",
                    "reason": item.get("reason", ""),
                })

        for item in policy.get("prohibited_patterns", []):
            pat = item.get("pattern", "")
            if pat:
                try:
                    if re.search(pat, code, re.IGNORECASE):
                        findings.append({
                            "severity": "BLOCKER",
                            "type": "content_policy",
                            "message": f"Prohibited pattern matched: '{pat}'",
                            "reason": item.get("reason", ""),
                        })
                except re.error:
                    pass

    # 2. Check for credential leaks
    credential_patterns = [
        (r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"][^'\"]{10,}", "Possible API key in code"),
        (r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"][^'\"]+['\"]", "Possible password in code"),
        (r"(?i)(secret|token)\s*[:=]\s*['\"][^'\"]{10,}", "Possible secret/token in code"),
        (r"sk-[a-zA-Z0-9]{20,}", "Possible OpenAI API key"),
        (r"ghp_[a-zA-Z0-9]{36}", "Possible GitHub personal access token"),
        (r"AKIA[0-9A-Z]{16}", "Possible AWS access key"),
    ]
    for pat, msg in credential_patterns:
        if re.search(pat, code):
            findings.append({
                "severity": "BLOCKER",
                "type": "credential_leak",
                "message": msg,
            })

    # 3. Check for TODO/FIXME/HACK (quality concern)
    todo_matches = re.findall(r"(?i)\b(TODO|FIXME|HACK|XXX)\b.*", code)
    if todo_matches:
        findings.append({
            "severity": "CONCERN",
            "type": "incomplete_code",
            "message": f"Found {len(todo_matches)} TODO/FIXME/HACK comment(s)",
            "details": [m.strip() for m in todo_matches[:5]],
        })

    # 4. Check for stub implementations
    stub_patterns = [
        (r"(?i)not\s+implemented", "Stub: 'not implemented'"),
        (r"(?i)raise\s+NotImplementedError", "Stub: raises NotImplementedError"),
        (r'panic\s*\(\s*".*implement', "Stub: panic with 'implement'"),
    ]
    for pat, msg in stub_patterns:
        if re.search(pat, code):
            findings.append({
                "severity": "CONCERN",
                "type": "stub_implementation",
                "message": msg,
            })

    # 5. Check for commented-out code blocks (3+ consecutive comment lines)
    lines = code.split("\n")
    consecutive_comments = 0
    comment_blocks = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("#") or stripped.startswith("*"):
            consecutive_comments += 1
        else:
            if consecutive_comments >= 3:
                comment_blocks += 1
            consecutive_comments = 0
    if comment_blocks > 0:
        findings.append({
            "severity": "SUGGESTION",
            "type": "dead_code",
            "message": f"Found {comment_blocks} block(s) of 3+ consecutive comment lines (possible dead code)",
        })

    # Summary
    blocker_count = sum(1 for f in findings if f["severity"] == "BLOCKER")
    concern_count = sum(1 for f in findings if f["severity"] == "CONCERN")
    suggestion_count = sum(1 for f in findings if f["severity"] == "SUGGESTION")

    return json.dumps({
        "file": file_path or "(inline code)",
        "findings": findings,
        "summary": {
            "total": len(findings),
            "blockers": blocker_count,
            "concerns": concern_count,
            "suggestions": suggestion_count,
            "verdict": "BLOCK" if blocker_count > 0 else ("WARN" if concern_count > 0 else "PASS"),
        },
    }, indent=2, default=str)


# ---- Tool 5: Get Metrics Dashboard ----


@mcp.tool()
def cos_get_metrics(metric_type: str = "all") -> str:
    """Get current COS metrics: trust scores, error rates, cost, KPIs.

    Args:
        metric_type: Which metrics to return: all, errors, trust, cost, kpis, skills.
    """
    metrics_dir = PROJECT_ROOT / ".cognitive-os" / "metrics"
    result: Dict[str, Any] = {}

    metric_files = {
        "errors": "error-learning.jsonl",
        "trust": "trust-scores.jsonl",
        "cost": "cost-events.jsonl",
        "kpis": "kpi-history.jsonl",
        "skills": "skill-metrics.jsonl",
        "hallucinations": "hallucinations.jsonl",
        "assumptions": "assumptions.jsonl",
        "clarifications": "clarification-events.jsonl",
        "blast_radius": "blast-radius.jsonl",
    }

    requested = metric_files if metric_type == "all" else {
        k: v for k, v in metric_files.items() if k == metric_type
    }

    for key, filename in requested.items():
        entries = _read_jsonl(metrics_dir / filename, max_lines=20)
        if entries:
            result[key] = {
                "count": len(entries),
                "recent": entries[-5:],  # Last 5 entries
            }

    # Add file existence summary
    all_metrics_files = list(metrics_dir.glob("*.jsonl")) if metrics_dir.is_dir() else []
    result["_available_files"] = [f.name for f in sorted(all_metrics_files)]

    if not result.get("_available_files"):
        result["message"] = "No metrics files found. Metrics are generated during COS sessions."

    return json.dumps(result, indent=2, default=str)


# ---- Tool 6: Suggest Skill ----


@mcp.tool()
def cos_suggest_skill(message: str) -> str:
    """Given a user message, suggest the best COS skill to use.

    Uses the skill routing table to match intents to skills.

    Args:
        message: The user's message or task description.
    """
    router = _try_import_skill_router()
    if router is not None:
        try:
            match = router.best_match(message)
            if match:
                return json.dumps({
                    "best_match": {
                        "skill": match.skill_name,
                        "command": match.invoke_command,
                        "confidence": match.confidence,
                        "reason": match.reason,
                    },
                    "alternatives": [],
                }, indent=2)
            else:
                return json.dumps({
                    "best_match": None,
                    "message": "No skill matched the given message. Try being more specific.",
                })
        except Exception as e:
            return json.dumps({"error": f"Skill router error: {e}"})

    # Fallback: basic keyword matching against CATALOG.md
    catalog_path = PROJECT_ROOT / "CATALOG.md"
    if catalog_path.is_file():
        try:
            catalog = catalog_path.read_text(encoding="utf-8")
            msg_lower = message.lower()
            matches = []
            for line in catalog.split("\n"):
                if line.startswith("| /") or line.startswith("| `/"):
                    # Extract skill name from table
                    parts = line.split("|")
                    if len(parts) >= 3:
                        skill = parts[1].strip().strip("`")
                        desc = parts[2].strip()
                        # Simple keyword overlap
                        desc_words = set(desc.lower().split())
                        msg_words = set(msg_lower.split())
                        overlap = len(desc_words & msg_words)
                        if overlap > 0:
                            matches.append({
                                "skill": skill,
                                "description": desc,
                                "keyword_overlap": overlap,
                            })
            matches.sort(key=lambda x: x["keyword_overlap"], reverse=True)
            if matches:
                return json.dumps({
                    "best_match": matches[0],
                    "alternatives": matches[1:3],
                    "source": "catalog_keyword_match",
                }, indent=2)
        except OSError:
            pass

    return json.dumps({
        "error": "Skill router not available and CATALOG.md not found.",
        "suggestion": "Ensure lib/skill_router.py exists or CATALOG.md is present.",
    })


# ---- Tool 7: Save to Memory ----


@mcp.tool()
def cos_save_memory(
    title: str,
    content: str,
    type: str = "manual",
    project: str = "",
    topic_key: str = "",
) -> str:
    """Save an observation to COS persistent memory (Engram).

    Args:
        title: Short, searchable title (e.g., "JWT auth middleware decision").
        content: Structured content. Recommended format:
                 **What**: ..., **Why**: ..., **Where**: ..., **Learned**: ...
        type: Category: decision, architecture, bugfix, pattern, config, discovery.
        project: Project name for scoping.
        topic_key: Stable key for upserts (e.g., "architecture/auth-model").
    """
    return _engram_save(
        title=title,
        content=content,
        type_=type,
        project=project,
        topic_key=topic_key,
    )


# ---- Tool 8: Get Project Status ----


@mcp.tool()
def cos_status() -> str:
    """Get COS installation status: phase, rules, hooks, skills, packages, metrics."""
    status: Dict[str, Any] = {}

    # Project phase from cognitive-os.yaml
    config = _read_yaml_simple(PROJECT_ROOT / "cognitive-os.yaml")
    if config:
        status["phase"] = config.get("project", {}).get("phase", "unknown")
        status["project_name"] = config.get("project", {}).get("name", "unknown")
        status["project_type"] = config.get("project", {}).get("type", "unknown")
    else:
        status["phase"] = "unknown"
        status["config_found"] = False

    # Count components
    status["rules"] = _count_files("rules/*.md", PROJECT_ROOT)
    status["hooks"] = _count_files("hooks/*.sh", PROJECT_ROOT)
    status["skills"] = _count_files("skills/*/SKILL.md", PROJECT_ROOT)
    status["packages"] = _count_files("packages/*/cos-package.yaml", PROJECT_ROOT)

    # Count lib modules
    status["lib_modules"] = _count_files("lib/*.py", PROJECT_ROOT)

    # Metrics files
    metrics_dir = PROJECT_ROOT / ".cognitive-os" / "metrics"
    if metrics_dir.is_dir():
        metric_files = list(metrics_dir.glob("*.jsonl"))
        status["metrics_files"] = len(metric_files)
        # Total lines across all metrics
        total_entries = 0
        for mf in metric_files:
            try:
                with open(mf, "r") as f:
                    total_entries += sum(1 for _ in f)
            except OSError:
                pass
        status["total_metric_entries"] = total_entries
    else:
        status["metrics_files"] = 0
        status["total_metric_entries"] = 0

    # Active tasks
    for tasks_path in [
        PROJECT_ROOT / ".claude" / "tasks" / "active-tasks.json",
        PROJECT_ROOT / ".cognitive-os" / "tasks" / "active-tasks.json",
    ]:
        tasks = _read_json(tasks_path)
        if tasks:
            task_list = tasks.get("tasks", [])
            status["active_tasks"] = {
                "total": len(task_list),
                "pending": sum(1 for t in task_list if t.get("status") == "pending"),
                "in_progress": sum(1 for t in task_list if t.get("status") == "in_progress"),
                "completed": sum(1 for t in task_list if t.get("status") == "completed"),
            }
            break
    else:
        status["active_tasks"] = {"total": 0, "message": "No active-tasks.json found"}

    # Sessions
    sessions_dir = PROJECT_ROOT / ".cognitive-os" / "sessions"
    if sessions_dir.is_dir():
        session_dirs = [d for d in sessions_dir.iterdir() if d.is_dir()]
        status["active_sessions"] = len(session_dirs)
    else:
        status["active_sessions"] = 0

    # Content policy
    policy_path = PROJECT_ROOT / ".cognitive-os" / "content-policy.yaml"
    status["content_policy"] = policy_path.is_file()

    return json.dumps(status, indent=2, default=str)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()

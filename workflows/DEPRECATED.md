# DEPRECATED: Legacy Pipeline System

> This directory contains the legacy pipeline system from the Sazonia project archive.
> It is superseded by the `lib/` modules and should NOT receive new code.

## Status

**Deprecated** as of March 2026. Retained as reference code only.

## What This Was

The `workflows/` directory was the original pipeline execution system built for the Sazonia project. It provided:

- `workflows/lib/agent.py` -- Claude agent executor
- `workflows/lib/git.py` -- Git operations for worktree-based pipelines
- `workflows/lib/data_types.py` -- Pipeline data structures
- `workflows/lib/shared_phases.py` -- Reusable SDD phase implementations
- `workflows/lib/telegram.py` -- Notification integration
- `workflows/lib/clickup.py` -- ClickUp task management integration
- `workflows/lib/file_parser.py` -- File parsing utilities
- `workflows/lib/utils.py` -- General utilities
- `workflows/run.py` -- Pipeline runner entry point
- `workflows/backend_*.py` -- Service-specific pipeline definitions

## What Replaced It

The `lib/` directory contains the current execution system with better typing, structured results (`ClaudeResult`), and proper error handling:

| Legacy (`workflows/lib/`) | Current (`lib/`) | Notes |
|---------------------------|------------------|-------|
| `agent.py` | `claude_executor.py` | Typed `ClaudeResult`, timeout handling, cost tracking |
| `git.py` | (integrated into `issue_pipeline.py`) | Worktree management merged into pipeline |
| `data_types.py` | (integrated into each module) | Per-module dataclasses instead of shared types |
| `shared_phases.py` | `sdd_resume.py` | Phase resumption with Engram state |
| `telegram.py` | `notifications.py` | Multi-provider: Telegram + webhook support |
| `run.py` | `batch_runner.py` | Sequential/parallel batch execution with cost tracking |
| N/A | `singularity.py` | New: autonomous MAPE-K control loop |
| N/A | `domain_router.py` | New: domain-aware verification routing |
| N/A | `webhook_trigger.py` | New: GitHub webhook -> pipeline automation |
| N/A | `impact_analysis.py` | New: change impact analysis |
| N/A | `phase_timing.py` | New: SDD phase timing and estimation |

## Migration Path

If you find code importing from `workflows.lib`, migrate it:

```python
# Before (legacy)
from workflows.lib.agent import run_claude_agent
from workflows.lib.data_types import PipelineResult

# After (current)
from lib.claude_executor import ClaudeExecutor, ClaudeResult
```

## Do NOT

- Add new pipeline code to `workflows/`
- Import from `workflows.lib` in new code
- Modify existing files in `workflows/` (they are frozen reference)

## Why Not Delete It

The legacy pipelines contain project-specific logic (Sazonia service definitions, ClickUp integration patterns) that may be useful as reference when building similar integrations. Deletion is planned once all reference value has been extracted.

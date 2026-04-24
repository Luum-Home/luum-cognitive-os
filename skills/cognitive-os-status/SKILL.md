<!-- SCOPE: os-only -->
---
name: cognitive-os-status
description: "Full health check of all Cognitive OS components"
triggers: ["/cognitive-os-status", "/aos-status", "/health"]
audience: both
---

# /cognitive-os-status

> Complete health report of the Cognitive OS in one command.


## Instructions

Run a comprehensive health check of every Cognitive OS subsystem. Output a single ASCII table with component, status, and details. No verbose explanations.

### Step 1: Check Hooks

Read `.claude/settings.local.json`. Extract all hook entries across all lifecycle events (SessionStart, PreToolUse, PostToolUse, PreCompact, Stop). For each hook:
- Extract the .sh file path (resolve `$CLAUDE_PROJECT_DIR` to the project root)
- Check if the file exists and is executable (`test -x`)
- Count total registered vs total executable

Status: OK if all executable, WARN if some missing, FAIL if none found.

### Step 2: Check Rules

Count rule files:
- `.cognitive-os/rules/*.md` (exclude RULES-COMPACT.md from count)
- `.claude/rules/*.md`
- Verify `RULES-COMPACT.md` exists in `.cognitive-os/rules/`

Status: OK if RULES-COMPACT.md exists and rules > 0, WARN if RULES-COMPACT.md missing.

### Step 3: Check Skills

Count skill directories:
- `.cognitive-os/skills/*/SKILL.md` (OS skills)
- `.claude/skills/*/SKILL.md` (project skills, if any)
- Verify `CATALOG.md` exists in `.cognitive-os/skills/`

Status: OK if CATALOG.md exists, WARN if missing.

### Step 4: Check Squads

Count YAML files in `.cognitive-os/squads/*.yaml`.

Status: OK if > 0, WARN if 0.

### Step 5: Check Agents

Count agent persona files:
- `.cognitive-os/agents/*.md`
- `~/.claude/agents/*.md`

Status: OK if > 0, WARN if 0.

### Step 6: Check Metrics

List `.jsonl` files in `.cognitive-os/metrics/`. For each, count lines (`wc -l`). Report how many have data (> 0 lines) vs total.

Status: OK if all have data, WARN if some empty, FAIL if dir missing.

### Step 7: Check Config

Read `cognitive-os.yaml`:
- Extract `project.phase`
- Extract `resources.budget.monthly_limit_usd`
- Show current phase and budget

Status: OK if file exists and parseable.

### Step 8: Check Docker Cognitive OS Services

Run:
```bash
docker compose -f docker-compose.cognitive-os.yml ps --format json 2>/dev/null
```

Check status for: nemo-guardrails, paperclip. Report healthy/unhealthy/not running for each. (ADR-058: the former observability trace-UI stack was removed; LLM observability is now Phoenix via `uv run phoenix serve`, checked separately as a pip process.)

If docker compose fails or file not found, report all as "not running".

### Step 9: Check Engram

Call `mem_context` to verify engram is accessible. If it returns data, report OK with observation count if available. If it fails, report FAIL.

### Step 10: Check Progressive Loading

Verify both files exist and count tokens (approximate: `wc -w` as proxy):
- `.cognitive-os/skills/CATALOG.md`
- `.cognitive-os/rules/RULES-COMPACT.md`

Report combined word count as approximate token count.

Status: OK if both exist, WARN if one missing.

### Step 11: Check Templates

Count files in `.cognitive-os/templates/*.md`.

Status: OK if > 0, WARN if 0.

### Step 12: Check Workflows

Verify `.cognitive-os/workflows/run.py` exists. Count Python pipeline files (`*_pipeline.py`).

Status: OK if run.py exists, WARN if missing.

### Step 13: Check Plans

Count subdirectories with content in `.cognitive-os/plans/` (exclude README.md).

Status: OK always (0 plans is fine).

### Output Format

Print the results as an ASCII table:

```
╔═══════════════════╦════════╦═══════════════════════════════╗
║ Component         ║ Status ║ Details                       ║
╠═══════════════════╬════════╬═══════════════════════════════╣
║ Hooks             ║ OK     ║ 18 registered, 18 executable  ║
║ Rules             ║ OK     ║ 22 rules (16 OS + 6 project)  ║
║ Skills            ║ OK     ║ 21 skills (OS) + CATALOG.md   ║
║ Squads            ║ OK     ║ 5 squad definitions           ║
║ Agents            ║ OK     ║ 19 personas (3 OS + 16 global)║
║ Metrics           ║ WARN   ║ 3/10 files have data          ║
║ Phase             ║ OK     ║ reconstruction                ║
║ Budget            ║ OK     ║ $0/$200 monthly               ║
║ Phoenix (pip)     ║ OK     ║ reachable on :6006            ║
║ LiteLLM           ║ OK     ║ healthy on :4000              ║
║ NeMo Guardrails   ║ FAIL   ║ not running                   ║
║ Paperclip         ║ FAIL   ║ not running                   ║
║ Engram            ║ OK     ║ accessible                    ║
║ Progressive Load  ║ OK     ║ ~1,200 tokens                 ║
║ Templates         ║ OK     ║ 6 templates                   ║
║ Workflows         ║ OK     ║ 5 pipelines                   ║
║ Plans             ║ OK     ║ 0 active plans                ║
╚═══════════════════╩════════╩═══════════════════════════════╝

Overall: 14/17 OK, 1 WARN, 2 FAIL
```

Use the exact box-drawing characters shown. Adjust column widths to fit content. The "Overall" summary line goes after the table.

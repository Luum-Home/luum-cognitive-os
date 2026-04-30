<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Context Optimization Protocol

## Purpose

Reduce baseline token overhead from ~17,500 tokens to ~3,500 tokens per session (~80% reduction).

## 3-Level Progressive Skill Loading

| Level | What | When | Budget |
|-------|------|------|--------|
| Level 1 | CATALOG-COMPACT.md (name + 1-line per skill) | Always loaded at session start | ~1.5-2K tokens |
| Level 2 | Full SKILL.md | When skill is invoked or trigger matches | ~1-3K per skill |
| Level 3 | references/ files | When detailed examples needed | ~2-5K per skill |

### Loading Rules

- ONLY `skills/CATALOG-COMPACT.md` is loaded at session start (Level 1). Regenerate it
  with `python3 scripts/generate_compact_catalog.py` whenever a skill is added, renamed,
  or retired.
- `skills/CATALOG.md` (the full catalog with invocations, audience columns, and section
  notes) is NOT loaded at session start. Invoke `/catalog-full` on demand to load it.
- When a skill is needed (user invokes or contextual trigger), load the full SKILL.md (Level 2)
- When detailed reference is needed during implementation, load references/ files (Level 3)
- Never load more than 5 skills simultaneously
- Unload unused skills after 5 minutes of inactivity

### Contextual Triggers

Skills auto-load (Level 2) when the agent detects relevant context:

| Trigger | Skills Loaded |
|---------|---------------|
| Editing `*.go` files | go-service-patterns, go-architecture |
| Editing `*.ts` files | typescript-patterns |
| Writing tests | testing-patterns |
| Error/failure detected | sre-agent, systematic-debugging |
| `/squad-report` invoked | squad-manager, squad-protocol |
| Cross-service work | architecture, services-config |

## Compact Rule Loading

| Strategy | Loaded | Budget |
|----------|--------|--------|
| `compact` | RULES-COMPACT.md only | ~1,500 tokens |
| `full` | All individual rule files | ~5,500 tokens |

### Contextual Rule Loading

Full rules are loaded on top of RULES-COMPACT.md when triggers match:

- `go-architecture.md` -- when editing Go files
- `sre-protocol.md` -- when errors are detected
- `constitutional-gates.md` -- when working on financial operations
- `services-config.md` -- when debugging connection/port issues
- `testing-local.md` -- when writing or running tests

## Token Budget Targets

| Metric | Target | Current (full load) |
|--------|--------|---------------------|
| Session start overhead | < 5,000 tokens | ~17,500 tokens |
| Per-agent overhead | < 3,000 tokens | ~8,000 tokens |
| Savings vs full load | > 75% | — |
| Max active skills | 5 | all loaded |

## Metrics

Context usage can be logged to `.cognitive-os/metrics/context-usage.jsonl`. Logging is agent-instruction-only — no automatic hook fires for context monitoring. Agents MUST self-monitor context thresholds per `rules/context-management.md` (50% / 70% / 85%).

Fields tracked:
- `catalog_tokens`: tokens used by CATALOG-COMPACT.md (Level 1)
- `rules_tokens`: tokens used by RULES-COMPACT.md
- `total_overhead`: sum of catalog + rules at session start
- `full_load_tokens`: what full loading would cost
- `savings_pct`: percentage saved

## Dual-Search Protocol for Artifacts (BMAD v6 Pattern 11)

When searching for any artifact (spec, design, plan, proposal, etc.), agents MUST follow a three-step search protocol that handles both small projects (single files) and large projects (sharded documents).

### Search Order

```
Step 1: Search for complete file
    │
    ├── Found → Use it
    └── Not found or too large
         │
         v
Step 2: Search for sharded version
    │
    ├── Found index → Load index + relevant sections
    └── Not found
         │
         v
Step 3: Search in Engram
    │
    ├── Search by topic key (prefixed per engram-organization.md)
    ├── If not found: search by legacy key (sdd/{change}/...)
    └── If not found: search by keyword
```

### Step 1: Complete File Search

Look for the artifact as a single file:

| Artifact | File Pattern |
|----------|-------------|
| Proposal | `{change-name}/proposal.md`, `openspec/changes/{change}/proposal.md` |
| Spec | `{change-name}/spec.md`, `openspec/changes/{change}/spec.md` |
| Design | `{change-name}/design.md`, `openspec/changes/{change}/design.md` |
| Tasks | `{change-name}/tasks.md`, `openspec/changes/{change}/tasks.md` |
| Plan | `plans/{plan-name}.md` |

### Step 2: Sharded Version Search

For large artifacts that have been split:

| Artifact | Shard Pattern |
|----------|--------------|
| Proposal | `{change-name}/proposal/index.md` + `proposal/section-*.md` |
| Spec | `{change-name}/spec/index.md` + `spec/section-*.md` |
| Design | `{change-name}/design/index.md` + `design/component-*.md` |
| Tasks | `{change-name}/tasks/index.md` + `tasks/batch-*.md` |

When loading sharded artifacts:
1. Always load `index.md` first (contains structure and cross-references)
2. Load only the sections relevant to the current task
3. Never load all sections at once unless explicitly needed

### Step 3: Engram Search

Follow the search strategy from `engram-organization.md`:
1. Search with prefixed topic key: `planning/{change}/spec`
2. Fall back to legacy key: `sdd/{change}/spec`
3. Fall back to keyword search: `{change} spec`
4. Always use `mem_get_observation` for full content (search results are truncated)

### Integration with Context Budget

The dual-search protocol respects token budgets:
- If a complete file exceeds `level2_budget` (30K tokens), prefer the sharded version
- If sharded sections exceed budget, load only the index + most relevant section
- Log which search step succeeded in `.cognitive-os/metrics/context-usage.jsonl`

## Configuration

All settings in `cognitive-os.yaml` under `skills.loading`, `rules.loading`, and `cost.optimization`.

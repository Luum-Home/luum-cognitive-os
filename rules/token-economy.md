<!-- SCOPE: both -->
# Token Economy — Cost Transparency and Waste Prevention

## The 5 Token Principles (ALWAYS ACTIVE)

### 1. Transparency

The user must know their cost at all times. Every session MUST report cost on completion.
Cost-per-action should be estimable before execution. Use `lib/cost_dashboard.py` for
formatted cost reports and `format_compact_status()` for mid-session awareness.

### 2. Worthiness

Before each action, evaluate if the tokens are worth spending:
- Reading a 5000-line file when you need 3 lines is waste. Use offset+limit.
- Using opus for a rename is waste. Use haiku.
- Launching an agent for a grep is waste. Use Grep tool directly.
- Re-exploring something Engram already knows is waste. Search memory first.

### 3. Decomposition

Complex problems MUST be decomposed into smaller tasks. Each task uses the minimum
model needed. Do not use one opus call for what 5 haiku calls can do better and cheaper.
See `rules/decomposition.md` for thresholds and guidelines.

### 4. Memory-First

Before any research or exploration, check Engram. If the answer exists from a previous
session, do not spend tokens re-discovering it. Every `mem_search` costs ~100 tokens.
Every re-exploration costs ~5000+ tokens. The 50x ratio makes memory-first mandatory.

### 5. Optimize by Default

Use the cheapest model that can handle the task. Progressive escalation: haiku, then
sonnet, then opus. Only escalate when quality is insufficient, not preemptively.
Check `rules/model-routing.md` for the routing table.

## Cost Awareness Rules

- Session cost MUST be reported in session summary (use `CostDashboard.format_session_report()`)
- Agent launches SHOULD include estimated cost in the delegation prompt
- Model downgrade chain activates at 80% daily budget (per `rules/resource-governance.md`)
- Skills should document their typical cost range in frontmatter

## Anti-Waste Patterns

| Waste Pattern | Fix |
|---------------|-----|
| Full file read for a few lines | `Read` with `offset` + `limit` |
| `cat` or `head` via Bash | Use `Read` tool with limits |
| Search via file reading | Use `Grep` tool instead |
| opus for simple tasks | Route to haiku (archiving, formatting, docs) |
| Re-discovering known info | `mem_search` before exploring |
| Large command output | Pipe through `tail`, `head`, or `grep` |
| Launching agent for 1 command | Run the command directly |
| Reading full test output | Use `--summary` or `tail -20` |

## Integration

- **Cost Dashboard**: `lib/cost_dashboard.py` provides session/daily/monthly reports
- **Resource Governance**: `rules/resource-governance.md` enforces budget limits
- **Model Routing**: `rules/model-routing.md` maps tasks to optimal models
- **Context Optimization**: `rules/context-optimization.md` reduces token overhead
- **Decomposition**: `rules/decomposition.md` breaks costly tasks into cheaper sub-tasks

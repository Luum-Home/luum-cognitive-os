<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Resource Governance Protocol

## Budget Enforcement (ALWAYS ACTIVE)

- Read budget limits from cognitive-os.yaml `resources.budget` section
- Before launching ANY sub-agent, check:
  - daily spend vs `daily_alert_usd` threshold
  - monthly spend vs `monthly_limit_usd`
  - If > 80% monthly: use sonnet instead of opus
  - If > 95% monthly: use haiku, warn user
  - If > 100% monthly: BLOCK agent launches, alert user

### Cost Estimation Before Launch

Before spawning a sub-agent, estimate its cost:
```
estimated_cost = (expected_input_tokens * input_price + expected_output_tokens * output_price) / 1_000_000
```

Model prices (per 1M tokens):
| Model | Input | Output |
|-------|-------|--------|
| opus | $15.00 | $75.00 |
| sonnet | $3.00 | $15.00 |
| haiku | $0.25 | $1.25 |

If `estimated_cost + daily_spend > daily_alert_usd`: warn before launching.
If `estimated_cost + monthly_spend > monthly_limit_usd`: BLOCK and alert user.

### Cost Logging

After every agent completion, log to `.cognitive-os/metrics/cost-events.jsonl`:
```json
{"timestamp":"ISO","agent":"name","model":"sonnet","input_tokens":1200,"output_tokens":3400,"estimated_cost_usd":0.07}
```

## Infrastructure Auto-Scale

- Start Docker services ON DEMAND:
  - Observability (Phoenix): now a pip process, started via `uv run phoenix serve`; stopped with Ctrl+C (not Docker-managed)
  - NeMo Guardrails: start when PII detected in content, stop after 15min idle
  - Paperclip: start when `/squad-report` or governance review, stop after 30min idle
- Check idle containers: `docker ps --filter status=running` vs actually being called
- Log infra events to `.cognitive-os/metrics/infra-usage.jsonl`

### Infra Event Format
```json
{"timestamp":"ISO","container":"paperclip","event":"start|stop|idle_detected","reason":"on_demand|idle_timeout|manual"}
```

## Agent Launch Governance

- Max parallel agents: read from `resources.compute.max_parallel_agents` (default: 5)
- If launching N agents and N > max: queue in batches of `batch_size`
- Agent timeout: kill after `resources.compute.agent_timeout_seconds` (default: 300s)
- Before launching: estimate cost (model x expected tokens x price)
- After completion: log actual cost to cost-events.jsonl

### Batch Queuing

When parallel agent limit is reached:
1. Queue excess agents in FIFO order
2. Launch next queued agent when a running agent completes
3. Log queuing events to resource-checks.jsonl

## Model Downgrade Chain

When budget pressure detected:
1. opus ($15/$75 per 1M) -> sonnet ($3/$15) — 5x cheaper
2. sonnet -> haiku ($0.25/$1.25) — 12x cheaper
3. haiku -> openrouter/free ($0/$0) — free tier, degraded quality
4. openrouter/free -> BLOCK (no more agents until budget resets)

### Downgrade Rules

| Budget Used | Action |
|-------------|--------|
| < 80% | Use routing table as-is |
| 80-95% | Force sonnet for all non-critical tasks (design, debugging stay opus) |
| 95-100% | Force haiku for everything except security/critical tasks |
| 99-100% | Route to openrouter/free for non-critical tasks |
| > 100% | BLOCK all agent launches except openrouter/free for trivial tasks, full BLOCK at 110% |

## Token Conservation

- Sub-agents get ONLY the skills they need (not the full catalog)
- Context summarization at 70% window usage (`resources.tokens.auto_summarize_at_percent`)
- Auto-unload skills after `resources.tokens.skill_cache_ttl_seconds` (default: 300s) unused
- Compress rules to bullet points for sub-agents when `resources.tokens.rule_compression` is "aggressive"

### Context Budget Per Agent

Each sub-agent has a context budget based on its task complexity:
| Task Type | Max Context (tokens) |
|-----------|---------------------|
| Documentation, archiving | 10,000 |
| Implementation, testing | 30,000 |
| Design, architecture | 50,000 |
| Debugging, root cause analysis | 50,000 |

## Resource Check Logging

Every resource governance decision is logged to `.cognitive-os/metrics/resource-checks.jsonl`:
```json
{"timestamp":"ISO","action":"agent_launch|model_downgrade|budget_block|infra_scale","decision":"allow|deny|downgrade","reason":"description","agent":"name","model_requested":"opus","model_assigned":"sonnet"}
```

## Governor Schedule

- Auto-run `/resource-governor` every N sessions (configured in `resources.optimization.governor_interval_sessions`)
- Auto-run on session end if `resources.optimization.auto_run_on_session_end` is true
- Manual run: user invokes `/resource-governor`

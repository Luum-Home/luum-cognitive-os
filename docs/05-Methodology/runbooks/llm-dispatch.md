# Runbook: LLM Dispatch (ADR-049)

**Audience**: operator of the Cognitive OS. Covers daily operational tasks
around the sub-agent dispatch system (Qwen primary + Claude fallback).

## 1. Quick start (first time)

### 1.1 Verify the machinery is wired

```bash
bash scripts/smoke-qwen-fallback.sh
```

Expected: `ALL 4 CHECKS PASS`. If any fails, go to §5 Troubleshooting.

### 1.2 Check provider state

```bash
python3 scripts/llm_status.py
```

Verify:
- `alibaba_qwen ✓ configured` with API key redacted
- No kill-switches active
- Recent dispatches (or "no data" if this is a fresh install)

### 1.3 Dispatch a test task

```bash
uv run python3 scripts/orchestrator.py \
  --task "Respond with exactly: OK" \
  --providers qwen,claude
```

Expected output:
```
agent_id:    orch-xxxxxxxx
provider:    alibaba_qwen
success:     True
elapsed:     2.3s
input_tok:   12
output_tok:  2
cost_usd:    0.0001
```

## 2. Activate (fresh install, no key yet)

### 2.1 Subscribe to Alibaba Qwen Coding Plan Pro

- Sign up at https://www.alibabacloud.com/en/campaign/ai-coding-plan
- Choose Pro tier ($50/mo, 90K requests/month — first month $15 promo)
- Wait for "Active" status (can show "out of stock, restocking at HH:MM"
  — plans are released in daily batches)

### 2.2 Generate an API key in Model Studio

- Go to Alibaba Cloud Model Studio → API Keys → Create
- Note your workspace ID (e.g. `ws-xxxxx.ap-southeast-1.maas.aliyuncs.com`)
- Copy the key starting with `sk-...`

### 2.3 Add to .env

```bash
cat >> .env <<EOF
# ADR-049 LLM dispatch — Qwen overflow provider
ALIBABA_QWEN_API_KEY=sk-<your-key>
ALIBABA_QWEN_BASE_URL=https://<your-workspace>.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
EOF
```

**NEVER paste the key in chat, commit, PR description, or issue tracker.**
`.env` is gitignored. Rotate immediately if exposure is suspected.

### 2.4 Install the openai SDK

```bash
uv sync --extra direct_providers
```

### 2.5 Verify

```bash
bash scripts/smoke-qwen-fallback.sh
# Expected: ALL 4 CHECKS PASS
```

## 3. Dispatch patterns

### 3.1 Default cascade (recommended)

```bash
uv run python3 scripts/orchestrator.py --task "<your task>"
# providers default: qwen,claude
```

Qwen handles it; if Qwen fails, Claude fallback fires.

### 3.2 Single provider only

```bash
uv run python3 scripts/orchestrator.py --task "<task>" --providers qwen
# or
uv run python3 scripts/orchestrator.py --task "<task>" --providers claude
```

### 3.3 Invert priority (Claude primary — only when quality is critical)

```bash
uv run python3 scripts/orchestrator.py --task "<task>" --providers claude,qwen
```

Claude tries first; if rate-limited, Qwen picks up.

### 3.4 Programmatic (from Python)

```python
from lib.dispatch import dispatch

result = dispatch(
    prompt="Summarize the last commit",
    providers=["qwen", "claude"],
    task_type="general",
    skill_name="my-skill",  # optional, for metrics
)
if result.success:
    print(result.text, f"${result.cost_usd:.4f}")
```

### 3.5 Sub-agent with tool use (Qwen agent loop, ADR-051 Phase 1)

For multi-step tasks (Read file → Edit → run Bash), use
`lib/qwen_agent_loop.py`:

```python
from lib.qwen_agent_loop import run_agent

r = run_agent(
    task="Read pyproject.toml and list all optional extras",
    tools_allowed=["read_file"],  # whitelist
    max_iterations=10,
)
```

Note: tool set limited to Read/Edit/Bash in Phase 1. Grep/WebFetch/etc
arrive in Phase 2.

## 4. Deactivate / Kill-switches

### 4.1 Soft — remove API key

```bash
# Edit .env — comment out or delete:
# ALIBABA_QWEN_API_KEY=sk-...
```

Effect: cascade skips Qwen, uses Claude directly.

### 4.2 Disable Qwen this session

```bash
export COS_DISABLE_QWEN=1
```

Effect: cascade skips Qwen regardless of API key.

### 4.3 Force Claude-only this session

```bash
export COS_FORCE_CLAUDE_PRIMARY=1
```

Effect: `--providers` list rewritten to `["claude"]`.

### 4.4 Block all cascade fallback

```bash
export COS_DISABLE_LLM_FALLBACK=1
```

Effect: primary provider fires; if it fails, error surfaces immediately.
Use for debugging (see raw errors) or strict single-provider policy.

### 4.5 Agent-safe Qwen smoke without `.env`

Use `COS_SKIP_DOTENV=1` when an agent or automation must run the Qwen live
smoke using only already-exported environment variables. This avoids indirectly
loading repo-local `.env` while preserving the default human workflow.

```bash
export ALIBABA_QWEN_API_KEY=...
COS_SKIP_DOTENV=1 bash scripts/smoke-qwen-fallback.sh
```

### 4.6 Credential-safe Qwen smoke with allowlisted `.env` keys

When the operator explicitly wants the agent to run the live smoke using
repo-local `.env` credentials, use the credential-safe primitive instead of
running the smoke script directly:

```bash
scripts/cos-credential-safe-run qwen-fallback-smoke --approve
```

The wrapper reads only `ALIBABA_QWEN_API_KEY`, `ALIBABA_QWEN_BASE_URL`, and
`ALIBABA_QWEN_WORKSPACE_ID` from `.env`, forces `COS_SKIP_DOTENV=1` for the
child process, verifies the pinned script hash, starts the child with a
sanitized environment, redacts output, bounds model-visible output, and writes
`.cognitive-os/metrics/credential-safe-runs.jsonl` without secret values.

### 4.7 Re-enable

```bash
unset COS_DISABLE_QWEN COS_FORCE_CLAUDE_PRIMARY COS_DISABLE_LLM_FALLBACK COS_SKIP_DOTENV
```

## 5. Troubleshooting

### 5.1 `meta.llm_providers_reachable` = ASPIR ("SDK not installed")

```bash
uv sync --extra direct_providers
```

### 5.2 Qwen 401 `Incorrect API key`

- Check `.env` — key present, no whitespace/quotes?
- Test: `echo $ALIBABA_QWEN_API_KEY | wc -c` should be 37 chars (35 +
  trailing newline)
- Verify in Alibaba Cloud panel the key is Active
- If subscription is still "out of stock", plan purchase hasn't
  processed — wait for restock window
- Key was pasted in chat? Rotate immediately (see §6 Security)

### 5.3 Qwen base URL 404

Workspace-scoped endpoints look like:
`https://ws-xxxxx.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`

Verify in Alibaba Model Studio panel under your workspace.

### 5.4 "provider qwen unavailable — advancing cascade"

Means `_try_qwen` returned None. Causes:
- `ALIBABA_QWEN_API_KEY` not set → add to `.env`
- `COS_DISABLE_QWEN=1` → unset
- `openai` SDK not installed → `uv sync --extra direct_providers`

### 5.5 Claude Max rate-limit blocks primary chat (you can't type to
orchestrator)

**This is NOT solved by ADR-049** — Claude Code native chat can't be
redirected. Workaround:

1. **Wait for reset** — local time shown in the error message
2. **Dual-IDE**: open Cline / Cursor / Qwen Code configured with your
   Qwen key. Continue work there until Claude Code recovers.
3. **CLI dispatch**: while waiting, use
   `uv run python3 scripts/orchestrator.py --task "..."` from terminal
   for batch work. That uses Qwen directly (doesn't touch Claude Max).

### 5.6 Tests pass but LIVE API fails

Run the live probe:
```bash
uv run python3 -c "
from lib.qwen_provider import call
r = call([{'role':'user','content':'ping'}])
print(r)
"
```

Common causes:
- Network issue
- Key expired (regenerate in Alibaba panel)
- Subscription ended (check billing)

## 6. Security

### 6.1 API key exposure response

If an API key was pasted anywhere visible (chat, PR, Slack, email):

1. **Revoke immediately** in Alibaba Cloud Model Studio → API Keys
2. **Generate new key**
3. **Update `.env`** on all machines that use it
4. Search transcripts/logs for the key prefix (`sk-xxxxxx`) and redact
5. Rotate quarterly as best practice

### 6.2 `.env` hygiene

- `.env` is in `.gitignore` — verify: `grep -F '.env' .gitignore`
- Never commit `.env`
- Use `env.example` as the template (has placeholders, no real keys)
- Share keys via password manager only, never plaintext

### 6.3 Audit access

```bash
tail -20 .cognitive-os/metrics/llm-dispatch.jsonl
```

Review recent dispatches — provider_used, cost, task_type. Unexpected
patterns (spike in claude calls, unknown skill_name) = investigate.

## 7. Cost monitoring

### 7.1 Daily totals

```bash
python3 scripts/llm_status.py --days 1
```

### 7.2 Monthly totals by provider

```bash
python3 scripts/llm_status.py --days 30
```

### 7.3 Raw ingestion for custom analysis

```bash
# Total cost last 7 days
python3 -c "
import json, time
from pathlib import Path
cutoff = time.time() - 7*86400
total = 0.0
for line in Path('.cognitive-os/metrics/llm-dispatch.jsonl').read_text().splitlines():
    try:
        r = json.loads(line)
        ts = time.mktime(time.strptime(r['ts'], '%Y-%m-%dT%H:%M:%SZ'))
        if ts >= cutoff:
            total += r.get('cost_usd', 0)
    except: pass
print(f'\${total:.4f}')
"
```

## 8. Expected state matrix

| Indicator | Healthy value |
|---|---|
| `meta.llm_providers_reachable` in `cos-config-audit` | IMPL |
| `scripts/smoke-qwen-fallback.sh` | 4/4 PASS |
| `python3 scripts/llm_status.py` | ≥1 provider configured, no kill-switches |
| `.cognitive-os/metrics/llm-dispatch.jsonl` | Writing records on each dispatch |
| Unit tests | `pytest tests/unit/test_dispatch.py` all pass |

## Related

- `rules/llm-dispatch.md` — normative rule
- `docs/02-Decisions/adrs/ADR-049-llm-gateway-selection-and-overflow-providers.md` — decision record
- `.cognitive-os/plans/roadmaps/adr-049-050-051-mega-plan.md` — checkpoint roadmap
- `skills/llm-status/SKILL.md` — skill user invokes
- `lib/dispatch.py` — dispatch implementation
- `lib/qwen_provider.py` — Qwen direct-SDK
- `lib/qwen_agent_loop.py` — tool-use loop (ADR-051 Phase 1)

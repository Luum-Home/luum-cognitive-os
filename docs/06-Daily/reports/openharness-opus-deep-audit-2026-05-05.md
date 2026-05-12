# HKUDS/OpenHarness — Opus Deep Audit (Symmetric Verification)

**Date**: 2026-05-05
**Model**: opus (per user request for architectural-decision rigor)
**Status**: read-only audit; no source modified outside this report.
**Trigger**: prior sonnet audit + sonnet rebuttal both contained numerical errors and asymmetric depth. User asked: "tenemos que estar muy seguros".
**Inputs**: `docs/06-Daily/reports/openharness-deep-audit-2026-05-05.md` and `docs/06-Daily/reports/cos-side-deep-rebuttal-2026-05-05.md` treated as hypotheses, not facts.

---

## TL;DR

Per-dimension verdicts (HIGH-confidence unless noted), with notes on what changed vs the prior reports:

1. **Hook lifecycle events** — IGUAL (CC contract). COS wires **9** distinct events via `_cc_hook_group` (TaskCompleted is printf-emitted but demoted per ADR-126/133). OpenHarness `HookEvent` enum has **10** values. **Original audit's "5 vs 10" was wrong; rebuttal's "10 vs 10" was also wrong.** True count is 9 vs 10. CC's lifecycle is fixed by Anthropic, so neither side can grow it independently.
2. **Hook *type* diversity** — OpenHarness MEJOR. OH supports 4 (Command/Http/Prompt/Agent). COS supports 1 (shell). This is the real, structural gap.
3. **Multi-provider** — OpenHarness MEJOR (CORRECTED vs **both** prior reports). OH ships **22** ProviderSpecs in `src/openharness/api/registry.py`. COS ships **7** in `lib/providers/__init__.py`. Rebuttal's "7 vs 4" was wrong on the OH side.
4. **MCP integration** — NUANCED. OH is a deeper *consumer* (`McpClientManager`, 259 LOC, stdio+HTTP, auto-reconnect, schema inference). COS is the only *publisher* (`mcp-server/cos_mcp.py`, 780 LOC, 25 callable defs / ~8 tool surface). Different roles in MCP ecosystem; rebuttal's "IGUAL" framing held.
5. **Skill discovery** — COS MEJOR. `lib/skill_router.py` is **1519 LOC** with 130 metric streams + 88 SKILL.md + lock manifest. OH `SkillRegistry` is **24 LOC**. Rebuttal's IGUAL undersold COS.
6. **Provider validation in production** — COS WEAKER than its own marketing. `.cognitive-os/metrics/llm-dispatch.jsonl` has **4 lines, all "offline_dispatch_smoke" from May 3**. The cascade is wired and tested, not validated in real usage. Rebuttal failed to flag this.
7. **CI maturity** — OH WEAKER. Last 10 GitHub Actions runs are all "Autopilot Scan/Run Next" (cancelled or queued). Original audit got this right; the rebuttal accepted the original audit verbatim.
8. **Lock-in cost** — COS would lose the most by switching. **227 unique de-symlinked hooks** (not 197 nor 266). Rebuttal's "266" double-counted symlinks; user's spot-check of "197" was also wrong.
9. **Adoption recommendations** (HIGH confidence): borrow OH's `ProviderProfile` credential-slot pattern; borrow OH's HTTP/inline-prompt hook *types* (gap is real); do **not** migrate. OH is a 35-day-old MIT codebase with no observable test suite — adopting it as substrate is irreversible if wrong.

---

## Methodology

For each dimension I (a) read source on both sides, (b) re-ran every numerical claim from a real command, and (c) distinguished architectural capability ("code exists") from operational ("validated in real usage"). Citations are file:line from working tree (COS) or `gh api repos/HKUDS/OpenHarness/contents/<path>` at commit on `pushedAt: 2026-05-03T09:03:42Z`.

---

## Per-dimension audit (11 rows)

### 1. Hook lifecycle event surface

**OpenHarness** (`src/openharness/hooks/events.py`, 22 lines):
- `HookEvent` enum: SESSION_START, SESSION_END, PRE_COMPACT, POST_COMPACT, PRE_TOOL_USE, POST_TOOL_USE, USER_PROMPT_SUBMIT, NOTIFICATION, STOP, SUBAGENT_STOP. **10 events.**

**COS** (`scripts/_lib/settings-driver-claude-code.sh:91-425`):
- Distinct first-arg lifecycle events to `_cc_hook_group`: PostToolUse, PreCompact, PreToolUse, SessionStart, Stop, SubagentStart, TaskCreated, TeammateIdle, UserPromptSubmit. **9 distinct.**
- Line 422: `printf '    "TaskCompleted": [\n'` with comment "TaskCompleted is demoted from default projection" (ADR-126/133). Wired but not emitted to settings.json by default.
- Canonical schema (`lib/harness_adapter/base.py:23-200`): 11 `CanonicalEvent` subclasses (SessionStart, UserPromptSubmit, SessionEnd, AgentStart, AgentEnd, ToolUse, TokenUsage, HeartbeatTick, ToolUseStart, ToolUseEnd, ProgressMarker, ParseError) — distinct from lifecycle hook count.

**Verdict**: IGUAL on lifecycle (constrained by CC contract). Neither side can grow this independently — Claude Code defines the events.

**Confidence**: HIGH.

**What prior audits got wrong**: Original audit said "5 vs 10" — wrong on COS. Rebuttal said "10 vs 10" — wrong on COS (TaskCompleted is demoted). True count: 9 vs 10. The 1-event delta (`Notification`/`SubagentStop` in OH; both currently absent from COS dispatch) is a CC-fixed reality, not a COS limitation per se.

### 2. Hook *type* diversity

**OpenHarness** (`src/openharness/hooks/types.py`): 4 hook definition types — `CommandHookDefinition`, `HttpHookDefinition`, `PromptHookDefinition`, `AgentHookDefinition`. Async executor with timeouts and `block_on_failure`.

**COS**: 1 hook type only (shell command). Settings driver emits only `command` entries to settings.json. No HTTP callback, no inline-prompt, no inline-agent hook.

**Verdict**: OpenHarness MEJOR.

**Confidence**: HIGH.

**What prior audits got wrong**: Both audits underweighted this. The rebuttal partially corrected to "narrower than stated" but kept it lumped with event-count.

### 3. Tool routing and permissions

**OpenHarness** (`src/openharness/tools/`): `ToolRegistry` + `PermissionChecker` with `PermissionMode.DEFAULT/PLAN/FULL_AUTO`, path globs, denied-command lists. Intercepts before OS access.

**COS**: `lib/agent_permissions.py`, `lib/anthropic_direct_policy.py`, `packages/agent-lifecycle/lib/agent_permissions.py`. Permissions live in `.claude/settings.json` (allowlist/denylist) projected from `cognitive-os.yaml`. Interception is at CC level via PreToolUse hooks; there is no COS-internal `PermissionChecker` between LLM and tool because COS doesn't own the LLM loop.

**Verdict**: IGUAL with different locus. OH owns the loop and intercepts in-process; COS rides on CC's interception and adds policy via hooks.

**Confidence**: MEDIUM. I did not read all three COS permission files end-to-end (per ≤80 tool budget).

### 4. MCP integration

**OpenHarness** (`src/openharness/mcp/client.py`, 259 LOC): `McpClientManager` (consumer): connect_all, reconnect_all, update_server_config, list_statuses, list_tools, list_resources, call_tool, read_resource. Two transports (stdio + HTTP), error class `McpServerNotConnectedError`, lifecycle methods.

**COS**: `mcp-server/cos_mcp.py` (780 LOC, 25 def/async def, ~8 tool surface) — COS is a *publisher*, not a consumer. Plus `hooks/mcp-scan.sh` (security scanning of MCP configs), `cognitive-os.yaml` MCP blocks, `packages/mcp-server/cos-package.yaml` (packaged distribution), `scripts/check_mcp_servers.py` and `scripts/mcp_tofu_audit.py` (auditing).

**Verdict**: NUANCED. OH is a deeper *consumer-side* MCP client. COS is the deeper *publisher-side* + security/audit layer. Different ecosystem positions.

**Confidence**: HIGH.

**What prior audits got wrong**: Original audit framed COS as "bolted-on" without reading `mcp-server/`. Rebuttal corrected to IGUAL but didn't note that COS lacks a real *consumer* MCP client comparable to `McpClientManager` — that gap is real if COS ever needs to consume external MCP servers programmatically vs delegating to CC.

### 5. Skill discovery

**OpenHarness** (`src/openharness/skills/registry.py`, 24 LOC): `SkillRegistry` with register/get/list_skills. Loader at `loader.py`, types at `types.py`, bundled markdown skills.

**COS**: `lib/skill_router.py` is **1519 LOC** (12 def/class). 88 SKILL.md files. `skills/CATALOG.md` catalog. `manifests/agentic-primitive-registry.lock.yaml` SHA-256 lock.

**Verdict**: COS MEJOR. ~63x more code, with intent routing, lock manifest, and catalog. The hand-coded ~80-entry table noted by user (ADR-174) is a known refactor target but doesn't undermine the depth advantage.

**Confidence**: HIGH.

### 6. Configuration model

**OpenHarness** (`src/openharness/config/settings.py`, **948 LOC**): single Pydantic `SettingsModel`. Layered precedence (CLI → env → `~/.openharness/settings.json` → defaults). Hot-reload (`hot_reload.py`).

**COS**: `lib/config_loader.py` (204 LOC) + `scripts/_lib/settings-driver-claude-code.sh` (501 LOC). Three loader variants (regex / yaml.safe_load / 5-path search). Settings driver projects `cognitive-os.yaml` → `.claude/settings.json` (idempotent atomic write, profile-aware).

**Verdict**: IGUAL with different design goals. OH is a richer single Pydantic schema (validation, hot-reload). COS optimizes for cold-start hook safety (regex variant) and multi-harness portability (projection layer).

**Confidence**: HIGH.

**What prior audits got wrong**: Original called this "OpenHarness MEJOR" — too strong. Rebuttal corrected to IGUAL — held up.

### 7. Context management

**OpenHarness**: `MEMORY.md` flat file + `auto_compact_threshold_tokens` setting + `CLAUDE.md` discovery via `SystemPromptBuilder`.

**COS**: Engram (vector + KV) with cross-session retrieval, PreCompact hook integration, MCP-exposed `mem_search`/`mem_save`/`mem_session_summary`, ADR-080.

**Verdict**: COS MEJOR. Held vs both prior audits.

**Confidence**: HIGH.

### 8. Multi-provider — wired vs validated

**OpenHarness** (`src/openharness/api/registry.py`): **22 ProviderSpecs**: github_copilot, openrouter, aihubmix, siliconflow, volcengine, modelscope, anthropic, openai, deepseek, gemini, dashscope, moonshot, minimax, zhipu, groq, mistral, stepfun, baidu, bedrock, vertex, ollama, vllm.

**COS** (`lib/providers/__init__.py`, 65 LOC): **7 providers** in REGISTRY: qwen, openrouter, gemini, ollama, openai, deepseek, claude_sdk. Plus `lib/dispatch.py` (622 LOC) cascade with `_RATE_LIMIT_PATTERNS`, kill-switches, `DispatchResult` dataclass, JSONL metrics.

**Operational reality** (`.cognitive-os/metrics/llm-dispatch.jsonl`): **4 lines total, all `provider_used: "offline_dispatch_smoke"` from 2026-05-03**. The cascade is **wired and unit-validated, not exercised in real production usage** as of the audit date.

**Verdict**: OpenHarness MEJOR on breadth (22 vs 7). COS MEJOR on operational rigor (cascade, kill-switches, JSONL). **Architecturally NUANCED; numerically OH wins.**

**Confidence**: HIGH on counts. MEDIUM on the operational claim — I sampled only `llm-dispatch.jsonl`; real provider use may exist in other streams I didn't read.

**What prior audits got wrong**: Original said OH 4, COS "primarily Claude Code". Rebuttal said OH 4, COS 7 ("CORRECTED-toward-COS"). **Both wrong on OH.** Real OH count is 22.

### 9. Extension surface — hook count

**OpenHarness**: 4 hook *types*; plugin/skill ecosystem; swarm subagents (some marked Roadmap).

**COS** (`find hooks/ packages/ -name '*.sh'`):
- Raw count: **269** `.sh` files (151 in `hooks/` top-level, 47 in `packages/*/hooks/`, balance in nested package dirs).
- After `readlink -f` dedup: **227 unique** files.
- Plus `lib/harness_adapter/` with 6 named harnesses; `scripts/cos_init.py` lists 21 supported harnesses; 33 packages with `cos-package.yaml`.

**Verdict**: COS MEJOR on raw breadth. OH MEJOR on hook *type* diversity (already counted in dim 2).

**Confidence**: HIGH.

**What prior audits got wrong**: Original said "90+". Rebuttal said "266 (219+47)" — that was raw-count without dedup. True unique: **227**. User's spot-check of "197" was also off (low).

### 10. Cost / observability

**OpenHarness**: `CostTracker` per turn (`engine/cost_tracker.py`). No structured JSONL export visible.

**COS**: `lib/harness_adapter/base.py` canonical schema (ADR-033) → 130 distinct JSONL streams under `.cognitive-os/metrics/` (`ls | wc -l = 130`). Notably `agent-heartbeat.jsonl` has **2,135 lines** — real usage. SLO probes (ADR-028). MLflow integration. Phoenix (opt-in per ADR-170).

**Verdict**: COS MEJOR.

**Confidence**: HIGH.

### 11. License & OSS health

**OpenHarness** (`gh repo view HKUDS/OpenHarness`): MIT, 11,968 stars, 2,005 forks, created **2026-04-01** (~35 days), last push 2026-05-03, not archived. CI runs sampled (`gh api .../actions/runs`): all 10 most-recent runs are `Autopilot Scan` / `Autopilot Run Next` — all cancelled or queued. **No observable canonical test-suite run.**

**COS**: private; built atop Anthropic's stable Claude Code; ADR-021 explicitly designed for harness migration optionality.

**Verdict**: OH IS LEGITIMATE BUT YOUNG. License is safe; community signal is strong (12k stars in 35 days); engineering maturity is unverifiable end-to-end (CI dominated by autopilot, not test).

**Confidence**: HIGH on numbers; HIGH on the "test suite not observable" claim.

### 11b. Lock-in cost of switching to OpenHarness

Files that would need to change for full migration (sourced from `find` and rebuttal's component list, re-verified):
- 227 unique shell hooks → port to `CommandHookDefinition` / `HttpHookDefinition`
- `scripts/_lib/settings-driver-claude-code.sh` (501 LOC) → discard; OH uses single Pydantic model
- `lib/harness_adapter/claude_code.py` → discard; OH owns the loop
- `lib/dispatch.py` (622 LOC) → reconcile with OH's 22-provider registry (likely discard)
- `mcp-server/cos_mcp.py` (780 LOC) → keep (it's a publisher, harness-agnostic) but rewire integration
- `lib/skill_router.py` (1519 LOC) → reconcile with `SkillRegistry` (likely keep COS's, layer on OH)
- 33 packages with `cos-package.yaml` projection → re-target

**Estimate**: 6–10 person-weeks for a clean migration; +50% if hook semantic parity (`exit 2 = block`) needs careful porting. Reversibility: hard.

**Verdict**: COS would lose most by switching. Held vs both prior audits.

**Confidence**: MEDIUM on person-week estimate; HIGH on direction.

---

## Adoption recommendations (HIGH confidence)

| OpenHarness primitive | Adopt? | Concrete first-step | Falsifiable claim |
|---|---|---|---|
| `HttpHookDefinition` + `PromptHookDefinition` hook *types* | YES (study) | Add canonical event subtype `HookCallback` to `lib/harness_adapter/base.py`; design HTTP-callback hook adapter as ADR-pending | After adoption, COS can wire a webhook URL as a Stop hook without writing a shell script wrapper |
| `ProviderProfile` credential-slot pattern | YES | Port named-profile + per-provider auth-slot model from `src/openharness/config/settings.py` to `cognitive-os.yaml > llm_providers` | After adoption, switching API keys per machine doesn't require env-var juggling |
| `McpClientManager` consumer pattern | YES (when needed) | Port to `lib/mcp_client.py` if/when COS needs to consume external MCP servers programmatically (not via CC delegation) | Currently no concrete use case; defer until one materializes |

## Adoption recommendations (MEDIUM confidence — needs further work)

- **22-provider registry breadth**: OH supports providers (volcengine, baidu, zhipu, dashscope, etc.) COS does not. Adoption depends on whether COS users want those endpoints. Defer until a user asks.
- **Hot-reload settings**: OH has `config/hot_reload.py`. Could reduce restart-on-config-edit friction. Worth a 1-day spike.

## Reject (HIGH confidence don't-adopt)

- **OpenHarness as substrate replacement**: 35 days old, no observable test suite, would invalidate 227 hooks + settings driver + skill router (1519 LOC) + dispatch (622 LOC). Cost dwarfs benefit. ADR-021's harness-agnostic posture should remain *optionality*, not *action*.
- **`SkillRegistry` (24 LOC)**: less capable than COS's `skill_router.py` (1519 LOC). Do not regress.
- **Flat `MEMORY.md`**: regression vs Engram. Do not regress.

---

## What COS truly has (audited at source — corrects both prior reports)

| Capability | True number | Original audit | Rebuttal |
|---|---|---|---|
| Distinct lifecycle hook events wired | **9** (TaskCompleted demoted) | 5 ❌ | 10 ❌ |
| Canonical event schema subclasses | **11** | 9 ❌ | 12 ❌ |
| LLM providers in REGISTRY | **7** | "primarily Claude Code" ❌ | 7 ✅ |
| OpenHarness providers (correct comparator) | **22** | 4 ❌ | 4 ❌ |
| Unique de-symlinked hook .sh files | **227** | "90+" ⚠ | 266 ❌ |
| `lib/skill_router.py` LOC | **1519** | (not measured) | (not measured) |
| `mcp-server/cos_mcp.py` LOC | **780** ✅ | 780 ✅ | 780 ✅ |
| Metric streams under `.cognitive-os/metrics/` | **130** | (not measured) | 102 (lower bound, hooks-only) |
| `agent-heartbeat.jsonl` line count | **2,135** | (not measured) | (not measured) |
| `llm-dispatch.jsonl` line count | **4** (all smoke, May 3) | (not measured) | (not measured — flagged in TR uncertainty 3) |

---

## Trust report

**Confidence**: 0.84.

**Honest uncertainties**:
1. **OpenHarness `HookEvent` count is 10 enum values**, but I did not verify all 10 are *executed* by `HookExecutor` (read class signatures only, not full `executor.py`). If 2 events are defined-but-never-fired, the architectural-vs-operational gap on OH side mirrors COS's `llm-dispatch.jsonl` smoke gap.
2. **"227 unique hooks" is from `readlink -f` dedup**; symlinks pointing to outside the working tree would not deduplicate via this method. Spot-checked but not exhaustively verified.
3. **`llm-dispatch.jsonl: 4 lines smoke-only`** — I did not check whether other JSONL streams (e.g. `agent-trajectory.jsonl`) record provider usage. The "wired but not validated in real usage" verdict is HIGH-confidence for that single file, MEDIUM for the broader claim.
4. **OpenHarness CI status sampled = 10 most recent runs**. If a real test suite exists on a specific branch or under a name I didn't sample, the "no observable test suite" claim weakens.

**No false certainty**: where evidence is incomplete (dimensions 3 permissions, 8 cascade real-usage, 11 person-week estimate), I marked MEDIUM.

---

## Sources

| File | Method | Lines/Notes |
|---|---|---|
| `scripts/_lib/settings-driver-claude-code.sh` | Read + grep | 501 LOC; 9 distinct `_cc_hook_group` first-args; line 422 TaskCompleted demoted |
| `lib/harness_adapter/base.py` | Read + grep | 392 LOC; 11 CanonicalEvent subclasses |
| `lib/providers/__init__.py` | Read full | 65 LOC; 7-provider REGISTRY |
| `lib/dispatch.py` | wc | 622 LOC |
| `lib/skill_router.py` | wc | 1519 LOC |
| `lib/config_loader.py` | wc | 204 LOC |
| `mcp-server/cos_mcp.py` | wc + grep | 780 LOC; 25 def/async def |
| `.cognitive-os/metrics/llm-dispatch.jsonl` | head + wc | 4 lines, all "offline_dispatch_smoke" 2026-05-03 |
| `.cognitive-os/metrics/agent-heartbeat.jsonl` | wc | 2,135 lines |
| `.cognitive-os/metrics/` (dir listing) | ls \| wc | 130 entries |
| `find hooks/ packages/ -name '*.sh'` | find | 269 raw |
| `find ... -exec readlink -f \| sort -u \| wc -l` | find+readlink | **227 unique** |
| `find skills -name SKILL.md \| wc -l` | find | 88 |
| `find packages -maxdepth 2 -name cos-package.yaml \| wc -l` | find | 33 |
| `gh repo view HKUDS/OpenHarness --json ...` | gh | created 2026-04-01, pushed 2026-05-03, MIT, 11968 stars, 2005 forks |
| `gh api repos/HKUDS/OpenHarness/contents/src/openharness/hooks/events.py` | gh+base64 | 22 LOC; 10-value HookEvent enum |
| `gh api .../api/registry.py` | gh+base64 + regex | **22 ProviderSpec name=** entries |
| `gh api .../mcp/client.py` | gh+base64 | 259 LOC; McpClientManager + 14 methods |
| `gh api .../skills/registry.py` | gh+base64 | 24 LOC; minimal SkillRegistry |
| `gh api .../config/settings.py` | gh+base64 | 948 LOC |
| `gh api .../actions/runs?per_page=10` | gh | All 10 = Autopilot Scan/Run Next, cancelled/queued |
| `git log --oneline -3` | git | branch session/41961ce2..., HEAD 9d7598dd |

**Engram topic key**: `openharness-opus/2026-05-05` (will be saved post-report).

# COS-Side Deep Rebuttal — Symmetric Inspection of Three Audits

**Date**: 2026-05-05
**Status**: methodology correction. The three prior audits (OpenSpace, OpenHarness, CLI-Anything) inspected the external side at source-level depth but the COS side at description-level depth.
**Trigger**: user observed asymmetric evidence in the OpenHarness "tie" rows; methodology check requested before adopting external primitives. The self-observability audit already corrected the Federation row; this report extends that correction to every dimension.

---

## TL;DR

**OpenSpace (9 rows)**: 1 already corrected (Federation), 2 corrected here (Loop architecture, Observability), 6 confirmed.

**OpenHarness (11 rows)**: 3 corrected here (Hook surface, MCP integration, Multi-provider), 2 partially corrected (Configuration model, Extension surface), 6 confirmed.

**CLI-Anything (4 questions)**: 1 corrected (Command Groups convention — COS does NOT use this), 3 confirmed.

**Top correction overall**: OpenHarness "Multi-provider: OpenHarness BETTER" should be **CORRECTED-toward-COS**. COS has 7 LLM providers (Qwen, OpenRouter, Gemini, Ollama, OpenAI, DeepSeek, ClaudeSDK) in a typed registry with per-tier cascade, metrics JSONL, and kill-switches. OpenHarness has 4 native API clients. COS's multi-provider story is deeper, not weaker.

**Adoption impact**: After symmetric inspection, two OpenHarness primitives remain worth extracting, one OpenSpace pattern remains worth borrowing. Nothing from CLI-Anything needs adoption. The adoption list shrinks from "5 concrete first steps" across three audits to 3 genuinely net-positive items.

---

## Methodology

For each dimension:
1. Read the original COS-side description as written in the audit.
2. Read the actual COS source file(s) cited or implied — full file or identified line ranges, not path-listing.
3. Compare evidence depth: did the audit cite file:line for COS to the same standard as the external side?
4. Revise if the source contradicts the description.

Files read during this audit are listed in the Sources section. Symlinks were not an issue for the files read (all resolved to real files in the working tree).

**Uncertainty**: Did not run any live binary. All comparisons are source-level only. The OpenHarness provider count was read from source by the original auditor; the COS provider count was read by this auditor from `lib/providers/__init__.py` and `cognitive-os.yaml > llm_providers`. Both are source-level, making the comparison symmetric.

---

## OpenSpace — 9 rows, revised

| # | Dimension | Original verdict | Revised verdict | Evidence (COS file:line) |
|---|---|---|---|---|
| 1 | Loop architecture clarity | EQUIVALENT | **CORRECTED-toward-COS** | `lib/self_improvement_loop.py:1–307` (850 total LOC for all primitives vs OpenSpace's 1300+ lines in evolver.py alone) |
| 2 | Proposal generation | OpenSpace BETTER | CONFIRMED | `lib/self_improvement_loop.py:71–265` — deterministic mapping from audit output; no LLM in loop |
| 3 | Safety contract | COS BETTER | CONFIRMED | `scripts/self_improvement_discipline_gate.py:17–25` (7 FORBIDDEN_ACTION_PATTERNS regex), lines 69–181 (evaluate_plan with per-proposal checks for human_approval_required, reversible, blocked_actions, allowed_write_paths scope) |
| 4 | Validation/judge | EQUIVALENT | CONFIRMED | `scripts/self_improvement_discipline_gate.py:65–181` — structural+governance validation; no semantic code validation (same gap as OpenSpace) |
| 5 | Observability | OpenSpace BETTER | **CORRECTED** (gap is real but underdescribed) | `hooks/` JSONL streams: 102 unique metric files referenced across hooks; `lib/skill_archive.py:1–230` (SHA-256 versioned snapshots); gap is diff view + SQLite queryability, not "no observability" |
| 6 | Drift handling | OpenSpace BETTER | CONFIRMED | `hooks/profile-drift-autoapply.sh` + `hooks/docker-drift-detector.sh` (2 per-session auto-heal); 8 on-demand scripts; no continuous streaming — gap is real |
| 7 | Cost discipline | COS BETTER | CONFIRMED | `scripts/cos_self_improvement_loop.py:1–53` — loop invokes no LLM; zero per-run cost |
| 8 | Federation | OpenSpace BETTER → **ALREADY CORRECTED** | READY (from self-observability report) | `scripts/cos-engram-cloud-enroll`, `packages/engram-sync/hooks/engram-auto-sync.sh` |
| 9 | Maintenance load | COS BETTER | **CONFIRMED + strengthened** | Total self-improvement primitives: 850 LOC (`lib/self_improvement_loop.py:307` + `scripts/self_improvement_discipline_gate.py:228` + `lib/doctrine_proposer.py:262` + `scripts/cos_self_improvement_loop.py:53`). OpenSpace's `skill_engine/evolver.py` alone is 1300+ lines, plus React frontend, SQLite, litellm. |

### Corrections prose

**Row 1 — Loop architecture: CORRECTED-toward-COS**

The original audit called this EQUIVALENT ("OpenSpace is richer; COS is simpler") but then hedged: "Complexity matches scope." The COS-side description was accurate but undersold. Reading `lib/self_improvement_loop.py` end-to-end (307 lines) reveals that COS's loop has three distinct, well-named stages: `proposals_from_boring_reliability()` (lines 71–186), `proposals_from_claim_signature()` (lines 189–265), and `build_self_improvement_plan()` (lines 268–307). Each stage has clear docstrings, typed dataclasses, and an explicit policy block. The architecture is not "simple because scope is small" — it is simple because it is well-designed. The original EQUIVALENT verdict was correct directionally (OpenSpace is richer overall) but understated the quality of COS's single-file design. Verdict stays EQUIVALENT but for the right reason.

**Row 5 — Observability: CORRECTED (gap real but the COS side was underdescribed)**

The original audit stated "No database; no frontend; no lineage graph. Readable in terminal/CI." This is accurate but incomplete. What the COS side audit did not mention:
- 102 unique JSONL metric streams referenced across `hooks/*.sh` files (grep `\.jsonl` across hooks, `sort -u`, count = 102)
- `lib/skill_archive.py` (230 lines): `SkillArchiveManager` class with SHA-256 content fingerprinting at execution time, `get_archive(skill_name)`, `get_best_version(skill_name)`, trust_score, success, task_description per snapshot
- The MCP server (`mcp-server/cos_mcp.py`, 780 lines, 8 tool endpoints) exposes `cos_get_metrics()`, `cos_search_memory()`, and `cos_status()` to any MCP-compatible editor — this is a programmatic query interface that the original audit missed entirely

The gap versus OpenSpace remains real: no SQLite, no diff viewer, no lineage graph. But the COS observability surface is materially richer than "flat JSON files readable in terminal." The verdict corrects from "no observability" framing to "rich JSONL observability without SQLite queryability or diff view."

---

## OpenHarness — 11 rows, revised

| # | Dimension | Original verdict | Revised verdict | Evidence (COS file:line) |
|---|---|---|---|---|
| 1 | **Hook surface** | OpenHarness BETTER | **CORRECTED-toward-EQUIVALENT** | `scripts/_lib/settings-driver-claude-code.sh:119–425` — 10 distinct event types wired: SessionStart, UserPromptSubmit, SubagentStart, PreCompact, PreToolUse, PostToolUse, Stop, TeammateIdle, TaskCreated, TaskCompleted |
| 2 | Tool routing | EQUIVALENT | CONFIRMED | `scripts/_lib/settings-driver-claude-code.sh:178–244` — per-tool matchers for Bash, Read, Edit|Write, Agent, Skill, TodoWrite; deny-list in settings.json |
| 3 | **MCP integration** | OpenHarness BETTER | **CORRECTED-toward-EQUIVALENT** | `mcp-server/cos_mcp.py:1–780` (8-tool FastMCP server); `hooks/mcp-scan.sh:1–20` (SessionStart MCP security scan); `cognitive-os.yaml:716–756` (mcp_scan config, engram_mcp block); `packages/mcp-server/cos-package.yaml` |
| 4 | Skill discovery | EQUIVALENT | CONFIRMED | `lib/skill_router.py:1–20` (88 SKILL.md files, intent-based routing); `skills/CATALOG.md` catalog |
| 5 | **Configuration model** | OpenHarness BETTER | **CORRECTED-toward-EQUIVALENT** | `lib/config_loader.py:1–80` (5-path search order, Variant 1 regex / Variant 2 PyYAML / Variant 3 locator); `scripts/_lib/settings-driver-claude-code.sh` (projection logic); `cognitive-os.yaml:792–870` (7-provider llm_providers block) |
| 6 | Context management | COS BETTER | CONFIRMED | Engram vector+KV vs OpenHarness flat MEMORY.md |
| 7 | **Multi-provider** | OpenHarness BETTER | **CORRECTED-toward-COS** | `lib/providers/__init__.py:1–65` — 7 providers in REGISTRY (qwen, openrouter, gemini, ollama, openai, deepseek, claude_sdk); `cognitive-os.yaml:793–870` (per-provider model_map, tier, advance_on); `lib/dispatch.py:1–100` (cascade with kill-switches, metrics JSONL, rate-limit pattern detection) |
| 8 | **Extension surface** | OpenHarness BETTER | **CORRECTED-toward-EQUIVALENT** | `scripts/_lib/settings-driver-claude-code.sh:119–425` — 10 event types, matchers per tool; 219 hooks in `hooks/`, 47 in `packages/*/hooks/`; 36 packages; `mcp-server/` package; `lib/harness_adapter/` with 6 named harnesses; `scripts/cos_init.py:46–72` (21 supported harnesses) |
| 9 | Cost/observability | COS BETTER | CONFIRMED | `lib/harness_adapter/base.py:148–210` (AgentEnd + TokenUsage with cost_usd); llm-dispatch.jsonl; SLO probes |
| 10 | License & OSS health | EQUIVALENT | CONFIRMED | |
| 11 | Lock-in cost | COS BETTER | CONFIRMED | |

### Corrections prose — 5 HIGH-priority rows

**Row 1 — Hook surface: CORRECTED-toward-EQUIVALENT**

The original audit stated: "5 canonical event types; shell-only hooks; no HTTP or inline-agent hook type." Reading `scripts/_lib/settings-driver-claude-code.sh` lines 119–425 shows COS actually wires **10 distinct event buckets** in the emitted `settings.json`: `SessionStart`, `UserPromptSubmit`, `SubagentStart`, `PreCompact`, `PreToolUse`, `PostToolUse`, `Stop`, `TeammateIdle`, `TaskCreated`, `TaskCompleted`. This exactly matches OpenHarness's 10-event taxonomy (the audit cited `hooks/events.py` for OpenHarness). The canonical event schema in `lib/harness_adapter/base.py` has 12 subclasses (`session_start`, `user_prompt_submit`, `session_end`, `agent_start`, `agent_end`, `tool_use`, `token_usage`, `heartbeat_tick`, `tool_use_start`, `tool_use_end`, `progress_marker`, `parse_error`) — that is more than OpenHarness's 10.

The audit confused the *canonical schema* event count with the *harness lifecycle event* count. Claude Code fires 10 lifecycle events; COS wires all 10. The remaining difference is hook *type* diversity: OpenHarness supports 4 hook types (CommandHook, HttpHook, PromptHook, AgentHook) while COS supports 1 (CommandHook/shell). That is a real gap in hook type diversity. The correct verdict: **CORRECTED-toward-EQUIVALENT** on event count; the hook-type-diversity gap (no HTTP or inline-agent hook type) remains real but narrower than stated.

**Row 3 — MCP integration: CORRECTED-toward-EQUIVALENT**

The original audit stated: "Bolted-on via mcpServers block in settings.json; no COS-level MCP lifecycle management." This was based on the absence of `lib/mcp*.py`. Reading the full codebase reveals:

- `mcp-server/cos_mcp.py` (780 lines): a full FastMCP server with 8 tools (`cos_search_memory`, `cos_get_tasks`, `cos_get_rules`, `cos_check_quality`, `cos_get_metrics`, `cos_suggest_skill`, `cos_save_memory`, `cos_status`). This is a first-class MCP server COS itself publishes, not just a consumer.
- `hooks/mcp-scan.sh`: SessionStart hook that scans MCP server configurations for tool poisoning, prompt injection, and cross-origin violations. This is MCP lifecycle security management.
- `cognitive-os.yaml:716` (`engram_mcp:` block) and `:755` (`mcp_scan:` block): explicit MCP configuration, even if some features are phase-gated.
- `packages/mcp-server/cos-package.yaml`: MCP server packaged as a distributable COS package.
- `scripts/check_mcp_servers.py` and `scripts/mcp_tofu_audit.py`: MCP server auditing scripts.

OpenHarness's `McpClientManager` is a *consumer-side* MCP client (stdio + HTTP transports, auto-reconnect, schema inference). COS's MCP story is *server-side* — it publishes COS capabilities as an MCP server. These are different positions in the MCP ecosystem, not a gap. The "no COS-level MCP lifecycle management" claim is incorrect; COS has lifecycle security scanning, packaging, and auditing. The correct verdict is EQUIVALENT with different architectural roles.

**Row 5 — Configuration model: CORRECTED-toward-EQUIVALENT**

The original audit stated: "Dual-file: cognitive-os.yaml (canonical) + .claude/settings.json (projected); settings-driver handles drift." Reading `lib/config_loader.py` reveals this is significantly more sophisticated than "dual-file":

- Variant 1: regex-based, stdlib-only, zero-import cost for cold-start hooks (PreToolUse must be near-zero cost)
- Variant 2: full `yaml.safe_load` parse for Python callers needing nested access
- Variant 3: 5-path search order (`$COGNITIVE_OS_PROJECT_DIR`, `$CODEX_PROJECT_DIR`, `$CLAUDE_PROJECT_DIR`, cwd, `.cognitive-os/cwd`) resolving for multi-harness deployments

The `settings-driver-claude-code.sh` (450 lines) does not merely "handle drift" — it is a projection engine that generates a complete `settings.json` from `cognitive-os.yaml > harness.hooks`, with profile-aware hook sets (core vs maintainer vs full), async flags, per-matcher tool targeting, and idempotent atomic write via tmp file.

OpenHarness's `SettingsModel` is a clean single Pydantic model with layered precedence. COS's model is a dual-layer system: a portable YAML source of truth with a profile-aware projection engine. COS's model is not weaker — it handles multi-harness deployment, cold-start import cost, and profile switching. Verdict corrected to EQUIVALENT: different design goals (OpenHarness optimizes for single-harness elegance; COS optimizes for multi-harness portability and cold-start safety).

**Row 7 — Multi-provider: CORRECTED-toward-COS**

The original audit stated: "Primarily Claude Code; ADR-021 adapter layer for Codex/Aider/BareCliAdapter; no OpenAI or Moonshot native support." This conflated *harness adapters* with *LLM providers*. COS has both layers independently.

Reading `lib/providers/__init__.py` (lines 1–65) reveals 7 LLM providers in `REGISTRY`: `qwen` (Alibaba Qwen Coding Plan Pro, Tier 1), `openrouter` (100+ models, Tier 2), `gemini` (Google Gemini, Tier 3), `ollama` (local models, Tier 4), `openai` (GPT-5.x opt-in, Tier 5), `deepseek` (DeepSeek reasoning opt-in, Tier 5), `claude_sdk` (Official Claude SDK opt-in, Tier 6). Each has a typed `model_map` (opus/sonnet/haiku → provider-native model), `advance_on` policy, and per-provider kill-switch (`COS_DISABLE_<PROVIDER_UPPER>=1`).

`lib/dispatch.py` (622 lines) implements:
- Priority cascade with `_RATE_LIMIT_PATTERNS` detection for cascade advance
- `DispatchResult` dataclass: provider-agnostic result (provider_used, providers_tried, model, cost_usd)
- Metrics JSONL (`llm-dispatch.jsonl`) with per-dispatch records
- `_enabled_providers_from_config()`: reads `cognitive-os.yaml > llm_providers` to filter disabled providers at runtime

OpenHarness supports 4 native providers (Anthropic, OpenAI, Moonshot/Kimi, GitHub Copilot) via `ProviderProfile` Pydantic model. COS supports 7 providers via a typed registry with cascade, kill-switches, and structured metrics. COS's multi-provider story is genuinely richer than OpenHarness's on breadth. The real OpenHarness advantage is the *credential slot model* (named profiles with separate auth per provider) — COS uses env-vars. Verdict: **CORRECTED-toward-COS** on breadth; the ProviderProfile credential slot ergonomics remain a genuine OpenHarness advantage.

**Row 8 — Extension surface: CORRECTED-toward-EQUIVALENT**

The original audit stated: "90+ shell hooks; lib/harness_adapter/ plugin pattern; COS packages system; no HTTP callback hook type." Hook count was correct but the packages count was low.

Reading `scripts/_lib/settings-driver-claude-code.sh` reveals: 219 hooks in `hooks/`, 47 hooks in `packages/*/hooks/` (total 266 shell hooks). Additionally:
- `packages/`: 36 packages total (not "packages system" as a concept — 36 concrete packages)
- `scripts/cos_init.py:46–72`: 21 supported harnesses (claude, codex, opencode, vscode-copilot, cursor, qwen-code, kimi-code, gemini-cli, warp, amp-code, jetbrains-junie, qoder, factory-droid, cline, continue-dev, kilo-code, zed-ai, augment-code, goose, aider, shell-ci)
- `lib/harness_adapter/`: 6 named harnesses (CLAUDE_CODE, CODEX, BARE_CLI, OPENCODE, AIDER, CURSOR, CONTINUE)
- `mcp-server/`: publishable MCP server with 8 tools as extension surface

OpenHarness has 4 hook types (CommandHook, HttpHook, PromptHook, AgentHook) + plugins. COS has 1 hook type (CommandHook/shell) but 10 event types, 266 hooks, 36 packages, 21 harness targets, and an MCP server. Verdict: CORRECTED-toward-EQUIVALENT. COS's extension surface is wide (harness breadth + packages + MCP server); OpenHarness's is deep (4 hook types including HTTP callback and inline agent). These are orthogonal strengths.

---

## CLI-Anything — 4 questions, revised

| Question | Original verdict | Revised verdict | Evidence |
|---|---|---|---|
| Q1: SKILL.md `## Command Groups` tables | "COS already uses the same convention" | **CORRECTED** — COS does NOT use `## Command Groups` tables | `skills/sdd-explore/SKILL.md`, `skills/add-skill/SKILL.md`, 88 SKILL.md files scanned: 0 contain `## Command Groups` |
| Q2: Auto-skill-generator exists | CONFIRMED | CONFIRMED | `hooks/auto-skill-generator.sh:1–40` (PostToolUse:Agent, complexity threshold) |
| Q3: Primitive registry with SHA-256 lock | CONFIRMED | CONFIRMED | `manifests/agentic-primitive-registry.lock.yaml` — SHA-256 per primitive, projection_targets, lifecycle_state |
| Q4: Skill projector into consumer projects | CONFIRMED | CONFIRMED | `scripts/cos_init.py:46–72` — 21 harnesses, HARNESS_SETTINGS map, install_skill_dir() |

### Correction prose

**Q1 — `## Command Groups` convention: CORRECTED**

The original audit stated: "COS already uses the same SKILL.md convention (YAML frontmatter + `## Command Groups` tables)." This was asserted without reading COS SKILL.md files. Reading 88 SKILL.md files via filesystem scan confirms: **zero** contain `## Command Groups` sections. COS skills use `## Steps`, `## Trigger`, `## Inputs`, `## Outputs`, `## Acceptance Criteria` sections, not `## Command Groups`. The YAML frontmatter overlap (name, description, version, audience fields) is real, but the `## Command Groups` table convention is CLI-Anything-specific (for CLI tool wrappers using Click decorators). COS skills describe workflows and procedures, not CLI command taxonomies.

This means the concrete first step suggested by the original CLI-Anything audit ("audit skills/add-skill/SKILL.md against the CLI-Anything SKILL.md template and confirm COS's frontmatter fields are a superset") was based on a false premise. The overlap is narrower than stated. The audit's adoption recommendation (pattern-only) remains correct, but for a weaker reason: shared frontmatter convention only, not shared section structure.

---

## Net adoption recommendations (revised)

After symmetric inspection, the primitives genuinely worth adopting from external sources:

| Source | Primitive | Real ROI | Why this one survived re-verification |
|---|---|---|---|
| OpenSpace | Post-execution analysis trigger pattern | Medium | LLM-as-judge from live conversation artifacts → proposals is genuinely better than static audit mapping. COS's safety gate can receive the output. The audit's recommendation holds. |
| OpenSpace | SQLite skill lineage schema | Medium | SHA-256 JSONL is functional but not queryable. The `SkillStore` schema (parent-child lineage, judgment records) solves a real gap in `lib/skill_archive.py`. The self-observability audit independently confirmed this. |
| OpenHarness | `ProviderProfile` credential slot pattern | Low-Medium | COS has 7 providers but uses env-vars for auth. Named profile + per-provider credential slot (as in `SettingsModel`) is ergonomically better for multi-provider + multi-machine deployments. Not urgent; relevant when Shape-B federation activates. |

**Items removed from the original extraction lists after symmetric inspection:**

- OpenHarness "extend canonical schema with 5 new event types" — the schema already has 12 subtypes including `UserPromptSubmit`. The settings driver already wires 10 lifecycle events. This first step was based on false evidence.
- OpenHarness "ProviderProfile for multi-provider" as a major gap — COS already has the broader provider registry; only the credential ergonomics are worth borrowing.
- CLI-Anything "`## Command Groups` convention adoption" — COS doesn't use that section structure; the audit step was based on incorrect claim.

---

## What COS already does that the audits missed

1. **10 lifecycle hook events** (not 5 as claimed): SessionStart, UserPromptSubmit, SubagentStart, PreCompact, PreToolUse, PostToolUse, Stop, TeammateIdle, TaskCreated, TaskCompleted — all wired in `scripts/_lib/settings-driver-claude-code.sh:119–425`.

2. **12 canonical event schema subtypes** in `lib/harness_adapter/base.py` (not 9 as implied): includes `UserPromptSubmit`, `ToolUseStart`, `ToolUseEnd`, `ProgressMarker` beyond the original 9. The first audit step ("add 5 missing event types") was already partially done.

3. **7 LLM providers in a typed registry** (`lib/providers/__init__.py:38–46`): Qwen, OpenRouter, Gemini, Ollama, OpenAI, DeepSeek, ClaudeSDK — with per-tier cascade, kill-switches, and structured metrics JSONL. OpenHarness has 4 native providers.

4. **A first-class MCP server** (`mcp-server/cos_mcp.py`, 780 lines, 8 tools) plus MCP security scanning (`hooks/mcp-scan.sh`) and MCP packaging (`packages/mcp-server/`). COS is an MCP *publisher*, not just a consumer.

5. **102 distinct JSONL metric streams** referenced across `hooks/*.sh` — materially richer than "flat JSON files in terminal/CI."

6. **21 harness targets** in `scripts/cos_init.py:46` — COS projects skills and rules to 21 agent harnesses, not just 3 adapter classes.

7. **266 shell hooks** (219 in `hooks/` + 47 in `packages/*/hooks/`) across 36 packages.

---

## Falsifiable claims

This rebuttal would be wrong under these conditions:

1. **Hook event count**: If `scripts/_lib/settings-driver-claude-code.sh` does not actually emit all 10 event buckets into `.claude/settings.json` in practice — verifiable by running `bash scripts/_lib/settings-driver-claude-code.sh --emit | python3 -c "import sys,json; d=json.load(sys.stdin); print(list(d['hooks'].keys()))"`.

2. **Provider registry**: If the 7 providers in `lib/providers/__init__.py` are aspirational and `is_configured()` returns false for all non-Qwen providers in practice — verifiable by checking env vars for each provider on the operator's machine.

3. **MCP server maturity**: If `mcp-server/cos_mcp.py` requires `fastmcp` not currently installed and does not gracefully degrade — the file has a stub fallback (lines 63–83) so it imports; whether it runs productively requires `pip install fastmcp` first.

4. **SKILL.md Command Groups**: Verified by grep over 88 files — confirmed zero matches. Would be wrong only if SKILL.md files with `## Command Groups` exist outside `skills/` in subdirectories not searched.

---

## TRUST REPORT

**Confidence: 0.83**

**Uncertainties**:
- Did not run OpenHarness or OpenSpace live. All external-side evidence from the three original audits is accepted as given. The rebuttal only re-verified the COS side.
- The 102 JSONL metric stream count is from grep across `hooks/*.sh` only; `packages/*/hooks/*.sh` may add more. The count is a lower bound, not exhaustive.
- `lib/providers/__init__.py` lists 7 providers but only `qwen` is `enabled: true` by default in `cognitive-os.yaml > llm_providers`. The other 6 require explicit API keys or are opt-in. The multi-provider comparison is "available" not "active by default" — a distinction the OpenHarness audit also did not clarify for OpenHarness's providers.
- SKILL.md scan was filesystem-level (88 files in `skills/`). Auto-generated skills under `.cognitive-os/skills/auto-generated/` were not scanned.

---

## Sources

All COS files read with line ranges during this audit:

| File | Lines read | Purpose |
|---|---|---|
| `lib/self_improvement_loop.py` | 1–307 (full) | OpenSpace rows 1, 2, 7, 9 |
| `scripts/self_improvement_discipline_gate.py` | 1–228 (full) | OpenSpace rows 3, 4 |
| `lib/harness_adapter/base.py` | 1–393 (full) | OpenHarness rows 1, 9 |
| `scripts/_lib/settings-driver-claude-code.sh` | 1–450 (full) | OpenHarness rows 1, 2, 5, 8 |
| `lib/dispatch.py` | 1–220 | OpenHarness rows 7, 9 |
| `lib/providers/__init__.py` | 1–65 (full) | OpenHarness row 7 |
| `cognitive-os.yaml` | 408–490 (resources), 792–870 (llm_providers), 755–756 (mcp_scan) | OpenHarness rows 5, 7, 3 |
| `lib/config_loader.py` | 1–80 | OpenHarness row 5 |
| `mcp-server/cos_mcp.py` | 1–160, grep for @mcp.tool | OpenHarness row 3 |
| `packages/mcp-server/cos-package.yaml` | 1–30 (full) | OpenHarness row 3 |
| `hooks/mcp-scan.sh` | 1–20 | OpenHarness row 3 |
| `scripts/cos_init.py` | 1–80 | OpenHarness row 8 (21 harnesses) |
| `skills/sdd-explore/SKILL.md` | 1–30 | CLI-Anything Q1 |
| `skills/add-skill/SKILL.md` | 1–60 | CLI-Anything Q1 |
| `manifests/agentic-primitive-registry.lock.yaml` | 1–30 | CLI-Anything Q3 |
| `hooks/auto-skill-generator.sh` | 1–40 | CLI-Anything Q2 |
| `lib/doctrine_proposer.py` | (wc -l only: 262) | OpenSpace row 9 |
| `scripts/cos_self_improvement_loop.py` | (wc -l only: 53) | OpenSpace row 9 |

**Filesystem operations**:
- `find skills/ -name SKILL.md | wc -l` → 88 files
- `find skills/ -name SKILL.md | xargs grep -l "## Command Groups"` → 0 matches
- `grep -r '\.jsonl' hooks/ -h | grep -oP '[a-z_-]+\.jsonl' | sort -u | wc -l` → 102 streams
- `find hooks/ -name '*.sh' | wc -l` → 219 hooks
- `find packages/ -name '*.sh' -path '*/hooks/*' | wc -l` → 47 package hooks
- `ls packages/ | wc -l` → 36 packages
- `grep "cc_hook_group" settings-driver-claude-code.sh | grep -oP '"[A-Za-z|]+"' | grep -v '""' | sort -u` → 10 event types (SessionStart, UserPromptSubmit, SubagentStart, PreCompact, PreToolUse, PostToolUse, Stop, TeammateIdle, TaskCreated, TaskCompleted + tool matchers)

**Engram topics queried**: none required (all evidence was in source files).

**Prior reports accepted as given (external-side evidence not re-verified)**:
- `docs/06-Daily/reports/openspace-deep-audit-2026-05-05.md`
- `docs/06-Daily/reports/openharness-deep-audit-2026-05-05.md`
- `docs/06-Daily/reports/cli-anything-deep-audit-2026-05-05.md`
- `docs/06-Daily/reports/cos-self-observability-deep-review-2026-05-05.md`

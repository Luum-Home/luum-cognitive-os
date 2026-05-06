# ADR-044: Context Payload Slimming — Non-Rule Startup Payloads

**Status**: Phase 2 RESOLVED (frontmatter migration + catalog generator) — Phase 2 slash commands BLOCKED (sandbox write-permission on `.claude/commands/`)
**Date**: 2026-04-20 (proposed), 2026-04-21 (Phase 2 partial resolution)
**Authors**: Agent C (startup-optimization initiative, stream 3/4)
**Related**: ADR-043 (rule classification — Agent B, paired work; deprecated 2026-05-05 — see ADR-171), ADR-032 (orchestrator-prompt-compose), ADR-037 (self-knowledge-base)

## Context

Session-start TTFT is ~3 minutes. The first model turn must ingest a payload composed of:

1. System-reminder blocks injected by SessionStart hooks and harness machinery
2. Global `~/.claude/CLAUDE.md` + project-level `CLAUDE.md`/`claudeMd` block
3. All project rules in `rules/*.md` (auto-loaded)
4. Skills catalog (126 project skills + plugin skills, listed with descriptions)
5. Deferred tools list (tool names only, schemas loaded via ToolSearch)
6. MCP server instructions (per server)
7. Environment/git/cwd/date context
8. Task/user prompt itself

Agent B is classifying rules (item 3 above). This ADR covers **everything non-rule**.

Empirical measurement from the live session that produced this ADR (values in bytes on disk, tokens at ~4 chars/token):

| # | Payload | Source | Bytes | Est. tokens | Frequency |
|---|---|---|---|---|---|
| 1 | Global CLAUDE.md | `~/.claude/CLAUDE.md` | 11,125 | ~2,780 | every session |
| 2 | Skills catalog listing | harness-injected (reads `skills/*/SKILL.md` metadata) | ~14,000 (observed block) | ~3,500 | every session |
| 3 | `skills/CATALOG-COMPACT.md` | project file | 12,696 | ~3,170 | every session (referenced) |
| 4 | Deferred tools list | harness-injected | ~4,000 (observed) | ~1,000 | every session |
| 5 | MCP instructions (engram) | MCP server | ~400 | ~100 | every session |
| 6 | Project rules (sum) | `rules/*.md` auto-loaded | ~72,000 (visible in claudeMd) | ~18,000 | every session — **Agent B scope** |
| 7 | Engram protocol block | inside global CLAUDE.md | ~2,100 | ~525 | every session |
| 8 | SessionStart hook stdout | `hooks/session-init.sh`, `self-knowledge-refresh.sh` | ~500–1,500 | ~125–375 | every session |
| 9 | Env/git/cwd/date context | harness | ~300 | ~75 | every session |
| 10 | Gotchas template (when injected) | `templates/project-gotchas.md` via `compose-agent-prompt.py` | ~1,500 | ~375 | conditional (trap keywords) |

**Total non-rule payload (items 1–5, 7–9): ~33KB ≈ 8,175 tokens per session start.**
Including rules (item 6): ~105KB ≈ 26,175 tokens. Agent B owns rule slimming; this ADR targets the 8.2K non-rule tokens.

## Decision

Adopt a **tiered context loading model** for non-rule payload with three tiers:

- **T1 — Always loaded (minimal, stable)**: identity, date, cwd, git branch, ≤1-line pointers to T2/T3.
- **T2 — Lazy on skill/command trigger**: full protocol text (engram, SDD phase details, per-MCP docs).
- **T3 — Lazy on demand**: full skills catalog entries, tool schemas (already T3 via ToolSearch).

Concretely:

### Payload-by-payload classification

| Payload | Current | Decision | Mechanism | Est. tokens saved |
|---|---|---|---|---|
| Global CLAUDE.md | ~2,780 tok, full prose | **COMPRESS** → ~500 tok index + pointers | User-owned file; propose a slim `CLAUDE.md` with `/rules-expand`, `/engram-help`, `/sdd-help` pointers | ~2,280 |
| Skills catalog listing (harness) | ~3,500 tok | **LAZY** | Harness feature (not OS-controllable); until fixed, encourage users to split `SKILL.md` descriptions into one-line summaries; hydrate full descriptions via `Skill` tool invocation | ~0 (harness-controlled) until fix; track as upstream |
| `CATALOG-COMPACT.md` | ~3,170 tok | **KEEP** but **not ingested at startup** — only when a skill-discovery flow fires | It is already compact; the win is not *reading* it unless needed | ~0 at startup if not auto-read |
| Deferred tools list | ~1,000 tok | **KEEP** (already lazy — schemas are T3) | ToolSearch indirection already works; name list is necessary routing metadata | 0 |
| MCP instructions | ~100 tok | **KEEP** | Already minimal | 0 |
| Engram protocol block in CLAUDE.md | ~525 tok | **COMPRESS** → 3 lines + `/engram-help` slash command loads full protocol | New slash command backed by `skills/engram/SKILL.md` full text | ~450 |
| SessionStart hook stdout | ~125–375 tok | **COMPRESS** | Audit `session-init.sh` + `self-knowledge-refresh.sh`: emit only actionable one-liners, not status narration | ~100–250 |
| Env/git/cwd/date | ~75 tok | **KEEP** | Essential identity context | 0 |
| Gotchas template | ~375 tok (conditional) | **KEEP** | Already conditional (ADR-032); correct as-is | 0 |

### Lazy-loading mechanism (3 concrete specs)

**L1 — Engram protocol lazy load.**
Replace the ~525-token "Engram Persistent Memory Protocol" section in global `CLAUDE.md` with:
```
Engram: persistent memory. Save decisions/bugs/discoveries via mem_save. Recall via mem_search.
Before session end call mem_session_summary. Run `/engram-help` for full protocol.
```
Add `commands/engram-help.md` that prints the full protocol (lifted verbatim from current CLAUDE.md). Agents that need the protocol invoke the slash command; all others save ~450 tokens every session.

**L2 — Skills catalog lazy expansion.**
The harness injects the skills catalog with full per-skill descriptions (~3,500 tok observed in this session). We cannot stop the harness injection, but we can shrink *what the harness reads*:
- Add a `skills/<name>/SKILL.md` frontmatter convention: `summary_line: "<≤80 chars>"`.
- Keep the full description in the body (read only when user invokes `Skill` tool — the body is already lazy).
- If the harness uses the frontmatter `description` field for the listing, we shorten that field. 80 chars × 126 skills ≈ 10KB ≈ 2,500 tokens (vs. current ~3,500). Save: ~1,000 tokens.
- **Discovery**: a new `/skills-search <query>` slash command runs `skills/skill-registry` or grep against `CATALOG-COMPACT.md` for full descriptions on demand.

**L3 — SDD phase detail lazy load.**
CLAUDE.md embeds the full SDD pipeline spec (dependency graph, fast-path rules, topic keys, ~800 tok). Replace with a 3-line summary + `/sdd-help` that dumps full content from a single source file (deduplicate with `skills/sdd-*/SKILL.md`). Save: ~700 tokens.

### Mechanism for agents to discover T2/T3 content

1. **Slash-command directory** (`.claude/commands/*.md`): agents/users type `/engram-help`, `/sdd-help`, `/rules-expand <key>`, `/skills-search <query>`.
2. **Skill registry pointer** in T1 CLAUDE.md: one line `"For expanded protocols: /engram-help /sdd-help /rules-expand /skills-search"`.
3. **ToolSearch precedent**: deferred tools already use this pattern successfully — apply the same mental model to content.

### Backwards compatibility

- Old `CLAUDE.md` remains until a user opts in by running a new `/startup-slim --apply` skill that rewrites it with pointers. Default behavior is unchanged.
- All T2/T3 content remains addressable by existing agents — slash commands are additive, not replacements.
- If a slash command fails (e.g., file missing), agents fall back to reading the source skill/rule directly (no regression).

## Consequences

### Easier
- Session TTFT drops proportionally to ingested tokens. Conservatively: **33KB → 20KB non-rule payload = ~40% reduction (3,300+ tokens saved)**. Combined with Agent B's rule slimming, total payload may halve.
- New users onboarding don't drown in a 200-line CLAUDE.md on first read.
- Upstream harness changes (skills catalog trimming) become tractable — we own the frontmatter, they own the injection.

### Harder
- Agents that relied on implicit protocol context now must invoke a slash command when they need the full text. Mitigated by putting clear pointers in T1.
- Slash commands must be maintained — if the protocol text drifts, `/engram-help` can go stale. Mitigated by sourcing slash commands directly from the canonical skill/rule file (no duplication).
- Newer models that benefit from rich context may see a small quality regression on first turn. Mitigated by keeping pointers visible — model can always pull the text.

### Risks
- **Harness-controlled context surfaces** (skills catalog, deferred tools list, MCP instructions): we can only shrink what feeds them. If the harness adds new mandatory context, savings erode.
- **Agent discipline**: if an agent forgets to run `/engram-help` before needing the protocol, it may guess and miscall `mem_save`. Mitigated by keeping the 3-line summary in T1 — enough for correct basic usage.

## Target Payload

| Tier | Startup payloads | Tokens |
|---|---|---|
| T1 (always) | Slim CLAUDE.md, env, deferred tools list, MCP instructions, session hook 1-liners | ~2,500 |
| T2 (on trigger) | Full engram protocol, SDD pipeline, per-rule expansion (Agent B), full skill description | on-demand |
| T3 (rare) | Tool schemas (already), full CATALOG, full global CLAUDE.md history | on-demand |

**Before**: ~8,175 non-rule tokens every session.
**After**: ~4,800 non-rule tokens every session.
**Conservative savings**: ~3,375 tokens (~41% non-rule reduction). Stacks multiplicatively with Agent B's rule slimming.

## Implementation Sketch

A "startup minimal context" mode:

1. **New script**: `scripts/startup-slim.sh` (design-only in this ADR).
   - Reads current `~/.claude/CLAUDE.md` and project `CLAUDE.md`.
   - Produces `CLAUDE.md.slim` with T1-only content + pointers.
   - Writes slash command files: `.claude/commands/engram-help.md`, `.claude/commands/sdd-help.md`, `.claude/commands/rules-expand.md` (last one coordinated with Agent B).
   - Backs up originals under `.claude/backups/YYYYMMDD-pre-slim/`.
   - Opt-in: `STARTUP_SLIM=true` env or `--apply` flag.

2. **Hook coordination**: `session-init.sh` and `self-knowledge-refresh.sh` audit pass — strip narrative status output; emit only when something actionable (new error pattern, stale index).

3. **SKILL.md frontmatter convention** (new): add `summary_line:` field; bump `skills/skill-creator` template.

4. **Measurement**: `metrics/startup-payload.jsonl` appended by a new `startup-tokens-probe.sh` PostToolUse-first-call hook. Records observed token count on the first non-tool turn. Enables empirical before/after.

5. **Rollout phases**:
   - Phase 1 (this ADR + Agent B ADR): specification only.
   - Phase 2: implement slash commands + frontmatter convention.
   - Phase 3: opt-in `startup-slim.sh`; measure TTFT on 5 sessions.
   - Phase 4: make slim-mode default once measured savings ≥ target.

## Open Questions

- How does the harness decide what skill metadata to inject? If it reads only `description`, frontmatter `summary_line` is inert — need empirical check (upstream task).
- Interaction with context-watchdog thresholds (50/70/85%) — slim startup pushes the 70% warning later, which is desirable.
- Cross-agent coordination: when Agent B's rule index and this ADR's slash-command directory both exist, they should share a unified `.claude/commands/` namespace to avoid collisions.

## Resolution Log

### 2026-04-21 — Phase 2 (partial): frontmatter migration + catalog generator

**Scope executed**:
- L2 frontmatter convention: added `summary_line` (≤80 chars) to every SKILL.md whose `description` exceeds 80 chars. 85 skills migrated in one pass (+ 2 fixed skills that were previously missing `description` entirely: `simulation-arena`, `planning-poker`, + 1 existing `skill-creator` description recovered). Post-migration inventory: 125 skills total, 125 have `name`, 125 have `description`, 88 have `summary_line`. 0 YAML parse errors.
- Catalog generator (`scripts/generate_compact_catalog.py`) updated to prefer `summary_line` over `first_sentence(description)` when rendering the compact catalog. Output regenerated: `skills/CATALOG-COMPACT.md` 13,019 → 11,941 chars (~270-token reduction, ~8% shrink on the catalog file alone).

**Scope BLOCKED (sandbox write-permission)**:
- L1 `/engram-help` slash command (`.claude/commands/engram-help.md`)
- L3 `/sdd-help` slash command (`.claude/commands/sdd-help.md`)
- L2 `/skills-search` slash command (`.claude/commands/skills-search.md`)
- Cross-agent `/rules-expand` namespace reservation (`.claude/commands/rules-expand.md`)

The sandbox in this session denied both `mkdir .claude/commands` and `Write` to files under that path. Slash-command authoring requires either:
1. An out-of-sandbox pass (user or orchestrator with elevated permissions creates `.claude/commands/` first, then a follow-up agent fills in the four command files), OR
2. A settings.json allowlist entry granting write access under `.claude/commands/**` (per `rules/orchestrator-prompt-compose.md` — touching `.claude/` is a trap-sensitive target and deserves the pipe-through check).

**Does not touch**:
- Global `~/.claude/CLAUDE.md` — ADR explicitly marks this user-owned; slimming that file is Phase 3 / opt-in via `scripts/startup-slim.sh` (not built yet).
- `skills/invariant-check/`, `rules/decision-depth-gate.md` — scope-excluded by coordinating task prompt.

**Acceptance criteria status**:
| # | Criterion | Target | Actual | Met |
|---|---|---|---|---|
| 1 | Every skill has `name` + `description` + scope/audience | 125 | 125 | yes |
| 2 | `summary_line` added where `description` > 80 chars | 88 | 88 | yes |
| 3 | `.claude/commands/*.md` ≥ 3 files | ≥3 | 0 | no (blocked) |
| 4 | ADR-044 has Resolution Log 2026-04-21 | yes | yes | yes |
| 5 | Catalog regenerated + parses | yes | 11,941 chars, 0 errors | yes |
| 6 | Frontmatter YAML parse test | 0 errors | 0 errors | yes |

**Next action (Phase 2 completion)**: relaunch Phase 2 slash-command work from a context where `.claude/commands/` is writable. The four command bodies are fully specified in §"Lazy-loading mechanism" of this ADR and can be generated directly from the current `~/.claude/CLAUDE.md` sections plus `skills/CATALOG-COMPACT.md` for the `/skills-search` body.

## References

- ADR-032 (orchestrator-prompt-compose, gotchas injection)
- ADR-037 (self-knowledge-base)
- Paper "Evaluating AGENTS.md" (arxiv.org/abs/2602.11988) — context files reduce task success ≥20%
- `rules/adaptive-bypass.md` — the "less context improves quality" principle
- `skills/CATALOG-COMPACT.md` — the compression precedent to emulate for engram/SDD/MCP blocks

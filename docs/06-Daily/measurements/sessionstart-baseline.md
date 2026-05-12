# SessionStart Deep Audit — Self-Host vs Client Baseline

**Date**: 2026-04-30
**Author**: manual audit (read-only investigation)
**Context**: ADR-074 two-stage loading + ADR-075 tier expansion + ADR-079 self-hosting fix.
All token estimates use bytes ÷ 4. Where actual measurement was impossible, cells are marked `[est]`.

---

## 1. Component Tables

### Key: measurement vs estimate

- **measured** — `wc -c` on actual file
- `[est]` — approximated from script stdout inspection or harness docs
- All byte→token conversions use ÷4 (Claude tokenizer skews ±20% from this estimate)

---

### 1.1 Self-Hosting (this repo, `luum-agent-os`)

Efficiency profile: `default` (reads `cognitive-os.yaml → efficiency.profile: default`).
After ADR-079, `IS_SELF_HOSTING=true` no longer forces `EFFICIENCY_PROFILE=full`.
Current state: **1 rule symlink** in `.claude/rules/cos/` (RULES-COMPACT.md only).

| Component | Mechanism | Bytes (measured) | ~Tokens | Notes |
|---|---|---|---|---|
| `~/.claude/CLAUDE.md` (global) | claudeMd — harness loads all `~/.claude/*.md` | 11,125 | ~2,781 | measured |
| `<repo>/CLAUDE.md` | claudeMd | 0 | 0 | file does not exist in this repo |
| `RULES-COMPACT.md` symlink | claudeMd via `.claude/rules/cos/RULES-COMPACT.md` symlink | 8,596 | ~2,149 | measured |
| `skills/CATALOG-COMPACT.md` | claudeMd via `.claude/skills/CATALOG-COMPACT.md` symlink | 14,280 | ~3,570 | measured; ALWAYS injected at SessionStart (not skill-tool-triggered) |
| `session-init.sh` stdout | SessionStart hook → ~10 echo lines | ~246 | ~62 | measured (script analysis); prints session ID + catalog pointer only |
| `session-startup-protocol.sh` stdout | SessionStart hook → SUMMARY heredoc | ~350 | ~88 | measured (script analysis); 6-line status summary |
| `infra-health.sh` stdout | SessionStart hook → 1 status line typical | ~80 | ~20 | `[est]`; "Infrastructure: N/M services running" when Docker inactive/no services |
| `self-install.sh` stdout | SessionStart hook → 1 status line | ~40 | ~10 | `[est]`; "Self-hosting: OK (default)" |
| `self-knowledge-refresh.sh` stdout | SessionStart hook → 0 stdout (JSON to file only) | 0 | 0 | measured (no stdout echo without stderr) |
| `crash-recovery.sh` stdout | SessionStart hook (called by session-init) → conditional output | ~0 | ~0 | `[est]`; only emits if orphaned state-snapshot.json exists |
| `host-tool-doctor.sh` stdout | SessionStart hook → 0 unless doctor script missing | ~0 | ~0 | `[est]`; only emits WARN when doctor script is absent |
| `profile-drift-autoapply.sh` stdout | SessionStart hook → silent unless drift detected | ~0 | ~0 | `[est]`; no stdout in normal operation |
| `reaper-daemon-launcher.sh` stdout | SessionStart hook → daemon management | ~0 | ~0 | `[est]`; exits silently after launching background process |
| `session-watchdog-launcher.sh` stdout | SessionStart hook → daemon management | ~0 | ~0 | `[est]`; exits silently |
| `docker-drift-detector.sh` stdout | SessionStart hook → silent unless drift | ~0 | ~0 | `[est]` |
| `cos-executor-daemon-launcher.sh` stdout | SessionStart hook → daemon launch | ~0 | ~0 | `[est]` |
| `engram-daemon-launcher.sh` stdout | SessionStart hook → daemon launch | ~0 | ~0 | `[est]` |
| `session-resume.sh` stdout | SessionStart hook → conditional recovery output | ~0 | ~0 | `[est]`; only if previous session state found |
| `aspirational-audit-weekly.sh` stdout | SessionStart hook → silent except once/week | ~0 | ~0 | `[est]`; rate-limited by mtime check |
| `session-start-worktree-nudge.sh` stdout | SessionStart hook → conditional nudge | ~0 | ~0 | `[est]`; only if commits since last wrapup |
| `mcp-scan.sh` stdout | SessionStart hook → silent unless MCP issues | ~0 | ~0 | `[est]` |
| MCP server instructions (engram) | Harness system-reminder (not COS-controlled) | ~2,000 | ~500 | `[est]`; engram tool descriptions block |
| Deferred tools list | Harness system-reminder (not COS-controlled) | ~1,200 | ~300 | `[est]`; harness-managed listing of available deferred tools |
| **TOTAL (self-host, typical session)** | | **~37,917** | **~9,480** | |

**Notes on self-hosting**:
- No project-level CLAUDE.md exists in this repo — verified.
- CATALOG-COMPACT.md is loaded via claudeMd (symlink in `.claude/skills/`), not via a hook echoing the content. The hook (`session-init.sh`) only prints a one-line pointer: `Skills catalog: skills/CATALOG-COMPACT.md`. Claude Code loads the file content directly.
- After ADR-079 (staged but not yet committed as of this audit), the self-hosting penalty of ~83 KB (~20,779 tokens) from loading 16 duplicate rules at Stage 1 is eliminated.

---

### 1.2 Client Install (fresh project using COS, `efficiency.profile: default`)

In client mode: `IS_SELF_HOSTING=false`, `EFFICIENCY_PROFILE=default`, `SYNC_ALL_RULES=false`.
`CORE_RULES=["RULES-COMPACT.md"]` — post `991b24a`. Client project has its own CLAUDE.md.

| Component | Mechanism | Bytes (measured/est) | ~Tokens | Notes |
|---|---|---|---|---|
| `~/.claude/CLAUDE.md` (global) | claudeMd | 11,125 | ~2,781 | measured; same user global file |
| `<client-project>/CLAUDE.md` | claudeMd | ~2,000 | ~500 | `[est]`; typical COS-generated client CLAUDE.md ~2KB |
| `RULES-COMPACT.md` symlink | claudeMd via `.claude/rules/cos/RULES-COMPACT.md` | 8,596 | ~2,149 | measured |
| `skills/CATALOG-COMPACT.md` | claudeMd via `.claude/skills/CATALOG-COMPACT.md` symlink | 14,280 | ~3,570 | measured; same catalog, same mechanism |
| `session-init.sh` stdout | SessionStart hook | ~246 | ~62 | same as self-host |
| `session-startup-protocol.sh` stdout | SessionStart hook | ~350 | ~88 | same as self-host |
| `infra-health.sh` stdout | SessionStart hook | ~80 | ~20 | `[est]` |
| `self-install.sh` stdout | SessionStart hook → "Self-hosting: OK" | ~40 | ~10 | `[est]` |
| Other SessionStart hooks (12 remaining) | SessionStart hooks → silent in normal operation | ~0 | ~0 | `[est]`; same as self-host — all are conditional/daemon launchers |
| MCP server instructions | Harness system-reminder | ~2,000 | ~500 | `[est]` |
| Deferred tools list | Harness system-reminder | ~1,200 | ~300 | `[est]` |
| **TOTAL (client, post-991b24a)** | | **~39,917** | **~9,980** | |

**Notes on client mode**:
- The only real difference from self-host is the presence of a client CLAUDE.md (~2KB typical).
- Before `991b24a`, CORE_RULES contained 16 entries totalling ~76 KB (~19,000 tokens). After: 1 entry (RULES-COMPACT.md = 8,596 bytes). Net saving: **~67 KB (~16,850 tokens)** removed from Stage 1.
- The `[ref-key]` expansion at Stage 2 (PreToolUse[Agent]) still loads those rule bodies on-demand when `inject-phase-context.sh` fires — but only for the agent calls that need them, not at SessionStart.

---

## 2. Pre-991b24a vs Post-991b24a Comparison

| Mode | Pre-991b24a bytes | Post-991b24a bytes | Saving (bytes) | Saving (tokens) |
|---|---|---|---|---|
| Self-host (pre-ADR-079) | ~121,035 | ~37,917 | ~83,118 | ~20,779 |
| Self-host (post-ADR-079, staged) | same regression | ~37,917 | ~83,118 | ~20,779 |
| Client default | ~107,017 | ~39,917 | ~67,100 | ~16,775 |

The self-host saving was silently zero until ADR-079 (staged) removes the `IS_SELF_HOSTING` force.

---

## 3. Per-Commit SessionStart Impact Analysis

| Commit | Subject | Self-Host SessionStart Impact | Client SessionStart Impact | Evidence |
|---|---|---|---|---|
| `61d5703` | feat(learning-loop): close tier-0 gaps | **+0 tokens** (hooks output, not SessionStart) | **+0 tokens** | Adds `skill-feedback-tracker.sh` to PostToolUse[Agent], not SessionStart. `.claude/settings.json` change is a PostToolUse hook registration. |
| `991b24a` | perf(self-install): drop redundant CORE_RULES | **+0 tokens (self-host regression, pre-ADR-079)** | **–16,775 tokens** | `hooks/self-install.sh` CORE_RULES reduced 16→1 entries. Self-host was bypassed by IS_SELF_HOSTING=full override. Client gets full saving. |
| `3912338` | fix(rules): align stage1 core rule contract | **0 tokens** | **0 tokens** | Only test file change (`tests/integration/test_consolidation_external.py`). No hook or rule changes. |
| `c8a5259` | feat(rules): add tiered ref-key expansion | **0 tokens (SessionStart)** | **0 tokens (SessionStart)** | Adds `expansion.tier_filter: [0,1]` to `cognitive-os.yaml`. Affects PreToolUse[Agent] inject-phase-context.sh only — not SessionStart. Adds TIER frontmatter to 112 rules (no size impact on RULES-COMPACT). |
| `e93e3b7` | perf(ref-key-loader): selective tier-based expansion | **0 tokens** | **0 tokens** | Docs-only: ADR-075 + research-log. No hook or claudeMd changes. |
| `f360fe4` | perf(rules): tighten Tier-1 keep-list (~56K tokens at default) | **0 tokens (SessionStart)** | **0 tokens (SessionStart)** | 57 rules changed from TIER:1→TIER:2. Affects Stage-2 expansion at PreToolUse[Agent] only. SessionStart loads RULES-COMPACT.md (unchanged size) not the individual rule files. |
| `0c2583f` | feat(metrics): expansion validation harness + baseline | **0 tokens** | **0 tokens** | New test files and fixtures only. No runtime hook or claudeMd changes. |
| `5146fd8` | docs(hermes-alignment): tier 2 ADRs + skill frontmatter | **0 tokens** | **0 tokens** | Skill frontmatter additions + ADRs. CATALOG-COMPACT.md was NOT regenerated in this commit. No SessionStart change. |
| `22e7f5f` | feat(memory): mid-task memory tool (port from hermes) | **0 tokens (SessionStart)** | **0 tokens (SessionStart)** | Adds `memory-prefetch.sh` under UserPromptSubmit (async), not SessionStart. Settings change is UserPromptSubmit hook only. |
| ADR-079 (staged, not yet committed) | fix: CORE_RULES applies to self-hosting | **–20,779 tokens** | **0 tokens** | Removes IS_SELF_HOSTING force from `hooks/self-install.sh` lines 255-263. Brings self-host into parity with client. |

**Summary**: Of all commits today, only `991b24a` impacts SessionStart tokens (client only, –16,775 tokens). The ADR-079 staged change will add a second impact (self-host, –20,779 tokens) when committed.

---

## 4. CATALOG-COMPACT Injection — Verification

**Question**: Is `CATALOG-COMPACT.md` always injected at SessionStart, or only when the Skill tool is first used?

**Answer: ALWAYS injected at SessionStart.**

Mechanism: `.claude/skills/CATALOG-COMPACT.md` is a symlink to `skills/CATALOG-COMPACT.md`.
Claude Code loads all `.md` files in `.claude/skills/` as `claudeMd` content — this is a harness-level behaviour (not COS-controlled). The file is loaded unconditionally before any user interaction.

`session-init.sh` line 111 only prints a one-line pointer (`Skills catalog: skills/CATALOG-COMPACT.md (run /catalog-full for details)`) — it does NOT cat the file content to stdout. The actual 14,280-byte content arrives via claudeMd.

Evidence: `.claude/skills/CATALOG-COMPACT.md` exists as a symlink (confirmed `ls -la`). No conditional loading logic exists in any SessionStart hook.

---

## 5. Unexplored Levers — Ranked

Ranked by estimated tokens saved per session (self-host mode, post-ADR-079 baseline of ~9,480 tokens).

| # | Lever | What Changes | Tokens Saved (self-host / client) | Effort | Risk | Why Not Done Yet |
|---|---|---|---|---|---|---|
| 1 | **CATALOG-COMPACT lazy-load on first Skill use** | Remove `CATALOG-COMPACT.md` symlink from `.claude/skills/`. Only inject when agent first invokes the Skill tool (via a PreToolUse[Skill] hook that cats the file to context). | ~3,570 / ~3,570 | ~50 LOC hook + change to `.claude/skills/` management in self-install.sh | Medium: agent cannot discover skills by name until first Skill invocation. In practice agent usually knows slash commands, but serendipitous skill discovery breaks. | Harness loads `.claude/skills/*.md` unconditionally — removing requires a PreToolUse hook workaround. No formal Skill lazy-load mechanism exists yet. |
| 2 | **`~/.claude/CLAUDE.md` trim (user-controlled)** | Refactor the 11,125-byte global CLAUDE.md to strip SDD workflow details, model routing table, rule cross-references that are also in RULES-COMPACT. Keep only global personal preferences and the Delegation Rules preamble. | ~1,500–2,000 / ~1,500–2,000 | 1 file, 1 edit session, ~30 min | Low: breaks nothing, only reduces verbosity. Risk: user may lose nuance from removed sections. | Belongs to the user, not COS. COS cannot edit this without explicit user action. Flagged here as the largest user-controlled lever. |
| 3 | **RULES-COMPACT diet: remove ADR cross-reference appendix** | `rules/RULES-COMPACT.md` section "Cross-references" and "Related" footers in referenced rules add ~1,200 bytes with no runtime value (links to docs the agent cannot open). Strip them from the compact index. | ~300 (compact only) / ~300 | 1 file, 1 edit | Low: formatting only, no logic change | Not high-priority given small absolute saving. Has not been flagged as a bottleneck. |
| 4 | **SessionStart hook consolidation: merge stdout-emitting hooks** | `session-init.sh`, `session-startup-protocol.sh`, and `infra-health.sh` each pay a process-spawn overhead (~50–150 ms) and emit overlapping status lines. Merge into a single `session-context.sh` that outputs one consolidated block. | ~300 (removes duplicate header lines) / ~300 | ~200 LOC + regression tests | Low: functional equivalence easy to verify | Three hooks grew independently. Consolidation requires agreement on what each emits and is a maintenance refactor, not a feature. |
| 5 | **MCP engram instructions block: defer verbose protocol** | The engram system-reminder block (~2,000 bytes / ~500 tokens) includes tool listing + proactive-save rules on every session. Replace with a minimal pointer: "Engram active. Run `engram-help` for protocol." | ~400 / ~400 | Requires changes to MCP server's `instructions` field in server config | Medium: agents may not call `engram-help` and miss save triggers, reducing memory consistency. | The engram MCP server controls its own instructions string. COS does not own that component. Change requires upstream coordination. |
| 6 | **ROADMAP.md removal from Tier-0 / CORE_RULES** | `ROADMAP.md` (7,241 bytes / ~1,810 tokens) is classified Tier-0 but contains implementation-status notes, not runtime governance. It is referenced by RULES-COMPACT section 2 but agents rarely need the sprint-level context at SessionStart. Demote to Tier-1 or Tier-2. | ~1,810 / ~1,810 (if also removed from Stage-1 claudeMd) | 1-line frontmatter change + 1 CORE_RULES exclusion if needed | Low: ROADMAP.md is informational; removing from context does not change agent behaviour in normal operation | ROADMAP was classified Tier-0 conservatively to ensure agents know rule enforcement status. It was historically important when rules.enforcement was broken; now that ADR-072 + registered hooks are live, it is less critical at every session. |

---

## 6. ADR Decision: None Required

No non-trivial architectural decision is forced by this audit. The levers above are implementation options, not architectural choices requiring an ADR. The next ADR should be ADR-080 if and when the team decides to implement lazy-load for CATALOG-COMPACT (Lever 1) — that decision changes the harness contract for skill discovery and warrants a record.

---

## 7. Methodology Notes

- Token estimates: bytes ÷ 4. Claude's actual tokenizer produces different counts (GPT-family BPE averages ~4 chars/token for English prose, but markdown tables/code can be 3–5 chars/token). Actual counts will differ by ±15–25%.
- Hook stdout sizes: measured by static analysis of echo/printf/cat statements in each hook script, not by running the hooks. Some conditional branches (infra-health, crash-recovery) may emit more in failure cases.
- Client CLAUDE.md: estimated at ~2,000 bytes based on `cognitive-os-init` template output. Actual client projects vary.
- MCP engram instructions: estimated from visible system-reminder content (~2,000 bytes is conservative; the actual block including CONFLICT SURFACING and HOW TO ASK sections is likely 3,000–4,000 bytes).
- `IS_SELF_HOSTING=true` bypass: the ADR-079 fix is staged but not committed at time of this audit. The "post-ADR-079" rows reflect the expected state after that commit lands.

---

## 8. Cross-References

- `docs/06-Daily/measurements/stage2-expansion-baseline.md` — Stage-2 PreToolUse[Agent] expansion measurements (separate from SessionStart)
- `docs/02-Decisions/adrs/ADR-074-tier-0-learning-loop-closure.md` — two-stage loading architecture
- `docs/02-Decisions/adrs/ADR-075-stage2-selective-expansion.md` — tier filter for Stage-2
- `docs/02-Decisions/adrs/ADR-079-corerules-applies-to-self-hosting.md` — IS_SELF_HOSTING override removal
- `hooks/self-install.sh` lines 253–270 — IS_SELF_HOSTING detection + EFFICIENCY_PROFILE logic
- `hooks/session-init.sh` lines 106–115 — CATALOG-COMPACT pointer (not inline)
- `.claude/skills/CATALOG-COMPACT.md` — symlink that delivers catalog via claudeMd
- `.claude/rules/cos/RULES-COMPACT.md` — symlink that delivers compact rule index via claudeMd

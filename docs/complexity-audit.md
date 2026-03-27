# Complexity Audit: Cognitive OS vs BMAD Method v6

> Date: 2026-03-22
> Verdict: **Over-engineered.** Not catastrophically, but significantly. ~40% of content is dead weight.

---

## 1. Raw Numbers

| Metric | BMAD v6 (src/) | Cognitive OS (.cognitive-os/) |
|--------|---------------:|----------------------:|
| Total files | 272 | 198 |
| Total lines | 39,841 | 28,625 |
| Skill entry points | 43 | 24 |
| Core skills (shipped) | 40 files / 5,936 lines | — |
| Domain skills (shipped) | 232 files / 33,905 lines | — |
| Hooks | 0 (no hook system) | 24 files / 2,366 lines |
| Rules | 0 (embedded in skills) | 28 files / 2,135 lines |
| Docs | 0 (separate website) | 53 files / 11,863 lines |
| Workflows | 0 (part of skills) | 28 files / 4,413 lines |
| Config | 0 | 1 file / 222 lines |

**Key insight**: BMAD v6 has MORE total lines but most are CLI tooling (20,782 lines) and website (32,856 lines) that never touch the agent context. Their shipped content is 39,841 lines across 272 files but uses step-file sharding — only SKILL.md entry points (avg 6-87 lines each) load initially. Steps load on demand.

Cognitive OS has fewer total lines but a MUCH higher percentage loads into context. The 53 docs alone (11,863 lines) are never loaded by the agent but add cognitive overhead for maintenance.

## 2. What BMAD Achieves with LESS

### 2.1 No Hooks, No Runtime Overhead

BMAD v6 has **zero hooks**. Zero. They achieve quality through:
- **Step-file architecture**: Long workflows break into discrete step files loaded sequentially, not all at once
- **Skill validators**: Static validation at install time (not runtime)
- **Adversarial review skills**: Loaded on demand, not as hooks

Cognitive OS has **20 registered hooks** that fire on tool calls. Two hooks fire on EVERY tool call (matcher: `*`):
- `private-mode-metrics-gate.sh` — checks a flag file. 18 lines.
- `tool-loop-detector.sh` — parses stdin JSON. 79 lines.

Each Agent call fires **8 hooks** (4 pre, 4 post). Each Bash call fires **3 hooks**.

### 2.2 No Separate Rules Layer

BMAD embeds behavioral constraints directly in skill SKILL.md files and agent definitions. No separate rules directory. No compact-vs-full loading strategy. No contextual triggers.

Cognitive OS has **28 rules** (2,135 lines) plus a compact version (39 lines), plus contextual trigger configuration in cognitive-os.yaml. The compact version alone is good engineering. The 28 full rules files that sit on disk but rarely load are maintenance debt.

### 2.3 No Docs in the Agent Directory

BMAD keeps documentation on a separate website. The skill directory contains only what the agent needs: SKILL.md + step files + templates.

Cognitive OS has **53 docs (11,863 lines)** inside `.cognitive-os/docs/`. The agent never reads these during normal operation. They exist as reference for humans, but they duplicate information already in rules, skills, and the CATALOG.

## 3. Dead Weight Identified

### 3.1 Dead Hooks (3 files, 279 lines)

Files exist in `hooks/` but are NOT registered in `settings.local.json`:

| Hook | Lines | Status |
|------|------:|--------|
| `context-budget.sh` | 86 | Dead — mentions SessionStart but not registered |
| `context-watchdog.sh` | 79 | Dead — mentions PostToolUse but not registered |
| `coverage-gate.sh` | 114 | Dead — mentions PostToolUse but not registered |

**Action**: Delete or register them. Currently they waste disk space and confuse maintenance.

### 3.2 SaaS Vision Docs (9 files, 3,577 lines) — Not Actionable Today

These are business/planning documents with zero operational value for the agent:

| Doc | Lines | Why dead weight |
|-----|------:|-----------------|
| `commercial-features.md` | 615 | Sales pitch, not agent instructions |
| `propuesta-comercial.md` | 616 | Same content in Spanish |
| `open-source-design.md` | 644 | OSS framework design that doesn't exist yet |
| `openclaw-implementation-roadmap.md` | 397 | Roadmap for patterns not yet adopted |
| `openclaw-remaining-patterns.md` | 387 | More unimplemented patterns |
| `next-steps-saas.md` | 351 | SaaS launch plan |
| `saas-product-vision.md` | 298 | Product vision doc |
| `portability-plan.md` | 166 | Multi-IDE plan not started |
| `pitch-ejecutivo.md` | 103 | Executive pitch deck content |

**Action**: Move to a separate `docs/vision/` directory outside `.cognitive-os/`, or to a Google Doc. These should not live alongside operational agent configuration.

### 3.3 Docs That Duplicate Rules (12+ files, ~2,500 lines)

These docs describe the same system that a rule already defines:

| Doc | Lines | Duplicates Rule |
|-----|------:|-----------------|
| `context-optimization.md` | 238 | `rules/context-optimization.md` (75 lines) |
| `context-engineering.md` | 182 | `rules/context-management.md` (78 lines) |
| `fault-tolerance.md` | 188 | `rules/fault-tolerance.md` (79 lines) |
| `agent-kpis.md` | 259 | `rules/agent-kpis.md` (112 lines) |
| `squad-system.md` | 366 | `rules/squad-protocol.md` (119 lines) |
| `sre-agent.md` | 145 | `rules/sre-protocol.md` (76 lines) |
| `resource-governor.md` | 118 | `rules/resource-governance.md` (111 lines) |
| `auto-skill-generation.md` | 66 | `rules/auto-skill-generation.md` (136 lines) |
| `private-mode.md` | 56 | `rules/private-mode.md` (41 lines) |
| `auto-refinement.md` | 156 | Related to `rules/closed-loop-prompts.md` (270 lines) |
| `model-compatibility.md` | 53 | `rules/model-compatibility.md` (75 lines) |
| `model-evaluation.md` | 143 | `rules/model-routing.md` (40 lines) |

**Action**: The rules are authoritative. The docs add "nice explanation" but nobody reads them. Delete or consolidate into the rule files as a `## Details` section.

### 3.4 Redundant Rules (3 files, 126 lines)

Three rules cover "skill management" from slightly different angles:

| Rule | Lines | Focus |
|------|------:|-------|
| `skill-adaptation.md` | 64 | Feedback loop for skill improvement |
| `skill-auto-loader.md` | 30 | Load skills based on detected stack |
| `skill-registry-protocol.md` | 32 | Priority order for skill loading |

**Action**: Merge into one `skill-management.md` rule.

### 3.5 Overlapping Hooks (3 pairs)

| Pair | Overlap | Verdict |
|------|---------|---------|
| `error-learning.sh` + `error-pattern-detector.sh` | First captures errors, second reads the captures and warns. | **Legitimate pipeline** — keep both, but they could be one hook with two modes. |
| `skill-feedback-tracker.sh` + `skill-metrics-tracker.sh` | Both fire on Agent/Skill completion. First saves to Engram, second to JSONL. | **Redundant** — merge into one hook that does both. Saves one hook invocation per agent call. |
| `private-mode-gate.sh` + `private-mode-metrics-gate.sh` | Both check the same flag file. First blocks Engram tools, second suppresses metrics. | **Legitimate split** — different matchers (Engram tools vs `*`). But the `*` matcher means `private-mode-metrics-gate.sh` fires on EVERY tool call to check a flag that's rarely set. |

## 4. Hook Performance Overhead

### Per-Tool-Call Overhead

Every single tool call (Read, Edit, Grep, Bash, etc.) triggers:
1. `private-mode-metrics-gate.sh` — reads stdin, checks flag file, exits
2. `tool-loop-detector.sh` — reads stdin, parses JSON, checks patterns

That's **2 shell process spawns per tool call**. In a session with 200 tool calls, that's 400 shell processes just for monitoring.

### Per-Agent Overhead

Each Agent tool call triggers **8 hooks**:
- Pre: `resource-check.sh`, `inject-phase-context.sh`, `agent-prelaunch.sh`, `error-pattern-detector.sh`
- Post: `agent-checkpoint.sh`, `auto-refine.sh`, `auto-skill-generator.sh`, `architecture-compliance.sh`

Plus the 2 universal hooks. That's **10 shell processes per agent call**.

### BMAD's Approach: Zero Runtime Overhead

BMAD achieves similar goals (quality checks, error recovery, skill improvement) through:
- Skills that users invoke when needed
- Step-file architecture that loads incrementally
- Static validation at install time
- No runtime hook system at all

## 5. Token Budget Comparison

### Cognitive OS Baseline (Session Start)

| Source | Tokens (est.) |
|--------|-------------:|
| `RULES-COMPACT.md` | ~1,500 |
| `CATALOG.md` | ~2,000 |
| `cognitive-os.yaml` | ~800 |
| `.claude/CLAUDE.md` | ~500 |
| `.claude/rules/` (7 files) | ~1,500 |
| CLAUDE.md (global) | ~3,000 |
| **Total baseline** | **~9,300** |

This is reasonable. The progressive loading system works well.

### BMAD v6 Baseline (Session Start)

BMAD loads only the agent persona (50-90 lines) plus bmad-help if invoked. Total baseline: ~500-1,000 tokens. Skills load fully on demand via SKILL.md (6-177 lines each) + step files.

**BMAD's baseline is ~10x lighter.** But BMAD doesn't have always-active rules, phase awareness, or cost tracking. Different tradeoffs.

## 6. What We're Doing RIGHT That BMAD Doesn't

1. **Progressive loading** (RULES-COMPACT + CATALOG): Genuinely good engineering. BMAD loads full skills; we load indexes.
2. **Phase-aware behavior**: `reconstruction` vs `production` mode changes agent behavior. BMAD has no concept of project phases.
3. **Error learning loop**: Capturing errors -> detecting patterns -> injecting warnings is valuable for long projects.
4. **Engram integration**: Persistent memory across sessions. BMAD has no memory system.
5. **Private mode**: Privacy toggle for sensitive work. BMAD has no equivalent.
6. **Resource governance**: Budget tracking and model routing optimization. BMAD has no cost awareness.
7. **Squad system**: Multi-agent coordination. BMAD's agents are independent roles.

## 7. What BMAD v6 Got Right That We Should Learn From

### 7.1 Step-File Architecture (v6 Pattern 5)

BMAD breaks complex workflows into numbered step files (`step-01-init.md`, `step-02-analysis.md`). Each step is loaded individually. The agent follows one step, completes it, loads the next.

**We should adopt this** for our larger skills like `sre-agent` (491 lines), `systematic-debugging` (503 lines), and `test-driven-development` (386 lines).

### 7.2 Skill-Only Architecture

BMAD v6.1 converted ALL agents, workflows, and tasks into skills with SKILL.md entry points. One format, one loading mechanism. Their v6 changelog explicitly states they "removed legacy YAML/XML workflow engine plumbing."

**We have 4 separate concepts**: skills, workflows, hooks, rules. Skills and rules overlap. Workflows are Python scripts that don't integrate with the skill system.

### 7.3 No Docs in the Agent Directory

BMAD's principle: if the agent doesn't need it, it shouldn't be in the agent's directory. Documentation lives on the website, not in `src/`.

**We have 53 docs (11,863 lines)** in the agent directory. Zero of them are loaded during normal operation.

### 7.4 Static Validation Over Runtime Checks

BMAD validates skill quality at install time with `validate-skills.js` and `validate-file-refs.js`. Problems are caught before they reach the agent.

**We check everything at runtime** with hooks, adding latency to every operation.

## 8. Specific Recommendations

### Immediate Actions (Trim ~6,000 lines)

1. **Delete 3 dead hooks**: `context-budget.sh`, `context-watchdog.sh`, `coverage-gate.sh` (-279 lines)
2. **Move 9 SaaS vision docs** out of `.cognitive-os/docs/` to `docs/vision/` (-3,577 lines)
3. **Delete 12 duplicate docs** that restate what rules already define (-2,500 lines)
4. **Merge 3 skill-related rules** into one `skill-management.md` (-~60 lines)
5. **Merge `skill-feedback-tracker.sh` + `skill-metrics-tracker.sh`** into one hook (-~50 lines)

### Medium-Term Actions

6. **Move `private-mode-metrics-gate.sh`** from `*` matcher to specific matchers (Bash, Edit, Write, Agent). It doesn't need to fire on Read/Grep/Glob.
7. **Adopt step-file architecture** for skills > 200 lines
8. **Consolidate overlapping rule+doc+skill triplicates** (agent-kpis, sre, squad, resource-governance)
9. **Move Python workflows** to skills format for consistency

### Architectural Questions

10. **Do we need 20 hooks?** BMAD has zero. The error-learning + pattern-detector pipeline is valuable. The rest could be optional or skill-invoked instead of always-on.
11. **Do we need 28 rules?** The compact version (39 lines) proves we can express everything in ~1,500 tokens. The full rules exist for contextual loading but 12 of them have duplicate docs.
12. **Do we need 53 docs?** At most 15 are operational. The rest are vision/planning/sales content.

## 9. Final Verdict

**Cognitive OS is over-engineered for its current stage**, but the CORE architecture is sound:

- Progressive loading: GOOD
- Phase-aware behavior: GOOD
- Error learning: GOOD
- Engram integration: GOOD
- Hook system concept: GOOD (but too many hooks)
- Rules system concept: GOOD (but too many rules, duplicated by docs)
- Docs: BAD (41% is SaaS vision, 23% duplicates rules, only 36% is operational)

**The problem isn't the architecture. The problem is accumulation.** Every good idea got a rule, a doc, a skill, AND a hook. BMAD v6's key lesson from removing 67,793 lines: you can achieve the same outcomes with less material if each piece has exactly one home.

### Recommended Target State

| Layer | Current | Target | Reduction |
|-------|--------:|-------:|-----------:|
| Hooks | 24 (20 registered) | 12-14 | ~40% |
| Rules | 28 | 18-20 | ~30% |
| Skills | 24 | 24 | 0% (skills are fine) |
| Docs | 53 | 15-20 | ~65% |
| Workflows | 28 | 28 | 0% (separate concern) |
| **Total lines** | **28,625** | **~17,000** | **~40%** |

The goal: every piece of content has exactly ONE canonical home. No rule+doc+skill triplicates. No dead hooks. No SaaS vision docs mixed with operational config.

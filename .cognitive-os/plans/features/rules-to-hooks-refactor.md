# Plan: Rules-to-Hooks Architectural Refactor

## Problem

The OS has ~100 rules (markdown files) loaded into agent context. This costs ~73K tokens at full load, ~1.5K compressed via RULES-COMPACT. The fundamental issue: rules are **passive documentation** that depends on the agent "remembering" to follow them. Hooks are **active enforcement** that runs automatically.

Today:
- Agent reads rule → agent decides whether to follow it → maybe it does, maybe it doesn't
- Hook fires → behavior is enforced regardless of what the agent "remembers"

Evidence from this session: the confidentiality-enforcer HOOK catches IP leaks that the confidentiality-protection RULE would have missed (agent forgets, hook doesn't).

## Proposal: 3-Tier Architecture

### Tier 1: Hooks (enforcement — no tokens)
Rules that can be enforced automatically become hooks. Zero token cost. The agent doesn't need to know about them.

**Candidates for migration (rules → hooks):**

| Rule | Hook Behavior | Why It Works |
|---|---|---|
| `license-policy.md` | PreToolUse on Agent: scan prompt for library names, check licenses | License check is mechanical — pattern match on SPDX identifiers |
| `content-policy.md` | Already a hook | Already migrated |
| `confidentiality-protection.md` | Already a hook | Already migrated |
| `credential-management.md` | PostToolUse on Edit/Write: scan for hardcoded secrets | secret-detector.sh already does this partially |
| `scope-proportionality.md` | Already a hook | Already migrated |
| `blast-radius.md` | Already a hook | Already migrated |
| `rate-limiting.md` | Already a hook | Already migrated |
| `pre-commit-gate.md` | Already a git hook | Already migrated |
| `scope-creep-detection.md` | Already a hook | Already migrated |
| `assumption-tracking.md` | Already a hook | Already migrated |

**~30 rules are already hooks.** The rule .md files exist as documentation for humans, but enforcement is in the hook.

### Tier 2: Skills (workflows — loaded on demand)
Rules that describe "how to do X" become skills. Only loaded when needed. Token cost: ~1-3K per skill, only when active.

**Candidates for migration (rules → skills):**

| Rule | Skill | Why |
|---|---|---|
| `closed-loop-prompts.md` | Already encoded in `templates/agent-preamble.md` | The preamble IS the skill |
| `acceptance-criteria.md` | `/exhaustive-prompt` already does this | Skill exists |
| `sandbox-sampling.md` | `/sandbox-sample` already does this | Skill exists |
| `estimation-calibration.md` | `/planning-poker` and `/estimation-report` | Skills exist |
| `plan-first.md` | `/plan-feature` and `/plan-bug` | Skills exist |
| `scout-pattern.md` | `/scout` | Skill exists |
| `error-learning.md` | `/error-analyzer` | Skill exists |
| `trust-score.md` | Trust report format → part of `templates/agent-preamble.md` | Template injection |

**~20 rules are already duplicated in skills/templates.** The rule .md just documents what the skill already does.

### Tier 3: RULES-COMPACT (routing table — ~1.5K tokens)
The minimal set of rules that MUST be in context because they're behavioral contracts that can't be enforced mechanically:

| Rule | Why It Must Stay | Tokens |
|---|---|---|
| `adaptive-bypass.md` | Complexity classification requires judgment | ~200 |
| `agent-quality.md` | Meta-rule about output quality | ~300 |
| `token-economy.md` | 5 principles for cost awareness | ~150 |
| `phase-aware-agents.md` | Phase determines behavior | ~200 |
| `definition-of-done.md` | DoD by complexity level | ~200 |
| `responsiveness.md` | Communication protocol | ~100 |
| `broken-window-policy.md` | Cultural rule (fix what you find) | ~100 |
| `anti-hallucination.md` | Ground truth verification | ~150 |

**~10-15 rules are genuinely irreducible** — they require agent judgment and can't be mechanized.

## Migration Strategy

### Phase 1: Audit (1 session)
- For each of the ~100 rules, classify: HOOK (already enforced), SKILL (already a workflow), COMPACT (must stay in context), or REDUNDANT (documented elsewhere)
- Produce a migration matrix

### Phase 2: Deduplicate (1-2 sessions)
- Remove rule .md files where the hook/skill already exists AND the rule adds no information the hook doesn't enforce
- Update RULES-COMPACT to reflect removals
- Run full test suite after each batch

### Phase 3: Migrate remaining (2-3 sessions)
- Rules that CAN become hooks but aren't yet → implement hooks
- Rules that CAN become skills but aren't yet → implement skills
- Test each migration

### Phase 4: Slim RULES-COMPACT (1 session)
- Reduce to only the ~10-15 irreducible rules
- Target: < 500 tokens for the routing table
- Full test suite validation

## Component Scoping: OS-only vs Project vs Both

Every hook, skill, and rule should be classified by scope:

| Scope | Where It Lives | When It Fires | Example |
|---|---|---|---|
| **os-only** | Only in luum-agent-os repo | Only when developing the OS itself | `registration-check.sh`, `self-install.sh`, `/register-component` |
| **project** | Installed in target projects | Only in target projects | `confidentiality-enforcer.sh`, `/context-analysis`, `/threat-model` |
| **both** | In OS repo + installed in projects | Always | `secret-detector.sh`, `content-policy.sh`, `error-pipeline.sh` |

### How to Discriminate

**Hooks**: Guard clause at the top of each hook:
```bash
# OS-only hook: exit immediately if not in the OS repo
if [ ! -f "$PROJECT_DIR/hooks/self-install.sh" ]; then exit 0; fi

# Project-only hook: exit if we ARE the OS repo
if [ -f "$PROJECT_DIR/hooks/self-install.sh" ]; then exit 0; fi
```

**Skills**: `audience` field in SKILL.md frontmatter:
```yaml
audience: os       # Only available in the OS repo
audience: project  # Only available in target projects
audience: both     # Available everywhere
```

**Rules**: `scope` field:
```yaml
scope: os       # Self-hosting, dogfooding rules
scope: project  # Project-specific enforcement
scope: both     # Universal rules
```

### Classification of New Components

| Component | Scope | Rationale |
|---|---|---|
| `registration-check.sh` | os-only | Only relevant when developing the OS |
| `/register-component` | os-only | Only relevant for OS component management |
| `confidentiality-enforcer.sh` | project | Protects project IP, not relevant in OS itself |
| `predev-completeness-check.sh` | project | Checks project docs, not OS docs |
| `git-context-capture.sh` | both | Useful in any project |
| `audit-id-enricher.sh` | both | Useful in any project |
| `session-changelog.sh` | both | Useful in any project |
| `/context-analysis` | project | Pre-dev planning for projects |
| `/threat-model` | project | Security analysis for projects |
| `self-install.sh` | os-only | Dogfooding symlink setup |
| `broken-window-policy.md` | both | Cultural rule for all development |

### Migration Impact

During the rules→hooks refactor, each migrated component gets a scope tag. The `cos-init` installer uses scope to decide what gets installed:
- `os-only` → never installed in target projects
- `project` → always installed
- `both` → always installed

## Skill Atomicity

Skills should be as atomic as possible. A skill that does 8 things is harder to test, reuse, and compose than 8 skills that each do 1 thing.

### Current Anti-Patterns

| Skill | Problem | Fix |
|---|---|---|
| `/sdd-ff` | Meta-command that chains 5+ phases | Keep as orchestrator shortcut, but each phase is its own atomic skill |
| `/execution-plan` | Does budget + phases + blockers + DoR/DoD | Could split into `/estimate-budget`, `/plan-phases`, `/identify-blockers` |
| `/audience-summaries` | Generates 8 documents | Could be invoked per-audience: `/audience-summary executive` |

### Atomicity Rules

1. **One skill = one output artifact** — if a skill writes to 3 files, consider splitting
2. **Composable** — skill A's output is skill B's input (pipeline)
3. **Independently testable** — each skill can be tested without running others first
4. **Independently invocable** — user can run just this skill, not a mandatory chain

### Skills as Building Blocks

```
/context-analysis → docs/01-context/
        ↓
/threat-model → docs/04-security/
        ↓
/competitive-research → docs/07-research/
        ↓
/execution-plan → docs/09-execution-plan/
        ↓
/audience-summaries → docs/10-summaries/
```

Each is atomic. The chain is optional — you can run `/threat-model` without `/context-analysis` if you already have context. The orchestrator composes them, but each stands alone.

### Meta-Skills (Orchestration Shortcuts)

For convenience, meta-skills chain atomic skills:
- `/project-kickoff` = `/context-analysis` → `/threat-model` → `/competitive-research` → `/execution-plan` → `/audience-summaries`
- `/sdd-ff` = `/sdd-propose` → `/sdd-spec` + `/sdd-design` → `/sdd-tasks` → `/sdd-apply` → `/sdd-verify` → `/sdd-archive`

Meta-skills are thin wrappers. All logic lives in the atomic skills.

## Expected Outcome

| Metric | Before | After |
|---|---|---|
| Rules in context (full load) | ~73K tokens | ~5K tokens |
| Rules in context (COMPACT) | ~1.5K tokens | ~500 tokens |
| Hook enforcement | ~30 hooks | ~50 hooks |
| Behavioral coverage | Same | Same (enforcement moved, not removed) |
| Agent compliance | Depends on memory | Automatic |

## Risks

1. **Some rules are nuanced** — e.g., "broken window policy" is a cultural value, not a mechanical check. Making it a hook that blocks on pre-existing test failures would be too aggressive.
2. **Rule files are documentation for humans** — even if a hook enforces the behavior, humans reading the OS need to understand WHY. Solution: keep rules as docs but don't load them into agent context (they become reference-only).
3. **Test coupling** — many behavioral tests assert that specific rules exist as .md files. These tests need updating as rules migrate.

## Behavioral Tests for the Refactor

- **M1**: After migration, `RULES-COMPACT.md` is < 500 tokens (`wc -w` < 400)
- **M2**: Every hook that replaces a rule has at least 2 behavioral tests proving it enforces the behavior
- **M3**: No rule removal reduces the number of passing tests (behavioral coverage maintained)
- **M4**: Full test suite passes after each migration batch
- **M5**: Agent context overhead at session start < 5K tokens (measured by context-watchdog)

## Dependencies

- `/register-component` (built this session) — validates consistency after each migration
- Full test suite must pass before and after each phase
- Engram session summaries capture what was migrated for cross-session continuity

## Estimated Effort

| Phase | Sessions | Model | Est. Cost |
|---|---|---|---|
| Audit | 1 | sonnet | ~$2 |
| Deduplicate | 1-2 | sonnet | ~$3-5 |
| Migrate | 2-3 | sonnet+opus | ~$5-8 |
| Slim COMPACT | 1 | sonnet | ~$2 |
| **Total** | **5-7 sessions** | — | **~$12-17** |

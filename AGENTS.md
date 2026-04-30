# Luum Agent OS — Cognitive Operating System for AI Coding Agents

> Universal instructions for any AI coding agent working on this project.
> Claude Code users: `.claude/rules/` contains the complete governance mesh.
> Full rules: `rules/RULES-COMPACT.md` | Config: `cognitive-os.yaml`

---

## Project Overview

Cognitive OS is a portable, framework-agnostic operating system for AI coding agents. It provides self-improving skills, automated quality gates, fault tolerance, SRE auto-repair, cost tracking, and squad-based agent organization for **any** project (Go, Node.js, Python, Java, Rust, or any stack).

The OS follows a 3-layer architecture: universal OS agentic primitives in `hooks/`, `rules/`, `skills/`; project-specific extensions in `{project}/.claude/`; and auto-generated config via `/cognitive-os-init`. Project-specific content is never hardcoded into the OS itself.

---

## Architecture

| Primitive | Location | Purpose |
|-----------|----------|---------|
| **Hooks** | `hooks/` | Claude Code lifecycle hooks (SessionStart, PreToolUse, PostToolUse, Stop) |
| **Rules** | `rules/` | Governance rules loaded contextually — compact index at `rules/RULES-COMPACT.md` |
| **Skills** | `skills/` | Reusable SKILL.md procedures invoked by agents |
| **Config** | `cognitive-os.yaml` | Single source of truth for phase, budget, infrastructure |
| **Engram** | MCP memory plugin | Persistent memory across sessions (decisions, bugs, discoveries) |
| **Metrics** | `.cognitive-os/metrics/*.jsonl` | JSONL append-only logs for all runtime events |
| **Lib** | `lib/` | Python modules: cost tracking, skill routing, escalation detection, etc. |
| **Templates** | `templates/` | Prompt composition templates (agent-preamble, quality-gates, error-recovery) |
| **Squads** | `squads/` | Squad YAML definitions for multi-agent team organization |

Hooks wire into the Claude Code hook system. The hook chain is: SessionStart initializes state → PreToolUse gates run before every tool call → PostToolUse validates results → Stop records session metrics.

Memory lifecycle quick map: `docs/architecture/memory-lifecycle.md`. Use it to
understand which hooks save context, which hooks recover prior state, and which
doctor proves Codex/Claude session portability.

---

## Vocabulary

### Canonical term: "agentic primitive"

The layer of OS constructs that agents compose at runtime is called **agentic primitives**. This aligns with Anthropic's published SDK vocabulary ([Agent SDK overview](https://platform.claude.com/docs/en/agent-sdk/overview), [hooks guide](https://docs.anthropic.com/en/docs/claude-code/hooks-guide), [agent skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)) and with broad industry usage (LangChain, AutoGen, Semantic Kernel all use "primitive" for atomic agentic building blocks).

| Agentic primitive | This repo's slot |
|---|---|
| Skill | `skills/` + `.cognitive-os/skills/` |
| Hook | `hooks/` |
| Rule | `rules/` |
| Agent | `agents/` |
| Subagent | spawned at runtime via the `Agent` tool |
| Memory | Engram via `mcp__plugin_engram_engram` tools |
| MCP server | configured in `.claude/settings.json` |

### Carve-out: "component" remains valid

"Component" is **not** banned — it is reserved for generic software-engineering contexts where the term is established and unambiguous:

- UI/frontend components (React, Vue, Web Components)
- Microservice components in a service mesh
- Build or test components (pytest component, Makefile component)
- Third-party library components

Within agentic-layer documentation, **always prefer "agentic primitive"** (or the specific slot name: skill, hook, rule, agent). Writing "OS component" when the referent is a skill or hook is imprecise and will confuse readers migrating from generic software-engineering backgrounds.

### Enforcement

This decision is recorded as `decision/terminology/agentic-primitives` in Engram. A future audit test (`tests/audit/test_vocabulary_agentic_primitives.py`) will flag the phrase "OS component" in `rules/`, `skills/`, `hooks/`, and `docs/` files as a vocabulary drift violation. Until that test exists, authors are expected to self-enforce.

Cross-reference: ADR-072 (`docs/adrs/ADR-072-test-lane-taxonomy.md`) uses "primitive" for lane-taxonomy entities — consistent with this decision.

---

## Build & Test

```bash
# Unit tests
python3 -m pytest tests/unit/ -v

# Behavior tests
python3 -m pytest tests/behavior/ -v

# Integration tests (requires Docker)
python3 -m pytest tests/integration/ -v

# Full suite with parallel workers
python3 -m pytest tests/ -n auto

# Hook syntax validation
bash -n hooks/*.sh

# Coverage report
bash tests/coverage-report.sh

# Install dependencies
pip install -r requirements.txt
```

Minimum coverage target: **80%** (enforced, blocks PRs below threshold).

---

## Code Style & Conventions

**Python (`lib/`, `tests/`)**
- snake_case for functions and variables; PascalCase for classes
- Type hints on all public function signatures
- Docstrings for all public APIs
- Pytest markers: `@pytest.mark.unit`, `@pytest.mark.behavior`, `@pytest.mark.integration`

**Bash hooks (`hooks/`)**
- Source `hooks/_lib/common.sh` at the top of every hook
- Use `safe-jsonl` helper for writing metrics (prevents corruption)
- Exit 0 = pass/advisory, exit 2 = BLOCK, exit 1 = error
- Every hook must handle graceful degradation if optional tools are missing

**Skills (`skills/*/SKILL.md`)**
- YAML frontmatter with `name`, `version`, `description`, `triggers` fields
- Include a contextual trigger section at the end
- Auto-generated skills have `auto-generated: true` in frontmatter

**Rules (`rules/*.md`)**
- End with a "Contextual Trigger" section listing keywords that load the rule
- Keep rules under 200 lines; split if longer
- Always-active rules are listed in `rules/RULES-COMPACT.md`

---

## Current Phase: `reconstruction`

Read from `cognitive-os.yaml → project.phase`. Current: **reconstruction**.

| Phase | Behavior |
|-------|----------|
| **reconstruction** | Rewrite non-compliant code. Break patterns if wrong. Speed > governance. |
| stabilization | Standards established. Fix remaining issues. |
| production | No breaking changes. Feature flags for risky changes. |
| maintenance | Bug fixes and security patches only. |

In **reconstruction**: even small tasks can be done directly without ceremony. Rewrite over patch.

---

## Quality Standards

### Every task MUST have acceptance criteria
```
ACCEPTANCE CRITERIA:
1. grep -rl 'term' src/ | wc -l = 0
2. go build ./... exits 0
3. go test ./... exits 0
```

### Definition of Done (by complexity)
- **Trivial** (`<3 files, <20 lines`): compiles + no lint errors
- **Small** (`1–3 files`): + existing tests pass
- **Medium** (`multi-file`): + new tests written + coverage maintained
- **Large** (`multi-service`): + 80% coverage + integration tests + adversarial review
- **Critical** (`security/payments/auth/migrations`): + security review + idempotency + audit trail + rollback tested

### Trust Report (every significant output)
```
TRUST_REPORT: SCORE=75 STATUS=MEDIUM EVIDENCE=3 UNCERTAINTIES=2
```
Score = evidence(40%) + acceptance criteria(30%) + self-awareness(20%) + proportionality(10%).
Claiming "100% confident, no uncertainties" is a RED FLAG.

---

## Key Rules (always active)

1. **No sycophancy** — lead with substance; no flattery openers ("Great question!", "Absolutely!")
2. **No incomplete code** — no TODO/FIXME comments, no stub implementations, no commented-out code blocks
3. **Broken window policy** — if you find something broken, fix it; "pre-existing" is not an excuse
4. **Credentials in env only** — never in source files, URLs, commit messages, or PR descriptions
5. **Blocked paths** — never touch `.env`, `*.key`, `*.pem`, `secrets/*`, `.git/config`
6. **License gate** — AGPL/SSPL/BSL/ELv2 are BLOCKED; MIT/Apache/BSD are safe
7. **Docs require context** — never use `sed` for Markdown; always rewrite prose with context
8. **Escalate, don't spin** — after 3 failed retries or same error twice, output `ESCALATION:` with diagnosis
9. **Model routing** — opus for architecture/debugging, sonnet for implementation, haiku for docs/archiving
10. **Reviews must find something** — "LGTM" is prohibited; every review needs at least one finding

---

## MCP Servers

No project-specific MCP servers are registered in `.claude/settings.json`. MCP servers (e2b, aguara, context7, engram) are configured per-user in `~/.claude/settings.json`. See `rules/RULES-COMPACT.md` section 17-19 for ecosystem tool integrations.

---

## Skills

Skills follow the open SKILL.md standard. Each skill lives at `skills/{name}/SKILL.md` with YAML frontmatter and step-by-step instructions. Auto-generated skills are at `skills/auto-generated/`.

Key skills: `/sdd-new`, `/sdd-apply`, `/sdd-verify`, `/scout`, `/error-analyzer`, `/agent-kpis`, `/cognitive-os-status`, `/capability-snapshot`, `/optimize-skill`, `/sandbox-sample`.

Run `/skill-registry` to regenerate the skill index at `.atl/skill-registry.md`.

---

*Phase: reconstruction | Config: `cognitive-os.yaml` | Full rules: `rules/RULES-COMPACT.md`*

---
report_type: portable-ai-primitive-standards-due-diligence
date: 2026-05-09
scope: .ai-overlay, primitive-contracts, cross-ide-adapters, agent-skills, rules-hooks-tools
status: implemented-as-generated-overlay-slice
related_adrs: [ADR-057, ADR-064, ADR-076, ADR-126, ADR-146, ADR-147, ADR-154, ADR-189, ADR-190, ADR-205, ADR-256, ADR-257]
---

# Portable AI Primitive Standards Due Diligence — 2026-05-09

## Question

Should Cognitive OS port all agentic primitives into a `.ai/` directory like the
`practica-entrevista` product overlay and treat that layout as the standard for
IDE-agnostic primitives?

## Short answer

Not as an immediate move of canonical source of truth.

The external sweep found three maturity levels:

1. **Strong standards:** `AGENTS.md`, `SKILL.md` / Agent Skills, and MCP.
2. **Strong host-specific surfaces:** Claude hooks/skills, OpenCode permissions
   and plugins, Cursor/Windsurf/Kiro/Cline/Continue rules, Copilot custom
   instructions, Amp/Qoder/Junie AGENTS-based guidance.
3. **Emerging `.ai/` overlay standard:** VERSA / dotAIslash proposes exactly the
   shape we saw in the practice repo: one `.ai/` folder, canonical primitives,
   profiles/adapters, permissions, tools, memory, and validation.

Therefore `.ai/` should become a **portable consumer overlay/export target** and
possibly a future canonical packaging surface, but `manifests/primitive-contracts.yaml`
should remain the internal source of truth until the overlay has generator,
conformance tests, round-trip checks, and consumer fleet impact proof.

## Decision pressure

The current ADR-256 implementation slices are still valid because they do not
hardcode a non-`.ai` worldview. They create the ingredients a `.ai` overlay needs:

```text
primitive-contracts.yaml
  -> primitive-interventions.jsonl
  -> codebase-itinerary.jsonl
  -> projection-fidelity report
  -> .ai overlay generator / adapters
```

What changes after this due diligence is Phase 6 priority: consumer UX should be
implemented as `.ai` overlay generation before any broad manual port.

## 40-source web sweep

This is a breadth sweep, not a full per-tool source-code audit. Its purpose is to
avoid making `.ai` / portable primitive decisions from local intuition only.

| # | Source | Surface observed | Relevance to COS |
|---:|---|---|---|
| 1 | [VERSA / dotAIslash](https://dotaislash.github.io/) | `.ai/` portable repo spec with canonical primitives, profiles, rules, agents, tools, permissions | Direct candidate for consumer overlay shape. |
| 2 | [AGENTS.md](https://github.com/agentsmd/agents.md) | Open Markdown guidance format | Strong baseline for project-level instructions. |
| 3 | [GitHub Copilot custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions) | `.github/copilot-instructions.md`, `.github/instructions`, `AGENTS.md` | Adapter target; mostly advisory. |
| 4 | [Cursor rules](https://docs.cursor.com/es/context/rules) | `.cursor/rules`, `AGENTS.md`, legacy `.cursorrules` | Adapter target; structural/advisory. |
| 5 | [Windsurf rules/memories](https://docs.windsurf.com/ro/windsurf/cascade/memories) | `.windsurf/rules/`, `AGENTS.md`, rule activation modes | Adapter target; structural/advisory plus workflow concepts. |
| 6 | [Kiro steering](https://kiro.dev/docs/steering/) | `.kiro/steering/`, `AGENTS.md`, inclusion modes | Adapter target; richer steering than plain AGENTS. |
| 7 | [Cline rules](https://docs.cline.bot/customization/cline-rules) | `.clinerules/`, Cursor/Windsurf compatibility, `AGENTS.md` | Cross-tool rule compatibility signal. |
| 8 | [Continue rules](https://docs.continue.dev/customize/rules) | `.continue/rules`, Hub rules | Adapter target; rule distribution model. |
| 9 | [OpenCode permissions](https://opencode.ai/docs/permissions/) | `permission` allow/ask/deny keyed by tools | Runtime enforcement candidate. |
| 10 | [OpenCode plugins](https://dev.opencode.ai/docs/plugins/) | plugin lifecycle including tool execution hooks | Runtime adapter candidate for primitive interventions. |
| 11 | [OpenCode agents](https://opencode.ai/docs/agents/) | agents, permissions, subagents | Agent/profile adapter evidence. |
| 12 | [Claude Code skills](https://docs.claude.com/en/docs/claude-code/skills) | `SKILL.md` folders with progressive loading | Skill contract alignment. |
| 13 | [Claude Code hooks](https://code.claude.com/docs/en/hooks) | lifecycle hooks including tool events | Native lifecycle enforcement model. |
| 14 | [Trigger.dev Skills](https://trigger.dev/docs/skills) | portable Agent Skills installable across assistants | External validation of SKILL.md portability. |
| 15 | [mdskills.ai docs](https://www.mdskills.ai/docs) | directory of skills, plugins, MCP, rules and specs | Ecosystem packaging signal. |
| 16 | [Agent Skills specification](https://agentskills.my/specification) | SKILL.md open standard, discovery/activation/resources | Strong input for skill primitive shape. |
| 17 | [agentskills GitHub](https://github.com/agentskills/agentskills) | Agent Skills spec repository | Source repo for skill standard. |
| 18 | [OpenClaw agentskills skill](https://github.com/openclaw/skills/blob/main/skills/killerapp/agentskills-io/SKILL.md) | skill that validates/publishes Agent Skills | Shows real ecosystem use. |
| 19 | [Zed ACP](https://zed.dev/acp) | Agent Client Protocol for editor/agent integration | Adapter transport candidate, not primitive registry. |
| 20 | [MCP tools](https://modelcontextprotocol.info/docs/concepts/tools/) | standard tool exposure primitive | Tool adapter boundary; not project rules. |
| 21 | [A2A specification](https://google-a2a.github.io/A2A/specification/) | agent-to-agent interoperability | Cross-agent communication, not IDE primitive projection. |
| 22 | [Qoder CLI](https://docs.qoder.com/cli/using-cli) | `AGENTS.md` memory, subagents, tools | Adapter target; AGENTS.md adoption signal. |
| 23 | [JetBrains Junie](https://www.jetbrains.com/help/ai-assistant/junie-agent.html) | `.junie/AGENTS.md`, MCP, permissions, `.aiignore` | Adapter target and `.aiignore` signal. |
| 24 | [Junie CLI](https://junie.jetbrains.com/docs/junie-cli-usage.html) | `.junie/AGENTS.md` persistent guidance | CLI adapter signal. |
| 25 | [Kimi CLI](https://www.kimi.com/code/docs/en/kimi-cli.html) | ACP mode | ACP adapter candidate. |
| 26 | [Qwen Code MCP docs](https://qwenlm.github.io/qwen-code-docs/en/users/features/mcp/) | MCP integration | Tool-surface adapter candidate. |
| 27 | [Amp manual](https://ampcode.com/manual) | hierarchical `AGENTS.md` locations | Strong AGENTS.md multi-scope signal. |
| 28 | [Android Studio Gemini agent files](https://developer.android.com/studio/gemini/agent-files) | `AGENTS.md` plus `GEMINI.md` precedence | Gemini adapter precedence rule. |
| 29 | [Codex AGENTS.md docs](https://github.com/openai/codex/blob/main/docs/agents_md.md) | Codex AGENTS.md discovery/scoping | Codex adapter baseline. |
| 30 | [Aider conventions](https://aider.chat/docs/usage/conventions.html) | `--read CONVENTIONS.md` guidance | Advisory adapter path; repo-map adjacent. |
| 31 | [Goose docs](https://goose-docs.ai/) | MCP-heavy local agent | Runtime/tool ecosystem signal. |
| 32 | [OpenLeash](https://openleash.ai/) | pre-action authorization sidecar for agents | Candidate pattern for intervention ledger authorization. |
| 33 | [APort / OAP explainer](https://aport.io/blog/what-is-aport-pre-action-authorization-ai-agents/) | Open Agent Passport idea | Candidate pattern for signed authorization. |
| 34 | [Veto](https://veto.so/) | runtime action authorization | Candidate guardrail pattern. |
| 35 | [Open Agent Passport paper](https://arxiv.org/abs/2603.20953) | deterministic pre-action authorization | Research basis for intervention ledger hardening. |
| 36 | [SkillsBench](https://arxiv.org/abs/2602.12670) | measuring skill effectiveness | Future primitive benchmark input. |
| 37 | [Agent Skills architecture paper](https://arxiv.org/abs/2602.12430) | skills architecture, acquisition, security | Skill lifecycle/security input. |
| 38 | [Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988) | AGENTS.md effect on coding agents | Evidence for project-level context files. |
| 39 | [Impact of AGENTS.md efficiency](https://arxiv.org/abs/2601.20404) | runtime/token impact of AGENTS.md | Context budget risk input. |
| 40 | [Context Engineering for AI Agents](https://arxiv.org/abs/2510.21413) | context files and tool-specific formats | Supports context portability premise. |
| 41 | [Configuring Agentic AI Coding Tools](https://openreview.net/pdf/ae0f92b7a4b3e8628d1c622654b9fe46d69f03bb.pdf) | empirical exploration of coding-agent config | Config-sprawl evidence. |
| 42 | [Sema Code](https://arxiv.org/abs/2604.11045) | decoupling agent engine from clients | Supports adapter boundary thinking. |

## What the sweep changes

### `.ai/` is not just local inspiration

The practice repo's `.ai` pattern now has an external analog in VERSA. COS should
therefore treat `.ai` as a first-class export target to evaluate, not merely a
local convenience layout.

### `AGENTS.md` is the strongest cross-tool instruction anchor

Many hosts either support `AGENTS.md` directly or refer to it as a compatibility
format. COS adapters should emit AGENTS.md-compatible guidance where possible,
even when also generating host-native rules.

### `SKILL.md` is the strongest portable skill primitive

COS already uses SKILL.md. The gap is not format adoption; the gap is contract
coverage, conformance, security gate, license gate, and activation evidence.

### Runtime enforcement remains host-specific

Rules/instructions are portable. Enforcement is not. OpenCode permissions/plugins,
Claude hooks, CI wrappers, and future OAP/OpenLeash-style authorization are
different enforcement surfaces. A `.ai` overlay must declare fidelity honestly.

## Rejected immediate approach

Do not move every primitive source file into `.ai/` in one commit. Generate a complete `.ai` overlay first, then decide whether canonical migration is justified.

Reasons:

- It would break existing hook/settings generation, tests, docs, and consumer
  update flows.
- Many primitives are executable scripts, not only instructions; `.ai` must point
  to or wrap them before it owns them.
- VERSA is promising but not yet proven inside this repo's harness matrix.
- A direct move would confuse canonical source of truth before conformance tests
  exist.

## Recommended target architecture

```text
COS internal source of truth
  manifests/primitive-contracts.yaml
  hooks/ skills/ rules/ scripts/
          |
          v
.ai overlay generator
  .ai/context.json
  .ai/primitives/{hooks,skills,rules,workflows,tools}/...
  .ai/profiles/{claude,codex,cursor,windsurf,copilot,kiro,opencode}/...
  .ai/adapters/{claude-code,codex,cursor,windsurf,copilot,kiro,opencode}/...
  .ai/logs/schema/*.json
          |
          v
host-specific projection
  AGENTS.md, SKILL.md dirs, .cursor/rules, .windsurf/rules,
  .github/copilot-instructions.md, .kiro/steering,
  opencode.json/plugins, Claude/Codex hooks, CI scripts
          |
          v
runtime evidence
  primitive-interventions.jsonl
  codebase-itinerary.jsonl
  projection-fidelity report
  trace_joiner
```

## New work items before port-all

1. Add ADR-258 for `.ai` portable primitive overlay.
2. Add `.ai` overlay manifest/generator that exports all lifecycle primitives as generated reference rows and enriches the five ADR-257 contracts.
3. Add conformance tests that compare `.ai/primitives` back to
   `manifests/primitive-contracts.yaml` and `manifests/primitive-lifecycle.yaml`.
4. Add adapter report proving generated `.ai` profiles map to current harness
   projection surfaces.
5. Then enrich every lifecycle primitive into a full portable contract in batches.

## Verdict

Adopt `.ai` as the **portable overlay/export format** for Cognitive OS. Do not
make `.ai` the internal canonical source yet. The standard candidate is real
enough to deserve a first-class ADR and generator, but not mature enough to
justify a mass source-tree move before conformance proof.

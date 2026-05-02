# Harness Engineering in Cognitive OS

This document defines how Cognitive OS interprets harness engineering and where
that discipline is implemented in this repository.

Harness engineering means designing the environment around an AI coding model so
that the model can work as a governed software agent instead of an unconstrained
chatbot. The harness supplies context, tools, memory, verification, and runtime
boundaries while allowing the underlying model or provider to change.

For Cognitive OS, the harness is not a single vendor product. The harness is the
portable operating layer made of agentic primitives, projected into Claude Code,
Codex, Cursor, and future runtimes through explicit drivers.

## Operating Thesis

Cognitive OS should make coding agents:

1. **governable** — policy, security, scope, and quality are explicit;
2. **verifiable** — claims must be backed by executable evidence;
3. **portable** — behavior is authored once and projected through harness
   drivers;
4. **context-efficient** — durable artifacts and retrieval avoid stuffing every
   rule, log, and decision into the model context;
5. **progressive** — the smallest useful harness should work before optional
   extensions are enabled.

The last point is important. A stronger harness is not necessarily a larger
harness. Over-specialized tools, excessive rules, and large static instruction
payloads can reduce agent performance. Cognitive OS should prefer simple,
composable primitives and add specialization only when measured behavior justifies
it.

## Pillar Matrix

| Harness engineering pillar | Cognitive OS implementation | Status | Risk | Next pressure point |
|---|---|---|---|---|
| Repository as system | `AGENTS.md`, `cognitive-os.yaml`, `rules/`, `skills/`, `hooks/`, `templates/`, `.cognitive-os/`, `manifests/harness-profiles.yaml` | Strong | Entry path can feel large | Keep the minimal profile obvious and executable |
| Progressive context | `rules/RULES-COMPACT.md`, `.codex/project-index.md`, query-tailored context injection, context diet | Strong | Too many rules can still leak into active context | Prefer task-tailored loading and compact maps |
| Durable memory | Engram protocol, session summaries, git context capture, changelogs, metrics JSONL | Strong | MCP availability differs by host; shell hooks cannot directly call in-process MCP tools | Keep repository artifacts primary and MCP memory opportunistic |
| Verification | tests, quality gates, `auto-verify`, DoD gates, trust reports, proof paths | Strong | Verification can become slow or noisy | Maintain fast lanes and explicit acceptance criteria |
| Multi-agent orchestration | `cos-agent`, sprint primitives, squads, review-agent pattern, subagent context injection | Medium/strong | Native subagent features differ by harness; coding tasks often have dependency coupling | Use subagents for bounded sidecar work and persist outputs as artifacts |
| Tool surface | Unix/file-system primitives, hooks, MCP, skills, external tools | Medium | Hyper-specialized tools can degrade behavior | Default to simple shell/file/search tools; justify specialized tools with evidence |
| Harness portability | `lib/harness_adapter`, settings drivers, Codex/Claude hook projections, cross-harness authoring rules | Medium/strong | Driver parity is uneven across event surfaces | Treat harnesses as drivers and document capability differences honestly |
| Self-improvement | ADRs, Engram learnings, failure monitors, skill optimization, governed self-improvement plans | Medium | Self-modifying prompts/rules can drift without review | Require artifact, test, and approval paths before promotion |

## Minimal Harness Profile

The minimum useful Cognitive OS harness should fit in a short operator path. Its
required hook spine is `hooks/session-init.sh`, `hooks/auto-verify.sh`, and
`hooks/session-learning.sh`; its required command spine is
`scripts/cos-doctor-harness.sh`, `scripts/measure_harness_profiles.py`,
`scripts/cos_sprint.py`, `bin/cos-agent`, and `bin/cos-skill`.

```text
1. Read AGENTS.md.
2. Load cognitive-os.yaml.
3. Run `cos init-check` or `cos doctor harness`.
4. Select one bounded task with explicit acceptance criteria.
5. Implement using simple file-system and shell primitives first.
6. Verify with the smallest trustworthy test lane.
7. Persist progress to repository artifacts and Engram when available.
8. Close with a session summary and next steps.
```

A minimal installation should not require understanding every hook, skill, or
future architecture layer. Optional subsystems should remain discoverable without
becoming mandatory context. The executable contract for this profile lives in
`manifests/harness-profiles.yaml`; `scripts/cos-doctor-harness.sh` validates the
readiness path, and `scripts/measure_harness_profiles.py` compares the minimal
contract against full Claude/Codex projections.

## Context and Memory Contract

The model context window is working memory, not long-term storage. Cognitive OS
uses three levels of memory:

1. **Repository artifacts** — docs, manifests, metrics, changelogs, ADRs, and
   generated summaries. These are the primary durable memory because every
   harness can read files.
2. **Runtime metrics** — append-only JSONL records under `.cognitive-os/metrics/`
   and related session folders. These give hooks and doctors a machine-readable
   audit trail.
3. **MCP memory** — Engram observations, session summaries, and retrieval. This
   is valuable when available, but the SO must degrade gracefully without it.

Subagents should not rely on chat relay for important findings. When a subagent
produces work that another agent or future session needs, it should leave a
small durable artifact or structured summary and return only a lightweight
reference to the orchestrator.

## Multi-Agent Guidance

Cognitive OS uses the orchestrator-worker pattern, but should avoid treating
multi-agent execution as universally better.

Use subagents when:

- the task is independent or can be bounded by a clear file/work scope;
- exploration would flood the main context with logs, search results, or large
  files;
- parallel work produces enough value to justify higher token and coordination
  cost;
- review or verification can run independently from implementation.

Avoid subagents when:

- the next local action is blocked on the delegated result;
- the task requires constant shared state;
- the prompt would need to include most of the parent context;
- the subagent would be asked to self-approve its own implementation.

For coding work, prefer disjoint write scopes and durable output files over
long chat summaries. The orchestrator is responsible for integration and final
verification.

## Verification Doctrine

An agent should not declare work complete just because the code looks plausible.
Completion requires evidence proportional to task risk:

- acceptance criteria are explicit;
- relevant tests or checks were run;
- failures are reported, not hidden;
- generated claims can be reproduced from logs, commands, or artifacts;
- significant work ends with a trust report or equivalent evidence summary.

For UI work, browser or end-to-end checks should be preferred when unit tests
cannot prove the user-visible behavior. For infrastructure, auth, payments,
security, or migrations, verification must include rollback/idempotency/security
considerations appropriate to the risk.

## Tooling Discipline

The default tool model should be small and legible:

- read files;
- search files;
- list directories;
- run bounded shell commands;
- edit files;
- run tests;
- write durable summaries.

Specialized tools are allowed when they reduce risk or improve measurable
outcomes. They should have clear descriptions, scoped permissions, and tests or
manual proof paths. If a specialized tool merely hides a simple shell/file-system
operation, prefer the simpler primitive.

## Relation to Existing Documents

This document is the synthesis layer. Details live in narrower architecture docs
and ADRs:

- [Cross-Harness Authoring](cross-harness-authoring.md) — behavior once, driver
  projection second.
- [Cross-Runtime Portability](cross-runtime-portability.md) — kernel plus driver
  model for supported harnesses.
- [Memory Lifecycle](memory-lifecycle.md) — hooks, Engram, session summaries, and
  recovery.
- [Harness Driver Parity](harness-driver-parity.md) — honest driver capability
  comparison.
- [Skills and Rules Portability Gap](skills-rules-portability-gap.md) — remaining
  `.claude/` gravity and canonicalization work.
- [ADR-036: Sprint Orchestration Primitives](../adrs/ADR-036-sprint-orchestration-primitives.md)
  — durable multi-agent sprint artifacts.
- [ADR-057: Cross-Harness Authoring and Driver Projection](../adrs/ADR-057-cross-harness-authoring-and-driver-projection.md)
  — accepted authoring discipline.
- [ADR-064: Harness-Agnostic Cognitive OS](../adrs/ADR-064-harness-agnostic-cognitive-os.md)
  — accepted harness abstraction surfaces.

## External Evidence

The current stance is aligned with several public engineering references:

- Anthropic, [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents): use initializer/coding-agent roles, `init.sh`, feature lists, progress files, one-feature-at-a-time work, and explicit testing.
- Anthropic, [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system): orchestrator-worker architecture, separate context windows, memory for plans, and careful delegation.
- Anthropic Claude Code docs, [Subagents](https://code.claude.com/docs/en/sub-agents): subagents preserve context by doing side work in their own windows and returning summaries.
- Anthropic, [Building agents with the Claude Agent SDK](https://claude.com/blog/building-agents-with-the-claude-agent-sdk): file and folder structure is a form of context engineering; start with agentic search before heavier semantic systems.
- Vercel, [We removed 80% of our agent's tools](https://vercel.com/blog/we-removed-80-percent-of-our-agents-tools): simpler file-system tooling outperformed a more specialized agent architecture in their benchmark.
- GitHub community issue, [anthropics/claude-code#35296](https://github.com/anthropics/claude-code/issues/35296): anecdotal reports of context degradation before nominal context exhaustion. Treat as community evidence, not an official Anthropic guarantee.

## Anti-Patterns

Avoid these patterns when evolving Cognitive OS:

1. **Harness maximalism** — adding hooks, skills, MCPs, or rules because they are
   possible rather than because they improve a measured outcome.
2. **Context stuffing** — loading every policy and historical note into every
   session or subagent.
3. **Chat-only state** — leaving task status, decisions, and test evidence only
   in the conversation.
4. **Self-approval** — letting an implementation agent mark its own work done
   without independent verification.
5. **Driver masquerade** — describing a Claude-only or Codex-only behavior as
   portable without naming the projection gap.
6. **Opaque specialization** — hiding simple file-system work behind a fragile
   bespoke tool.

## Acceptance Criteria for Harness Changes

A new or modified harness primitive should satisfy these checks before it is
advertised as durable:

1. The behavioral core is documented independently of any single harness.
2. Driver-specific projection is explicit when needed.
3. The smallest trustworthy verification lane is named.
4. Context impact is considered, especially for always-loaded rules or prompts.
5. Memory/output artifacts are defined for cross-session continuity.
6. Failure behavior is clear: block, warn, retry, degrade, or escalate.
7. Product messaging does not claim portability beyond tested driver behavior.

## Closed Gaps

- `manifests/harness-profiles.yaml` defines the official `minimal` and `full`
  harness profiles.
- `cos init-check` and `cos doctor harness` expose the readiness check normally
  provided by ad hoc project-level `init.sh` scripts.
- `cos measure harness-profiles` measures minimal vs full hook surface without
  mutating active settings.
- `cos sprint run --dispatch` executes sprint tasks through the portable
  `cos-agent` surface and records launch/completion events.
- `tests/contracts/test_harness_engineering_docs.py` protects this document and
  its docs-index link.

## Continuing Guardrails

These are ongoing operating checks, not unimplemented scope from this slice:

- Keep auditing always-on hook and rule count against the minimal-context
  principle.
- Prefer real non-Claude agent runs when expanding dispatch coverage so the
  stubbed integration path does not become the only evidence.

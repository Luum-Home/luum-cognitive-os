---
cluster: agent-wrappers-templates
date: 2026-05-06
phase: shallow
budget_max_tool_calls: 45
tool_calls_used: 4
count: 15
counts:
  promote: 2
  hold: 1
  reject: 12
  total: 15
---

# Cluster: agent-wrappers-templates (shallow)

Theme: claude/agent CLI wrappers, template starter kits, lab-grade agent harnesses. Hypothesis going in: most are thin wrappers over claude-code, opencode/openclaw, or generic LLM CLIs with no defensible delta.

Outcome: hypothesis confirmed. 12/15 rejected. Two primitives worth Phase-2 deep dive: coder/agentapi (HTTP-normalization across agent CLIs) and oktsec (signed/auditable agent-to-agent message bus). One on hold pending closer look: mco-org/mco.

---

## Per-repo

### 1. AutoMaker-Org/automaker
- URL: github.com/AutoMaker-Org/automaker
- License: MIT (LICENSE file; GitHub reports NOASSERTION because README "no longer maintained" notice precedes the license block)
- Stars: 3,141
- Last commit: 2026-03-15
- Primary language: TypeScript
- Purpose: Agent-based automation toolkit (broad scope, claude-code adjacent).
- Verdict: reject
- Rationale: Repo self-declares "no longer actively maintained." We already integrate via automaker-bridge skill where useful; pulling unmaintained TS into our Python/Go core adds risk with no upside.

### 2. CamiloAndresGTRUniandes/lucy-ai
- URL: github.com/CamiloAndresGTRUniandes/lucy-ai
- License: MIT
- Stars: 15
- Last commit: 2026-05-05
- Primary language: Shell
- Purpose: Bot config + skill set for openclaw harness.
- Verdict: reject
- Rationale: Personal config bundle, single example. Starter kit, not primitive. No reusable abstractions.

### 3. code-yeongyu/oh-my-openagent
- URL: github.com/code-yeongyu/oh-my-openagent
- License: Sustainable Use License (non-OSI, source-available, restricts commercial competing use; SPDX: NOASSERTION)
- Stars: 56,001
- Last commit: 2026-05-06
- Primary language: TypeScript
- Purpose: "Best agent harness," fork of opencode tooling.
- Verdict: reject
- Rationale: Sustainable Use License is non-commercial / anti-competitive — fails our license-policy filter (treat as non-permissive). Patterns may inspire but we cannot adopt code.

### 4. coder/agentapi
- URL: github.com/coder/agentapi
- License: MIT
- Stars: 1,373
- Last commit: 2026-04-13
- Primary language: Go
- Purpose: HTTP API in front of Claude Code, Goose, Aider, Gemini, Amp, Codex — uniform message/event protocol across heterogeneous agent CLIs.
- Verdict: promote
- Rationale: Solves a real primitive we re-implement piecemeal in lib/dispatch.py and lib/harness_adapter/. Go, MIT, active. Worth a Phase-2 deep read on event schema and process supervision; could feed ADR-033 harness-agnostic event capture.

### 5. coleam00/context-engineering-intro
- URL: github.com/coleam00/context-engineering-intro
- License: MIT
- Stars: 13,275
- Last commit: 2026-03-16
- Primary language: Python
- Purpose: Educational starter showing how to do "context engineering" with Claude Code.
- Verdict: reject
- Rationale: Tutorial / starter kit, single worked example. Not a primitive. Concepts already absorbed into our SDD pipeline and skill catalog.

### 6. floci-io/floci
- URL: github.com/floci-io/floci
- License: MIT
- Stars: 4,362
- Last commit: 2026-05-06
- Primary language: Java
- Purpose: Local AWS emulator (LocalStack-style).
- Verdict: reject
- Rationale: Misclassification — floci is a cloud emulator, not an agent wrapper or template. Off-cluster. Flag for re-cluster review.

### 7. github/spec-kit
- URL: github.com/github/spec-kit
- License: MIT
- Stars: 92,727
- Last commit: 2026-05-05
- Primary language: Python
- Purpose: GitHub's official Spec-Driven Development toolkit.
- Verdict: reject
- Rationale: Direct overlap with our own SDD pipeline (sdd-init/explore/propose/spec/design/tasks/apply/verify/archive) which is more complete and engram-backed. Could be referenced for compatibility but not adopted; we'd be the upstream-equivalent here.

### 8. gsd-build/get-shit-done
- URL: github.com/gsd-build/get-shit-done
- License: MIT
- Stars: 60,274
- Last commit: 2026-05-06
- Primary language: JavaScript
- Purpose: Meta-prompting + context-engineering + SDD layer for Claude Code by TÂCHES.
- Verdict: reject
- Rationale: Thin wrapper around claude-code with meta-prompt templates; no clear delta beyond what our prompt-composition + SDD pipeline already cover. Star count signals popularity, not novelty.

### 9. heypinchy/pinchy
- URL: github.com/heypinchy/pinchy
- License: AGPL-3.0
- Stars: 155
- Last commit: 2026-05-06
- Primary language: TypeScript
- Purpose: Self-hosted enterprise agent platform on top of OpenClaw.
- Verdict: reject
- Rationale: AGPL-3.0 — blocked by license-policy. Cannot adopt code or patterns into MIT/Apache codebase without contamination concerns.

### 10. kittors/CliRelay
- URL: github.com/kittors/CliRelay
- License: MIT
- Stars: 639
- Last commit: 2026-05-06
- Primary language: Go
- Purpose: Wraps Gemini CLI / Codex / Claude Code / Qwen Code as an OpenAI-compatible HTTP API to surface free-tier access.
- Verdict: reject
- Rationale: Functional overlap with coder/agentapi (#4) but goal is provider-arbitrage, not orchestration primitive. Conflicts with our lib/dispatch.py provider routing and ToS posture (free-tier proxying is grey-zone). agentapi is the better candidate for the same shape.

### 11. lgcyaxi/oh-my-claude
- URL: github.com/lgcyaxi/oh-my-claude
- License: NONE (no LICENSE file)
- Stars: 0
- Last commit: 2026-04-25
- Primary language: TypeScript
- Purpose: Multi-agent orchestration plugin for Claude Code with DeepSeek/GLM/MiniMax.
- Verdict: reject
- Rationale: No license = all rights reserved by default. Cannot legally adopt. Also 0 stars and thin wrapper around claude-code with no clear delta.

### 12. mco-org/mco
- URL: github.com/mco-org/mco
- License: MIT
- Stars: 333
- Last commit: 2026-03-18
- Primary language: Python
- Purpose: Neutral orchestration layer for multiple agent CLIs (Claude Code, Codex, Gemini, OpenCode, Qwen).
- Verdict: hold
- Rationale: Theme overlaps our orchestrator and lib/dispatch.py heavily. Worth a quick Phase-2 read to confirm whether any abstractions (IDE-side adapters, neutral message envelope) are cleaner than what we have. Risk: reinvention pull.

### 13. oktsec/oktsec
- URL: github.com/oktsec/oktsec
- License: Apache-2.0
- Stars: 11
- Last commit: 2026-05-01
- Primary language: Go
- Purpose: Security layer for agent-to-agent communication — message signing, inspection, audit log, single binary, no LLM.
- Verdict: promote
- Rationale: Off-theme for "wrappers/templates" but a genuine primitive: complements our agent-security + audit-trail rules and could harden cross-instance Engram replication (ADR-141). Apache-2.0, Go, recent. Worth Phase-2 deep dive even at low star count — small repos in security primitives often win on signal.

### 14. onecli/onecli
- URL: github.com/onecli/onecli
- License: Apache-2.0
- Stars: 2,091
- Last commit: 2026-05-05
- Primary language: TypeScript
- Purpose: Open-source vault that brokers service access for AI agents without exposing keys.
- Verdict: reject
- Rationale: Off-cluster (secrets vault, not wrapper/template). License OK but route through a different cluster (security/secrets) if we want to evaluate; not part of this scout's theme.

### 15. vercel-labs/coding-agent-template
- URL: github.com/vercel-labs/coding-agent-template
- License: Apache-2.0
- Stars: 1,700
- Last commit: 2026-04-13
- Primary language: TypeScript
- Purpose: Multi-agent coding platform template using Vercel Sandbox + AI Gateway.
- Verdict: reject
- Rationale: Template/starter kit tightly coupled to Vercel Sandbox + AI Gateway runtime. Not a portable primitive; vendor-bound. Adoption would impose Vercel infra dependency.

---

## Phase 2 candidates

1. coder/agentapi — HTTP normalization across agent CLIs (Claude Code, Goose, Aider, Gemini, Amp, Codex). Read for: event schema, process supervision pattern, comparison with our lib/harness_adapter/ (ADR-033). Go/MIT/active.

2. oktsec/oktsec — Signed, audited agent-to-agent message bus. Read for: signing protocol, audit log shape, applicability to ADR-141 Engram Cloud replication and our agent-security TTL/secret-blocking layer. Apache-2.0/Go/active, low stars but high signal.

3. mco-org/mco (hold/conditional) — IDE-neutral orchestration layer. Quick read only to confirm there is/isn't a cleaner abstraction than our orchestrator before committing more time.

## Misclassifications flagged

- floci-io/floci is an AWS local emulator (LocalStack analog), not an agent wrapper. Re-cluster.
- onecli/onecli is a vault, off-theme for wrappers/templates. Re-cluster to security/secrets.
- oktsec/oktsec is also off-theme strictly speaking (security primitive, not wrapper) but kept and promoted due to clear value.

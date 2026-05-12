---
cluster: cli-claw-derivatives
date: 2026-05-06
phase: shallow
theme: claude-code derivatives + opencli + claw forks (lookalike personal-AI / coding-agent harnesses)
input_file: .cognitive-os/runtime/repo-scout-batch-2026-05-06/cluster-cli-claw-derivatives.txt
input_count: 19
unique_repos: 18
counts:
  total: 18
  passes_to_deep: 2
  monitor: 10
  reject: 6
notes:
  - OpenClaw/OpenClaw and openclaw/openclaw collapse to one repo (GitHub case-collapse) → counted once.
  - Gitlawb/openclaude LICENSE explicitly states "derived from Anthropic's Claude Code CLI" (proprietary) → reject (legal), per constraint.
  - kirodotdev/Kiro has no LICENSE file → reject (no usable license).
  - codeking-ai/cligate is AGPL-3.0 → reject per AGPL exclusion.
  - warengonzaga/tinyclaw is GPL-3.0 → reject (copyleft, not in MIT/Apache/BSD/ISC pass list).
  - nashsu/opencli-rs-skill (autocli-skill) has no license → reject.
  - "Claw" naming cluster is dominated by lookalike/clone harnesses competing with claude-code; passes gate on extractable primitive, not naming/popularity.
  - OpenHands NOASSERTION resolves to MIT (with separate enterprise/ subtree) → eligible.
---

# Cluster: cli-claw-derivatives — Shallow Audit

Theme: Lookalike "claw"-named coding-agent harnesses, claude-code derivatives, and the OpenCLI sub-cluster. Names are largely riffs on a common viral template; many are clones with thin variations. Filter: derivation from proprietary Claude Code → legal reject; no/copyleft license → reject; otherwise gate on extractable primitive (sandbox model, hooks, routing, memory, container isolation, hardware-targeted runtime).

## Repos

### 1. Gitlawb/openclaude
- URL: https://github.com/Gitlawb/openclaude
- License: NOASSERTION (LICENSE declares "code derived from Anthropic's Claude Code CLI", proprietary; MIT only on contributor modifications)
- Stars: 25,952
- Last commit: 2026-05-06
- Primary language: TypeScript
- One-line purpose: Self-described open Claude-Code-like harness ("runs anywhere, uses anything").
- Triage verdict: **reject**
- Rationale: LICENSE explicitly admits derivation from proprietary Claude Code source. Per cluster constraint, derivatives of proprietary Claude Code are legal-reject regardless of stars/activity. Cannot adopt code or patterns without crossing Anthropic's commercial terms.

### 2. InternLM/WildClawBench
- URL: https://github.com/InternLM/WildClawBench
- License: MIT
- Stars: 337
- Last commit: 2026-04-27
- Primary language: Python
- One-line purpose: In-the-wild benchmark for AI agents in the OpenClaw environment.
- Triage verdict: **monitor**
- Rationale: Benchmark, not harness. MIT and active. Could feed our eval/benchmark surface (alongside RAGAS/DeepEval/Promptfoo). Not a primitive source, but worth tracking as a potential evaluation dataset for agent harnesses targeting "claw"-style task suites. No urgency for deep dive.

### 3. openclaw/openclaw (a.k.a. OpenClaw/OpenClaw)
- URL: https://github.com/openclaw/openclaw
- License: MIT
- Stars: 368,765
- Last commit: 2026-05-06
- Primary language: TypeScript
- One-line purpose: Personal-AI assistant ("any OS, any platform") — flagship of the "claw" lookalike cluster.
- Triage verdict: **passes-to-deep**
- Rationale: Massive, MIT-licensed, very active. Dominates this naming cluster and is the upstream that several others (zeroclaw, nanoclaw, picoclaw, tinyclaw, zeptoclaw) explicitly reference or fork against. Worth a deep pass to identify whether it carries genuinely novel primitives (provider-swapping, channel abstraction, sandbox model) vs. just a populist veneer over claude-code patterns. High blast radius if we extract from it; verify provenance carefully in deep phase.

### 4. OpenHands/OpenHands
- URL: https://github.com/OpenHands/OpenHands
- License: NOASSERTION → MIT (LICENSE: MIT for everything outside `enterprise/`, separate license for `enterprise/`)
- Stars: 72,702
- Last commit: 2026-05-06
- Primary language: Python
- One-line purpose: AI-driven development platform (formerly OpenDevin).
- Triage verdict: **passes-to-deep**
- Rationale: Mature, large, MIT-on-core agent harness. Established sandbox/runtime separation, container-isolated execution, multi-agent orchestration patterns. Direct overlap with our agent runtime concerns (impact-analysis, sandbox-sampling, blast-radius). MIT licensing on the non-enterprise tree makes both code and patterns adoptable. One of the few "real" entries in this cluster.

### 5. codeking-ai/cligate
- URL: https://github.com/codeking-ai/cligate
- License: AGPL-3.0
- Stars: 55
- Last commit: 2026-05-03
- Primary language: JavaScript
- One-line purpose: Multi-protocol AI proxy for Claude Code / Codex / Gemini / OpenClaw with account pooling.
- Triage verdict: **reject**
- Rationale: AGPL-3.0 is in the cluster's reject list. Concept (multi-CLI proxy / account pooling) overlaps with our llm-dispatch (ADR-049) but we cannot adopt code or do clean-room from AGPL surface without legal review. Skip.

### 6. dollspace-gay/OpenClaudia
- URL: https://github.com/dollspace-gay/OpenClaudia
- License: MIT
- Stars: 70
- Last commit: 2026-05-03
- Primary language: Rust
- One-line purpose: Open-source agentic coding harness (Rust).
- Triage verdict: **monitor**
- Rationale: MIT, Rust, active, but small (70 stars) and self-description gives no extractable primitive at surface. Rust harness is interesting reference but not unique vs. ironclaw / zeptoclaw / zeroclaw which dominate the Rust slice of this cluster. Re-evaluate if it surfaces a distinct architectural idea.

### 7. kirodotdev/Kiro
- URL: https://github.com/kirodotdev/Kiro
- License: none (no LICENSE file)
- Stars: 3,616
- Last commit: 2026-04-08
- Primary language: TypeScript
- One-line purpose: Agentic IDE working "alongside you from prototype to production".
- Triage verdict: **reject**
- Rationale: No license → no permission to adopt code or apply clean-room with confidence. Without explicit grant, default copyright forbids reuse. Skip until/unless a license is added.

### 8. nashsu/AutoCLI (alias opencli-rs)
- URL: https://github.com/nashsu/AutoCLI
- License: Apache-2.0
- Stars: 2,561
- Last commit: 2026-04-20
- Primary language: Rust
- One-line purpose: Rust CLI for fetching info from 55+ sites and controlling Electron desktop apps for AI agents.
- Triage verdict: **monitor**
- Rationale: Apache-2.0, active, distinct primitive (web/desktop site-adapter library, similar to a tool-use plugin pack). Useful as a reference for how to build an extensible site/tool adapter registry, but not a harness. Track for future "tool surface" expansion; not deep-pass priority right now.

### 9. nashsu/autocli-skill (alias opencli-rs-skill)
- URL: https://github.com/nashsu/autocli-skill
- License: none
- Stars: 809
- Last commit: 2026-04-20
- Primary language: (unspecified)
- One-line purpose: Skill pack for ClaudeCode/OpenClaw/Agent — natural-language fetch over 55+ platforms via Chrome session.
- Triage verdict: **reject**
- Rationale: No license file. Cannot adopt code or skill manifests without explicit grant. Companion to AutoCLI (which is Apache-2.0); if we want the patterns, look at AutoCLI's sources. Skip.

### 10. nearai/ironclaw
- URL: https://github.com/nearai/ironclaw
- License: Apache-2.0
- Stars: 12,145
- Last commit: 2026-05-05
- Primary language: Rust
- One-line purpose: Privacy-, security-, extensibility-focused Agent OS (Rust).
- Triage verdict: **monitor**
- Rationale: Apache-2.0, sizeable, active, and explicitly positions on "privacy + security + extensibility" — exactly our axes (engram-api-safety, agent-security, content-policy). Could be a reference for extension/plugin architecture in Rust. Not deep-pass yet because shallow signal doesn't yet show a uniquely extractable primitive vs. zeroclaw/zeptoclaw. Re-evaluate if its plugin model is documented.

### 11. nullclaw/nullclaw
- URL: https://github.com/nullclaw/nullclaw
- License: MIT
- Stars: 7,412
- Last commit: 2026-05-05
- Primary language: Zig
- One-line purpose: "Fastest, smallest, fully autonomous AI assistant infrastructure" written in Zig.
- Triage verdict: **monitor**
- Rationale: Zig is the only differentiator vs. a dozen Rust/TS lookalikes. MIT and active. Zig adoption is too narrow for direct integration into our harness, but as a reference implementation of a minimal autonomous loop in a non-GC language it is occasionally interesting. Low priority.

### 12. openagen/zeroclaw
- URL: https://github.com/openagen/zeroclaw
- License: Apache-2.0
- Stars: 1,863
- Last commit: 2026-03-15
- Primary language: Rust
- One-line purpose: Fork of zeroclaw — "deploy anywhere, swap anything".
- Triage verdict: **reject**
- Rationale: Fork (per `fork: true`). Not the canonical zeroclaw-labs upstream. ~1.7 months stale vs. upstream which committed today. No reason to track a downstream fork when the upstream zeroclaw-labs/zeroclaw is in this same cluster, more popular, and actively maintained. Skip.

### 13. qhkm/zeptoclaw
- URL: https://github.com/qhkm/zeptoclaw
- License: Apache-2.0
- Stars: 618
- Last commit: 2026-05-05
- Primary language: Rust
- One-line purpose: Local-first, sandboxed, single-binary Rust personal-AI infrastructure.
- Triage verdict: **monitor**
- Rationale: Apache-2.0, active. Phrasing ("local-first, sandboxed autonomy, single binary") aligns with our sandbox/private-mode/engram-api-safety surface. Smaller than zeroclaw/ironclaw but explicitly local-first which is closer to our use case than cloud-hosted variants. Watch for a clearer sandbox model write-up before promoting to deep.

### 14. qwibitai/nanoclaw
- URL: https://github.com/qwibitai/nanoclaw
- License: MIT
- Stars: 28,615
- Last commit: 2026-05-05
- Primary language: TypeScript
- One-line purpose: Container-isolated alternative to OpenClaw with messaging-app integrations and Anthropic Agents SDK.
- Triage verdict: **monitor**
- Rationale: MIT, very active, large. Container-as-sandbox model + messaging-channel adapters are interesting, and direct Anthropic Agents SDK use is a reference for our llm-dispatch alignment. Not promoted to deep because the surface area is mostly integration glue (chat platforms) rather than a primitive we'd extract. Worth tracking; revisit if/when we expand into channel surfaces.

### 15. sipeed/picoclaw
- URL: https://github.com/sipeed/picoclaw
- License: MIT
- Stars: 28,772
- Last commit: 2026-05-06
- Primary language: Go
- One-line purpose: Tiny, fast, deploy-anywhere agent runtime from Sipeed (hardware vendor).
- Triage verdict: **monitor**
- Rationale: MIT, Go, very active, hardware-vendor backing (Sipeed). Go runtime is interesting alignment with our cmd/cos / cmd/cos-test layer. Hardware-targeted angle is unusual in this cluster. Track for Go primitives that may map to our Go test-lane / orchestrator layer; not yet enough surface signal for a deep pass.

### 16. smykla-skalski/klaudiush
- URL: https://github.com/smykla-skalski/klaudiush
- License: MIT
- Stars: 12
- Last commit: 2026-05-06
- Primary language: Go
- One-line purpose: Validation dispatcher for Claude Code hooks enforcing git workflow + commit conventions + code quality.
- Triage verdict: **monitor**
- Rationale: Tiny (12 stars, just clears the 10-star threshold) but extremely on-thesis: it dispatches Claude Code hooks for git/commit/quality enforcement — exactly the surface our hooks/self-install + rules/python-naming/bash-naming live on. Worth tracking for shared dispatch patterns; too small/unproven to promote without seeing the dispatcher implementation. Revisit if it grows or if we plan a hooks-dispatcher refactor.

### 17. warengonzaga/tinyclaw
- URL: https://github.com/warengonzaga/tinyclaw
- License: GPL-3.0
- Stars: 242
- Last commit: 2026-05-04
- Primary language: TypeScript
- One-line purpose: "Original tiny claw" personal AI companion.
- Triage verdict: **reject**
- Rationale: GPL-3.0 is copyleft and outside the pass list (MIT/BSD/Apache/ISC). Adopting code would force GPL on dependents; clean-room of patterns possible but cost/benefit poor given the dozen permissively-licensed alternatives in this cluster. Skip.

### 18. zeroclaw-labs/zeroclaw
- URL: https://github.com/zeroclaw-labs/zeroclaw
- License: Apache-2.0
- Stars: 31,057
- Last commit: 2026-05-06
- Primary language: Rust
- One-line purpose: Apache-2.0 Rust personal-AI infrastructure ("deploy anywhere, swap anything").
- Triage verdict: **monitor**
- Rationale: Canonical upstream of the zeroclaw lineage. Apache-2.0, very active, large. Strong candidate as a reference Rust implementation, but in this cluster the deep-pass slot in the Rust slice is better invested in OpenHands (Python, sandboxed) and openclaw (TS, viral upstream) which together cover broader primitive ground. Promote to deep in a later pass if a specific Rust-runtime question arises (sandbox model, swap-provider primitive). For now, track.

## Phase 2 candidates

1. **openclaw/openclaw** — viral upstream of the "claw" naming family, MIT, massive activity. Verify provenance (is any portion derived from proprietary Claude Code?) and harvest provider-swapping / channel-abstraction / sandbox primitives if clean.
2. **OpenHands/OpenHands** — mature MIT (core) Python harness with established container-sandboxed agent runtime and multi-agent orchestration. Direct overlap with our blast-radius/sandbox-sampling/impact-analysis surfaces; high yield expected for harvested primitives.

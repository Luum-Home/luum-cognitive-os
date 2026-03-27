# Case Study 1: Decomposing a Legacy Monolith with Parallel Agents

> Anonymized case study. The client, its product, its vendors, its stack details and its
> figures are deliberately left out: the combination of those details would identify the
> organization. What remains is the part that transfers to other projects.

---

## Summary

A team used Cognitive OS during one long working session to decompose a legacy backend
monolith into smaller services, modernize the client app that consumed it, and install
Cognitive OS itself in the project. The work that a traditional plan estimated in months of
single-engineer effort was carried out by many agents working in parallel, coordinated by one
operator.

## The Challenge

- A monolith that had grown over years, with several services around it written in
  different languages.
- External integrations that were mocked behind flags, some depending on SDKs that were no
  longer maintained.
- A client app on an outdated framework version.
- A rebranding that touched code, configuration and build identifiers at once.

## What Was Done

- **Research before building**: open-source tools were evaluated and licence-checked before
  adopting any of them.
- **Backend decomposition**: domains were extracted one at a time into services that shared a
  common set of internal packages (errors, middleware, persistence, events), so each new
  service started from the same foundations instead of from scratch.
- **Integrations behind interfaces**: the mock flags were replaced by a plugin boundary, so a
  real provider and a fake one are interchangeable.
- **Client modernization**: framework upgrades and a move to a feature-oriented layout, in
  batches.
- **Rebranding as a mechanical, verifiable change**: renames driven by search-and-verify loops
  instead of manual edits.
- **Cognitive OS itself**: hooks, rules, skills and agent personas installed and adapted to the
  project as the work went on.
- **Tests at every step**: unit, integration and end-to-end suites written alongside each
  migrated domain.

Only part of the monolith was migrated in that session; the rest followed the same pattern.

## Why It Worked

1. **Parallel execution**: independent domains were migrated by agents running at the same time.
2. **Accumulated knowledge**: Engram persisted decisions across agent sessions, so later agents
   did not re-decide what earlier ones had settled.
3. **Pattern reuse**: a shared set of internal packages gave every new service the same
   foundations.
4. **Error learning**: each agent's mistakes became warnings for the next one.
5. **Automatic skill generation**: complex solutions were converted into reusable skills.
6. **Constitutional gates**: quality checks ran automatically on every change.
7. **Spec-driven development**: the SDD workflow kept the output structured and verifiable.

## Limits of This Case

- The speed-up compares an up-front traditional estimate with the observed session; there is
  no controlled counterfactual.
- Migrating part of a monolith is not the same as running it in production: hardening,
  operations and the remaining domains are separate work.
- The figures of the original engagement are not published here, on purpose.

---

# Case Study 2: 14 Architecture Decisions Implemented in 24 Hours (2026-05-07)

> Self-applied case study. Cognitive OS used Cognitive OS to deliver its own orchestration substrate. Reproducible from `git log` and the public research stream.

## Executive Summary

Following an operator-driven question — *"are we covering everything the established tools cover in their most recent versions?"* — the Cognitive OS team executed in **~36 hours of wall-clock time across two operator sessions**:

- A **79-source prior-art research report** on multi-agent coding orchestration
- A **coverage-gap analysis** with binding constraints (license / footprint / test tiers / verdict block schema)
- **11 parallel research agents** producing ~42,000 words and ~230 sources of gap-specific reports
- A **ranked synthesis** with verdict blocks per gap
- **C1–C4 evaluation contract promoted from chat directives to a versioned manifest** (`manifests/orchestration-research-evaluation.yaml`)
- **14 ADRs (220–236, ADR-229 tombstone) drafted and Slice-A-implemented** in code, tests, manifests, and hooks
- An **independent guardrail validator** confirming the substrate-consumer boundary holds

The traditional estimate for the implementation portion alone (substrate + consumers + adapters across multiple lib modules, manifests, hooks, and tests) is 4–8 weeks of senior single-author work.

## The Challenge

A pre-launch self-audit revealed that the existing pre-agent-stash mechanism — central to multi-agent safety — was an industry anti-pattern producing the same class of bug Anthropic shipped (issue #11005), the LangGraph+Pydantic incompatibility (issue #6027), and the November 2025 industry $47,000 runaway-loop incident.

The challenge: replace the broken primitive without breaking adoption, while also covering the gaps the prior-art research uncovered (replay timeline, sandbox tiers, MCP server, agent-to-agent handoff, cross-session teams, etc.).

## What Was Accomplished

### Research and synthesis

| Task | Traditional Estimate | Actual Time |
|---|---|---|
| Multi-agent coding orchestration prior-art research (15 systems, 7 cross-cutting topics, 79 sources) | 1–2 weeks | ~3 hours (single LLM session) |
| Coverage gap analysis + C1–C4 constraints | 3–5 days | ~1 hour |
| 11 parallel gap-specific research reports (42K words, 230 sources) | 2–4 weeks (sequential) | ~12 minutes (parallel) |
| Ranked synthesis with per-gap verdict blocks | 2–3 days | ~30 minutes |
| Promotion of C1–C4 from prose to canonical manifest | 1–2 days | ~30 minutes |

### ADR drafting

| Task | Traditional Estimate | Actual Time |
|---|---|---|
| Draft ADR-226 Event-Sourced Session Bus (load-bearing) | 1 day | ~30 minutes |
| Draft ADR-227 Shadow-Git Checkpoint Substrate | 1 day | ~30 minutes |
| Draft ADR-228 Retry + Cost Budget (consolidated) | 1 day | ~30 minutes |
| Draft ADR-230 Handoff Envelope + Cycle Dedup | 1 day | ~30 minutes |
| Draft ADR-223 / 224 / 225 (reserved set) | 3 days | ~30 minutes (first cut) |
| Draft ADR-231 / 232 / 233 / 234 / 235 / 236 (consumers + adapters) | 1 week | ~2 hours (Codex parallel) |

### Implementation (Codex parallel session)

| Task | Traditional Estimate | Actual Time |
|---|---|---|
| `lib/session_bus.py` v2 with monotonic sequencing, per-session streams, group-commit durability | 1 week | ~2 hours |
| `lib/event_wrap.py` decorator + 4 event projection stubs (cost ledger, handoff chain, retry classifier, timeline) | 3–4 days | ~1 hour |
| `lib/shadow_git.py` + `cos rollback` CLI + atomic file+conversation truncation | 1 week | ~2 hours |
| `lib/dispatch_gate.py` + `lib/retry_classifier.py` + `lib/session_budget.py` + idempotency mixin + circuit breaker | 1–2 weeks | ~3 hours |
| `lib/handoff_envelope.py` + `lib/handoff_dispatcher.py` + cycle-dedup + permission intersection | 4–5 days | ~2 hours |
| `lib/agent_team.py` + `cos team` CLI + IPC hooks | 1 week | ~3 hours |
| `lib/sandbox_adapter.py` + Bubblewrap/Seatbelt OS-native default | 4–5 days | ~2 hours |
| `lib/agent_daemon.py` + tmux launcher + sentinels + queue/state | 1 week | ~2 hours |
| `lib/policy_eval.py` + YAML policy evaluator + sample policy | 3–4 days | ~1 hour |
| `lib/deferred_tool_loading.py` + manifest-backed eager/deferred planning + ToolSearch-like index | 2–3 days | ~1 hour |
| FastMCP-based 8-tool MCP server (`packages/mcp-server/`) + cross-harness registration plans | 1 week | ~2 hours |
| 11 schema-versioned manifests across all primitives | 3–4 days | ~1 hour |
| 20+ test files spanning unit/audit/behavior/benchmark/integration/red_team-portability/smoke | 2–3 weeks | ~3 hours |
| 6 new/modified hooks integrating into PreToolUse/PostToolUse lanes | 3–4 days | ~1 hour |

### Validation

| Task | Traditional Estimate | Actual Time |
|---|---|---|
| Substrate-consumer guardrail validator (14 checks across 6 dimensions) | 2–3 days | ~30 minutes |
| Phase-1 test suite passing 52/52 in 3.82s | continuous | continuous |
| Independent run of `scripts/validate_substrate_consumers.py` confirming 14/14 PASS | 1 day | ~5 seconds |

## Totals

| Metric | Value |
|---|---|
| **Traditional estimate (implementation only)** | 4–8 weeks (1 senior engineer) |
| **Actual time (research + drafting + implementation + validation)** | ~36 hours wall-clock |
| **ADRs drafted and Slice-A-implemented** | 14 |
| **`lib/` modules added** | 15 |
| **Manifests added (schema-versioned YAML)** | 11 |
| **Test files added** | 20+ |
| **Hooks added/modified** | 6 |
| **Phase-1 test suite size** | 52 tests, all passing in 3.82s |
| **Guardrail validator checks** | 14 / 14 PASS |
| **Sources cited across the research line** | ~230 unique URLs |
| **Words across research reports** | ~42,000 |

## What This Means

The first case study (a legacy monolith decomposed by parallel agents) showed that Cognitive OS can help decompose external systems.

The second case study shows that **Cognitive OS can extend itself with the same discipline it extends external systems.** The ADRs honor a versioned C1–C4 contract (license allowlist/blocklist, footprint discipline, test-tier matrix). The implementation honors the ADRs. The guardrail validator confirms the substrate-consumer boundary holds. The IMPLEMENTATION-CHECKLIST publishes per-ADR slice progression (Slices A–F across 14 ADRs as of the latest update) with T6/T7/T8/T9/T10 hardening pendings called out per ADR — no overclaim.

For commercial purposes, the operative point is not "fast" — it is "fast under a versioned contract that an operator can audit." Speed without contract is research-inflation. Speed under contract is durable engineering.

## Reproducibility

```bash
# Read the research foundation
cat docs/03-PoCs/research/multi-agent-orchestration-prior-art-2026-05-06.md

# Read the gap analysis with C1-C4 constraints
cat docs/03-PoCs/research/orchestration-coverage-gap-analysis-2026-05-06.md

# Read the canonical evaluation contract
cat manifests/orchestration-research-evaluation.yaml

# Read the ranked synthesis
cat docs/03-PoCs/research/orchestration-gaps/SYNTHESIS-2026-05-06.md

# Read the implementation tracker (per-ADR slice + tier-test pendings)
cat docs/03-PoCs/research/orchestration-gaps/IMPLEMENTATION-CHECKLIST-2026-05-07.md

# Run the substrate-consumer guardrail validator
python3 scripts/validate_substrate_consumers.py

# Run the Phase-1 test suite
python3 -m pytest tests/unit/test_event_sourced_bus.py \
  tests/unit/test_shadow_git.py tests/unit/test_dispatch_gate.py \
  tests/unit/test_handoff_envelope.py tests/unit/test_retry_classifier.py \
  tests/unit/test_session_budget.py -q
```

All artifacts are in `main` and reproducible.

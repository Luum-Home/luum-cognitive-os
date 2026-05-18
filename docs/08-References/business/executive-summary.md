# Cognitive OS — The Operating System for AI-Powered Development

> One-page executive summary for decision makers. What Cognitive OS is, why it matters, and how to get started.

---

## The Problem

AI coding assistants (Claude Code, Cursor, Codex, Gemini) are the most transformative tools since version control. But they all share critical limitations:

- **No memory**: Every session starts from scratch. The AI doesn't remember decisions, bugs, or conventions.
- **No quality control**: Nothing prevents an agent from introducing bugs, skipping tests, or violating the architecture.
- **No coordination**: Running multiple agents in parallel creates chaos — handoff cycles cause 41–87% failure rates in production multi-agent systems (MAST 2025), and zero frameworks prevent it.
- **No replay**: When an agent goes wrong at step 17, you can't rewind to step 16 and try again. Devin solved this with hypervisor snapshots; nobody else has.
- **No cost safety**: A single runaway loop in November 2025 burned $47,000 in API costs because dashboards detect *after* the fact, not before the next call fires.
- **No observability**: There's no way to know what the agents did, how many tokens they burned, or whether they succeeded.
- **No continuous improvement**: When an agent makes a mistake and you correct it, that correction is lost. The same error will happen again.

The result: developers spend 30-50% of their AI time re-establishing context, verifying quality, and fixing errors — work that the AI should be handling.

## The Solution

Cognitive OS is a middleware layer that sits between the developer and any AI assistant. It's not another AI tool — it's the infrastructure that makes all AI tools work better.

```
Developer --> Cognitive OS --> AI Assistant (Claude/Cursor/Codex/Gemini)
                 |
    +---------------------------+
    | Engram (Memory)           |  Remembers everything between sessions
    | Skills (Workflows)        |  Reusable procedures that self-improve
    | Hooks (Enforcement)       |  Quality gates impossible to bypass
    | Metrics (Observability)   |  Knows what agents did and how much it cost
    | SDD (Planning)            |  Structured approach for complex changes
    | SRE (Reliability)         |  Detects and repairs failures automatically
    +---------------------------+
```

## What It Does

> Status legend: **REAL** = production-ready and hook-enforced. **DORMANT** = code
> exists but feature-flagged off / opt-in. **ASPIRATIONAL** = scaffolded, loop
> not yet closed. Full reconciliation in
> [`docs/09-Quality/legal/h1-feature-status-audit.md`](../../09-Quality/legal/h1-feature-status-audit.md)
> and [`docs/08-References/business/features.md`](features.md).

| # | Feature | Status | What It Does |
|---|---------|--------|--------------|
| 1 | Persistent Memory | REAL | Your AI remembers decisions, bugs, and conventions between sessions |
| 2 | Spec-Driven Development | REAL | 8 core phases plus optional init/bootstrap and fast paths for complex changes |
| 3 | Quality Control | REAL | Immutable gates + configurable rules |
| 4 | Self-Improvement | DORMANT | Captures errors, detects patterns, **proposes** skill and routing updates for human review (autonomous mutation is gated by ADR-201/204/206) |
| 5 | Multi-Agent Orchestration | REAL | 12+ simultaneous coordinated agents |
| 6 | Security | REAL | Guardrails, dangerous command blocking, audit trails |
| 7 | Observability and Costs | REAL | Traces, metrics, budget caps |
| 8 | Multi-IDE Portability | REAL | Claude/Codex native lifecycle plus structural projections; proof level differs by harness |
| 9 | Industry Presets | REAL | Pre-loaded best practices for fintech, healthcare, e-commerce |
| 10 | Source-Available Core | REAL | FSL-1.1-MIT (source-available, converts to MIT after 2 years), extensible via plugins |

## Proven in Production

A 170-endpoint monolith was decomposed into 14+ microservices in ~24 hours using Cognitive OS:

| Metric | Value |
|---|---|
| Agents launched | 100+ |
| Agents in parallel | 12+ |
| Tests written | 700+ |
| Traditional estimate | 9-15 months |
| Actual time | ~24 hours |
| Acceleration factor | ~300x |

## What Makes It Different

1. **Depth of integration** — 13 integrated primitives that work as a system, not as standalone tools. Memory feeds error learning, which feeds skill adaptation, which feeds KPIs.

2. **Proven on real software** — Not a demo project. Built and validated on a fintech platform with 170+ endpoints, 3 programming languages, and 14 integrations with external providers.

3. **Telemetry-guided improvement** — The system records errors, patterns, and skill outcomes so maintainers can review proposed improvements; autonomous mutation remains gated by explicit experiments and human approval.

4. **Portability** — Not tied to any IDE or AI provider. Rules, skills, integrations, and manifests are projected by proof level: native lifecycle, governed wrapper, structural projection, planned, or unsupported.

## Getting Started

```bash
# Clone Cognitive OS into your project
cd your-project
git clone https://github.com/luum-home/luum-cognitive-os.git .cognitive-os-repo
cp -r .cognitive-os-repo/.cognitive-os/ .cognitive-os/
rm -rf .cognitive-os-repo

# Initialize — detects your stack and generates project-specific config
claude
> /cognitive-os-init

# Done — your AI now has memory, discipline, and self-improvement
```

## Contributing

Cognitive OS is source-available under FSL-1.1-MIT, with automatic MIT conversion, and contributions are welcome. Visit the repository on GitHub to report issues, propose features, or create plugins for your industry.

---

*Cognitive OS: governance, memory, and orchestration infrastructure that turns AI
assistants into more disciplined engineering collaborators. Autonomy in the
self-improvement and self-healing loops is propose-only and human-gated; it is
not unsupervised.*

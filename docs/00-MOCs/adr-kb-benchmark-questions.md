# ADR Knowledge Pilot — Frozen Benchmark Question Set

Human-readable companion to the machine-readable fixture at
[`adr-kb-benchmark-questions.jsonl`](adr-kb-benchmark-questions.jsonl), consumed by
[`scripts/adr_kb_benchmark.py`](../../scripts/adr_kb_benchmark.py).

**This fixture is FROZEN.** It must not change between the BEFORE and AFTER
benchmark arms (sdd/adr-knowledge-pilot). Any edit to a question, its
`gold_adr` list, or its category invalidates the paired comparison — treat
this file and the JSONL as read-only once the BEFORE arm has run against them.
If a question turns out to be wrong (e.g. the gold ADR is misidentified),
that is a new fixture version, not an edit — re-run both arms from scratch.

26 questions, spanning 25 distinct ADRs from the 150-ADR pilot set (ADRs
`>2000` raw tokens per the measured threshold in
`sdd/adr-knowledge-pilot/design`). Category mix: existence, decision,
why/incident, consequence, cross-ADR.

| ID | Category | Question | Gold ADR(s) |
|----|----------|----------|--------------|
| q01 | existence | Does an ADR exist that governs how context-injection token budgets are enforced? | ADR-186 |
| q02 | decision | What did the project decide about activating the ADR-038 Wave 3 context budget limits? | ADR-186 |
| q03 | why-incident | What incident or pressure led to writing the Engram Lifecycle Evolution ADR? | ADR-071 |
| q04 | consequence | What is the consequence of consolidating the ADR namespace under docs/02-Decisions/adrs? | ADR-087 |
| q05 | existence | Is there a capability coverage matrix ADR, and what reality-level enum does it define? | ADR-252 |
| q06 | decision | What decision governs which LLM providers are used for overflow when Claude is rate-limited? | ADR-049 |
| q07 | decision | What typed-memory verification and staleness policies does Memory Governance v2 introduce? | ADR-261 |
| q08 | decision | What primitives were designed to coordinate multiple concurrent agent sessions? | ADR-116 |
| q09 | cross-adr | How does session lifecycle management interact with multi-session coordination primitives? | ADR-047, ADR-116 |
| q10 | why-incident | What problem prompted the Multi-Session Git Coordination ADR? | ADR-089 |
| q11 | consequence | What is the event-sourced session bus, and what consequence does it have for session state recovery? | ADR-226 |
| q12 | decision | Does the cosd remote API require authentication, and what mechanism does it use? | ADR-260 |
| q13 | decision | What per-session cap and preview/reference-only modes does the tool-replay budget ledger define? | ADR-263 |
| q14 | consequence | What is the Evolve Loop Spike, and what consequence follows from LLM-driven skill candidates being queued? | ADR-262 |
| q15 | existence | Is there an umbrella ADR for cross-harness adoption of Hermes, and what does it cover? | ADR-080 |
| q16 | cross-adr | How does the Codex Harness Adapter relate to the Hermes Cross-Harness Adoption umbrella ADR? | ADR-081, ADR-080 |
| q17 | decision | What decision defines the multi-surface UI architecture spanning CLI, Phoenix, Engram Cloud, Obsidian? | ADR-172 |
| q18 | consequence | What compliance frameworks does the air-gapped surface ADR address, and what consequence for audit evidence? | ADR-142 |
| q19 | decision | What retry taxonomy and attempt limits does the consolidated Retry Contract + Cost Session Budget ADR define? | ADR-228 |
| q20 | why-incident | What is the harness-agnostic event capture layer, and why was a canonical schema needed? | ADR-033 |
| q21 | consequence | What design makes git stash mutation reversible-by-design, and what consequence for quarantine ops? | ADR-117 |
| q22 | decision | What is Tier 2 of clean-room detection, and what are the boundaries of AST-normalized similarity? | ADR-271 |
| q23 | existence | Does an ADR exist for auditing script exposure and ratcheting invocation surfaces? | ADR-283 |
| q24 | why-incident | What layered prevention does the Concurrent Agent Safety Layer ADR put in place, and what incident motivated it? | ADR-108 |
| q25 | cross-adr | What destructive git operations does the Agent Git Operations Safety ADR prevent, and how does it relate to concurrent agent safety? | ADR-094, ADR-108 |
| q26 | consequence | What decision established the SO Reliability & Observability Framework, and what consequence for failure tracking? | ADR-028 |

## Arms

- **BEFORE** (runs today): raw ADR file(s) named in `gold_adr`, read from
  `docs/02-Decisions/adrs/ADR-NNN*.md`.
- **AFTER** (blocked until synthesis pages + `context_injector.py` remap land
  under `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`): the `ADR-NNN.synthesis.md`
  page(s) plus the relevant Tier-2 index node from `docs/00-MOCs/decisions.md`.

Run with:

```bash
python3 scripts/adr_kb_benchmark.py --arm before \
  --questions docs/00-MOCs/adr-kb-benchmark-questions.jsonl \
  --json-out .cognitive-os/metrics/adr-kb-benchmark-before.jsonl --report
```

Last updated: 2026-07-03

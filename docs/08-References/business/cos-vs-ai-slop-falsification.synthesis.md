---
type: reference-synthesis
source: docs/08-References/business/cos-vs-ai-slop-falsification.md
provenance: "Establishes a falsifiable A/B/C benchmark protocol so Cognitive OS's value claim can be disproven rather than merely asserted — more hooks, skills, rules, and manifests are explicitly stated not to be proof by themselves."
---

## What it is

A short, sharp protocol document defining a three-group (A/B/C) benchmark design to test whether Cognitive OS actually improves agent-assisted engineering outcomes versus native-harness or minimal-substrate alternatives, with explicit rules for what counts as a product win.

## Key mechanics

- **Three groups**: A = native-harness (Codex/Claude/OpenCode/Goose plus shell/git/tests/permissions/prompt-injection defense/SDD, no COS); B = minimal-cos (small/default COS substrate); C = full-cos (broad COS governance mesh) — all run on the same work.
- **Product verdict rules**: if A wins, COS is "slop or premature abstraction" for that task class; if B wins, the default product should be minimal-COS + agentic literacy; if C wins, full-COS is justified only for the winning task classes; if B and C tie, **B wins by default** because smaller surface area has lower cognitive/operational cost.
- **Current executable evidence**: `scripts/cos-falsification-benchmark --json --write-report`, with output landing at `docs/06-Daily/reports/cos-falsification-benchmark-latest.{json,md}`. The deterministic no-provider benchmark currently supports the `minimal-cos-default` verdict specifically for the safety/recovery/evidence task set.
- **Explicit limits**: the deterministic benchmark proves local safety/recovery/evidence outcomes only — it does *not* prove live LLM quality, human cognitive-load reduction, or time-to-merge improvements, which require a separate manual/live protocol.

## Relations & where used

This is the underlying falsification framework that the "Product Verdict Rules" in `cognitive-os-efficiency-operating-model.md`'s claim-tier ladder and `durable-product-master-plan.md`'s "Bet 1: Reliability over breadth" both implicitly rely on for evidentiary discipline. The A/B/C task-class framing is a narrower, executable sibling of the broader Workstream F comparison in `conversation-reality-audit-2026-04-30.md`.

## Status / caveats

Very short document — mostly protocol definition plus one concrete verdict. The "current executable evidence" section reports only a **deterministic, no-live-provider** benchmark result; it explicitly disclaims coverage of the harder, more commercially relevant claims (LLM quality, cognitive load, time-to-merge). Any product messaging citing this document should not overstate the `minimal-cos-default` finding beyond the safety/recovery/evidence task set it was measured on.

---
report_type: documentation-consistency-review
scope: ide-agnostic-primitives-observable-self-use
reviewed_at: 2026-05-09
status: corrected-minor-drift
---

# IDE-Agnostic Primitive Documentation Review — 2026-05-09

## Scope

This review reconciles the documentation thread that started from the consumer
`.ai/` overlay at:

```text
<consumer-repo>/.ai
```

and now spans IDE-agnostic primitive projection, ADR-256, primitive authoring,
OpenSage pattern extraction, and observable primitive self-use.

## Reviewed artifacts

| Artifact | Role | Status |
|---|---|---|
| `docs/architecture/ide-agnostic-primitive-projection.md` | Explains canonical primitive → portable contract → adapter → runtime evidence | Updated with `.ai/` overlay lesson and first runtime slice |
| `docs/adrs/ADR-256-primitive-contract-registry-and-runtime-evidence-ledger.md` | Root architecture decision for primitive contracts, intervention ledger, itinerary, and trace join | Updated to include codebase itinerary in the root chain and phase 0/6 wording |
| `docs/architecture/primitive-contract-registry-implementation-plan.md` | Plan-first implementation sequence for ADR-256 | Updated with phase 0 contract freeze and phase 6 consumer UX |
| `skills/primitive-authoring/SKILL.md` | Authoring gate for new/modified/promoted primitives | Consistent; no content change required |
| `docs/architecture/opensage-self-programming-patterns.md` | OpenSage-inspired pattern extraction contract | New artifact from the OpenSage analysis |
| `manifests/self-programming-agent-patterns.yaml` | Machine-readable OpenSage pattern contract | New audited manifest |
| `docs/reports/external-tools-radar-opensage-addendum-2026-05-09.md` | Radar decision for OpenSage ADK | Updated to require the pattern audit before adapter-lab work |
| `docs/README.md` | Documentation index | Deduplicated ADR-256 / IDE projection links and added this review |
| `skills/CATALOG.md` | Skill catalog | Removed duplicate `primitive-authoring` entry |

## Canonical synthesis

The stable architecture sentence is:

```text
canonical primitive
  -> portable contract
  -> harness/IDE adapter
  -> projection fidelity
  -> runtime evidence
  -> primitive intervention ledger
  -> codebase itinerary
  -> joined run trace
```

IDE-agnostic does **not** mean equal enforcement in every IDE. It means:

1. intent is portable;
2. required capabilities are explicit;
3. each adapter declares honest fidelity;
4. runtime evidence shows what actually happened.

## `.ai/` consumer-overlay lesson

The consumer overlay is a product mirror, not a replacement for COS internals:

```text
.ai/primitives/   # canonical skills/rules/workflows/hooks
.ai/adapters/     # per-IDE README.md + install.sh
.ai/context/      # durable project context
.ai/logs/         # simple JSONL metrics
.ai/state/        # anchors/budgets/session state
.ai/scripts/      # verify, routing, usage, access audits
```

The useful idea is packaging clarity: consumers need a small, installable mental
model. COS should preserve richer contracts and ledgers internally, then expose a
small overlay-style UX later through commands such as `cos adapters list`,
`cos adapters install codex`, and `cos adapters verify`.

## Observable self-use gap

COS already has partial evidence through dogfood scoring, primitive harness
coverage, ACC, hook timing, run traces, and behavior tests. The missing per-run
answer remains:

> The agent inspected these safe targets, these primitives observed/warned/blocked/suggested these actions, and this was the effect.

ADR-256 covers the missing runtime surfaces:

- `manifests/primitive-contracts.yaml`
- `.cognitive-os/metrics/primitive-interventions.jsonl`
- `.cognitive-os/metrics/codebase-itinerary.jsonl`

## OpenSage pressure test

OpenSage ADK is now documented as a pressure test, not an adopted runtime. The
five extracted patterns are:

1. dynamic agent topology;
2. dynamic tool/skill synthesis;
3. sandboxed execution;
4. graph/hierarchical memory;
5. real benchmark loops.

The guardrail is `manifests/self-programming-agent-patterns.yaml` plus:

```bash
scripts/cos-self-programming-pattern-audit --json
```

## Drift corrected in this review

1. `docs/README.md` had duplicate ADR-256 and IDE-agnostic projection entries.
2. `skills/CATALOG.md` had duplicate `primitive-authoring` entries.
3. ADR-256's root chain mentioned runtime intervention evidence and trace join,
   but omitted codebase itinerary in the initial context chain.
4. ADR-256 and the implementation plan now use a consistent phase shape:
   phase 0 through phase 6.
5. The IDE-agnostic projection doc now records the `.ai/` overlay lesson and the
   recommended first runtime slice.

## Recommended next implementation slice

```text
ACCEPTANCE CRITERIA:
1. tool-sequence capture records Read/Grep/Glob/LS with safe target metadata only.
2. `.cognitive-os/metrics/primitive-interventions.jsonl` exists.
3. Destructive git/rm, reinvention, and large-file primitives can emit canonical intervention rows.
4. `trace_joiner.py` joins tool sequences with primitive interventions.
5. A synthetic test proves read advisory + git block + reinvention warning joined by session.
```

## Stop condition

Do not start adapter UX or OpenSage-like dynamic runtime adoption until ADR-256
phase 1 and phase 2 exist. Otherwise COS would be adding more projection surface
without the observable evidence layer that distinguishes architecture proposed
from architecture observed.

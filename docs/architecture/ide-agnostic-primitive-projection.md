# IDE-Agnostic Primitive Projection

**Date:** 2026-05-09  
**Status:** Architecture synthesis

Cognitive OS makes agentic primitives IDE-agnostic by separating four layers:

```text
canonical primitive
  -> portable contract
  -> harness/runtime projection
  -> runtime evidence
```

A primitive is portable when its intent and contract are authored once, each
projection declares fidelity honestly, and evidence shows whether it ran,
warned, blocked, advised, or only existed as instructions.

## Existing foundations

- ADR-057: cross-harness authoring and driver projection.
- ADR-064: harness-agnostic Cognitive OS surfaces.
- ADR-154: multi-IDE structural projection.
- ADR-189: harness implementation coverage.
- ADR-205: run trace / flight recorder.
- `manifests/harness-projection.yaml`: harness status and proof levels.
- `manifests/harness-driver-capabilities.yaml`: driver event support.
- `manifests/primitive-projection-profiles.yaml`: default/full projection profiles.
- `scripts/cos-consumer-fleet-audit`: installed consumer impact panel.
- `scripts/cos-service-readiness-gate`: service/headless readiness gate.

## Fidelity levels

| Fidelity | Meaning |
|---|---|
| `native-lifecycle-enforced` | Host lifecycle runs the primitive at the right event and can block/warn. |
| `host-plugin-lifecycle-capable` | Host exposes plugin/tool lifecycle events that can enforce primitives, but COS has not yet signed runtime projection/smoke. |
| `governed-wrapper-enforced` | COS wrapper enforces when native lifecycle is insufficient. |
| `structural-advisory` | Project files/instructions are generated; no runtime enforcement claimed. |
| `ci-enforced` | Enforced only when shell/CI lane runs. |
| `service-enforced` | Enforced by headless/service/daemon substrate, not an IDE. |
| `documented-only` | Durable docs/contract, no active runtime projection. |
| `unsupported` | No safe projection or fallback. |

## Runtime shapes beyond IDEs

Primitive projection must consider more than IDEs:

| Shape | Question |
|---|---|
| IDE/harness embedded | Does it run through Claude/Codex/Cursor/etc. surfaces? |
| Consumer fleet | Which installed projects receive or are impacted by it? |
| Shell/CI | Can it run without IDE lifecycle? |
| Headless worker | Can it run in Docker/headless proof drills? |
| `cosd` service | Does it affect daemon task admission, queue, provider boundary, protected writes, or public service claims? |

Use:

```bash
scripts/cos-consumer-fleet-audit --json
scripts/cos-service-readiness-gate --json
```


## `.ai/` product mirror

`<consumer-repo>/.ai` is not deeper than COS, but it is clearer as consumer packaging. It separates:

```text
.ai/primitives/   # canonical skills/rules/workflows/hooks
.ai/adapters/     # per-IDE translators with README.md + install.sh
.ai/context/      # durable project context
.ai/logs/         # simple JSONL metrics
.ai/state/        # anchors/budgets/session state
.ai/scripts/      # verification, routing, usage, access audits
```

The product lesson is: consumers need a small overlay-shaped mental model, while COS can keep richer internal manifests and ledgers. Adapters must translate canonical primitives; they must not invent new primitive behavior.

## OpenCode adapter correction

OpenCode should not be treated as instruction-only. Current official OpenCode
surfaces include:

- project/global rules through `AGENTS.md` and `opencode.json` instruction files;
- configurable agents, commands, permissions, and bash command patterns;
- plugins with `tool.execute.before` and `tool.execute.after` lifecycle events.

That means an OpenCode projection can use:

```text
primitive contract
  -> opencode.json / AGENTS.md for advisory context
  -> OpenCode permissions for coarse allow/ask/deny policy
  -> OpenCode plugin hooks for pre/post tool enforcement and metrics
  -> primitive-interventions.jsonl as COS evidence sink
```

Until the COS OpenCode plugin adapter is implemented and smoke-tested, the
existing `opencode.json` projection remains structural proof only. The target
fidelity for eligible blocking/advisory primitives is therefore
`host-plugin-lifecycle-capable`, not `documented-only` and not yet
`native-lifecycle-enforced`.

## Observable self-use gap

COS already has partial observability: dogfood scoring, primitive harness coverage, ACC, hook timing, run traces, and behavior tests. The missing per-run answer is:

> The agent inspected these safe targets, these primitives observed/warned/blocked/suggested these actions, and this was the effect.

ADR-256 closes that through a primitive intervention ledger and codebase itinerary, joined into run traces.

## Recommended first runtime slice

```text
ACCEPTANCE CRITERIA:
1. tool-sequence capture records Read/Grep/Glob/LS with safe target metadata only.
2. `.cognitive-os/metrics/primitive-interventions.jsonl` exists.
3. Destructive git/rm, reinvention, and large-file primitives can emit canonical intervention rows.
4. `trace_joiner.py` joins tool sequences with primitive interventions.
5. A synthetic test proves read advisory + git block + reinvention warning joined by session.
```

## Root implementation proposal

The root proposal is ADR-256 and its implementation plan:

- `docs/adrs/ADR-256-primitive-contract-registry-and-runtime-evidence-ledger.md`
- `docs/architecture/primitive-contract-registry-implementation-plan.md`

They started as plan-first documents. ADR-257 now implements the minimal
`manifests/primitive-contracts.yaml` slice; the runtime ledgers and trace join
remain future phases.

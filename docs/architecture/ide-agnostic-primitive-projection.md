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

## Root implementation proposal

The root proposal is ADR-256 and its implementation plan:

- `docs/adrs/ADR-256-primitive-contract-registry-and-runtime-evidence-ledger.md`
- `docs/architecture/primitive-contract-registry-implementation-plan.md`

They are plan-first documents. They do not claim the runtime ledgers exist yet.

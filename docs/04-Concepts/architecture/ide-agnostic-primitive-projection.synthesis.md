---
type: concept-synthesis
source: docs/04-Concepts/architecture/ide-agnostic-primitive-projection.md
status: "Architecture synthesis"
provenance: "Cognitive OS primitives must be portable across IDEs/harnesses without inventing new behavior per adapter."
---

## What it is
Cognitive OS makes agentic primitives IDE-agnostic via four layers: canonical primitive -> portable contract -> harness/runtime projection -> runtime evidence. A primitive is portable when authored once, each projection declares fidelity honestly, and evidence shows whether it ran, warned, blocked, advised, or only existed as instructions.

## Key mechanics
- Foundations: ADR-057 (cross-harness authoring), ADR-064 (harness-agnostic surfaces), ADR-154 (multi-IDE structural projection), ADR-189 (harness coverage), ADR-205 (run trace/flight recorder); `manifests/harness-projection.yaml`, `manifests/harness-driver-capabilities.yaml`, `manifests/primitive-projection-profiles.yaml`; `scripts/cos-consumer-fleet-audit`, `scripts/cos-service-readiness-gate`.
- Fidelity levels: `native-lifecycle-enforced`, `host-plugin-lifecycle-capable`, `governed-wrapper-enforced`, `structural-advisory`, `ci-enforced`, `service-enforced`, `documented-only`, `unsupported`.
- Runtime shapes beyond IDEs: IDE/harness embedded, consumer fleet, shell/CI, headless worker, `cosd` service.
- `.ai/` has two distinct roles that must not collapse: maintainer generated overlay (`luum-agent-os/.ai/`, source of truth = `manifests/primitive-contracts.yaml` + `primitive-lifecycle.yaml` + `harness-projection.yaml`) vs consumer package view (`<consumer-repo>/.ai/`, human-readable, adapters translate but never invent behavior).
- Compiler chain target: `manifests/primitive-contracts.yaml` + `primitive-lifecycle.yaml` + `harness-projection.yaml` + rules/skills/hooks/scripts -> adapter compiler (`lib/adapter_compile.py`, `scripts/cos-adapter-compile`, `cos adapters compile`) -> AGENTS.md, `.cursor/rules/*.mdc`, `.github/copilot-instructions.md`, `.devin/rules/*.md`, CLAUDE.md, CONVENTIONS.md, `opencode.json`. Compiler must preserve fidelity (e.g. `structural-advisory` can't become a runtime-blocking claim).
- ADR-272: a `rulesync`-style backend may help but only behind the first-party adapter compiler, only for `structural-advisory` outputs.
- OpenCode surfaces (rules/AGENTS.md, permissions, plugin `tool.execute.before/after` hooks) mean target fidelity is `host-plugin-lifecycle-capable`, not `documented-only`, pending a tested COS plugin adapter.
- ADR-256 (primitive intervention ledger + codebase itinerary) closes the "observable self-use gap": what the agent inspected, what primitives observed/warned/blocked, and the effect — joined into run traces via `trace_joiner.py`.

## Relations & where used
ADR-057, ADR-064, ADR-154, ADR-189, ADR-205, ADR-256, ADR-257, ADR-272; `docs/02-Decisions/adrs/ADR-256-primitive-contract-registry-and-runtime-evidence-ledger.md`; `docs/04-Concepts/architecture/primitive-contract-registry-implementation-plan.md`.

## Status / caveats
ADR-257 implements only the minimal `manifests/primitive-contracts.yaml` slice; runtime ledgers and trace join remain future phases. OpenCode plugin adapter not yet implemented/smoke-tested.

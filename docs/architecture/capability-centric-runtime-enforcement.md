# Capability-Centric Runtime Enforcement

> Runtime rules for making Cognitive OS choose execution intent before vendor, model, or gateway.

## Decision

Cognitive OS should treat model and provider names as implementation details.

The runtime decision order is:

1. Resolve the task into an execution profile.
2. Apply explicit skill requirements when present.
3. Shape provider cascade and gateway fallback from the execution profile.
4. Record the execution profile in dispatch metrics.
5. Let provider, model, and gateway adapters satisfy that profile.

This prevents the system from aging around today's vendor names.

## Runtime Surfaces

| Surface | Enforcement |
|---|---|
| `lib/execution_profile.py` | Defines stable capability profiles and maps task/skill intent into profile IDs. |
| `lib/skill_routing.py` | Parses `execution_profile`, `tier`, and capability flags from skill frontmatter. |
| `lib/dispatch.py` | Resolves an execution profile before provider cascade selection and records it in `llm-dispatch.jsonl`. |
| `lib/gateway_selector.py` | Respects execution-profile constraints such as local/private execution when selecting fallbacks. |
| `lib/model_router.py` | Routes model execution through the same profile-aware gateway selection. |

## Compatibility Rule

Explicit provider overrides still win.

If a skill declares `providers_preferred`, the runtime treats that as a deliberate compatibility decision. If no provider preference is declared, the execution profile can shape the cascade:

- frontier or long-context work prefers the strongest supported path first
- low-cost or fast-turnaround work prefers cheaper/faster paths first
- balanced work preserves the existing cascade

This keeps old routing compatible while making new routing capability-first by default.

## Fail-Closed Rule

Local/private execution must not silently fall back to Claude or another cloud path.

If the local gateway is unavailable, the route fails closed instead of breaking the privacy constraint.

## Metrics Contract

Every dispatch metric should include an `execution_profile` block with the profile ID and relevant constraints.

That makes quality analysis provider-agnostic: future evals can compare outcomes by capability intent rather than by brand name.

## Promotion Path

Next enforcement steps:

- move more skill frontmatter from provider names to explicit `execution_profile` values
- teach additional provider adapters to satisfy profiles instead of being selected directly
- group outcome metrics by `execution_profile.id`
- add CI checks that new routing metadata does not introduce vendor-first defaults


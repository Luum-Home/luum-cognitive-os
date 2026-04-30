# ADR-009: Go-Only Auto-Generation in Phase 5

## Status

Accepted — 2026-04-16

## Context

The `Generator` interface accepts a `Language` field with values `"go"` or `"bash"`. Missing-coverage patterns could, in principle, be auto-filled by either: bash plugins are easier to template (a short script) while Go validators are compiled and type-checked.

Phase 5 ships the first version of the auto-generator. Scoping which languages it emits changes the template surface, the verification surface, and the set of runtime failure modes the reviewer (see ADR-008) has to understand.

## Decision

Phase 5's Generator emits only Go. Bash auto-generation is deferred beyond v1.0. The `generated_artifacts.language` column is kept in the schema for future use, but only `"go"` values are written in Phase 5.

Human-authored bash plugins continue to work via `BashAdapter` — this decision is about what the generator produces, not about what the system accepts.

## Alternatives Considered

1. **Mixed Go and bash from day one** — doubles the template surface and the review checklist without evidence of demand. Rejected.
2. **Bash-first, Go later** — bash is easier to emit but has a long tail of quoting/escaping/portability bugs that surface at runtime, not at build time. Auto-generated bash would ship regressions that the compiler would have caught for Go. Rejected.
3. **Go-first, bash post-v1.0** — the chosen path. Aligns with the Phase 3 direction of porting high-value bash hooks into Go validators.

## Consequences

- Generator templates and their tests cover one language. The review CLI (ADR-008) shows a single code shape per artifact.
- The `language` column is effectively constant in Phase 5, which is acceptable — it costs nothing and keeps the schema forward-compatible.
- Users who want an auto-generated bash plugin must write it themselves and register it via `BashAdapter`. This is a known limitation and is documented.
- When bash auto-generation is revisited, the decision record is this ADR; changing it does not require a schema migration.

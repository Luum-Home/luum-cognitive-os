# ADR-002: Transformer as Separate Interface from Validator

## Status

Accepted

## Context

klaudiush only has Validators (allow/deny/warn). We need hooks that modify data:
- `result-truncator`: truncates large tool outputs
- `inject-phase-context`: adds phase rules to agent prompts
- `secret-redactor`: strips secrets from tool input
- `symlink-resolver`: resolves symlinks in file paths

Options:
1. Extend Validator with mutation capabilities (add `Transform()` method)
2. Create a separate Transformer interface with its own pipeline
3. Use middleware pattern (each handler wraps the next)

## Decision

Separate Transformer interface with its own pipeline. Transformers have `Phase` (pre/post validation) and `Priority` (execution order within phase). They run in a defined order and can modify the hook Context or response payload. Validators remain pure read-only checks.

## Consequences

- Clear separation of concerns: mutations are explicit and ordered
- The pipeline is slightly more complex (two pipelines to manage), but each is simpler
- A component that needs both validation and transformation implements both interfaces
- Pre-transformers can normalize input before validators see it (e.g., symlink resolution prevents false "file not found" reports)
- Post-transformers can modify the response regardless of validation outcome
- Priority ordering prevents non-deterministic mutation conflicts

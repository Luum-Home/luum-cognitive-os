# ADR-192: Surface 5 Bubble Tea Adoption

## Status

Accepted — 2026-05-06

## Context

ADR-173 kept Surface 5 open as a research gate, and ADR-187 required a proof
contract before adopting a custom TUI/UI substrate. The Go CLI already uses the
Charm ecosystem for operator UX, and `bubbletea` is available in the module graph.
The gap was a sourced adoption decision and a compile-level proof inside the COS
CLI module.

## Decision

Adopt Bubble Tea as the Surface 5 terminal UI substrate for Cognitive OS.

This does not make every existing terminal script a full-screen TUI. The current
`scripts/cos-tui` remains the operable Python bridge for whitelisted report
refresh actions. Bubble Tea is the substrate for the next native Go TUI surface
under `cmd/cos`.

The first proof slice is intentionally small:

- `cmd/cos/internal/tui/proof.go` imports Bubble Tea directly and implements a
  minimal model.
- `cmd/cos/internal/tui/proof_test.go` verifies the Bubble Tea model contract.
- `cmd/cos/go.mod` carries Bubble Tea as a direct dependency after `go mod tidy`.

## ADR-187 Proof Pack

| Required proof | Evidence |
|---|---|
| Source compatibility | Direct import and compilation in `cmd/cos/internal/tui/proof.go`. |
| License acceptability | Charm Bubble Tea is MIT licensed. |
| Runtime boundary | Native Go CLI module only; no IDE hook dependency. |
| Operator value | Enables richer local operator workflows than line-oriented shell snapshots. |
| Reversibility | Surface 5 remains isolated under `cmd/cos/internal/tui`; Python `scripts/cos-tui` remains functional. |
| Failure mode | If Bubble Tea regressions occur, CLI commands and scripts continue to run without the full-screen TUI. |
| Testability | `go test ./cmd/cos/...` compiles and exercises the proof model. |

## Consequences

- Surface 5 is no longer an unassigned substrate slot.
- Implementation can proceed incrementally without rewriting the existing
  whitelisted `scripts/cos-tui` bridge.
- Future Surface 5 work should extend the Go package rather than adding another
  unrelated TUI framework.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. ADR-173 remains the historical research gate and ADR-192 records the adoption.
2. `cmd/cos/internal/tui/proof.go` imports Bubble Tea directly.
3. `cmd/cos/internal/tui/proof_test.go` proves the minimal Bubble Tea model contract.
4. `cd cmd/cos && go test ./...` passes.
```

---
adr: 195
title: Surface 5 Operable TUI Contract
status: accepted
implementation_status: partial
date: '2026-05-06'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit partial/phase scope
---

# ADR-195: Surface 5 Operable TUI Contract

## Status

Accepted — 2026-05-06

## Context

ADR-187 defined the proof requirements for adopting a Surface 5 UI substrate.
ADR-192 adopted Bubble Tea and proved the dependency boundary in the Go `cos`
module. ADR-194 then secured the `cosd` remote API guardrail so a future UI can
consume daemon state without inventing a weaker control path.

The remaining gap is the product contract for moving from a proof model to a
real operator surface. Cognitive OS already exposes release evidence, `cosd`
queue state, primitive coverage reports, and action receipts. Surface 5 should
compose those existing agentic primitive signals instead of creating a parallel
scheduler, database, or authority layer.

## Decision

Implement Surface 5 as a Bubble Tea operator console under `cmd/cos`, starting
with a read-only MVP.

The command contract is:

```bash
cos tui                  # interactive Bubble Tea console
cos tui --snapshot       # deterministic non-interactive snapshot
cos tui --project-dir .  # inspect an explicit install/project root
```

The first MVP includes these tabs:

- Overview
- cosd
- Coverage
- Release
- Receipts

The read-only MVP may read repository artifacts and COS runtime files, but it
must not mutate state, run provider/model calls, write receipts, process queues,
or change git state. Missing artifacts are rendered as warnings rather than
fatal errors so the TUI is useful during partial installs.

Future operable actions are allowed only after all of these are true:

1. the action has an explicit allowlist entry;
2. the operator confirms the action in the UI;
3. the action emits a receipt with Surface 5 metadata;
4. the action delegates to an existing CLI/script/API contract rather than
   embedding a separate implementation; and
5. tests prove the action cannot run without confirmation.

## Implementation

The accepted read-only slice is:

- `cmd/cos/internal/tui/app.go` defines the Surface 5 snapshot model, Bubble Tea
  tab shell, and deterministic text renderer.
- `cmd/cos/internal/cli/tui.go` exposes `cos tui` and `cos tui --snapshot`.
- `cmd/cos/internal/tui/app_test.go` verifies artifact readers, deterministic
  rendering, tab switching, and quit handling.
- `cmd/cos/internal/cli/tui_test.go` verifies the end-to-end snapshot command.

## Consequences

- Surface 5 has a real operator entrypoint instead of only an adoption proof.
- The first implementation is safe to run in local checkouts and install roots
  because it observes files and reports only.
- `scripts/cos-tui` remains a compatibility surface for existing scripted
  refresh workflows until the Go TUI reaches action parity.
- Operable actions are intentionally deferred behind confirmation and receipt
  contracts, preventing the TUI from becoming an unreviewed mutation channel.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. `cos tui --snapshot --project-dir .` prints Overview, cosd, Coverage, Release, and Receipts sections.
2. `cos tui` launches through Bubble Tea without adding a second TUI framework.
3. The first MVP performs no writes and has no mutating keybindings.
4. Missing coverage/release/runtime artifacts render warnings instead of crashing.
5. Tests cover snapshot readers, render output, keyboard tab navigation, quit handling, and the CLI snapshot command.
6. `cd cmd/cos && go test ./...` passes.
```

## Alternatives rejected

- Start Surface 5 with mutating keybindings immediately; rejected because read-only observability needed a stable proof before confirmation-gated actions.

## Verification

```bash
cd cmd/cos && go test ./internal/tui ./internal/cli
python3 -m pytest tests/contracts/test_cos_tui_operable_surface_contract.py -q
```

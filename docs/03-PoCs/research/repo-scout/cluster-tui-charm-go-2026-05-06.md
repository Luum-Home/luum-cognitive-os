---
cluster: tui-charm-go
theme: charmbracelet ecosystem Go TUI libraries
date: 2026-05-06
phase: shallow
total_repos: 9
license_pass: 8
license_reject: 1
active: 9
archived: 0
phase_2_candidates: 8
adr_gate: ADR-173/187 SURFACE-5
---

# Cluster: tui-charm-go (shallow)

## Repos

### 1. charmbracelet/bubbletea
- URL: https://github.com/charmbracelet/bubbletea
- License: MIT
- Stars: 42,114
- Last commit: 2026-04-24
- Primary language: Go
- Purpose: Elm-architecture TUI framework — the canonical Go TUI runtime.
- Verdict: PASS-TO-DEEP
- Rationale: Foundational dep for any Go TUI in COS (already used by `cmd/cos`). License-clean, highly active, ecosystem anchor.

### 2. charmbracelet/bubbles
- URL: https://github.com/charmbracelet/bubbles
- License: MIT
- Stars: 8,309
- Last commit: 2026-04-26
- Primary language: Go
- Purpose: Reusable Bubbletea components (list, table, textinput, viewport, spinner, paginator).
- Verdict: PASS-TO-DEEP
- Rationale: First-party companion to bubbletea; saves writing primitives. Direct fit for cos-test/cos UIs.

### 3. charmbracelet/lipgloss
- URL: https://github.com/charmbracelet/lipgloss
- License: MIT
- Stars: 11,196
- Last commit: 2026-04-26
- Primary language: Go
- Purpose: Declarative styling/layout DSL for terminal output.
- Verdict: PASS-TO-DEEP
- Rationale: Core styling library — eligible to replace ad-hoc ANSI in COS Go binaries.

### 4. charmbracelet/huh
- URL: https://github.com/charmbracelet/huh
- License: MIT
- Stars: 6,846
- Last commit: 2026-04-22
- Primary language: Go
- Purpose: Forms/prompts library (select, multiselect, input, confirm) on top of bubbletea.
- Verdict: PASS-TO-DEEP
- Rationale: Direct candidate for interactive flows in `cos` (init wizard, sdd-propose interactive mode).

### 5. charmbracelet/glamour
- URL: https://github.com/charmbracelet/glamour
- License: MIT
- Stars: 3,456
- Last commit: 2026-04-27
- Primary language: Go
- Purpose: Stylesheet-based markdown renderer for terminal.
- Verdict: PASS-TO-DEEP
- Rationale: Useful for rendering ADRs, RULES-COMPACT, agent reports inside `cos` TUI.

### 6. charmbracelet/gum
- URL: https://github.com/charmbracelet/gum
- License: MIT
- Stars: 23,551
- Last commit: 2026-05-04
- Primary language: Go
- Purpose: Shell-script-friendly TUI primitives as a CLI binary.
- Verdict: PASS-TO-DEEP
- Rationale: Could replace bash prompt hacks in `hooks/` and `scripts/` (confirm, choose, spin). Distribution-as-binary is the integration pattern.

### 7. charmbracelet/vhs
- URL: https://github.com/charmbracelet/vhs
- License: MIT
- Stars: 19,598
- Last commit: 2026-05-04
- Primary language: Go
- Purpose: Scriptable terminal-recorder producing GIFs/MP4/WebM from .tape files.
- Verdict: PASS-TO-DEEP
- Rationale: High-leverage for COS docs/01-Build-Log/release artifacts (demo recordings of `cos` flows). Low integration risk (offline tool).

### 8. charmbracelet/soft-serve
- URL: https://github.com/charmbracelet/soft-serve
- License: MIT
- Stars: 6,874
- Last commit: 2026-05-04
- Primary language: Go
- Purpose: Self-hostable Git server with a TUI front (SSH-based).
- Verdict: PASS-TO-DEEP (lower priority)
- Rationale: License-clean and active; speculative fit for air-gapped Engram/ADR transport (touches ADR-141 cross-instance replication). Keep in surface but defer until a concrete need.

### 9. charmbracelet/crush
- URL: https://github.com/charmbracelet/crush
- License: FSL-1.1-MIT (Functional Source License) — reported as NOASSERTION by GitHub, verified via LICENSE
- Stars: 23,900
- Last commit: 2026-05-06
- Primary language: Go
- Purpose: Charmbracelet's agentic coding TUI ("glamourous agentic coding for all").
- Verdict: REJECT
- Rationale: FSL-1.1-MIT is on the cluster reject list (non-permissive during the 2-year functional period; converts to MIT only after). Not eligible for adoption or code reuse under ADR-173/187 license-clean gate. Patterns may be observed but no code lift.

## Phase 2 candidates

1. charmbracelet/bubbletea
2. charmbracelet/bubbles
3. charmbracelet/lipgloss
4. charmbracelet/huh
5. charmbracelet/glamour
6. charmbracelet/gum
7. charmbracelet/vhs
8. charmbracelet/soft-serve

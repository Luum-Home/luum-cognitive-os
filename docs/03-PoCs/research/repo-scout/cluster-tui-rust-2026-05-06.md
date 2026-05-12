---
cluster: tui-rust
date: 2026-05-06
phase: shallow
theme: Rust TUI libraries (ratatui, crossterm, tui-rs, cursive, helix)
total_repos: 5
adopt: 2
investigate: 1
reject: 2
phase_2_candidates: 2
gate: ADR-173/187 SURFACE-5
---

# Cluster: tui-rust (Shallow Phase)

Theme: Rust TUI ecosystem evaluation for potential adoption in COS terminal-facing surfaces. SURFACE-5 reduction gate (ADR-173/187) applies — favor a single TUI primitive over multiple competing ones.

## Repos

### 1. ratatui/ratatui
- URL: https://github.com/ratatui/ratatui
- License: MIT
- Stars: 20,213
- Last commit: 2026-05-04
- Primary language: Rust
- Purpose: Actively-maintained successor to tui-rs; immediate-mode TUI rendering library.
- Triage verdict: ADOPT
- Rationale: Industry-standard Rust TUI library, MIT-licensed, very active, large ecosystem of widget crates. Clear winner for SURFACE-5 consolidation if a Rust TUI primitive is needed.

### 2. crossterm-rs/crossterm
- URL: https://github.com/crossterm-rs/crossterm
- License: MIT
- Stars: 4,034
- Last commit: 2026-04-08
- Primary language: Rust
- Purpose: Cross-platform terminal manipulation backend (cursor, events, color).
- Triage verdict: ADOPT
- Rationale: Foundational dependency under ratatui and most modern Rust TUIs. MIT, actively maintained, no viable alternative at this layer. Adopt as transitive of ratatui.

### 3. gyscos/cursive
- URL: https://github.com/gyscos/cursive
- License: MIT
- Stars: 4,789
- Last commit: 2026-05-03
- Primary language: Rust
- Purpose: Retained-mode (callback/widget-tree) TUI library — alternative paradigm to ratatui.
- Triage verdict: INVESTIGATE
- Rationale: Different paradigm (retained vs immediate mode); only worth deeper look if ratatui's immediate-mode model is a poor fit for COS use cases. Otherwise reject under SURFACE-5 (one TUI library, not two).

### 4. fdehau/tui-rs
- URL: https://github.com/fdehau/tui-rs
- License: MIT
- Stars: 10,873
- Last commit: 2023-08-06 (archived)
- Primary language: Rust
- Purpose: Original immediate-mode Rust TUI library.
- Triage verdict: REJECT
- Rationale: Deprecated and archived; ratatui is the maintained fork. Use ratatui.

### 5. helix-editor/helix
- URL: https://github.com/helix-editor/helix
- License: MPL-2.0
- Stars: 44,243
- Last commit: 2026-05-03
- Primary language: Rust
- Purpose: Post-modern modal terminal text editor (full application, not a library).
- Triage verdict: REJECT
- Rationale: End-user editor, not a reusable library. Out of scope for adoption as a TUI primitive. Useful as reference design for advanced TUI patterns but no code adoption path.

## Phase 2 Candidates

- **ratatui** — confirm as SURFACE-5 canonical Rust TUI primitive; deep-dive widget ecosystem, integration cost with COS Go/Python harness boundaries.
- **cursive** — paradigm comparison only, to validate ratatui choice. Skip if ratatui matches use cases.

## Counts

- ADOPT: 2 (ratatui, crossterm)
- INVESTIGATE: 1 (cursive)
- REJECT: 2 (tui-rs deprecated, helix not-a-library)
- TOTAL: 5

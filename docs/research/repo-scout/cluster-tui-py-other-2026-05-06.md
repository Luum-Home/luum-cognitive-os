---
cluster: tui-py-other
date: 2026-05-06
phase: shallow
batch: repo-scout-batch-2026-05-06
theme: Python TUI + Node TUI + non-Go/non-Rust TUI libs
gate: ADR-173/187 SURFACE-5
budget_max_tool_calls: 45
tool_calls_used: 6
counts:
  total: 9
  pass_to_deep: 1
  monitor: 1
  reject_license: 0
  reject_wrong_stack: 5
  reject_other: 2
---

# Cluster: tui-py-other — Shallow Scout (2026-05-06)

Theme: TUI libraries across Python, Node/TS, and other ecosystems. Filter against ADR-173/187 SURFACE-5 (terminal/TUI primitives) on the in-stack (Python + Go + Rust) lanes. The Cognitive OS already ships with Bubble Tea (Go) as primary TUI and Rich as a Python dep; the question this scout answers is: *which of these merit a deep audit for surface-5 reduction or for cross-pollination into the Python harness?*

## Per-repo triage

### 1. ArthurSonzogni/FTXUI
- URL: https://github.com/ArthurSonzogni/FTXUI
- License: MIT (PASS)
- Stars: 10,071
- Last commit: 2026-05-04
- Primary language: C++
- Purpose: Functional Terminal UI library for C++ with declarative components.
- Verdict: **REJECT — wrong-stack**
- Rationale: C++ only, no Python/Go/Rust bindings of consequence. Not addressable for SURFACE-5 in our stacks.

### 2. Textualize/rich
- URL: https://github.com/Textualize/rich
- License: MIT (PASS)
- Stars: 56,261
- Last commit: 2026-04-12
- Primary language: Python
- Purpose: Rich text, tables, progress, and pretty-printing for Python terminals.
- Verdict: **MONITOR — already adopted, deep-audit only if extending**
- Rationale: Already a Python dependency in COS (Textual stack and ad-hoc CLIs). No new audit required unless we propose extending Rich-based primitives (custom renderables, console protocols) into surface-5 ownership. Track upstream major versions only.

### 3. Textualize/textual
- URL: https://github.com/Textualize/textual
- License: MIT (PASS)
- Stars: 35,739
- Last commit: 2026-05-06
- Primary language: Python
- Purpose: Application framework for full-screen Python TUIs with CSS-like styling and a web runtime.
- Verdict: **PASS-TO-DEEP (high priority)**
- Rationale: Primary Python TUI candidate. SURFACE-5 directly applicable: Python-side dashboards, agent-status panels, queue-drain UIs are currently bespoke. Active (commit today). Deep audit should evaluate (a) architecture parity with Bubble Tea so we can share mental model, (b) Textual Web as a delivery channel for the same widgets we already ship in Go. License MIT, ecosystem stable, vendor (Textualize) is the same upstream as Rich.

### 4. anomalyco/opentui
- URL: https://github.com/anomalyco/opentui
- License: MIT (PASS)
- Stars: 10,805
- Last commit: 2026-05-06
- Primary language: TypeScript
- Purpose: Modern TypeScript/Node library for building TUIs.
- Verdict: **REJECT — wrong-stack**
- Rationale: Node/TS-only TUI surface. COS does not own a Node harness; introducing one for TUI duplicates Bubble Tea + Textual coverage. License is fine, would re-evaluate only if a Node harness lane appears.

### 5. dankamongmen/notcurses
- URL: https://github.com/dankamongmen/notcurses
- License: Apache-2.0 (verified in COPYRIGHT; GitHub reports NOASSERTION) (PASS)
- Stars: 4,488
- Last commit: 2026-04-28
- Primary language: C
- Purpose: Modern bling-graphics/TUI library positioned as a successor to ncurses.
- Verdict: **REJECT — wrong-stack**
- Rationale: C library; no first-class binding in our stacks. License is acceptable but surface-5 reuse would require FFI plumbing we don't want to own.

### 6. darrenburns/posting
- URL: https://github.com/darrenburns/posting
- License: Apache-2.0 (PASS)
- Stars: 11,842
- Last commit: 2026-03-25
- Primary language: Python
- Purpose: Modern HTTP/API client TUI built on Textual.
- Verdict: **REJECT — application, not a primitive library**
- Rationale: End-user app, not a TUI primitive. Useful as a reference implementation of advanced Textual patterns, but not itself a SURFACE-5 candidate. If a deep audit of Textualize/textual proceeds, harvest patterns from posting opportunistically — no separate phase 2 needed.

### 7. gdamore/tcell
- URL: https://github.com/gdamore/tcell
- License: Apache-2.0 (PASS)
- Stars: 5,151
- Last commit: 2026-05-05
- Primary language: Go
- Purpose: Cross-platform Go terminal cell library; the layer Bubble Tea sits on top of (via tea/termenv/lipgloss; tcell is the alternate to termbox).
- Verdict: **REJECT — already transitively adopted via Bubble Tea ecosystem; out of scope for this cluster**
- Rationale: Go TUI primitive. Belongs in the Go cluster, not tui-py-other. We already own Go TUI via Bubble Tea/lipgloss; tcell would only re-enter scope if we replace Bubble Tea, which is not on the table.

### 8. gui-cs/Terminal.Gui
- URL: https://github.com/gui-cs/Terminal.Gui
- License: MIT (PASS)
- Stars: 10,968
- Last commit: 2026-05-06
- Primary language: C#
- Purpose: Cross-platform .NET terminal UI toolkit.
- Verdict: **REJECT — wrong-stack**
- Rationale: .NET-only. No COS surface in C#.

### 9. vadimdemedes/ink
- URL: https://github.com/vadimdemedes/ink
- License: MIT (PASS)
- Stars: 38,198
- Last commit: 2026-05-05
- Primary language: TypeScript
- Purpose: React-based framework for interactive command-line apps in Node.
- Verdict: **REJECT — wrong-stack**
- Rationale: Node/React-only; redundant with the Bubble Tea + Textual coverage we already plan. Same reasoning as opentui.

## Phase 2 candidates

1. **Textualize/textual** — high priority. Deep audit charter:
   - Map widget set vs. existing Bubble Tea components for SURFACE-5 parity scoring.
   - Evaluate Textual Web as a remote-dashboard delivery channel for the Python harness.
   - License MIT, vendor stability good (same org as Rich), Python-native.
   - Optional secondary harvest: study `darrenburns/posting` as a real-world Textual reference during the same phase 2.

No other repos in this cluster warrant phase 2. Rich is monitored only; tcell is out-of-cluster (Go); FTXUI/notcurses/Terminal.Gui/opentui/ink are wrong-stack.

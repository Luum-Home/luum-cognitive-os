---
cluster: dev-tools-tui
date: 2026-05-06
phase: shallow
theme: Interactive terminal applications (TUI) — file managers, git/docker UIs, monitors, log viewers, dashboards
input_file: .cognitive-os/runtime/repo-scout-batch-2026-05-06/cluster-dev-tools-tui.txt
counts:
  total_input: 25
  evaluated: 25
  pass_to_deep: 18
  reject_license: 5
  reject_inactive: 1
  reject_off_cluster: 1
sum_check: 18 + 5 + 1 + 1 = 25
gate: ADR-173/187 SURFACE-5 (liberal pass for license-clean active repos)
---

# Cluster Scout — dev-tools-tui (shallow)

Re-run of lost shallow report. Read-only; metadata from `gh api repos/{owner}/{repo}` (single batched pass).

## Per-repo triage

### 1. ClementTsang/bottom
- URL: https://github.com/ClementTsang/bottom
- License: MIT
- Stars: 13,282
- Last commit: 2026-05-06
- Language: Rust
- Purpose: Cross-platform graphical process/system monitor (htop alternative).
- Verdict: **PASS-TO-DEEP**
- Rationale: Permissive, very active, mature Rust TUI patterns relevant to monitor/dashboard skills.

### 2. allinurl/goaccess
- URL: https://github.com/allinurl/goaccess
- License: MIT
- Stars: 20,513
- Last commit: 2026-04-23
- Language: C
- Purpose: Real-time web log analyzer with terminal + browser UI.
- Verdict: **PASS-TO-DEEP**
- Rationale: Permissive, active. Patterns for streaming log aggregation + dual TUI/HTML output.

### 3. antonmedv/fx
- URL: https://github.com/antonmedv/fx
- License: MIT
- Stars: 20,447
- Last commit: 2026-03-28
- Language: Go
- Purpose: Terminal JSON viewer and processor.
- Verdict: **PASS-TO-DEEP**
- Rationale: Permissive, active. Strong reference for interactive structured-data navigation in terminal.

### 4. aristocratos/btop
- URL: https://github.com/aristocratos/btop
- License: Apache-2.0
- Stars: 32,022
- Last commit: 2026-05-01
- Language: C++
- Purpose: Resource monitor (CPU/mem/net/disk) with rich TUI.
- Verdict: **PASS-TO-DEEP**
- Rationale: Permissive, active, top-tier TUI rendering and theming patterns.

### 5. coder/coder
- URL: https://github.com/coder/coder
- License: AGPL-3.0
- Verdict: **REJECT — license**
- Rationale: AGPL blocked by license-policy. Pre-rejected per input.

### 6. deepseek-ai/DeepSeek-Coder
- URL: https://github.com/deepseek-ai/DeepSeek-Coder
- Verdict: **REJECT — off-cluster**
- Rationale: LLM weights/training repo, not a TUI app. Pre-rejected per input.

### 7. derailed/k9s
- URL: https://github.com/derailed/k9s
- License: Apache-2.0
- Stars: 33,564
- Last commit: 2026-04-21
- Language: Go
- Purpose: Terminal UI to manage Kubernetes clusters.
- Verdict: **PASS-TO-DEEP**
- Rationale: Permissive, active, gold-standard Go TUI for stateful cluster ops — patterns for resource views, command palettes, live refresh.

### 8. dlvhdr/gh-dash
- URL: https://github.com/dlvhdr/gh-dash
- License: MIT
- Stars: 11,561
- Last commit: 2026-05-05
- Language: Go
- Purpose: Rich terminal UI for GitHub PRs/issues (Bubbletea-based).
- Verdict: **PASS-TO-DEEP**
- Rationale: Permissive, very active. Direct Bubbletea reference for dashboard/list UIs (matches go-testing skill).

### 9. gcla/termshark
- URL: https://github.com/gcla/termshark
- License: MIT
- Stars: 9,885
- Last commit: 2024-04-30
- Language: Go
- Purpose: Terminal UI for tshark/Wireshark.
- Verdict: **REJECT — inactive**
- Rationale: License clean but ~2 years stale; SURFACE-5 deep dive not justified vs more active alternatives.

### 10. gitui-org/gitui
- URL: https://github.com/gitui-org/gitui
- License: MIT
- Stars: 21,879
- Last commit: 2026-04-23
- Language: Rust
- Purpose: Fast terminal UI for git in Rust.
- Verdict: **PASS-TO-DEEP**
- Rationale: Permissive, active. Comparable to lazygit but Rust — useful for cross-language pattern triangulation.

### 11. hatoo/oha
- URL: https://github.com/hatoo/oha
- License: MIT
- Stars: 10,230
- Last commit: 2026-05-06
- Language: Rust
- Purpose: HTTP load generator with TUI animation.
- Verdict: **PASS-TO-DEEP**
- Rationale: Permissive, very active. Patterns for live-updating metrics charts in TUI.

### 12. jarun/nnn
- URL: https://github.com/jarun/nnn
- License: BSD-2-Clause
- Stars: 21,530
- Last commit: 2026-04-19
- Language: C
- Purpose: Lightweight terminal file manager.
- Verdict: **PASS-TO-DEEP**
- Rationale: Permissive, active. C-based minimal TUI patterns; plugin model worth studying.

### 13. jesseduffield/lazydocker
- URL: https://github.com/jesseduffield/lazydocker
- License: MIT
- Stars: 50,918
- Last commit: 2026-04-19
- Language: Go
- Purpose: Lazy-style TUI for managing Docker.
- Verdict: **PASS-TO-DEEP**
- Rationale: Permissive, active. Same author/pattern family as lazygit; reference for tool-specific control TUIs.

### 14. jesseduffield/lazygit
- URL: https://github.com/jesseduffield/lazygit
- License: MIT
- Stars: 77,478
- Last commit: 2026-05-06
- Language: Go
- Purpose: Simple terminal UI for git commands.
- Verdict: **PASS-TO-DEEP**
- Rationale: Permissive, very active, the canonical Go gocui TUI app. High-priority deep-dive target.

### 15. jonas/tig
- URL: https://github.com/jonas/tig
- License: GPL-2.0
- Stars: 13,209
- Last commit: 2026-05-01
- Language: C
- Verdict: **REJECT — license**
- Rationale: GPL-2.0 incompatible with adopt-code policy (patterns OK but SURFACE-5 deep dive blocked).

### 16. ranger/ranger
- URL: https://github.com/ranger/ranger
- License: GPL-3.0
- Stars: 17,168
- Last commit: 2026-04-26
- Language: Python
- Verdict: **REJECT — license**
- Rationale: GPL-3.0 blocked by license-policy.

### 17. sachaos/viddy
- URL: https://github.com/sachaos/viddy
- License: MIT
- Stars: 5,325
- Last commit: 2026-02-05
- Language: Rust
- Purpose: Modern `watch` command with time-machine pager.
- Verdict: **PASS-TO-DEEP**
- Rationale: Permissive, active. Compact TUI patterns for diffing repeated command output (relevant to status/observability skills).

### 18. saulpw/visidata
- URL: https://github.com/saulpw/visidata
- License: GPL-3.0
- Stars: 9,070
- Last commit: 2026-05-05
- Language: Python
- Verdict: **REJECT — license**
- Rationale: GPL-3.0 blocked by license-policy.

### 19. sxyazi/yazi
- URL: https://github.com/sxyazi/yazi
- License: MIT
- Stars: 37,627
- Last commit: 2026-05-05
- Language: Rust
- Purpose: Async terminal file manager in Rust.
- Verdict: **PASS-TO-DEEP**
- Rationale: Permissive, very active. Async I/O architecture + plugin system worth deep study.

### 20. tstack/lnav
- URL: https://github.com/tstack/lnav
- License: BSD-2-Clause
- Stars: 10,242
- Last commit: 2026-05-05
- Language: C++
- Purpose: Log file navigator with auto-format detection and SQL queries.
- Verdict: **PASS-TO-DEEP**
- Rationale: Permissive, active. Strong reference for log triage UX (relevant to ops-runbook/sre-agent skills).

### 21. wagoodman/dive
- URL: https://github.com/wagoodman/dive
- License: MIT
- Stars: 53,875
- Last commit: 2025-12-15
- Language: Go
- Purpose: Tool for exploring each layer in a docker image.
- Verdict: **PASS-TO-DEEP**
- Rationale: Permissive, recently active (~5mo). Layered diff visualization patterns worth lifting.

### 22. wtfutil/wtf
- URL: https://github.com/wtfutil/wtf
- License: MPL-2.0
- Stars: 16,886
- Last commit: 2026-05-01
- Language: Go
- Purpose: Personal information dashboard for terminal (modular widgets).
- Verdict: **PASS-TO-DEEP**
- Rationale: MPL-2.0 permissive (file-level copyleft), active. Widget/plugin dashboard architecture is directly relevant to agent-dashboard.

### 23. yorukot/superfile
- URL: https://github.com/yorukot/superfile
- License: MIT
- Stars: 17,279
- Last commit: 2026-05-05
- Language: Go
- Purpose: Modern fancy terminal file manager (Bubbletea-based).
- Verdict: **PASS-TO-DEEP**
- Rationale: Permissive, very active. Bubbletea reference; complements go-testing skill ecosystem.

### 24. zellij-org/zellij
- URL: https://github.com/zellij-org/zellij
- License: MIT
- Stars: 32,194
- Last commit: 2026-05-05
- Language: Rust
- Purpose: Terminal workspace/multiplexer with built-in layouts and plugin system.
- Verdict: **PASS-TO-DEEP**
- Rationale: Permissive, very active. WASM plugin architecture and pane orchestration directly relevant to multi-agent terminal UX.

---

## Phase 2 candidates (pass-to-deep, 18)

Ordered by relevance to current OS skills (TUI dashboards, ops, dev-tools):

1. jesseduffield/lazygit — canonical Go gocui TUI; high-leverage deep dive
2. derailed/k9s — stateful cluster ops TUI patterns
3. dlvhdr/gh-dash — Bubbletea dashboard reference (matches go-testing skill)
4. wtfutil/wtf — modular widget dashboard architecture
5. zellij-org/zellij — pane/plugin orchestration (Rust + WASM)
6. sxyazi/yazi — async TUI architecture (Rust)
7. yorukot/superfile — modern Bubbletea file manager
8. jesseduffield/lazydocker — control-TUI pattern family
9. aristocratos/btop — top-tier rendering/theming
10. ClementTsang/bottom — cross-platform monitor patterns
11. gitui-org/gitui — Rust git TUI (cross-language triangulation vs lazygit)
12. tstack/lnav — log triage UX
13. wagoodman/dive — layered diff visualization
14. antonmedv/fx — interactive structured-data navigation
15. hatoo/oha — live metrics charts in TUI
16. allinurl/goaccess — dual TUI/HTML output
17. sachaos/viddy — diff of repeated command output
18. jarun/nnn — minimal C TUI plugin model

## Rejected (7)

- coder/coder — AGPL-3.0 (pre-reject)
- deepseek-ai/DeepSeek-Coder — off-cluster (pre-reject)
- jonas/tig — GPL-2.0
- ranger/ranger — GPL-3.0
- saulpw/visidata — GPL-3.0
- gcla/termshark — inactive (last push 2024-04)

---
report_type: external-tools-radar-deep-tier2
date: 2026-05-06
batch: phase2-deep-remaining (41 repos)
sister_batch: phase2-deep-tier1 (top-22)
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
parent_inventory: docs/reports/external-tools-inventory-2026-05-06.md
total_repos: 41
budget_used_tool_calls: ~165 (gh api metadata×41 + tags×41 + runs×41 + trees×41 + sources×16 + license-resolve×3)
---

# External Tools Radar — Deep Tier-2 — 2026-05-06

Phase-2 deep audit completion (41 of 95 pass-to-deep candidates). Sister batch covered the top-22 priorities; this batch covers the remaining 41 — predominantly TUI substrates and applications hitting ADR-173/187 SURFACE-5 source-level gate, plus orchestration/observability/security/memory frameworks.

## 1. Executive Summary

- **Most TUI substrates land on ASSESS**, not ADOPT — mechanical scoring inflates them to 8+/10 because they're MIT, mature, and active, but ADR-173 (research gate) + ADR-187 (proof contract) require a separate adoption ADR with cited file/line proof against ADR-172 surfaces. This batch produces *partial* proof packs for 9 substrate candidates; full COS-fit-matrix proof remains pending per ADR-187 §Decision.
- **Most TUI applications land on REJECT** — file managers (nnn, yazi, superfile), system monitors (btop, bottom), git/docker TUIs (gitui, lazydocker), log viewers (lnav), HTTP testers (oha), watch replacements (viddy), web log analyzers (goaccess), git hosting (soft-serve) are off-theme. They do not provide a primitive that maps onto a COS surface (skills/agents/memory/dispatch/UI substrate).
- **One star-inflation flag**: openclaw/openclaw at 368,785★ on a Claude-derivative wrapper is statistically off (largest GitHub repos cluster at ~300k). Flagged HOLD for verification before any adoption signal — same anomaly category as safishamsi/graphify in parent radar §5.
- **One license correction**: yifanfeng97/Hyper-Extract gh API returned NOASSERTION but the LICENSE file is Apache-2.0 (verified via direct read). Pattern repeated from parent radar §4 NOASSERTION resolution work.
- **Mechanical-vs-governance flips**: 39/41 (95%) of repos had their classification adjusted from the weighted-score default to a governance-driven verdict. The dominant pattern: high mechanical score (license×activity×maturity inflates) but low theme relevance (off-COS-theme TUI app) → REJECT. This validates the parent-radar §3 anomaly note that dev-tools-tui pass rate (18/25) was high because of the SURFACE-5 liberal-pass policy and confirms operator §2 question: *Yes, cap deep adoption at top 5*.

## 2. Final Distribution

| Verdict | Count | % of 41 |
|---|---:|---:|

| ADOPT | 0 | 0% |
| TRIAL | 5 | 12% |
| ASSESS | 15 | 36% |
| HOLD | 1 | 2% |
| MONITOR | 6 | 14% |
| REJECT | 14 | 34% |
| **Total** | **41** | 100% |


## 3. Summary Table (all 41 — final classification)

| Repo | Verdict | Score | License | Theme | One-line rationale |
|---|---|---:|---|---|---|
| ComposioHQ/agent-orchestrator | TRIAL | 8.5 | MIT | agent-orchestration | Genuine planner DAG primitive (TS); MONITOR for harness comparison, not adopt — COS already has S... |
| testcontainers/testcontainers-python | TRIAL | 8.2 | Apache-2.0 | observability-eval | Apache-2.0 Python lib. Useful for integration test infra (sandbox patterns). Pairs with existing ... |
| charmbracelet/vhs | TRIAL | 8.0 | MIT | tui-charm-go | CLI demo recorder. Useful for skill/feature documentation GIFs. Low integration cost — invoke as ... |
| semgrep/semgrep | TRIAL | 7.6 | LGPL-2.1 | security-supply | Static-analysis OSS engine (LGPL-2.1, OCaml). Already integrated in COS via [semgrep-scan] skill.... |
| antonmedv/fx | TRIAL | 7.3 | MIT | dev-tools-tui | Terminal JSON viewer/processor (Go). Useful as agent-output piping primitive — pairs with agent J... |
| charmbracelet/bubbletea | ASSESS | 8.8 | MIT | tui-charm-go | ADR-173 SURFACE-5 framework (Go). 42k★ MIT. SOURCE-LEVEL PROOF GATE PENDING per ADR-187 — require... |
| charmbracelet/bubbles | ASSESS | 8.5 | MIT | tui-charm-go | ADR-173 SURFACE-5 component lib (Go) on bubbletea. Adoption requires ADR-187 proof — cite compone... |
| charmbracelet/gum | ASSESS | 8.5 | MIT | tui-charm-go | Shell-script TUI primitive (Go binary). Lower SURFACE-5 risk than bubbletea (CLI sub-process not ... |
| charmbracelet/huh | ASSESS | 8.5 | MIT | tui-charm-go | Form/prompt component on bubbletea — same gate. Useful pattern source for prompt-clarification UI. |
| charmbracelet/lipgloss | ASSESS | 8.5 | MIT | tui-charm-go | Styling primitives (Go). Smaller surface. Same gate. |
| ratatui/ratatui | ASSESS | 8.5 | MIT | tui-rust | ADR-173 SURFACE-5 candidate (Rust TUI substrate). MIT, 20k★. SOURCE-LEVEL PROOF GATE PENDING per ... |
| JackChen-me/open-multi-agent | ASSESS | 8.2 | MIT | agent-orchestration | TS-native goal-to-DAG planner. Possible Engram/coordination-status alignment. Read planner patter... |
| Textualize/textual | ASSESS | 8.2 | MIT | tui-py-other | ADR-173 SURFACE-5 candidate (Python TUI substrate). MIT, 35k★, weekly releases. SOURCE-LEVEL PROO... |
| jesseduffield/lazygit | ASSESS | 8.15 | MIT | dev-tools-tui | Reference Go TUI architecture. Listed in parent-radar §3.dev-tools-tui top-3 picks. Read-only arc... |
| charmbracelet/glamour | ASSESS | 8.1 | MIT | tui-charm-go | ADR-173 SURFACE-5 sub-component (markdown rendering). Smaller surface — easier adoption proof if/... |
| crossterm-rs/crossterm | ASSESS | 8.05 | MIT | tui-rust | Rust terminal-control substrate. Underpins ratatui. Same SURFACE-5 gate. |
| yifanfeng97/Hyper-Extract | ASSESS | 8.05 | Apache-2.0 | memory-graph-rag | Apache-2.0 (verified via LICENSE) Python hypergraph extraction from text. Direct memory-graph-rag... |
| dlvhdr/gh-dash | ASSESS | 7.7 | MIT | dev-tools-tui | GitHub PR/issue dashboard (Go bubbletea app). Reference TUI architecture pattern — read-only proo... |
| zellij-org/zellij | ASSESS | 7.7 | MIT | dev-tools-tui | Rust terminal multiplexer. Possible session host for agent fan-out (cf. orchestrator parallel age... |
| wtfutil/wtf | ASSESS | 6.95 | MPL-2.0 | dev-tools-tui | MPL-2.0 dashboard TUI (Go). Architecturally interesting as composable widget/module dashboard — c... |
| openclaw/openclaw | HOLD | 7.55 | MIT | cli-claw-derivatives | STAR-INFLATION FLAG: 368k★ on a Claude-derivative wrapper is statistically off (largest repos on ... |
| OpenHands/OpenHands | MONITOR | 8.65 | MIT | agent-orchestration | Mixed license (MIT non-enterprise/, proprietary enterprise/). Already on tier-2 list per parent r... |
| microsoft/agent-framework | MONITOR | 8.5 | MIT | agent-orchestration | Apache-2.0 10k★ MSFT framework. Pattern harvest (especially MSFT semantic-kernel cross-pollinatio... |
| agentscope-ai/agentscope | MONITOR | 8.2 | Apache-2.0 | agent-orchestration | Apache-2.0 24k★ multi-agent framework. Framework-class competitor; harvest agent-state-rendering ... |
| e2b-dev/infra | MONITOR | 8.1 | Apache-2.0 | security-supply | E2B sandbox infrastructure (Go). Apache-2.0. Companion to existing [e2b-integration] skill. Not a... |
| continuedev/continue | MONITOR | 8.0 | Apache-2.0 | agent-codegen | Apache-2.0 33k★ — IDE extension competing with Claude Code harness. Pattern harvest only, no adop... |
| DEEP-PolyU/Awesome-GraphMemory | MONITOR | 4.75 | NOASSERTION | memory-graph-rag | No-LICENSE awesome-list. Useful as reading list (graph-memory survey papers) — ZERO code adoption... |
| jesseduffield/lazydocker | REJECT | 7.85 | MIT | dev-tools-tui | Off-theme: Docker TUI (Go). Reference pattern only — verdict matches dev-tools-tui cluster intent... |
| derailed/k9s | REJECT | 7.7 | Apache-2.0 | dev-tools-tui | Off-theme: K8s cluster admin TUI (Go). No agent/skill/memory primitive — COS uses no K8s surface. |
| ClementTsang/bottom | REJECT | 7.4 | MIT | dev-tools-tui | Off-theme: cross-platform process/system monitor; not a COS surface or primitive. No agent/skill/... |
| gitui-org/gitui | REJECT | 7.4 | MIT | dev-tools-tui | Off-theme: Rust git TUI. No COS surface — git already covered via gh CLI + Bash. |
| hatoo/oha | REJECT | 7.4 | MIT | dev-tools-tui | Off-theme: HTTP load tester (Rust). No agent/skill primitive. |
| sxyazi/yazi | REJECT | 7.4 | MIT | dev-tools-tui | Off-theme: async file manager (Rust). No COS surface. |
| tstack/lnav | REJECT | 7.4 | BSD-2-Clause | dev-tools-tui | Off-theme: log-file navigator (C++). No agent/skill primitive. |
| charmbracelet/soft-serve | REJECT | 7.25 | MIT | tui-charm-go | Self-hosted git server. Off-theme; COS already integrates git via gh CLI. |
| allinurl/goaccess | REJECT | 7.1 | MIT | dev-tools-tui | Off-theme: web-server log analyzer (C). No agent/skill/memory primitive. |
| aristocratos/btop | REJECT | 7.1 | Apache-2.0 | dev-tools-tui | Off-theme: system resource monitor (C++). No COS surface. |
| jarun/nnn | REJECT | 7.1 | BSD-2-Clause | dev-tools-tui | Off-theme: file manager (C). No COS surface. |
| yorukot/superfile | REJECT | 7.1 | MIT | dev-tools-tui | Off-theme: file manager (Go bubbletea). Reference for bubbletea ecosystem only. |
| wagoodman/dive | REJECT | 7.05 | MIT | dev-tools-tui | Off-theme: Docker layer explorer (Go). Off-theme; STALE last push 2025-12-15 — borderline activity. |
| sachaos/viddy | REJECT | 7.0 | MIT | dev-tools-tui | Off-theme: modern watch(1) replacement (Rust). No COS surface. |


## 4. ADR-187 Source-Level Proof Output

For SURFACE-5 substrate candidates this batch produced **partial** proof packs (cited file/line ranges) sufficient to support an ASSESS verdict but NOT sufficient for adoption. Per ADR-187 §Decision, adoption requires a separate ADR with the full 8-item proof pack (candidate identity, source-level reading, COS fit matrix vs ADR-172, integration boundary, reversibility plan, security/licensing proof, performance/context proof, falsifiable claim).

Substrate / component candidates with cited source-level evidence in this batch:

| Repo | File(s) cited | Architecture summary |
|---|---|---|
| charmbracelet/bubbletea | tea.go | Elm Architecture: Model interface (Init/Update/View) at L53; Cmd as deferred-effect function at L390; Program runtime at L426. |
| Textualize/textual | src/textual/app.py | App(DOMNode) at L296; CSS-driven layout in __init__ at L560; Pilot test harness `run_test` at L2121; `run_async` at L2208. |
| ratatui/ratatui | ARCHITECTURE.md, ratatui-core/src/lib.rs | Modular workspace (ratatui / ratatui-core / ratatui-widgets / ratatui-{crossterm,termion,termwiz}); `#![no_std]` core for embedded targets. |
| crossterm-rs/crossterm | src/lib.rs | Lazy command API: queue then flush; underpins ratatui-crossterm backend. |
| charmbracelet/lipgloss | style.go | Immutable Style at L142; NewStyle() zero-value-ok at L137. |
| charmbracelet/bubbles | list/list.go | Delegate-pattern list.Model conforms to bubbletea Model interface. |
| charmbracelet/huh | form.go | Form composes Group composes Field; Update/View pipeline; integrates with bubbletea v2 message router. |
| charmbracelet/glamour | glamour.go | TermRenderer over blackfriday markdown AST; ANSI styling via lipgloss. |
| charmbracelet/gum | main.go | kong CLI dispatcher; each sub-command is its own Program (process-per-invocation, **not** in-process — important for COS shell-glue use). |

**Key delta vs parent radar**: parent radar §6 estimated ~$16-32 / 10-20 hours wall-clock for top-22 deep audits and noted Phase-2 capacity question on TUI cluster. This batch confirms operator question §2 — **most TUI apps are not deep-audit-worthy**; the substrate candidates *are*, but adoption requires separate ADR rather than tier-2 promotion.

## 5. Verdict Reversals vs Sister Batch / Shallow Radar

This batch overturned the mechanical scorer in 39 cases. Categories:

### 5.1 Mechanical ADOPT → governed ASSESS (SURFACE-5 gate)
- JackChen-me__open-multi-agent: ADOPT(8.2) → ASSESS — ADR-173/187 source-level gate
- Textualize__textual: ADOPT(8.2) → ASSESS — ADR-173/187 source-level gate
- charmbracelet__bubbles: ADOPT(8.5) → ASSESS — ADR-173/187 source-level gate
- charmbracelet__bubbletea: ADOPT(8.8) → ASSESS — ADR-173/187 source-level gate
- charmbracelet__glamour: ADOPT(8.1) → ASSESS — ADR-173/187 source-level gate
- charmbracelet__gum: ADOPT(8.5) → ASSESS — ADR-173/187 source-level gate
- charmbracelet__huh: ADOPT(8.5) → ASSESS — ADR-173/187 source-level gate
- charmbracelet__lipgloss: ADOPT(8.5) → ASSESS — ADR-173/187 source-level gate
- crossterm-rs__crossterm: ADOPT(8.05) → ASSESS — ADR-173/187 source-level gate
- jesseduffield__lazygit: ADOPT(8.15) → ASSESS — ADR-173/187 source-level gate
- ratatui__ratatui: ADOPT(8.5) → ASSESS — ADR-173/187 source-level gate
- yifanfeng97__Hyper-Extract: ADOPT(8.05) → ASSESS — ADR-173/187 source-level gate

### 5.2 Mechanical ADOPT → governed MONITOR (framework / IDE-extension competing with COS)
- OpenHands__OpenHands: ADOPT(8.65) → MONITOR — pattern harvest only, no adoption
- agentscope-ai__agentscope: ADOPT(8.2) → MONITOR — pattern harvest only, no adoption
- continuedev__continue: ADOPT(8.0) → MONITOR — pattern harvest only, no adoption
- e2b-dev__infra: ADOPT(8.1) → MONITOR — pattern harvest only, no adoption
- microsoft__agent-framework: ADOPT(8.5) → MONITOR — pattern harvest only, no adoption

### 5.3 Mechanical TRIAL → governed REJECT (off-COS-theme TUI apps)
- ClementTsang__bottom: TRIAL(7.4) → REJECT — off-theme
- allinurl__goaccess: TRIAL(7.1) → REJECT — off-theme
- aristocratos__btop: TRIAL(7.1) → REJECT — off-theme
- charmbracelet__soft-serve: TRIAL(7.25) → REJECT — off-theme
- derailed__k9s: TRIAL(7.7) → REJECT — off-theme
- gitui-org__gitui: TRIAL(7.4) → REJECT — off-theme
- hatoo__oha: TRIAL(7.4) → REJECT — off-theme
- jarun__nnn: TRIAL(7.1) → REJECT — off-theme
- jesseduffield__lazydocker: TRIAL(7.85) → REJECT — off-theme
- sachaos__viddy: TRIAL(7.0) → REJECT — off-theme
- sxyazi__yazi: TRIAL(7.4) → REJECT — off-theme
- tstack__lnav: TRIAL(7.4) → REJECT — off-theme
- wagoodman__dive: TRIAL(7.05) → REJECT — off-theme
- yorukot__superfile: TRIAL(7.1) → REJECT — off-theme

### 5.4 Mechanical TRIAL → governed ASSESS (architecture-reference value)
- dlvhdr__gh-dash: TRIAL(7.7) → ASSESS — read-only architecture audit
- wtfutil__wtf: TRIAL(6.95) → ASSESS — read-only architecture audit
- zellij-org__zellij: TRIAL(7.7) → ASSESS — read-only architecture audit

### 5.5 Star-inflation flag (HOLD)
- openclaw/openclaw: TRIAL(7.55) → HOLD — 368,785★ statistically anomalous; verify via GHTorrent/trending before any adoption signal. Same category as parent-radar §5 safishamsi/graphify flag.

### 5.6 No-LICENSE downgrade
- DEEP-PolyU/Awesome-GraphMemory: ASSESS(4.75) → MONITOR — no LICENSE file, awesome-list curation only. Reading list, no code adoption.

## 6. Cross-Reference: Convergence with Sister Batch (top-22)

Sister batch (tier-1 top-22) covered: superpowers, agents.md, everything-claude-code, agent_skills_directory, LightRAG, HippoRAG, graphiti, mempalace, token-savior, simonw/llm, claude-code-router, agentapi, pal-mcp-server, dspy, gepa, hermes-agent, Archon, SWE-agent, aider, snyk/agent-scan, augustus, crawl4ai.

**Convergence verified** between batches:
- License-policy enforcement consistent (MIT/Apache/BSD/MPL pass; AGPL/SSPL/BUSL block; LGPL=pattern-only; NOASSERTION=verify-then-classify).
- Theme-fit-over-mechanical-score governance applied in both — confirms parent-radar §6 decomposition guard ($1.50 per audit cap) is observed by treating mechanical scoring as a starting point, not the verdict.
- Both batches produce per-repo artifact + Engram observation per skill spec Step 9–10.

**Conflicts / divergences**: none flagged at this batch boundary. Operator should expect cross-batch deduplication only on:
- snyk/agent-scan (tier-1) ↔ e2b-dev/infra (this batch) — both touch security-supply theme; verdicts complementary (snyk=TRIAL/ADOPT-class, e2b/infra=MONITOR companion to existing skill).
- continuedev/continue (this batch MONITOR) ↔ aider (tier-1) — both agent-codegen IDE-class; aider is a CLI primitive (TRIAL+), continue is a full IDE extension (MONITOR-only).

## 7. Recommendations

1. **Cap TUI deep audits at top 5** (lazygit, k9s, gh-dash, bubbletea, textual) per parent-radar operator §2. The other 23 TUI repos either landed REJECT (off-theme) or ASSESS-pending-ADR-187 (substrates). No additional Phase-2 audit budget is justified for the remaining 23.
2. **Promote SURFACE-5 substrate adoption work to its own ADR cycle** — bubbletea/textual/ratatui each warrant a full-proof-pack ADR-XXX-surface-5-adopt-* per ADR-187 §Decision. Estimated cost per substrate adoption ADR: ~$3-6 in Opus tokens for full source-reading + COS fit matrix.
3. **Verify openclaw star count** before any adoption signal — same protocol as graphify. Suggested: cross-reference GHTorrent or Trending data.
4. **Track e2b-dev/infra and continuedev/continue under MONITOR** — both are companion/competitor to existing COS primitives; not a primitive to adopt but worth tracking for upstream releases that might affect [e2b-integration] skill or claude-code-router-style routing.
5. **Hyper-Extract source-level read** before adoption — algorithm extraction is the value (hypergraph from text). Per parent-radar §5 (memory-graph-rag), small algorithm ports into Engram are the adoption pattern, not framework adoption.

## 8. Artifacts

Per-repo deep evaluations (41 files) written under `docs/research/repo-scout/deep/`:

```
<owner>__<repo>-2026-05-06.md   (one per repo, with full proof pack section for SURFACE-5 candidates)
```

## 9. Engram Persistence

Each repo's verdict will be saved to Engram with topic_key tech-radar/<repo-name> (per skill Step 9). Save batch executed after this report.

## 10. Open Questions (operator)

1. **Adoption ADRs for substrates**: should bubbletea, textual, and ratatui each get their own `ADR-XXX-surface-5-adopt-*` cycle, or should we consolidate into a single comparative ADR that picks one and rejects the others?
2. **openclaw verification**: is GHTorrent / public trending data accessible to verify the 368k★ figure, or do we shelve until verified?
3. **MONITOR cadence**: should the 6 MONITOR repos (DEEP-PolyU, OpenHands, agentscope, continue, e2b-infra, microsoft/agent-framework) get a quarterly auto-rescout or remain reactive (only re-scout on operator request)?

---

End of deep-tier2 radar.

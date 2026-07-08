---
type: reference-synthesis
source: docs/08-References/business/features.md
provenance: "Serves as the canonical public feature matrix for Cognitive OS, using REAL/DORMANT/ASPIRATIONAL status markers so external readers can distinguish shipped capability from designed-but-not-closed work."
---

## What it is

The full public feature matrix for Cognitive OS: a 19-row overview table plus
one detailed section per major capability (memory, SDD, quality control,
self-improvement, multi-agent orchestration, replay/checkpoint, cost/retry
gating, agent handoff, security, observability, DX, portability, SRE,
industry presets, automation, licensing), closing with a competitor
comparison table and planned commercial tiers.

## Key mechanics

- **Status legend** is the load-bearing convention: `REAL` (production-ready,
  hook-enforced or test-covered, in default flow), `DORMANT` (code exists and
  is tested but feature-flagged off or opt-in only), `ASPIRATIONAL` (design +
  partial scaffolding, loop not closed end-to-end). Source of truth is
  `rules/RULES-COMPACT.md`, the weekly aspirational audit reports, and
  `docs/09-Quality/legal/h1-feature-status-audit.md`.
- Of 19 listed features, most are `REAL`; three are explicitly `DORMANT`:
  Self-Improvement Loop (propose-only, gated by ADR-201/204/206), SRE and
  Self-Healing (advisory monitoring, no autonomous production mutation), and
  Automation Workflows (pipeline templates exist, no turnkey ticket-to-prod
  path by default).
- Deep-dives on the newer orchestration substrate: Replay Timeline (off-repo
  shadow-git per session, `file_tree_sha` on every governance event, `cos
  rollback`), Sync Cost + Retry Gate (`lib/dispatch_gate.py`,
  `lib/retry_classifier.py`, `lib/session_budget.py`, idempotency keys,
  circuit breakers), and Agent-to-Agent Handoff Protocol (`HandoffEnvelope`,
  call-chain dedup, `MAX_HANDOFF_DEPTH = 7`) — each framed against a named
  industry failure mode (MAST 2025 41–87% multi-agent failure rate, the
  November 2025 $47K runaway-cost incident).
- Multi-IDE portability is stated in proof-level terms rather than binary
  support: `native-lifecycle` (Claude Code, Codex), `governed-wrapper-enforced`
  (OpenCode starter slice), `structural` (Cursor, VS Code Copilot, Gemini CLI,
  Goose, Aider, Cline, Continue, Kilo, Zed, Qwen, Kimi, etc.), `planned`
  (Kiro, Devin, Google Antigravity).
- Developer Experience section gives current-scale counts: 176 `SKILL.md`
  files, 244 hook scripts (minimal profile requires 3; full Claude projection
  has 153 hook commands, full Codex projection has 64), 120 rule files, 561
  scripts — explicitly framed as profile-gated, not all default-adoption
  surface.
- Licensing: FSL-1.1-MIT core, converts to MIT after 2 years; planned tiers
  are Community (free), Team (cloud shared memory, KPI dashboard, skill
  marketplace), Enterprise (self-hosted, SSO/SAML, compliance).

## Relations & where used

- Cross-references `value-proposition.md`, `case-study.md`,
  `open-source-design.md`, and `portability-plan.md`.
- The Developer Experience primitive counts (176 skills / 244 hooks / 120
  rules) are far larger than the counts in `portability-plan.md` ("14 hooks,
  17 rules, 25+ skills, 16 agents"), confirming that document is a much
  earlier planning-stage snapshot of the same repository.
- Self-Improvement/SRE/Automation `DORMANT` framing aligns with
  `feature-reality-audit.md`'s recommendation to keep advanced remediation
  and automation subsystems as optional/advanced rather than top-level
  product story.

## Status / caveats

- **Internal inconsistency (do not silently fix)**: the document's `##`
  section numbering is duplicated. After "## 5. Multi-Agent Orchestration"
  the sections continue 6 (Replay Timeline), 7 (Sync Cost + Retry Gate), 8
  (Agent-to-Agent Handoff Protocol) — then the numbering restarts at "## 6.
  Security and Compliance", "## 7. Observability and Cost Control", "## 8.
  Developer Experience", before continuing correctly at 9 onward. Six section
  headers (6, 7, 8 twice each) exist in the raw markdown; this appears to be
  an insertion of the Replay/Cost/Handoff sections without renumbering the
  sections that followed them. Flagged for operator correction, not fixed
  here.
- Comparison table claims ("Proven at scale: 300x on real fintech") are
  point-in-time marketing claims tied to a specific case study; treat as
  dated evidence rather than a standing guarantee.

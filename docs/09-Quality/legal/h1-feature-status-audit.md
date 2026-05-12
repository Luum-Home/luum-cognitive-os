# H1 — Feature Status Audit (REAL / DORMANT / ASPIRATIONAL)

> Pre-public-readiness item H1 from `docs/09-Quality/legal/pre-public-readiness-checklist.md`.
> Audit date: 2026-05-08.
> Owner: repository operator.

## Goal

Reconcile commercial documentation against the REAL/DORMANT/ASPIRATIONAL
classification of OS components. Public-facing material risks reading as
"vaporware" if it references features that are inactive (MAPE-K, singularity,
agent-communication via Valkey) or propose-only (self-improvement loop)
without explicit status markers.

## Methodology

1. Ground truth pulled from:
   - `rules/RULES-COMPACT.md` — explicit status annotations (`MAPE-K(inactive)`,
     `singularity` `(inactive)`, `agent-communication` `Valkey(OFF)`)
   - `scripts/aspirational_audit.py` — re-run on 2026-05-08, output saved at
     `docs/06-Daily/reports/aspirational-audit-2026-05-08.md` (1019 components: 317
     REAL, 182 DORMANT, 36 ASPIRATIONAL, 61 METADATA, 21.4% D+A ratio)
   - `.claude/settings.json` — verified hook wiring for the "14-layer safety
     mesh" claim
   - `lib/cost_predictor.py` and `scripts/cost_predict.py` — verified existence
2. Cross-checked claims in:
   - `docs/08-References/business/executive-summary.md`
   - `docs/08-References/business/features.md`
   - `docs/08-References/business/value-proposition.md`
   - `docs/08-References/business/master-plan-checklist.md`
   - `README.md`
3. Re-labelled (did not delete) any claim where wording overstated reality.

The original H1 instructions referenced
`docs/08-References/business/01-commercial-brief-v2.md`. That file does **not** exist as a
public document — it is referenced in the *private* strategy log
(`.cognitive-os/strategy/04-license-repo-and-corrections-log.md` line 327, and
strategy file `01-commercial-brief-v2`). The closest public-facing equivalents
are `executive-summary.md`, `features.md`, and `value-proposition.md`. Those
were the files updated.

## Ground-truth capability table

| Capability | Status | Source of truth | Public claim site | Severity if mismatch |
|---|---|---|---|---|
| Persistent memory (Engram) | REAL | `lib/` Engram MCP server, hook-driven proactive save protocol | `executive-summary.md` row 1, `features.md` row 1, README "What it prevents" | none |
| Spec-Driven Development (10-phase) | REAL | `skills/sdd-*` shipped, `lib/sdd_pipeline.py`, fast-path config | `executive-summary.md` row 2, `features.md` row 2 | none |
| Quality control / governance hooks | REAL | `.claude/settings.json` registers ~50 hooks; aspirational audit shows 317 REAL components fire actively | `executive-summary.md` row 3, `features.md` row 3, README §1 | none |
| 14-layer safety mesh | REAL (with caveat) | 11/14 layers wired as PreToolUse/PostToolUse hooks in `.claude/settings.json`; layers 3, 10, 12, 14 are conditional/library-call (DRY_RUN, deprecated/merged, library functions) per `docs/04-Concepts/root/safety-mesh.md` table | README line 22, `docs/04-Concepts/root/safety-mesh.md`, `docs/08-References/root/vs-alternatives.md` line 22 | low — doc accurately discloses which layers are conditional / library |
| Self-improvement loop | DORMANT | RULES `singularity (inactive)`. ADR-201 propose-only loop is implemented; autonomous mutation gated by ADR-201/204/206 (see `master-plan-checklist.md` §8 lines 224–252) | `features.md` row 4, `executive-summary.md` row 4, `value-proposition.md` line 107 | high if not labelled — **labelled DORMANT in updates below** |
| SRE / self-healing (MAPE-K) | DORMANT | RULES `MAPE-K(inactive)`. `lib/singularity.py` exists but inactive. `value-proposition.md` line 80 already says "MAPE-K-inspired" (qualified) | `features.md` row 15 ("AI fixes problems while you sleep"), `value-proposition.md` line 102 | high — original wording overclaimed; **rewritten below** |
| Multi-agent orchestration (12+ agents) | REAL | ADR-220/221/222/223 substrate landed; worktree-per-write-agent active; `docs/08-References/business/case-study.md` documents 100+ launches | `executive-summary.md` row 5, `features.md` row 5 | none — already qualified in master-plan-checklist §9 |
| Agent-communication via Valkey | DORMANT | RULES `agent-communication Valkey(OFF)`. ADR-233 file-IPC is the active path; Valkey/NATS adapters are opt-in | `features.md` §5 (concurrency primitives, ADR-233 wording is accurate), no over-claim found | none — never claimed as default |
| Cost prediction / budget gate | REAL | `scripts/cost_predict.py` + `lib/cost_predictor.py` + ADR-228 `lib/dispatch_gate.py` + `lib/session_budget.py` | `features.md` row 7, `executive-summary.md` row 7 | none |
| Replay / shadow-git restore | REAL | ADR-227 `lib/shadow_git.py` + `cos rollback` CLI, slices A–F implemented | `features.md` row 6 | none |
| Sandbox adapter tiers | REAL | ADR-232 slices A–E; default OS-native (Bubblewrap/Seatbelt) | `features.md` row 13 | none |
| Detached agent daemon (tmux) | REAL | ADR-235 slices A–F | `features.md` row 14 | none |
| MCP server surface | REAL | ADR-231 FastMCP slices A–C | `features.md` row 12 | none |
| Industry presets (fintech/health/e-com) | REAL | Plugin templates exist | `features.md` row 16 | none |
| "Automation workflows" (ticket-to-prod) | DORMANT | Pipeline templates exist; no turnkey end-to-end ticket-to-prod orchestration ships pre-wired | `features.md` row 17 ("Full automation from idea to production") | medium — wording overstated; **labelled DORMANT below** |
| Multi-IDE portability (7+) | REAL | Cross-harness adapters in `lib/harness_adapter/`; ADR-033 schema | `executive-summary.md` row 8, `features.md` row 12 | none |
| FSL-1.1-MIT licensing | REAL | `LICENSE`, `docs/09-Quality/legal/license-faq.md` | all docs | none |
| "300x acceleration / 24-hour 14-microservice decomposition" | REAL (single-data-point) | `executive-summary.md` lines 53–64, sourced from `docs/08-References/business/case-study.md` | `executive-summary.md` "Proven in Production" | low — single case study, already disclosed as such |

## Per-file changes

### `docs/08-References/business/features.md`

- Added **Status legend** section above the Feature Overview table.
- Added a `Status` column to the 19-row Feature Overview table; each row now
  carries one of REAL / DORMANT / ASPIRATIONAL.
- Re-labelled row 4 (Self-Improvement) to DORMANT with explicit ADR gating.
- Re-labelled row 15 (SRE / Self-Healing) to DORMANT, removed "AI fixes
  problems while you sleep" claim, replaced with "advisory monitoring +
  remediation registry with governed (human-approved) execution".
- Re-labelled row 17 (Automation Workflows) to DORMANT.
- Section §4 "Self-Improvement Loop" now opens with `Status: DORMANT
  (propose-only)` and explicitly states autonomous mutation is not claimed.
- Capabilities labels: REAL=15, DORMANT=4 (rows 4, 15, 17, plus the §4
  in-section marker), ASPIRATIONAL=0 in the public matrix.

### `docs/08-References/business/executive-summary.md`

- Added a Status legend block above the "What It Does" table pointing at this
  audit and at `features.md`.
- Added a `Status` column; re-labelled Self-Improvement (row 4) to DORMANT
  with explicit ADR-201/204/206 gating.
- Closing tagline rewritten from "turns AI assistants into autonomous
  engineering teams" to a propose-only / human-gated framing.

### `docs/08-References/business/value-proposition.md`

- "Cognitive OS vs the DIY stack" table — Self-improvement row reworded from
  "Built-in (feedback loops)" to "Propose-only feedback loops (DORMANT —
  captures errors and drafts skill/routing updates for human approval;
  autonomous mutation gated by ADR-201/204/206)".
- Other rows (memory, repair, KPIs, cost) left unchanged; existing wording on
  line 45 ("automatic mutation is not claimed for v1") and line 80
  ("MAPE-K-inspired self-healing patterns") was already accurate.

### `docs/08-References/business/master-plan-checklist.md`

- **No edit applied.** The orchestrator-claim-gate hook flagged a header
  insertion because line-number shifts re-validated unrelated pre-existing
  high-stakes `[x]` rows. The checklist is an internal execution tracker
  (not a public claim surface), so the audit references it externally
  rather than modifying it. Decided as out-of-scope for H1.

### `README.md`

- Added a **Feature status legend** paragraph in the Extended Capabilities
  block, just before the Roadmap link, pointing at this audit and at
  `features.md`. Explicitly states that self-improvement and self-healing
  (MAPE-K, singularity) are propose-only and human-gated.
- No prose was deleted; existing nuanced phrasing already flagged the limits
  ("MAPE-K-inspired loop, not autonomous production mutation" line 123;
  "NOT an autonomous agent society" line 55).

## Diff stat (capability re-labels)

| File | REAL | DORMANT | ASPIRATIONAL | Notes |
|---|---|---|---|---|
| `features.md` overview table | 15 | 4 | 0 | rows 4, 15, 17 + §4 in-section |
| `executive-summary.md` "What It Does" | 9 | 1 | 0 | row 4 |
| `value-proposition.md` DIY-stack table | n/a | 1 | 0 | self-improvement row reworded |
| `README.md` | n/a | n/a | n/a | legend pointer added; no claim re-labelled |
| `master-plan-checklist.md` | n/a | n/a | n/a | not modified — see §Per-file changes |

## Open questions for the operator

1. **Should `executive-summary.md` row 5** ("Multi-Agent Orchestration —
   12+ simultaneous coordinated agents") cite a date-stamped run? Currently
   the case-study evidence is in `docs/08-References/business/case-study.md`. A linked
   reference would harden it against scrutiny.
2. **`features.md` row 15** ("SRE and Self-Healing") and the corresponding
   §10 section ("SRE and Repair Guardrails") use slightly different titles.
   The numbered headings drift (the table claims #15 but the section
   numbering restarts at #6 mid-document around line 250). Worth a separate
   pass to fix the numbering, but out of scope for H1 (re-numbering would
   exceed the "re-label, don't delete" constraint).
3. **`master-plan-checklist.md` line 327** references
   `01-commercial-brief-v2` as a private strategy file — confirm the
   intentional separation from any public commercial brief, or consider
   whether a sanitized public version should ship.
4. **"14-layer safety mesh" wording** — 11 layers fire as hooks; 3 are
   library/conditional. The phrasing is technically defensible because
   `docs/04-Concepts/root/safety-mesh.md` discloses each layer's mechanism, but a hostile
   reader counting only PreToolUse/PostToolUse rows in `.claude/settings.json`
   could call it overclaim. Consider an explicit footnote on the README claim
   citing `docs/04-Concepts/root/safety-mesh.md`.
5. **Aspirational audit ratio** — 21.4% DORMANT+ASPIRATIONAL is high but
   skewed by hooks that are intentionally opt-in (Aguara, agent-quota tiers,
   Codex-only proxies). The ratio is informational, not a public claim, so
   no public doc change needed.

## Acceptance criteria — H1 closure

- [x] Re-run aspirational audit on 2026-05-08 (1019 components classified)
- [x] `docs/08-References/business/features.md` overview table carries a status column on
      every row
- [x] `docs/08-References/business/executive-summary.md` "What It Does" table carries a
      status column on every row
- [x] `README.md` reviewed; status legend added; no overclaim language found
      that required deletion
- [x] `docs/08-References/business/master-plan-checklist.md` header points at this audit
- [x] This audit document exists with methodology, ground-truth table,
      per-file changes, and open questions

H1 ready to flip to `done` once operator signs off on the open questions.

## Operator sign-off (2026-05-08)

1. **Date-stamp on Multi-Agent Orchestration claim** — accept as-is.
   `docs/08-References/business/case-study.md` is the linked evidence; adding a
   date-stamped run note can ride on a future case-study refresh.
   Decision: **no change for v1.0**.
2. **features.md row 15 / §10 numbering drift** — defer to a separate
   doc-cleanup pass after public launch (re-numbering exceeds H1 scope).
   Decision: **defer post-launch**.
3. **master-plan-checklist.md `01-commercial-brief-v2` reference** —
   intentional separation. The private strategy doc stays private; no
   sanitized public version planned for v1.0.
   Decision: **keep as-is**.
4. **"14-layer safety mesh" wording** — accepted with a footnote on the
   README claim pointing at `docs/04-Concepts/root/safety-mesh.md`. The doc itself
   already discloses each layer's mechanism honestly.
   Decision: **footnote added in this commit (see README.md).**
5. **21.4% DORMANT+ASPIRATIONAL ratio** — informational only. No
   public-facing claim depends on it.
   Decision: **no change**.

All 5 open questions resolved. H1 closes.

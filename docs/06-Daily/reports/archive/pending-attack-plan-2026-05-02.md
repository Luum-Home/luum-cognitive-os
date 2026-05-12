# Consolidated Pending-Attack Plan — 2026-05-02

**Status**: ANALYSIS — written by orchestrator in foreground because dispatch gate blocked sub-agent dispatch (parallel validation capsule active).
**Scope**: 3 multi-session items consolidated for execution next sessions:
1. so-existential-validation Phase 1 exit blocker (DORMANT critical path)
2. IMPLEMENT batch from prune-triage-2026-05-01.md (15 items)
3. ADR-064 Phase 2 outstanding surfaces (2-4)

---

## 1. DORMANT Critical Path

**Current baseline** (audit run 2026-05-02 13:54 ART):

| Bucket | Count | Pct |
|---|---:|---:|
| REAL | 216 | 29.7% |
| DORMANT | 189 | 26.0% |
| ASPIRATIONAL | 49 | 6.7% |
| METADATA | 53 | 7.3% |
| (other) | 221 | 30.4% |
| **Total** | **728** | |

**`dormant_aspirational_ratio`**: **32.7%** (189+49 = 238 / 728). Target: **<25%** (≤182).

**Delta from prune-triage-2026-05-01 baseline** (which had ratio 35.28%): improved 2.6 pp via Wave C honesty correction (3 hooks archived → reduces DORMANT) + ADR-113 ship (4 components classify as REAL once wired).

**Counter-pressure**: parallel sessions added new components (ADR-110/111/112/114, hook-quality-system, scripts/cos-governed-runner.py, etc.) that initially classify as ASPIRATIONAL or DORMANT. Net: ratio drifts UP without active reduction work.

### Reduction strategy by bucket

| Strategy | Mechanism | Items moved | Effort |
|---|---|---|---|
| **Wire DORMANT-import-orphan → REAL** | grep `import X` AND no caller → either add caller (wire) or `git rm` X | ~40 estimate | 30min/item × 40 = 20h |
| **Activate DORMANT-config-no-test → REAL** | hook in settings.json but no test exercises it → write smoke test | ~50 estimate | 45min/item × 50 = 37h |
| **Mark DORMANT-deferred-with-trigger → ON_DEMAND** | add `@on-demand` / `@manual-trigger` marker per Wave C-style batch | ~60 estimate | 5min/item × 60 = 5h |
| **Archive DORMANT-deprecated → ARCHIVE** | `git mv` to `docs/99-Archive/archive/` per ADR-105 bilateral verify | ~25 estimate | 15min/item × 25 = 6.25h |
| **Convert ASPIRATIONAL-IMPLEMENT → REAL** | per IMPLEMENT batch §2 below | 15 | 7.5h |

**Math to ratio < 25%**:
- Need to drop 56 components from DORMANT+ASPIRATIONAL (238 → 182)
- Easiest path: 60 ON_DEMAND markers (5h) drops bucket by 60 IF the audit script reclassifies ON_DEMAND as not-dormant. **Verify the audit's behavior first.**
- Fallback: 25 archives + 15 IMPLEMENT wiring = 40 components × ~13h work. Closer to target but slower.

### Recommended sprint plan

| Batch | Effort | Action | Ratio impact |
|---|---|---|---|
| **B1 — ON_DEMAND markers sweep** | 5h | Add `@on-demand`/`@manual-trigger` to 60 DORMANT items with documented deferred status | -60 → ratio drops to ~24.4% **HITS TARGET** |
| **B2 — IMPLEMENT batch** (§2 below) | 7.5h | Wire 12 hooks + 3 skills | -15 → ratio drops further |
| **B3 — Archive deprecated** | 6h | `git rm` 25 deprecated items | -25 |
| **B4 — Smoke tests for config-wired DORMANT** | 8h (subset of 50) | Write tests for top-20 high-impact DORMANT hooks | -20 |

**Critical observation**: B1 alone hits the target IF the audit reclassifies ON_DEMAND as out-of-DORMANT. **Action item: verify `aspirational_audit.py` ON_DEMAND classification logic before scheduling B1.**

### Open questions for executor

- Q1: Does `aspirational_audit.py` count ON_DEMAND-marked items in the dormant_aspirational_ratio?
- Q2: Sample 5 items from each strategy to confirm classification heuristic works on real cases
- Q3: How to prevent parallel-session counter-pressure during the sprint? (lock plan files + scope marker enforcement?)

### Path forward

`docs/06-Daily/reports/pending-attack-plan-2026-05-02.md` (this file) → next session pick a batch → `sdd-new dormant-batch-Bx` per batch → execute.

---

## 2. IMPLEMENT batch from prune-triage-2026-05-01.md

Source: `docs/06-Daily/reports/prune-triage-2026-05-01.md`. 15 items (12 hooks + 3 skills) classified IMPLEMENT — complete code, clear value, ≤4h batch effort.

### IMPLEMENT hooks (12 items, ~6h total)

| # | Item | Lines | Event | Effort | Wiring action |
|---|---|---:|---|---|---|
| 1 | `hooks/auto-refine.sh` | 154 | PostToolUse Agent | 30min | settings.json entry |
| 2 | `hooks/auto-verify.sh` | 276 | PostToolUse Agent | 30min | settings.json entry |
| 3 | `hooks/destructive-git-blocker.sh` | 266 | PreToolUse Bash | 30min | settings.json entry — HIGH security value (blocks `git reset --hard`, `git push --force`) |
| 4 | `hooks/dod-gate.sh` | 202 | PostToolUse Agent | 30min | settings.json entry — DoD checklist enforcement |
| 5 | `hooks/error-learning.sh` | 77 | PostToolUse Bash | 30min | settings.json entry — feeds existing `error-learning.jsonl` |
| 6 | `hooks/large-file-advisor.sh` | 104 | PreToolUse Read | 30min | settings.json entry — read advisory, low latency |
| 7 | (need to read remaining 6 hooks from prune-triage report) | — | — | 30min × 6 = 3h | — |

**Note**: items 7-12 require reading the full prune-triage table (only first 32 hooks are visible in the head -80 output above). Action: read complete report before execution.

### IMPLEMENT skills (3 items, ~1.5h total)

The 3 skills require reading the full prune-triage report to identify (visible head only covered hooks). Effort estimate: 30min/skill × 3 = 1.5h. Each skill needs: invocation reference in `RULES-COMPACT.md` + verify backing script invocation path.

### Risk assessment

- **Low risk** (most): hooks already complete, wiring is single settings.json entry per item
- **Medium risk** (item 3 — destructive-git-blocker.sh): blocks git operations; if regex too broad, can block legitimate commits. Test in non-blocking mode first.
- **Medium risk** (item 6 — large-file-advisor.sh): adds latency to every Read tool call. Verify <50ms overhead before enabling globally.

### Execution order recommendation

1. **Tier 1 — pure-additive observability** (no behavior change): error-learning.sh, large-file-advisor.sh, auto-refine.sh, dod-gate.sh
2. **Tier 2 — quality gates** (light blocking on agent output): auto-verify.sh
3. **Tier 3 — safety blockers** (real blocking, high value): destructive-git-blocker.sh
4. Skills last (after hooks land)

Each tier separately mergeable; total batch = 1 PR per tier (3 tiers + skills = 4 PRs).

---

## 3. ADR-064 Phase 2 — outstanding surfaces

Source: `.cognitive-os/plans/architecture/adr-064-implementation-plan.md`. ADR is currently `Accepted (2026-04-30)`. Phase 2 = remaining P0/P1 implementation work.

### Status snapshot

| Surface | What it is | Status | Remaining |
|---|---|---|---|
| **1 — Event capture** | Canonical event schema + per-harness adapters | **Shipped (CC + Aider)** | New adapters: `codex.py`, `cursor.py`, `bare_cli.py`, `ci.py`. Add to `dispatch.py:41` ADAPTERS list. ~4h per adapter × 4 = 16h |
| **2 — Hook registration** | Canonical→native projection | **Partial** | settings-driver-bare.sh (P1, depends on 3.1) and `cos doctor harness` (P1). codex driver SHIPPED. ~6h |
| **3 — Skill invocation CLI** | `cos-skill list/describe/run` | **Mostly shipped** | `cos-skill run` has CC stop-gap (/slash-cmd) + bare_cli/codex body render. Gap: no `cos-agent` yet. ~10h |
| **4 — Sub-agent spawning** | `cos-agent spawn` | **Pending** | Whole surface unimplemented. ~12h |

### Effort summary

- Surface 1 closure: 16h (4 adapters)
- Surface 2 closure: 6h (driver-bare + doctor)
- Surface 3 closure: 10h (cos-agent spawn cmd)
- Surface 4: 12h (whole)
- Verification suite (test_harness_parity.py, demo-portability-proof.sh): ~6h
- **Total Phase 2 closure**: ~50h

### Recommendation: split per surface vs monolithic

**Split per surface** (recommended):
- Surface 1 first (unblocks Codex observability — flat dashboard line is current pain)
- Surface 2 (driver-bare) after, depends on Surface 4 not being needed yet
- Surface 3 (cos-agent) before Surface 4 since 4 depends on it
- Surface 4 last

Each surface = own SDD change (proposal + design + apply + verify + archive). Monolithic would be 50h single change with high blast radius.

### Recommended sequence

1. `/sdd-new adr-064-codex-adapter` — Surface 1 closure, codex.py adapter (~4h, low blast)
2. `/sdd-new adr-064-bare-cli-adapter` — Surface 1, bare_cli.py adapter (~4h)
3. `/sdd-new adr-064-cursor-adapter` — Surface 1, cursor.py (~4h)
4. `/sdd-new adr-064-ci-adapter` — Surface 1, ci.py (~4h)
5. `/sdd-new adr-064-cos-doctor-harness` — Surface 2 (~6h)
6. `/sdd-new adr-064-cos-agent` — Surface 3+4 combined (~22h)
7. `/sdd-new adr-064-verification-suite` — final closure (~6h)

Each is a separate session. Total: 7 sessions, ~50h spread over 2-3 weeks.

---

## Cross-reference

This document is the consolidated input for next sessions. Each section maps to a separate work stream:

- **§1 DORMANT** → spawn `/sdd-new dormant-batch-B1` after verifying audit ON_DEMAND classification
- **§2 IMPLEMENT** → spawn `/sdd-new implement-batch-tier1` (4 PRs total per tier)
- **§3 ADR-064** → spawn `/sdd-new adr-064-codex-adapter` first

## Caveats

1. **Numbers are estimates**: effort per item is based on prune-triage report and ADR-064 plan. Real time may vary ±50%.
2. **Counter-pressure** from parallel sessions: ratio target <25% may slip if other work adds DORMANT/ASPIRATIONAL faster than reduction. Mitigation: run audit before/after each batch.
3. **Item 7-12 of IMPLEMENT batch**: not enumerated above; requires reading complete prune-triage report (the head -80 view didn't reach item 32+).
4. **ON_DEMAND classification**: §1 B1 strategy assumes audit reclassifies ON_DEMAND as not-dormant. **Untested**.

## Authored

Orchestrator (foreground) on 2026-05-02 ~14:00 ART. Dispatch gate blocked sub-agent for this analysis; document quality is bounded by what the orchestrator could read+analyze in the available budget. Background agents handling sdd-apply W0+W1+W2 and ADR-113 tests are still running and may produce parallel outputs.

Save engram: `mem_save` topic_key=`pending-attack-plan/2026-05-02` (handled by orchestrator after this write).

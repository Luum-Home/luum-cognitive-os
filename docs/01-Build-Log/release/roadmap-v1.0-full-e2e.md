# Roadmap v1.0 — 100% Functional + Full E2E Coverage

> **Goal**: Zero aspirational artifacts in the main tree. Every promise has an automated E2E test. Every core scenario has a manual QA playbook. `v1.0.0` tagged only after 100% E2E green.
>
> **Commitment**: 7-8 focused sessions, ~3-4 weeks calendar time.
>
> **Decision date**: 2026-04-16. User chose Option A (100% literal) over pragmatic alternatives.

---

## 🎯 NEXT SESSION PICKUP — READ THIS FIRST

**Current position**: **Session N closing** (target tag: `v0.9.2` — dogfood-ready + pilot-ready)

**To start next session**: just say "seguí con N+2" (or whichever step from the ledger below).

### What's DONE at session N close (2026-04-16)

Session N delivered the **foundations** for everything downstream:

- ADR-001 (harness path fix) + ADR-002 (simplify profiles to default + --full)
- 10 core adoption skills unblocked from ghost state (verified 10/10 reachable via `scripts/cos-core-skills-check.sh`)
- Install/update/uninstall scripts audited and fixed across 4 clusters
- UX sprint: install.sh rewrite, cos-status command, cos-update idempotent, hook hygiene (auto-verify, auto-refine, dod-gate, session-sanity hooks), rate-limiter UX improvements
- Capa-3 audit infrastructure: 1496 audit tests collected, 5 scorecards documenting aspirational gaps
- Capa-4 observability infra: `lib/telemetry.py` + usage reports + ghost-skill detector
- Sprint 4 canary: `scripts/cos-release-check.sh` + core-skills-check + 11 integration tests
- Sprint 2a orphan-fate decisions: 5 squads + 3 agents archived, aspirational rules trimmed
- 6 skill frontmatter bugs fixed (all have `name:` field now)
- Skill authoring docs established (`docs/05-Methodology/usage/skill-authoring.md`)
- Roadmap committed (this file)

**Empirical state at close**: aspirational ratio dropped from 49% → ~25-30% (exact number per audit re-run at session close).

### What's NOT done — pending sessions (in priority order)

| # | Session | Scope | Why deferred |
|---|---------|-------|--------------|
| N+2 | 113 skills E2E | Parameterized tests for non-core 113 skills + random-sample manual QA | Volume — ~20 min of test execution alone; cannot fit in same session as N+1 without compaction risk |
| N+3 | Hooks E2E | Trigger harness + per-wired-hook test + archive 41 orphans | Parallel-safe with N+2/4/5, but each sprint ~5-8 agents |
| N+4 | Rules E2E | Hook-enforced via N+3 harness; agent-instruction via scenario tests; declarative → `docs/04-Concepts/patterns/` | Builds on N+3 hook harness |
| N+5 | Install + Upgrade E2E × 5 scenarios | Fresh install parameterized (default/full/upgrade/broken/minimal) + real-machine manual QA | Needs real tmp-machine scenarios — cannot fully automate without actual box |
| N+6 | cos-dispatch integration E2E | 5 vendors × 2 events × 2 scenarios (20 golden) + load + chaos | Needs real vendor payloads as fixtures |
| N+7 | CI + release gate + v1.0 canary | `.github/workflows/e2e.yml` + coverage dashboard + 3 real client projects + **tag v1.0.0** | Requires N+1..N+6 green + 3 actual external projects |
| N+8 | Buffer + polish + release | Gaps from prior + README landing + blog post + first external user | Reserved for surprises |

### How to resume

Each session starts by reading this section. Then:
1. Update "Current position" to the session being executed
2. Pull latest — check what commits landed since last session
3. Run `bash scripts/cos-release-check.sh --dry-run` + `pytest -m audit` to capture current aspirational baseline
4. Execute the sprint per the ledger below
5. At session end, update "What's DONE" and move to next session

### Hard commitments from session N

- **Don't skip sessions**. Each session has an acceptance gate. Moving to N+X without N+X-1 done = technical debt accumulates.
- **Trust Report per session close**. Evidence-based, not vibes.
- **Aspirational % measured empirically** every session (via `pytest -m audit`).
- **No v1.0 tag until N+7 closes clean**. No shortcuts.

---

## Scope definition

**100% = each component is either:**
- ✅ **Functional + E2E tested** (automated test verifies documented behavior)
- 📦 **Archived** (under `_archived/` or `docs/04-Concepts/patterns/`, outside main flow, documented rationale)

Nothing lives in the "exists but doesn't do what it promises" state.

## Session ledger

| Session | Focus | Automated E2E deliverable | Manual QA deliverable | Aspirational target |
|---------|-------|---------------------------|------------------------|---------------------|
| N (current) | Sprint foundations | UX1/2/3/5/6 + F1-cleanup + Sprint 2a/4/5 + UX8 + audit-cleanup | — | 49% → ~25% |
| N+1 | Skills E2E core | `tests/e2e/skill_invocation_harness.py` + 10 core skills | `docs/qa/core-skills-manual-qa.md` + human run-through | 25% → ~20% |
| N+2 | Skills E2E rest | Parameterized tests for 113 remaining skills | Random sample 20 human-verified | 20% → ~15% |
| N+3 | Hooks E2E | `tests/e2e/hook_trigger_harness.py` + per-wired-hook tests; orphans archived | Rate-limiter/blast-radius/gotchas-injection screenshots | 15% → ~8% |
| N+4 | Rules E2E | Hook-enforced via N+3; agent-instruction via scenario tests; declarative → `docs/04-Concepts/patterns/` | Auto-injected context review | 8% → ~3% |
| N+5 | Install + Upgrade E2E | 5 scenarios parameterized (default/full/upgrade/broken/minimal) | Real-machine onboarding video | 3% → ~1% |
| N+6 | cos-dispatch integration E2E | 5 vendors × 2 events × 2 scenarios = 20 golden tests; load + chaos suite | Real Claude Code session trace | 1% → ~0.5% |
| N+7 | CI + release gate + canary | `.github/workflows/e2e.yml`; coverage dashboard; release gate blocks on E2E fail | 3 real client projects run full playbook → tag v1.0.0 | ~0% |
| N+8 (buffer) | Polish + release | Gaps discovered in N+1..N+7 | README landing + blog post + first external user onboarding | 0% |

## Acceptance gate per session

Each session closes ONLY if:
1. All stated E2E deliverables land with green tests
2. Manual QA playbook executed + checklist signed off by a human
3. Trust Score report filed with evidence
4. Aspirational target met or explained

If a session fails to meet gate: reassessment, potentially borrow from N+8 buffer. Do NOT advance to next session with open gaps.

## Risk register

| Risk | Mitigation |
|------|-----------|
| E2E harness for skills is harder than expected (invocation via agent requires real API) | Use subprocess-invoked test harness that simulates Skill tool invocation via mock harness; accept slightly-less-real coverage |
| 113 skills E2E costs more tokens than estimated | Batch parameterized tests by category; limit tests per skill to 1 happy + 1 error |
| 3 real client projects unavailable for N+7 | Use 3 throwaway client projects (`/tmp/client-1,2,3`) with realistic scaffolding |
| Scope creep finds a 4th install path missed | N+8 buffer absorbs; if exceeds, formally add N+9 |
| Adversarial review in N+4 scenario tests is too subjective | Define explicit pass/fail rubric per rule category; use adversarial-review skill itself to self-audit |

## Trust commitments

- Every session closes with TRUST_REPORT + evidence list
- Any claim "X is fixed" must have corresponding test that would fail if X regresses
- Manual QA sign-off is a real human running the playbook, not an LLM claim
- Aspirational % is measured empirically by `pytest -m audit` failure count / total

## Reference

- User decision: 2026-04-16 session, after capa-3 audit revealed 49% aspirational
- Baseline empirical evidence: `docs/04-Concepts/architecture/functional-audit/scorecard-*.md`
- Prior gap analysis: `docs/04-Concepts/architecture/FROZEN-BACKLOG.md`
- Release criteria: `docs/01-Build-Log/release/v1.0-release-criteria.md`

---

**Last updated**: 2026-04-16 (session where commitment was made)  
**Status**: Active roadmap, tracks weekly

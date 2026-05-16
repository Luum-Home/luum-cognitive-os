# Post-Mortem: Cognitive OS Growth Crisis (March–April 2026)

**Authors:** Luz Montiel (engineering) + Claude (architect)
**Date:** 2026-04-16
**Scope:** Project lifespan from v0.1.0 (2026-03-27) through stabilization sessions (2026-04-15/16)
**Severity:** Medium-High — silent degradation was accumulating at rate faster than detection
**Resolution:** Partial — 93-95% stabilization reached, pattern prevention mechanisms active

---

## TL;DR

The Cognitive OS grew from zero to 375+ agentic primitives in 18 days. During that growth, three patterns emerged:
1. **Aspirational logic** — schemas, metadata, and flags added but never consumed
2. **False coverage** — 67 test files (19% of suite) that only verified file existence, giving confidence that masked real regressions
3. **Invisible performance debt** — a single hook was adding 30-90 seconds per agent call for weeks before anyone noticed

None of these were caught by tests or reviews because the measurement systems that could detect them did not exist. The project grew faster than its capacity to measure its own health.

This session (April 15-16) built those measurement systems. The OS is now *self-aware* — it can detect its own degradation patterns. This document captures what went wrong, why, and the mechanisms now in place to prevent recurrence.

---

## TIMELINE

### Phase 1: Genesis (March 21-27, 2026)
- **March 21:** Project conception, engram begins recording decisions
- **March 23:** AGPL license audit — Redis/MinIO flagged incompatible with SaaS. Replaced with Valkey/SeaweedFS.
- **March 27 15:17:** Commit `1a7e421` — v0.1.0 released. **One commit adds 60+ hooks, 80+ skills, 30+ libs.**
  - `rate-limit-protection.sh` is born with an O(n) Python subprocess loop (undetected for 19 days)
  - `completion-gate.sh` is born with an unconditional EXIT trap (42s wasted per session for 19 days)
  - `dispatch-gate.sh` is born with 9 sequential Python cold starts

### Phase 2: Explosion (March 28-31, 2026)
- **March 28:** 38 commits in one day. v0.2.0 → v0.2.1. Agent Teams hooks created but never registered. SCOPE tags introduced as metadata with no consumers.
- **March 30:** v0.3.0 — skills.sh, auto-update, auto-update-projects safety guard against self-destruction (CRITICAL fix caught in testing, not prod — lucky)
- **March 31:** v0.3.3-v0.3.6 — namespace safety fix (CRITICAL: `rm -rf` on `.cognitive-os` symlinks could have destroyed sibling projects), SDD fast path, context diet, model catalog centralization

### Phase 3: Growing Pains (April 8-11, 2026)
- **April 8-9:** "Maturation sprint" v0.4.0-v0.7.0. 472 behavioral tests claim to be added. Later audit reveals many are structural.
- **April 9:** dispatch-gate.sh doubles from 86 lines to 270 in two hours. Circuit breaker + consequence engine + model advisor wired independently, each adding its own Python cold start.
- **April 10-11:** Rules-to-hooks refactor WS (93b56f2 through 5739bd4). 73 rules → 14 always-loaded. 74 rule symlinks deleted. Hook Architecture v2 lands.
- **April 11 16:22:** Commit `f49731d` — **Stabilization Freeze declared** (ADR-017). First time the project formally acknowledges "stop adding features." But `feat:` commits continue.

### Phase 4: First Crisis (April 13, 2026)
- **April 13:** "Contamination fix" commit `57ed5cf` removes 40 lib files and 34 hook files that were project-specific contamination. **Fix does not update references.** This creates:
  - 20 apparently-ghost hooks (actually symlinks — wrong audit call)
  - 13 apparently-missing libs (11 actually existed — wrong audit call again)
  - Broken chains between live hooks and deleted libs
- **April 13:** WS6 scope tagging applied to 82 hooks + 137 libs. **Tags read by zero code.** Pure busywork.

### Phase 5: Awareness (April 15, 2026)
- **April 15:** Deep audit session. Five parallel Opus agents reveal the truth:
  - Hook overhead estimated at ~97s/session (later measured accurately as ~36.5s — first audit inflated by symlink confusion)
  - 353 aspirational agentic primitives cataloged
  - 67 test files purely structural
  - 252 commits with zero ADRs
  - Only 3 of 13 "missing libs" actually missing
  - Only 3 of 69 "phantom skills" actually phantom
- **April 15:** Three worst hooks fixed:
  - `rate-limit-protection.sh`: 30-90s → 50-100ms (O(n) Python → single call)
  - `dispatch-gate.sh`: 2.1s → 300-400ms (9 cold starts → 1)
  - `completion-gate.sh`: 42s saved from non-Agent calls (trap moved)

### Phase 6: Reconstruction (April 15-16, 2026)
- 22 ADRs created (15 retroactive covering full history + 7 design ADRs)
- cos-dispatch Phase 1+2: 10 Go packages built, all tests passing
- Pattern detector implemented
- Auto-ADR detection hook
- Mandatory rules injected into sub-agents
- 2-tier skill loading (CATALOG-COMPACT)
- CI gate with mutation testing
- 67 structural tests deleted, 33 mixed files pruned
- Skills hygiene sweep (21 skills)
- Task Panel adapter (first ADR-021 implementation)
- User permissions added to prevent agent permission deaths
- **Stabilization: 80% → 93%+ in two sessions**

---

## ROOT CAUSE ANALYSIS

### Surface causes

1. **Velocity over verification**: 252 commits in 18 days, averaging 14/day, peaking at 38/day
2. **AI-generated code at scale**: v0.1.0 commit message is "Cognitive OS v0.1.0 — AI Agent Operating System" — the entire project was AI-generated in one commit
3. **Single-person project**: No peer review, no code review process, all decisions by one human + AI

### Deeper causes

4. **Measurement vacuum**: No benchmarks in CI, no mutation testing, no performance regression detection, no pattern detector. The tools to see degradation did not exist until this session.
5. **Documentation debt**: ADRs were not written as decisions were made — 252 commits, 0 ADRs. Context was lost faster than it could be captured.
6. **Metadata-as-implementation**: Fields added to files counted as "progress" even when no code consumed them. The illusion of progress.
7. **Test theater**: 342 test files felt reassuring. Nobody measured what they actually verified.

### Systemic cause

**The feedback loop was open-loop**: code added → "tests pass" → commit → next feature. At no point did the system say "this hook got slower" or "this field has no consumer." Without feedback, debt accumulates invisibly.

---

## CONTRIBUTING FACTORS

### Factor 1: Optimism Bias
Every feature felt complete when the happy path worked. Edge cases (large cost-events.jsonl, symlinks in audits, Agent vs non-Agent hook paths) were discovered in production, not in tests.

### Factor 2: Tool Choice Hiding Problems
`pytest --tb=no -q` output was dominated by passing tests. Failures scrolled off screen. The 34% mutation kill rate was not visible until we ran mutation testing explicitly.

### Factor 3: Fragmented Memory
Plans lived in engram (2,348 observations). Code lived in git. CLAUDE.md held rules. Skills had their own routing table. There was no single place that said "this is what's aspirational vs implemented."

### Factor 4: Premature Abstraction
Provider adapters, dispatcher design, transformer pipelines — all excellent architecture. But rushed into the codebase before the core features were stable, leaving many half-implemented systems.

### Factor 5: Agent Amnesia
Sub-agents don't inherit orchestrator context. Each audit re-discovered the same problem (symlinks) in a different wrong way. Parallel investigation was not parallel — it was repeated.

---

## WHAT WENT RIGHT

Credit where due — despite the wounds, several things were solid:

- **engram captured everything**: 2,348 observations meant we could reconstruct history in this session
- **Git history was clean**: 252 commits, every one pushed, no squashes — full forensic trail
- **License compliance was thorough**: AGPL audit in March, Redis/MinIO replaced proactively
- **Safety mesh concept was right**: even when implementations were incomplete, the *intent* of the architecture guided recovery
- **User was honest**: admitting "I feel overwhelmed" enabled the stabilization freeze. Without that admission, we would still be adding features.
- **Tests existed**: many were structural, but the ones that were behavioral (94% of unit tests) were genuinely valuable
- **The fundamental architecture was sound**: 5-layer Clean Architecture, dependency rule, provider abstraction — these all survived the stabilization and remain good decisions

---

## MEASURED IMPACT

### Before stabilization (April 14, 2026)
- 342 test files, test quality unknown
- Hook overhead: unmeasured, later found to be ~36.5s/session (peak 90s+ on agent calls)
- ADRs: 0
- Aspirational agentic primitives: 353+ undocumented
- Mutation score: unmeasured
- Agent amnesia: guaranteed — no injection mechanism

### After stabilization (April 16, 2026)
- 274 test files, 94% behavioral (structural ones deleted)
- Hook overhead: ~20s/session (44% reduction, verified)
- ADRs: 22 (full decision history)
- Aspirational agentic primitives: 0 of the discovered 353 remain (removed or implemented)
- Mutation score: 34% baseline on rate_limiter.py (measured, CI gate set at 40%)
- Agent amnesia: prevented via SubagentStart injection of mandatory rules

### Commits during stabilization (44 in one session)
- docs: 15
- fix: 10
- feat: 13
- perf: 3
- clean: 3
- test: 1 (creating 23 behavioral tests for the perf fixes)

Project shrunk by ~4,000 lines net while adding capabilities. The paradox: **less code, more function, measurable health.**

---

## PREVENTION MECHANISMS NOW IN PLACE

Mapped to each root cause:

### For "velocity over verification"
- `hooks/adr-detector.sh`: PostToolUse on git commit — auto-generates ADR drafts for architectural changes
- Pre-commit hook Gate 3f: blocks commits with structural-only tests
- CI gate `.github/workflows/test-quality.yml`: runs mutation testing on changed files, fails PR if kill rate < 40%

### For "measurement vacuum"
- `lib/pattern_detector.py`: detects dead metadata, broken chains, phantom entries, structural tests
- `hooks/pattern-check.sh`: runs at SessionStart (async), surfaces critical patterns
- `hooks/_lib/file_checker.sh`: symlink-aware existence checks — eliminates false "missing" reports
- cos-dispatch Phase 4 (in progress): SQLite tracking of every validator execution

### For "documentation debt"
- `templates/agent-mandatory-rules.md`: injected into every sub-agent via SubagentStart
- `.cognitive-os/plans/roadmaps/stabilization-roadmap.md`: living tracker of remaining work
- `docs/04-Concepts/architecture/FROZEN-BACKLOG.md`: consolidated deferred work (30+ plans)
- `docs/04-Concepts/architecture/LESSONS-LEARNED.md`: the 5 wounds + red flags (sibling to this post-mortem)
- 22 ADRs documenting all major decisions

### For "metadata-as-implementation"
- `detect_dead_metadata` in pattern_detector: greps for field readers after field is added
- Principle in LESSONS-LEARNED: "no metadata without consumer"
- CI gate rejects schema additions without reader code

### For "test theater"
- `scripts/check_test_quality.py`: AST-based classifier, flags structural tests
- `.cosmic-ray.toml`: mutation testing config
- Pre-commit + CI gates enforce minimum test quality

### For "agent amnesia"
- `hooks/subagent-context-injector.sh` → loads `templates/agent-mandatory-rules.md`
- Every sub-agent inherits: symlink handling, test quality rules, performance anti-patterns, engram persistence
- `/audit-integrity` skill provides standardized audit method

---

## LESSONS DISTILLED

1. **AI-scale code generation needs AI-scale measurement**: if you can generate 60 agentic primitives in one commit, you need automated checks that scale with generation, not with human review capacity.

2. **Schema additions are not progress**: adding a field to 100 files is not work — it's negative work unless code reads that field. The metric of progress is *behavior change*, not *file change*.

3. **Tests are a liability until they kill mutants**: a test that passes on both correct code and broken code provides negative value (false confidence). Test quality, not test count, is the metric.

4. **Sub-agents are stateless by design**: the orchestrator must inject all necessary context. Never assume a sub-agent knows what you just decided 10 turns ago.

5. **Silent degradation is the enemy**: the OS must be noisy about its health. Pattern detection, benchmarks, mutation scores, auto-ADR — all exist to make invisible problems visible.

6. **Velocity without feedback loops is debt accumulation**: each commit without a failing test that catches regression is debt. The only way to grow sustainably is with working feedback.

7. **Symlinks are a fact of life**: `readlink -f` before any classification. This one line of bash would have prevented hours of wrong-audit analysis.

8. **Document decisions in the moment or lose them forever**: 252 commits, 0 ADRs — reconstruction is expensive. Auto-ADR removes the excuse of "I'll document later."

9. **The freeze is a feature**: declaring "stop" is harder than "continue." But continuing on a cracked foundation is catastrophic. Stabilization freezes are productive, not punitive.

10. **Self-awareness is the moat**: a system that detects its own problems can be trusted. A system that looks healthy while rotting cannot. The five mechanisms above are what separates this project's future from its past.

---

## REMAINING RISKS

Honest acknowledgment of what could still go wrong:

- **cos-dispatch Phases 3-5 not yet built** — the mature dispatcher that would make pattern detection production-quality is partial
- **Mutation score is measured but not enforced on existing code** — CI gate only applies to new changes
- **Engram sync not activated** — single-machine local state, cross-device access manual
- **Documentation of agentic primitives is uneven** — many skills/hooks/libs still have stale docs (partial sweep in this session)
- **Subagent context injection depends on orchestrator remembering to use the hook** — if disabled, we lose the amnesia prevention
- **Human reviewer is still single-point-of-failure** — only one person reviews auto-ADR drafts

These are documented in `stabilization-roadmap.md` with effort estimates. Project is 93-95% stable, not 100%.

---

## COMMITMENTS FOR THE FUTURE

Based on what we learned:

1. **No feature PR without an associated ADR** (draft acceptable) when it changes architecture
2. **No schema addition without reader code** in the same PR
3. **No "test" that doesn't call `subprocess.run`, import code, or invoke a function**
4. **Pre-commit must run** — never commit with `--no-verify`
5. **Weekly health check**: read `LESSONS-LEARNED.md`, verify no red flags active
6. **Monthly backlog review**: check `FROZEN-BACKLOG.md`, unfreeze items carefully

---

## APPENDIX: The Conversation That Led Here

This post-mortem was written during the stabilization session on April 16, 2026, after the user asked:

> Operator request: write a post-mortem for the project's rapid growth, especially where development speed left aspirational logic ahead of behavioral reality, and preserve the details discussed in the session.

That request triggered this document. It exists because the user recognized that the discomfort of discovering 353 aspirational agentic primitives, 67 false tests, three wrong audits — is itself valuable knowledge. Losing that discomfort would mean losing the motivation for self-awareness.

The post-mortem joins `LESSONS-LEARNED.md`, `FROZEN-BACKLOG.md`, and `stabilization-roadmap.md` as the four living documents that preserve institutional memory across sessions. Each captures a different dimension:

- **Post-mortem**: *what happened and why*
- **Lessons learned**: *how to prevent recurrence*
- **Frozen backlog**: *what to do when stable*
- **Stabilization roadmap**: *what to do to reach stable*

---

**Signed:** 2026-04-16
**Review frequency:** After every major session (>10 commits) or quarter
**Ownership:** Luz Montiel, with this document serving as AI-collaborator testimony

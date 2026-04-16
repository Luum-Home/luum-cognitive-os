# Cognitive OS Stabilization Roadmap

**Created:** 2026-04-15
**Status:** Active — Phase 80% complete

This document tracks the remaining work to bring the Cognitive OS from "functional but fragile" to "stable for exponential growth."

## Current State (2026-04-15)

After the comprehensive audit and stabilization session:

- **20 ADRs** documenting all major decisions (retroactive + design)
- **cos-dispatch Phase 1+2** complete: 10 Go packages, all tests passing
- **3 critical hook perf fixes** applied (rate-limit-protection, dispatch-gate, completion-gate)
- **67 structural test files** deleted (false coverage eliminated)
- **Guardrails in place**: CI gate with mutation testing, mandatory agent rules, pattern detector, auto-ADR
- **8,023 / 8,031 tests passing** (99.9%)

## Remaining Work

### P0 — Block "stable" certification

| # | Item | Impact | Estimated effort |
|---|------|--------|------------------|
| 1 | ~~Fix 8 failing tests (singularity + session_lifecycle timeout)~~ | **DONE** — extracted _singularity_suggestion to lib | ✓ |
| 2 | Register adr-detector.sh and pattern-check.sh in settings.json | Hooks not firing | 30min |
| 3 | session-init.sh performance (6 Python cold starts → 1) | Slow session start | 2h |
| 4 | Behavioral tests for 3 hook fixes | No regression protection | 4h |

### P1 — Required for exponential growth confidence

| # | Item | Impact | Estimated effort |
|---|------|--------|------------------|
| 5 | cos-dispatch Phase 3: port 17 hooks to Go validators | Real dispatcher usage | 11 days |
| 6 | cos-dispatch Phase 4: SQLite pattern tracking | Auto-improvement enabled | 7 days |
| 7 | cos-dispatch Phase 5: auto-generator + feedback loop | Self-improving system | 8 days |
| 8 | Prune 47 mixed test files (remove structural, keep behavioral) | Cleaner coverage | 1 day |
| 9 | Raise mutation score baseline from 34% to 60%+ | Stronger test quality | 3-5 days |

### P2 — Quality of life

| # | Item | Impact | Estimated effort |
|---|------|--------|------------------|
| 10 | 2-tier skill loading (compact catalog + on-demand body) | ~5K tokens saved/session | 1 day |
| 11 | Activate engram cloud sync for cross-device access | Mobile backlog access | 1h + setup |
| 12 | Datasette dashboard for engram (read-only mobile view) | Mobile-friendly UI | 2h |
| 13 | claude-sync for ~/.claude/ across machines | Multi-device work | 1h |

### P3 — Technical debt

| # | Item | Impact | Estimated effort |
|---|------|--------|------------------|
| 14 | ADR-021: Dead metadata pattern + auto-detection | Prevents future aspirational code | 2h |
| 15 | Document all skills/hooks/libs (many have stale docs) | Developer onboarding | 3-5 days |
| 16 | Migrate remaining 16 orphaned project dirs (from matias) | Cleanup | 30min |
| 17 | Implement audience filtering at install time | Installer respects audience tag | 4h |

## Stability Scorecard

| Dimension | Score | Target |
|-----------|-------|--------|
| Test pass rate | 99.9% | 100% |
| Mutation score | 34% | 60%+ |
| Hook overhead/session | ~20s | <10s |
| Aspirational components | ~150 | <20 |
| ADR coverage of decisions | 20/30 major | 100% |
| Guardrails (CI + hooks + rules) | 5/7 | 7/7 |
| Cross-device capability | Manual | Automated |
| Multi-tool support | Designed | Implemented |

**Overall:** 80% stable — solid foundation, need Phase 3-5 for full confidence in exponential growth.

## Session Summary 2026-04-15

24 commits, 349 files changed, +11,173 / -14,926 lines. Project shrunk while adding capabilities.

See `docs/architecture/adrs/` for all decisions made.

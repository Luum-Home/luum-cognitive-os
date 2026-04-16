# Frozen Backlog — Pre-Stabilization Plans

Consolidated inventory of all plans, decisions, and queued work from engram that was frozen during the stabilization freeze (ADR-017) and the April 2026 stabilization sessions.

**Purpose:** Single source of truth for "what to work on when the OS is stable enough." These items were deferred because the user chose stabilization over new features — resume them when the stabilization roadmap is complete.

**Status reference (2026-04-16):** OS is ~93-95% stable. Do NOT start items from this backlog until stabilization hits 100%.

---

## MEGA PLANS (Multi-session)

### 1. Stabilization Mega Plan — engram #5889
**Decision:** engram #5319 (freeze declared)
**Scope:** 10 sessions, 6 phases, wiring from 43% → 90%
**Status:** Sessions 1-2 executed (April 13-16); 4 phases remaining
**Next:** Resume Phase 3+ after current stabilization hits 100%

### 2. Self-Optimizing Pipeline (WS13) — engram #3441
**Scope:** MAPE-K loop (7 monitors, 9 event types) for autonomous improvement
**Blocks:** cos-dispatch Phase 5 (auto-generator) must land first

### 3. Token Optimization Mega Plan — engram #3663
**Scope:** Multi-phase token reduction across rules, skills, CATALOG, preamble
**Partial progress:** 2-tier CATALOG-COMPACT (DONE this session), context-diet, SDD fast path
**Remaining:** prompt cache tuning, anchored summarization hardening, rule loader improvements

### 4. Intelligent Context Compaction (WS proposal) — engram #3085
**Scope:** 4 workstreams, 5-7 sessions, $12-18 budget
**Status:** Proposal only

---

## QUEUED FEATURE WORK

### 5. Session Queue — 14 Workstreams — engram #3660
Started April 10, most items still queued:
- WS1: CLAUDE.md diet (partial — done)
- WS2: Anchored summarization (partial)
- WS3: Prompt cache manager (partial)
- WS4: Parameterize skills with cognitive-os.yaml (partial)
- WS5: Trim docs to pointer stubs (REVERTED — kept)
- WS6: SCOPE tagging (DONE then REMOVED — tags were aspirational)
- WS7: Hook arch v2 (DONE) + WS7b: Repetition detector + WS7c: False-positive auto-tuning
- WS9: pytest error fixes (DONE — 292→0)
- WS11: Test baseline diff hook
- WS12: Smart-commit classifier (lib exists, not wired)
- WS13: State persistence heartbeat (DONE)
- WS14: Agent resilience tests (DONE) + WS14b: Compaction resilience
- WS15: Session hygiene automation (DONE)
- WS16: Agent context injection (DONE)

### 6. Token Optimization (TO-series) — engram backlog
- TO1: CLAUDE.md diet 92→18 rules (DONE)
- TO2: Smart file access helpers (partial)
- TO3: Model recommender with routing discipline (partial)
- TO4: Response compression rules (partial)
- TO5: Notification digest system (partial)
- TO6: Context usage estimator (partial)
- TO7: Preamble compression (DONE 58%)
- TO8: Memory-first protocol (partial)

### 7. Pending Plans Inventory — engram #3661
**Scope:** Meta-plan listing all pending plans as of April 2026
**Status:** This document supersedes it

### 8. Queued next tasks — engram #1825
- COS MCP server
- ShellSpec testing
- PR review automation
- TurboQuant research

### 9. GGA Engram integration — engram #1827
- Issues #51 #52
- Bidirectional integration (partial — search works, push pending)

### 10. 5 Remaining QUEUED tasks — engram #1836
Not detailed in session summaries; check engram when resuming.

---

## EVALUATIONS (Research — decide later)

### 11. Tool evaluations pending decision
| Tool | engram ID | Decision pending |
|------|-----------|------------------|
| autoskills (midudev) | 1959 | WATCH — NC license |
| opencli-rs-skill (nashsu) | 1958 | WATCH — Apache-2.0 |
| GGA (Gentleman Guardian Angel) | 1823 | Evaluate for integration |
| OpenClaw + Agent Zero | 1805 | Framework comparison |
| E2B sandbox | Evaluated — package created |
| Archon workflow engine | 1822 | Research |
| Garagon tools (aguara/mantis/tero) | 1774, 1772 | tero EVALUATE; mantis WATCH |

### 12. Package migration — engram #1684
**Scope:** 10 integrations → cos packages
**Status:** Partial — 4 packages migrated (POC), 6 pending

---

## ARCHITECTURE DECISIONS PENDING

### 13. Plugin Marketplace — engram #1675
**Scope:** Roadmap documented, not implemented
**Blocks:** Need cos-dispatch Phase 3+ for proper plugin model

### 14. Onboarding Wizard (TUI) — engram #1819
**Design:** Complete (`docs/onboarding-wizard-design.md`)
**Implementation:** Partial — `cos setup` command exists
**Remaining:** Full TUI polish

### 15. Security Stack Master — engram #1781
**Status:** docs/security-stack.md exists
**Integration:** Partial — 5 layers wired, 3 pending

### 16. Agnix Integration — engram #1664
**Scope:** Agnix linter → Cognitive OS integration
**Status:** Package exists, full integration pending

### 17. Plans directory consolidation — engram #1788
**Decision pending:** `plans/` root dir vs `.cognitive-os/plans/`
**Recommendation:** Consolidate into `.cognitive-os/plans/` only

### 18. Rules consolidation — engram #1820
**Scope:** 73 rules → 14 always-loaded (DONE)
**Remaining:** Context7 auto-trigger tuning, scope-aware loading

---

## DECISIONS MADE BUT NOT FULLY IMPLEMENTED

### 19. Rules-to-hooks refactor — engram #2946, #2968, #2973
**Decision:** Move enforcement from CLAUDE.md rules to shell hooks
**Status:** Mostly done. 22 EXCLUDED_RULES, 17 hook-enforced
**Pending:** 5 rules without hook equivalent — decide: keep as rule OR implement hook

### 20. Agent Orchestration (Real) — engram #2753
**Scope:** From aspirational to real agent teams
**Partial:** TeammateIdle/TaskCreated/TaskCompleted hooks registered (DONE this session)
**Pending:** Real dispatch through agent-bus with Valkey backend

### 21. Docker → pip migration — engram #4819
**Status:** Phase 1+2 DONE (6 + 3 services migrated)
**Pending:** 3 services still in docker-compose (Paperclip, PostgreSQL, Valkey)

### 22. Project-audit / Pre-dev completeness — engram #2927
**Scope:** Audit tracking gaps
**Status:** Package exists; hook (predev-completeness-check.sh) registered
**Pending:** More thorough gap coverage

---

## COMPONENTS WAITING FOR ACTIVATION

### 23. Security tools implementation gap — engram #3155
Hooks exist for: Semgrep, MCP-Scan, Promptfoo, Garak, Aguara, Parry
Status: Partially wired. Some exist as hooks but aren't in default profile.

### 24. Skills needing audience-awareness logic — engram #1771
**Scope:** Skills that need runtime logic (not just metadata) for audience
**Status:** audience field filtering DONE this session (ADR-021)
**Pending:** Skills that need deeper per-audience logic

### 25. Rate-limit status tool — engram #1763
**Scope:** Verify rate-limit status tool after WorkloadScheduler
**Blocker:** WorkloadScheduler completion

### 26. Non-blocking retry pattern — engram #1764
**Scope:** CronCreate + WorkloadScheduler non-blocking retry integration
**Status:** Partial

---

## REFERENCE / BACKLOG CLEANUP

### 27. Smart-commit skill — engram #3508
**Scope:** Atomic commit splitting
**Priority:** Low (nice-to-have)

### 28. Broken window policy for test errors — engram #3404
**Scope:** Enforce even test errors (not just failures)
**Priority:** Medium

### 29. Docs-to-Skills Audit — engram #3153
**Scope:** 115 docs classified
**Status:** Mostly processed; some stubs reverted this session

### 30. Skill Atomicity Audit — engram #3151
**Scope:** 103 skills classified across 3 dimensions
**Status:** Applied this session (release-os, cognitive-os-init, self-improve split)

---

## HOW TO USE THIS BACKLOG

1. **DO NOT** start items while stabilization is in progress (see `stabilization-roadmap.md`)
2. **DO** check engram for full context before resuming an item (`mem_search` with the engram ID or topic_key)
3. **DO** update this file when items complete — move to "Archive" section (to be added)
4. **DO** file new deferred work here (not scattered in engram)

## Next review

Check this backlog AFTER stabilization reaches 100%. Priority order for resumption:
1. Mega Plan Stabilization (#1) — continue Phases 3-6
2. Pending architecture decisions (#11-18)
3. Queued features (#4-10)
4. Evaluations (#11-12)
5. Nice-to-haves (#27-30)

## Sources

All items in this backlog reference engram entries (SQLite at `~/.engram/engram.db`). To read full content:
```python
import sqlite3
db = sqlite3.connect('~/.engram/engram.db')
row = db.execute("SELECT content FROM observations WHERE id=?", (5889,)).fetchone()
```

Topic keys for searching:
- `planning/*` — planning documents
- `sdd/*` — SDD artifacts
- `architecture/*` — arch decisions
- `implementation/*` — implementation records

---

**Last updated:** 2026-04-16
**Created during:** Session 2026-04-16 (gap closure + stabilization to 93%)
**Engram IDs referenced:** 30+ entries

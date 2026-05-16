# Next Session Handoff — 2026-04-20

> Session closed after 30+ commits, v0.14.1 shipped, 9 ADRs (032-042), aspirational ratio 78% → 67%.

## Priority Order (ranked by unblocking impact × effort)

### P0 — Operational cleanup (do first, ~30 min total)

| # | Task | Effort | Why priority |
|---|------|--------|--------------|
| 1 | Regenerate `settings.json` via `bash scripts/apply-efficiency-profile.sh standard` | 2 min | Picks up work-queue-sync + renamed hooks from duplication-resolver. May need to re-verify hook registration completeness. |
| 2 | Fix `tests/unit/test_aider_streaming_adapter.py` collection error | 15 min | Blocks full-suite CI. Pre-existing since ADR-034 merge. |
| 3 | Fix `test_every_skill_in_catalog` failure | 15 min | 1 failing test. Check if duplication-resolver already regenerated CATALOG-COMPACT.md. |
| 4 | Remove empty `.claude/worktrees/gracious-burnell-5a757d/` dir | 30 sec | Residue from session. |

### P1 — Unblock CI + critical path (~3 sessions)

| # | Task | Effort | Why |
|---|------|--------|-----|
| 5 | **ws9-test-errors classification** | 1-2h | pytest-timeout now installed; run full suite, categorize 292 errors, fix or mark xfail with reasons |
| 6 | **ADR-039 Embeddings retry** (sentence-transformers install + tests + benchmark) | 1 session | WIP stub committed; unlocks ADR-040 |
| 8 | **ADR-044 PostgreSQL local daemon** | 1 session | Mirror of ADR-042 |

### P2 — Coverage + architecture maturity (~4-5 sessions)

| # | Task | Effort | Why |
|---|------|--------|-----|
| 9 | **ADR-041 Wave B** (~50 Tier B chaos tests) | 2 sessions | Use `scripts/cos_chaos_template.py` from MVP; drops aspirational ratio substantially |
| 10 | **ADR-040 Query-tailored context** | 1.5 sessions | Depends on ADR-037 + ADR-039 done |
| 11 | **ADR-038 Wave 2** (typed input_schema + 4-layer context budget) | 1 session | Industry alignment continues |
| 12 | **ADR-038 Wave 3** (Pydantic TrustReport + typed handoff tool) | 1 session | Breaking change; v0.16.0 |

### P3 — Feature completion (~4-5 sessions)

| # | Task | Effort | Why |
|---|------|--------|-----|
| 13 | **ws5-doc-conversions** (115 docs → skills) | 1 session | D28 still OPEN |
| 14 | **ws4-skill-splits** (21 skills) | 2-3 sessions | D27 OPEN |
| 15 | **os-visual-ui full dashboard** | 1-2 sessions | cos-watch TUI is MVP only |
| 16 | **ADR-036 sprint full** (TUI multi-agent + aggregator + consolidated-commit) | 1 session | MVP shipped; UX gap |

### P4 — Polish (~2 sessions)

| # | Task | Effort | Why |
|---|------|--------|-----|
| 17 | SessionStart nudge cache optimization (500ms → <50ms) | 30 min | SLO honesty; follow pattern of cwd-inject-cache |
| 18 | ADR-038 Wave 4 (separate planning template) | 2h | Optional smolagents pattern |
| 19 | ADR-033b Wave 2 (Aider Python API migration) | 1 session | Hardening |
| 20 | ADR-037 glossary quality (remove JSON-snippet noise in top results) | 1h | Cosmetic |

## Pending Tasks Files
Full specs at `.cognitive-os/pending-tasks/`:
- adr-033b-duration-and-aider-hardening.md
- adr-034-live-streaming.md (partially done)
- adr-036-sprint-orchestration.md
- adr-037-self-knowledge-base.md (done)
- adr-038-preamble-v2-industry-aligned.md (Wave 1 done)
- adr-039-reinvention-phase-b-beta.md (WIP)
- adr-040-query-tailored-context-injection.md
- adr-041-exercised-coverage-pipeline.md (MVP done)
- rate-limit-queue-jsonl-migration.md (done)

## Key State
- Branch: `main` only. Remote origin/main synced.
- Tag: `v0.14.1`
- Aspirational ratio: 67.3% (target <40%)
- Tests: 9814 collected, 1 known collection error + 1 catalog failure
- Executor daemon: FIXED (v0.14.0 shipped broken, fixed in flight agent today)

## Critical Commands for Next Session Startup
```bash
# 1. Check session starts clean
cd <repo-root>
bash scripts/apply-efficiency-profile.sh standard   # regenerate settings
git status                                           # should be clean

# 2. Run smoke
bash scripts/cos-smoke.sh

# 3. Baseline audit
python3 scripts/aspirational_audit.py --dry-run

# 4. Rebuild self-knowledge index
python3 scripts/cos_build_self_knowledge.py
```

## Total Effort Estimate
~12-15 sessions to reach "SO production-ready + full self-hosting".

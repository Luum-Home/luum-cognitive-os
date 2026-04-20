# DEBT REGISTER — 2026-04-20

Comprehensive sweep of deferred, parked, xfail, and follow-up items across the codebase. Post-ADR-028 close (commit 92cf485). Bar for "real debt": a named file/commit/engram ref AND a reasonable prospect of non-trivial cost if ignored.

Sweep sources:
- `.cognitive-os/work-queue.json` (parked + removed + user_concerns)
- `.cognitive-os/tasks/active-tasks.json` (3 in_progress from this session)
- `.cognitive-os/sessions/*/tasks.json` (167 dirs — all empty arrays or completed; no orphan residue)
- `tests/**/*.py` xfail / skip markers (14 real hits)
- ADR open-questions sections (ADR-028 §Open questions, ADR-029 Phase B, ADR-027a §Action items, ADR-028a §Action items, ADR-002 §Remaining gaps)
- `rules/ROADMAP.md` (8 hook-enforced-BROKEN + 2 code-dead hooks)
- `docs/architecture/FROZEN-BACKLOG.md` (30 consolidated deferrals)
- `docs/architecture/stabilization-roadmap.md` (P2/P3 residue)
- `lib/_wiring-allowlist.txt` (9 "not yet wired" libs)
- Git log `--grep=defer|follow-up|frozen|parked` since 2026-03-01

---

## Section 1 — Debt inventory

Severity scale: BLOCKING = blocks a named release / gate / active pilar; HIGH = will bite within 2 sprints; MEDIUM = real debt, non-urgent; LOW = tracked but accepted; NOISE = flagged but not actually debt (see §4).

Age in days from 2026-04-20. Effort in session-units (1 session ≈ 3-4h Opus).

| id | source | kind | age | severity | summary | first step | effort |
|----|--------|------|-----|----------|---------|------------|--------|
| D01 | ADR-028 OQ#1 / R3 | deferred_adr | 4 | ~~**BLOCKING**~~ **CLOSED** | ~~Bug 2 root cause unknown~~ **RESOLVED 2026-04-20**: live static scan found 0 active destructive git commands in hooks/. Root cause was agent behavior (stash pop + checkout via-ref), not a hook. ADR-003 three-layer defense active, 10/10 chaos tests pass. See `docs/reports/d01-git-reset-forensics-2026-04-20.md`. | — | 0 |
| D02 | rules/ROADMAP.md §1.5 | parked_task | 4 | **BLOCKING** | `agent-identity.md` audit trail never fires — `audit-id-enricher.sh` exists but not in `.claude/settings.json`. Every agent launch has no audit ID. | Register under `PreToolUse Agent` matcher | 0.25 |
| D03 | rules/ROADMAP.md §1.2 | parked_task | 4 | **BLOCKING** | `auto-rollback-trigger.sh` not registered — rule claims automatic rollback, reality is manual only. SDD apply-verify loop can't rollback. | Register under `PostToolUse Agent` with failure signal | 0.25 |
| D04 | rules/ROADMAP.md §1.3 | parked_task | 4 | HIGH | `confidence-gate.sh` not registered (only `trust-score-validator.sh` is). Pre-launch confidence gate is a lie. | Register under `PreToolUse Agent` | 0.25 |
| D05 | rules/ROADMAP.md §1.4 | parked_task | 4 | HIGH | `confidentiality-enforcer.sh` not registered — PII/secret egress relies on separate `secret-detector.sh` which covers a subset. | Register under `PostToolUse Edit\|Write` | 0.25 |
| D06 | rules/ROADMAP.md §1.6 | parked_task | 4 | HIGH | `predev-completeness-check.sh` not registered — Medium+ tasks skip readiness gate silently. | Register under `PreToolUse Agent` name-match `sdd-apply*` | 0.25 |
| D07 | rules/ROADMAP.md §1.7 | parked_task | 4 | HIGH | `reinvention-check.sh` is Phase A advisory; ADR-029 explicitly defers Phase B hard-block that needs a similarity mechanism. | Build semantic similarity (Jaccard / embeddings) or decide never | 2 |
| D08 | work-queue `ws6-scope-tags` | parked_task | >14 | HIGH | ~260 component files have no `scope: os-only\|project\|both` tag. Audit classified ASPIRATIONAL. Blocks ws8 auto-classifier. | Write tagger script; tag 260 files | 1.5 |
| D09 | work-queue `adr-027-phase-2-3` | parked_task | >14 | HIGH | D2 `ref_key_loader.py` MISSING entirely — ADR-027a §2 contextual on-demand rule inclusion cannot land. D3 hook dedupe also blocked. | Write `ref_key_loader.py` MVP | 1 |
| D10 | ADR-028 OQ#4 | deferred_adr | 4 | HIGH | `MetricEvent` schema versioning strategy unwritten. A breaking change in Phase D forces a migration plan not yet drafted. Current field: `schema_version` int. | Draft migration policy doc before next MetricEvent field addition | 0.5 |
| D11 | ADR-028 OQ#5 | deferred_adr | 4 | HIGH | Killswitch fallback under full disk unspecified. If flag file can't be written, `scripts/so-emergency-stop.sh` fails silently. | Implement `SO_KILLSWITCH=1` env var fallback in `hooks/_lib/killswitch.sh` | 0.25 |
| D12 | tests/behavior/test_agent_resilience.py:79 | xfail | ~21 | MEDIUM | Preamble has no concrete numeric tool-call ceiling — caused the 476-tool-call incident. xfail is a real product gap. | Add `max 50 tool calls` line to `templates/agent-preamble.md` | 0.25 |
| D13 | tests/behavior/test_agent_resilience.py:167 | xfail | ~21 | MEDIUM | `pre-compaction-flush.sh` not registered as PreCompact (hook type may not be supported by current Claude Code) — compaction save is best-effort. | Research if Anthropic added PreCompact event; register or revise rule | 0.5 |
| D14 | tests/behavior/test_agent_resilience.py:365 | xfail | ~21 | MEDIUM | Preamble has no warning against unrestricted sub-agent spawning — cascading context exhaustion risk. | Add dispatch-gate check instruction to preamble | 0.25 |
| D15 | tests/integration/test_compaction_resilience.py:648 | xfail | ~21 | MEDIUM | `crash-recovery.sh` not wired into SessionStart; snapshot injection not implemented. Hook only creates `meta.json`. | Implement state-snapshot load in `session-init.sh`; register crash-recovery | 0.5 |
| D16 | tests/chaos/test_disk_full_metrics.py:78 | xfail | ~7 | HIGH | `append_event()` propagates ENOSPC instead of degrading gracefully. Production hot path — disk-full crashes session. | Wrap write in try/except OSError; emit warning | 0.25 |
| D17 | tests/chaos/test_fd_exhaustion.py:94 | xfail | ~7 | MEDIUM | `so-vitals.sh` exits 1 on ImportError under FD pressure — brittle observability under stress. | Catch ImportError; degrade to minimal dump | 0.25 |
| D18 | tests/unit/test_safe_jsonl.py:223-225 | xfail | ~14 | MEDIUM | Heartbeat intermittently produces malformed JSON / does not fire in subshell context. Race or env-inheritance bug. | Repro with `bash -c`; check SAFE_JSONL_LOADED guard | 0.5 |
| D19 | ADR-002 §Remaining gaps | deferred_adr | 0 | MEDIUM | `tests/contracts/EXCLUDED_HOOKS.txt` marks global-verify as "FUTURE" target Stop matcher — stale after registration as PreToolUse/PostToolUse Agent. | Edit file to reflect reality | 0.1 |
| D20 | ADR-027a §Action items | deferred_adr | ~10 | MEDIUM | 5 checkboxes unticked: KPI update D3, remove D2 compact-claude-md bullet, token target 1200, ws9 dep, work-queue annotation | Single editing pass on ADR-027 + work-queue | 0.25 |
| D21 | ADR-028a §Action items | deferred_adr | ~10 | MEDIUM | 10 checkboxes unticked (all D-phase amendments: session-init comment, open Q#9, D1.C scope note, auto-checkpoint docstring, work-queue 2 entries, F-4…F-7 pre-exit) | Methodical editing pass | 0.5 |
| D22 | ADR-028 OQ#8 | deferred_adr | 4 | MEDIUM | Orchestrator itself has no heartbeat — sub-agents do. Silent orchestrator hangs undetectable by so-vitals. | Decide: add in Phase D or accept | 0.25 |
| D23 | ADR-028 OQ#6 | deferred_adr | 4 | LOW | `test_fd_exhaustion` on macOS may collide with OS-wide limits. Needs per-host sandbox. (Related to D17.) | Add `pytest.skipif` on macOS <=1024 FDs | 0.1 |
| D24 | rules/ROADMAP.md §2.5 | code_dead | ~14 | MEDIUM | `response-length-check.sh` referenced in `self-install.sh` EXCLUDED_RULES comment but file does NOT exist. Misleading — rule is agent-instruction-only. | Either build hook or edit EXCLUDED_RULES comment | 0.25 |
| D25 | rules/ROADMAP.md §2.6 | code_dead | ~14 | MEDIUM | `context-budget.sh` does not exist — `rules/context-optimization.md` acknowledges it. Thresholds (50/70/85%) are self-reported. | Build hook or rewrite rule to remove hook reference | 0.5 |
| D26 | lib/_wiring-allowlist.txt | uncommitted_note | ~30 | LOW | 9 libs marked "not yet wired": Jupyter integration, SDD resume, webhook-trigger, orchestrator-mode detection, phase-timing, smart truncator, external clients, concurrency primitive, advanced tool creation. Each is a file with no caller. | Decide per-lib: wire or delete | 2 |
| D27 | work-queue `ws4-p3-p4-splits` | parked_task | >14 | LOW | 21 remaining skill splits (P3 composability + P4 template dedup). Aspirational per audit #11624. | Decide if still valuable; close or execute | 1 |
| D28 | work-queue `ws5-doc-conversions` | parked_task | >14 | LOW | 0 of 11 doc→skill conversions done. | Decide if still valuable; close or execute | 1 |
| D29 | work-queue `multi-device-portability` | parked_task | >14 | LOW | Pure research. No infrastructure. Partially superseded by engram-sync git export. | Close; mark superseded by Apr-16 engram-sync | 0.1 |
| D30 | work-queue `os-visual-ui` | parked_task | >14 | LOW | MLflow pip not installed; mlflow-sync.sh silent no-op on every Stop. | `pip install mlflow` or remove hook registration | 0.25 |
| D31 | work-queue `plugin-caveman-review` | parked_task | >14 | LOW | 92 new commits in caveman plugin never triaged. Review-by 2026-05-01 (11 days). | Run `/eval-repo` on caveman | 0.5 |
| D32 | FROZEN-BACKLOG #14 | uncommitted_note | >30 | LOW | Onboarding wizard TUI — `cos setup` partial, full polish deferred | Scope-out full polish OR accept `cos setup` as final | 0.5 |
| D33 | FROZEN-BACKLOG #17 | uncommitted_note | >30 | LOW | Plans directory consolidation decision pending (`plans/` vs `.cognitive-os/plans/`) | Pick one; move and delete other | 0.25 |
| D34 | FROZEN-BACKLOG #21 | uncommitted_note | >30 | MEDIUM | Docker→pip phase 3 pending: Paperclip, PostgreSQL, Valkey still in docker-compose | Design migration per service | 2 |
| D35 | FROZEN-BACKLOG #23 | uncommitted_note | >30 | MEDIUM | Security tools partially wired: Semgrep/MCP-Scan/Promptfoo/Garak/Aguara/Parry hooks exist, not in default profile | Add to `default` profile in `apply-efficiency-profile.sh` | 0.5 |
| D36 | FROZEN-BACKLOG #19 | uncommitted_note | >30 | LOW | 5 rules still without hook equivalent — decide: keep as rule OR implement hook. | Audit 5 rules; per-rule decision | 0.5 |
| D37 | tests/audit/test_install_scripts.py:392-409 | skip | ~10 | NOISE→LOW | 3 install tests skipped (network, Docker, HOME mutation). Documented gaps, not real debt. | Set up CI sandbox with Docker + redirected HOME | 1 |
| D38 | lib/code_reviewer.py:159-162 | todo | >30 | NOISE | Regex patterns for matching TODO/FIXME/HACK/XXX — these are scanner rules, not TODOs themselves. | N/A | - |
| D39 | work-queue `release-v0.9.0` | priority_queue | 0 | HIGH | Release v0.9.0 still `pending` after ws9 closure. 58 commits since v0.8.7 unreleased. | Run `lib/release_analyzer.py`; tag | 0.5 |
| D40 | work-queue `test-quality-audit` | priority_queue | 0 | MEDIUM | 530+ tests not yet audited for structural-vs-behavioral meaningfulness. Mutation gate unrun. | Run mutation gate across `tests/` | 1 |
| D41 | .cognitive-os/tasks/active-tasks.json | session_orphan | 0 | NOISE | 3 in_progress tasks from THIS session (Opus:plans, Opus:debt-register, Sonnet:artifact-verify) — will close on completion. | N/A | - |
| D42 | hooks/ grep TODO/FIXME | todo | 0 | NOISE | Zero TODO/FIXME/HACK/XXX matches inside `hooks/`. (Pre-commit gate blocks them.) | N/A | - |
| D43 | FROZEN-BACKLOG §P1 Core vs Extensions | uncommitted_note | >14 | MEDIUM | Advisory-LLM hooks + recap-sync should move to `packages/` before v1.0 (otherwise core ships bloated). | Create `packages/advisory-llm/` + `packages/claude-code-integration/`; move 4 files | 0.5 |
| D44 | tests/chaos/test_reset_cascade_detector.py:90,125 | skip | ~4 | ~~MEDIUM~~ **CLOSED** | ~~2 skips on reset-cascade detector chaos~~ **RESOLVED 2026-04-20**: `skipif` guards are conditional on blocker file existence — file exists, all 10 tests pass (0 skips). No action needed. | — | 0 |

44 rows. Non-noise: 40.

---

## Section 2 — Severity summary

| Severity | Count | Effort sum (sessions) |
|----------|-------|-----------------------|
| BLOCKING | 3 | 1.0 |
| HIGH | 12 | 7.0 |
| MEDIUM | 17 | 8.6 |
| LOW | 8 | 5.85 |
| NOISE | 4 | 0 |

**Total non-noise effort: ~22.5 session-units** (~15–22 working hours if run clean by Opus; >30h if Sonnet).

---

## Section 3 — Clusters

Grouping unlocks "one session closes N items". Ordered by ROI.

### C1. Hook registration sweep (closes D02, D03, D04, D05, D06 — 5 items, ~1.25 sessions)
Five hooks exist on disk, not registered. One edit to `.claude/settings.json` (or the `self-install.sh` template) registers all five. Gated on someone reading `hooks/self-install.sh` EXCLUDED_RULES and deciding whether these hooks are actually safe to fire. High-ROI, high-risk — one bad registration blocks every agent.

### C2. ADR-028 open-questions closure (closes D01, D10, D11, D22, D23 — 5 items, ~1.5 sessions)
All five are downstream-phase blockers for ADR-028's successor pilar work. D01 (git reset forensics) is BLOCKING; the rest are pre-reqs to extend MetricEvent / enable killswitch robustness. Cluster lead: Opus, forensic mindset.

### C3. xfail triage on agent resilience (closes D12, D14, D15, D16, D17, D18 — 6 items, ~1.75 sessions)
All six are product gaps documented as tests. Three cluster in the preamble (D12, D14) + state persistence (D15); three in observability under stress (D16, D17, D18). Splitting between a templates-sweep agent and a chaos-resilience agent closes the cluster.

### C4. ADR addenda editing pass (closes D19, D20, D21 — 3 items, ~0.85 sessions)
All pure text editing in ADRs + work-queue. No engineering. Sonnet agent, one pass.

### C5. Frozen-backlog cleanup vote (closes D27, D28, D29, D30, D31, D32, D33 — 7 LOW items, ~3.6 sessions if executed)
Most should be closed (superseded) or explicitly abandoned rather than executed. The 30-item FROZEN-BACKLOG has accumulated ASPIRATIONAL items that audit #11624 already flagged. A single "close vs execute" vote session compresses 7 items into ≤3 decisions.

### C6. Wiring allowlist decision (closes D26 — 1 item split 9 ways, ~2 sessions)
9 libs marked "not yet wired." Each needs a wire-or-delete decision. Good shadow-governor task — nothing ships, but dead-code risk drops.

### C7. Release unblock (closes D39, D40 — 2 items, 1.5 sessions)
v0.9.0 release is `pending` with 58 unreleased commits AND test-quality audit unrun. Release alone = 0.5; test-quality audit = 1. Running test-quality audit BEFORE release is the prudent order — otherwise release on unaudited tests.

---

## Section 4 — Noise / false positives

Items that look like debt but are not.

- **D38** `lib/code_reviewer.py:159-162` — regex patterns matching `TODO`/`FIXME`/`HACK`/`XXX` in the scanner itself. These are PATTERNS the scanner uses; flagging them is self-reference. NOT debt.
- **D41** `.cognitive-os/tasks/active-tasks.json` 3 in_progress entries — are THIS session's live tasks. Will close on session end. NOT debt, will auto-resolve.
- **D42** `hooks/` grep for TODO — **zero matches**. The pre-commit gate (`hooks/pre-commit-gate.sh`) blocks TODO in hooks. This is evidence of a working gate, not debt. The 167 session dirs scanned likewise hold no residual orphaned tasks (0 pending across the 5 session files with tasks.json content — the other 162 are empty arrays).
- **D37** `tests/audit/test_install_scripts.py` 3 skips (network, Docker, HOME mutation) — documented environment requirements, not product gaps. Reclassified NOISE→LOW because CI sandbox setup IS work if we want them green.
- Sessions 162/167: all empty arrays. The "session orphan" category yields zero real debt. The only pending work sits in `.cognitive-os/tasks/active-tasks.json` (single-file authoritative queue).

### Contradictions vs. work-queue

Work-queue claims these are "completed_this_sprint" but the codebase disagrees on two:

- **WS6 SCOPE tagging** listed `DONE then REMOVED` in FROZEN-BACKLOG #5, but `ws6-scope-tags` is still `parked` in work-queue.json with "0 of ~260 files tagged". Both true — the tags were tried, rolled back, and the parked item survived the roll-back. Not a false claim, but the narrative is confusing. **Recommend: mark `ws6-scope-tags` as `removed_2026_04_20` with `reason_removed: superseded_by_ws6_rollback`.**
- **`adr-027-phase-1`** listed as completed via commit `e4a3c86` but ADR-027a §Action items has 5 pre-reqs **still unticked** (D20). The Phase 1 code shipped before all its ADR-defined preconditions were met. Technically complete, procedurally irregular. **Recommend: retro-amend ADR-027a action items to `done` if verified, or reopen.**

---

## Section 5 — Top 5 decisions

Ranked by cost-of-inaction × ease-of-decide.

### 1. ACT NOW — Cluster C1 (hook registration) + D02 specifically (audit-id-enricher)
**Why**: Every agent launched right now has no audit trail ID. This invalidates `rules/agent-identity.md`, weakens post-mortem forensics (D01 forensic retrospection depends on audit IDs), and misleads anyone reading the rule. Cost: 15-minute settings.json edit.
**Risk**: bad registration could fire PreToolUse on every agent — test in isolation first.

### 2. ACT NOW — D01 (git reset forensics)
**Why**: BLOCKING on D3 re-runs, BLOCKING on anyone trusting the working tree, and cheap to investigate (grep + reflog). The longer this sits, the more sessions potentially lose work.
**Output**: `grep -rn "git reset\|git clean -f\b" hooks/ scripts/ packages/*/hooks/` + reflog review of 10 sessions.

### 3. CLOSE (don't defer) — Cluster C5 (7 LOW frozen-backlog items)
**Why**: These are ASPIRATIONAL per audit #11624 and accumulating review-by dates that keep slipping. Closing is 0.25 sessions total. Executing is 3.6 sessions of low-ROI work. A decisive "closed as won't-fix — superseded" label is cleaner than eternal `review_by: 2026-06-01`.

### 4. DEFER-WITH-DATE — Cluster C3 xfail triage, capped at 1 sprint
**Why**: Six xfails are real product gaps but none are BLOCKING today. Set a hard cap: "all six resolved or converted to accepted LOW by 2026-05-15." xfail debt grows silently — the rule is one sprint max.

### 5. ESCALATE — D07 (ADR-029 Phase B) + D34 (Docker→pip phase 3)
**Why**: Both require architectural decisions beyond fix-it work. D07 (Phase B reinvention-check hard-block) needs a similarity-mechanism design call (embeddings vs Jaccard vs abandon). D34 (3 remaining services off docker-compose) is a blocker for the "pip-first ALWAYS" user concern in work-queue.json. Both are ≥2 sessions with design uncertainty. User should pick the next pilar explicitly.

---

## Adversarial review (meta)

- **BLOCKING/HIGH found**: 15 (target ≥5). D01 + D02 + D03 are the strongest — all three mean the claimed enforcement layer (rules + hooks) is honest-only-on-paper.
- **False positives found**: 5 (target ≥3). D38, D41, D42, sessions-162-empty, contradictions-in-WS6/ADR-027-phase-1.
- **Contradictions against work-queue**: WS6 + ADR-027 Phase 1 named above.
- **Empty-ish risk**: 44 rows (40 non-noise). Sweep was exhaustive given time budget.

The single-biggest structural risk this register uncovers: **the "hook-enforced" claim in `rules/RULES-COMPACT.md` is partially false.** Eight rules that claim hook enforcement actually rely on hook files that exist but are never registered (D02–D06 + rules/ROADMAP.md §1.1 `audit-trail` split into three sub-hooks). The README-to-reality gap is the systemic pattern behind many of the individual rows here.

---

*Generated 2026-04-20. Next review: 2026-05-04 (2-week cadence) or on completion of any Top-5 decision.*

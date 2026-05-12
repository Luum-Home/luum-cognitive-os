# Cross-check Part C: Orchestration (2026-05-08)

Repo: `luum-agent-os` @ `main` (working tree, not public mirror).

## 🔍3 Squad coordination

**Veredicto:** **MEJOR_NUESTRO (post-archival realism)** vs. *competing externals*; **REGRESIÓN intencional, formalizada** vs. *internal historical claim*.

**Estado actual:**
- `packages/_archived/squads/` exists with explicit README dating archival to **Sprint 2A, 2026-04-16**, citing the Capa-3 functional audit (`docs/04-Concepts/architecture/functional-audit/scorecard-packages-squads-agents.md` F5–F8).
- Audit findings are unambiguous: 5/5 squad YAMLs were "0% runtime integration" — no Python/Go loader, broken `skills: [testing-patterns]` refs (skill does not exist), broken `agentRef:` refs (`backend-architect`, `security-engineer`, `sre-agent`, `devops-agent`, `engineering-manager-agent` have no `agents/*.md`).
- One survivor: `squads/organization.yaml` kept at root *as a user-init template only*, still with no runtime loader.
- `rules/squad-protocol.md` and `skills/squad-manager/` remain as governance/skill surface but are decoupled from the dead YAML wiring.
- Live multi-agent surface lives in `lib/agent_team.py` (ADR-233 file-IPC, schema `agent-team-file-ipc/v1`, advisory locks, inbox/task primitives), `lib/agent_bus.py`, `lib/agent_message_bus.py`, `lib/agent_lifecycle.py`, `lib/handoff_envelope.py` (ADR-230), `lib/session_coordination.py`, `packages/agent-coordination/` and `packages/agent-lifecycle/` (these are the *integrated* packages — symlinked into `lib/` per the audit's F1).

**ADR-251 status:** `Accepted — Slice A implemented` (frontmatter `status: accepted`, body §Status). Slice A artefacts present: `manifests/agent-orchestration-adapters.yaml`, `scripts/agent-orchestration-boundary-audit.py`, `scripts/agent-orchestration-benchmark.py`, `tests/unit/test_agent_orchestration_boundary_audit.py`, `tests/unit/test_agent_orchestration_benchmark.py` (all listed in `implementation_files:`). The "research/ADR-251 lo marca pending" framing in the prompt is **stale** — ADR-251 has moved past pending. What remains pending is the *adoption of external orchestration adapters* (LangGraph / AutoGen / CrewAI / OpenAI Agents SDK) behind that boundary, not Slice A itself.

**External anchor:** `docs/03-PoCs/research/repo-scout/monitor-followup/awslabs__agent-squad-2026-05-06.md` deep-evaluated `awslabs/agent-squad` (Apache-2.0, ~7.6k★) at `MONITOR_CONFIRMED` — explicitly noted overlap with `skill_router.best_match` and "would compete with existing skill_router". This is the correct verdict: the *concept* is mature externally, but adopting awslabs/agent-squad would re-introduce the same kind of routing bespoke we just archived.

**¿Reactivar, formalizar tombstone, o re-diseñar?:**
- **Tombstone is NOT owed.** The archival README *is* the tombstone — it is dated, cites the audit, lists the un-archive preconditions (loader, agentRef resolution, skills resolution, governance gate wiring), and points at the design doc (`docs/04-Concepts/root/plug-and-play.md`).
- **Already re-designed.** ADR-251 is the redesign: instead of growing a bespoke "squad runtime", COS becomes the *governance plane* and external orchestrators (LangGraph et al.) plug in as adapters. The adapter manifest + boundary audit + benchmark trio is the load-bearing primitive, not a YAML squad loader.
- **Reactivation gate:** un-archive only after a YAML loader resolves agentRef + skills against real artefacts. That is the same gate the README sets and is consistent with `[component-reality-check]` (`scripts/aspirational_audit.py`).
- **Recommendation:** add an explicit ADR-tombstone entry pointing `_archived/squads/` → ADR-251 as `Superseded-by`, so future readers don't have to triangulate README + audit + ADR. The slot exists in the tombstone series (ADR-003/004/005/043/046/085/214/229 are tombstones) but no squad-tombstone ADR currently bridges the two artefacts.

**Net judgement:** *intentional dormancy*, *formalized via README + audit + ADR-251*, *not regression*. Better than externals because the failure mode (bespoke YAML loader with broken refs) was empirically caught and the redesign is architectural (governance ⊥ orchestration) rather than another bespoke loader.

---

## 🔍6 Hermes / Cline shadow-git (ADR-227)

**Veredicto:** **IGUAL (parity on substrate)** + **MEJOR_NUESTRO on atomicity guarantees** vs. Cline; claim "Slices A–F implementadas" is **CONFIRMED**, not aspirational.

**Nuestra implementación (concrete files):**
- `lib/shadow_git.py` (canonical substrate). Implements `snapshot()` via `git init --bare` + `GIT_INDEX_FILE=<temp>` + `git hash-object -w` + `git update-index --add --cacheinfo` + `git write-tree`. The user's `.git/index` is provably untouched (the index is a sibling of the bare repo at `repo.parent / "shadow.index"`).
- `manifests/shadow-git.yaml` (declarative manifest matching ADR-227 §"Manifest declaration").
- `hooks/auto-checkpoint.sh`, `hooks/pre-agent-snapshot.sh`, `hooks/post-agent-snapshot-restore.sh`, `hooks/pre-cleanup-snapshot.sh` (lifecycle wiring).
- `docs/05-Methodology/runbooks/shadow-git-rollback.md` (operator-facing runbook).
- `lib/snapshot_manager.py`, `lib/checkpoint_manager.py` (related; checkpoint orchestration).
- `scripts/cos-rollback` (CLI surface specified in ADR-227).
- ADR-227 frontmatter: "Slices A–F implemented (2026-05-07)", complementary ADR-224 ("shadow-state snapshots — off-repo") and ADR-099 / ADR-200 / ADR-220 are wired in.

**Cómo se compara con Cline:**

Cline's shadow-git is documented at <https://github.com/cline/cline> (`src/integrations/checkpoints/`, see `CheckpointTracker.ts`, `CheckpointGitOperations.ts`). Convergent invariants — both implementations satisfy:

1. **Disjoint `GIT_DIR` / out-of-tree bare repo.** Cline: separate repo. COS: `~/.cognitive-os/snapshots/{project_id}/{session_id}/.git`, hard-rule "Bare repo never enters user's project tree" (ADR-227 §"Hard rules"). ✅ parity.
2. **Index isolation.** Cline: separate index. COS: `GIT_INDEX_FILE=<temp>`, asserted by CI test on `.git/index` byte-equality. ✅ parity.
3. **Untracked-file capture.** Cline: yes. COS: `_list_files()` walks workspace, excludes `.git/`/`.cognitive-os/`/`node_modules`/`__pycache__/`. ✅ parity, with documented size bounds (`size_warning_mb: 50`, `size_block_mb: 500`).
4. **`.gitignore` honoured.** Cline: yes. COS: hardcoded exclusions (the manifest enumerates them). Slightly weaker than Cline's full gitignore parser; acceptable for the listed exclusions.
5. **Restore as `git checkout-index --prefix=`.** Cline: yes. COS: yes (`files_only` mode in ADR-227 §"Restore operation").

**Where COS goes further than Cline (MEJOR_NUESTRO):**
- **Atomic file+conversation restore (ADR-227 §"Atomic restore semantics").** COS ties file restore to ADR-226 event-bus `truncate_session(target_seq)` under a session-scoped `flock`. ADR-227 explicitly calls out that *Claude Code SDK `rewindFiles()` does NOT do this* and Cline solves it for files only. COS solves it for files + conversation atomically — with `RESTORE_FAILED` rollback semantics, diff-tree preview written *before* mutation, and `--yes`/interactive confirmation gating.
- **Governance-as-restore-point.** ADR-227 §Context: every policy-check / blast-radius / audit-finding event carries `file_tree_sha`. Cline does not have this — it is the explicit defensible differentiator the gap research called out.
- **Schema versioning** (`shadow-git/v1`) and **CLI refusals** (refuses-without-preview, refuses-under-dirty-workspace). Stronger guarantees than Cline's UX.

**¿Hay claim aspirational?:** **NO.** I verified the file exists, contains real `subprocess.run(["git", "init", "--bare", ...])` and `git write-tree` calls, real `GIT_INDEX_FILE` isolation, and real session-scoped `flock`. The "Slices A–F implementadas" frontmatter is backed by code. The pattern *was* imported from Cline/Hermes/Kilo.ai/`git-shadow` (ADR-227 §"Source"), per `[reinvention-prevention]` — pattern adoption, not code adoption.

**Caveat to flag:** ADR-227 test matrix lists T1/T2/T3/T4/T5/T7/T10 as ✅ but T6 (performance, p95<200ms) and T9 (adoption-truth) as ⬜. The 200ms p95 budget is a non-trivial claim under heavy workspaces; recommend running the benchmark before any public messaging that cites "Devin-parity at zero infra cost".

---

## 🔍10 agentapi (coder/agentapi, MIT)

**Veredicto:** **NO_COMPARABLE en el strict sense** + **MEJOR_NUESTRO** for the slice both touch, *but* **MEJOR_EXTERNO en testdata corpus** — agentapi should be vendored.

**Nuestra implementación:** `lib/harness_adapter/` is real (ABC + canonical event schema per ADR-033):
- `lib/harness_adapter/base.py`: `HarnessAdapter` ABC + `CanonicalEvent` dataclass registry (`SessionStart`, `AgentStart`, `AgentEnd`, `ToolUse`, `TokenUsage`, `HeartbeatTick`). Subclass registry pattern with `__init_subclass__`, JSONL roundtrip, version-tolerant `from_dict`.
- `lib/harness_adapter/claude_code.py`, `codex.py`, `aider.py`, `aider_streaming.py`, `bare_cli.py`, `dispatch.py`, `tool_use_correlation.py`. Six adapters present.
- `HarnessName` enum lists 8 harness slots: `claude_code`, `codex`, `bare_cli`, `opencode`, `aider`, `cursor`, `continue`, `unknown`. Three of the eight (`opencode`, `cursor`, `continue`) are slots without adapter files yet — this matches ADR-033's "passive POC for Aider, additive expansion later".
- ADR-033b adds duration correlation + Aider hardening; ADR-034 adds live streaming. Active line of work.

**Comparison with agentapi (deep-evaluated at `docs/03-PoCs/research/repo-scout/deep/coder__agentapi-2026-05-06.md`, 8.7/10, ADOPT):**

| Dimension | agentapi (Go, MIT) | `lib/harness_adapter/` (Python) |
|---|---|---|
| **Problem solved** | HTTP API normalization across CLI agents (in-band: `POST /message`, `GET /messages`, `GET /events` SSE). Front-end for *driving* agents. | Telemetry normalization across harnesses (canonical events: AgentStart/End, ToolUse, TokenUsage, HeartbeatTick). Back-end for *observing* agents. |
| **Mechanism** | `termexec` spawns subprocess + `screentracker` diffs terminal screen + `msgfmt` parses output. Screen-scrape-based. | Hook stdin → `dispatch.handle_event` → adapter → JSONL emit. Hook-driven. |
| **Harnesses covered** | 11 (aider, amazonq, amp, auggie, claude, codex, copilot, cursor, gemini, goose, opencode) — testdata fixtures for each | 6 wired (claude_code, codex, bare_cli, aider×2, dispatch) + 3 declared slots |
| **Output stability** | Pre-1.0 (v0.12.x) | ADR-033 schema is internal-stable; ADR-033b/034 are additive |
| **Coupling** | External Go binary as sidecar | In-process Python, zero deps |

These overlap *only* on "harness fingerprinting" — the question of "is this output Aider's `<<thinking>>` block or Claude Code's tool call?". For that slice:
- **MEJOR_EXTERNO:** agentapi's `lib/msgfmt/testdata/{format,initialization}/{aider,amazonq,amp,auggie,claude,codex,copilot,cursor,gemini,goose,opencode}/` is the most comprehensive harness-format corpus in the public radar (11 harnesses, golden fixtures for `first_message`, `multi-line-input`, `second_message`, `thinking`, `confirmation_box`, `auto-accept-edits`, `remove-task-tool-call`). COS has nothing equivalent.
- **MEJOR_NUESTRO** for the canonical-event surface (ADR-033's typed dataclasses + `_registry` are cleaner than parsing free-form HTTP messages; AgentBusMetrics / cost dashboards can consume our schema directly).

**¿Mismos casos?:** **No.** agentapi normalises *interactive I/O*; `lib/harness_adapter/` normalises *observability events*. agentapi is closer in spirit to ADR-161 (remote control plane / provider adapter boundary) and ADR-196 (cosd task API) than to ADR-033.

**Recommended action (already noted in the deep-eval):** vendor `lib/msgfmt/testdata/` under MIT into `lib/harness_adapter/testdata/` and use it as the golden corpus for adapter unit tests. Phase-2 task, ~1 day for testdata vendor + 3–5 days to port `msgfmt` parsers to Python. Do **not** adopt agentapi as a sidecar — that would re-introduce a Go runtime dependency and cross the boundary set by ADR-049 (LLM dispatch) without justification.

---

## Resumen ejecutivo

| # | Item | Veredicto | Nota |
|---|---|---|---|
| 3 | Squad coordination | MEJOR_NUESTRO (vs externals) / Intentional dormancy formalized | ADR-251 redesign live; squad-tombstone ADR would close documentation loop |
| 6 | Hermes/Cline shadow-git (ADR-227) | IGUAL on substrate, MEJOR_NUESTRO on atomicity + governance receipts | Claim "Slices A–F" is real; T6/T9 still ⬜ |
| 10 | agentapi vs harness_adapter | NO_COMPARABLE (different problem) / MEJOR_EXTERNO on testdata corpus | Vendor `lib/msgfmt/testdata/` into `lib/harness_adapter/testdata/` |

**Single biggest signal:** ADR-251 + the archived squads + `lib/shadow_git.py` together demonstrate the *governance vs. mechanism* boundary that is the project's strongest architectural posture. None of the three items are aspirational — each is backed by code or by a deliberate, dated archival decision. The two follow-ups worth scheduling:

1. **Squad-tombstone ADR** — slot a new tombstone (e.g. ADR-253-tombstone) that names `packages/_archived/squads/` and points to ADR-251 as `Superseded-by`. Cleans up the cross-reference path.
2. **agentapi testdata vendor** — small, MIT-clean, immediately strengthens harness adapter test coverage. Tracked under ADR-033b/034 line of work.

**Acceptance criteria status:** each item cites ≥1 file/ADR (`ADR-251`, `packages/_archived/squads/README.md`, `docs/04-Concepts/architecture/functional-audit/scorecard-packages-squads-agents.md`; `ADR-227`, `lib/shadow_git.py`, `manifests/shadow-git.yaml`, `hooks/auto-checkpoint.sh`; `ADR-033`, `lib/harness_adapter/base.py`) and ≥1 external reference (awslabs/agent-squad, cline/cline, coder/agentapi). No claim flagged as ASPIRATIONAL after grounded code inspection.

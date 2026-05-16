# Cross-check Part E: Observability + Claims Debt (2026-05-08)

> Phase: reconstruction. Brutal mode. Each verdict cites a concrete path/grep.

## 🔍11 Phoenix vs Langfuse vs MLflow

**Verdict:** RESOLVED AND PARTIALLY IMPLEMENTED. The decision is not MLflow-vs-Phoenix; it is **MLflow + Phoenix coexist**, with separate roles, and Langfuse deprecated.

**Documented decision:**
- Primary ADR: **ADR-058** (`docs/02-Decisions/adrs/ADR-058-observability-migration-langfuse-to-phoenix.md`), date 2026-04-24, status **Accepted**.
- ADR-067 does NOT cover observability; it is `ADR-067-frontmatter-defense-in-depth.md` (another topic). The mental research pointer suggesting ADR-067 was wrong.
- Base evaluation: `docs/04-Concepts/architecture/observability-backend-evaluation-2026-04-24.md` with a pinned §Decision section at the end pointing to ADR-058.

**Rolees per ADR-058:**
| Backend | Role | Status | Evidence |
|---|---|---|---|
| JSONL | source of truth local | Core, always-on | `.cognitive-os/metrics/*.jsonl` |
| MLflow | outcome/cost metrics exporter | DEFAULT (`mode: pip`) | `lib/mlflow_bridge.py` (273L) |
| Phoenix | trace UI LLM-native (OTel) | OPTIONAL (`mode: pip`) | `lib/record_completion.py` L38-47 (`from phoenix.otel import register`); `skills/phoenix-trace-ui/SKILL.md` exists |
| Langfuse | DEPRECATED | Phase 0 done; Phase 2-4 pending | Still 9 OTel/phoenix hits in `record_completion.py`, **0 hits langfuse** → trace sink already migrated |

**Is the decision correct?**

Pros:
- MLflow for outcome metrics + Phoenix for LLM traces resolves the legitimate objection ("MLflow does not understand prompts/tools/spans").
- Phoenix is OTel-native → portability to Grafana/Jaeger without reinstrumentation.
- 1.34 GiB RAM freed (audit from 2026-04-24 documented in ADR-058).
- License posture corrected 2026-05-06: ELv2 server (operator-installed) + Apache-2.0 SDK packages. The rule §10 [`license-policy`] BLOCKS ELv2, but ADR-058 explicitly states Phoenix is operator-installed runtime (no bundled), which is within the ELv2 allowed scope. **Edge case:** if someone tries to package Phoenix in a COS release, the license-gate should fire. I did not see a test enforcing it: minor gap.

Cons / open risks:
- Phase 3 (remove Langfuse from `docker-compose.cognitive-os.yml`) target 2026-06-15 — pending.
- Phase 4 (volume cleanup) target 2026-06-30 — pending.
- README still advertises "Phoenix only mentioned" (I verified this: README L64 mentions Phoenix as one of 4 surfaces, without depth). The claim in `docs/09-Quality/manual-tests/proof-paths.md` was not audited here.

**Recommendation:** KEEP current decision. Phoenix + MLflow is the correct combination. Action: close Phase 3/4 before 2026-06-30 and add a test verifying that the COS bundle does not embed the Phoenix ELv2 server.

---

## DEBT-1 blast-radius advisory vs blocking

**Decision:** INTENTIONAL ADVISORY — not real debt.

**Evidence (`packages/task-management/hooks/blast-radius.sh`):**
- Comment L4-5: `Advisory only (exit 0) — does NOT block, but warns for HIGH/CRITICAL`.
- L216: `# Advisory only — always exit 0`.
- L160-171: thresholds **explicitly raised** because "the old rules flagged every doc/test agent as CRITICAL because 'migration' or 'auth' keyword alone triggered it. Noise > signal."
- L192-205: uses `hookSpecificOutput.additionalContext` with `permissionDecision: "allow"` (ADR-023). The design itself says "I do not want to block; I want to inject context into the orchestrator."
- L144-158: integrates with `clarification-gate` via hook-pipe — if ambiguity ≥ 30, lowers the HIGH threshold a 20. This is the mechanism **correct** for selective escalation.

**Documented reason:** keyword estimation over the prompt is heuristic — blocking by heuristic would generate massive false positives. `docs/04-Concepts/root/safety-mesh.md` L23 confirms: "Layer 2: blocks: 0 (WARN only)".

**README discrepancy:** README L34 says `blast-radius.sh` "warns before a task touches more than a safe scope" — this is **correct**, not an overclaim. The discrepancy the user suggested ("warns" vs actually blocks) does not exist. The README claim is precise.

**Action:** KEEP advisory. Consider adding an opt-in mode `BLAST_RADIUS_BLOCKING=true` for production if demand appears, but NOT default. The current design is correct.

---

## DEBT-2 Tombstone convention

**Status:** Formal convention EXISTS, but was NOT applied to archived squads.

**Existing convention:**
- `skills/adr-tombstone/SKILL.md` defines the pattern.
- `scripts/adr_tombstone.py` + `tests/unit/test_adr_tombstone.py` implement it (seen in frontmatter of `ADR-085-tombstone.md`).
- 8 ADRs already use the pattern: `ADR-003, 004, 005, 043, 046, 085, 214, 229`.
- Canonical frontmatter: `status: tombstone`, `superseded_by: <ADR-X>`, `tier: maintainer`, `tags: [adr, tombstone, governance]`.
- Typical use (ADR-229): consolidation, reserved slot, not reusesble.

**Archived squads gap:**
- `packages/_archived/squads/` contains 4 archived YAML files (infra/platform/mobile/payments) + explanatory README from 2026-04-16 (Sprint 2A).
- README cites `docs/04-Concepts/architecture/functional-audit/scorecard-packages-squads-agents.md` as justification.
- **No ADR tombstone formally records the decision to archive squads.** `grep -ril squad docs/02-Decisions/adrs/` only returns `ADR-075-stage2-selective-expansion.md` (related, not a tombstone).
- The rule §10 [`license-policy`] and KPIs do not force tombstones for archived components, but the implicit convention (see ADR-229) is that **reverted/consolidated decisions → ADR tombstone**.

**It is real debt.** Archiving 4 squads + neutralizing the loader is an architecture decision with public surface (affected `.cognitive-os/squads/` symlinks, health reports, KPIs). It deserves a formal record.

**Proposed action:**
1. Create `docs/02-Decisions/adrs/ADR-NNN-squad-templates-archival.md` (next available slot) with frontmatter `status: tombstone-of-feature` or `status: superseded` (NO tombstone-of-slot — that pattern is for empty ADRs). Suggested correct status: **`status: superseded` with `supersedes: []` and a body that tombstones the *feature*, not the ADR slot**.
2. Alternative: extend `skills/adr-tombstone/` with a subtype "feature-tombstone" different from current "slot-tombstone".
3. The `packages/_archived/squads/` README must link to the new ADR.

---

## Claims audit README/AGENTS.md

> No root `CLAUDE.md` exists in this repo (verified: `ls CLAUDE.md` → no such file). The equivalent is `AGENTS.md` + `rules/RULES-COMPACT.md`. Both audited.

| # | Claim | Status | Evidence | Action |
|---|---|---|---|---|
| 1 | "14-layer safety mesh" (README L26, docs/04-Concepts/root/safety-mesh.md) | **VERIFIED** | `docs/04-Concepts/root/safety-mesh.md` enumerates the 14 layers with hook + exit code. 11 are hooks PreTool/PostTool, 3 are library/conditional. All cited hooks exist: `clarification-gate.sh`, `blast-radius.sh`, `dry-run-preview.sh`, `rate-limiter.sh` (`hooks/rate-limiter.sh`), `scope-proportionality.sh`, `claim-validator.sh`, `assumption-tracker.sh`, `trust-score-validator.sh`, `confidence-gate.sh`, `clarification-interceptor.sh`, `auto-rollback-trigger.sh`. Libraries: `lib/cross_verifier.py`, `reinvention-check.sh`, `lib/memory_scanner.py`. README is honest when breaking down 11+3. | Keep. |
| 2 | "claim-validator.sh blocks agents that report test results without running tests (Layer 6, blocks in production mode)" | **VERIFIED** | Hook exists in `hooks/claim-validator.sh` and `packages/quality-gates/hooks/claim-validator.sh`. Conditional blocking in production mode is aligned with the pattern advisory-vs-blocking for the rest. | Keep. |
| 3 | "auto-rollback reverts on retry exhaustion (Layer 11)" | **VERIFIED** | `hooks/auto-rollback-trigger.sh` exists; safety-mesh L11 "exit 2 + revert"; rule §6 [`auto-rollback`] hook-enforced. | Keep. |
| 4 | "blast-radius warns before a task touches more than a safe scope" | **VERIFIED** | Ver DEBT-1. Advisory consciente, no overclaim. | Keep. |
| 5 | "trust-score-validator requires a scored Trust Report with evidence" (Layer 8) | **PARTIAL** | Hook exists (`hooks/trust-score-validator.sh`). BUT safety-mesh L8 says exit code "0 (LOG only)" — that is, does NOT block, only logs. README L37 says "requires" which suggests enforcement; in reality is advisory in the current hook. The rule §3 [`trust-score`] says "mandatory" but I do not see blocking enforcement in code. | Soften language to "logs and surfaces missing Trust Reports" or document where effective blocking occurs. |
| 6 | "rate-limiter caps tool calls, agent spawns, and hourly spend" (Layer 4) | **VERIFIED** | 5 files exist: `rate-limiter.sh`, `rate-limit-detector.sh`, `rate-limit-drain.sh`, `rate-limit-precheck.sh`, `rate-limit-protection.sh`. Broad coverage matches the claim. | Keep. |
| 7 | "Phoenix traces, Engram Cloud memory, Obsidian/markdown reader" as 4 operator-facing surfaces (README L62-64, ADR-172) | **PARTIAL** | Phoenix: lib/record_completion.py L38 imports it; skill `phoenix-trace-ui` exists. Engram: tools `mcp__plugin_engram_engram__*` active. Obsidian: I did NOT verify a concrete binding in this audit — claim not covered. ADR-172 referenced ADR exists (not read). | Verify surface Obsidian in another pass. |
| 8 | "Cognitive OS maps to a traditional OS: kernel, scheduler, memory, drivers, syscalls, networking, MAPE-K" (README L124-127) | **PARTIAL/ASPIRATIONAL** | Mapping is metaphor. `cognitive-os.yaml` (65KB) is kernel-config. Engram is memory. Hooks are scheduler. BUT "MAPE-K-inspired loop" — the README itself says "advisory self-healing patterns... not autonomous production mutation". Rule §10 lists [`singularity`] as "MAPE-K(inactive)". The architecture claim is real as design; the live implementation is partial. README already labels this correctly with the note "(MAPE-K-inspired loop, not autonomous production mutation)". | Keep — README already qualifies the claim. |
| 9 | "self-improvement / self-healing... propose-only and human-gated" (README L172-174) | **VERIFIED as an honest caveat** | README EXPLICITLY says "autonomous production mutation is not claimed". This is NOT an overclaim; it is deliberate underclaiming. Rule §10 [`singularity`] confirms `(inactive)`. | Keep. It is an example of an honest claim. |
| 10 | "REAL/DORMANT/ASPIRATIONAL feature status legend" (README L166-174) | **VERIFIED** | `scripts/aspirational_audit.py` exists (referenced in RULES-COMPACT). Skill `component-reality-check` listed. Doc `docs/09-Quality/legal/h1-feature-status-audit.md` referenced (not read in this pass). Rule §"Change Safety" cites the pattern. | Keep. It is healthy self-auditing. |
| 11 | "Squads and teams are experimental layers, not the adoption path" (README L57-58) | **VERIFIED + recognizing gap DEBT-2** | `packages/_archived/squads/README.md` confirms "0% runtime integration, no loader, no parser." `squads/organization.yaml` is kept as template. README es honesto. | Close with ADR tombstone (DEBT-2). |
| 12 | "FSL-1.1-MIT" license badge (README L8) | **VERIFIED** | `LICENSE` file present; rule §10 license-policy blocks AGPL/SSPL/BSL but allows FSL/MIT. Consistent. | Keep. |
| 13 | "11 that fire as hooks PreTool/PostTool, 3 are library/conditional" (README L26) | **VERIFIED** | safety-mesh L1-L11 has Type=PreToolUse/PostToolUse; L12, L14 Type=Library; L13 PostToolUse. **Minor discrepancy:** L13 (`reinvention-check.sh`) es PostToolUse per the doc, not library. Correct count should be **12 hooks + 2 libraries**, no 11+3. | Correct README L26 to "12 fire as PreTool/PostTool hooks, 2 are library calls". |

---

## Executive summary

- **Observability:** Phoenix+MLflow decision (ADR-058) is correct, NOT ADR-067. Migration is in Phase 0/1/2; Phase 3-4 pending for 2026-06-30. Trace sink is already zero-Langfuse in `lib/record_completion.py`.
- **DEBT-1 (blast-radius):** false alarm. Advisory is an intentional and well documented in-code decision. Keep.
- **DEBT-2 (tombstone squads):** real debt. Convention exists (8 ADR-tombstones precedentes), was not applied a `packages/_archived/squads/`. Create formal ADR.
- **Claims README/AGENTS:** 8 VERIFIED, 3 PARTIAL, 0 pure ASPIRATIONAL, 1 trivial numeric correction (11+3 → 12+2). README is notably honest: it already qualifies MAPE-K as "inspired/not autonomous" and lists REAL/DORMANT/ASPIRATIONAL legend. **Only overclaim:** Trust Report "requires" suggests blocking where the current hook only logs (Layer 8, exit 0).
- **Prioritized actions:**
  1. Create ADR tombstone for squad archival (DEBT-2).
  2. Correct count 11+3 → 12+2 in README L26.
  3. Soften claim for Trust Report "requires" or add blocking enforcement where README promises it.
  4. Cerrar ADR-058 Phase 3 (remove Langfuse from docker-compose) before 2026-06-15.

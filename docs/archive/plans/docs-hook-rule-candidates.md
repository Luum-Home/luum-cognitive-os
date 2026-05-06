<!--
RECONCILIATION STATUS: STALE
Reconciled: 2026-04-21
Reason: one-shot classification snapshot from 2026-04-11. The hooks/rules referenced (content-policy, secret-detector, license-policy) have long since been evaluated; no downstream ADR adopted this tabulation as a work plan.
Recommendation: archive as historical audit artifact.
-->

# Docs → Hooks/Rules Classification — April 2026

> Methodology: First 30 lines of each doc scanned for prohibition/enforcement signals.
> Principle: "como=skill, por que=doc, no hagas X=hook"
> - Prohibitions ("never", "must not", "blocked", "forbidden") → HOOK-CANDIDATE (automatic enforcement)
> - Behavioral guidance ("when X, do Y", "always do X", "agents must/should") → RULE-CANDIDATE (contextual agent guidance)
> - Neither → SKIP (handled by parallel skill-candidate pass, or pure reference)

---

## HOOK-CANDIDATE (enforcement should be automatic)

Docs whose primary content is "never do X" — the kind of policy that should be enforced by a hook at zero token cost, not read into context every session.

| Doc | Core Prohibition | Suggested Hook Event | Hook Exists? | Action |
|---|---|---|---|---|
| `docs/secret-detection.md` | Block content with secrets/injection patterns before Engram save; PostToolUse on Write | PostToolUse on Edit\|Write | `hooks/secret-detector.sh` ✅ | Trim to pointer stub — fully covered |
| `docs/blocked-tools.md` | Block AGPL/SSPL/BSL libraries from being adopted | PreToolUse on Agent (license check) | `hooks/clarification-gate.sh` partial; `rules/license-policy.md` covers it | Trim to pointer stub — behavioral aspect is a rule, no new hook needed |
| `docs/safety-mesh.md` | "Never allow low-confidence results in production", "BLOCK" language throughout | PostToolUse on Agent | 14 hooks listed in the doc already exist ✅ | This IS the hook catalog — trim to index with links, not a full rule |
| `docs/security-stack.md` | Prohibits specific attack vectors; many layers blocked automatically | PostToolUse/PreToolUse | All 20 active hooks already registered ✅ | Reference-only — trim to summary table pointing to individual hooks |
| `docs/content-policy.md` | "Prohibited terms must never appear" | PostToolUse on Edit\|Write | `hooks/content-policy.sh` ✅ | Already a pointer stub (empty file found); confirm conversion |

**Note**: `docs/safety-mesh.md` and `docs/security-stack.md` are architectural reference documents — they describe what hooks do, not add new behavior. They are NOT candidates for new hooks; they ARE candidates for trimming to pointer stubs since the actual enforcement is in the hooks.

---

## RULE-CANDIDATE (behavioral guidance for agents)

Docs containing "agents must/should", "when X do Y", "always do" — guidance that belongs as a contextual rule loaded on trigger, not a full markdown doc consumed as prose.

| Doc | Core Guidance | Rule Exists? | Action |
|---|---|---|---|
| `docs/anti-hallucination.md` | "Agents must verify claims against filesystem ground truth"; 10-layer defense with behavioral guidance | `rules/anti-hallucination.md` ✅ | Trim to pointer stub — rule exists |
| `docs/agent-quality.md` | "Agents do minimum → acceptance criteria mandatory"; anti-sycophancy, no stubs in committed code | `rules/agent-quality.md` ✅ | Trim to pointer stub — rule exists |
| `docs/trust-score.md` | "Every agent MUST include Trust Report; 0% confidence = red flag; at least 1 uncertainty required" | `rules/trust-score.md` ✅ | Trim to pointer stub — rule exists |
| `docs/sandbox-sampling.md` | "MUST use sampling for >100 files; NEVER sed on Markdown" | `rules/sandbox-sampling.md` ✅ | Trim to pointer stub — rule exists |
| `docs/dogfooding.md` | "Substantial changes MUST go through SDD; self-hosting required" | `rules/dogfooding.md` ✅ | Trim to pointer stub — rule exists |
| `docs/session-concurrency.md` | "Sessions MUST use advisory locking; session isolation protocol" | `rules/session-concurrency.md` ✅ | Trim to pointer stub — rule exists |
| `docs/fault-tolerance.md` | "Agents MUST check if work already exists before starting; idempotency required" | `rules/fault-tolerance.md` ✅ | Trim to pointer stub — rule exists |
| `docs/phase-system.md` | "When in reconstruction: agents MUST rewrite; when in production: agents MUST use feature flags" | `rules/phase-aware-agents.md` ✅ | Trim to pointer stub — fully covered by phase-aware-agents rule |
| `docs/self-building-protocol.md` | "Orchestrator MUST use its own tools at defined integration points — MUST rules, not SHOULD" | No dedicated rule ❌ (content lives in global CLAUDE.md `Mandatory Self-Usage Protocol`) | The `rules/dogfooding.md` rule covers SDD self-usage; the library-usage mandate is in CLAUDE.md. **Candidate for a new `rules/self-usage.md` rule** if CLAUDE.md is insufficient |
| `docs/definition-of-done.md` | (Already a pointer stub) → points to `/dod-check` skill | `rules/definition-of-done.md` ✅ | Already converted — no action |
| `docs/os-vs-project-separation.md` | "NEVER put project-specific content in .cognitive-os/; OS skills MUST be config-driven not hardcoded" | `rules/os-vs-project.md` ✅ | Trim to pointer stub — rule exists |
| `docs/license-policy.md` | "Antes de integrar CUALQUIER herramienta: verificar licencia; AGPL/SSPL = BLOCKER" | `rules/license-policy.md` ✅ | Trim to pointer stub — rule exists |
| `docs/prompt-driven-governance.md` | "Convert natural-language-judgment hooks to `type: prompt` hooks" — architectural guidance for OS dev | No rule ❌ (ADR proposal, not behavioral rule) | RULE-CANDIDATE: guidance for how to author new hooks → `rules/hook-authoring.md` when ready |
| `docs/agent-efficiency-strategy.md` | "Never load all rules by default; agents MUST use minimum context"; behavioral mandate for orchestrator | `rules/context-optimization.md` ✅ (progressive loading) + `rules/token-economy.md` ✅ | Trim to pointer stub — covered by existing rules |

---

## NEW RULE CANDIDATES (docs with guidance but no existing rule)

These docs contain behavioral guidance that is NOT yet captured in any rule file, making them candidates for new rules rather than pointer stubs.

| Doc | Missing Rule | Why It Matters |
|---|---|---|
| `docs/self-building-protocol.md` | `rules/self-usage.md` | "Orchestrator MUST use its own tools" is a binding protocol not covered by `dogfooding.md` (which only addresses SDD pipeline). The mandate covers: `skill_router.best_match()` on every message, `WorkloadScheduler` for >3 agents, `mem_context` before research. Currently only in CLAUDE.md prose. |
| `docs/phase-system.md` | Already covered by `rules/phase-aware-agents.md` | No new rule needed — confirm phase-system is a pointer stub target |

---

## ALREADY-CONVERTED POINTER STUBS (skip — done)

These docs were already trimmed to 3-line pointer stubs in a previous session:

| Doc | Points To |
|---|---|
| `docs/auto-library.md` | `/recommend-library` skill |
| `docs/automation-doc-sync.md` | `/doc-sync` skill |
| `docs/capability-snapshot.md` | `/capability-snapshot` skill |
| `docs/competitive-arena.md` | `/arena` skill |
| `docs/definition-of-done.md` | `/dod-check` skill |
| `docs/gpu-sandbox.md` | `/gpu-sandbox` skill |
| `docs/health-monitoring.md` | `/cognitive-os-status` skill |
| `docs/plan-system.md` | `/plan-feature` skill |

---

## PURE REFERENCE DOCS (skip — not hook/rule candidates)

Docs with no prohibition or behavioral guidance language — they are design docs, research, competitive analysis, or architectural explanations intended for humans. The parallel skill-candidate pass handles these.

| Doc | Category |
|---|---|
| `docs/adw-patterns.md` | Research/reference (ADW concepts) |
| `docs/architecture/*.md` | Architecture analysis/ADR docs |
| `docs/archived/*.md` | Historical artifacts — already archived |
| `docs/auto-repair-system.md` | Describes the MAPE-K system — reference for how it works |
| `docs/benchmarking.md` | Benchmark methodology — reference |
| `docs/bmad-v6-patterns.md` | Implementation status tracker — reference |
| `docs/business/*.md` | Business docs, roadmaps, value props — human-facing |
| `docs/competitive-*.md` | Competitive analysis — reference |
| `docs/complexity-audit.md` | Audit results — reference |
| `docs/component-audit.md` | Classification audit — reference |
| `docs/component-sources.md` | Source catalog — reference |
| `docs/configurable-quality-gates.md` | Config reference for cognitive-os.yaml |
| `docs/cos-package-manager.md` | Design doc — reference |
| `docs/credential-management.md` | (empty file / already in rules) |
| `docs/dashboard-architecture.md` | Architecture ADR — reference |
| `docs/design-philosophy.md` | Philosophy/metaphor doc — humans only |
| `docs/distributed-architecture.md` | Architecture vision — reference |
| `docs/ecosystem-comparison.md` | Tool comparison — reference |
| `docs/engram-namespaces.md` | Engram design — covered by `rules/engram-organization.md` |
| `docs/execution-backends.md` | Backend abstraction design — reference |
| `docs/faq.md` | FAQ — human reference |
| `docs/gateway-architecture.md` | Gateway ADR — reference |
| `docs/getting-started*.md` | Onboarding docs — human reference |
| `docs/global-vs-project-config.md` | Claude Code config reference — technical reference |
| `docs/hook-security-profiles.md` | Covered by `rules/hook-security-profiles.md` ✅ |
| `docs/hooks.md` | Hook catalog/reference — already documented by hooks/ dir |
| `docs/how-to-extend.md` | Extension guide → skills exist |
| `docs/ide-compatibility.md` | Compatibility matrix — reference |
| `docs/identity-stack.md` | Architecture design — reference |
| `docs/implementation-phases.md` | Roadmap — reference |
| `docs/infra-intent.md` | Covered by `rules/infra-intent.md` ✅ |
| `docs/integrations/*.md` | Integration design docs — reference |
| `docs/launch-strategy.md` | Launch plan — business |
| `docs/leverage-points.md` | Research patterns — reference |
| `docs/multi-model-factory.md` | Vision doc — reference |
| `docs/onboarding-wizard-design.md` | Design doc — reference |
| `docs/open-source-strategy.md` | Business strategy ADR |
| `docs/openclaw-patterns.md` | Pattern adoption log — reference |
| `docs/organizational-model.md` | Analogy/metaphor — reference |
| `docs/os-vs-project-separation.md` | Covered by `rules/os-vs-project.md` ✅ |
| `docs/overview.md` | Product overview — human reference |
| `docs/package-manager-design.md` | Design ADR — reference |
| `docs/patterns-adopted.md` | Pattern catalog — reference |
| `docs/performance.md` | Performance guide — covered by `rules/performance-monitoring.md` ✅ |
| `docs/persistence-map.md` | Persistence reference — technical |
| `docs/phase-system.md` | Covered by `rules/phase-aware-agents.md` ✅ |
| `docs/piter-framework.md` | Research framework — reference |
| `docs/plug-and-play.md` | Architecture vision — reference |
| `docs/product-principles.md` | Product philosophy — human reference |
| `docs/prompt-templates.md` | Template library — reference |
| `docs/quickstart.md` | Onboarding — human reference |
| `docs/recommended-stack.md` | Stack selection — reference |
| `docs/research-log.md` | Research notes — reference |
| `docs/research/*.md` | Research analysis — reference |
| `docs/roadmap.md` | Roadmap — reference |
| `docs/rules-consolidation-plan.md` | Planning doc — reference |
| `docs/rules-loading-architecture.md` | Architecture reference |
| `docs/rules.md` | Rules catalog — covered by `rules/RULES-COMPACT.md` |
| `docs/sandbox-sampling.md` | Covered by `rules/sandbox-sampling.md` ✅ |
| `docs/secret-detection.md` | Covered by `hooks/secret-detector.sh` ✅ |
| `docs/self-improvement-loop.md` | Describes the loop — covered by `rules/self-improvement-protocol.md` ✅ |
| `docs/self-repair-guide.md` | User-facing guide — reference for humans observing COS |
| `docs/self-usage-audit.md` | Audit snapshot — reference |
| `docs/session-concurrency.md` | Covered by `rules/session-concurrency.md` ✅ |
| `docs/singularity.md` | Covered by `rules/singularity.md` ✅ |
| `docs/skills.md` | Skills catalog — reference |
| `docs/state-snapshots.md` | Devbox setup — reference |
| `docs/stress-test-strategy.md` | Stress test plan — reference |
| `docs/testing*.md` | Test docs — reference |
| `docs/tool-stack.md` | Tool research — reference |
| `docs/trust-model.md` | User-facing trust explanation — human reference |
| `docs/trust-score.md` | Covered by `rules/trust-score.md` ✅ |
| `docs/ui-platforms-evaluation.md` | Tool evaluation — reference |
| `docs/ux-principles.md` | UX philosophy — human reference |
| `docs/versioning-strategy.md` | Versioning guide — reference |
| `docs/zero-touch-engineering.md` | Vision doc — reference |

---

## Summary

| Category | Count | Action |
|---|---|---|
| Docs with hook coverage already existing | 5 | Trim to pointer stub (hooks fully implemented) |
| Docs with rule coverage already existing | 12 | Trim to pointer stub (rules fully implemented) |
| Docs needing a new rule (not yet covered) | 1 | Create `rules/self-usage.md` from `self-building-protocol.md` content |
| Docs needing a new hook (not yet covered) | 0 | None — all enforcement language already has hooks |
| Already-converted pointer stubs (done) | 8 | No action needed |
| Pure reference docs (skip) | ~70 | Handled by parallel skill-candidate pass |

**Estimated token savings from trimming the 17 hook/rule-duplicating docs to pointer stubs**: ~15K–20K tokens freed from docs/ context (each doc avg ~1K tokens → 17 docs = ~17K tokens, reduced to 3 lines each ≈ 50 tokens each).

**Single new artifact recommended**:
- `rules/self-usage.md` — Extract the "Mandatory Self-Usage Protocol" from `docs/self-building-protocol.md` into a proper rule file that agents can load on trigger. The CLAUDE.md version is prose; a rule file would be structured, scannable, and hookable.

---

## Docs Confirmed as Rule Duplicates → Immediate Pointer Stub Candidates

These 12 docs have a 1:1 rule counterpart and add zero behavioral guidance beyond what the rule already states:

1. `docs/anti-hallucination.md` → `rules/anti-hallucination.md`
2. `docs/agent-quality.md` → `rules/agent-quality.md`
3. `docs/trust-score.md` → `rules/trust-score.md`
4. `docs/sandbox-sampling.md` → `rules/sandbox-sampling.md`
5. `docs/dogfooding.md` → `rules/dogfooding.md`
6. `docs/session-concurrency.md` → `rules/session-concurrency.md`
7. `docs/fault-tolerance.md` → `rules/fault-tolerance.md`
8. `docs/phase-system.md` → `rules/phase-aware-agents.md`
9. `docs/os-vs-project-separation.md` → `rules/os-vs-project.md`
10. `docs/license-policy.md` → `rules/license-policy.md`
11. `docs/agent-efficiency-strategy.md` → `rules/context-optimization.md` + `rules/token-economy.md`
12. `docs/self-improvement-loop.md` → `rules/self-improvement-protocol.md`

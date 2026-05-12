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
| `docs/09-Quality/root/secret-detection.md` | Block content with secrets/injection patterns before Engram save; PostToolUse on Write | PostToolUse on Edit\|Write | `hooks/secret-detector.sh` ✅ | Trim to pointer stub — fully covered |
| `docs/05-Methodology/root/blocked-tools.md` | Block AGPL/SSPL/BSL libraries from being adopted | PreToolUse on Agent (license check) | `hooks/clarification-gate.sh` partial; `rules/license-policy.md` covers it | Trim to pointer stub — behavioral aspect is a rule, no new hook needed |
| `docs/04-Concepts/root/safety-mesh.md` | "Never allow low-confidence results in production", "BLOCK" language throughout | PostToolUse on Agent | 14 hooks listed in the doc already exist ✅ | This IS the hook catalog — trim to index with links, not a full rule |
| `docs/04-Concepts/root/security-stack.md` | Prohibits specific attack vectors; many layers blocked automatically | PostToolUse/PreToolUse | All 20 active hooks already registered ✅ | Reference-only — trim to summary table pointing to individual hooks |
| `docs/content-policy.md` | "Prohibited terms must never appear" | PostToolUse on Edit\|Write | `hooks/content-policy.sh` ✅ | Already a pointer stub (empty file found); confirm conversion |

**Note**: `docs/04-Concepts/root/safety-mesh.md` and `docs/04-Concepts/root/security-stack.md` are architectural reference documents — they describe what hooks do, not add new behavior. They are NOT candidates for new hooks; they ARE candidates for trimming to pointer stubs since the actual enforcement is in the hooks.

---

## RULE-CANDIDATE (behavioral guidance for agents)

Docs containing "agents must/should", "when X do Y", "always do" — guidance that belongs as a contextual rule loaded on trigger, not a full markdown doc consumed as prose.

| Doc | Core Guidance | Rule Exists? | Action |
|---|---|---|---|
| `docs/04-Concepts/root/anti-hallucination.md` | "Agents must verify claims against filesystem ground truth"; 10-layer defense with behavioral guidance | `rules/anti-hallucination.md` ✅ | Trim to pointer stub — rule exists |
| `docs/07-Capabilities/root/agent-quality.md` | "Agents do minimum → acceptance criteria mandatory"; anti-sycophancy, no stubs in committed code | `rules/agent-quality.md` ✅ | Trim to pointer stub — rule exists |
| `docs/04-Concepts/root/trust-score.md` | "Every agent MUST include Trust Report; 0% confidence = red flag; at least 1 uncertainty required" | `rules/trust-score.md` ✅ | Trim to pointer stub — rule exists |
| `docs/04-Concepts/root/sandbox-sampling.md` | "MUST use sampling for >100 files; NEVER sed on Markdown" | `rules/sandbox-sampling.md` ✅ | Trim to pointer stub — rule exists |
| `docs/04-Concepts/root/dogfooding.md` | "Substantial changes MUST go through SDD; self-hosting required" | `rules/dogfooding.md` ✅ | Trim to pointer stub — rule exists |
| `docs/04-Concepts/root/session-concurrency.md` | "Sessions MUST use advisory locking; session isolation protocol" | `rules/session-concurrency.md` ✅ | Trim to pointer stub — rule exists |
| `docs/04-Concepts/root/fault-tolerance.md` | "Agents MUST check if work already exists before starting; idempotency required" | `rules/fault-tolerance.md` ✅ | Trim to pointer stub — rule exists |
| `docs/04-Concepts/root/phase-system.md` | "When in reconstruction: agents MUST rewrite; when in production: agents MUST use feature flags" | `rules/phase-aware-agents.md` ✅ | Trim to pointer stub — fully covered by phase-aware-agents rule |
| `docs/04-Concepts/root/self-building-protocol.md` | "Orchestrator MUST use its own tools at defined integration points — MUST rules, not SHOULD" | No dedicated rule ❌ (content lives in global CLAUDE.md `Mandatory Self-Usage Protocol`) | The `rules/dogfooding.md` rule covers SDD self-usage; the library-usage mandate is in CLAUDE.md. **Candidate for a new `rules/self-usage.md` rule** if CLAUDE.md is insufficient |
| `docs/05-Methodology/root/definition-of-done.md` | (Already a pointer stub) → points to `/dod-check` skill | `rules/definition-of-done.md` ✅ | Already converted — no action |
| `docs/04-Concepts/root/os-vs-project-separation.md` | "NEVER put project-specific content in .cognitive-os/; OS skills MUST be config-driven not hardcoded" | `rules/os-vs-project.md` ✅ | Trim to pointer stub — rule exists |
| `docs/license-policy.md` | "Antes de integrar CUALQUIER herramienta: verificar licencia; AGPL/SSPL = BLOCKER" | `rules/license-policy.md` ✅ | Trim to pointer stub — rule exists |
| `docs/05-Methodology/root/prompt-driven-governance.md` | "Convert natural-language-judgment hooks to `type: prompt` hooks" — architectural guidance for OS dev | No rule ❌ (ADR proposal, not behavioral rule) | RULE-CANDIDATE: guidance for how to author new hooks → `rules/hook-authoring.md` when ready |
| `docs/07-Capabilities/root/agent-efficiency-strategy.md` | "Never load all rules by default; agents MUST use minimum context"; behavioral mandate for orchestrator | `rules/context-optimization.md` ✅ (progressive loading) + `rules/token-economy.md` ✅ | Trim to pointer stub — covered by existing rules |

---

## NEW RULE CANDIDATES (docs with guidance but no existing rule)

These docs contain behavioral guidance that is NOT yet captured in any rule file, making them candidates for new rules rather than pointer stubs.

| Doc | Missing Rule | Why It Matters |
|---|---|---|
| `docs/04-Concepts/root/self-building-protocol.md` | `rules/self-usage.md` | "Orchestrator MUST use its own tools" is a binding protocol not covered by `dogfooding.md` (which only addresses SDD pipeline). The mandate covers: `skill_router.best_match()` on every message, `WorkloadScheduler` for >3 agents, `mem_context` before research. Currently only in CLAUDE.md prose. |
| `docs/04-Concepts/root/phase-system.md` | Already covered by `rules/phase-aware-agents.md` | No new rule needed — confirm phase-system is a pointer stub target |

---

## ALREADY-CONVERTED POINTER STUBS (skip — done)

These docs were already trimmed to 3-line pointer stubs in a previous session:

| Doc | Points To |
|---|---|
| `docs/04-Concepts/root/auto-library.md` | `/recommend-library` skill |
| `docs/05-Methodology/root/automation-doc-sync.md` | `/doc-sync` skill |
| `docs/07-Capabilities/root/capability-snapshot.md` | `/capability-snapshot` skill |
| `docs/08-References/root/competitive-arena.md` | `/arena` skill |
| `docs/05-Methodology/root/definition-of-done.md` | `/dod-check` skill |
| `docs/04-Concepts/root/gpu-sandbox.md` | `/gpu-sandbox` skill |
| `docs/04-Concepts/root/health-monitoring.md` | `/cognitive-os-status` skill |
| `docs/04-Concepts/root/plan-system.md` | `/plan-feature` skill |

---

## PURE REFERENCE DOCS (skip — not hook/rule candidates)

Docs with no prohibition or behavioral guidance language — they are design docs, research, competitive analysis, or architectural explanations intended for humans. The parallel skill-candidate pass handles these.

| Doc | Category |
|---|---|
| `docs/08-References/root/adw-patterns.md` | Research/reference (ADW concepts) |
| `docs/04-Concepts/architecture/*.md` | Architecture analysis/ADR docs |
| `docs/99-Archive/archived/*.md` | Historical artifacts — already archived |
| `docs/04-Concepts/root/auto-repair-system.md` | Describes the MAPE-K system — reference for how it works |
| `docs/08-References/root/benchmarking.md` | Benchmark methodology — reference |
| `docs/08-References/root/bmad-v6-patterns.md` | Implementation status tracker — reference |
| `docs/08-References/business/*.md` | Business docs, roadmaps, value props — human-facing |
| `docs/competitive-*.md` | Competitive analysis — reference |
| `docs/06-Daily/root/complexity-audit.md` | Audit results — reference |
| `docs/06-Daily/root/component-audit.md` | Classification audit — reference |
| `docs/04-Concepts/root/component-sources.md` | Source catalog — reference |
| `docs/05-Methodology/root/configurable-quality-gates.md` | Config reference for cognitive-os.yaml |
| `docs/07-Capabilities/root/cos-package-manager.md` | Design doc — reference |
| `docs/credential-management.md` | (empty file / already in rules) |
| `docs/04-Concepts/root/dashboard-architecture.md` | Architecture ADR — reference |
| `docs/04-Concepts/root/design-philosophy.md` | Philosophy/metaphor doc — humans only |
| `docs/04-Concepts/root/distributed-architecture.md` | Architecture vision — reference |
| `docs/04-Concepts/root/ecosystem-comparison.md` | Tool comparison — reference |
| `docs/04-Concepts/root/engram-namespaces.md` | Engram design — covered by `rules/engram-organization.md` |
| `docs/04-Concepts/root/execution-backends.md` | Backend abstraction design — reference |
| `docs/00-MOCs/entrypoints/faq.md` | FAQ — human reference |
| `docs/04-Concepts/root/gateway-architecture.md` | Gateway ADR — reference |
| `docs/05-Methodology/getting-started*.md` | Onboarding docs — human reference |
| `docs/04-Concepts/root/global-vs-project-config.md` | Claude Code config reference — technical reference |
| `docs/09-Quality/root/hook-security-profiles.md` | Covered by `rules/hook-security-profiles.md` ✅ |
| `docs/05-Methodology/root/hooks.md` | Hook catalog/reference — already documented by hooks/ dir |
| `docs/05-Methodology/root/how-to-extend.md` | Extension guide → skills exist |
| `docs/04-Concepts/root/ide-compatibility.md` | Compatibility matrix — reference |
| `docs/04-Concepts/root/identity-stack.md` | Architecture design — reference |
| `docs/01-Build-Log/root/implementation-phases.md` | Roadmap — reference |
| `docs/04-Concepts/root/infra-intent.md` | Covered by `rules/infra-intent.md` ✅ |
| `docs/08-References/integrations/*.md` | Integration design docs — reference |
| `docs/01-Build-Log/root/launch-strategy.md` | Launch plan — business |
| `docs/04-Concepts/root/leverage-points.md` | Research patterns — reference |
| `docs/04-Concepts/root/multi-model-factory.md` | Vision doc — reference |
| `docs/04-Concepts/root/onboarding-wizard-design.md` | Design doc — reference |
| `docs/08-References/root/open-source-strategy.md` | Business strategy ADR |
| `docs/08-References/root/openclaw-patterns.md` | Pattern adoption log — reference |
| `docs/04-Concepts/root/organizational-model.md` | Analogy/metaphor — reference |
| `docs/04-Concepts/root/os-vs-project-separation.md` | Covered by `rules/os-vs-project.md` ✅ |
| `docs/00-MOCs/entrypoints/overview.md` | Product overview — human reference |
| `docs/04-Concepts/root/package-manager-design.md` | Design ADR — reference |
| `docs/08-References/root/patterns-adopted.md` | Pattern catalog — reference |
| `docs/04-Concepts/root/performance.md` | Performance guide — covered by `rules/performance-monitoring.md` ✅ |
| `docs/04-Concepts/root/persistence-map.md` | Persistence reference — technical |
| `docs/04-Concepts/root/phase-system.md` | Covered by `rules/phase-aware-agents.md` ✅ |
| `docs/08-References/root/piter-framework.md` | Research framework — reference |
| `docs/04-Concepts/root/plug-and-play.md` | Architecture vision — reference |
| `docs/04-Concepts/root/product-principles.md` | Product philosophy — human reference |
| `docs/05-Methodology/root/prompt-templates.md` | Template library — reference |
| `docs/00-MOCs/entrypoints/quickstart.md` | Onboarding — human reference |
| `docs/08-References/root/recommended-stack.md` | Stack selection — reference |
| `docs/03-PoCs/root/research-log.md` | Research notes — reference |
| `docs/03-PoCs/research/*.md` | Research analysis — reference |
| `docs/01-Build-Log/root/roadmap.md` | Roadmap — reference |
| `docs/05-Methodology/root/rules-consolidation-plan.md` | Planning doc — reference |
| `docs/04-Concepts/root/rules-loading-architecture.md` | Architecture reference |
| `docs/05-Methodology/root/rules.md` | Rules catalog — covered by `rules/RULES-COMPACT.md` |
| `docs/04-Concepts/root/sandbox-sampling.md` | Covered by `rules/sandbox-sampling.md` ✅ |
| `docs/09-Quality/root/secret-detection.md` | Covered by `hooks/secret-detector.sh` ✅ |
| `docs/04-Concepts/root/self-improvement-loop.md` | Describes the loop — covered by `rules/self-improvement-protocol.md` ✅ |
| `docs/05-Methodology/root/self-repair-guide.md` | User-facing guide — reference for humans observing COS |
| `docs/06-Daily/root/self-usage-audit.md` | Audit snapshot — reference |
| `docs/04-Concepts/root/session-concurrency.md` | Covered by `rules/session-concurrency.md` ✅ |
| `docs/04-Concepts/root/singularity.md` | Covered by `rules/singularity.md` ✅ |
| `docs/05-Methodology/root/skills.md` | Skills catalog — reference |
| `docs/04-Concepts/root/state-snapshots.md` | Devbox setup — reference |
| `docs/09-Quality/root/stress-test-strategy.md` | Stress test plan — reference |
| `docs/09-Quality/testing*.md` | Test docs — reference |
| `docs/04-Concepts/root/tool-stack.md` | Tool research — reference |
| `docs/04-Concepts/root/trust-model.md` | User-facing trust explanation — human reference |
| `docs/04-Concepts/root/trust-score.md` | Covered by `rules/trust-score.md` ✅ |
| `docs/04-Concepts/root/ui-platforms-evaluation.md` | Tool evaluation — reference |
| `docs/04-Concepts/root/ux-principles.md` | UX philosophy — human reference |
| `docs/01-Build-Log/root/versioning-strategy.md` | Versioning guide — reference |
| `docs/04-Concepts/root/zero-touch-engineering.md` | Vision doc — reference |

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
- `rules/self-usage.md` — Extract the "Mandatory Self-Usage Protocol" from `docs/04-Concepts/root/self-building-protocol.md` into a proper rule file that agents can load on trigger. The CLAUDE.md version is prose; a rule file would be structured, scannable, and hookable.

---

## Docs Confirmed as Rule Duplicates → Immediate Pointer Stub Candidates

These 12 docs have a 1:1 rule counterpart and add zero behavioral guidance beyond what the rule already states:

1. `docs/04-Concepts/root/anti-hallucination.md` → `rules/anti-hallucination.md`
2. `docs/07-Capabilities/root/agent-quality.md` → `rules/agent-quality.md`
3. `docs/04-Concepts/root/trust-score.md` → `rules/trust-score.md`
4. `docs/04-Concepts/root/sandbox-sampling.md` → `rules/sandbox-sampling.md`
5. `docs/04-Concepts/root/dogfooding.md` → `rules/dogfooding.md`
6. `docs/04-Concepts/root/session-concurrency.md` → `rules/session-concurrency.md`
7. `docs/04-Concepts/root/fault-tolerance.md` → `rules/fault-tolerance.md`
8. `docs/04-Concepts/root/phase-system.md` → `rules/phase-aware-agents.md`
9. `docs/04-Concepts/root/os-vs-project-separation.md` → `rules/os-vs-project.md`
10. `docs/license-policy.md` → `rules/license-policy.md`
11. `docs/07-Capabilities/root/agent-efficiency-strategy.md` → `rules/context-optimization.md` + `rules/token-economy.md`
12. `docs/04-Concepts/root/self-improvement-loop.md` → `rules/self-improvement-protocol.md`

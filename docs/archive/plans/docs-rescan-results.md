<!--
RECONCILIATION STATUS: STALE
Reconciled: 2026-04-21
Reason: point-in-time scan output from 2026-04-11. The 8 pointer-trimmed conversions shipped in ws5 (commit a8c6c58); remaining 9 SKILL-CANDIDATE conversions are parked — tracked implicitly under the docs-to-skills-audit plan, not here.
Recommendation: archive; the live tracker for residual conversions is in skill-atomicity-audit + docs-to-skills-audit.
-->

# Docs Re-Scan Results — April 2026

**Date**: 2026-04-11
**Total docs scanned**: 120
**Status**: APPROVED

## Classification Summary

| Category | Count | Token savings |
|---|---|---|
| SKILL-CANDIDATE | 9 | ~18K tokens |
| SKILL-EXISTS (needs pointer trim) | 9 | ~15K tokens |
| POINTER-DONE | 8 | already saved |
| REFERENCE (keep as doc) | 88 | 0 |
| OBSOLETE | 6 | ~7K tokens |

---

## SKILL-CANDIDATE (action needed)

Docs with numbered/procedural steps that should be converted to skills.

| Doc | Proposed Skill | Size (chars) | ~Tokens |
|---|---|---|---|
| `docs/agent-teams-testing.md` | `test-agent-teams` (already exists — pointer needed) | 7,074 | 1,769 |
| `docs/benchmarking.md` | `run-benchmark` (already exists — pointer needed) | 4,893 | 1,223 |
| `docs/getting-started.md` | `cos-setup` (already exists — pointer needed) | 18,351 | 4,588 |
| `docs/getting-started-quick.md` | `cos-quickstart` (already exists — pointer needed) | 2,631 | 658 |
| `docs/quickstart.md` | `cos-quickstart` (duplicate of getting-started-quick.md) | 1,410 | 353 |
| `docs/testing-cognitive-os-suite.md` | `cognitive-os-test` (already exists) | 6,847 | 1,712 |
| `docs/testing-cognitive-os.md` | new skill: `cos-testing-guide` | 11,287 | 2,822 |
| `docs/self-repair-guide.md` | `self-improve` (partially exists) or new `repair-guide` | 14,840 | 3,710 |
| `docs/state-snapshots.md` | `devbox-checkpoint` (already exists — pointer needed) | 1,916 | 479 |

> **Note**: 7 of these 9 already have matching skills. They need pointer stubs, not new skills.
> True new skill candidates: `testing-cognitive-os.md` → `cos-testing-guide`, `self-repair-guide.md` → `repair-guide`

---

## SKILL-EXISTS (needs pointer trim)

Docs whose skill exists but the doc hasn't been trimmed to a pointer yet.

| Doc | Existing Skill | Size (chars) | ~Tokens |
|---|---|---|---|
| `docs/agent-teams-testing.md` | `test-agent-teams` | 7,074 | 1,769 |
| `docs/benchmarking.md` | `run-benchmark` | 4,893 | 1,223 |
| `docs/getting-started.md` | `cos-setup` / `cos-install` | 18,351 | 4,588 |
| `docs/getting-started-quick.md` | `cos-quickstart` | 2,631 | 658 |
| `docs/quickstart.md` | `cos-quickstart` | 1,410 | 353 |
| `docs/testing-cognitive-os-suite.md` | `cognitive-os-test` | 6,847 | 1,712 |
| `docs/state-snapshots.md` | `devbox-checkpoint` | 1,916 | 479 |
| `docs/hook-security-profiles.md` | `switch-security-profile` | 23,519 | 5,880 |
| `docs/self-building-protocol.md` | `self-improve` (partial) | 15,629 | 3,907 |

**Total token savings from pointer conversion**: ~20,569 tokens (~20K)

---

## POINTER-DONE (already converted)

Docs already trimmed to pointer stubs (contain "converted to an on-demand skill").

| Doc | Points to |
|---|---|
| `docs/auto-library.md` | `/recommend-library` |
| `docs/automation-doc-sync.md` | `/doc-sync` |
| `docs/capability-snapshot.md` | `/capability-snapshot` |
| `docs/competitive-arena.md` | `/arena` |
| `docs/definition-of-done.md` | `/dod-check` |
| `docs/gpu-sandbox.md` | `/gpu-sandbox` |
| `docs/health-monitoring.md` | `/cognitive-os-status` |
| `docs/plan-system.md` | `/plan-feature` |

---

## OBSOLETE (delete/archive)

| Doc | Reason |
|---|---|
| `docs/archived/benchmark-results.md` | Explicitly archived, point-in-time artifact from 2026-03-23, outdated |
| `docs/archived/cleanup-verification.md` | Explicitly archived, one-time verification report from 2026-03-22, complete |
| `docs/quickstart.md` | Duplicate of `docs/getting-started-quick.md`; both cover same install steps |
| `docs/launch-strategy.md` | Checklist-style (Phase 0-1), largely stale; action items are done or irrelevant |
| `docs/rules-consolidation-plan.md` | Implementation plan doc (35K chars); consolidation has likely been done; verify and archive |
| `docs/self-usage-audit.md` | Point-in-time audit from 2026-03-29; numbers stale (106 skills listed, many more exist now) |

---

## REFERENCE (no action needed)

Pure knowledge, architecture, research, or strategy docs that should stay as docs.

| Doc | Category |
|---|---|
| `docs/INDEX.md` | Index/navigation |
| `docs/README.md` | Architecture vision |
| `docs/adw-patterns.md` | Theory/framework reference |
| `docs/agent-efficiency-strategy.md` | Strategy/architecture |
| `docs/agent-quality.md` | Theory/system description |
| `docs/agent-teams.md` | Architecture/integration doc |
| `docs/anti-hallucination.md` | Architecture/system description |
| `docs/architecture-principles.md` | Architecture theory |
| `docs/architecture.md` | System architecture |
| `docs/architecture/cos-vs-project-overlap-analysis.md` | Analysis/research |
| `docs/architecture/cross-runtime-portability.md` | Architecture analysis |
| `docs/architecture/cross-tool-landscape.md` | Research/landscape |
| `docs/architecture/project-consumption-patterns.md` | Architecture patterns |
| `docs/architecture/reality-audit.md` | Source of truth reference |
| `docs/architecture/tac-course-reference.md` | Research reference |
| `docs/auto-repair-system.md` | Architecture/system description |
| `docs/automation.md` | Architecture/system description |
| `docs/blocked-tools.md` | License research/decisions |
| `docs/bmad-v6-patterns.md` | Implementation status tracking |
| `docs/business/case-study.md` | Business/marketing |
| `docs/business/executive-summary.md` | Business/marketing |
| `docs/business/features.md` | Product reference |
| `docs/business/kubernetes-for-agents.md` | Conceptual/marketing |
| `docs/business/open-source-design.md` | Architecture/strategy |
| `docs/business/openclaw-implementation-roadmap.md` | Roadmap/planning |
| `docs/business/openclaw-remaining-patterns.md` | Pattern analysis |
| `docs/business/portability-plan.md` | Strategy/planning |
| `docs/business/roadmap.md` | Roadmap |
| `docs/business/value-proposition.md` | Business/marketing |
| `docs/competitive-analysis.md` | Research/competitive |
| `docs/competitive-landscape.md` | Research/competitive |
| `docs/complexity-audit.md` | Analysis/audit |
| `docs/component-audit.md` | Reference/inventory |
| `docs/component-sources.md` | Reference/provenance |
| `docs/configurable-quality-gates.md` | Architecture/configuration |
| `docs/cos-package-manager.md` | Design doc |
| `docs/dashboard-architecture.md` | Architecture/ADR |
| `docs/design-philosophy.md` | Philosophy/vision |
| `docs/distributed-architecture.md` | Architecture vision |
| `docs/dogfooding.md` | Philosophy/process |
| `docs/ecosystem-comparison.md` | Research/competitive |
| `docs/engram-namespaces.md` | Architecture/design |
| `docs/execution-backends.md` | Architecture/design |
| `docs/faq.md` | Reference/knowledge |
| `docs/fault-tolerance.md` | Architecture/comprehensive guide |
| `docs/gateway-architecture.md` | Architecture/competitive |
| `docs/global-vs-project-config.md` | Reference/knowledge |
| `docs/hooks.md` | Reference/inventory |
| `docs/how-to-extend.md` | Pointer to skills (already a pointer) |
| `docs/ide-compatibility.md` | Compatibility reference |
| `docs/identity-stack.md` | Architecture/design |
| `docs/implementation-phases.md` | Roadmap/planning |
| `docs/infra-intent.md` | Architecture/component description |
| `docs/integrations/cursor-cloud-agents.md` | Integration design doc |
| `docs/leverage-points.md` | Framework reference |
| `docs/multi-model-factory.md` | Vision/architecture |
| `docs/onboarding-wizard-design.md` | Design doc (future feature) |
| `docs/open-source-strategy.md` | ADR/strategy |
| `docs/openclaw-patterns.md` | Research/patterns |
| `docs/organizational-model.md` | Conceptual/analogy |
| `docs/os-vs-project-separation.md` | Architecture/principles |
| `docs/overview.md` | Architecture/overview |
| `docs/package-manager-design.md` | Design doc |
| `docs/paperclip-integration.md` | Integration architecture |
| `docs/patterns-adopted.md` | Research/provenance catalog |
| `docs/performance.md` | Architecture/monitoring |
| `docs/persistence-map.md` | Reference/architecture |
| `docs/phase-system.md` | Architecture/system description |
| `docs/piter-framework.md` | Framework reference |
| `docs/product-principles.md` | Product philosophy |
| `docs/prompt-driven-governance.md` | ADR/design proposal |
| `docs/prompt-templates.md` | Reference/catalog |
| `docs/recommended-stack.md` | Research/decisions |
| `docs/research-log.md` | Research/decisions |
| `docs/research/archon-evaluation.md` | Research evaluation |
| `docs/research/minimal-context-principle.md` | Research findings |
| `docs/research/wisc-framework-analysis.md` | Research analysis |
| `docs/roadmap.md` | Roadmap/planning |
| `docs/rules-loading-architecture.md` | Architecture/technical |
| `docs/rules.md` | Reference/inventory |
| `docs/safety-mesh.md` | Architecture/comprehensive |
| `docs/sandbox-sampling.md` | Architecture/system description |
| `docs/secret-detection.md` | Architecture/component |
| `docs/security-stack.md` | Architecture/security posture |
| `docs/self-improvement-loop.md` | Architecture/system description |
| `docs/session-concurrency.md` | Architecture/design |
| `docs/singularity.md` | Architecture/comprehensive |
| `docs/skills.md` | Reference/inventory |
| `docs/stress-test-strategy.md` | Strategy/validation |
| `docs/testing-cognitive-os.md` | Research/testing guide (SKILL-CANDIDATE noted above) |
| `docs/testing.md` | Architecture/test suite |
| `docs/tool-stack.md` | Research/decisions |
| `docs/trust-model.md` | Architecture/trust |
| `docs/trust-score.md` | Architecture/system description |
| `docs/ui-platforms-evaluation.md` | Research/evaluation |
| `docs/ux-principles.md` | Philosophy/UX |
| `docs/versioning-strategy.md` | Architecture/versioning |
| `docs/zero-touch-engineering.md` | Framework/vision |

---

## Action Priority

### High priority (convert to pointers — frees significant context)
1. `docs/hook-security-profiles.md` → pointer to `switch-security-profile` (~5,880 tokens)
2. `docs/getting-started.md` → pointer to `cos-setup` / `cos-install` (~4,588 tokens)
3. `docs/self-building-protocol.md` → pointer to `self-improve` (~3,907 tokens)
4. `docs/testing-cognitive-os-suite.md` → pointer to `cognitive-os-test` (~1,712 tokens)
5. `docs/agent-teams-testing.md` → pointer to `test-agent-teams` (~1,769 tokens)

### Low-hanging fruit (small docs, quick pointers)
6. `docs/benchmarking.md` → pointer to `run-benchmark`
7. `docs/getting-started-quick.md` → pointer to `cos-quickstart`
8. `docs/state-snapshots.md` → pointer to `devbox-checkpoint`

### New skills to create
9. `docs/testing-cognitive-os.md` → create skill `cos-testing-guide`
10. `docs/self-repair-guide.md` → create skill `repair-guide`

### Delete/archive
11. `docs/archived/` contents → already archived subdirectory, safe to keep
12. `docs/quickstart.md` → delete (duplicate of getting-started-quick.md)
13. `docs/launch-strategy.md` → archive (stale action items)
14. `docs/rules-consolidation-plan.md` → verify done, then archive
15. `docs/self-usage-audit.md` → archive (stale point-in-time)

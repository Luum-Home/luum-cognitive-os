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
| `docs/07-Capabilities/root/agent-teams-testing.md` | `test-agent-teams` (already exists — pointer needed) | 7,074 | 1,769 |
| `docs/08-References/root/benchmarking.md` | `run-benchmark` (already exists — pointer needed) | 4,893 | 1,223 |
| `docs/00-MOCs/entrypoints/getting-started.md` | `cos-setup` (already exists — pointer needed) | 18,351 | 4,588 |
| `docs/00-MOCs/entrypoints/getting-started-quick.md` | `cos-quickstart` (already exists — pointer needed) | 2,631 | 658 |
| `docs/00-MOCs/entrypoints/quickstart.md` | `cos-quickstart` (duplicate of getting-started-quick.md) | 1,410 | 353 |
| `docs/09-Quality/root/testing-cognitive-os-suite.md` | `cognitive-os-test` (already exists) | 6,847 | 1,712 |
| `docs/09-Quality/root/testing-cognitive-os.md` | new skill: `cos-testing-guide` | 11,287 | 2,822 |
| `docs/05-Methodology/root/self-repair-guide.md` | `self-improve` (partially exists) or new `repair-guide` | 14,840 | 3,710 |
| `docs/04-Concepts/root/state-snapshots.md` | `devbox-checkpoint` (already exists — pointer needed) | 1,916 | 479 |

> **Note**: 7 of these 9 already have matching skills. They need pointer stubs, not new skills.
> True new skill candidates: `testing-cognitive-os.md` → `cos-testing-guide`, `self-repair-guide.md` → `repair-guide`

---

## SKILL-EXISTS (needs pointer trim)

Docs whose skill exists but the doc hasn't been trimmed to a pointer yet.

| Doc | Existing Skill | Size (chars) | ~Tokens |
|---|---|---|---|
| `docs/07-Capabilities/root/agent-teams-testing.md` | `test-agent-teams` | 7,074 | 1,769 |
| `docs/08-References/root/benchmarking.md` | `run-benchmark` | 4,893 | 1,223 |
| `docs/00-MOCs/entrypoints/getting-started.md` | `cos-setup` / `cos-install` | 18,351 | 4,588 |
| `docs/00-MOCs/entrypoints/getting-started-quick.md` | `cos-quickstart` | 2,631 | 658 |
| `docs/00-MOCs/entrypoints/quickstart.md` | `cos-quickstart` | 1,410 | 353 |
| `docs/09-Quality/root/testing-cognitive-os-suite.md` | `cognitive-os-test` | 6,847 | 1,712 |
| `docs/04-Concepts/root/state-snapshots.md` | `devbox-checkpoint` | 1,916 | 479 |
| `docs/09-Quality/root/hook-security-profiles.md` | `switch-security-profile` | 23,519 | 5,880 |
| `docs/04-Concepts/root/self-building-protocol.md` | `self-improve` (partial) | 15,629 | 3,907 |

**Total token savings from pointer conversion**: ~20,569 tokens (~20K)

---

## POINTER-DONE (already converted)

Docs already trimmed to pointer stubs (contain "converted to an on-demand skill").

| Doc | Points to |
|---|---|
| `docs/04-Concepts/root/auto-library.md` | `/recommend-library` |
| `docs/05-Methodology/root/automation-doc-sync.md` | `/doc-sync` |
| `docs/07-Capabilities/root/capability-snapshot.md` | `/capability-snapshot` |
| `docs/08-References/root/competitive-arena.md` | `/arena` |
| `docs/05-Methodology/root/definition-of-done.md` | `/dod-check` |
| `docs/04-Concepts/root/gpu-sandbox.md` | `/gpu-sandbox` |
| `docs/04-Concepts/root/health-monitoring.md` | `/cognitive-os-status` |
| `docs/04-Concepts/root/plan-system.md` | `/plan-feature` |

---

## OBSOLETE (delete/archive)

| Doc | Reason |
|---|---|
| `docs/99-Archive/archived/benchmark-results.md` | Explicitly archived, point-in-time artifact from 2026-03-23, outdated |
| `docs/99-Archive/archived/cleanup-verification.md` | Explicitly archived, one-time verification report from 2026-03-22, complete |
| `docs/00-MOCs/entrypoints/quickstart.md` | Duplicate of `docs/00-MOCs/entrypoints/getting-started-quick.md`; both cover same install steps |
| `docs/01-Build-Log/root/launch-strategy.md` | Checklist-style (Phase 0-1), largely stale; action items are done or irrelevant |
| `docs/05-Methodology/root/rules-consolidation-plan.md` | Implementation plan doc (35K chars); consolidation has likely been done; verify and archive |
| `docs/06-Daily/root/self-usage-audit.md` | Point-in-time audit from 2026-03-29; numbers stale (106 skills listed, many more exist now) |

---

## REFERENCE (no action needed)

Pure knowledge, architecture, research, or strategy docs that should stay as docs.

| Doc | Category |
|---|---|
| `docs/00-MOCs/entrypoints/INDEX.md` | Index/navigation |
| `docs/00-MOCs/entrypoints/README.md` | Architecture vision |
| `docs/08-References/root/adw-patterns.md` | Theory/framework reference |
| `docs/07-Capabilities/root/agent-efficiency-strategy.md` | Strategy/architecture |
| `docs/07-Capabilities/root/agent-quality.md` | Theory/system description |
| `docs/07-Capabilities/root/agent-teams.md` | Architecture/integration doc |
| `docs/04-Concepts/root/anti-hallucination.md` | Architecture/system description |
| `docs/04-Concepts/architecture-principles.md` | Architecture theory |
| `docs/04-Concepts/architecture.md` | System architecture |
| `docs/04-Concepts/architecture/cos-vs-project-overlap-analysis.md` | Analysis/research |
| `docs/04-Concepts/architecture/cross-runtime-portability.md` | Architecture analysis |
| `docs/04-Concepts/architecture/cross-tool-landscape.md` | Research/landscape |
| `docs/04-Concepts/architecture/project-consumption-patterns.md` | Architecture patterns |
| `docs/04-Concepts/architecture/reality-audit.md` | Source of truth reference |
| `docs/04-Concepts/architecture/tac-course-reference.md` | Research reference |
| `docs/04-Concepts/root/auto-repair-system.md` | Architecture/system description |
| `docs/05-Methodology/root/automation.md` | Architecture/system description |
| `docs/05-Methodology/root/blocked-tools.md` | License research/decisions |
| `docs/08-References/root/bmad-v6-patterns.md` | Implementation status tracking |
| `docs/08-References/business/case-study.md` | Business/marketing |
| `docs/08-References/business/executive-summary.md` | Business/marketing |
| `docs/08-References/business/features.md` | Product reference |
| `docs/08-References/business/kubernetes-for-agents.md` | Conceptual/marketing |
| `docs/08-References/business/open-source-design.md` | Architecture/strategy |
| `docs/08-References/business/openclaw-implementation-roadmap.md` | Roadmap/planning |
| `docs/08-References/business/openclaw-remaining-patterns.md` | Pattern analysis |
| `docs/08-References/business/portability-plan.md` | Strategy/planning |
| `docs/08-References/business/roadmap.md` | Roadmap |
| `docs/08-References/business/value-proposition.md` | Business/marketing |
| `docs/08-References/root/competitive-analysis.md` | Research/competitive |
| `docs/08-References/root/competitive-landscape.md` | Research/competitive |
| `docs/06-Daily/root/complexity-audit.md` | Analysis/audit |
| `docs/06-Daily/root/component-audit.md` | Reference/inventory |
| `docs/04-Concepts/root/component-sources.md` | Reference/provenance |
| `docs/05-Methodology/root/configurable-quality-gates.md` | Architecture/configuration |
| `docs/07-Capabilities/root/cos-package-manager.md` | Design doc |
| `docs/04-Concepts/root/dashboard-architecture.md` | Architecture/ADR |
| `docs/04-Concepts/root/design-philosophy.md` | Philosophy/vision |
| `docs/04-Concepts/root/distributed-architecture.md` | Architecture vision |
| `docs/04-Concepts/root/dogfooding.md` | Philosophy/process |
| `docs/04-Concepts/root/ecosystem-comparison.md` | Research/competitive |
| `docs/04-Concepts/root/engram-namespaces.md` | Architecture/design |
| `docs/04-Concepts/root/execution-backends.md` | Architecture/design |
| `docs/00-MOCs/entrypoints/faq.md` | Reference/knowledge |
| `docs/04-Concepts/root/fault-tolerance.md` | Architecture/comprehensive guide |
| `docs/04-Concepts/root/gateway-architecture.md` | Architecture/competitive |
| `docs/04-Concepts/root/global-vs-project-config.md` | Reference/knowledge |
| `docs/05-Methodology/root/hooks.md` | Reference/inventory |
| `docs/05-Methodology/root/how-to-extend.md` | Pointer to skills (already a pointer) |
| `docs/04-Concepts/root/ide-compatibility.md` | Compatibility reference |
| `docs/04-Concepts/root/identity-stack.md` | Architecture/design |
| `docs/01-Build-Log/root/implementation-phases.md` | Roadmap/planning |
| `docs/04-Concepts/root/infra-intent.md` | Architecture/component description |
| `docs/08-References/integrations/cursor-cloud-agents.md` | Integration design doc |
| `docs/04-Concepts/root/leverage-points.md` | Framework reference |
| `docs/04-Concepts/root/multi-model-factory.md` | Vision/architecture |
| `docs/04-Concepts/root/onboarding-wizard-design.md` | Design doc (future feature) |
| `docs/08-References/root/open-source-strategy.md` | ADR/strategy |
| `docs/08-References/root/openclaw-patterns.md` | Research/patterns |
| `docs/04-Concepts/root/organizational-model.md` | Conceptual/analogy |
| `docs/04-Concepts/root/os-vs-project-separation.md` | Architecture/principles |
| `docs/00-MOCs/entrypoints/overview.md` | Architecture/overview |
| `docs/04-Concepts/root/package-manager-design.md` | Design doc |
| `docs/08-References/root/patterns-adopted.md` | Research/provenance catalog |
| `docs/04-Concepts/root/performance.md` | Architecture/monitoring |
| `docs/04-Concepts/root/persistence-map.md` | Reference/architecture |
| `docs/04-Concepts/root/phase-system.md` | Architecture/system description |
| `docs/08-References/root/piter-framework.md` | Framework reference |
| `docs/04-Concepts/root/product-principles.md` | Product philosophy |
| `docs/05-Methodology/root/prompt-driven-governance.md` | ADR/design proposal |
| `docs/05-Methodology/root/prompt-templates.md` | Reference/catalog |
| `docs/08-References/root/recommended-stack.md` | Research/decisions |
| `docs/03-PoCs/root/research-log.md` | Research/decisions |
| `docs/03-PoCs/research/archon-evaluation.md` | Research evaluation |
| `docs/03-PoCs/research/minimal-context-principle.md` | Research findings |
| `docs/03-PoCs/research/wisc-framework-analysis.md` | Research analysis |
| `docs/01-Build-Log/root/roadmap.md` | Roadmap/planning |
| `docs/04-Concepts/root/rules-loading-architecture.md` | Architecture/technical |
| `docs/05-Methodology/root/rules.md` | Reference/inventory |
| `docs/04-Concepts/root/safety-mesh.md` | Architecture/comprehensive |
| `docs/04-Concepts/root/sandbox-sampling.md` | Architecture/system description |
| `docs/09-Quality/root/secret-detection.md` | Architecture/component |
| `docs/04-Concepts/root/security-stack.md` | Architecture/security posture |
| `docs/04-Concepts/root/self-improvement-loop.md` | Architecture/system description |
| `docs/04-Concepts/root/session-concurrency.md` | Architecture/design |
| `docs/04-Concepts/root/singularity.md` | Architecture/comprehensive |
| `docs/05-Methodology/root/skills.md` | Reference/inventory |
| `docs/09-Quality/root/stress-test-strategy.md` | Strategy/validation |
| `docs/09-Quality/root/testing-cognitive-os.md` | Research/testing guide (SKILL-CANDIDATE noted above) |
| `docs/09-Quality/root/testing.md` | Architecture/test suite |
| `docs/04-Concepts/root/tool-stack.md` | Research/decisions |
| `docs/04-Concepts/root/trust-model.md` | Architecture/trust |
| `docs/04-Concepts/root/trust-score.md` | Architecture/system description |
| `docs/04-Concepts/root/ui-platforms-evaluation.md` | Research/evaluation |
| `docs/04-Concepts/root/ux-principles.md` | Philosophy/UX |
| `docs/01-Build-Log/root/versioning-strategy.md` | Architecture/versioning |
| `docs/04-Concepts/root/zero-touch-engineering.md` | Framework/vision |

---

## Action Priority

### High priority (convert to pointers — frees significant context)
1. `docs/09-Quality/root/hook-security-profiles.md` → pointer to `switch-security-profile` (~5,880 tokens)
2. `docs/00-MOCs/entrypoints/getting-started.md` → pointer to `cos-setup` / `cos-install` (~4,588 tokens)
3. `docs/04-Concepts/root/self-building-protocol.md` → pointer to `self-improve` (~3,907 tokens)
4. `docs/09-Quality/root/testing-cognitive-os-suite.md` → pointer to `cognitive-os-test` (~1,712 tokens)
5. `docs/07-Capabilities/root/agent-teams-testing.md` → pointer to `test-agent-teams` (~1,769 tokens)

### Low-hanging fruit (small docs, quick pointers)
6. `docs/08-References/root/benchmarking.md` → pointer to `run-benchmark`
7. `docs/00-MOCs/entrypoints/getting-started-quick.md` → pointer to `cos-quickstart`
8. `docs/04-Concepts/root/state-snapshots.md` → pointer to `devbox-checkpoint`

### New skills to create
9. `docs/09-Quality/root/testing-cognitive-os.md` → create skill `cos-testing-guide`
10. `docs/05-Methodology/root/self-repair-guide.md` → create skill `repair-guide`

### Delete/archive
11. `docs/99-Archive/archived/` contents → already archived subdirectory, safe to keep
12. `docs/00-MOCs/entrypoints/quickstart.md` → delete (duplicate of getting-started-quick.md)
13. `docs/01-Build-Log/root/launch-strategy.md` → archive (stale action items)
14. `docs/05-Methodology/root/rules-consolidation-plan.md` → verify done, then archive
15. `docs/06-Daily/root/self-usage-audit.md` → archive (stale point-in-time)

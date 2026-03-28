# Component Audit — CORE vs PACKAGE Classification

## Summary

This document tracks the classification of every Cognitive OS component as CORE (kernel) or PACKAGE (optional add-on). Use `/component-classifier` to classify new components.

## Classification Criteria

| Signal | CORE | PACKAGE |
|---|---|---|
| OS boots without it? | No | Yes |
| External tool dependency? | No | Yes |
| Domain-specific? | No | Yes |
| Used by >50% of components? | Yes | No |
| Can be installed/removed independently? | No | Yes |

## CORE Components

Components that are part of the OS kernel and versioned with the OS itself.

### Hooks (CORE)

| Hook | Reason |
|---|---|
| session-init.sh | OS lifecycle — session startup |
| session-cleanup.sh | OS lifecycle — session teardown |
| crash-recovery.sh | OS lifecycle — recovery after crash |
| error-pipeline.sh | Foundational error capture |
| secret-detector.sh | Security — always required |
| content-policy.sh | Security — always required |
| rate-limiter.sh | Fundamental governance |
| result-truncator.sh | Context protection |
| auto-checkpoint.sh | OS lifecycle — data safety |
| self-install.sh | OS lifecycle — dogfooding bootstrap |

### Rules (CORE)

| Rule | Reason |
|---|---|
| adaptive-bypass.md | Fundamental workflow routing |
| acceptance-criteria.md | Quality gate — always active |
| agent-quality.md | Quality meta-rule — always active |
| closed-loop-prompts.md | Fundamental agent execution pattern |
| context-management.md | Context protection — always active |
| fault-tolerance.md | OS resilience — always active |
| rate-limiting.md | Fundamental governance |
| token-economy.md | Cost governance — always active |
| trust-score.md | Verification — always active |
| phase-aware-agents.md | Phase system — always active |
| definition-of-done.md | Quality gate — always active |
| model-routing.md | Model selection — always active |
| resource-governance.md | Budget enforcement — always active |
| credential-management.md | Security — always active |
| content-policy.md | Security — always active |
| license-policy.md | Legal compliance — always active |

### Libs (CORE)

| Lib | Reason |
|---|---|
| model_router.py | Used by >50% of components for model selection |
| cost_dashboard.py | Used by >50% of components for cost tracking |
| rate_limiter.py | Fundamental governance enforcement |
| agent_permissions.py | Security — permission system |
| secret_ref.py | Security — credential resolution |
| checkpoint_manager.py | OS lifecycle — crash recovery |

### Skills (CORE)

| Skill | Reason |
|---|---|
| cognitive-os-init | OS lifecycle — project bootstrap |
| cognitive-os-test | OS lifecycle — self-test |
| cognitive-os-status | OS lifecycle — health check |
| capability-snapshot | OS lifecycle — capability protection |
| compose-prompt | Fundamental prompt composition |
| component-classifier | OS governance — classification system |

## PACKAGE Components

Components that can be installed/removed independently. Each has its own semver version.

### External Tool Integrations

| Package | External Tool | Version |
|---|---|---|
| @luum/semgrep-scan | Semgrep SAST | 1.0.0 |
| @luum/cognee-integration | Cognee knowledge graph | 0.1.0 |
| @luum/repomix-integration | Repomix repo analysis | 0.1.0 |

### Domain-Specific Skills

| Package | Domain | Version |
|---|---|---|
| @luum/deep-research | Research & analysis | 0.1.0 |
| @luum/eval-repo | Repository evaluation | 0.1.0 |
| @luum/audit-website | Web auditing | 0.1.0 |
| @luum/arena | Competitive benchmarking | 0.1.0 |
| @luum/contract-drift | API contract validation | 0.1.0 |

### Quality Add-ons

| Package | Purpose | Version |
|---|---|---|
| @luum/quality-gates | Extended quality checks | 1.0.0 |
| @luum/trust-system | Trust score + confidence gate + consequence | 1.0.0 |
| @luum/estimation | Planning poker + calibration | 0.1.0 |

## Audit Log

| Date | Component | Classification | Classified By |
|---|---|---|---|
| 2026-03-28 | component-classifier | CORE | Initial audit |
| 2026-03-28 | component-classification.md | CORE | Initial audit |

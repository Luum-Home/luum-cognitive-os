<!-- SCOPE: os-only -->
---
name: cos-maintainer-operations
description: Use when maintaining Cognitive OS capability/audit/control-plane scripts such as ACC, active primitive index,
  adapter compile, CI local validation, memory lifecycle doctor, runtime hook reality, release/security red-team, proof drills,
  or script exposure follow-up. Prefer these canonical scripts instead of ad-hoc repo scans.
version: 1.0.0
user-invocable: true
audience: os-dev
tags:
- maintainer
- scripts
- audits
- capability
- release
- security
- proof
summary_line: Route high-value COS maintainer operations through canonical scripts.
platforms:
- claude-code
- codex
- shell
routing_intents:
- intent: cos_maintainer_operations
  description: User wants to run or maintain Cognitive OS capability, audit, control-plane, release, red-team, proof, or operational
    scripts.
  confidence: 0.84
---

# COS Maintainer Operations

## Purpose

Use canonical Cognitive OS maintainer primitives instead of rediscovering or
rewriting audit/control-plane commands.

## Fast command map

| Intent | Canonical script |
|---|---|
| Agent Capability Coverage refresh/report | `scripts/acc_pipeline.py --project-dir . --refresh` |
| Active primitive inventory | `scripts/cos-active-primitive-index --json` |
| Consumer adapter compile/projection proof | `scripts/cos-adapter-compile <harness> --output <dir> --dry-run --json` |
| Adoption profile check | `scripts/cos-adoption-profile --profile core` |
| Local CI lane | `scripts/cos-ci-local.sh` |
| Core skill availability | `scripts/cos-core-skills-check.sh` |
| Memory lifecycle doctor | `scripts/cos-doctor-memory-lifecycle.sh` |
| New ADR creation | `scripts/cos-new-adr` |
| Runtime hook reality audit | `scripts/cos-runtime-hook-reality` |
| SessionStart budget audit | `scripts/cos-session-start-budget` |
| Silent failure audit | `scripts/cos-silent-failure-audit` |
| WIP safety score | `scripts/cos-wip-safety-score` |
| Release creation | `scripts/create-release.sh` |
| Security red-team runner | `scripts/security_red_team.py` |
| Proof drill selection | `scripts/proof-drill-select` |

## Workflow

1. Pick the smallest matching command from the table.
2. Prefer `--json` or dry-run modes when available.
3. If a command writes generated reports, stage only the intended report outputs.
4. For broad validation, use `scripts/cos-ci-local.sh` before heavier release lanes.

## Validation

```bash
python3 -m py_compile scripts/acc_pipeline.py scripts/security_red_team.py
bash -n scripts/cos-ci-local.sh scripts/create-release.sh
```

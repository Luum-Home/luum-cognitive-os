<!-- SCOPE: os-only -->
---
name: cos-install-operations
description: Use when installing, bootstrapping, upgrading, uninstalling, onboarding, or safely running Cognitive OS operator/setup
  scripts. Routes setup and install work through protected canonical scripts instead of ad-hoc shell commands.
version: 1.0.0
user-invocable: true
audience: os-dev
tags:
- install
- bootstrap
- upgrade
- setup
- operator
- protected-surface
summary_line: Route COS install/bootstrap/upgrade/operator setup through canonical scripts.
platforms:
- claude-code
- codex
- shell
routing_intents:
- intent: cos_install_operations
  description: User wants to install, bootstrap, upgrade, uninstall, onboard, or safely run Cognitive OS operator setup scripts.
  confidence: 0.84
---

# COS Install Operations

## Purpose

Use this skill for Cognitive OS install, bootstrap, upgrade, uninstall,
onboarding, and credential-safe operator setup flows.

## Protected command map

| Intent | Canonical script |
|---|---|
| Bootstrap/update COS surfaces | `scripts/cos-bootstrap.sh` |
| Credential-safe command runner | `scripts/cos-credential-safe-run` |
| Record onboarding evidence | `scripts/cos-record-onboarding.sh` |
| Weekly/profile config audit | `scripts/cos-weekly-config-audit.sh` |
| Initialize/project COS into a target | `scripts/cos_init.py` |
| Setup dependencies/profiles | `scripts/setup.sh` |
| Uninstall projected surfaces | `scripts/uninstall.sh` |
| Upgrade projected surfaces | `scripts/upgrade.sh` |

## Workflow

1. Prefer dry-run/JSON flags when the target script supports them.
2. Treat these scripts as protected install/profile surfaces: do not demote or
   archive them without checking `manifests/primitive-readiness-protected-install-surfaces.yaml`.
3. Never pass credentials inline; use environment variables or the credential-safe runner.
4. After install/profile changes, run the relevant doctor or audit before claiming success.

## Validation

```bash
bash -n scripts/cos-bootstrap.sh scripts/setup.sh scripts/uninstall.sh scripts/upgrade.sh
python3 -m py_compile scripts/cos_init.py
```

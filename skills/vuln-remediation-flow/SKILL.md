<!-- SCOPE: os-only -->
---
name: vuln-remediation-flow
invocation_pattern: on-demand
command: /vuln-remediation-flow
description: Lab-stage propose-only cloud flow contract for sandboxed vulnerability remediation.
version: 0.1.0
audience: os
tags: [flows, vulnerability-remediation, cloud-worker, lab]
last-updated: 2026-05-04
effort: sonnet
lifecycle_state: lab
criticality: standard
flow_contract: flow_contract.yaml
framing_exercise_statement:
  boots_cos_init: partial
  uses_native_engram_client: partial
  dispatches_through_configured_providers: partial
  hooks_fire_natively: partial
  session_lifecycle_handled: partial
  notes: Lab registration establishes the contract before worker execution; each axis remains partial until the Docker/cloud worker path runs the flow end-to-end.
routing_patterns:
  - pattern: '\bvuln[- ]?remediation[- ]?flow\b'
    confidence: 0.95
  - pattern: '\bvulnerability\s+remediation\b'
    confidence: 0.85
  - pattern: '\bsandboxed\s+vulnerability\s+remediation\b'
    confidence: 0.75
---

# Vulnerability Remediation Flow

## Purpose

Register the first lab cloud-flow contract for Cognitive OS: sandboxed
vulnerability remediation that produces a reviewed proposal instead of landing
changes autonomously.

## Contract

The machine-readable contract is `flow_contract.yaml` in this directory. Validate it with:

```bash
scripts/cos-flow-register.sh --check --contract skills/vuln-remediation-flow/flow_contract.yaml
```

## Inputs

Accepted input classes:

- CVE feed item
- Semgrep finding
- Dependabot alert
- Manual vulnerability report copied into a tracked evidence file

Each input must have a stable identifier and a deterministic source before the
flow can move beyond `advisory`.

## Output

The flow produces a proposal bundle under `docs/proposals/` or
`.cognitive-os/proposals/`. The proposal must include:

1. the source vulnerability identifier;
2. the sandbox commands run;
3. test and rescan evidence;
4. a reviewer signature field;
5. explicit non-merge status.

## Safety Contract

- No auto-merge.
- No direct push to `main` or `master`.
- No promotion to `core` or `team`.
- No invented evidence.
- No bypass of governance gates.
- Human approval is mandatory for any proposed patch.

## Current Lab Boundary

This skill is a registration surface, not a claim that the cloud worker runtime
is complete. ADR-140, ADR-141, and ADR-142 still need their worker, replication,
and audit surfaces before this flow can be promoted.

## Contextual Trigger

Use this skill when the task is to register, validate, or iterate on the first
COS cloud vulnerability-remediation flow contract.

---
adr: 203
title: Subagent Capability Contract and Launch Preflight
status: accepted
implementation_status: not-applicable
date: '2026-05-06'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted decision/policy record with no explicit implementation
  surface
---

# ADR-203 — Subagent Capability Contract and Launch Preflight

## Status
Accepted


<!-- SCOPE: OS -->

**Status**: Accepted  
**Date**: 2026-05-06  
**Related**: ADR-032, ADR-056, ADR-111, ADR-190, ADR-201, ADR-202  
**Implementation**: `manifests/subagent-capabilities.yaml`, `scripts/subagent_launch_preflight.py`, `scripts/cos subagent preflight`

---

## Context

A parallel research launch selected `Explore` subagents for tasks that required
writing markdown artifacts under `.cognitive-os/strategy/research/`. `Explore`
completed correctly as read-only agents and returned results, but could not
write files. One `general-purpose` agent wrote successfully because it had write
capability.

The operator explanation was honest but incomplete: this was not only a launch
mistake. It exposed a missing machine-readable contract between selected
subagent type and required output mode.

The unsafe implicit rule was:

```text
research -> Explore
```

The correct rule is:

```text
research + no file artifact required -> Explore
research + write artifact required -> general-purpose / worker
implementation -> worker / general-purpose
inspection only -> Explore
```

This repeats the recent self-bite pattern:

```text
implicit contract + automatic execution + no preflight = operational failure
```

## Decision

Define a manifest-backed subagent capability contract and a launch preflight.

Each subagent type declares:

- purpose;
- read/write/edit/spawn capability;
- allowed output modes;
- aliases;
- safe fallback types;
- guidance for parent-orchestrator persistence.

The preflight compares selected subagent type against the prompt's required
output capabilities before launch.

If a prompt requires file artifacts and the selected subagent type cannot write,
the launch must block unless the prompt explicitly declares parent persistence
or `result_only` output.

## Contract

```yaml
subagent_types:
  explore:
    purpose: codebase search and read-only analysis
    can_read: true
    can_write: false
    can_edit: false
    can_spawn: false
    output_modes: [result_only]

  general-purpose:
    purpose: implementation, artifact writing, broad task execution
    can_read: true
    can_write: true
    can_edit: true
    can_spawn: false
    output_modes: [result, file_artifact]
```

## Blocking rule

```text
if prompt_requires_file_artifact and not subagent.can_write:
    BLOCK launch
```

The block message must explain:

- selected type;
- missing capability;
- detected artifact requirement;
- safe alternatives;
- explicit parent-persistence override if appropriate.

## Parent persistence exception

`Explore` remains valid for research if the orchestrator declares:

```text
Explore read-only and return result only; parent will persist artifacts.
```

That exception must be explicit because it changes ownership of artifact
creation from the child agent to the parent orchestrator.

## Consequences

### Positive

- Read-only agents remain safe by design.
- Research tasks that need durable artifacts use a writer-capable type.
- The system catches impossible launches before parallel fan-out.
- Capability mismatches become telemetry for ADR-201 instead of hidden manual
  recovery work.

### Negative / trade-offs

- Some borderline prompts may require the operator to specify `result_only` or
  parent persistence.
- The first detector is heuristic and must be refined from telemetry.
- Harness-native agent type names must be normalized through aliases.

## Alternatives rejected

- **Always use general-purpose for research**: rejected because it removes the
  safety value of read-only exploration.
- **Let Explore return results and let the parent write manually**: rejected as
  the default because it creates serial recovery work and can lose provenance.
- **Rely on agent judgment**: rejected because agent type capabilities are known
  before launch and should be enforced mechanically.
- **Document only**: rejected because the previous failure happened despite the
  read-only contract existing in prose.

## Telemetry

Every mismatch should emit or be convertible to ADR-201 evidence:

```json
{
  "event": "subagent_capability_mismatch",
  "agent_type": "Explore",
  "prompt_requires_write": true,
  "write_capability": false,
  "classification": "capability_contract_mismatch"
}
```

Repeated mismatches should trigger `PromoteFromTelemetry` proposals to lower
selector confidence, change launch prompts, or expand tests.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_subagent_launch_preflight.py -q
scripts/cos subagent preflight --type Explore --prompt 'write research/02-real-self-improvement.md' --json
scripts/cos subagent preflight --type Explore --prompt 'Explore read-only and return result only; parent will persist artifacts to research/02.md' --json
```

The first command must block. The second must pass because parent persistence is
explicit.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

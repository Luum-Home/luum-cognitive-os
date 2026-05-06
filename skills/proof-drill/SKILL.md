<!-- SCOPE: both -->
---
name: proof-drill
version: 1.0.0
description: Select and run opt-in proof drills and smoke checks for COS self-build and consumer-project validation without polluting default test lanes.
summary_line: Select opt-in proof drills and smoke checks without default-lane pollution.
audience: both
platforms: [claude-code, codex, shell]
triggers:
  - proof drill
  - smoke opt-in
  - one-off smoke
  - runtime proof
  - prove headless
  - prueba manual
  - prueba opt-in
routing_patterns:
  - pattern: '\bproof[- ]?drill\b'
    confidence: 0.95
  - pattern: '\brun\s+proof\s+drills?\b'
    confidence: 0.85
  - pattern: '\bsmoke\s+check\s+(cos|self[- ]build)\b'
    confidence: 0.75
---

# Proof Drill

Use this skill when an operator asks for a proof drill, one-off smoke, provider
smoke, Docker/headless runtime proof, or a validation that is intentionally too
heavy or account-backed for normal test lanes.

## Contract

The registry at `manifests/proof-drill-registry.yaml` is the source of truth for
what the SO can run, where it may run, and whether it belongs to COS self-build
or a consumer project.

Do not add smoke opt-ins or proof drills to default laptop, CI, or project test
lanes. They are explicit runtime qualifications.

## Procedure

1. Classify the request:
   - `os-self`: the check builds or qualifies this Cognitive OS repository.
   - `consumer-project`: the check validates a downstream project using COS.
   - `both`: the check has separate SO and consumer-project evidence modes.
2. Select the entry from `manifests/proof-drill-registry.yaml` by `id`,
   `selector`, or `when_to_run`.
3. Before running anything, report the selected class:
   - `standard-test-lane`: normal validation may run when it matches task scope.
   - `smoke-opt-in`: run only after the operator asked for that smoke.
   - `proof-drill`: run only after explicit proof-drill intent.
   - `manual-proof`: follow the manual evidence ladder and record commands.
4. Check safety fields:
   - `default_lane` must be `false` for `smoke-opt-in`, `proof-drill`, and
     `manual-proof`.
   - `requires_credentials` must be present before provider-backed checks.
   - `cost_class` must be called out when provider, Docker, cloud, VM, or
     Kubernetes resources may be used.
   - `destructive_scope` must be compatible with the current workspace.
5. Prefer account-free and local evidence first. Treat missing credentials as a
   skipped provider proof, not as runtime failure.
6. Run the exact registry command only when it exists and matches the requested
   scope. For consumer projects, prefer `/run-tests` and the project test
   framework unless a COS projection explicitly installs the requested drill.
7. Capture evidence:
   - absolute working directory;
   - command;
   - exit code;
   - artifact paths;
   - credential and cost posture;
   - what the result proves;
   - what remains unproven.
8. If the proof exposes a stale claim, use `/test-contract-repair` to convert the
   claim into a stronger behavioral/manual contract before declaring closure.

## Existing selectors

- `skills/cognitive-os-test/SKILL.md` — normal SO pytest lanes with persisted
  summaries.
- `skills/run-tests/SKILL.md` — consumer-project test selection.
- `skills/smoke-test/SKILL.md` — guided SO smoke selection.
- `scripts/smoke-qwen-fallback.sh` — provider-backed Qwen fallback smoke.
- `scripts/smoke-multi-provider-fallback.sh` — provider-backed fallback smoke.
- `scripts/cos-headless-service-drill` — Docker/headless service proof drill.
- `scripts/cos-engram-cloud-docker-smoke` — Engram Cloud Docker smoke.
- `scripts/cos-cross-instance-drill` — cross-instance evidence transfer drill.

## Output format

```text
PROOF_DRILL_REPORT
id: <registry id>
scope: <os-self|consumer-project|both>
class: <standard-test-lane|smoke-opt-in|proof-drill|manual-proof>
working_directory: <absolute path>
command: <command or manual procedure>
exit_code: <code or SKIPPED>
artifacts: <paths or none>
credential_posture: <none|required-present|required-missing>
cost_posture: <local|provider|docker|cloud|mixed>
proves: <bounded claim>
does_not_prove: <remaining gaps>
next_step: <repair, promote, rerun with credentials, or none>
```

## Contextual Trigger

Load this skill when the task mentions proof drill, smoke opt-in, runtime proof,
headless proof, Docker proof, provider smoke, one-off smoke, manual proof,
consumer-project validation boundary, or tests that must not run with the full
suite by default.

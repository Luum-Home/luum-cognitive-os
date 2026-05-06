# COS Instance Installer Implementation Roadmap

## Purpose

This runbook turns ADR-163 into an executable roadmap. It keeps the current
IDE/CLI workflow intact while adding service/headless modes in proof-gated
phases.

Machine-readable phases: `manifests/cos-instance-implementation-phases.yaml`.

## Product statement

Cognitive OS is not an IDE plugin. It is an agent governance/runtime layer with
multiple frontends:

- IDE harnesses;
- CLI local;
- shell/CI;
- Docker/headless service;
- remote ingress;
- VM/EC2 workers;
- Kubernetes pods.

## Phase roadmap

| Phase | Name | Status | Proof | Summary |
|---|---|---|---|---|
| 1 | Instance init contract | implemented | contract | `cos-instance-init` profiles and metadata writes. |
| 2 | Instance up/doctor/smoke | planned | contract | Operator wrappers for status and smoke without provider calls. |
| 3 | Host CLI bridge security contract | implemented | contract | ADR-164 and manifest define the bridge before runtime. |
| 4 | Host CLI bridge non-provider smoke | planned | bridge-smoke | Run harmless status/version commands through bridge. |
| 5 | Host provider smoke | planned | provider-smoke | Cost/approval-gated Codex/Claude provider execution. |
| 7 | Worktree/branch/PR runtime | planned | pr-smoke | Implement ADR-162 through worktree and PR proposal. |
| 8 | VM/EC2 instance | planned | local-smoke | Single-node service instance. |
| 9 | Kubernetes instance | planned | docker-smoke | Worker pods with readiness/liveness and external credential boundaries. |

## Current acceptance

```bash
python3 -m pytest tests/contracts/test_cos_instance_profiles.py -q
python3 -m pytest tests/contracts/test_cos_instance_implementation_phases.py -q
python3 -m pytest tests/contracts/test_host_cli_bridge_contract.py -q
```

## Next implementation slice

The next code slice should be Phase 2, not provider execution:

```bash
scripts/cos-instance-doctor --profile local --json
scripts/cos-instance-smoke --profile docker-headless --no-provider --json
scripts/cos-instance-up --profile docker-headless --dry-run --json
```

Provider execution remains blocked until Phase 5.

## Promotion checklist

A planned profile or phase can move to implemented only when:

1. docs and manifest status are updated together;
2. at least one automated contract test signs the status;
3. a manual test records the exact commands and evidence;
4. credential-store-copy remains blocked;
5. rollback/disable path is documented;
6. provider calls, if any, are explicit opt-in and human-approved.

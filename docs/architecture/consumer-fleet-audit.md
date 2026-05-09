# Consumer Fleet Audit

Cognitive OS has the primitives to answer whether downstream projects are
installed, current, and producing trustworthy evidence, but those primitives are
separate unless the fleet audit joins them.

The canonical read-only entry point is:

```bash
scripts/cos-consumer-fleet-audit --json
```

For a human summary:

```bash
scripts/cos-consumer-fleet-audit
```

## What the audit joins

| Question | Existing evidence source | Fleet-audit field |
|---|---|---|
| Which projects are registered for this SO source? | `~/.cognitive-os/installations.json` | `projects[]`, `summary.matching_source` |
| Does each project still exist? | registered path on disk | `projects[].exists` |
| Does each project expose install metadata? | `.cognitive-os/install-meta.json` | `projects[].install_meta_exists` |
| Is the project on the current SO source version? | source `git describe` / `VERSION`, registry, install metadata | `projects[].effective_version`, `version-drift` finding |
| Which harness was installed? | install metadata | `projects[].harness` |
| Are primitive and skill locks current? | `scripts/cos-registry-lock --audit` | `registry_lock_audit` |
| Is the external-help product claim signed? | `scripts/cos-claim-signature-audit` | `claim_signature_audit.helps_projects_signed` |
| Which validation lanes should run before trusting auto-update changes? | documented targeted lanes | `required_test_lanes[]` |

## Current boundaries

The audit is intentionally **read-only**. It does not:

- mutate consumer projects;
- run project-specific tests inside consumer repositories;
- import consumer evidence into product claims;
- promote consumer improvement proposals into core primitives;
- run `scripts/auto-update-projects.sh` automatically.

Use it as the first diagnostic panel before running auto-update, importing
consumer evidence, or claiming that a release propagated safely.

## Related commands

```bash
bash scripts/auto-update-projects.sh --list
bash scripts/auto-update-projects.sh --dry-run
scripts/cos-registry-lock --audit
scripts/cos-claim-signature-audit --json
scripts/cos-export-consumer-evidence --help
scripts/cos-import-consumer-evidence --help
scripts/cos-export-consumer-improvement-proposals --help
scripts/cos-import-consumer-improvement-proposals --help
```

## Validation lanes

The fleet audit reports these lanes rather than running them:

```bash
python3 -m pytest tests/behavior/test_auto_update.py tests/integration/test_auto_update_safety.py -q
python3 -m pytest tests/behavior/test_consumer_project_projection.py -q
python3 -m pytest tests/unit/test_consumer_improvement_proposals.py tests/unit/test_cross_stack_adoption_truth.py tests/behavior/test_cross_stack_adoption_truth_cli.py -q
```

These lanes cover the updater, symlink/namespacing safety, downstream projection,
consumer improvement proposals, and adoption-truth substrate. They are still not
a substitute for stack-specific consumer tests.

## Status interpretation

| Status | Meaning |
|---|---|
| `pass` | Registered projects exist, install metadata is coherent, lock audit passes, and no blocking fleet finding exists. Informational unsigned-claim findings may still appear. |
| `warn` | A project is stale, install metadata is incomplete, the registry itself needs operator attention, or claim-signature audit reports a warning such as maturity-loop evidence debt. |
| `fail` | A registered project path is missing or the primitive/skill lock audit fails. |

The `helps-projects` claim remains unsigned until
`manifests/external-adoption-evidence.yaml` contains qualifying non-maintainer
external evidence. Self-owned dogfood reports are useful operational evidence,
but they do not sign the external-help claim.

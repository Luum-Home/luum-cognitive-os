---
adr: 333
title: Publication Safety Primitive
status: accepted
implementation_status: implemented
date: '2026-05-31'
supersedes: []
superseded_by: null
implementation_files:
  - lib/publication_safety.py
  - scripts/cos-publication-safety
  - hooks/publication-safety.sh
  - manifests/publication-safety.yaml
  - docs/04-Concepts/architecture/publication-safety-receipt-v0.md
tier: maintainer
tags: [publication, safety, consumer-gates, receipts]
classification_basis: implemented portable runner, hook bridge, receipt contract, and tests
---

# ADR-333: Publication Safety Primitive

## Status

Accepted — implemented on 2026-05-31.

## Context

A downstream Luum repository already has strong publication gates for raw secret scanning, private-content classification, public documentation boundaries, repository references, Git history publication safety, environment templates, language governance, trademark claims, and aggregate pre-publication receipts.

Cognitive OS had adjacent primitives for secrets, private-content portability, public claims, release guarding, and protected publication, but no single primitive that lets a consumer repository declare its own publication gates and receive a normalized Cognitive OS receipt.

Hardcoding the downstream gates into Cognitive OS would violate the OS portability boundary. The correct adoption path is a configurable bridge.

## Decision

Add a portable `publication-safety` primitive:

1. Consumer repositories declare commands in `manifests/publication-safety.yaml` using `publication-safety-config/v0`.
2. Cognitive OS runs those commands through `lib/publication_safety.py` without `shell=True`.
3. The CLI `scripts/cos-publication-safety` emits `publication-safety-receipt/v0` at `.cognitive-os/receipts/publication-safety/summary.json` by default.
4. `hooks/publication-safety.sh` no-ops unless the consumer has enabled a config or explicitly sets `COS_PUBLICATION_SAFETY_REQUIRED=1`.
5. The hook blocks high-risk publication commands when required configured gates fail.
6. Raw stdout/stderr are represented by hashes and byte counts by default; raw logs require explicit `--write-step-logs`.

The primitive is a runner and normalizer, not a scanner. Repository-specific publication policy stays in the consumer repo.

## Alternatives rejected

- Hardcoding downstream Luum publication gates into Cognitive OS: rejected because it would violate the OS portability boundary and leak consumer-specific policy into core.
- Replacing existing scanners with a COS scanner: rejected because this primitive normalizes receipts while consumer repositories retain their own scanners and allowlists.
- Always-on blocking with no config: rejected because consumers need graceful no-op behavior until they opt into publication safety enforcement.

## Consequences

- Cognitive OS can enforce publication safety claims across consumer repositories without learning their private gate internals.
- Mature downstream gates can be adopted as configuration rather than copied into core.
- Receipts become comparable across projects even when the underlying commands differ.
- Consumer projects still own their allowlists, env templates, i18n policy, history decisions, and scanner configuration.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. No Cognitive OS code hardcodes luum-agent-harness paths or Luum-specific gate names.
2. A temp consumer config with passing commands produces publication-safety-receipt/v0 status=pass.
3. A required failing command produces status=fail and CLI exit 2.
4. An optional failing command produces status=warn and strict CLI exit 2.
5. Command stdout/stderr are hashed by default and raw step logs are opt-in.
6. The hook no-ops when no config is present and blocks when COS_PUBLICATION_SAFETY_REQUIRED=1 plus a failing config.
7. `cos publication safety` routes through the dispatcher.
```

## Verification

```bash
python3 -m pytest tests/unit/test_publication_safety.py tests/behavior/test_publication_safety_cli.py tests/contracts/test_publication_safety_contract.py -q
bash -n hooks/publication-safety.sh
python3 -m py_compile lib/publication_safety.py scripts/cos-publication-safety
scripts/cos publication safety --allow-missing-config --json
```

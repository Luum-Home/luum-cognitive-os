# Cross-Instance Learning Runway

Cross-instance learning is the path from a single-maintainer solo swarm to a
multi-machine, multi-maintainer learning system.

The runway deliberately avoids full federation until ADR-132 Shape-B triggers
fire.

## Shape A vs Shape B

| Shape | Meaning | Current action |
|---|---|---|
| Shape A | one maintainer, 1–2 machines, one authority | portable evidence and locks |
| Shape B | 2+ maintainers, 3+ machines, remote agents, fragmented memory | federation design becomes justified |

## Primitive 1 — Consumer evidence exchange

Export from a consumer project:

```bash
scripts/cos-export-consumer-evidence \
  --project example-consumer \
  --reporter "external-user" \
  --profile core \
  --duration-days 30 \
  --cos-version 0.23.0 \
  --cognitive-cost "low after onboarding" \
  --output /tmp/example-consumer-cos-evidence.json
```

Import upstream:

```bash
scripts/cos-import-consumer-evidence /tmp/example-consumer-cos-evidence.json
```

The import updates:

```text
manifests/external-adoption-evidence.yaml
```

This is the first step toward signing the “helps projects” claim.

## Primitive 2 — Registry lock

Generate deterministic primitive and skill locks:

```bash
scripts/cos-registry-lock --write
```

Audit drift:

```bash
scripts/cos-registry-lock --audit
```

Lock files:

```text
manifests/agentic-primitive-registry.lock.yaml
skills/REGISTRY.lock
```

This lets two machines detect that they are not operating with the same
primitive/skill catalog.

## Primitive 3 — Engram portable bundle

Export:

```bash
scripts/cos-engram-bundle --project example-project
```

Propose import:

```bash
scripts/cos-engram-import-propose .cognitive-os/engram-bundles/<bundle>.json
```

Import proposals are written under:

```text
.cognitive-os/engram-import-proposals/
```

No memory store is mutated. Conflicts are explicit by `topic_key`.

## Primitive 4 — Federation trigger audit

```bash
scripts/cos-federation-trigger-audit
```

Reads:

```text
manifests/federation-triggers.yaml
```

Current expected state:

```text
status: deferred
shape: Shape A
```

If Shape-B triggers fire, the next ADR should design distributed locks,
federated memory, code-owner/quorum rules, and cross-machine runtime marker
handling.

## Safety boundary

The runway does not:

- auto-merge external evidence into claims;
- auto-import Engram observations;
- run consensus;
- introduce Redis/Valkey locks;
- make maintainer tier externally adoptable.

It only makes the future federation problem measurable and reversible.

## Manual drills

Use `scripts/cos-cross-instance-drill` to deliberately provoke the runway states
without mutating real product evidence.

```bash
scripts/cos-cross-instance-drill --scenario external-evidence
scripts/cos-cross-instance-drill --scenario shape-b-trigger
scripts/cos-cross-instance-drill --scenario registry-drift
scripts/cos-cross-instance-drill --scenario engram-conflict
scripts/cos-cross-instance-drill --scenario shape-b-governance
scripts/cos-cross-instance-drill --scenario all
```

The drills use temporary manifests, temporary lock files, temporary Engram
bundles, and temporary governance checklists. They prove that the machinery can
flip states when the inputs are present, but they do **not** sign real claims.

| Scenario | What it proves | Real state mutated |
|---|---|---|
| `external-evidence` | a qualifying non-maintainer report signs `helps-projects` in a temp manifest | no |
| `shape-b-trigger` | Shape-B trigger audit flips from deferred to triggered with threshold inputs | no |
| `registry-drift` | registry lock audit detects skill/primitive drift | no |
| `engram-conflict` | topic-key conflict becomes an import proposal | no |
| `shape-b-governance` | multi-maintainer governance checklist can be generated for review | no |

The distinction matters:

- **Drill pass** means the runway works.
- **Claim signed** still requires real external evidence or real Shape-B
  operation.

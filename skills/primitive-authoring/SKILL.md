<!-- SCOPE: both -->
---
name: primitive-authoring
description: Governed workflow for creating, modifying, or promoting Cognitive OS agentic primitives in the SO or in consumer projects. Use when building a new skill/rule/hook/script/workflow, converting a repeated conversation into a primitive, deciding whether a primitive belongs in the OS or a project overlay, or assessing ADR-256 projection/runtime/consumer/service impact.
version: 0.1.0
audience: both
tags: [primitives, governance, portability, authoring, projection, observability]
user-invocable: true
routing_patterns:
  - pattern: '\bprimitive[- ]?authoring\b'
    confidence: 0.96
  - pattern: '\b(create|build|add|author|promote|modify)\s+(a\s+)?(new\s+)?(agentic\s+)?primitive\b'
    confidence: 0.92
  - pattern: '\b(nueva?|crear|construir|agregar|promover)\s+(una?\s+)?primitiva\b'
    confidence: 0.90
---

# Primitive Authoring

Use this skill before creating or changing any agentic primitive: skill, rule,
hook, script, workflow, template, manifest, doctor, or project-local primitive.

> No new primitive without reuse check, ownership boundary, portable contract,
> projection-fidelity claim, runtime-evidence plan, consumer-fleet impact check,
> and service/headless impact check.

## 1. Reuse check

Classify the request first:

- `USE_EXISTING`
- `IMPROVE_EXISTING`
- `DOCUMENT_ONLY`
- `CREATE_PRIMITIVE`
- `DISCARD`

Search existing surfaces before writing files:

```bash
rg -n "candidate terms" skills rules hooks scripts docs/architecture docs/adrs manifests -S
```

Use `scripts/cos_primitive_harvester.py` when the input is a conversation excerpt.

## 2. Ownership boundary

Choose one:

- `os-core`
- `os-maintainer`
- `package-or-extension`
- `consumer-project`
- `documentation-only`

Project-specific policy/config belongs in the consumer overlay, not hardcoded into
COS. Reusable behavior can move into COS with project-specific configuration kept
outside the core primitive.

## 3. Contract stub

Before implementation, write a primitive contract stub. If
`manifests/primitive-contracts.yaml` exists, use it. Otherwise include the stub in
ADR/plan/PR notes.

Required fields:

```yaml
id: kebab-case-id
family: skill|rule|hook|script|workflow|template|manifest|doctor
source: path/to/source
intent: One sentence.
trigger:
  kind: user_request|before_tool_call|after_tool_call|session_start|session_end|manual|ci|service_event
requires: []
actions:
  preferred: block|warn|advise|suggest|observe|allow|execute
  fallback: warn|documented-only|none
evidence:
  metrics: []
  proof_tests: []
projection:
  claude: {fidelity: native-lifecycle-enforced|structural-advisory|documented-only|unsupported}
  codex: {fidelity: native-lifecycle-enforced|governed-wrapper-enforced|structural-advisory|documented-only|unsupported}
  shell-ci: {fidelity: ci-enforced|documented-only|unsupported}
  cosd-service: {fidelity: service-enforced|documented-only|unsupported}
impact:
  consumer_fleet: none|install-update-risk|projection-risk|unknown
  service_mode: harness-embedded-only|shell-ci-safe|headless-worker-safe|cosd-service-safe|unsupported
```

## 4. Projection fidelity

Do not claim stronger fidelity than the harness/service can prove.

- IDE structural files are usually `structural-advisory`.
- Native lifecycle hooks may be `native-lifecycle-enforced` only when the host emits the needed event.
- CLI/CI primitives are `ci-enforced` only when the lane runs.
- `cosd`/headless primitives are `service-enforced` only when service boundaries and readiness gates support them.

## 5. Consumer-fleet impact

If the primitive changes install, update, projection, generated settings, default
profiles, or consumer-visible files, run or plan:

```bash
scripts/cos-consumer-fleet-audit --json
```

Use its `required_test_lanes[]` in validation when relevant. If registered
projects are stale or missing install metadata, do not assume the primitive
reaches them.

## 6. Service/headless impact

A primitive may affect COS outside IDEs. Classify the runtime shape:

| Shape | Required thinking |
|---|---|
| Harness embedded | IDE lifecycle/projection fidelity. |
| Shell/CI | Works without IDE env or hooks. |
| Headless worker | Works in Docker/headless proof lane. |
| `cosd` service | Respects daemon API, queue, auth, provider, and protected-write boundaries. |

For service/headless claims, run or plan:

```bash
scripts/cos-service-readiness-gate --json
```

Do not assume IDE hooks fire in service mode. Do not expose provider calls,
credentials, destructive actions, or raw shell through `cosd` without an ADR and
readiness proof.

## 7. Evidence plan

Risk determines proof:

| Risk | Proof |
|---|---|
| docs-only | link/check acceptance criteria |
| skill/rule advisory | frontmatter/registry test + realistic fixture |
| script/report | unit/schema + CLI smoke |
| advisory hook | behavior test + latency consideration |
| blocking/mutating hook | false-positive tests + repair/bypass path + metric row |
| consumer projection | temp consumer project projection + fleet-audit consideration |
| service/headless | service-readiness gate + headless/service proof lane |

If ADR-256 ledgers exist, plan `primitive-interventions.jsonl`,
`codebase-itinerary.jsonl`, and trace joiner integration as needed.

## 8. Implement narrowly

After this gate, use the family-specific primitive:

- `skills/add-skill/SKILL.md`
- `skills/add-rule/SKILL.md`
- `skills/add-hook/SKILL.md`
- ADR tooling for docs decisions

Keep first slices small; do not migrate the world.

## Acceptance criteria template

```text
ACCEPTANCE CRITERIA:
1. Reuse check recorded.
2. Ownership boundary declared.
3. Contract stub exists.
4. Harness/runtime fidelity does not exceed evidence.
5. Consumer-fleet impact considered when downstream projects may be affected.
6. Service/headless impact considered when COS can run outside IDE lifecycle.
7. Tests/proof match risk class.
8. Runtime evidence plan exists, or documented-only rationale exists.
```

## Stop conditions

Stop for design review if the primitive:

- is default-on or blocking;
- touches secrets, credentials, private content, destructive Git, deletion, or remote service boundaries;
- changes consumer projection/update/install behavior;
- changes service/headless/cosd behavior or public service claims;
- duplicates an existing primitive;
- requires a harness capability not present in capability manifests.

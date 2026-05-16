---
name: primitive-authoring
description: 'Use when building a new skill/rule/hook/script/workflow, converting
  a repeated conversation into a primitive, deciding whether a primitive belongs in
  the OS or a project overlay, or assessing ADR-256/ADR-258 projection/runtime/consumer/service
  impact. Purpose: Governed workflow for creating, modifying, or promoting Cognitive
  OS agentic primitives in the SO or in consumer projects.'
version: 0.2.0
audience: both
tags:
- primitives
- governance
- portability
- authoring
- projection
- observability
- portable-ai
user-invocable: true
platforms:
- claude
- codex
- opencode
- cursor
- vscode-copilot
- shell-ci
routing_patterns:
- pattern: \bprimitive[- ]?authoring\b
  confidence: 0.96
- pattern: \b(create|build|add|author|promote|modify)\s+(a\s+)?(new\s+)?(agentic\s+)?primitive\b
  confidence: 0.92
- pattern: /primitive-authoring\b
  confidence: 0.96
routing_intents:
- intent: agentic_primitive_authoring
  description: User wants to create, modify, promote, or assess an agentic primitive
    such as a skill, rule, hook, script, or reusable workflow.
  confidence: 0.9
triggers:
- primitive-authoring
- /primitive-authoring
- Primitive Authoring
- Use when building a new skill/rule/hook/script/workflow, converting a repeated conversation
  into a primitive, deciding w
---
<!-- SCOPE: both -->
# Primitive Authoring

Use this skill before creating or changing any agentic primitive: skill, rule,
hook, script, workflow, template, manifest, doctor, or project-local primitive.

> No new primitive without reuse check, ownership boundary, portable contract,
> projection-fidelity claim, runtime-evidence plan, consumer-fleet impact check,
> service/headless impact check, and generated `.ai` overlay proof when the
> primitive is consumer-visible.

## 0. Standards boundary

Cognitive OS uses these standards and near-standards deliberately:

- `AGENTS.md` is a strong cross-agent instruction surface.
- `SKILL.md` / Agent Skills are a strong skill packaging surface.
- `.ai` / VERSA / dotAIslash is a candidate consumer overlay surface, not the
  canonical source of truth for COS internals.
- MCP, ACP, and A2A are related protocols/transports, but they are not equivalent to a portable primitive contract.
- OpenCode permissions/plugins can become an adapter runtime surface only after
  a native smoke proves enforcement and ledger receipt.

Invariant: **COS canonical internal registry != consumer .ai overlay**. The
canonical primitive remains in COS source (`skills/`, `rules/`, `hooks/`,
`scripts/`, `manifests/primitive-contracts.yaml`). The `.ai/` tree is generated
packaging for consumers and IDE adapters; do not hand-edit it as canonical state.

## 1. Reuse check

Classify the request first:

- `USE_EXISTING`
- `IMPROVE_EXISTING`
- `DOCUMENT_ONLY`
- `CREATE_PRIMITIVE`
- `DISCARD`

Search existing surfaces before writing files:

```bash
rg -n "candidate terms" skills rules hooks scripts docs/04-Concepts/architecture docs/02-Decisions/adrs manifests -S
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
`manifests/primitive-contracts.yaml` exists, use it for governed primitives. If a
primitive is not ready for registry promotion, document why it is only
`primitive-lifecycle-derived` in the generated overlay and what evidence is
missing before it can claim registry governance.

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
portable_contract:
  source: primitive-contract-registry|primitive-lifecycle-derived
  warning: null|"Must be promoted into manifests/primitive-contracts.yaml before claiming full contract-registry governance."
projection:
  claude: {fidelity: native-lifecycle-enforced|structural-advisory|documented-only|unsupported}
  codex: {fidelity: native-lifecycle-enforced|governed-wrapper-enforced|structural-advisory|documented-only|unsupported}
  cursor: {fidelity: structural-advisory|documented-only|unsupported}
  vscode-copilot: {fidelity: structural-advisory|documented-only|unsupported}
  opencode: {fidelity: host-plugin-lifecycle-capable|structural-advisory|documented-only|unsupported}
  shell-ci: {fidelity: ci-enforced|documented-only|unsupported}
  cosd-service: {fidelity: service-enforced|documented-only|unsupported}
impact:
  consumer_fleet: none|install-update-risk|projection-risk|unknown
  service_mode: harness-embedded-only|shell-ci-safe|headless-worker-safe|cosd-service-safe|unsupported
```


## 3b. Language-agnostic routing metadata

When the primitive is a skill or any user-routed primitive, follow ADR-302:

- Keep `routing_patterns` only for deterministic aliases: slash commands,
  primitive IDs, URLs, paths, file extensions, config keys, or other machine
  shapes.
- Do not add keyword regexes for natural-language intent detection.
- Add `summary_line`: one short routing-oriented sentence.
- Add `routing_intents`: semantic descriptions of what the user is asking for.
- If broader language coverage is needed, use ADR-299 enrichment as corpus data,
  not as hard routing logic:

```bash
scripts/cos-skill-description-enrich --dry-run --skills {skill-name} --languages en,es,pt,de,fr,it --intents-per-lang 2
scripts/cos-routing-benchmark --quick
scripts/cos-language-dependence-audit --output .cognitive-os/reports/language-dependence-audit.md
```

For SO primitives, semantic metadata belongs in canonical COS source. For
consumer-project primitives, project-specific vocabulary belongs in the project
overlay/config; do not hardcode downstream product/team language into OS-level
regex.

## 3c. SCOPE both portability proof scaffold

When an artifact declares `SCOPE: both`, create its paired red-team proof from
the same canonical path logic used by `scripts/cos-scope-both-portability-audit`:

```bash
scripts/cos-portability-proof-scaffold --artifact hooks/{hook-name}.sh
scripts/cos-portability-proof-scaffold --artifact scripts/{script-name}.py
scripts/cos-portability-proof-scaffold --artifact skills/{skill-name}/SKILL.md
```

Then replace the generated baseline with a primitive-specific falsification
probe. Do not invent a different filename; the scope gate and audit both use
`lib/portability_proof_paths.py` for their suggested path logic.

Before commit, run the automatic source-level contract checks:

```bash
scripts/cos-scope-both-portability-audit --strict --no-write
scripts/cos-scope-projection-audit --strict --no-write
```

For any primitive that can be projected or installed into a consumer project, run
the runtime projection smoke as the authoritative check:

```bash
scripts/cos-scope-projection-audit --run-install-smoke --strict --no-write
scripts/cos-install-projection-audit --json
scripts/cos status --portability
```

`scripts/cos-install-projection-audit` is the hard install guard: it creates
filtered Codex and Claude fixture installs and proves every generated hook
registration points to a hook file actually copied by that same install scope
and mode. Do not treat a SCOPE classifier pass as enough for install safety.

## 4. Projection fidelity

Do not claim stronger fidelity than the harness/service can prove.

- IDE structural files are usually `structural-advisory`.
- Native lifecycle hooks may be `native-lifecycle-enforced` only when the host emits the needed event.
- CLI/CI primitives are `ci-enforced` only when the lane runs.
- `cosd`/headless primitives are `service-enforced` only when service boundaries and readiness gates support them.
- OpenCode is only `host-plugin-lifecycle-capable` until a real OpenCode permissions/plugin smoke proves runtime enforcement and an intervention ledger row.

## 5. Consumer overlay and adapter proof

When the primitive is visible to consumers or IDE adapters, regenerate/check the
portable overlay after changing the canonical source:

```bash
scripts/cos-portable-ai-overlay --check
scripts/cos-adapters verify --json
```

Required checks:

- every generated `.ai/primitives/**/*.json` row has `portable_contract`;
- registry-backed primitives report `portable_contract.source = primitive-contract-registry`;
- lifecycle-only primitives report `portable_contract.source = primitive-lifecycle-derived` and do not claim full governance;
- adapter manifests describe projection honestly without inventing knowledge;
- `.ai/context.json` keeps the generated-overlay warning.

Do not move canonical primitives physically into `.ai/` unless a future ADR
explicitly changes the architecture and migration plan.

## 6. Consumer-fleet impact

If the primitive changes install, update, projection, generated settings, default
profiles, or consumer-visible files, run or plan:

```bash
scripts/cos-install-projection-audit --json
scripts/cos-consumer-fleet-audit --json
```

Use its `required_test_lanes[]` in validation when relevant. If registered
projects are stale or missing install metadata, do not assume the primitive
reaches them.

## 7. Service/headless impact

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

## 8. Observable self-use and evidence plan

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

If ADR-256 ledgers apply, plan `primitive-interventions.jsonl`,
`codebase-itinerary.jsonl`, and trace joiner integration. For runtime-relevant
changes, prove observable self-use with:

```bash
scripts/cos-observe-primitives --json
```

A primitive is not observably used merely because it exists in docs. It needs an
inspection/action/evidence path appropriate to its risk class.

## 9. Implement narrowly

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
3. Contract stub exists, or lifecycle-derived rationale is explicit.
4. Harness/runtime fidelity does not exceed evidence.
5. Generated .ai overlay is current when the primitive is consumer-visible.
6. Adapter manifests verify when projection behavior changes.
7. Consumer-fleet impact considered when downstream projects may be affected.
8. Service/headless impact considered when COS can run outside IDE lifecycle.
9. Tests/proof match risk class.
10. Every `SCOPE: both` artifact has its scaffolded paired proof path, then a real falsification probe.
11. `scripts/cos-scope-both-portability-audit --strict --no-write` passes.
12. `scripts/cos-scope-projection-audit --strict --no-write` passes.
13. Consumer-visible primitives pass `scripts/cos-scope-projection-audit --run-install-smoke --strict --no-write`.
14. Runtime evidence plan exists, or documented-only rationale exists.
```

## Stop conditions

Stop for design review if the primitive:

- is default-on or blocking;
- touches secrets, credentials, private content, destructive Git, deletion, or remote service boundaries;
- changes consumer projection/update/install behavior;
- changes service/headless/cosd behavior or public service claims;
- duplicates an existing primitive;
- requires a harness capability not present in capability manifests;
- would require hand-editing generated `.ai/` files as canonical source.

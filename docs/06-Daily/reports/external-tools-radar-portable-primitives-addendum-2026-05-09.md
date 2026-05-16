---
report_type: external-tools-radar-addendum
subject: portable-primitive-standards-and-adapter-runtime-tools
generated_at: 2026-05-09
status: assess-trial-patterns
related_docs:
  - docs/06-Daily/reports/portable-ai-primitive-standards-due-diligence-2026-05-09.md
  - docs/02-Decisions/adrs/ADR-258-portable-ai-overlay-for-agentic-primitives.md
  - docs/04-Concepts/architecture/ide-agnostic-primitive-projection.md
  - docs/04-Concepts/root/ide-compatibility.md
  - manifests/external-tools-adoption.yaml
---

# External Tools Radar Portable Primitive Addendum — 2026-05-09

## Decision

Add five missing or under-connected tool/spec families to the Cognitive OS tech
radar for the portable primitive program:

<!-- english-only-content-audit: allow -->
1. **VERSA / dotAIslash** — `ASSESS / trial-overlay-standard`.
2. **Agent Skills ecosystem** — `ASSESS / conformance-reference`.
3. **Zed Agent Client Protocol (ACP)** — `ASSESS / adapter-runtime-transport`.
4. **OpenCode permissions/plugins** — `TRIAL / adapter-design`.
5. **Open Agent Passport / pre-action authorization** — `MONITOR / ledger-hardening-pattern`.

These are not default dependencies. They are radar entries and implementation
constraints for ADR-258, ADR-256, and future adapter/runtime evidence work.

## Why these were missing from the previous implementation

The ADR-256/257 work was based on internal docs, existing ADRs, the practice
repo `.ai` layout, OpenSage comparison, and existing tech-radar context. It did
not originally include a dedicated 40+ source external due-diligence pass focused
on `.ai`/portable primitive specs. ADR-258 and this addendum close that gap.

## Tool/spec decisions

### 1. VERSA / dotAIslash

| Field | Value |
|---|---|
| Radar status | `ASSESS` |
| Adoption kind | `trial-overlay-standard` |
| License posture | MIT reported on landing page; still treat as spec/reference, not dependency |
| COS use | Shape and validate the generated `.ai/` overlay |
| Blocked use | Do not make `.ai/` canonical source until conformance and consumer proof mature |

VERSA directly matches the packaging question: a vendor-neutral `.ai/` folder for
repo context, profiles, rules, agents, tools, permissions, validation, and
conformance. COS should track it because it can influence the consumer overlay
shape. COS should not outsource primitive truth to VERSA yet; the source of truth
remains `manifests/primitive-contracts.yaml`, `manifests/primitive-lifecycle.yaml`,
`hooks/`, `skills/`, `rules/`, and `scripts/`.

Implementation impact:

- Keep `scripts/portable_ai_overlay.py` as the generator.
- Add future optional `versa lint` compatibility only behind a graceful optional gate.
- Do not require VERSA packages in default bootstrap.

### 2. Agent Skills ecosystem / mdskills / Trigger.dev Skills

| Field | Value |
|---|---|
| Radar status | `ASSESS` |
| Adoption kind | `conformance-reference` |
| License posture | Mixed per skill/package; license gate required before importing anything |
| COS use | Validate `SKILL.md` metadata, progressive disclosure, install/discovery expectations |
| Blocked use | Do not bulk-import marketplace skills or generated skills without `primitive-authoring` |

COS already uses `SKILL.md`. The missing action is not format adoption; it is
contract alignment. Agent Skills references should be used to ratchet COS skill
frontmatter, trigger semantics, bundled-resource rules, and license/credential
review before any skill is promoted into a primitive contract.

Implementation impact:

- Future contract tests should compare COS `skills/*/SKILL.md` against the
  Agent Skills contract subset COS claims.
- `primitive-authoring` remains mandatory for new skills, marketplace imports,
  generated skills, and dynamic skill synthesis.
- Marketplace references are metadata only until license, credential, and sandbox
  gates pass.

### 3. Zed ACP

| Field | Value |
|---|---|
| Radar status | `ASSESS` |
| Adoption kind | `adapter-runtime-transport` |
| License posture | Protocol/reference assessment; no runtime dependency adopted |
| COS use | Evaluate as transport boundary for editor/agent adapter runtime |
| Blocked use | Do not model ACP as a primitive registry or policy engine |

ACP is relevant because it separates editor clients from agent servers. That is
useful for future COS service/headless mode and IDE adapters, but it does not
replace primitive contracts, permission policy, or runtime evidence ledgers.

Implementation impact:

- Connect ACP to the adapter runtime roadmap, not to `.ai` canonicalization.
- Use ACP as a possible transport for service-mode adapters after ADR-256 ledger
  and ADR-258 overlay conformance are stable.
- Require runtime receipts before claiming ACP-backed enforcement.

### 4. OpenCode permissions/plugins

| Field | Value |
|---|---|
| Radar status | `TRIAL` |
| Adoption kind | `adapter-design` |
| License posture | Reference native host surfaces; no bundled dependency |
| COS use | Design native OpenCode adapter around permissions and plugin lifecycle |
| Blocked use | Do not invent a parallel COS-only OpenCode enforcement layer |

OpenCode is the strongest immediate candidate for runtime adapter proof beyond
Claude/Codex because it exposes host-native permission and plugin surfaces. COS
should map contract-required capabilities to OpenCode permissions/plugins and
emit `primitive-interventions.jsonl` from native plugin events when possible.

Implementation impact:

- Add an OpenCode adapter design before marking any OpenCode primitive as
  runtime-enforced.
- Keep current `host-plugin-lifecycle-capable` fidelity until a signed smoke test
  proves `tool.execute.before`/equivalent enforcement and ledger emission.
- OpenCode adapter rows in `.ai/profiles/opencode.json` must remain non-enforced
  unless runtime receipts exist.

### 5. Open Agent Passport / pre-action authorization

| Field | Value |
|---|---|
| Radar status | `MONITOR` |
| Adoption kind | `ledger-hardening-pattern` |
| License posture | Research/protocol monitor; no implementation adopted |
| COS use | Inform future deterministic pre-tool-call authorization and signed receipts |
| Blocked use | Do not add dependency or claim OAP compatibility without a separate audit |

Pre-action authorization is directly relevant to the primitive intervention
ledger. It gives a future direction for turning `primitive-interventions.jsonl`
from an internal observation ledger into a signed, deterministic authorization
receipt stream. The idea is promising but must stay research-only until COS runs
a dedicated security and privacy audit.

Implementation impact:

- Extend ADR-256 future phases with optional authorization-receipt hardening.
- Preserve current privacy rule: no raw commands, paths, file contents, or secrets
  in intervention or itinerary ledgers.
- Keep OAP/APort/OpenLeash/Veto references as patterns, not dependencies.

## Radar summary

| Tool/spec family | Verdict | COS action | Dependency? |
|---|---|---|---|
| VERSA / dotAIslash | ASSESS | Track `.ai` schema/conformance and map to generated overlay | No |
| Agent Skills / mdskills / Trigger.dev Skills | ASSESS | Ratchet `SKILL.md` contract and promotion gates | No |
| Zed ACP | ASSESS | Evaluate adapter runtime transport for service/headless IDE boundary | No |
| OpenCode permissions/plugins | TRIAL | Produce native adapter design and smoke before enforcement claims | No |
| Open Agent Passport / pre-action authorization | MONITOR | Study signed pre-tool authorization receipts for ledger hardening | No |

## Next actions

1. Add these entries to `manifests/external-tools-adoption.yaml` as
   pattern/spec-only rows.
2. Add this addendum to `docs/06-Daily/reports/external-tools-radar-INDEX.md`.
3. Link from `docs/04-Concepts/patterns/ecosystem-tools.md` under EVALUATE/TRIAL/MONITOR.
4. Keep ADR-258 `.ai` generation non-canonical until VERSA-style conformance is
   tested against COS consumer projects.
5. Draft a dedicated OpenCode adapter design before changing OpenCode fidelity
   from `host-plugin-lifecycle-capable` to enforced.

## Source links

- [VERSA / dotAIslash](https://dotaislash.github.io/)
- [mdskills.ai docs](https://www.mdskills.ai/docs)
- [Trigger.dev Skills](https://trigger.dev/docs/07-Capabilities/skills)
- [Zed ACP](https://zed.dev/acp)
- [OpenCode permissions](https://opencode.ai/docs/permissions/)
- [OpenCode plugins](https://dev.opencode.ai/docs/plugins/)
- [Open Agent Passport paper](https://arxiv.org/abs/2603.20953)
- [APort explainer](https://aport.io/blog/what-is-aport-pre-action-authorization-ai-agents/)

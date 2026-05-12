---
report_type: architecture-gap-investigation
scope: primitive-contract-author-once-cross-ide-projection
reviewed_at: 2026-05-09
status: phase-1-implemented-runtime-ledgers-pending
---

# Primitive Contract / Cross-IDE Premise Investigation — 2026-05-09

## Question

Does Cognitive OS already satisfy the premise:

```text
create all agentic primitives in one IDE-agnostic place
  -> let COS primitives/scripts/tools adapt them to all listed IDEs/harnesses
  -> preserve honest fidelity and runtime evidence per harness
```

## Verdict

**No, not completely.** At initial review, the premise was repeatedly contemplated and partially
implemented, but it was not yet true as an end-to-end architecture. ADR-257 has
since implemented the minimal contract registry slice; runtime ledgers and
contract-driven projection remain pending.

The documentation and ADR line already establish the direction:

```text
canonical behavior
  -> harness-specific projection
  -> proof/fidelity boundaries
  -> observable evidence
```

But the implementation is still split across several older surfaces:

- primitive files: `skills/`, `rules/`, `hooks/`, `scripts/`;
- lifecycle metadata: `manifests/primitive-lifecycle.yaml`;
- active/index/readiness ledgers;
- harness projection manifests;
- `scripts/cos_init.py` projection logic;
- ACC reports and primitive harness coverage;
- runtime metrics and trace joiner.

At initial review, the missing root object was ADR-256 Phase 1:

```text
manifests/primitive-contracts.yaml
```

ADR-257 has since created that file for the first five primitives. No projection
engine consumes the contract rows yet to generate per-harness adapter output.

## Existing decisions that already contemplated the premise

| ADR / doc | What it already covers | Gap relative to the premise |
|---|---|---|
| ADR-021 Vendor-Agnostic State with Provider Adapters | COS-owned canonical state plus thin provider adapters. | State/UI adapter pattern, not primitive contract projection. |
| ADR-057 Cross-Harness Authoring and Driver Projection | Explicitly says author behavior once and project through harness drivers. | Conceptual contract only; no per-primitive machine contract registry. |
| ADR-064 Harness-Agnostic Cognitive OS | Defines harness abstraction surfaces: event capture, hook registration, skill invocation, sub-agent spawning. | Focuses on harness event/settings plumbing, not one contract per primitive. |
| ADR-081 Codex Harness Adapter | Makes Codex a second canonical harness and moves from Claude-only to adapter-backed canonical events/settings. | Codex slice only; does not generalize every primitive into a portable contract row. |
| ADR-126 Agentic Primitive Lifecycle Governor | Requires lifecycle state, supported harnesses, projection targets, runtime projection, metrics, evidence. | Lifecycle metadata is close, but it lacks capability requirements, per-harness fidelity, action schema, and intervention evidence mapping. |
| ADR-127 Active Primitive Index | Derives operator-facing active surface from lifecycle metadata. | Index/readability layer; not adapter generation. |
| ADR-144 Hook-Enforced Rule Projection Contract | Requires hook-enforced rule exclusions to be represented in canonical projection registries. | Rule/hook wiring safety, not all primitive families and IDE adapters. |
| ADR-146 Primitive Readiness Ledger | Classifies scripts/hooks/skills/rules and consumer accessibility. | Readiness/triage, not authoritative primitive contract. |
| ADR-147 ACC Pipeline | Orchestrates readiness, coverage, docs, gap tools into an ACC report. | Measures representation/projectability; does not author/project from one primitive contract. |
| ADR-150 Projection Profiles and Harness Registry | Adds default/full projection profiles and harness registry. | Profile/harness proof; not per-primitive contract as source input. |
| ADR-154 Multi-IDE Structural Harness Projection | Implements structural projections for OpenCode, VS Code Copilot, and Cursor. | Structural config generation only; no runtime parity and no contract-driven adapter generation. |
| ADR-155 Shell/CI Formal Harness | Makes shell/CI a structural harness. | Command projection only; runtime stack success is out of scope. |
| ADR-159 / ADR-160 Structural Harness Batches | Expands structural projection to many AGENTS/rules/MCP harnesses. | Broadens adapters, but still projects from installer logic, not primitive contracts. |
| ADR-189 Surface Implementation Coverage | Adds surface axis for primitive support: IDE, CLI, shell-CI, UI, service, report. | Coverage/reporting layer; does not create the canonical contract. |
| ADR-190 Harness Action Receipts | Creates vendor-neutral action receipts and trust levels. | Action evidence vocabulary, not primitive intervention ledger. |
| ADR-205 Trace Joiner | Joins metric streams into run traces. | Needs primitive interventions/codebase itinerary from ADR-256 to answer primitive self-use. |
| ADR-256 Primitive Contract Registry and Runtime Evidence Ledger | Directly names the missing root contract and evidence ledger. | Proposed / plan-first; implementation not done. |

## Implementation evidence reviewed

### Projection exists, but is not contract-driven yet

`scripts/cos_init.py` supports many harness IDs:

```text
claude, codex, opencode, vscode-copilot, cursor, qwen-code, kimi-code,
gemini-cli, warp, amp-code, jetbrains-junie, qoder, factory-droid, cline,
continue-dev, kilo-code, zed-ai, augment-code, goose, aider, shell-ci
```

For structural harnesses, `_write_structural_instruction_harness_settings()`
writes project-local files such as `opencode.json`, `.cursor/rules/...`,
`.github/copilot-instructions.md`, AGENTS-derived files, and MCP placeholders.

This is real cross-IDE projection, but it is driven by installer/driver logic and
profile manifests. It does **not** iterate over a canonical
`primitive-contracts.yaml` registry and decide, primitive by primitive, how to
project each behavior.

### Lifecycle metadata is close but not enough

`manifests/primitive-lifecycle.yaml` contains machine-readable rows for hundreds
of primitives. Example rows for the intended ADR-256 first slice already exist:

| Primitive | Lifecycle support today |
|---|---|
| `hooks/destructive-git-blocker.sh` | blocking hook, supported harnesses currently list `claude`, metric `git-op-blocks.jsonl`. |
| `hooks/destructive-rm-blocker.sh` | blocking hook, supported harnesses currently list `claude`, metric `rm-op-blocks.jsonl`. |
| `hooks/reinvention-check.sh` | advisory/sandbox hook, metric `reinvention-checks.jsonl`. |
| `hooks/large-file-advisor.sh` | advisory/sandbox hook, metric `large-file-reads.jsonl`. |
| `hooks/skill-router-bash-gate.sh` | advisory hook, supported harnesses `claude` and `codex`. |

However, lifecycle rows do not yet answer all ADR-256 contract questions:

- required capabilities, e.g. `inspect_shell_command`, `block_tool_call`,
  `emit_intervention`;
- trigger intent in portable terms, e.g. `before_tool_call` / `shell_command`;
- action contract with reason codes;
- per-harness projection fidelity, e.g. Claude native lifecycle, Codex governed
  wrapper, OpenCode plugin lifecycle capable, Cursor structural advisory;
- evidence sinks for canonical primitive interventions;
- trace correlation fields and redaction policy.

### OpenCode correction

OpenCode should not be treated as instruction-only. Current docs/manifests now
capture that OpenCode has native-ish host surfaces:

```text
opencode.json / AGENTS.md advisory context
  -> OpenCode permissions for coarse allow/ask/deny
  -> OpenCode plugin tool.execute.before/after for enforcement/observation
  -> primitive-interventions.jsonl for comparable COS evidence
```

Current COS proof remains structural until a COS OpenCode plugin adapter and
runtime smoke exist.

## Gap matrix against the premise

| Premise requirement | Current status | Assessment |
|---|---|---|
| One IDE-agnostic primitive definition place | `skills/`, `rules`, `hooks`, `scripts` plus lifecycle/readiness manifests | **Partial** |
| Machine-readable contract per primitive | Implemented for the first five primitives by ADR-257 in `manifests/primitive-contracts.yaml` | **Partial** |
| Harness adapters for all listed IDEs | Many structural adapters exist in `cos_init.py`; Claude/Codex have stronger lifecycle projection | **Partial** |
| Adapter generation from the primitive contract | Not implemented; projection is profile/driver driven | **Missing** |
| Per-primitive fidelity by harness | Planned in ADR-256; some proof levels exist at harness level | **Partial** |
| Runtime intervention evidence ledger | Planned as `.cognitive-os/metrics/primitive-interventions.jsonl` | **Missing** |
| Codebase itinerary / self-use proof | Planned as `.cognitive-os/metrics/codebase-itinerary.jsonl` | **Missing** |
| Joined trace answering “which primitive intervened” | Trace joiner exists, but lacks ADR-256 streams | **Partial** |

## Root conclusion

The answer is not “we forgot this entirely.” The answer is:

1. The repository has **many prior ADRs that contemplated pieces of it**.
2. ADR-057 is the earliest direct statement of the premise: author behavior once,
   project through harness drivers.
3. ADR-154/159/160 implemented broad structural IDE projection.
4. ADR-126/146/147/150/189 built lifecycle/readiness/ACC/proof infrastructure.
5. ADR-190/205 built action receipts and trace joining.
6. ADR-256 is the first ADR that names the missing root object explicitly:
   primitive contract registry + intervention ledger + itinerary.

So the real gap is **not conceptual**. It is the implementation bridge. ADR-257
closed the first arrow by creating the minimal registry:

```text
primitive-lifecycle/readiness metadata
  + existing primitive sources
  -> manifests/primitive-contracts.yaml  # ADR-257 Phase 1 implemented
  -> projection/fidelity report          # pending
  -> runtime intervention writers        # pending
  -> trace_joiner integration            # pending
```

## Implemented follow-up

ADR-257 implemented the recommended Phase 1 slice:

- `manifests/primitive-contracts.yaml`
- `tests/contracts/test_primitive_contract_registry.py`
- first five contracts:
  - `destructive-git-blocker`
  - `destructive-rm-blocker`
  - `reinvention-check`
  - `large-file-advisor`
  - `skill-router`

The remaining recommended next slice is ADR-256 Phase 2: implement the
`primitive-interventions.jsonl` writer/helper and bridge the first blocking
hooks. Only after contract/evidence reporting exists should COS broaden consumer
UX commands such as `cos adapters list/install/verify`.

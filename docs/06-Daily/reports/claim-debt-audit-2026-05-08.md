---
report_type: claim-debt-audit
scope: external-tools-radar-2026-05-08
date: 2026-05-08
status: documentation-before-implementation
---

# Claim Debt Audit — External Tools Radar 2026-05-08

## Purpose

The radar itself recommends adding a claim-debt column. This document is the
manual first pass before automating it. It identifies claims that could become
public overclaims if they are not qualified.

## Claim-debt table

| Claim | Current classification | Why it is risky | Required wording / closure |
|---|---|---|---|
| `85% token reduction` from deferred tool loading | Unmeasured locally | It is upstream/provider research, not a COS measurement. | Say "upstream-reported / locally unmeasured" until a COS benchmark exists. |
| FastMCP in root `requirements.txt` | Path errata | Tool use is real, dependency path is wrong. | Say package-level requirements declare FastMCP. |
| Langfuse fully removed | Partial | Trace sink migration appears real, but legacy refs/dependencies may remain. | Say deprecated for runtime tracing; classify remaining refs before claiming repo-wide removal. |
| Phoenix license posture | Needs packaging boundary | Phoenix server license posture differs from client/OTel usage. | Say operator-installed optional server unless license gate approves bundling. |
| Bubblewrap hardened sandbox | Partial | Adapter exists, but seccomp/capability/read-only-host questions remain. | Say native sandbox adapter shipped; hardening pending. |
| Deferred tool loading runtime | Partial/blueprint | COS has planning/index; provider-native runtime may not be active. | Say governance/index substrate exists; provider-native loading remains provider-dependent. |
| Trust Report "requires" | Corrected in README, stale in reports | Historical reports imply stronger enforcement than current hook. | Use advisory/logging wording unless blocking mode is implemented. |
| Obsidian/markdown reader surface | Unverified in this pass | README mentions operator-facing surface; proof path not linked by radar. | Add proof path or reduce claim. |
| 14 ADRs 222-236 | Arithmetic ambiguity | Range contains tombstones/reserved slots. | Count active/tombstone/reserved separately. |

## Public-claim rule

A radar claim can become public only if at least one of these is true:

- `runtime proof`: supported code path uses it and tests prove it;
- `cli proof`: supported CLI command uses it and tests prove it;
- `hook proof`: registered hook/profile uses it and tests prove it;
- `manual proof`: runbook exists and public wording says manual/opt-in;
- `research-only`: public wording explicitly says research/proposed/unmeasured.

## Open claim-debt items to resolve before implementation/public docs

1. Decide if Langfuse package references are optional legacy, to remove, or to
   retain under a documented migration boundary.
2. Add local token-reduction benchmark before using any numeric deferred-loading
   result as a COS claim.
3. Add a Phoenix packaging/license note to observability docs if Phoenix server
   remains operator-installed.
4. Add proof path or downgrade the Obsidian/markdown reader claim.
5. Normalize ADR count wording in the tech radar index.

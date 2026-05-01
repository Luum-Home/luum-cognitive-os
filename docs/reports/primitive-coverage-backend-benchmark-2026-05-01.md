# Primitive Coverage Backend Benchmark — 2026-05-01

## Scope

Local metadata/protocol benchmark of four code-intelligence candidates as possible backends for `primitive_coverage/`.
The benchmark deliberately avoids installing or vendoring candidates; it inspects local clones, licenses, package metadata, and README claims.

## Summary

| Candidate | Score | License | Recommendation |
|---|---:|---|---|
| [repowise](https://github.com/repowise-dev/repowise) | 50/110 | blocked | evaluate-only-license-blocked |
| [codegraphcontext](https://github.com/CodeGraphContext/CodeGraphContext) | 45/110 | compatible | secondary-or-reference-only |
| [qartez](https://github.com/kuberstar/qartez-mcp) | 40/110 | review-required | license-review-before-spike |
| [jcodemunch](https://github.com/jgravelle/jcodemunch-mcp) | 25/110 | review-required | license-review-before-spike |

## Question Matrix

| Candidate | Primitives first-class | Context-saving query | Unused consumers | Stale docs | JSON/SARIF | Token savings | Local/offline | License OK | Adapter fit |
|---|---|---|---|---|---|---|---|---|---|
| repowise | no (0) | no (0) | yes (15) | yes (15) | no (0) | yes (10) | yes (10) | no (0) | no (0) |
| codegraphcontext | no (0) | no (0) | yes (15) | no (0) | no (0) | no (0) | yes (10) | yes (10) | yes (10) |
| qartez | no (0) | no (0) | yes (15) | no (0) | partial (5) | yes (10) | yes (10) | no (0) | no (0) |
| jcodemunch | no (0) | no (0) | no (0) | no (0) | partial (5) | yes (10) | yes (10) | no (0) | no (0) |

## Token-Economy Baseline

- Text files counted: 10588
- Repo text bytes: 173914388
- Existing primitive evidence bytes: 4996978
- Evidence/repo ratio: 0.028732
- Rough savings vs reading every text file: 0.9713

## Notes by Candidate

### repowise

- Repo: https://github.com/repowise-dev/repowise
- Local path: `/private/tmp/cos-code-intel-candidates/repowise`
- License: blocked — License gate blocks AGPL/SSPL/BSL/ELv2-style terms for embedding.
- Recommendation: `evaluate-only-license-blocked`

- `first_class_primitives`: **no** (0 pts). Detects code/docs entities, but not COS skills/hooks/rules as first-class rows.
- `primitive_context_query`: **no** (0 pts). No native evidence that it maps files to primitive-level context-saving affordances.
- `unused_consumers`: **yes** (15 pts). Graph/index can likely support consumer-gap detection with a COS adapter.
- `stale_docs`: **yes** (15 pts). Documentation intelligence appears close enough to support stale-doc signals.
- `json_sarif`: **no** (0 pts). No SARIF/JSON reporting claim found.
- `token_savings`: **yes** (10 pts). README contains explicit token/cost/context reduction claims.
- `local_offline`: **yes** (10 pts). Designed to run as a local CLI/MCP indexing backend.
- `license_compatible`: **no** (0 pts). License gate blocks AGPL/SSPL/BSL/ELv2-style terms for embedding.
- `adapter_fit`: **no** (0 pts). Would need licensing clearance and/or an additional COS semantic adapter before use.

### codegraphcontext

- Repo: https://github.com/CodeGraphContext/CodeGraphContext
- Local path: `/private/tmp/cos-code-intel-candidates/CodeGraphContext`
- License: compatible — Permissive license detected.
- Recommendation: `secondary-or-reference-only`

- `first_class_primitives`: **no** (0 pts). Detects code/docs entities, but not COS skills/hooks/rules as first-class rows.
- `primitive_context_query`: **no** (0 pts). No native evidence that it maps files to primitive-level context-saving affordances.
- `unused_consumers`: **yes** (15 pts). Graph/index can likely support consumer-gap detection with a COS adapter.
- `stale_docs`: **no** (0 pts). No native stale-doc or docs-vs-code freshness signal found.
- `json_sarif`: **no** (0 pts). No SARIF/JSON reporting claim found.
- `token_savings`: **no** (0 pts). No explicit token-saving claim found.
- `local_offline`: **yes** (10 pts). Designed to run as a local CLI/MCP indexing backend.
- `license_compatible`: **yes** (10 pts). License is compatible with the repo allowlist.
- `adapter_fit`: **yes** (10 pts). Good backend candidate for primitive_coverage adapters without rewriting the framework.

### qartez

- Repo: https://github.com/kuberstar/qartez-mcp
- Local path: `/private/tmp/cos-code-intel-candidates/qartez-mcp`
- License: review-required — Custom/commercial or non-commercial terms require legal/commercial approval.
- Recommendation: `license-review-before-spike`

- `first_class_primitives`: **no** (0 pts). Detects code/docs entities, but not COS skills/hooks/rules as first-class rows.
- `primitive_context_query`: **no** (0 pts). No native evidence that it maps files to primitive-level context-saving affordances.
- `unused_consumers`: **yes** (15 pts). Graph/index can likely support consumer-gap detection with a COS adapter.
- `stale_docs`: **no** (0 pts). No native stale-doc or docs-vs-code freshness signal found.
- `json_sarif`: **partial** (5 pts). SARIF not found; JSON/structured output may be available via MCP/tool protocol.
- `token_savings`: **yes** (10 pts). README contains explicit token/cost/context reduction claims.
- `local_offline`: **yes** (10 pts). Designed to run as a local CLI/MCP indexing backend.
- `license_compatible`: **no** (0 pts). Custom/commercial or non-commercial terms require legal/commercial approval.
- `adapter_fit`: **no** (0 pts). Would need licensing clearance and/or an additional COS semantic adapter before use.

### jcodemunch

- Repo: https://github.com/jgravelle/jcodemunch-mcp
- Local path: `/private/tmp/cos-code-intel-candidates/jcodemunch-mcp`
- License: review-required — Custom/commercial or non-commercial terms require legal/commercial approval.
- Recommendation: `license-review-before-spike`

- `first_class_primitives`: **no** (0 pts). Detects code/docs entities, but not COS skills/hooks/rules as first-class rows.
- `primitive_context_query`: **no** (0 pts). No native evidence that it maps files to primitive-level context-saving affordances.
- `unused_consumers`: **no** (0 pts). No enough cross-reference evidence to detect scripts/primitives without consumers.
- `stale_docs`: **no** (0 pts). No native stale-doc or docs-vs-code freshness signal found.
- `json_sarif`: **partial** (5 pts). SARIF not found; JSON/structured output may be available via MCP/tool protocol.
- `token_savings`: **yes** (10 pts). README contains explicit token/cost/context reduction claims.
- `local_offline`: **yes** (10 pts). Designed to run as a local CLI/MCP indexing backend.
- `license_compatible`: **no** (0 pts). Custom/commercial or non-commercial terms require legal/commercial approval.
- `adapter_fit`: **no** (0 pts). Would need licensing clearance and/or an additional COS semantic adapter before use.

## Recommendation

Keep COS `primitive_coverage/` as the semantic orchestrator. Use an external graph backend only below it.
CodeGraphContext is the safest first adapter spike because it is MIT-licensed and local/MCP-oriented.
Qartez and jCodeMunch are promising token-efficiency references but require license review before integration.
Repowise is the closest conceptual product for graph+docs+decisions, but AGPL makes it evaluation-only unless legal explicitly approves a separate-process boundary.

## Inputs

- Generated at: `2026-05-01T15:18:20.014525+00:00`
- Candidates dir: `/private/tmp/cos-code-intel-candidates`
- Project dir: `<repo-root>`

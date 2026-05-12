---

adr: 247
title: Manifest-Driven Postmortem Regression Audits and External Tool Adapters
status: accepted
implementation_status: implemented
classification_basis: 'manifest-driven audit, runner, runbook, and verification commands implement the policy correction scope'
relationship_chain_exempt: true
date: 2026-05-08
supersedes: []
superseded_by: null
extends: [ADR-212, ADR-215, ADR-216, ADR-239, ADR-240, ADR-242, ADR-243, ADR-244, ADR-245, ADR-246]
implementation_files:
  - manifests/postmortem-regression-audit.yaml
  - scripts/cos-postmortem-regression-audit
  - docs/runbooks/postmortem-regression-audit.md
tier: maintainer
tags: [audits, manifests, external-tools, no-hardcoding, primitive-coherence]
---

<!-- ADR_RELATION_CHAIN_EXEMPT: part of the 2026-05-08 implementation-ledger ADR burst; relationship depth is tracked by control-plane audits rather than new transitive ADR scope. -->

# ADR-247: Manifest-Driven Postmortem Regression Audits and External Tool Adapters

## Status

Accepted. This ADR documents the policy correction made after ADR-242 through
ADR-246: audits must detect bug classes generically, avoid hardcoded sensitive
values, and prefer existing ecosystem tools behind explicit adapters instead of
rebuilding those tools inside Cognitive OS.

## Context

ADR-239 and later ADRs address multi-agent and release-readiness failures:
worktree isolation, history rewrite safety, post-rewrite push collisions,
claim enforcement, chaos test source mutation, and release freeze transactions.

The first implementation of `scripts/cos-postmortem-regression-audit` correctly
created a read-only detector, but the operator raised two important concerns:

1. The detector must not hardcode sensitive data or project-specific values.
2. COS should not reinvent mature tools such as Gitleaks, TruffleHog,
   git-filter-repo, pre-commit, Conftest/OPA, or GitHub branch protection.

External research on 2026-05-08 confirmed the industry pattern:

| Domain | Existing tool/pattern | COS stance |
|---|---|---|
| Multi-agent file isolation | Git worktrees per agent/task | Adopt as the filesystem isolation primitive; COS owns lifecycle and receipts |
| Secret detection | Gitleaks, TruffleHog, git-secrets, GitHub Secret Scanning / Push Protection | Consume as scanners; COS owns policy, evidence, and release gates |
| History cleanup | git-filter-repo + GitHub sensitive-data guidance | Use via governed wrapper; COS owns backup/idempotency/transaction controls |
| Hook orchestration | pre-commit, Lefthook, Overcommit, Husky | Project hooks to existing frameworks when useful; COS owns cross-harness coherence |
| Policy-as-code | Conftest/OPA, GitHub rulesets, branch protection, required checks | Integrate as external enforcement planes; COS owns manifest translation and local preflight |
| Chaos/source mutation guard | pytest fixtures, snapshot/revert, read-only mounts | Use pytest/runtime guards; COS owns protected-surface declarations |

The strategic point is: **COS is not a replacement for these tools. COS is the
agentic control plane that declares when and how those tools are consumed.**

## Decision

Postmortem regression audits must be **manifest-driven**.

Hardcoded Python checks are allowed only as generic check engines. The specific
ADR mapping, paths, forbidden patterns, required artifacts, external tools, and
sensitive-token sources must live in manifests.

Introduce the manifest:

```text
manifests/postmortem-regression-audit.yaml
```

The manifest declares checks such as:

```yaml
checks:
  - id: direct-filter-repo-callsite
    adr: ADR-242
    type: forbidden_pattern
    scope: [lib, scripts, hooks]
    pattern: "\\bgit\\s+filter-repo\\b"
    allow_paths:
      - scripts/cos-filter-repo-wrap.sh

  - id: release-freeze-artifact-missing
    adr: ADR-246
    type: required_paths
    paths:
      - scripts/cos-release-freeze
      - lib/release_freeze.py
```

Sensitive values must never be embedded in the manifest. Sensitive scans refer
to environment variable names or local-only manifests:

```yaml
sensitive_value_sources:
  env:
    - COS_HISTORY_SANITIZE_OPERATOR_EMAIL
    - COS_HISTORY_SANITIZE_HOME_PREFIX
```

## External tool adapter contract

Every external tool used by a governance primitive must be declared with:

- `tool`
- `owner`
- `license_spdx`
- `adapter`
- `allowed_callers`
- `failure_policy`
- `recursion_boundary`
- `input_sensitivity`
- `output_sanitization`

Example:

```yaml
external_tools:
  - tool: gitleaks
    owner: release-secret-audit
    license_spdx: MIT
    adapter: cli-json
    allowed_callers:
      - scripts/cos-secret-audit
    failure_policy: fail-closed-in-release
    recursion_boundary: no COS hook invocation from scanner subprocess
    input_sensitivity: repository blobs and git history
    output_sanitization: redact configured private tokens before publishing reports
```

## Non-hardcoding rules

1. Do not hardcode operator emails.
2. Do not hardcode local home paths.
3. Do not hardcode consumer/project codenames.
4. Do not hardcode private URLs, tokens, or organization-internal service names.
5. Use repo-relative paths in public docs and scripts.
6. Use env vars or gitignored local manifests for private values.
7. Public reports may include placeholders only.

## Alternatives rejected

- **Hardcode one Python check per ADR** — rejected because it does not scale and
  turns each new incident into another code edit.
- **Build first-party replacements for Gitleaks/TruffleHog/git-filter-repo** —
  rejected because mature tools already exist; COS should orchestrate them.
- **Rely only on GitHub hosted protections** — rejected because COS must work
  locally, cross-harness, and before a repo is public.
- **Store sensitive patterns directly in public manifests** — rejected because
  the detector would become the leak.

## Consequences

Positive:

- New postmortem classes become manifest entries instead of new bespoke scripts.
- Sensitive values stay out of code and public docs.
- Mature external tools can be adopted without losing COS governance.
- Primitive coherence improves because third-party tools become declared
  adapters with owners, callers, and recursion boundaries.

Negative:

- The manifest schema must be maintained.
- Generic check engines need good tests to avoid false positives.
- External tool version drift remains a supply-chain concern; ADR-212/ADR-215
  audits must cover tool versions and licenses.

## Verification

```bash
python3 -m pytest tests/unit/test_postmortem_regression_audit.py tests/unit/test_primitive_coherence_audit.py tests/audit/test_adr_contracts.py -q
scripts/cos-postmortem-regression-audit --json
scripts/primitive-coherence-audit.py --json
```

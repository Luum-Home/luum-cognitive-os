---
id: ADR-306
title: Scope Projection Runtime Audit
status: accepted
implementation_status: implemented
date: 2026-05-14
extends: [ADR-019, ADR-256, ADR-258, ADR-302]
related: [ADR-304]
tags: [portability, projection, scope, consumer-install, primitive-governance]
---

# ADR-306 — Scope Projection Runtime Audit

## Status

Accepted, implemented 2026-05-14.

## Context

COS now classifies agentic primitives with three canonical scopes:

- `os-only` — maintainer/self-construction primitives for operating COS itself.
- `project` — consumer-project primitives intended for downstream repositories.
- `both` — portable primitives valid in both the COS repo and downstream projects.

ADR-302 and the scope governance manifest made the taxonomy explicit. The
`cos-scope-both-portability-audit` and paired red-team proofs then removed the
largest blind spot for `both`: every declared portable primitive must now have a
paired falsification probe.

That still left a higher-level gap: **a paired portability test is not an
end-to-end guarantee that scope classification is respected by projection and
runtime install flows**. A primitive can pass a cwd/import portability probe and
still violate the taxonomy if:

- an `os-only` primitive leaks into a consumer install;
- a `project` or `both` primitive embeds the source COS checkout path;
- a wrapper uses `COGNITIVE_OS_PROJECT_DIR` as the OS source root instead of the
  consumer project root;
- a skill declares `<!-- SCOPE: os-only -->` but stale `audience: both` metadata
  causes it to be installed anyway.

The last case was real: the first runtime projection smoke found six `os-only`
skills projected into a `COS_INSTALL_SCOPE=project` install because
`skill_scope_allows()` honored legacy `audience:` before the canonical scope
marker.

## Decision

Introduce `scripts/cos-scope-projection-audit` as the canonical automated audit
for checking that scope taxonomy maps to projection/runtime evidence.

The audit performs four checks:

1. **Taxonomy validity** — every discovered `SCOPE:` marker must be one of
   `os-only`, `project`, or `both`.
2. **Portable proof coverage** — every `SCOPE: both` source artifact must have a
   paired proof path as defined by `lib/portability_proof_paths.py`.
3. **Source-root hardcoding** — `project` and `both` source artifacts must not
   embed the current COS checkout path or developer home path.
4. **Consumer projection smoke** — when invoked with `--run-install-smoke`, the
   audit creates a temporary consumer install using `COS_INSTALL_SCOPE=project`
   and blocks if any projected file carries `SCOPE: os-only` or an invalid scope.

The audit emits:

- `.cognitive-os/reports/scope-projection-audit.json`
- `.cognitive-os/reports/scope-projection-audit.md`

`--strict` exits `2` on block findings.

## Implementation

Files:

- `scripts/cos-scope-projection-audit` — report/audit CLI.
- `scripts/cos_init.py` — `skill_scope_allows()` now treats the canonical
  `<!-- SCOPE: ... -->` marker as authoritative over legacy `audience:`.
- `tests/unit/test_scope_projection_audit.py` — pure audit contract tests.
- `tests/unit/test_cos_init_py.py` and `tests/behavior/test_cos_init_parity_2_2.py`
  — regression tests for scope-marker precedence.
- Existing install-scope integration tests continue proving the install path.

## Consequences

Positive:

- The taxonomy is no longer just documentation; it is executable against source
  and a disposable consumer projection.
- `SCOPE: both` now has two layers of evidence: paired proof and projection
  audit.
- `os-only` leakage is caught in the same lane that operators can run before
  release or consumer packaging.

Tradeoffs:

- The install smoke is heavier than a static audit and should be opt-in for fast
  local loops (`--run-install-smoke`).
- Some legacy scripts still do not expose consistent `--help`; runtime proof
  must distinguish semantic command failure from path/cwd/import failure.
- The audit does not prove full harness behavioral parity. It proves the scope
  contract and projection boundary, while harness-specific semantics remain in
  projection-fidelity and adapter smoke lanes.

## Validation

Targeted commands used for implementation:

```bash
.venv/bin/python -m pytest tests/unit/test_scope_projection_audit.py -q
.venv/bin/python -m pytest tests/unit/test_cos_init_py.py tests/behavior/test_cos_init_parity_2_2.py -q
scripts/cos-scope-projection-audit --repo-root . --json --no-write
scripts/cos-scope-projection-audit --repo-root . --run-install-smoke --json --no-write
```

Final runtime-smoke result:

```json
{
  "block_findings": 0,
  "both_total": 764,
  "both_with_proofs": 764,
  "findings": 0,
  "projection_by_scope": {"both": 531, "project": 34},
  "source_by_scope": {"both": 764, "os-only": 355, "project": 64}
}
```

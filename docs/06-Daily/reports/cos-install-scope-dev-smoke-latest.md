# COS install-scope dev smoke — latest

This smoke simulates a normal developer initializing a small Python repository with each `COS_INSTALL_SCOPE` value, then running project tests, `cos-status`, and representative hook probes.

**Status:** `pass-with-product-warning`

**Finding:** Three names currently collapse into two effective primitive surfaces: project and both are equivalent; all is the maintainer/full superset.

## Scope matrix

| scope | install ok | total files | hooks | rules | skills | templates | os-only primitives | os-only support | tests pass | status JSON | destructive git blocked | secret probe ok | lethal present | lethal blocks |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| project | ✅ | 427 | 189 | 108 | 120 | 10 | 0 | 34 | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| both | ✅ | 427 | 189 | 108 | 120 | 10 | 0 | 34 | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| all | ✅ | 614 | 285 | 122 | 191 | 16 | 116 | 34 | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

## Interpretation

- `project` vs `both` equivalent: `True`.
- `all` is larger by count: `True`.
- Filtered scopes exclude top-level `SCOPE: os-only` primitives: `True`.
- Filtered scopes still carry `SCOPE: os-only` support files: `True`.
- `all` includes maintainer-only primitives: `True`.
- Extra `all` hooks pass their probes when present: `False`.

## Product consequence

Do not claim three distinct project-install tiers until project and both have separate semantics, tests, and user-facing docs. Today the evidence supports two tiers: filtered consumer install and all/maintainer install.

This still does **not** prove COS wins in quality, speed, or cognitive load. It proves the install surfaces can be exercised like a developer would exercise them, and it exposes whether the named tiers are semantically real.

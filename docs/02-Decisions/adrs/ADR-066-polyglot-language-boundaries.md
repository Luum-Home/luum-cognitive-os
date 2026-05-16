---
adr: 66
title: Polyglot Language Boundaries & Migration Pressure
status: proposed
implementation_status: planned
date: '2026-04-24'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit prose status migration for previously prose-only ADR
---

# ADR-066 — Polyglot Language Boundaries & Migration Pressure

## Status

Proposed — 2026-04-24.

Complements the Python naming refactor that landed today (rename of 35 hyphenated
Python scripts to `snake_case`, plus `rules/python-naming.md` and
`tests/audit/test_python_naming.py`) by codifying naming + role policy for the
**three** languages currently in tree: bash, Python, Go.

This ADR is **design-only**. It does not rewrite any existing code.

## Context

The Cognitive OS codebase has grown polyglot without an explicit policy:

- **bash**: 154 hooks (`hooks/*.sh`) + ~60 scripts (`scripts/*.sh`)
- **Python**: ~250 modules under `lib/`, 35+ scripts under `scripts/*.py`,
  ~10,500 unit/contract/audit tests under `tests/`
- **Go**: 2 CLI tools — `cos` (package manager) and `cos-test` (TUI test runner)
- **YAML/JSON**: configuration, schemas, settings
- **Markdown**: docs, ADRs, skills, rules

This works in practice but the absence of explicit policy is itself the root
cause of repeated drift. Symptoms surfaced today (2026-04-24):

1. **35 Python scripts had kebab-case filenames** (e.g. `radar-merge.py`,
   `cos-init-helper.py`). Bash naming convention had leaked across the language
   boundary, blocking pytest importability and forcing
   `importlib.util.spec_from_file_location` hacks in tests.
2. **Hook chain latency hit 18 seconds** on a single Stop event. RCA pointed to
   excessive subprocess forks across bash → Python boundaries (engram topic
   `perf/hook-chain-rca-2026-04-24`).
3. **Missing symlink**: `packages/quality-gates/hooks/_lib` was unset because the
   contract between a "package's hook directory" and the global `hooks/_lib/`
   was never written down.
4. **Test ergonomics**: importing hyphenated scripts required path manipulation
   instead of `from scripts.radar_merge import …`.

Operator observation (2026-04-24): the repository spans Bash, Python, Go, and other languages; the operator asked whether that was acceptable and then requested an ADR.

The operator does **not** want to rewrite anything. The ask is: **document the
policy so future drift is caught at the audit-test layer, not at the
"production hook is 18s slow" layer.**

## Decision — Role matrix

Each language is assigned an explicit role. This matrix is the reference for
"is this the right tool for this file?" reviews.

| Language | Role | Why it fits | Rejection criteria |
|---|---|---|---|
| Bash | Event handlers (hooks under `hooks/`), thin OS glue, install/bootstrap scripts | ~5ms cold start, native stdin/exit-code contract with Claude Code, ubiquitous on dev machines, no runtime install | Complex parsing (awk/sed >30 lines), state machines, JSON generation beyond `jq` wrappers, anything needing dataclasses, anything that wants tests |
| Python | Orchestration logic, parsing, data structures, internal CLI scripts, **all tests** | Rich ecosystem (pytest, pydantic, dataclasses, jinja, ruff), introspection, cross-platform, low friction for contributors | Latency-critical paths (<50ms cold start budget), single-binary distribution to end users, anything that must run before `uv sync` |
| Go | End-user-distributed CLI tools (`cos`, `cos-test`) | Single static binary, cross-platform, no runtime deps on the consumer's machine, fast startup | In-repo orchestration, test helpers, anything internal-only — Go's compile-deploy-test loop is too slow for iterative scripts |

The matrix is intentionally **narrow**: each language has one primary role and
explicit rejection criteria. New files must justify their language against this
table or propose an amendment.

## Decision — Naming conventions per language

This section ratifies the Python refactor that landed today and codifies
sibling conventions for bash and Go.

| Language | Convention | Example | Enforcement |
|---|---|---|---|
| Bash | `kebab-case` for filenames; `snake_case` for functions and variables; `UPPER_SNAKE_CASE` for env vars | `scripts/cos-bootstrap.sh` exporting `cos_bootstrap_init()` reading `$COS_PROFILE` | `shellcheck` in CI + an audit test (Phase 1 follow-up — see Open Questions) |
| Python | `snake_case` filenames, modules, functions, variables; `PascalCase` classes; `UPPER_SNAKE_CASE` constants | `scripts/radar_merge.py` :: `parse_doc_entries()` :: `class MergeAction` :: `DEFAULT_TIMEOUT` | `rules/python-naming.md` + `tests/audit/test_python_naming.py` (**LANDED TODAY** in commit-pair with this ADR) |
| Go | `camelCase` for unexported, `PascalCase` for exported, `gofmt` for everything else, package names lowercase single-word | `pkg/radar/Merger`, `pkg/radar/newMerger()` | `go vet` + `gofmt -l` in CI |

The Python row is the **load-bearing rule** today — it is what made today's
refactor non-optional. The bash and Go rows are codified now so the next drift
event has the same kind of audit test to point to.

## Decision — Migration pressure (re-write triggers)

This section answers: *"when does a file deserve to change languages?"* The
default answer is **never** — switching languages is expensive and almost
always premature. The triggers below are the **only** acceptable cases.

### Bash → Python

A bash script is a candidate for Python rewrite when **all** of:

- Length **>200 lines** (cumulative, including sourced helpers)
- AND **at least one** of:
  - Parses JSON beyond simple `jq -r '.field'` paths (e.g. needs schema
    validation, conditional traversal, multi-file merge)
  - Has nested conditionals depth **>3** (`if ... if ... case ... if`)
  - Has unit tests that are hard to write (bats coverage <50% because the
    script's logic is too entangled with its I/O)

**Concrete candidate today**: `scripts/cos-init.sh` is currently 300+ lines
with heavy `awk`/`sed` parsing of YAML and conditional branching for
profile/phase combinations. It is **flagged** as a migration candidate but
**not migrated** in this ADR.

**Concrete anti-candidate**: a 40-line cleanup hook that runs `find … -delete`
**stays in bash** even if it grows. The trigger is depth + parsing, not size
alone.

### Python → Go

A Python module is a candidate for Go rewrite **only** when:

- It is distributed to end users as a binary (`go install`, GitHub release
  asset, Homebrew formula, etc.)
- AND a Python equivalent would require the user to manage a Python
  environment (pip, uv, pipx) on their machine

Internal orchestration (anything under `lib/`, `scripts/*.py`, or `tests/`)
**never** migrates to Go. The pytest ecosystem is irreplaceable for our test
shape, and Go's compile loop kills iteration speed on internal tooling.

### Anti-migration rules

- **Bash hooks NEVER move to Python**, even if they grow long. The hard
  constraint is *startup latency × 154 hooks per session*. A 200ms Python
  startup × 154 hooks = 30s of pure interpreter spin-up per session. This is
  the ceiling that today's 18s incident already pushed against. Long bash
  hooks should be **decomposed** (split into smaller bash files, or have the
  heavy logic moved to a Python helper that the bash hook calls **once**).
- **Python scripts NEVER move to Go for performance reasons alone**. Go's
  performance edge over Python is irrelevant for our workloads — distribution
  is the only valid trigger.

## Decision — Boundary contracts

When bash calls Python (or vice versa), the contract MUST be one of these
shapes. Ad-hoc parsing across the boundary is the original sin that caused
today's 18s incident.

| Contract element | Rule |
|---|---|
| Data format | JSON on stdin/stdout. **Not** ad-hoc text, not space-separated fields, not "parse this with awk" |
| Exit codes | `0` = success, `1` = soft-fail (advisory; caller continues), `2+` = hard-fail (caller blocks) |
| Configuration | Environment variables, prefixed `COS_*` (reserved namespace) |
| Large output | If stdout >5KB, the producer wraps via `scripts/result-truncator.sh` (see `rules/result-management.md`) |
| Logging | stderr for human-readable messages; stdout reserved for the contract payload |
| Cross-language schemas | Today: none. See Open Questions for the JSON-Schema-as-source-of-truth discussion |

This is **aspirational normalization**, not a big-bang migration. Existing
bash↔Python handoffs that violate this contract should be flagged in code
review and migrated opportunistically. The next bash→Python audit (Phase 1
follow-up) will enumerate violations.

## What we replicate / what we do NOT

- **Replicate**: the existing polyglot setup. Bash for hooks, Python for
  orchestration, Go for distributed CLIs. This split is working; the issue was
  the *implicit* policy, not the split itself.
- **Do NOT replicate**: a "wrapper language" meta-tool that pretends to unify
  bash + Python + Go behind a single DSL. We've watched several
  agentic/devtool projects try this and it always becomes a fourth language
  with worse ergonomics than any of the three it claims to replace. The right
  fix is **explicit boundaries**, not a hidden unifier.

## Consequences

### Positive

- Drift like today's 35-hyphen-Python-script incident gets caught by audit
  tests **before** landing, not during a downstream pytest failure.
- New contributors have a single decision table to point to: "is this hook,
  helper, or distributed CLI?"
- Migration triggers are **numeric** (>200 lines, depth >3) instead of "I
  feel like this is too long". Reviewers can disagree on a number; they cannot
  disagree on a vibe.
- The 18s hook-chain incident has a documented mitigation path (decompose, or
  call a Python helper once instead of forking N times).

### Negative

- **3× onboarding cost persists.** Contributors still need bash, Python, and
  Go literacy to be effective across the codebase. This ADR does not reduce
  that cost — it accepts it as a cost of specialization. We are explicit about
  this trade-off rather than pretending polyglot is free.
- The bash and Go audit tests are not yet written. Until Phase 1 ships them,
  enforcement of the bash and Go naming rows is by code review only.

### Neutral

- No runtime behavior changes. Existing files are not renamed, moved, or
  rewritten by this ADR.
- The Python renames landed today via a separate refactor commit; this ADR
  ratifies the policy that made the renames mandatory.

## Alternatives rejected

1. **"Rewrite everything in Python"** — would balloon hook startup latency
   from ~5ms to ~150-200ms per hook. With 154 hooks per session this hits a
   30s ceiling we cannot afford. Rejected on the latency budget.
2. **"Rewrite everything in Go"** — loses the pytest ecosystem (10,500
   tests would have to be rewritten), and Go's compile loop is too slow for
   the iterative orchestration scripts we run dozens of times per day.
   Rejected on test ergonomics + iteration speed.
3. **"Drop Go entirely, ship `cos` CLI as a Python tool"** — pip/uv
   distribution is a nightmare for end consumers who do not already manage a
   Python environment. The single-static-binary property is the entire
   reason `cos` exists in Go.
4. **"One big README section instead of an ADR"** — has no enforcement
   surface. Without an audit test attached, README guidance decays in
   weeks. Rejected because today's incident proves we need teeth, not
   suggestions.
5. **"Write a custom DSL that compiles to bash + Python + Go"** — the
   "wrapper language" anti-pattern called out above. Adds a fourth language
   that is invariably worse than the three it abstracts. Rejected on
   precedent.

## Verification

How we know the policy is working:

1. `tests/audit/test_python_naming.py` passes (shipped today). No
   hyphenated `*.py` files anywhere in `scripts/`, `lib/`, `tests/`,
   `packages/`.
2. **Phase 1 follow-up (tracked, not blocking this ADR)**: companion audit
   tests for bash naming (filenames kebab-case, function names snake_case)
   and Go (`gofmt -l` clean, package names lowercase).
3. `scripts/cos-init.sh` is identified in this ADR as a bash→Python
   migration candidate. It is **flagged**, not migrated. A future ADR or
   sprint ticket may decide to migrate it; this ADR only commits to making
   the candidacy visible.
4. No new hyphenated Python scripts merge to `main` (enforced by today's
   audit test).
5. The hook-chain RCA (engram `perf/hook-chain-rca-2026-04-24`) is
   referenced from the boundary-contract section so the next reviewer can
   trace the latency rule back to a real incident.

## Related

- `rules/python-naming.md` — sibling rule shipped today with the Python
  refactor.
- ADR-064 — Harness-agnostic Cognitive OS. The `cos` Go binary is part of
  the harness-agnostic future and is the canonical example of "Go for
  end-user distribution".
- ADR-058 — Phoenix observability. Example of Python owning the
  instrumentation layer where pytest + pydantic give us leverage.
- ADR-065 — Radar update curation pipeline. Python orchestration over
  bash glue, the canonical shape this ADR ratifies.
- Engram topic `perf/hook-chain-rca-2026-04-24` — root-cause analysis of
  today's 18s hook-chain incident.

## Open questions

1. **Should we audit `scripts/cos-init.sh` for migration to Python right
   now, or wait until it genuinely becomes hard to maintain?** The script
   meets two of the three Bash→Python triggers (length, parsing depth) but
   is not visibly broken. Default position: **wait**. Migrate when the next
   substantive change touches it, not on speculation.
2. **Do we want a 4th language** (e.g. Lua for Neovim plugin integration,
   TypeScript for a web dashboard)? **Default: NO without an ADR
   amendment.** Each new language is a 1× addition to onboarding cost; we
   already accept 3× and that is the ceiling.
3. **How do we handle JSON Schema files or pydantic models that SHOULD be
   shared between Python and Go?** Today there is no cross-language schema
   source of truth. Options for a future ADR: (a) JSON Schema as authority,
   both languages generate; (b) protobuf; (c) keep duplicating with a
   contract test. Not blocking this ADR, but the question is open.
4. **Should the bash naming audit test be written this sprint or next?**
   It is the most likely next drift event (kebab-case is bash's native
   convention so violations are subtler) but writing it requires deciding
   on edge cases (vendored scripts? generated files? `*.bash` extension?).
   Default: next sprint, ticket created.

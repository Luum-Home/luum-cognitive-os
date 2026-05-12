---
adr: 70
title: Convention Enforcement — From Documentation to Mechanism
status: proposed
implementation_status: planned
date: '2026-04-27'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit proposed status without accepted status
---

# ADR-070: Convention Enforcement — From Documentation to Mechanism

## Status

**Proposed** — 2026-04-27. Direct outcome of the
`bugfix/decision-triage-systemic-2026-04-27` engram observation. Pairs with
ADR-069 (research-first protocol), which this ADR amends in §7. The implementation
that triggered this codification shipped in commit `b7c33c2`.

## Context

On 2026-04-27 a single triage session surfaced three independent bugs that all
shared one root cause:

1. **Reports gitignored path bug.** ADR-069 §5 specified
   `.cognitive-os/reports/research/` as the canonical storage for research
   reports. The path was documented but never enforced — and `.cognitive-os/`
   is gitignored. Research agents wrote there, then duplicated to
   `docs/reports/` to make the artifact visible in PRs. Result:
   `/decision-triage` cross-referenced both copies and inflated the criticals
   count from 8 to 33.

2. **`decision/<topic>` convention not enforced.** ADR-069 §5 said operator
   decisions persist via "engram observation OR new ADR". The OR was
   ambiguous. When the easy branch ("ship a commit, move on") was chosen,
   nobody auto-created the `decision/<topic>` observation. The triage skill
   then could not see ANSWERED status and re-flagged decisions that had
   already been resolved.

3. **`from lib.engram import search` import bug.** `scripts/decision_triage.py`
   imported a module that does not exist (`lib/engram` vs the real
   `lib/engram_client`). Unit tests passed because they mocked the engram
   surface. The bug shipped silently — every cross-reference returned
   `engram_available=False` and the skill degraded to "no memory" mode without
   surfacing an error.

The shared meta-pattern: **a convention is real only when a mechanism enforces it.**
Documentation alone drifts because nobody re-reads the doc when they ship the
work. Mock-based unit tests miss live integration. ADR sections without a
matching audit test become aspirational.

The operator's framing in Spanish was direct: *"solucionemos todo y que hayan
tests por favor, end to end"*. Tests, not prose.

The fixes for the three specific bugs landed in commit `b7c33c2`. This ADR
codifies the **general** pattern so future conventions ship with their
enforcement instead of inheriting the same drift debt.

## Decision — The four enforcement patterns

Every new convention picks one or more of these four mechanisms. The pattern
chosen depends on what kind of drift the convention is trying to prevent.

| Pattern | What it catches | Mechanism | Example today |
|---|---|---|---|
| **A) Audit test scanning artifacts** | Documentation, rule, or ADR drift away from a canonical convention (paths, naming, frontmatter, required sections) | `tests/audit/test_X.py` decorated `@pytest.mark.audit`, walks all relevant files read-only, asserts pattern compliance. CI runs it on every PR. Includes a meta-test proving the detector would catch the regression if reintroduced. | `tests/audit/test_doc_paths_tracked.py` would catch `.cognitive-os/...` cited as canonical storage in any tracked doc |
| **B) Pre-commit linter for code-level invariants** | Bad code patterns at commit time — bad imports, unused vars, undefined names, ghost references | `.git/hooks/pre-commit` symlinked to a tracked `.githooks/pre-commit` running `ruff`/`eslint`/`gofmt -l` with **explicit** rule selection (e.g. `F401, F811, F821, F841` for Python). No magic defaults. | A pre-commit `ruff F821` would have caught `from lib.engram import search` before it landed |
| **C) Auto-execute the convention** | Convention "OR ambiguity" — when a rule offers two branches, humans default to the easier one and the harder branch is silently skipped | When the operator/orchestrator does action X, the convention's other branch happens **automatically**. Replace "do A OR B" with "always do A; B is optional and additional". | `scripts/backfill_session_decisions.py` + `--mark-answered` flag in `decision_triage.py` auto-create the `decision/<topic>` observation |
| **D) Live integration test, not mocks** | Silent fallbacks where the mocked path differs from the real path — degraded mode looks like success | `tests/integration/test_X_live.py` with `@pytest.mark.requires_X`. Skips when the dependency is unavailable, runs otherwise. CI runs the lane on schedule (nightly) or behind a flag. | A `test_decision_triage_engram_live.py` that imports the real `engram_client` and queries a real engram daemon would have caught Cause 3 immediately |

For each pattern: WHEN to apply, WHAT it costs, WHAT it prevents, the
ANTI-PATTERN it replaces.

### Pattern A — Audit test scanning artifacts

- **WHEN**: the convention constrains what is on disk — a path, a frontmatter
  field, a required section, a naming convention, a forbidden import.
- **COST**: ~30–80 lines of pytest per audit. Runs in seconds. Zero runtime
  cost (CI-only).
- **PREVENTS**: doc drift, ADR drift, rule drift. Catches "I forgot to update
  the doc when I changed the path".
- **REPLACES**: "the README says so" / "we agreed in ADR-XX" — neither
  enforces anything.

### Pattern B — Pre-commit linter for code-level invariants

- **WHEN**: the convention forbids a code construct or requires a code-level
  invariant (no ghost imports, no unused variables, no `panic("not
  implemented")`, no TODO in committed code).
- **COST**: one-time setup of `.githooks/pre-commit` (tracked) + symlink in
  `.git/hooks/`. Each developer runs `git config core.hooksPath .githooks` once.
  Per-commit cost: <2 seconds.
- **PREVENTS**: bugs that ship because tests mocked the broken surface.
  Catches the bug at the lowest possible blast-radius layer.
- **REPLACES**: trusting that "the test suite will catch it" — mocks defeat
  this assumption.

### Pattern C — Auto-execute the convention

- **WHEN**: the convention has an "OR" branch where both options are valid but
  one requires more work. Humans take the cheaper branch. The other branch
  silently rots.
- **COST**: a script + a CLI flag wired into the natural workflow. Usually
  ~50 lines of automation.
- **PREVENTS**: the silent rot of the harder branch. Removes the human
  discretion that creates drift.
- **REPLACES**: "remember to also create the engram observation" — humans
  forget; scripts do not.

### Pattern D — Live integration test, not mocks

- **WHEN**: the convention claims that two systems work together (skill ↔
  engram, hook ↔ settings, agent ↔ MCP server). Mocks lie about this
  category of claim.
- **COST**: an integration lane in CI with `requires_X` markers. Some setup
  per dependency (engram daemon spawn, fixture data). May add 30s–2min to a
  nightly run.
- **PREVENTS**: silent fallbacks. The kind of bug where everything looks
  green but the real integration is broken.
- **REPLACES**: "it works in the unit test" — unit tests with mocks are
  evidence about the contract, not the integration.

## Decision — When to apply each pattern

A short decision tree for any new convention or feature:

```
New convention introduced?
├── Does it constrain a file path / artifact location?  → Pattern A
├── Does it forbid a code construct?                    → Pattern B
├── Does it require a follow-up action?                 → Pattern C
└── Does it integrate with an external service?         → Pattern D
```

Most non-trivial conventions need **two or more** patterns. Examples:

- ADR-069's research-report path convention: needs Pattern A (audit walks
  doc/rule/ADR for the canonical path) **and** Pattern C (research skill
  auto-writes to that path, no operator-side choice).
- ADR-066's polyglot naming: Pattern A (audit scans filenames) is enough —
  no integration, no follow-up action.
- The `decision/<topic>` engram convention (this ADR §7): Pattern C (auto-
  execute via `--mark-answered`) **and** Pattern D (live integration test
  proving the observation actually lands in engram).
- A new MCP server: Pattern D (live integration test) is mandatory; Pattern A
  for any artifact paths it introduces.

If the answer is "none of the four", reconsider whether the convention is
real — or just a hope.

## Decision — Test taxonomy

Three test types. Each carries a different reliability tier for a different
class of claim. The convention: every claim that would FAIL silently if
unimplemented MUST have a HIGHEST-tier test.

| Type | When valid | Trust |
|---|---|---|
| **Mock unit test** | Fast, isolates pure-function logic from its dependencies. Useful for branching logic, parser correctness, formatting. | LOW for integration claims; HIGH for pure-function logic |
| **Audit test** | Walks artifacts on disk read-only, validates conventions across the whole repo. | HIGH for "no drift" claims |
| **Live integration test** | Exercises the real dependency (engram MCP, network, DB). Marked `requires_X`, skipped when unavailable. | HIGHEST for "actually works" claims |

The 2026-04-27 trio is a textbook illustration:

- Mock unit tests for `decision_triage.py` passed. They proved the
  parser worked. They did **not** prove the import was real.
- An audit test would have caught the gitignored-path documentation drift.
- A live integration test would have caught the missing import the moment it
  ran against a real engram daemon.

Mock tests are not wrong — they are insufficient on their own for any claim
that crosses a system boundary.

## Decision — Audit test contract

Every audit test under `tests/audit/test_X.py` MUST follow this contract:

1. Decorated `@pytest.mark.audit` so the lane is identifiable in CI.
2. Walks the relevant files read-only — never writes, never mutates.
3. Includes at least one **anti-pattern detector meta-test**: writes a fake
   ghost violation to a temp file, runs the audit, expects FAIL, removes the
   temp file. This proves the detector actually detects.
4. Documented in the commit message and in `tests/audit/README.md` (which
   this ADR proposes to create — Phase 3).
5. Failure messages name the specific file and line where the drift was
   found. "drift detected" is not enough.

The meta-test point is load-bearing: an audit that cannot fail is theatre.

## Decision — `decision/<topic>` engram convention (amends ADR-069 §5)

ADR-069 §5 currently reads:

> Operator decisions persist via engram observation OR new ADR.

This ADR amends it to:

> Every operator-accepted decision MUST create a `decision/<topic_key>`
> engram observation. A new ADR is **optional and additional** for
> high-level architectural decisions. The orchestrator (or the
> `--mark-answered` CLI on `decision_triage.py`) is the auto-execution
> point — operators do not maintain engram by hand.

This is a patch-amendment to ADR-069, not a re-write. ADR-069 §1–4, §6–14
remain unchanged. The amendment is mechanical: replace ambiguity with a
hard rule + Pattern C automation.

## What we replicate / what we don't

**Replicate going forward:**

- Every new convention ships with its enforcement mechanism. The four
  patterns above are the menu.
- `templates/agent-research-only.md` updates to require an "Enforcement
  Mechanism" section in every research report — the report cannot land
  without naming Pattern A/B/C/D.
- `rules/research-first-protocol.md` Phase 0 deliverable list adds
  "enforcement mechanism" alongside the existing "scope, risks,
  recommendations".

**Do NOT replicate:**

- Retroactive backfill of audit tests for every existing convention in the
  repo. There are dozens. The cost is unjustified absent a regression
  incident. Apply on-demand.
- Pattern D (live integration tests) for every external dependency.
  Reserve for the surfaces where mock-vs-real divergence has burned us
  before (engram, MCP servers, the LLM dispatch layer).
- Replacing existing mock-based tests with integration tests wholesale.
  Mock tests remain valid for pure logic; the rule is "add the integration
  tier" not "delete the mock tier".

## Implementation phases

| Phase | Scope | Status |
|---|---|---|
| 1 | Codify the four patterns (this ADR) | Proposed |
| 2 | Backfill audits for the three bugs that triggered this ADR (gitignored path, missing observation, ghost import) | Done in commit `b7c33c2` |
| 3 | Create `tests/audit/README.md` documenting the audit test contract from §6 | Proposed |
| 4 | Update `rules/research-first-protocol.md` so Phase 0 deliverable includes "enforcement mechanism" | Proposed |
| 5 | Future bugs matching this meta-pattern get classified `type: convention-gap` in their RCAs | Living |

## Consequences

**Positive:**

- Convention drift becomes visible at PR time, not at incident time.
- Mock-test false confidence is cured for integration claims.
- Every new convention ships with its own enforcement; the cost is paid
  once by the author, not N times by every downstream consumer that
  rediscovers the drift.

**Negative:**

- Every new convention now requires more upfront thinking and test code.
  Roughly 2x the lines per convention, concentrated in CI-only artifacts.
- Live integration tests (Pattern D) introduce CI flakiness if the
  dependency is unstable. The `requires_X` skip pattern mitigates but
  does not eliminate this.
- Authors must learn the four-pattern menu. There is a one-time
  onboarding cost.

**Neutral:**

- Pure CI/test-time enforcement. No runtime behavior changes.
- Backwards compatible — existing conventions without enforcement are
  not broken, just unprotected.

## Alternatives rejected

1. **Trust documentation alone.** This is the status quo that produced the
   2026-04-27 trio. Rejected by evidence.
2. **Code review catches it.** Humans miss subtle drift, especially in
   conventions established months ago. Does not scale to N reviewers across
   M projects.
3. **Run a global audit weekly.** Too late — the drift has already shipped
   and downstream consumers have already diverged. CI on every PR is the
   right cadence.
4. **External policy engine (Conftest, Open Policy Agent, Semgrep rules).**
   Overkill for our scale. Pytest audit tests are zero-dependency, fast,
   and live next to the code they protect. We already have the infrastructure.
5. **Generate enforcement automatically from the convention text.** Tempting
   but speculative. NLP-driven enforcement would itself need enforcement.
   Rejected as recursion.

## Verification

The ADR is verified by the following commands:

```bash
test -f docs/adrs/ADR-070-convention-enforcement-mechanism.md
wc -l docs/adrs/ADR-070-convention-enforcement-mechanism.md
grep -c "^## " docs/adrs/ADR-070-convention-enforcement-mechanism.md
grep -c "^|" docs/adrs/ADR-070-convention-enforcement-mechanism.md
```

Acceptance:

- File exists at the canonical path.
- Length between 280 and 400 lines.
- ≥14 `## ` sections present.
- Tables present (≥4 rows for the four-pattern table, ≥3 rows for the
  taxonomy table).
- The §3 four-pattern table has exactly four rows mapping to Pattern A/B/C/D.
- The §4 decision tree covers all four patterns.
- The §5 test taxonomy lists three tiers.
- §11 lists ≥4 alternatives rejected.
- The §7 amendment to ADR-069 §5 is concrete, with quoted before/after text.

## Related

- `bugfix/decision-triage-systemic-2026-04-27` (engram observation) — the
  trigger for this ADR.
- ADR-069 — research-first protocol (this ADR amends §5).
- ADR-067 — frontmatter defense-in-depth (precedent for the
  template+hook+audit pattern).
- ADR-066 — polyglot language boundaries (Pattern A precedent for naming
  conventions enforced via audit tests).
- Commit `b7c33c2` — the implementation that shipped the three Phase 2 fixes.

## Open questions

1. Should audit tests be mandatory for **all** new ADRs, or only those that
   introduce conventions? Default proposal: only conventions; pure analysis
   ADRs (post-mortems, rationale-only) can skip. Operator confirms before
   we make it a hard rule.
2. How do we track "convention-enforcement gap" RCAs over time without
   adding bookkeeping overhead? Proposal: add a `type: convention-gap` tag
   in engram observations and let the existing search surface drive the
   retrospective.
3. Live integration tests with `requires_X` markers — should CI run them
   on every PR or skip to a nightly lane? Proposal: skip in the fast PR
   lane, run nightly. Re-evaluate after the first month of nightly data.
4. Does Pattern C (auto-execute) risk hiding the convention from the
   operator? If `--mark-answered` happens silently, do we still need a
   visible audit log entry? Proposal: yes — every auto-execution emits a
   line to `.cognitive-os/metrics/convention-auto-exec.jsonl`.

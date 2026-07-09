# Proposal: `cos-lib-package-rename`

- **Change:** `cos-lib-package-rename`
- **Phase:** propose (intent, scope, approach — no implementation in this artifact)
- **Repo:** luum-cognitive-os (SOURCE)
- **Date:** 2026-07-09
- **Supersedes:** N/A
- **Depends on:** `hook-lib-projection-contract` (merged to main: `6a0971910..7afca9351`) —
  this change resolves the risk that design's §7 flagged and deferred, then §8 later
  re-opened as "chosen" without an implementation artifact.
- **Evidence base:** `docs/06-Daily/reports/cos-lib-rename-dryrun-2026-07-08.md` (measured
  dry-run manifest, ground truth for all counts in this proposal); `scripts/cos_lib_rename_codemod.py`
  (deterministic codemod, dry-run validated, `--apply` not yet run); Engram topic
  `sdd/hook-lib-projection-contract/cos-lib-rename-codemod` (#30238).

---

## 1. Problem

`hook-lib-projection-contract` (merged) fixed the *installer-side* defect where projected
hooks `import lib.*` but the installer never shipped a `lib/` package to consumers. Its
fix — dependency-closure projection (option b) + a fail-open backstop (option d) — makes
the missing-`lib` case degrade to a silent no-op instead of a false `exit 2` block. That
design's own §7 flagged a **residual, unmitigated risk (U1): namespace collision.** If a
consumer repo has its **own** top-level `lib/` package, and `cwd` (the consumer root)
precedes the projected `PYTHONPATH` entry in Python's `sys.path` resolution order, the
consumer's `lib` **shadows** ours. Every projected hook that does `import lib.<module>`
silently resolves to the *consumer's* `lib/`, not COS's.

**Why the fail-open backstop is not a sufficient fix, only a bandage:**

1. **It hides the collision instead of resolving it.** Fail-open converts a `ModuleNotFoundError`
   (or a wrong-module import) into a silent no-op. That is correct behavior for the *previously
   missing* case, but for the *shadowed* case the import may not even raise — a consumer `lib/`
   with a same-named submodule (or one that raises a different, unrelated exception) can produce
   **wrong behavior**, not just no-op behavior. Fail-open only catches the exceptions it
   anticipates; it cannot catch "imported the wrong module and got plausible-looking wrong data."
2. **It converts an already-fragile feature set into a permanently degraded one.** Every hook
   whose `lib.*` import collides silently loses its feature (rate limiting, trust-score parsing,
   confidentiality scanning, queue drain, memory prefetch, phase context, telemetry) with **no
   signal to the operator** that governance is degraded. This is silent, not observable,
   degraded governance — the exact failure mode `hook-lib-projection-contract` was created to
   eliminate, just moved one layer down.
3. **Frequency is measured as unknown, not low.** The design's own §7 language is explicit:
   "not observed in the empty-sandbox probe... its real-world frequency is **unmeasured**."
   A production consumer with a `lib/` directory (a common top-level name for Python projects)
   is not a hypothetical; it is untested, not absent.
4. **It was explicitly deferred, not resolved, by the design that first identified it** — §7's
   own text names the durable fix ("rename the shipped package to a namespaced `cos_lib`") and
   defers it "because it re-introduces the 84-file edit cost this design exists to avoid." That
   cost estimate is now obsolete: a deterministic codemod (built and dry-run validated in this
   session) removes the manual-edit cost the deferral was reacting to.

The durable fix — eliminate the shared name `lib` entirely by renaming the shipped package to
`cos_lib` — removes the collision at the root: no consumer top-level directory is plausibly
named `cos_lib`, so there is nothing left to shadow. This proposal is that fix.

## 2. Approach

**Atomic package rename via deterministic codemod**, not a hand-edit campaign.

- **Tool:** `scripts/cos_lib_rename_codemod.py` — already built and dry-run validated this
  session (uncommitted, no source mutated). Dry-run is the default; `--apply` is required to
  mutate, `--json` for machine output, `--revert` swaps OLD/NEW for a symmetric rollback.
- **Mechanism:** AST-aware rewriting for `.py` (walks `Import`/`ImportFrom` nodes, confirms
  before editing), boundary-anchored regex for `.sh`/embedded Python
  (`(?<![A-Za-z0-9_.])lib(?=\.)` + `from lib import` + `-m lib.`), a **module allowlist** of
  373 real top-level `lib/` module names (so `lib.telegram`-style references that actually
  resolve to the *separate* `workflows/lib/` package are correctly refused, not rewritten), and
  a **protected-config guard** that refuses to write `hooks/`, `rules/`, `skills/`, `.claude/`
  without `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` — those files are listed so a single guarded
  env-session performs them atomically alongside everything else.
- **Measured blast radius (dry-run manifest, ground truth):**

  | Metric | Count |
  |---|---|
  | Total files to change | **902** |
  | Total import lines to change | **1854** |
  | Unguarded files / lines | 808 / 1705 |
  | **GUARDED** files (need `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`) | **94** |
  | GUARDED lines | 149 |
  | RISKY / correctly-refused edge cases | **47** |
  | String/path refs (enumerated, human-judgment required) | **125** |
  | Symlinks in `lib/` (no target rewrite needed) | **73** |

- **Idempotent + reversible:** a second pass on already-rewritten code is a no-op
  (`from cos_lib.foo import x` is left untouched). Revert = `git mv cos_lib lib` +
  `cos_lib_rename_codemod.py --revert --apply` (regex forward/reverse verified symmetric).
  The codemod never performs `git mv` itself — even under `--apply` the directory move is an
  explicit operator step, so an aborted run cannot leave a half-moved package.
- **Safety probe (19/19 pass):** boundary-anchored matcher correctly leaves `pathlib` (2848
  hits repo-wide), `zlib`, `glob`, `joblib`, `library`, `mylib.foo`, `a.lib`, `lib_path`,
  `self.lib`, `{'lib': 1}`, `foo_lib` untouched, while rewriting `from lib.foo import x`,
  `import lib.bar`, `from lib import baz`, `python3 -m lib.mod`, and split-token
  `["-m", "lib.session_lifecycle"]`.

This is a mechanical, already-validated rename, not new tooling — the design work is done;
this proposal governs the *decision to apply it* and the residual triage it requires.

## 3. Scope

Per-directory breakdown, measured by the codemod dry-run (§2 of the dry-run manifest):

| Directory | Python importer files | Notes |
|---|---|---|
| `tests` | 480 | Largest surface; not protected-config guarded |
| `scripts` | 153 | Not guarded |
| `lib` | 134 | Self-imports within the package being renamed; not guarded |
| `packages` | 42 | Package-internal `lib/*.py` module bodies behind symlinks; not guarded |
| `workflows` | 14 | **Untouched** — see §5 RISKY disposition |
| `hooks` (`.sh`) | 82 | Subset of the 94 GUARDED files; requires env-session |
| `mcp-server` | 1 | Not guarded |

Additionally in scope: **73 symlinks** in `lib/` (files live in `lib/`, point via relative
`../packages/*/lib/<mod>.py` into package-internal dirs — targets stay valid under `git mv`
since `packages/` is a sibling of both `lib/` and `cos_lib/`; no target rewrite needed, but the
57 module bodies behind those symlinks that do `from lib.<mod>` **are** rewritten so they
resolve correctly once loaded as `cos_lib.<mod>`), and **14 string/path refs** in real
package-dir resolvers (`lib/pattern_detector.py:228`, `lib/reinvention_guard.py:55`,
`lib/wiring_validator.py:181`, `packages/sdd-compound/lib/system_graph.py:233`,
`packages/verification-audit/lib/orchestrator_verify.py:40`, `scripts/aspirational_audit.py:299`,
`scripts/check_lib_wiring.py:85`) that literally resolve a directory named `lib` and must
become `cos_lib`, distinguished from the other 111 string refs (mostly `tests/` fixtures named
`lib` for unrelated reasons) that must **not** change.

**Explicitly out of scope:** `workflows/lib/` (separate vendored ADW package, keeps its name —
see §5), package-internal `packages/*/lib/` directories (not renamed, only their module bodies'
internal imports are rewritten), and the installer/bootstrap surface from
`hook-lib-projection-contract` (already merged; this proposal changes *what* it projects —
`cos_lib/` instead of `lib/` — not *how* it projects).

## 4. Alternatives rejected

| Alternative | Why rejected |
|---|---|
| **(a) Fail-open only** (ship the merged `hook-lib-projection-contract` backstop, do nothing further) | Already adopted as a first layer; insufficient alone per §1 — converts a false block into a silent, unobserved feature loss, and its own design explicitly named this as a deferred bandage, not a fix. Frequency of the collision is measured as unknown, not low. |
| **(b) `PYTHONPATH` prepend / `sys.path` reordering** (force the projected COS `lib/` ahead of the consumer's `cwd`-derived `lib/` in resolution order) | Fixes the collision direction but not the root cause; a consumer script that itself does `import lib.foo` expecting **its own** package would now silently get **ours** instead — inverts the bug rather than removing it. Also fragile: `sys.path` ordering depends on harness-specific invocation details (ADR-008 portability risk), unlike a rename which is invocation-agnostic. |
| **(c) Vendored subpath** (e.g. ship as `cognitive_os.lib` or nest under a namespace prefix without touching the 902 existing importers, using a compatibility shim) | Requires a compatibility shim maintained indefinitely, and does not remove the collision for any consumer whose own package happens to collide with the *chosen* namespace prefix — just moves the problem instead of eliminating it. Also leaves two coexisting import surfaces (`lib.*` internally, `cognitive_os.lib.*` for consumers) which is a larger long-term maintenance surface than one clean rename. |
| **(d) Manual 84-file (or 902-file) hand-edit campaign** | This is what the original design deferred the fix *for* — manual edit cost across 902 files/1854 lines is precisely the blast radius a deterministic codemod exists to absorb safely. Rejected as strictly worse than the chosen option once the codemod exists and is dry-run validated. |

**Chosen: atomic rename via the already-built, dry-run-validated codemod** (§2). It is the
only option that removes the collision at the root (no shared name to shadow), requires no
indefinite compatibility shim, and has a bounded, already-measured blast radius with a verified
reversal path.

## 5. Risks

| ID | Risk | Mitigation |
|---|---|---|
| **R1** | **Partial apply** — the codemod refuses to write the 94 GUARDED (`hooks/`) files without `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`; running `--apply` without that env var leaves 94 files un-rewritten while 808 others change, which the codemod's own doc-comment states explicitly leaves the repo **BROKEN** (hooks still `import lib.*` after `lib/` no longer exists). | Apply phase MUST run as a single guarded env-session (`COS_ALLOW_PROTECTED_CONFIG_WRITE=1`) covering both the guarded and unguarded edits plus the `git mv lib cos_lib` in one atomic commit/session — never split across sessions. Tasks phase must sequence this as one unit, not batched across the guard boundary. |
| **R2** | **Consumer mid-transition** — installed consumers that projected the old `lib/`-based hooks before this change lands will have stale projected hooks referencing `lib.*` while the SOURCE repo now ships `cos_lib.*`; a consumer that re-runs `cos init` mid-transition on a half-merged branch could get an inconsistent mix. | Land on a single feature branch, merge atomically (no intermediate main-branch state where SOURCE hooks reference `lib` but package is `cos_lib` or vice versa). Document a "re-init required" upgrade note per the merged `hook-lib-projection-contract` migration pattern (§6 of that design). |
| **R3** | **Guarded file miscount or drift** — the 94-count is itself a delta from an 82 grep-estimate (codemod catches split-token and package-level cases grep misses); if new hooks are added between dry-run (2026-07-08) and apply, the guarded set could grow and be missed if apply reuses a stale dry-run list instead of re-running. | Apply phase MUST re-run `cos_lib_rename_codemod.py --json` fresh immediately before `--apply` (not reuse this dry-run's file list) so the guarded/unguarded partition reflects the tree at apply time. |
| **R4** | **RISKY edges (47) misclassified** — all 47 are `workflows/*.py` importing `workflows/lib/*` (a separate vendored package); if the module allowlist (373 names) has a gap, a genuine COS `lib.*` import inside `workflows/` could be silently left un-rewritten instead of flagged, since RISKY items are explicitly *not* auto-rewritten and require human sign-off before the apply phase proceeds. | Apply/verify phase must re-confirm (per the dry-run manifest §4 disposition) that none of the 47 flagged names resolve to a real top-level `lib/` module — i.e., re-run the "confirm no COS `lib.*` import hides among them" check as an explicit verify-phase gate, not assume the dry-run's finding still holds if `workflows/` changes before apply. |
| **R5** | **String/path refs (125) left inconsistent** — these are enumerated, not auto-rewritten, because distinguishing "path to THE package" from "a fixture dir named lib" needs human judgment; if only some of the 14 real package-dir resolvers are updated (e.g. `lib/wiring_validator.py:181`) while others are missed, path resolution silently breaks only for the missed one(s), likely surfacing as a hard-to-trace `FileNotFoundError` well after apply. | Design/tasks phase must enumerate the exact 14 real-resolver refs (already listed in dry-run manifest §5) as individual, checked-off apply tasks — not a single "handle string refs" catch-all task — so each is independently verifiable. The 111 test-fixture refs should be spot-checked (sample) to confirm none are load-bearing package-dir resolvers mislabeled as fixtures. |

## 6. Success metrics

Grep-verified, machine-checkable assertions (run from repo root after apply):

1. **No residual old-package imports:**
   `grep -rE '(?<![A-Za-z0-9_.])lib(?=\.)|from lib import' --include='*.py' --include='*.sh' . | grep -v 'workflows/lib' | wc -l` → **0** (excluding the intentionally-untouched `workflows/lib/` surface).
2. **New-package imports present at the measured count:**
   `grep -rE '(?<![A-Za-z0-9_.])cos_lib(?=\.)|from cos_lib import' --include='*.py' --include='*.sh' . | wc -l` → **902** files touched / **1854** import-line total (matching the dry-run's measured totals — a mismatch signals apply drifted from the validated dry-run).
3. **Regression tests green:** the full test suite (`tests/audit`, `tests/unit`, `tests/integration`) exits 0 post-rename, including the existing `hook-lib-projection-contract` regression test (`tests/audit/test_hook_lib_projection.py` per that design's §5.4) re-targeted at `cos_lib`.
4. **Consumer isolation confirmed:** a fresh `cos init --full` into a temp consumer sandbox that itself contains a top-level `lib/` directory succeeds with no import collision — `python3 -c "import cos_lib.confidentiality_scanner"` resolves the COS module even when a same-named-but-different `lib/` exists in the consumer root (the U1 regression case this whole change exists to close).
5. **Idempotency confirmed:** re-running `cos_lib_rename_codemod.py --json` after apply reports 0 further edits (proves the rewrite is complete and idempotent, not partially applied).

## 7. Open questions for design phase

- **U-Q1 — Atomic vs. batched apply.** Should the apply phase be a single all-at-once
  `--apply` run (simplest, matches the codemod's atomicity guarantee) or should it be batched
  by directory (e.g. `lib/` + `packages/` first, `tests/` + `scripts/` second, guarded `hooks/`
  last) to make an interrupted apply easier to diagnose? R1 argues for atomic; large diff size
  (902 files) argues for reviewability in batches. Design must pick one and state why.
- **U-Q2 — RISKY-edge (47) disposition sign-off.** Is "leave `workflows/` untouched, confirmed
  no COS `lib.*` hides among them" (dry-run manifest §4) accepted as final, or does design want
  an explicit automated assertion (not just narrative confirmation) added to the regression
  test so a future `workflows/` change can't silently reintroduce a missed COS import?
- **U-Q3 — String/path refs (125) subset for apply.** Confirm the exact task-level breakdown
  of the 14 real-resolver edits (§5 R5) versus the 111 fixture refs — does design want a
  scripted check (e.g. AST-adjacent heuristic) to catch any 15th real resolver the dry-run
  missed, or is the enumerated list treated as complete and closed?
- **U-Q4 — Rollback strategy under partial failure.** If apply fails partway (e.g. guarded
  session interrupted after unguarded edits land but before `git mv` + guarded edits), what is
  the operator recovery path — full `git reset --hard` to pre-apply, or a documented resume
  procedure that re-runs the codemod against the partial state? The codemod's `--revert` flag
  assumes a *completed* forward apply; a partial-forward state is a different recovery case
  design should address explicitly.
- **U-Q5 — Consumer migration UX.** Beyond the "re-init to receive lib projection" note already
  planned for `hook-lib-projection-contract`, does this rename warrant its own upgrade-note
  addendum (since the package name itself changes, not just what's projected), and should
  `cos init` detect and warn on stale `lib/`-referencing consumer state from a pre-rename
  install?
- **U-Q6 (carried, not resolved here) — Pre-existing `cos_lib` tooling reconciliation.** Engram
  topic #30238 notes the repo already contains `cos_lib_symlink_invariant_audit.py` and
  `test_lib_symlink_invariant.py` — prior tooling using the `cos_lib` name ahead of this rename
  — that was not reconciled against this codemod during the dry-run session. Design phase must
  confirm these do not assume a different `cos_lib` layout/semantics than what this rename
  produces, and update or fold them in as needed.

## 8. Estimated effort

**One SDD-apply session**, guarded env pre-exported
(`COS_ALLOW_PROTECTED_CONFIG_WRITE=1`) for the entire session so the atomic pass (unguarded +
guarded + `git mv`) runs without a mid-session guard gap (R1). Scope is mechanical
(codemod-driven) rather than exploratory — the codemod is already built and dry-run validated,
so apply-phase work is: (1) re-run dry-run fresh (R3), (2) execute `git mv lib cos_lib` +
`--apply` in the guarded session, (3) hand-resolve the 14 real string/path refs (§5 R5), (4)
re-run full test suite + the consumer-isolation check (§6.4), (5) commit. No new tooling
required; effort is dominated by the guarded-session discipline and the §6 verification pass,
not by algorithm design.

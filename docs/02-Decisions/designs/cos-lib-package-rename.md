# Design: `cos-lib-package-rename`

- **Change:** `cos-lib-package-rename`
- **Phase:** design (resolves U-Q1..U-Q6 from the proposal; no implementation here)
- **Repo:** luum-cognitive-os (SOURCE)
- **Date:** 2026-07-09
- **Inputs:** `docs/02-Decisions/proposals/cos-lib-package-rename.md` (proposal, §7 open
  questions), `docs/06-Daily/reports/cos-lib-rename-dryrun-2026-07-08.md` (dry-run manifest,
  ground truth for all counts), `scripts/cos_lib_rename_codemod.py` (codemod, read in full),
  `docs/02-Decisions/designs/hook-lib-projection-contract.md` §7-8 (U1 origin + prior sign-off).

---

## 1. U-Q1 — Atomic vs. batched apply

**Decision: atomic, single `--apply` pass in one guarded env-session. Rejected: directory
batching.**

Justification:

1. **The codemod does not support `--batch`.** Reading `scripts/cos_lib_rename_codemod.py`
   `main()`: the only mode flags are `--apply`, `--json`, `--revert`, `--root`. There is no
   per-directory filter. Batching would require either (a) running the codemod repeatedly with
   a hand-added `--only-dir` filter that does not exist today (new tooling, out of scope per the
   proposal's "no new tooling required" framing), or (b) manually partitioning `git diff` hunks
   post-hoc, which reintroduces exactly the manual-edit risk the codemod exists to remove.
2. **R1 (proposal §5) is explicit that a partial apply is BROKEN, not partially-working.**
   `apply_edits()` refuses guarded files without the env var; if unguarded directories
   (`tests/`, `scripts/`, `lib/`, `packages/`) are rewritten in one batch and `hooks/` in a
   second, the repo sits in a broken intermediate state between the two commits — every hook
   still does `import lib.*` against a package that (once `git mv lib cos_lib` runs) no longer
   exists at that path. Batching does not make recovery easier; it manufactures a guaranteed
   broken commit on `main` (or the working branch) between batches.
3. **The "902 files argues for reviewability" concern (proposal §U-Q1) is addressed by review
   granularity, not apply granularity.** The diff is large but mechanical and homogeneous
   (`lib.X` → `cos_lib.X` substring rewrite); a reviewer diffs by directory in the PR view
   without the *apply* itself being split. Splitting the apply buys no additional safety over
   splitting the *review*.
4. **Partial-recovery framing is inverted.** Batching by guardedness only ever produces two
   states: (a) not-yet-guarded-batch-applied (fully revertible via `git reset`), or (b)
   guarded-batch-applied-on-top-of-broken-unguarded-batch (a state design must never allow to be
   committed). There is no intermediate state that is *both* committed and *working* — so
   batching purchases no partial-recovery benefit that a single atomic commit does not already
   have via `git revert` (§U-Q4).

**Apply recipe (single guarded session, per dry-run manifest §9):**

```bash
git checkout -b chore/cos-lib-rename
COS_ALLOW_PROTECTED_CONFIG_WRITE=1   # exported once, for the whole session
python3 scripts/cos_lib_rename_codemod.py --json > /tmp/cos-lib-rename-fresh-manifest.json  # R3: re-run fresh, do not reuse the 2026-07-08 dry-run
git mv lib cos_lib
python3 scripts/cos_lib_rename_codemod.py --apply
# hand-resolve the 14 (+1, see U-Q6) real string/path resolvers
# hand-resolve the cos_lib_symlink_invariant_audit.py + test reconciliation (U-Q6)
# run full test suite + consumer-isolation check (§6.4)
git add -A && git commit -m "..."   # ONE commit
```

---

## 2. U-Q2 — 47 RISKY edges disposition

**Decision: accept the dry-run's "leave untouched" finding as correct, but do not accept
narrative confirmation alone as final — add one automated regression assertion.**

All 47 share one root cause (dry-run §4): `workflows/*.py` doing `from lib.<mod> import ...`
where `<mod>` ∈ `{telegram, shared_phases, utils, agent, data_types, file_parser, ...}` resolves
to the separate, vendored `workflows/lib/` package, not the COS package under rename. Grouped
by pattern, all 47 are the *same* pattern (import-from-foreign-package), not 47 distinct cases —
this is a single disposition applied uniformly, not 47 individual judgment calls.

| Disposition | Count | Action |
|---|---|---|
| **skip (leave as `lib.*`, correct as-is)** | 47/47 | No edit. `workflows/lib/` keeps its own name; these imports are already correct for that package. |

**Required automated gate (closes the "narrative-only" gap the proposal flagged):** extend
`tests/audit/test_hook_lib_projection.py` (or add a sibling
`tests/audit/test_workflows_lib_isolation.py`) with an assertion that:

```python
# For every `from lib.<mod> import` in workflows/*.py, <mod> must NOT be a member of the
# cos_lib module allowlist (the same 373-name set scripts/cos_lib_rename_codemod.py computes
# via load_allowlist()). If any workflows/ import's <mod> IS a real cos_lib module, fail —
# a future workflows/ change silently reintroduced a missed COS import (the R4 regression).
```

This reuses `load_allowlist()` from the codemod directly (importable, no new logic) rather than
re-deriving the module list — one source of truth for "what is a real `cos_lib` submodule."
Task: **T9** (see §7 DAG).

---

## 3. U-Q3 — 125 string/path refs: auto-rewrite vs. manual subset

**Decision: 0 of the 125 are auto-rewritten. All resolve via manual review, but the review set
splits into two enumerable buckets with different sign-off requirements. A 15th real resolver,
missed by the dry-run's own heuristic, is identified below and MUST be added to the manual list
before apply.**

**Concrete criteria for "safe to auto-rewrite" (checked against the codemod's `RE_PATH_STRING`
matcher): NONE of the 125 qualify**, because every one is a bare string literal `"lib"` — there
is no boundary-anchoring possible for a 3-character string that also validly means "a directory
named lib for unrelated reasons" (test fixtures). Auto-rewriting bare string literals has no
AST-level confirmation path (unlike `import`/`from` statements, which `ast.parse` disambiguates
structurally) — a purely lexical match on `"lib"` cannot distinguish `Path(x) / "lib"` (package
resolver) from `(tmp_path / "lib").mkdir()` (throwaway fixture name). This is exactly why the
codemod enumerates rather than edits this bucket, and design does not overturn that call.

**Manual subset — Bucket A: real package-dir resolvers (dry-run §5), MUST be edited, individual
tasks:**

| # | File:line | Task |
|---|---|---|
| 1 | `lib/pattern_detector.py:228` | T5 |
| 2 | `lib/reinvention_guard.py:55` | T5 |
| 3 | `lib/wiring_validator.py:181` | T5 |
| 4 | `packages/sdd-compound/lib/system_graph.py:233` | T5 |
| 5 | `packages/verification-audit/lib/orchestrator_verify.py:40` | T5 |
| 6 | `scripts/aspirational_audit.py:299` | T5 |
| 7 | `scripts/check_lib_wiring.py:85` | T5 |
| 8 | `tests/contracts/test_orchestrator_verify.py:40` | T5 |
| 9 | `tests/hooks/test_aspirational_audit_weekly.py:42` | T5 |
| 10 | `tests/integration/test_aspirational_audit.py:38` | T5 |
| 11 | `tests/unit/test_pattern_detector.py:29-30` | T5 |
| 12 | `tests/unit/test_system_graph.py:92` | T5 |
| 13 | `tests/unit/test_wiring_validator.py:24` | T5 |

(13 files / 14 lines per dry-run §5 count — `tests/unit/test_pattern_detector.py` has 2 lines.)

**Bucket A+1 — a 15th real resolver the dry-run's own heuristic missed (finding, see §8):**
`scripts/cos_lib_symlink_invariant_audit.py:128` — `lib_dir = repo / "lib"`. This line resolves
the package directory by literal name exactly like the 14 above, but the codemod's string-ref
matcher only flags a `"lib"` literal when the line also contains `sys.path`, `PYTHONPATH`, or the
substring `path` (case-insensitive) — `lib_dir = repo / "lib"` contains none of those (the
variable is named `lib_dir`, not `*_path`), so it silently fell outside the enumerated 125/14.
Added to T5 as item 14; see §6 for why this specific miss matters.

**Bucket B — 111 test-fixture refs, spot-check only (R5's own recommendation), not
individually tasked:** sample-verify (proposal R5 mitigation) that none are load-bearing
package-dir resolvers mislabeled as fixtures. Task **T6**: spot-check a stratified sample (all
`tests/hooks/*`, `tests/integration/*`, plus 10 random `tests/unit/*` hits) — if any sampled hit
turns out to be load-bearing, escalate to a full manual pass over the remaining 111−sample.

**Scripted-check question (proposal U-Q3, second half):** design adopts a **narrow** scripted
check rather than a broad AST heuristic: extend the codemod's `RE_PATH_STRING` string-ref
matcher (§8 finding) to also flag any line containing `= .* / "lib"` or `os.path.join(\1, "lib")`
even without the `path`/`sys.path`/`PYTHONPATH` keyword gate, re-run `--json`, and diff the new
count against 125+1. Any *new* hits beyond the 15 already enumerated here get manual triage
before apply proceeds (task **T5b**, gate before T7).

---

## 4. U-Q4 — Rollback strategy

**Decision: `git revert` of the single atomic commit is primary. Manual `git checkout HEAD~ --
<paths>` is the documented resume path for the one failure mode `--revert` cannot handle
(partial-forward apply). The codemod's own `--revert` flag is NOT the primary rollback
mechanism — it is a secondary tool for a narrower case.**

| Option | When it applies | Verdict |
|---|---|---|
| **(a) `git revert <sha>`** | Apply committed successfully (single atomic commit per §1) | **Primary.** Full working-tree revert, symmetric with how the change landed, no dependency on the codemod script's own correctness at revert time (revert uses git's own diff inverse, not the codemod's `--revert` regex path). Works even if the codemod script itself is deleted/changed later. |
| **(b) codemod `--revert --apply`** | Only after `git mv cos_lib lib` has already re-run, on a repo where the rename is the *last* thing that happened to those files | Secondary/informational only. Proposal's own dry-run manifest §8 states this "assumes a *completed* forward apply" — it is not a general-purpose rollback, it is the forward pass run backwards. Useful for verifying regex symmetry (already done, 19/19 probe), not as an operational rollback command post-commit. |
| **(c) `git checkout HEAD~ -- <paths>`** | **Partial-forward failure**: the guarded env-session was interrupted after `git mv` + unguarded edits landed in the working tree but before the commit closed (i.e., nothing has been committed yet) | **Documented resume/abort path for the one gap `--revert` doesn't cover.** Because §1 mandates the *entire* apply (mv + unguarded + guarded edits) happen before the single commit, an interruption here is **still uncommitted** — the correct recovery is `git reset --hard` (or `git clean -fd` for the moved directory) to the last commit, **not** a partial `checkout HEAD~ -- <paths>` restore of individual files, since nothing has been partially committed to restore *from* per-path. Design correction to the proposal's U-Q4 framing: because apply is atomic-before-commit (§1), there is no partial-*commit* state to resume from — only a partial-*working-tree* state to discard. |

**Recommendation: for any failure during the guarded session (before the commit), abort with
`git reset --hard <last-good-commit>` (working tree only touched, nothing committed yet — safe).
For any defect discovered after the commit lands, `git revert <sha>`.** This resolves the
proposal's open question directly: `--revert` on the codemod is not the operator-facing rollback
tool; `git revert` is. Document both paths in the apply-phase task list (**T11**).

**Edge case:** if `git mv lib cos_lib` has run but the codemod `--apply` step fails partway
through file writes (e.g., disk full, permissions), `cos_lib/` exists with some files rewritten,
`lib/` no longer exists, and nothing is committed. Recovery: `git status` shows `cos_lib/` as an
added/renamed path and modified files — `git reset --hard` still cleanly discards all of it back
to the pre-apply commit, because git tracks the rename as an uncommitted working-tree change,
not as history. No special-casing needed beyond "reset before you commit."

---

## 5. U-Q5 — Consumer migration UX

**Decision: this rename warrants its own upgrade-note addendum (not folded silently into the
`hook-lib-projection-contract` note), and `cos init` SHOULD detect + warn on stale
`lib/`-referencing consumer state — but as a follow-on task, not a blocker for this SDD's
apply.**

**Impact analysis:**

- **16 registered consumers** (per `hook-lib-projection-contract` design §2: "16 in `--default`,
  55 in `--full`" hook counts — the 16/55 figures there are hook-count, not consumer-count; no
  explicit consumer-project registry count was found in the read files. Design flags this as an
  **unverified number carried from the task prompt**, not independently confirmed by any
  document read — see §8 residual uncertainty. The analysis below is qualitative and holds
  regardless of the exact consumer count.)
- **What breaks first if a consumer does NOT re-init:** the consumer's projected hooks were
  generated referencing `lib.*` imports (pre-rename). Post-rename, the SOURCE repo's `lib/`
  package no longer exists (`git mv` to `cos_lib/`), but this is a SOURCE-repo-only change — the
  consumer's *already-projected* files are static copies (per `hook-lib-projection-contract`'s
  dependency-closure projection model) and do not change until the consumer re-runs `cos init`.
  A non-re-initted consumer keeps working exactly as before (still importing its own projected
  `lib.*` files, which still exist in *their* tree) — **nothing breaks immediately.**
- **What breaks on next `cos init --full` without understanding the rename:** a consumer that
  re-inits picks up the new `cos_lib`-projected hooks. If their own environment/tooling
  hardcodes a `PYTHONPATH` entry or path reference assuming `.cognitive-os/lib/...` (rather than
  the parent-of-package entry `.cognitive-os` which `hook-lib-projection-contract` §1 already
  established as the correct, package-name-agnostic form), that consumer-side override would
  break. This is the same class of risk `hook-lib-projection-contract` already accepted for its
  own migration (§6 of that design), not a new risk class this SDD introduces.
- **Does fail-open (hook-lib-projection-contract §3) cover the transition period?** **Yes, for
  the "missing" case, but not for a genuine mid-transition collision.** Fail-open converts
  `ModuleNotFoundError` into a silent no-op — it does NOT distinguish "consumer hasn't re-initted
  yet, still on old `lib` hooks importing their own already-present `lib.*`" (nothing to fail
  open on — those imports still resolve fine, package unchanged from the consumer's point of
  view) from "consumer re-initted, got `cos_lib`-projected hooks, but something in their
  environment still shadows/blocks the import." The proposal's own §1 already established
  fail-open is a bandage, not a fix, for the *shadowing* case; this SDD's rename removes that
  case at the root for anyone who re-inits. Consumers who never re-init simply never get the
  fix, but are also never worse off than pre-rename (their static projection is untouched).

**Recommendation:** ship a short upgrade-note addendum alongside the existing
`hook-lib-projection-contract` migration note: *"if you installed before 2026-07-09, your
projected hooks import `lib.*`; re-run `cos init --full` to receive `cos_lib.*`-projected hooks
and close namespace-collision risk U1 for your project."* Detection/warning inside `cos init`
itself (scanning a consumer's `.cognitive-os/` for stale `lib.*` references pre-re-init) is
**out of scope for this SDD** — it requires new installer-side logic beyond the codemod's scope
and belongs to `hook-lib-projection-contract`'s own follow-on surface, not this rename's task
list. Flagged as residual risk (§8).

---

## 6. U-Q6 — Pre-existing `cos_lib_*` tooling reconciliation

Read in full: `scripts/cos_lib_symlink_invariant_audit.py` (461 lines) and
`tests/audit/test_lib_symlink_invariant.py` (187 lines).

**Do they assume `cos_lib` is a FUTURE package or ALREADY exists?** Neither, precisely — they
assume **`lib/` (the OLD name) is the live root package today**, and are simply *prefixed* with
the name `cos_lib` in their own filenames (`cos_lib_symlink_invariant_audit.py`,
`test_lib_symlink_invariant.py` — note the test file itself is NOT prefixed `cos_lib_`, only the
script is). Internally, both hardcode `"lib"` as the literal directory name:
`_collect_root_lib()` does `lib_dir = repo / "lib"` (line 128); the test docstring says "Verifies
... lib/*.py (root) and packages/*/lib/*.py counterparts." Neither file's *logic* references a
directory literally named `cos_lib` anywhere.

**Semantics — what do they actually audit?** The audit's true subject is the **symlink
invariant between `lib/*.py` (root) and `packages/*/lib/*.py` (package-internal)** — i.e. it
verifies that root-level modules are proper symlinks into their package-internal counterparts,
not real-file duplicates (drift detection for the "lib/*.py are SYMLINKS — NOT duplicates"
invariant the module docstring states). This is **exactly the same symlink relationship this
SDD's dry-run manifest §6 documents for the 73 `lib/` symlinks** (`lib/agent_bus.py ->
../packages/agent-coordination/lib/agent_bus.py`, etc.) — same invariant, same file set,
different tool. The script's `cos_lib_` filename prefix appears to have been chosen
*anticipating* this exact rename (its own docstring cites "ADR-267 follow-up," though the actual
ADR-267 in this repo is unrelated — license-compliance enforcement — so the citation is either a
stale/incorrect ADR reference or an internal renumbering artifact; not resolved further here as
it does not change the reconciliation call).

**Compatibility — will this rename break them, harmonize with them, or require rewiring?**
**Breaks them silently, in the worst way: false-green, not a crash.** After `git mv lib cos_lib`,
`_collect_root_lib()`'s `repo / "lib"` resolves to a directory that no longer exists → returns
`{}` (empty dict, the function's own not-a-dir guard: `if not lib_dir.is_dir(): return {}`). The
audit then finds **zero root files**, pairs nothing, reports **zero errors** — not because the
invariant holds, but because the tool is now looking at nothing. `test_actual_repo_performance_
and_baseline` (the one test that runs against the live repo, not a `tmp_path` fixture) would
**still pass** post-rename with a false-negative 0-errors result, silently disabling the drift
detector this SDD is supposed to preserve. This is the single most important finding of this
design phase (§8).

**Recommendation: RENAME the internal path references (not the filenames), reconciling them
into this SDD's own task list — not deferred to a post-apply audit.**

- Keep `scripts/cos_lib_symlink_invariant_audit.py`'s filename as-is (already correctly
  anticipates the target name).
- Update `_collect_root_lib()` (line 128: `lib_dir = repo / "lib"` → `repo / "cos_lib"`) and the
  `--scope` CLI choices/help text (`choices=["lib", "packages", "both"]` at line 415 — the `"lib"`
  literal there is a user-facing flag value, not a path; rename to `"cos_lib"` for consistency,
  keep `"lib"` as a deprecated alias for one release to avoid breaking any script that already
  calls `--scope lib`).
- Update `tests/audit/test_lib_symlink_invariant.py`: its fixtures build `tmp_path / "lib"` and
  `tmp_path / "packages" / "mypkg" / "lib"` — these are fixture-internal directory names that
  exercise the *audit function's* generic `root_files`/`pkg_files` logic, which after the fix
  above will look at `repo / "cos_lib"`, not `repo / "lib"`, when run against the real repo. The
  four `tmp_path`-based unit fixtures (clean/drift/dupe/dangling) can stay named `lib` internally
  IF `run_audit()` is parameterized to accept a root-dir-name override for testability — simplest
  fix: add a `root_pkg_name: str = NEW_PKG` parameter to `run_audit()`/`_collect_root_lib()`
  defaulting to `"cos_lib"`, and have the four `tmp_path` fixtures pass `root_pkg_name="lib"`
  explicitly so they keep testing the *general* symlink-invariant logic without needing to know
  the real package name. This avoids renaming every fixture path in the test file while fixing
  the real-repo-facing default. Only `test_actual_repo_performance_and_baseline` (no override,
  uses the real default) needs zero changes beyond the production default flip.
- Do **not** delete either file — the invariant they check (root package symlinks must not
  drift from package-internal originals) is orthogonal to and unaffected by *which* name the
  root package has; deleting would remove real drift-detection coverage this rename does not
  make obsolete.
- Do **not** wait for a "post-apply audit" — reconciling this now, in the same atomic commit,
  is required because `test_actual_repo_performance_and_baseline` runs in CI/test-suite and
  must not silently regress to a false-green 0-files-scanned state the moment `lib/` stops
  existing. This is task **T10**, gated before T12 (full test suite run), because running the
  suite before T10 would "pass" on the stale, blind version of this test.

---

## 7. Task DAG

| ID | Task | Guarded? | Depends on |
|---|---|---|---|
| T1 | `git checkout -b chore/cos-lib-rename` | no | — |
| T2 | Export `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` for the whole session (R1) | — | T1 |
| T3 | Re-run `cos_lib_rename_codemod.py --json` fresh; diff totals against the 2026-07-08 dry-run (R3) | no | T2 |
| T4 | `git mv lib cos_lib` | **guarded** (touches the tree root the guard cares about only indirectly; the mv itself is not a `hooks/`\* write, but must happen inside the guarded session per R1) | T3 |
| T5 | `COS_ALLOW_PROTECTED_CONFIG_WRITE=1 python3 scripts/cos_lib_rename_codemod.py --apply` (rewrites 902 files incl. 94 guarded) | **guarded** | T4 |
| T5b | Extended string-ref scan (§3) — diff new hits vs. the 15 enumerated; triage any new ones | no | T5 |
| T6 | Hand-edit the 14 (+1 = 15, §3/§8) real package-dir resolvers | no | T5b |
| T7 | Spot-check sample of the 111 fixture string refs (Bucket B, §3) | no | T5b |
| T8 | Confirm `workflows/*` untouched (git diff shows 0 changes there) | no | T5 |
| T9 | Add/extend `tests/audit/test_workflows_lib_isolation.py` (or equivalent) automated RISKY-edge gate (§2) reusing codemod's `load_allowlist()` | no | T8 |
| T10 | Fix `cos_lib_symlink_invariant_audit.py` + its test for the new default root name (§6) | no | T6 |
| T11 | Document rollback recipe (§4) in the task/commit notes (no code change, just recorded procedure) | no | T1 |
| T12 | Run full test suite (`tests/audit`, `tests/unit`, `tests/integration`) | no | T9, T10 |
| T13 | Consumer-isolation check: fresh `cos init --full` into temp sandbox with its own top-level `lib/`; `python3 -c "import cos_lib.confidentiality_scanner"` resolves correctly (proposal §6.4) | no | T12 |
| T14 | Idempotency re-run: `cos_lib_rename_codemod.py --json` reports 0 further edits | no | T13 |
| T15 | Single atomic commit (mv + all edits + T6 + T9 + T10) | — | T13, T14 |
| T16 | Write consumer migration upgrade-note addendum (§5) | no | T15 (can be authored in parallel, merged same PR) |

Batches: **T1-T2** (setup, unguarded) → **T3-T10** (the single guarded apply pass, per §1 —
these are sub-steps of ONE session/commit, not separate batches to commit independently) →
**T11-T14** (verification, unguarded) → **T15-T16** (commit + docs).

---

## 7b. Apply-time addendum — 2-phase codemod (added 2026-07-09)

**Discovered mid-apply (agent a0344a3fc2ec9b606):** the codemod is deliberately
AST-only. After T5 `--apply`, §6.1's textual grep still finds ~787 residuals in
~295 files — these are `lib.X` mentions inside comments, docstrings, and data
strings, not live import positions. The AST-only design is correct for safety
(prose regex cannot semantically distinguish live code from documentation), but
§6.1 as written cannot converge to 0 without a second pass.

**Resolution:** codemod extended with `--prose-sweep` flag (function
`prose_sweep()` at `scripts/cos_lib_rename_codemod.py`). It runs after
`apply_edits` in the SAME apply invocation, using the SAME boundary-anchored
regexes (`RE_DOTTED`, `RE_FROM_BARE`, `RE_DASH_M`), and applies them whole-file
to every tracked `.py`/`.sh`/`.md`. The negative lookbehind `(?<![A-Za-z0-9_.])`
in `RE_DOTTED` rejects `cos_lib.X` and other `_lib` suffixes, so re-running is
idempotent. `workflows/` is explicitly excluded (§2 U-Q2 policy).

**Updated task DAG:** T5 (AST apply) → **T5c (prose sweep, same subprocess call
with `--prose-sweep`)** → T5b (extended string-ref scan verifies both passes
completed). §6.1 acceptance now measured post-both-phases.

Recipe change: `COS_ALLOW_PROTECTED_CONFIG_WRITE=1 python3 scripts/cos_lib_rename_codemod.py --apply --prose-sweep`.

## 8. Acceptance criteria

- **§6.1** Grep-verified rename complete (post-both-phases: AST + prose sweep):
  `grep -rE '(?<![A-Za-z0-9_.])lib(?=\.)|from lib import' --include='*.py' --include='*.sh' . | grep -v 'workflows/lib' | wc -l` → **0**.
- **§6.2** Full test suite (`tests/audit`, `tests/unit`, `tests/integration`) exits 0, including
  the re-targeted `hook-lib-projection-contract` regression test and the new/updated
  `test_lib_symlink_invariant.py` (T10) and `test_workflows_lib_isolation.py` (T9).
- **§6.3** Fresh consumer install works: `cos init --full` into a temp sandbox containing its
  own top-level `lib/` succeeds; `python3 -c "import cos_lib.confidentiality_scanner"` resolves
  the COS module (U1 regression case closed).
- **§6.4** `hook-lib-projection-contract` regression suite still green, re-targeted at
  `cos_lib` (per that design's own migration note).
- **§6.5** Pre-existing `cos_lib_symlink_invariant_audit.py` + `test_lib_symlink_invariant.py`
  are explicitly updated (not left as-is, not deleted) per §6/T10, and
  `test_actual_repo_performance_and_baseline` reports a **non-zero** `scanned_root_files` count
  post-rename (proves the audit is scanning `cos_lib/`, not silently scanning nothing).

## 9. Risks & residual uncertainty (open after apply)

- **The "16 registered consumers" figure (task prompt, §5 above) is unverified** by any document
  read during this design phase — no consumer registry file was located. The qualitative
  migration-UX analysis in §5 does not depend on the exact count, but an operator wanting a
  precise consumer-impact count should locate and cite the actual registry before communicating
  impact externally.
- **`cos init` stale-state detection (§5)** is explicitly deferred as a follow-on to
  `hook-lib-projection-contract`, not this SDD — consumers who never re-init get no warning,
  though they also take on no new risk (their static projection is untouched).
- **The ADR-267 citation in `cos_lib_symlink_invariant_audit.py`'s docstring is stale/incorrect**
  (actual ADR-267 in this repo is license-compliance enforcement, unrelated) — a documentation
  correction, not a functional blocker; flagged but not fixed by this SDD's task list (out of
  the atomic-rename's blast radius).
- **T5b's "extended string-ref scan" is a design-time heuristic, not yet run** — it is possible
  additional misses beyond the one identified in §8/§3 exist; T5b is the gate that surfaces them
  before the commit, but design cannot guarantee zero further misses without executing it.
- **The `--scope lib` deprecated-alias question (§6)** — keeping `"lib"` as a backward-compatible
  alias for `--scope` is a one-release grace period recommendation, not enforced by any test in
  this design; a follow-up task should add a deprecation-removal reminder.

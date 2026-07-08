# Design: `hook-lib-projection-contract`

- **Change:** `hook-lib-projection-contract`
- **Phase:** design (technical design only — no implementation in this artifact)
- **Repo:** luum-cognitive-os (SOURCE)
- **Date:** 2026-07-08
- **Locked decision (operator):** Combined option **(b)** — dependency-closure `lib`
  projection + shared PYTHONPATH bootstrap + fail-open backstop + consumer-sandbox
  regression test.
- **Inputs:** `docs/02-Decisions/proposals/hook-lib-projection-contract.md`,
  `docs/06-Daily/reports/hook-lib-projection-breakage-2026-07-08.md`, seed probe
  `…/scratchpad/hook-lib-probe.py`.

---

## 0. What the design must nail down (from propose)

The proposal left **one** open question that gates apply: *how do projected hooks get
`lib/` on `sys.path` with minimal per-hook edits, portably across harnesses?* This design
resolves that (§1), then specifies the closure algorithm (§2), the fail-open backstop (§3),
the regression test (§4), the apply DAG (§5), and acceptance/migration/rollback (§6).

**Load-bearing correction to the proposal's sketch.** The proposal wrote
`PYTHONPATH=.cognitive-os/lib`. That is **wrong** for the imports in question. Every broken
hook does `from lib.<mod> import …` / `import lib.<mod>` — i.e. it imports the **package**
`lib`. Python resolves `lib.<mod>` by finding a directory named `lib/` (with `__init__.py`)
on a `sys.path` entry, so the path entry must be the **parent** of that directory. The
installer already ships the closure into `.cognitive-os/lib/<mod>.py` with an
`.cognitive-os/lib/__init__.py`, so the package root is `.cognitive-os/lib` and the correct
`sys.path` entry is its parent:

```
PYTHONPATH="$PROJECT_DIR/.cognitive-os"      # NOT .cognitive-os/lib
```

This is corroborated by the one lib-consumer that already works in a projected install —
`scripts/cos_quality_duplicates.py:12` does `sys.path.insert(0, dirname(dirname(__file__)))`
(= `.cognitive-os/`) before `from lib.duplicate_scanner import …` (`:13`). The bootstrap must
export the parent, not the package dir.

---

## 1. Bootstrap delivery mechanism (the resolved open question)

### 1.1 The runtime topology that decides this

Two facts from the settings drivers determine the choice:

- **Claude driver** (`scripts/_lib/settings-driver-claude-code.sh:64-76`): **every** hook
  command is emitted as
  `bash "$…/scripts/hook-timing-wrapper.sh" <event> "$…/<hook>.sh"`. The timing wrapper
  (`scripts/hook-timing-wrapper.sh`) is a **universal choke point** — 100% of Claude-wired
  hooks (16 in `--default`, 55 in `--full`) pass through it, including the killswitch bypass
  path (`:36-39` `exec "$@"`).
- **Codex driver** (`scripts/_lib/settings-driver-codex.sh:65-75`): hooks are **not** wrapped.
  Each command is `export COGNITIVE_OS_HARNESS=codex; export COGNITIVE_OS_PROJECT_DIR=…; if
  [ -x "$PWD/<hook>" ]; then bash "$PWD/<hook>"; fi`. There is already an `export` prefix in
  the command template — the natural injection point for Codex.

So the wrapper is universal **for Claude** but **not** across harnesses (ADR-008). A
wrapper-only fix leaves Codex broken. The design therefore injects at the **projection /
wrapper layer of each harness**, driven by a single shared path-computation file, giving
**0 per-hook edits** on every harness.

### 1.2 Per-mechanism evaluation

| Mechanism | Hooks needing edit | Portability (ADR-008) | Failure modes |
|---|---|---|---|
| **(i) Global env in `settings.json` `env`** | 0 | **Claude-only.** Codex/opencode/bare have no global-env equivalent; Codex injects env per-command. | **Session-wide `PYTHONPATH` pollution:** every `python3` the user runs via the Bash tool and the harness itself inherits it; a consumer with its **own** top-level `lib/` package gets shadowed/collided. Broad blast radius. Reject. |
| **(ii) Export inside `hook-timing-wrapper.sh`** | 0 | Covers **Claude** (both profiles route through wrapper). **Does not cover Codex** (bypasses wrapper). | Scoped to hook subprocesses only (good). Killswitch `exec "$@"` path must still inherit the export — achievable by exporting before `:36`. Incomplete alone. |
| **(iii) Sourced `_lib/hook-python-env.sh`, one `source` line per hook** | up to **84** | Portable (self-contained per hook) | 84 guarded (`hooks/**`) edits, each a `protected-config-write-guard` bypass; high regression surface; collapses toward rejected option (c). Reject as primary. |

### 1.3 Chosen primary + fallback

**Primary — projection-layer injection driven by one shared file (0 per-hook edits):**

1. **New shared file** `hooks/_lib/hook-python-env.sh` (guarded; auto-projected because
   `cos_init.py:1852-1857`/`:1831-1836` copies all of `hooks/_lib/` into
   `.cognitive-os/hooks/cos/_lib/`). It computes the project dir and exports the **corrected**
   path exactly once, idempotently:

   ```bash
   # hook-python-env.sh — single source of truth for hook lib path.
   # Sourced by the timing wrapper (Claude) and by the Codex command prefix.
   _cos_proj="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-${CODEX_PROJECT_DIR:-$PWD}}}"
   case ":${PYTHONPATH:-}:" in
     *":$_cos_proj/.cognitive-os:"*) : ;;                       # already present, no-op
     *) export PYTHONPATH="$_cos_proj/.cognitive-os${PYTHONPATH:+:$PYTHONPATH}" ;;
   esac
   ```

2. **Claude path — `scripts/hook-timing-wrapper.sh` sources it (1 edit, unguarded).**
   The wrapper resolves `PROJECT_DIR` at `:54`; add, immediately after that resolution and
   *before* the killswitch `exec` is reachable, a source of the sibling env file:
   `[ -f "$SCRIPT_DIR/../hooks/cos/_lib/hook-python-env.sh" ] && source …` (self-repo path
   `hooks/_lib/…` when running in-repo). Because the wrapper `export`s, the value is inherited
   by the real hook whether it runs via `bash "$HOOK_PATH"` (`:307-322`) or the killswitch
   `exec "$@"` (`:38`). One file edit covers all 55 Claude hooks.

3. **Codex path — `scripts/_lib/settings-driver-codex.sh` prefix (1 edit, unguarded).**
   Extend the existing `export …` prefix at `:73` to also
   `source "$PWD/.cognitive-os/hooks/cos/_lib/hook-python-env.sh" 2>/dev/null || true;` before
   `bash "$PWD/<hook>"`. One template edit covers all Codex hooks.

**Fallback / defense-in-depth (0 required edits):** the same `hook-python-env.sh` is
**source-able by any hook directly**. No hook needs the line today, but if a future harness
invokes a hook outside both the wrapper and the Codex prefix, adding a single
`source "$(dirname "$0")/_lib/hook-python-env.sh"` line to that one hook restores it — an
incremental, not wholesale, cost.

**Why this over (i):** (ii)+Codex-prefix scopes `PYTHONPATH` to hook subprocesses (no
session pollution, no shadowing of the user's own python), and is portable — the exact axes
on which global env injection fails.

**Chosen hook-edit count: 0.** Edits are 1 wrapper (unguarded) + 1 Codex driver (unguarded)
+ 1 new `_lib` file (guarded). opencode/bare drivers: same one-line prefix pattern when/if
they gain lib-importing hooks (currently none wired).

---

## 2. Dependency-closure algorithm

### 2.1 Structure facts

- `lib/` is a **flat** package: 369 `*.py`, `lib/__init__.py` present, no sub-packages
  (only `__pycache__`). Package name is `lib`; import form is always `lib.<flat_module>`.
- `lib/` contains **73 symlinks** into `packages/*` (e.g.
  `lib/cost_predictor.py -> ../packages/scope-governance/lib/cost_predictor.py`). `shutil.copy2`
  **dereferences** symlinks, so a projected copy is a real file — but the closure must follow
  the symlink to AST-parse the **real target's** own imports.

### 2.2 Algorithm (static, run inside `cos_init.py` at install time)

New module `scripts/lib_closure.py` (helper, unguarded), invoked from the hook-install loop:

1. **Seed set = hooks actually projected for this profile.** For `--full`, every
   `hooks/*.sh` that passes `scope_allows`; for `--default`, exactly the `default_hooks`
   list. (Same iteration already present at `cos_init.py:1822-1850`.) This scopes the closure
   to the profile's real hook set — the whole point of option (b) vs (a).
2. **Extract embedded Python from each seed hook** and pull `lib.<mod>` references from all
   three embedding forms:
   - heredocs (`python3 - <<'PYEOF' … PYEOF`, `python3 -c '…'`),
   - inline `-c` strings,
   - `python3 -m lib.<mod>`.
   Regex-seed exactly as the validated probe does
   (`…/scratchpad/hook-lib-probe.py::lib_modules`,
   `r"(?:from lib\.|import lib\.|-m lib\.|python3 -m lib\.)([A-Za-z0-9_]+)"`), then **upgrade
   to AST** for the heredoc bodies: `ast.parse` each heredoc, walk `Import`/`ImportFrom`
   nodes, collect names whose root is `lib`. AST removes false positives from comments/strings
   that regex alone would include.
3. **Transitive resolution over `lib/` itself.** Maintain a worklist of `lib.<mod>` names.
   For each, resolve the on-disk file `lib/<mod>.py` **through its symlink** (`Path.resolve()`);
   `ast.parse` the **real target**; add any `lib.<other>` it imports to the worklist. Repeat to
   fixpoint. (confidentiality_scanner is a clean example: it imports only stdlib —
   `lib/confidentiality_scanner.py:19-22` — so its closure is `{confidentiality_scanner}`.)
4. **Project the closure**, preserving the flat package layout:
   `.cognitive-os/lib/<mod>.py` for each closure member (real dereferenced content via
   `shutil.copy2` of the resolved target), plus ensure `.cognitive-os/lib/__init__.py`
   exists. This **extends** — does not replace — the existing 2-module duplicates subset at
   `cos_init.py:1436-1462`; that function's modules are simply members (or not) of the same
   `.cognitive-os/lib/` package now, so no special-casing is needed.
5. **Provenance for drift detection (addresses propose §7 symlink risk).** Write
   `.cognitive-os/lib/.closure-manifest.json` = `{module: sha256(dereferenced-content),
   source_rel_path, was_symlink}`. This lets ACC / the regression test detect when a
   projected copy has drifted from its `packages/*` origin, and documents which modules were
   symlink-dereferenced.

### 2.3 Staying correct as hooks change

Closure is recomputed on **every** `cos init` (installer-time, not cached), so adding a
`lib.*` import to any hook re-projects its closure on the next install. The regression test
(§4) is the enforcement: it fails in CI if a projected hook imports a `lib.*` module the
closure did not ship. **Static-closure blind spot** (dynamic `importlib` / string-built
module names) is real; it is covered by the fail-open backstop (§3) degrading a miss to a
silent no-op, never a false block — see §7 risk.

---

## 3. Fail-open backstop (precise fix)

### 3.1 The exact defect in `confidentiality-enforcer.sh`

Two lines conspire (`hooks/confidentiality-enforcer.sh`):

- `:87` runs the scanner heredoc with `2>&1`, **merging the Python traceback into
  `$PYTHON_OUTPUT`**.
- `:108` captures `PYTHON_EXIT=$?`; `:110` treats `PYTHON_EXIT -eq 1` as "violations found".

A `ModuleNotFoundError: No module named 'lib'` makes Python exit **1** with a traceback on
stderr → merged into stdout → `PYTHON_EXIT==1` → the JSON parse at `:111-130` fails (`[?]`
fields) → `:151` prints `CONFIDENTIALITY VIOLATION` → `:169` `exit 2` (**false hard block**).
Confirmed by the ground-truth run in the evidence report §4.

### 3.2 Fix — separate the violation channel from the error channel, with a tri-state contract

The root problem is **channel conflation** (exit code + merged streams carry two different
meanings). Fix by giving the scanner an unambiguous contract and the shell a tri-state:

1. **Scanner emits a distinct exit code for infra failure.** Wrap the heredoc body in
   `try/except` so that an import/environment failure exits with a **reserved code (3)**,
   never 1:
   ```python
   try:
       from lib.confidentiality_scanner import scan_file, load_protected_terms, is_scannable_path
   except Exception as e:
       import sys; print(f"SCANNER_INFRA_ERROR: {e}", file=sys.stderr); sys.exit(3)
   ```
   Contract becomes: **0 = clean, 1 = violations (valid JSON on stdout), 3 = infra error.**
2. **Stop merging stderr into the violation channel.** Change `:87` from `2>&1` to
   `2>"$PYERR"` (a `mktemp` file). `$PYTHON_OUTPUT` now holds **only** stdout (the JSON
   violation lines). A traceback can never masquerade as a violation.
3. **Fail OPEN on infra error.** Before the `:110` violation branch:
   ```bash
   if [ "$PYTHON_EXIT" -eq 3 ] || { [ "$PYTHON_EXIT" -ne 0 ] && [ "$PYTHON_EXIT" -ne 1 ]; }; then
       # ModuleNotFound / crash / any non-{0,1} code → allow + log, never block
       echo "CONFIDENTIALITY SCAN SKIPPED (infra error) for $FILE_PATH" >&2
       mkdir -p "$METRICS_DIR"
       echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"file\":\"$FILE_PATH\",\"action\":\"scan_error_fail_open\",\"exit\":$PYTHON_EXIT}" >> "$METRICS_DIR/confidentiality-enforcer.jsonl"
       exit 0
   fi
   ```
4. **Defensive re-validation of the `exit 1` path.** Even at exit 1, only treat rows that
   `json.loads` cleanly as violations; if stdout is empty/unparseable while exit==1, fail
   open (exit 0 + `scan_error_fail_open`). This makes the block path require *positive,
   parseable evidence of a violation*, not merely a nonzero code.

With the bootstrap (§1) in place the scanner imports fine and this backstop never fires; if a
closure miss (§2.3) or environment breakage recurs, the worst case is a **silent no-op**, not
`exit 2`.

### 3.3 Generalizing the idiom

Add a shared helper `hooks/_lib/hook-python-guard.sh` (guarded) exposing
`cos_run_python_guarded <outfile> <errfile> -- <python-invocation…>` that:
- runs the python with stdout→`outfile`, stderr→`errfile` (never merged),
- returns a tri-state via `$COS_PY_STATE` ∈ {`clean`, `result`, `infra_error`} keyed off the
  reserved exit code,
so any lib-importing **gate** (a hook whose nonzero exit blocks) can adopt "infra_error ⇒
fail open". The evidence report classifies only `confidentiality-enforcer` as Tier-1
(hard-block); the other ~15 default lib-importers already fail open via `|| true` /
`2>/dev/null` (report §5). The regression test (§4) **verifies** that fail-open claim for
every default Tier-2 hook rather than trusting the static inference (propose §7 caveat).

---

## 4. Regression test

**File:** `tests/audit/test_hook_lib_projection.py` (unguarded; seeded from
`…/scratchpad/hook-lib-probe.py`, whose extraction + consumer-layout logic is already
validated against the real breakage).

**What it does (must FAIL on today's code, PASS after apply):**

1. **Real projection.** `pytest` fixture runs `python3 scripts/cos_init.py --full <tmp>` (and
   a second case `--default <tmp2>`) into a temp consumer whose cwd is **not** the repo root
   (foreign-cwd, to defeat the in-repo `lib/` shadow).
2. **Closure presence.** For every projected lib-importing hook under
   `<tmp>/.cognitive-os/hooks/cos/`, extract its `lib.<mod>` set (same extractor as §2.2) and
   assert each `<tmp>/.cognitive-os/lib/<mod>.py` exists (transitive closure shipped).
3. **Import-resolution probe (no false ModuleNotFound).** With `cwd=<tmp>` and the bootstrap
   sourced (`PYTHONPATH=<tmp>/.cognitive-os`), run `python3 -c "import lib.<mod>"` for each
   imported module; assert **zero** `ModuleNotFoundError`. (Mirrors the seed probe's scenario
   (ii), which today reports 55/55 fail in `--full`, 16/16 in `--default`.)
4. **No false `exit 2` (Tier-1 + Tier-2 real run).** Execute each projected lib-importing
   hook in the sandbox (`cwd=<tmp>`, `CLAUDE_PROJECT_DIR=<tmp>`) on a **benign** PostToolUse
   payload (2-line text file). Assert **no hook exits 2**. For `confidentiality-enforcer.sh`
   specifically assert `exit 0` on the benign write (the exact ground-truth reproduction).
5. **Fail-open confirmation.** Temporarily hide the projected `lib/` (rename it) and re-run
   `confidentiality-enforcer.sh`; assert it now exits **0** with a `scan_error_fail_open`
   metrics row — proving the backstop, not just the happy path.

**Acceptance command:** `python3 -m pytest tests/audit/test_hook_lib_projection.py -q`
(exit 0 after apply; asserts 3-5 fail before apply). Register its dir/lane per
`rules/lane-taxonomy` if `tests/audit` is not already a declared lane.

---

## 5. Task DAG for apply

Guarded = under `hooks/**` (needs `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`, per
`protected-config-write-guard.sh:41` globs). `scripts/**`, `manifests/*` (non-`*security*`),
`tests/**`, `cos_init.py` are **unguarded**.

```
T1 (unguarded)  scripts/lib_closure.py            ── new closure module (§2.2)
      │
T2 (unguarded)  scripts/cos_init.py               ── call T1 from hook-install loop;
      │                                              project closure to .cognitive-os/lib
      │                                              + .closure-manifest.json (§2.2/2.3)
      │
      ├── T3 (GUARDED)  hooks/_lib/hook-python-env.sh   ── new shared bootstrap (§1.3)
      │        │
      │        ├── T4 (unguarded) scripts/hook-timing-wrapper.sh ── source T3 (Claude)
      │        └── T5 (unguarded) scripts/_lib/settings-driver-codex.sh ── source T3 (Codex)
      │
      ├── T6 (GUARDED)  hooks/_lib/hook-python-guard.sh ── tri-state runner (§3.3)
      │        │
      │        └── T7 (GUARDED) hooks/confidentiality-enforcer.sh ── channel split +
      │                                                              fail-open (§3.1-3.2)
      │
      └── T8 (unguarded) tests/audit/test_hook_lib_projection.py ── depends on T2,T3,T4,T7
              │
              └── T9 (unguarded) manifests/  ── record lib-projection contract for ACC
                                                (alongside harness-projection.yaml)
```

**Sequencing rule:** run the two guarded batches (T3, then T6→T7) **with**
`COS_ALLOW_PROTECTED_CONFIG_WRITE=1` exported; run everything else without it. T8 (the test)
must be authored to fail against pre-T2/T7 state and is the final gate. Suggested apply
batches: **Batch A** {T1,T2} (closure lands, verify §6.1/§6.5), **Batch B (guarded)** {T3}
+ **Batch B' (unguarded)** {T4,T5} (bootstrap, verify §6.2), **Batch C (guarded)** {T6,T7}
(fail-open, verify §6.3), **Batch D** {T8,T9} (lock the contract, verify §6.4/§6.6).

---

## 6. Acceptance criteria, migration, rollback

### 6.1-6.6 Verifiable acceptance (run from SOURCE repo root)

1. **Closure projected.**
   `python3 scripts/cos_init.py --full /tmp/cos_c && test -f /tmp/cos_c/.cognitive-os/lib/confidentiality_scanner.py` → exit 0.
2. **Bootstrap present + exports the CORRECT path.**
   `test -f /tmp/cos_c/.cognitive-os/hooks/cos/_lib/hook-python-env.sh` → 0, and
   `cd /tmp/cos_c && source .cognitive-os/hooks/cos/_lib/hook-python-env.sh && python3 -c "import lib.confidentiality_scanner"` → 0
   (confirms `PYTHONPATH=$PROJECT_DIR/.cognitive-os`, §0 correction).
3. **No false block (Tier-1).** Projected `confidentiality-enforcer.sh` in the sandbox
   (`cwd`/`CLAUDE_PROJECT_DIR` = `/tmp/cos_c`, benign 2-line write on stdin) → **exit 0**.
4. **Regression test green.**
   `python3 -m pytest tests/audit/test_hook_lib_projection.py -q` → exit 0
   (and demonstrably red before apply on checks §4.3-4.5).
5. **Probe parity.** Re-running the seed probe against a fresh consumer reports
   `fail_scenario_ii == 0` (was 55 in `--full`, 16 in `--default`).
6. **No SOURCE regression.** `python3 -m pytest tests/audit -q` and the hook-syntax lane → 0.
   `bash scripts/_lib/settings-driver-claude-code.sh --check` and the Codex driver `--check`
   → 0 (settings still in sync after the driver edit).

### Migration (existing consumer installs)

Consumers are broken today and recover by **re-projecting**: `cos init` for their
profile/harness. The installer is idempotent and overwrites projected hooks, the timing
wrapper, `.cognitive-os/hooks/cos/_lib/`, and now `.cognitive-os/lib/` with the closure. No
consumer data is touched; only projected COS files change. Publish a one-line upgrade note
("re-run `cos init` to receive the `lib/` projection + bootstrap"). ACC gains the §T9
manifest entry so a stale consumer is detectable.

### Rollback

Installer-only surface + one guarded hook edit → cheap revert:
1. `git revert` the change set (or drop T2's closure call + T4/T5 source lines + restore
   `confidentiality-enforcer.sh`), then `cos init` re-projects the prior state.
2. **Emergency, no redeploy:** `export COS_ALLOW_PROTECTED_CONFIG_WRITE` not needed; set
   `COS_HOOK_TIMING_DISABLE=1` only bypasses timing, **not** the fix — instead, to neutralize
   a bad bootstrap, ship an empty `hook-python-env.sh` (path unset ⇒ hooks fall back to their
   prior broken-but-fail-open behavior, and the §3 backstop keeps confidentiality-enforcer
   from false-blocking). The fail-open backstop (T7) is itself the safety net that makes
   rollback low-risk: even fully reverted bootstrap cannot resurrect the `exit 2`.

---

## 7. Risks & residual uncertainty

- **Namespace collision (new, honest, primary risk).** With `cwd=consumer root` on
  `sys.path[0]` and `PYTHONPATH=$root/.cognitive-os` appended, a consumer that has its **own**
  top-level `lib/` package will have **their** `lib` shadow ours (cwd precedes PYTHONPATH),
  re-breaking the import in exactly those consumers. Not observed in the empty-sandbox probe
  (which has no `lib/`), so its real-world frequency is **unmeasured**. Mitigation now: the §3
  fail-open backstop degrades the shadowed-import case to a no-op, never a false block.
  Durable fix (out of scope, flag for a follow-on ADR): rename the shipped package to a
  namespaced `cos_lib` and rewrite hook imports — deferred because it re-introduces the
  84-file edit cost this design exists to avoid.
- **Static-closure miss** (`importlib`/string-built names): covered by fail-open + the §4
  test for any exercised hook; open question carried from propose — whether to over-approximate
  with a small allowlist superset.
- **Symlink drift**: `.closure-manifest.json` hashes (§2.3) make drift detectable; re-init
  refreshes.
- **Cross-harness completeness**: opencode/bare drivers get the same one-line prefix pattern
  only when they wire a lib-importing hook (none today) — tracked, not blocking.
- **Guarded apply**: T3/T6/T7 need `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`; forgetting it blocks
  the apply.

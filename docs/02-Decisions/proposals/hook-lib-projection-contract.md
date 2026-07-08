# Proposal: `hook-lib-projection-contract`

- **Change:** `hook-lib-projection-contract`
- **Phase:** propose (design only — no implementation in this artifact)
- **Repo:** luum-cognitive-os (SOURCE)
- **Date:** 2026-07-08
- **Evidence base:** `docs/06-Daily/reports/hook-lib-projection-breakage-2026-07-08.md`
  (empirical probe; seed at `…/scratchpad/hook-lib-probe.py`)
- **Author note:** decision-grade summary; apply phase gated by `protected-config-write-guard` (see §4).

---

## 1. Problem

Projected Cognitive OS hooks `import lib.*`, but the installer never ships the `lib/`
package to consumers, so lib-importing hooks are broken in every consumer install. The
empirical probe (real projection into temp consumer sandboxes via `scripts/cos_init.py`,
plus one controlled real hook run) found **84 hooks** contain a `from lib.` / `import lib.`
/ `-m lib.` statement, and **84/84 fail** to import `lib.*` in a consumer under both the
"no lib" and the "reality" scenarios (isolated `import lib.<module>` probes, 0 passers).
Wired-in breakage: **55/55** lib-importing hooks projected in a `--full` install are broken
and **16/16** in the common `--default` install are broken. The installer projects only a
hard-coded **2-module subset** (`duplicate_scanner.py`, `project_paths.py`) into
`.cognitive-os/lib/` for the duplicates primitive (`scripts/cos_init.py:1436-1462`); no
lib-importing hook imports either of those two modules, and there is no root-level `lib/`
in the consumer at all. A controlled run of the projected `confidentiality-enforcer.sh`
against a benign 2-line text write produced `EXIT CODE: 2` with a fabricated
`CONFIDENTIALITY VIOLATION`, driven by `ModuleNotFoundError: No module named 'lib'`.

## 2. Root cause

**Single systemic cause:** the installer copies hooks byte-for-byte
(`scripts/cos_init.py:388-420` `install_hook`, and the `--default`/`--full` install loop at
`scripts/cos_init.py:1816-1864`) but never projects the `lib/` package they depend on, and
gives projected hooks no runtime path to it. In the SOURCE repo the hooks' path expressions
(`sys.path.insert($PROJECT_DIR)`, `PYTHONPATH="$OS_ROOT…"`, `$(dirname hook)/..`) happen to
resolve to the repo root, which *does* contain `lib/` — so the defect is invisible in-repo
and only manifests after projection, where those same expressions resolve to a `lib/`-less
consumer root or `.cognitive-os/hooks/`.

The universal import failure produces **two symptom tiers**, determined entirely by each
hook's error handling around the Python call:

- **Tier 1 — hard false-block (severe, 1 hook).** `confidentiality-enforcer.sh` captures
  the scanner heredoc with `2>&1` (line 87) and conflates `PYTHON_EXIT == 1` with "violations
  found" (line 110), so a `ModuleNotFoundError` traceback is mis-parsed as a violation and the
  hook reaches `exit 2  # BLOCK` (line 169). Projected in **both** `--default` and `--full`;
  fires on Edit/Write of any existing file. **Confirmed by real run.**
- **Tier 2 — silent fail-open (the other ~15 default lib-importers).** These wrap the call
  with `2>/dev/null || true`, `|| exit 0`, `$(...)`-capture, or `set -e`-immune command
  substitution (e.g. `rate-limiter.sh` fails open to `"OK"`; `trust-score-validator.sh`
  parses an empty result and warns "missing" then `exit 0`; `completion-gate.sh` wraps every
  `lib.*` call in `|| true`). They exit 0, but the feature (rate limiting, trust parsing,
  queue drain, memory prefetch, phase context, telemetry, etc.) is **dead** in every consumer.

## 3. Options

Ratings scale: HIGH / MEDIUM / LOW (higher = better on that axis, i.e. lower blast radius,
smaller install, easier reversal are "HIGH").

### (a) Full `lib/` projection + shared hook-python-env bootstrap
Deref and ship all of `lib/` to `.cognitive-os/lib/`; install a single
`_lib/hook-python-env.sh` that exports `PYTHONPATH=.cognitive-os/lib`, wired via the
Claude-native settings env where available and sourced from the `_lib` hooks already load.

- **Correctness:** HIGH — every current and future `lib.*` import resolves; no closure gaps.
- **Blast radius:** MEDIUM — installer (`cos_init.py`, ~2 functions) + 1 bootstrap file +
  settings driver; **0** hook edits if env-injected, else one source line per hook. Ships
  **369** modules.
- **Portability (ADR-008):** MEDIUM-HIGH — the sourced-bootstrap path works on any harness
  that copies `.cognitive-os/hooks/`; env-injection is Claude-native only.
- **Install size:** LOW (worst) — ~14 MB / 369 files; drags the *entire* `packages/*` lib
  surface (via 73 dereferenced symlinks) into every consumer, including packages the profile
  never uses.
- **Reversibility:** HIGH — installer-only change; revert + re-init.

### (b) Dependency-closure projection + shared bootstrap
Installer statically computes the transitive `lib.*` import set of the hooks actually
projected for the active profile and ships exactly those modules (plus their intra-`lib`
dependencies) to `.cognitive-os/lib/`, plus the same bootstrap as (a).

- **Correctness:** HIGH for projected hooks — with the caveat that static closure can miss
  dynamic imports (`importlib`, `__getattr__`, string-built module names).
- **Blast radius:** MEDIUM — installer (bootstrap + one new closure-computation module) +
  settings; **0**/≤N hook edits. Ships only the needed modules (tens, not 369).
- **Portability (ADR-008):** HIGH — same portable bootstrap; footprint scales with the
  profile's real hook set, matching the profile-boundary model.
- **Install size:** HIGH (best) — minimal; only referenced modules and their symlink targets
  are dereferenced.
- **Reversibility:** HIGH — installer-only.

### (c) Per-hook PYTHONPATH edits across all 84 hooks (no bootstrap) + project lib
Edit every lib-importing hook to set `PYTHONPATH=.cognitive-os/lib` on each Python
invocation; project `lib` (full or closure) alongside.

- **Correctness:** MEDIUM — only correct if *every* invocation (many hooks call `python3`
  multiple times, some inside heredocs) is edited; high chance of missed call sites.
- **Blast radius:** LOW (worst) — **84 hooks** edited, each with multiple call sites; every
  edit requires the `protected-config-write-guard` bypass; large regression surface.
- **Portability:** MEDIUM — self-contained per hook, but 84× duplicated logic to maintain.
- **Install size:** = chosen lib scope.
- **Reversibility:** LOW — an 84-file diff is painful to audit and revert.

### (d) Fail-safe hardening only — no lib projection (mitigation, NOT a fix)
Make every lib-import hook fail **open**: fix `confidentiality-enforcer.sh` so a
`ModuleNotFoundError` can never be mistaken for a violation (separate the scanner's
`stderr`/import-failure path from the `exit 1 == violations` path), and confirm all Tier-2
hooks stay no-op. Do **not** ship `lib/`.

- **Correctness:** LOW *as a fix* — the features stay dead; this only removes the false
  block. Explicitly a partial mitigation / safety net, not a resolution.
- **Blast radius:** MEDIUM — targeted edits to ~16 default hooks (chiefly the
  `confidentiality-enforcer` `PYTHON_EXIT` conflation); each needs the protected-config bypass.
- **Portability:** N/A — no projection change.
- **Install size:** HIGH — unchanged.
- **Reversibility:** HIGH — small, self-contained edits.

### Combined recommendation (b + shared bootstrap + d safety net + regression test)
Ship the dependency-closure `lib` subset (b) to `.cognitive-os/lib/`, export it via the
shared bootstrap, harden the Tier-1 hook (and confirm Tier-2 fail-open) per (d) so any
closure miss degrades to a silent no-op instead of a false block, and lock the whole
contract with a consumer-sandbox regression test.

## 4. Recommendation

**Adopt the Combined option: (b) dependency-closure projection + shared bootstrap + (d)
fail-safe hardening as a backstop + a projection regression test.**

Justification against the ratings: (b) is the only option that scores HIGH on correctness,
portability, *and* install-size simultaneously — it fixes the real defect (missing `lib`)
while keeping consumer installs proportional to the profile's actual hook set, unlike (a)
which drags all 369 modules and the entire `packages/*` surface into every consumer. (c) is
rejected on blast radius and reversibility (84-file, multi-call-site, guard-gated edits).
(d) alone is rejected because the features stay dead — but folded in as a backstop it is
valuable: it converts the worst failure mode (Tier-1 false `exit 2`) into a safe no-op,
covering the residual risk that static closure misses a dynamic import. The regression test
converts "works once" into an enforced contract.

**Protected-config gating for the apply phase.** `protected-config-write-guard` blocks writes
under `hooks/**` (and `rules/**`, `skills/**`, `.claude/**`, the installer surface) unless
`COS_ALLOW_PROTECTED_CONFIG_WRITE=1` is set. Of this change's surfaces:

- `hooks/_lib/hook-python-env.sh` (new bootstrap) and the (d) edits to
  `hooks/confidentiality-enforcer.sh` + Tier-2 hooks are under `hooks/**` → **guarded**; the
  apply phase MUST run with `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`.
- `scripts/cos_init.py`, `manifests/*.yaml`, and `tests/**` are not under `hooks/**` → not
  guarded by this rule (still subject to the normal review gates).

## 5. Acceptance criteria (verifiable)

Commands are run from the SOURCE repo root unless noted.

1. **Closure lib is projected.** After a real `--full` init into a temp consumer, the
   consumer's `.cognitive-os/lib/` contains every module in the projected hooks' transitive
   `lib.*` closure:
   `python3 scripts/cos_init.py --full <tmp> && test -f <tmp>/.cognitive-os/lib/confidentiality_scanner.py` exits 0.
2. **Bootstrap present and exports the path.** `test -f <tmp>/.cognitive-os/hooks/cos/_lib/hook-python-env.sh`
   exits 0, and sourcing it makes `python3 -c "import lib.confidentiality_scanner"` succeed
   with cwd = consumer root.
3. **No false block (Tier-1).** The projected `confidentiality-enforcer.sh`, run in the
   consumer sandbox (cwd = consumer root, `CLAUDE_PROJECT_DIR` = consumer root, benign
   2-line text write on stdin), exits **0** — not 2.
4. **NEW regression test — consumer-sandbox import contract.** A new test
   (`tests/audit/test_hook_lib_projection.py`, seeded from `…/scratchpad/hook-lib-probe.py`)
   performs a real `cos init` projection into a foreign-cwd temp consumer and, for **every**
   projected lib-importing hook, asserts: (a) no `ModuleNotFoundError` for any `lib.<module>`
   it imports, and (b) no hook produces a false `exit 2` on a benign PostToolUse payload.
   `python3 -m pytest tests/audit/test_hook_lib_projection.py -q` exits 0.
5. **Probe parity.** Re-running the seed probe against a freshly projected consumer reports
   `fail_scenario_ii_projected_only == 0` (was 55 in `--full`, 16 in `--default`).
6. **No SOURCE-repo regression.** `python3 -m pytest tests/audit -q` and the existing
   hook-syntax lane both exit 0.

## 6. Blast radius & rollout

**Surfaces touched**
- `scripts/cos_init.py` — add closure computation + project the closure to
  `.cognitive-os/lib/`; install the bootstrap into `.cognitive-os/hooks/cos/_lib/`
  (extends the existing `_lib` copy at lines 1830-1836 / 1851-1857).
- `hooks/_lib/hook-python-env.sh` — **new** shared bootstrap (guarded).
- `hooks/confidentiality-enforcer.sh` — (d) hardening of the `PYTHON_EXIT`/`2>&1` conflation
  (guarded); spot-confirm Tier-2 hooks already fail open (no edit if they do).
- `manifests/` — record the lib-projection contract (e.g. an entry alongside
  `harness-projection.yaml` / `primitive-consumer-availability.yaml`) so ACC can assert it.
- `tests/audit/test_hook_lib_projection.py` — **new** regression test (§5.4).
- `docs/02-Decisions/adrs/` — a new ADR capturing the contract (follow-on).

**Migration for existing consumer installs.** Consumers pick up the fix by re-running
`cos init` for their profile/harness (the installer is idempotent and overwrites projected
hooks + `.cognitive-os/lib/`). No consumer data is affected; only projected COS files change.
Document a one-line "re-init to receive lib projection" note in the upgrade path.

**Staged rollout.**
1. Land installer closure + bootstrap + `--default` projection; verify §5.1-5.3 on default.
2. Extend to `--full` (55 hooks) and add the regression test (§5.4); gate CI on it.
3. Fold in (d) hardening as the backstop and confirm Tier-2 fail-open.
4. Publish the ADR + upgrade note; recommend consumers re-init.

## 7. Risks & open questions

- **Static-closure misses (primary risk).** Dependency-closure (b) is static; hooks that
  build module names dynamically (`importlib`, `__getattr__`, string interpolation) can be
  missed, re-breaking those hooks. Mitigation: the (d) fail-open backstop makes a miss a
  silent no-op (never a false block), and the §5.4 regression test would catch a miss for any
  hook it exercises. Open question: should the closure over-approximate (ship a small
  allowlisted superset) to reduce miss risk at a modest size cost?
- **Probe caveat carried forward.** The evidence report notes Tier-2 fail-open is
  *static-inferred* for ~15 hooks (only `confidentiality-enforcer` was run for real). Before
  relying on (d) as a universal backstop, the apply/verify phase should actually execute each
  default Tier-2 hook in the sandbox to confirm it fails open — the §5.4 test formalizes this.
- **Symlink / drift concern.** `lib/` contains **73 symlinks** into `packages/*` (e.g.
  `lib/cost_predictor.py -> ../packages/scope-governance/lib/cost_predictor.py`).
  `shutil.copy2` dereferences symlinks, so projected copies are real files — good for
  portability, but they can **drift** from the `packages/*` source over time. Full projection
  (a) drags the entire package lib surface; closure (b) derefs only referenced targets.
  Mitigation: re-init on upgrade + the regression test. Open question: should the installer
  record a provenance/hash of dereferenced modules to detect drift?
- **Bootstrap delivery across harnesses.** Env-injection is Claude-native; other harnesses
  rely on the sourced bootstrap. Open question: is a single sourced `_lib/hook-python-env.sh`
  guaranteed to be loaded by every projected hook, or do some hooks need an added `source`
  line (raising blast radius toward option (c))? This must be resolved in design before apply.
- **Guarded apply.** All `hooks/**` edits need `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`; forgetting
  it will block the apply phase.

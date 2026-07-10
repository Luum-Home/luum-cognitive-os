# Hook `lib/` Projection Breakage — Empirical Forensic Report

- **Date:** 2026-07-08
- **Repo:** luum-cognitive-os (COS source)
- **Question:** How many projected COS hooks actually fail with `ModuleNotFoundError: No module named 'lib'` (or non-zero / exit-2) in a real consumer install, and is `lib/` reachable by projected hooks?
- **Method:** Real projection into temp consumer sandboxes via the actual installer (`scripts/cos_init.py`), isolated `import cos_lib.<module>` probes replicating each hook's consumer runtime, plus ONE controlled real hook run. No hook bodies executed except the single documented ground-truth run. Repo not mutated.

---

## 1. Decisive projection facts (with citations)

### (a) Is `lib/` projected into the consumer? NO — only a 2-module subset.

The consumer install is produced by `scripts/cos_init.py` (invoked by `cos init`; the `curl | bash` `scripts/install-cos.sh` only installs the Go `cos` binary and never touches `lib/`).

- Hooks are copied **byte-for-byte** to `.cognitive-os/hooks/cos/<name>.sh` with `shutil.copy2` and only a chmod — no wrapping, no env injection: `scripts/cos_init.py:388-420` (`install_hook`) and `scripts/cos_init.py:1816-1864` (hook install loop, both `--default` and `--full`).
- The ONLY Python `lib/` content shipped is a hard-coded 2-module subset for the duplicate-code scanner: `scripts/cos_init.py:1436-1462` copies exactly `duplicate_scanner.py` and `project_paths.py` into `.cognitive-os/lib/` plus a stub `__init__.py`. Nothing else from `lib/` is ever projected.
- Empirically verified in a real `--full` projection: `.cognitive-os/lib/` contains only `__init__.py`, `duplicate_scanner.py`, `project_paths.py`; there is **no root-level `lib/`** in the consumer at all.
- `grep -rn '\.cognitive-os/lib' scripts/ manifests/ tests/` returns **zero** references to `.cognitive-os/lib` as a general hook import target — it exists solely for the duplicates primitive.

### (b) Can projected hooks reach `lib/` at runtime? NO.

Projected hooks run with `cwd = consumer project root` and settings.json wires them with **no `PYTHONPATH`** and no path to any full `lib/` (`scripts/_lib/settings-driver-claude-code.sh:60-74`; consumer settings reference `.cognitive-os/hooks/cos/…` only). How each hook tries (and fails) to reach `lib/`:

- **74 hooks use `sys.path.insert(...)`**, but the inserted path is never a full `lib/` host:
  - 43 insert `$PROJECT_DIR` / `CLAUDE_PROJECT_DIR` → **consumer root** (no `lib/`).
  - 2 insert `COGNITIVE_OS_HOOK_ROOT` (= `$(dirname hook)/..`) → **`.cognitive-os/hooks/`** (no `lib/`), e.g. `hooks/rate-limiter.sh:108`.
  - `ROOT` / `OS_ROOT` / `COS_ROOT` (also `$(dirname hook)/..`) → **`.cognitive-os/hooks/`** (no `lib/`).
- **16 hooks set `PYTHONPATH=`** (via `grep`), but every target resolves to a `lib/`-less dir in the consumer: `$PROJECT_DIR`/`$_PROJECT_DIR` → consumer root; `$OS_ROOT`/`$COS_ROOT`/`$os_root`/`$ROOT`/`$HOOK_DIR/..` → `.cognitive-os/hooks/`. In the **source repo** these same expressions resolve to the repo root (which has `lib/`), which is exactly why the bug is invisible in-repo.
- **None of the 84 lib-importing hooks import the only two projected modules** (`cos_lib.duplicate_scanner`, `cos_lib.project_paths`) — they all import other `cos_lib.*` modules that are simply not on disk anywhere in a consumer.

**Conclusion:** `lib/` is not projected, and no projected hook can reach the modules it imports.

---

## 2. Enumeration

- **84 hooks** in `hooks/*.sh` contain a `from cos_lib.` / `import cos_lib.` / `-m cos_lib.` statement (measured; the orchestrator's earlier "76" is a close undercount — the delta is hooks whose import appears alongside a `sys.path` setup line).
- **16 of the 84 set `PYTHONPATH`** on the relevant invocation; the other 68 rely on cwd or `sys.path.insert`.
- Per-hook module lists and PYTHONPATH classifications are captured in the probe table (scratchpad `probe-table.json`).

---

## 3. Empirical import probe (no hook bodies executed)

For each of the 84 hooks, `python3 -c "import cos_lib.<module>"` was attempted with `cwd = consumer root` and `PYTHONPATH` bound exactly as the hook sets it (empty when it sets none), under two scenarios:

| Scenario | Consumer `lib` state | lib-importing hooks that FAIL |
|---|---|---|
| (i) `lib` NOT projected at all | no `lib` anywhere | **84 / 84** |
| (ii) subset projected (REALITY) | `.cognitive-os/lib/` = {duplicate_scanner, project_paths} | **84 / 84** |

- **Passers under either scenario: 0.**
- Of the 84, **55 are actually wired into a `--full` consumer** (`.cognitive-os/hooks/cos/`); all 55 fail. **16 are wired into a `--default` consumer** (the common install); all 16 fail. The remaining 29 are never projected even in `--full` (fragile but not a consumer runtime surface).
- **Positive control:** the same imports (`cos_lib.confidentiality_scanner`, `cos_lib.peer_card`, `cos_lib.rate_limiter`) succeed with `cwd = repo root` and no PYTHONPATH — confirming the probe measures the projection gap, not a broken probe.

---

## 4. Ground truth — one controlled real run (`confidentiality-enforcer.sh`)

Ran the **projected** `.cognitive-os/hooks/cos/confidentiality-enforcer.sh` once in the `--full` consumer sandbox (`cwd = consumer root`, `CLAUDE_PROJECT_DIR = consumer root`, no `PYTHONPATH`), feeding a benign `PostToolUse`-style stdin `{"tool_name":"Write","tool_input":{"file_path":"<sandbox>/benign.txt"}}` for a harmless 2-line text file.

**Observed:**
```
EXIT CODE: 2
STDERR:
CONFIDENTIALITY VIOLATION: prohibited content found in <sandbox>/benign.txt
  Line 0 [?]: ?
  Line 0 [?]: ?
  Line 0 [?]: ?
```

Root cause reproduced explicitly by running the hook's inner import as the hook does (`python3 -` heredoc, `cwd = consumer root`, no PYTHONPATH):
```
inner exit: 1
Traceback (most recent call last):
  File "<stdin>", line 2, in <module>
ModuleNotFoundError: No module named 'lib'
```

**Mechanism** (`hooks/confidentiality-enforcer.sh:87-108,110,151,169`): the scanner heredoc captures stderr with `2>&1` and exits **1** on `ModuleNotFoundError`; the hook treats `PYTHON_EXIT == 1` as "violations found", fails to parse the traceback as JSON (`[?]` fields), and reaches `exit 2 # BLOCK`. A benign write is reported as a confidentiality violation — a **false-positive hard block**, not a silent no-op.

---

## 5. True blast radius

Every lib-importing hook's import **does** break in a consumer (84/84 in isolation; 55/55 wired in `--full`, 16/16 wired in `--default`). But hook-level severity splits into two tiers based on error handling around the `lib` call:

- **Tier 1 — hard failure / false block (severe):** `confidentiality-enforcer.sh`. It is projected in BOTH `--default` and `--full`, fires on Edit/Write of any existing file, and propagates `exit 2` with a fabricated "CONFIDENTIALITY VIOLATION". **Confirmed by real run.** This is the one that surfaced.
- **Tier 2 — silent feature degradation (fail-open):** the large majority of the other 15 default-projected lib-importers wrap the call with `2>/dev/null || true` / `|| exit 0` / `|| echo "OK"` (e.g. `rate-limiter.sh:161` fails open to `"OK"` and never blocks; `memory-prefetch`, `session-init`, `pre-compaction-flush`, `task-created/completed`, `teammate-idle`, `user-prompt-capture`, `trust-score-validator`, `crash-recovery`, `inject-phase-context`, `session-wrapup-trigger`, `claim-validator`, `completion-gate`). These exit 0 but their feature is **dead** in every consumer — the OS silently loses memory prefetch, rate limiting, telemetry, trust parsing, phase context, etc.

**One-line blast radius:** In a default consumer install, **16/16** wired lib-importing hooks are non-functional; **1** of them (`confidentiality-enforcer`) actively and falsely **blocks** every Edit/Write with `exit 2`, and the other 15 **silently degrade** to no-ops. In a full install the count rises to **55/55** broken. Root cause is systemic and single: the installer projects hooks that `import cos_lib.*` but never projects the `lib/` package (only a 2-module duplicates subset) and gives projected hooks no path to it.

---

## 6. Static vs. real-run agreement

No disagreements. Static inference (all `cos_lib.*` imports unreachable in consumer), the isolated import probe (84/84 fail, 0 passers), and the real `confidentiality-enforcer` run (`exit 2`, `ModuleNotFoundError: No module named 'lib'`) all agree. One refinement the real run adds beyond static counting: the *hook-level* consequence is bimodal (Tier-1 false-block vs Tier-2 silent-degradation), driven by each hook's `|| true`/`2>/dev/null` handling — the import failure is universal, the visible symptom is not.

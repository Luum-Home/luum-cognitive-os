# Research — Python Major Bumps Probe (2026-04-24)

**Type**: Research-only (per ADR-069)
**Decision Status**: Awaiting operator triage
**Implementation NOT performed** (no actual upgrade)

---

## TL;DR

Of the three majors, **cryptography 46→47** is the most pressing: it dropped binary
elliptic curves, changed exception types, and is the only one with active CVE-adjacent
advisories in prior versions (Bleichenbacher, buffer overflow). The `default_backend()`
pattern used in `hermes-agent` is long-deprecated (since 36.0.0) but not yet removed in
47.0.0 — no immediate break, but the clock is ticking toward 49.0.0 removals.
**rich 14→15** is the safest upgrade: single breaking change is dropping Python 3.8,
which this repo does not use (requires ≥3.11). **wrapt 1.17→2.x** is indirect-only
(no first-party code imports it), but `deprecated`, `opentelemetry-instrumentation`, and
`testcontainers` all depend on it — requires transitive compatibility validation.

---

## Per-Package Analysis

### wrapt 1.17.3 → 2.1.2

**Direct usage in lib/, scripts/, tests/, hooks/**: None detected.

**Transitive consumers (from `uv tree`):**
- `deprecated` 1.3.1
- `openinference-instrumentation` 0.1.47
- `openinference-instrumentation-openai`
- `opentelemetry-instrumentation` 0.62b1
- `testcontainers[redis]` ≥4.0
- `arize-phoenix` 14.6.0
- `arize-phoenix-otel` 0.16.0

**Breaking changes 1.x → 2.x (released 2026-03-06):**
- `getcallargs()` and `formatargspec()` removed from wrapt module (use `inspect` directly)
- `BaseObjectProxy` replaces the internal `ObjectProxy` core; `AutoObjectProxy` and
  `LazyObjectProxy` added
- `ObjectProxy` raises `WrapperNotInitializedError` (subclass of both `ValueError` and
  `AttributeError`) instead of bare `ValueError`
- `enabled`, `adapter`, `proxy` args to `@decorator` changed to keyword-only
- Runtime dependency on `setuptools` removed (now uses `importlib.metadata`)
- Requires Python ≥3.9 (repo requires ≥3.11 — satisfied)

**Deprecated APIs we use directly**: None (no direct imports).

**Transitive compatibility risk**: Medium. None of the transitive consumers specify an
upper bound for wrapt in `uv.lock` (`{ name = "wrapt" }` with no version constraint),
but whether `deprecated` 1.3.1 and `opentelemetry-instrumentation` 0.62b1 are tested
against wrapt 2.x is unknown without checking their own test matrices. The
`WrapperNotInitializedError` change could cause subtle failures in packages that catch
`ValueError` from uninitialized proxies.

**CVEs in wrapt 1.17.3**: None known.

**Estimated breakage on upgrade**: **Low** (no direct usage; dependent packages have no
explicit upper bound). Low confidence — transitive packages may fail if they rely on
removed `getcallargs`/`formatargspec` or the old exception type.

**Recommendation**: **Wait** until transitive consumers explicitly support 2.x. Pin at
1.x for now. Check `opentelemetry-instrumentation` and `deprecated` changelogs before
upgrading.

**Effort if upgrade proceeds**: 1-2h (no first-party code to change; effort is verifying
transitive packages pass tests under 2.x).

---

### rich 14.3.4 → 15.x

**Direct usage**: 1 file — `scripts/cos_watch.py`

**APIs used** (lines 221-333):
- `rich.live.Live`
- `rich.panel.Panel`
- `rich.text.Text`
- bare `import rich` (availability check)

**Breaking changes 14.x → 15.x:**
- **Python 3.8 dropped** — only breaking change documented in 15.0.0
- No removed or renamed public APIs documented
- No changes to `Live`, `Panel`, or `Text` APIs

**Deprecated APIs we use**: None detected. The three APIs used (`Live`, `Panel`, `Text`)
are stable core APIs with no documented removal plan.

**Transitive consumers from `uv tree`:**
- `typer` 0.24.2 (depends on rich)
- `unclecode-litellm` (via typer)
- `import-linter` 2.11 (depends on rich)
- `arize-phoenix` 14.6.0 (depends on rich)

None of these specify an upper bound on rich in `uv.lock`.

**CVEs in rich 14.3.4**: None known. rich is a terminal rendering library with minimal
attack surface.

**Estimated breakage on upgrade**: **Negligible** (high confidence). This repo requires
Python ≥3.11; the only breaking change — dropping 3.8 — does not affect us. All three
APIs in `cos_watch.py` remain unchanged.

**Recommendation**: **Upgrade** — safe, no code changes needed.

**Effort if upgrade proceeds**: <30 minutes (bump version, run tests).

---

### cryptography 46.x → 47.0.0

**Note**: `uv.lock` already pins `cryptography = 47.0.0`. The "upgrade" scenario is
about verifying correctness of the current lock, not about bumping further.

**Direct usage in lib/, scripts/, tests/**: None detected in main source tree.

**Direct usage in `.claude/plugins/hermes-agent/`** (plugin code):
- `gateway/platforms/wecom_crypto.py` — `default_backend()`, AES/CBC
- `gateway/platforms/weixin.py` — `default_backend()`, AES/CBC and AES/ECB
- `gateway/platforms/wecom.py` — `Cipher`, `algorithms`, `modes` (AES/CBC)
- `gateway/platforms/qqbot/crypto.py` — `AESGCM`
- `skills/creative/excalidraw/scripts/upload.py` — `AESGCM`
- `tests/gateway/test_wecom.py` — `Cipher`, `algorithms`, `modes`

**Deprecated APIs we use:**

| API | Deprecated since | Removed in | Status |
|-----|-----------------|-----------|--------|
| `default_backend()` | 36.0.0 | Not yet (still functional in 47.x) | Warning-level only |
| `Cipher(..., backend=default_backend())` | 36.0.0 | Not yet | Warning-level only |
| AES/CBC (from main `modes`) | N/A | Not in 47.x | Safe |
| CFB, OFB, CFB8 modes | Moved to Decrepit in 47.x | Future (not 47.x) | Safe for now |

`default_backend()` is still importable in 47.x and issues a deprecation warning, not
an error. The plugin files pass `backend=default_backend()` to `Cipher(...)` — this
pattern is deprecated since 36.0.0 but still works in 47.0.0. However, scheduled for
removal in a future release (~49.0.0 based on cryptography's cadence).

**Breaking changes affecting our code:**
- `SECT*` binary curve removal: we do not use SECT curves → no impact
- Exception type change (`UnsupportedAlgorithm` vs `ValueError`): hermes-agent does not
  catch `ValueError` from key loading in the audited files → no immediate break
- AES/CBC, AES/ECB, AESGCM all remain in main module → no impact

**Transitive consumers:**
- `pyjwt[crypto]` 2.12.1 (uses cryptography for JWT signing)
- `authlib` 1.7.0
- `joserfc` 1.6.4
- `pyopenssl` 26.1.0

**CVE exposure in versions prior to 47.0.0:**
Known advisories affecting cryptography ≤46.x (OSV database):
- `GHSA-p423-j2cm-9vmq`: Buffer overflow with non-contiguous buffers (Medium, 6.9)
- `GHSA-r6ph-v2qm-q3c2`: Subgroup attack on SECT curves (High, 8.2) — fixed by removal
  of SECT curves in 47.0.0
- `GHSA-3ww4-gg4f-jr7f`: Bleichenbacher timing oracle (High, 8.7)
- `GHSA-cf7p-gm2m-833m`: SSH certificate mishandling (High, 8.7)

The `GHSA-r6ph-v2qm-q3c2` SECT-curve vulnerability is directly addressed by the 47.0.0
removal. The others require checking exact affected version ranges.

**Estimated breakage on upgrade to 47.0.0**: **Low** for main codebase. The lock is
already at 47.0.0. The hermes-agent plugin uses deprecated `default_backend()` but it
still works — emit warnings, not errors, in 47.x. Medium confidence that tests still
pass; deprecation warnings should not break test runs unless `-W error` is set.

**Recommendation**: 47.0.0 is already locked — **maintain current pin**. Schedule
removal of `default_backend()` pattern in hermes-agent for pre-49.0.0 cycle. No urgent
action needed unless deprecation warnings are being treated as errors.

**Effort to clean up `default_backend()`**: ~1h across 3 hermes-agent files (mechanical
substitution: remove `backend=default_backend()` from `Cipher(...)` calls, remove the
import).

---

## Cross-Package Transitive Risk

| Upstream Package | Requires wrapt | Requires rich | Requires cryptography |
|----------------|---------------|--------------|----------------------|
| arize-phoenix 14.6.0 | ✓ (no upper bound) | ✓ (no upper bound) | — |
| arize-phoenix-otel 0.16.0 | ✓ | — | — |
| opentelemetry-instrumentation 0.62b1 | ✓ | — | — |
| deprecated 1.3.1 | ✓ | — | — |
| typer 0.24.2 | — | ✓ | — |
| import-linter 2.11 | — | ✓ | — |
| pyjwt[crypto] 2.12.1 | — | — | ✓ |
| authlib 1.7.0 | — | — | ✓ |
| pyopenssl 26.1.0 | — | — | ✓ |

No package specifies an upper-bound version constraint on any of the three in `uv.lock`,
so the resolver would accept new versions. The risk is runtime behavior, not resolution
failure.

---

## Decision Points

| Package | Direct usage in our code? | Deprecated API used? | Transitive deps demand old? | Recommendation |
|---------|--------------------------|---------------------|----------------------------|----------------|
| wrapt 1.17→2.1.2 | No | No | Not explicitly pinned; risk unknown | **Pin at 1.x / Wait** |
| rich 14→15 | Yes (1 file, stable APIs only) | No | No upper bounds | **Upgrade — safe** |
| cryptography 46→47 | No (main); Yes (hermes-agent plugin, deprecated pattern) | `default_backend()` deprecated since 36.x, not yet removed | No upper bounds | **Already at 47.0.0 — maintain; clean up `default_backend()` pre-49.x** |

---

## Recommended Order

1. **rich 14→15**: upgrade now, zero risk, no code changes needed
2. **cryptography**: already at 47.0.0; schedule `default_backend()` cleanup for
   hermes-agent before 49.0.0 cycle
3. **wrapt 1.x→2.x**: wait until `opentelemetry-instrumentation` and `deprecated`
   packages explicitly validate against wrapt 2.x

---

## Open Questions

1. Do any CI flags (`-W error::DeprecationWarning`) convert cryptography's
   `default_backend()` deprecation warnings into errors? If so, hermes-agent tests
   would already be failing.
2. Are `opentelemetry-instrumentation` 0.62b1 and `deprecated` 1.3.1 tested against
   wrapt 2.x upstream? Check their changelogs before upgrading.
3. Is hermes-agent (`/.claude/plugins/hermes-agent/`) within the upgrade scope for this
   repo, or managed separately? The cryptography usage is entirely within that plugin.
4. The `uv.lock` already resolves to cryptography 47.0.0 but `uv pip list` did not
   surface `wrapt` or `rich` — confirm these are installed in the active venv with
   `uv sync --all-extras` before testing.

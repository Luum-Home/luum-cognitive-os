# Cutting the synthesis-serving channel in the context injector

**Date:** 2026-08-15
**Scope:** `cos_lib/context_injector.py`, `tests/integration/test_query_tailored_context.py`
**Outcome:** channel cut, 419 pages no longer served into agent context, 0 files deleted.

---

## 1. The premise, re-counted

The errand's two load-bearing claims were re-verified from scratch, not taken on trust.

**419 synthesis pages — confirmed.**

```bash
git ls-files '*.synthesis.md' | wc -l
#    419
```

All 419 resolve to a source document; there are no orphans. Command in §5.

**The injector scored the source and served the summary — confirmed.**
`cos_lib/context_injector.py` at HEAD `fe888ab7f` contained `_prefer_synthesis()`,
whose own docstring said it *"scores the richer raw doc but SERVES the synthesis
page when one exists"*. It had two call sites: `_search_adrs` (ADRs) and
`_search_docs` (04-Concepts, 05-Methodology, 07-Capabilities, 08-References,
09-Quality).

```bash
git grep -n '_prefer_synthesis' -- '*.py'
# cos_lib/context_injector.py:206:def _prefer_synthesis(raw: Path) -> Path:
# cos_lib/context_injector.py:280:            served = _prefer_synthesis(md_file)
# cos_lib/context_injector.py:339:                served = _prefer_synthesis(md_file)
```

Demonstrated end-to-end against the real repo, HEAD's module vs. the same query:

```
QUERY: testing strategy and lane taxonomy for the quality suite
  HEAD  -> docs/09-Quality/root/testing-cognitive-os-suite.synthesis.md
  now   -> docs/09-Quality/root/testing-cognitive-os-suite.md
```

**One correction to the errand's framing.** The injector emits *paths*, not file
content — `_format_context` writes one bullet per match (`[SOURCE] \`path\`
(score=N): title`), and the excerpt is the `# ` title parsed from the **source**
doc, not from the synthesis page. So the drift was never injected text; it was a
*pointer* handed to the agent, which then read the stale page. The channel is
real, the mechanism is one step longer than "the summary gets injected".

**Drift, measured rather than repeated.** The errand said three pages carry
figures their sources no longer have. Re-measured across all 419 pairs, counting
3-or-more-digit figures present in a synthesis page and absent from its source:

```
pairs checked: 419
synthesis pages carrying >=1 figure ABSENT from their source: 54 (13%)
    8 orphan figures  docs/04-Concepts/architecture/rust-migration-script-inventory.synthesis.md
                      e.g. 1,201 / 1,330 / 2,501 / 214,003 / 237,404
    6 orphan figures  docs/08-References/business/portability-plan.synthesis.md
    4 orphan figures  docs/08-References/business/features.synthesis.md
```

This is a **lower-bound heuristic with known false positives** — zero-padded ADR
identifiers (`093`, `241`) parse as figures. The top offender is genuine drift:
line-count inventories the source has since revised. Treat "54" as the ceiling of
a set whose floor is comfortably above zero, not as a precise count.

---

## 2. The change

`cos_lib/context_injector.py`. The remap was **removed**, not neutered — leaving a
function named `_prefer_synthesis` that returns `raw` would have been the cheap
green: the next reader assumes the name still describes the behavior.

- `_prefer_synthesis()` deleted (37 lines).
- Both call sites serve `md_file` directly.
- The section it occupied now carries the invariant in prose: *the injector serves
  the source document and nothing else*, with the reason (single unverified LLM
  pass at `9cf6612e3`, no generator, figures frozen at copy time) and the
  precondition for ever re-introducing a remap (a verified generator that keeps
  pages in sync).
- The `*.synthesis.md` skip during scoring stays, and its comments were rewritten:
  the pages used to be skipped *because they were the remap target*; they are now
  skipped because they are excluded outright. Same line of code, different reason,
  so the reason is now written down.
- `_search_docs`'s docstring and the step-4 comment in `build_context` updated to
  match.

**Blast radius:** one module, no signature changes, no config, no hooks. Fully
reversible with `git revert`.

**Protection check.** `cos_lib/**` is *not* write-protected.
`hooks/protected-config-write-guard.sh` (registered, 1 occurrence in
`.claude/settings.json`) covers `.claude/**`, `hooks/**`, `rules/**`,
`skills/*/SKILL.md`, `mcp.json` and three `manifests/*` entries — `cos_lib/**` is
absent from `protected_globs`. The edit applied directly; no patch-and-runbook
handoff was needed.

```bash
grep -c 'protected-config-write-guard' .claude/settings.json   # 1
grep -n 'protected_globs' hooks/protected-config-write-guard.sh
```

---

## 3. The test that pinned the defect

`tests/integration/test_query_tailored_context.py` had **four** tests asserting the
old behavior, not one: `test_non_adr_doc_serves_synthesis_sibling`,
`test_non_adr_doc_raw_fallback_when_no_synthesis`,
`test_adr_synthesis_behavior_unchanged`, and `test_prefer_synthesis_helper`.

They were rewritten to fix the correct property, and the missing case was added.
The suite now asserts:

| Test | Property fixed |
|---|---|
| `test_non_adr_doc_serves_source_when_synthesis_also_exists` | **the case the old suite lacked** — when *both* exist, the source is served and no `.synthesis.md` appears anywhere in the block |
| `test_non_adr_doc_serves_source_when_no_synthesis` | a doc without a sibling is served as itself |
| `test_adr_serves_source_when_canonical_synthesis_exists` | same invariant on the ADR path (`ADR-NNN.synthesis.md`) |
| `test_adr_serves_source_when_slugged_synthesis_exists` | the old remap's *second* fallback (`ADR-NNN-<slug>.synthesis.md`) does not resurface |
| `test_synthesis_pages_are_never_scored_as_documents` | excluding pages from serving did not promote them to independently scored documents |

The unit-level `_prefer_synthesis` helper test was dropped rather than adapted —
there is no helper left to unit-test, and keeping a shim to preserve the test
would have been the tail wagging the dog.

**They fail against the old code.** `git worktree` is blocked by
`destructive-git-blocker` (ADR-055b), so HEAD's module was reconstructed into a
scratch package and the *new* tests run against it:

```bash
S=<scratch>/oldcode1; mkdir -p "$S/cos_lib" "$S/tests/integration"
git show HEAD:cos_lib/__init__.py         > "$S/cos_lib/__init__.py"
git show HEAD:cos_lib/context_injector.py > "$S/cos_lib/context_injector.py"
cp tests/integration/test_query_tailored_context.py "$S/tests/integration/"
(cd "$S" && pytest tests/integration/test_query_tailored_context.py -q)
# 3 failed, 7 passed     <- the three source-of-truth assertions
```

Against the change:

```bash
.venv/bin/pytest tests/integration/test_query_tailored_context.py -q
# 10 passed in 0.06s
```

`test_synthesis_pages_are_never_scored_as_documents` passes on both sides by
design — it guards a regression the change could have introduced, not one it fixed.

**Full regression sweep**, every test touching the injector:

```bash
git grep -ln 'context_injector' -- tests/ | xargs .venv/bin/pytest -q
# 81 passed, 7 skipped in 53.81s
```

---

## 4. Token impact

The concern was that serving sources means serving longer documents. Measured, it
splits into two very different numbers.

**The injected block itself is flat.** Because the injector emits paths, the only
change to the block is the path string. Summed over all 419 pairs the difference
is **+290 characters (~+72 tokens total)** — and only 3 paths (`TOP_K=3`) appear in
any given block, so the per-turn cost of the change is **under 1 token**.

**The downstream read is where the cost lives**, if and when an agent opens the
file it was pointed at:

| | bytes | ~tokens |
|---|---:|---:|
| 419 source docs | 5,264,548 | 1,316,137 |
| 419 synthesis pages | 1,597,570 | 399,392 |
| **delta if every pair were read** | **+3,666,978** | **+916,744** |

Sources run **3.30x** their synthesis pages. Per document: median source 10,498 B
(~2,624 tok) against median synthesis 3,749 B (~937 tok).

**Realistic worst case per turn:** all three `TOP_K` hits are doc matches with
synthesis siblings, and the agent reads all three in full — **~+5,062 tokens**.
Against the 374,047-token turn baseline this session measured, that is **~1.35%**,
comparable to the 1.08% fixed markdown overhead already accepted. Typical turns
land well below it: most blocks mix `[CODE]` and `[DOCS]` hits, and an agent
rarely reads all three matches end to end.

**Verdict: no truncation or on-demand summarization needed.** The margin is there.
If a future measurement shows real turns clustering near the worst case, the
answer is bounded reads (head-N or section extraction at read time), not restoring
the remap — a truncated source is still the source.

---

## 5. What still points at the synthesis pages

`git grep -lI 'synthesis\.md'` over the repo, excluding the pages themselves and
daily reports, returns 17 files. They classify cleanly — and **only one was a
serving consumer**, which is the one just cut.

**Served them into agent context (the drift channel)**
- `cos_lib/context_injector.py` — **cut by this change.**

**Resolves them deliberately, by design**
- `scripts/adr_kb_benchmark.py` — a *retrieval benchmark*; resolving gold ADRs to
  their synthesis page is what it measures. Left alone: it is an instrument, not a
  serving path. Worth revisiting only if the benchmark is being read as evidence
  that synthesis retrieval is good.

**Validate the pages (schema enforcement)**
- `.github/workflows/okf-validation.yml`, `scripts/validate_okf.py`,
  `scripts/okf-schema.json` — enforce OKF frontmatter on `docs/**/*.synthesis.md`.
  Still green; they validate shape, never content or freshness.

**Exclude them (they already treat the pages as derivatives)**
- `scripts/audit_adr_status_links.py`, `scripts/generate_adr_index.py`,
  `tests/audit/test_adr_contracts.py`,
  `tests/audit/test_agent_training_harness_claims.py`,
  `tests/audit/test_anthropic_api_key_references.py`,
  `tests/audit/test_plan_locations.py` — each filters `*.synthesis.md` out. These
  corroborate the change: the repo already treated the pages as non-authoritative
  everywhere except the one place that served them.

**Index/MOC mentions**
- `docs/00-MOCs/entrypoints/INDEX.md`, `docs/02-Decisions/adrs/INDEX.md`,
  `docs/00-MOCs/adr-kb-benchmark-questions.md`.

### Two items now stale — reported, not touched

1. **`scripts/docs_reader_audit.py` — the reachability model that made them
   load-bearing.** Its `resolve_synthesis()` propagates the stronger verdict across
   each pair, justified in-code as *"context_injector.py serves one in place of the
   other"*. That justification is now false. This is precisely the mechanism the
   pruning agent cited when it declined to touch the pages. It is **not wired to
   any gate** (`git grep -ln 'docs_reader_audit' -- .github/ hooks/ scripts/ tests/
   manifests/ Makefile` returns only the script itself), so nothing breaks today —
   but until it is updated, the audit will keep vouching for 419 pages that no
   reader reaches.

2. **`manifests/volatile-number-baseline.json` — 52 of 281 entries (18.5%) are
   accepted volatile numbers inside synthesis pages.** With the pages no longer
   served, those 52 suppressions cover figures nothing consumes. A suppressor that
   suppresses nothing is a gate, per `gates-sin-trampa`. Not moved here: pruning a
   baseline is a decision, and it belongs with the disposition question below.

---

## 6. How many files are now inert

**419.** All 419 git-tracked `*.synthesis.md` pages are, as of this change, no
longer reachable by any path that puts them in front of an agent. What remains is
schema validation (OKF), one benchmark that resolves them on purpose, a stale
reachability model, and 52 baseline entries.

**Nothing was deleted, as instructed.** Disposition is a separate decision and is
now a much cheaper one to make: with the serving channel cut, deleting them cannot
silently change what any agent reads.

Suggested sequencing when that decision is taken, in dependency order:
`docs_reader_audit.resolve_synthesis()` -> the 52 baseline entries ->
`adr_kb_benchmark.py`'s gold-page resolution -> the pages themselves.

---

## 7. Corrections to the errand's premises

The errand invited refutation. Five items:

1. **"419 files, injector serves the summary" — both held.** Independently
   re-counted and re-read. No reason to stand down.

2. **`engram_crystallizer.py`, `engram_lifecycle.py` and `settings-driver-bare.sh`
   are not consumers.** The errand flagged them as possible consumers while warning
   that "synthesis" names two different things. It does, and these are the other
   one: all three have **zero** `.synthesis.md` matches
   (`grep -c 'synthesis\.md'` -> 0) and match only on skill-synthesis vocabulary.
   The warning was right; the file list attached to it was not.

3. **The test that pinned the defect was four tests, not one.** Line 265 was the
   one cited; `test_non_adr_doc_raw_fallback_when_no_synthesis`,
   `test_adr_synthesis_behavior_unchanged` and `test_prefer_synthesis_helper` also
   asserted the old behavior. Fixing only the cited one would have left three tests
   failing and the defect half-pinned.

4. **The synthesis pages are not injected as text.** They are handed over as
   paths. This does not weaken the case for the cut — it explains why the token
   saving the original design claimed (~61% reduction, per the ADR-knowledge-pilot
   design note referenced in the deleted comment) was never realized in the block
   itself, and was only ever realized if the agent read the file.

5. **"Three pages still carry figures their sources no longer have" understates
   it** — 54 of 419 do, by a heuristic that is a lower bound in coverage and an
   upper bound in precision. The direction of the errand's claim was right; the
   magnitude was low by roughly an order of magnitude.

**Nothing in the errand required standing down.** The one outcome that would have
meant "touch nothing" — the injector already serving sources, or the pages having
been verified by some process nobody found — did not materialize. `9cf6612e3`
remains the only production event, its own message still says `UNVERIFIED ...
pending sdd-verify`, and no generator exists.

---

## 8. Reproducing every figure in this report

```bash
# 419 pages, all with resolvable sources
git ls-files '*.synthesis.md' | wc -l

# size delta, path-string delta, and the drift census (§1, §4)
#   the three python blocks used are inline in this report's history; each
#   walks `git ls-files '*.synthesis.md'`, resolves the source sibling
#   (X.synthesis.md -> X.md, ADR-NNN.synthesis.md -> ADR-NNN-<slug>.md),
#   and sums st_size / diffs \b\d[\d,]{2,}\b sets.

# the cut, proven end to end
.venv/bin/python -c "
from cos_lib.context_injector import build_context
ctx = build_context('testing strategy and lane taxonomy for the quality suite',
                    project_root='.', use_cache=False)
print(ctx); print('synthesis served:', '.synthesis.md' in ctx)"
# -> synthesis served: False

# the tests
.venv/bin/pytest tests/integration/test_query_tailored_context.py -q   # 10 passed
git grep -ln 'context_injector' -- tests/ | xargs .venv/bin/pytest -q  # 81 passed, 7 skipped

# consumer census (§5)
git grep -lI 'synthesis\.md' -- . ':!*.synthesis.md' ':!docs/06-Daily/reports/*'
grep -c 'synthesis\.md#' manifests/volatile-number-baseline.json       # 52
```

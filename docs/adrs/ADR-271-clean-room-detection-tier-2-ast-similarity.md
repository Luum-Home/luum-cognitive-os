# ADR-270 — Clean-Room Detection Tier 2: AST-Normalized Similarity

## Status

Proposed (2026-05-11)

## Context

ADR-267 Hook #2 (`hooks/external-cache-content-leak.sh` + `scripts/cos_verbatim_copy_detector.py`)
ships verbatim-hash detection (Tier 1 per `rules/clean-room-detection-limits.md`).
It catches byte-near-identical copies of external-source-cache content in
staged files. It does NOT catch:

- **Symbol-renamed clones** — identifiers / function names changed but body
  identical.
- **Structural ports** — same algorithm, reordered code, different formatting.
- **Paraphrased adaptations** — reworded but semantically equivalent.
- **Pseudocode / prose descriptions** — natural-language descriptions of
  upstream code.
- **Conceptual / design-level reuse** — pattern lift without code copy.

The first two are mechanically detectable. The last three require T3 (semantic
embeddings), T4 (LLM-assisted review), or T5 (process / legal) per the matrix
in `rules/clean-room-detection-limits.md`.

ADR-029b already shipped a Phase B-alpha tokeniser (Jaccard on docstring + name
tokens) for the orthogonal anti-reinvention use case, plus a deferred Phase B-beta
for embeddings. Tier 2 for clean-room defense should reuse that infrastructure
where possible — same shape of problem (semantic similarity), different corpus
(external-source-cache instead of the COS tree).

## Decision

Build **`hooks/clean-room-ast-similarity-gate.sh`** plus
**`scripts/cos_clean_room_ast_similarity.py`** as ADR-267 Hook #8 (the next
slot after Hook #7 lib-symlink-invariant in commit `01929d8c`).

### Detection approach (Python first; other languages deferred)

1. Walk staged Python files (only `.py` for v1).
2. Parse each into AST via `ast` stdlib module.
3. Normalize the AST:
   - Replace every variable, function, class, and parameter identifier with a
     positional placeholder (`_v1`, `_v2`, ...) keyed by first-occurrence order.
   - Strip docstrings and comments (do this on source pre-parse).
   - Strip type annotations (Python evaluates type hints later; for similarity
     they are noise).
4. Serialize the normalized AST to a canonical string via `ast.dump(node, annotate_fields=False, include_attributes=False)`.
5. Compute SHA-256 of canonical AST string per top-level function and class.
6. Compare against pre-computed normalized-AST hashes of every `.py` file in
   `.cognitive-os/external-source-cache/`.
7. Report matches with: COS file, function/class name, upstream file +
   function/class, similarity classification (exact-AST / partial-AST).

### Modes

- Default: scan staged files, exit 1 on first match outside baseline.
- `--baseline` — capture current matches into
  `manifests/ast-similarity-baseline.yaml`.
- `--quick` — only staged files (pre-commit speed target: < 1 s on typical
  commit).
- `--format json|text|markdown`.
- `--allowlist <path>` — exclude path-prefixes (e.g. attribution-quoted code in
  docs/research/).
- `--ci` — exit 1 on any non-baseline match.

### Bypass

- `COS_ALLOW_AST_SIMILARITY=1` — generic logged bypass.
- `COS_ALLOW_CLEAN_ROOM_BYPASS=1` — shared bypass with verbatim-leak hook (for
  audit-trail coherence when both fire on the same commit).

### Baseline file

`manifests/ast-similarity-baseline.yaml` — same shape as
`manifests/verbatim-detection-baseline.yaml`. Captures known-accepted matches
(e.g. structural similarity that legal review classified as idea-expression
merger).

## Consequences

### Positive

- Closes the most common defendibility gap: symbol-renamed copies. An engineer
  doing `cat external/X.py > lib/X.py` and then `s/foo/bar/g` would currently
  pass T1; T2 catches it.
- Reuses ADR-029b Jaccard infra where overlap exists (token extraction, baseline
  schema).
- Defendibility paper trail: every T2 hit becomes either an accepted-baseline
  entry (reviewed) or a rejected commit (audited).

### Negative

- **False positives on common Python idioms**: singletons, dataclass scaffolds,
  argparse boilerplate will collide structurally. Baseline file is the
  mitigation; first soak run will produce a long baseline.
- **Performance ceiling**: pre-computing normalized-AST hashes for the full
  external-source-cache is O(N files * file size). Estimate: 4k files * 5 ms
  parse = 20 s cold; cached to JSON index keeps warm runs < 1 s.
- **Single-language**: Python only in v1. TypeScript / Rust / Go ports are NOT
  detected. Cross-language similarity remains T5.
- **AST instability**: small Python version differences (3.11 vs 3.12) can
  change `ast.dump` output. Need to pin canonicalisation logic, not rely on
  upstream `ast.dump` directly.

### Neutral

- Hook fires at pre-commit, opt-in via efficiency profile (NOT default until
  baseline soak shows acceptable false-positive rate).
- Does NOT replace T1 (verbatim-leak hook). The two are complementary —
  catches different shapes.

## Implementation phases

### Phase 1 — Python AST normalisation + similarity engine (~1 PW)

- `scripts/cos_clean_room_ast_similarity.py` — single-file Python tool.
- Pre-compute external-source-cache AST hashes to
  `.cognitive-os/runtime/ast-similarity-index.json` (cached).
- `--baseline` seed run.
- Reports: text / json / markdown.

### Phase 2 — Pre-commit hook + tests (~0.5 PW)

- `hooks/clean-room-ast-similarity-gate.sh` wrapper.
- `tests/integration/test_clean_room_ast_similarity.sh` — 10 cases:
  symbol-rename detection, baseline accept, allowlist exclude, performance
  budget, etc.
- Manual-trigger pending operator soak.

### Phase 3 — Soak + tune (~1 week wall-clock)

- Run on every commit in warn-only mode for one week.
- Capture false-positive rate.
- Decide promotion to active gate.

## Verification

- Symbol-rename test case: copy `lib/file_mutation_queue.py`, rename every
  identifier, stage → hook fires.
- Identity test case: stage `lib/review_agent.py` (already a symlink to packages
  authoritative) → hook does NOT fire (canonical path skipped).
- Baseline accept: add a known false-positive to baseline.yaml → re-run on
  same commit → hook passes.
- Allowlist exclude: add `docs/research/` to allowlist → annex F quotes ignored.

## Open questions

1. **TypeScript / Rust support**: defer to Phase 4 or never? Cross-language
   ports are real (`lib/file_mutation_queue.py` was TS-origin). T5 covers it
   today but accepting the gap forever leaves a real attack surface.
2. **AST hash granularity**: per-function or per-file? Per-function gives more
   precision (catches single-function copies) but explodes index size. Suggest
   per-function for indexed content > 50 LOC, per-file under.
3. **Baseline review cadence**: should the baseline file have an
   `expires-after` field forcing periodic re-validation of accepted matches?
   Legal landscape evolves.
4. **Cross-tool with verbatim-leak hook**: if the same commit trips T1 and T2,
   should the error message consolidate (one block, two findings) or fire
   separately (two blocks)? Lean consolidate — operator gets one bypass
   decision.

## Related

- ADR-029 — anti-reinvention gate Phase A (basename match).
- ADR-029b — anti-reinvention gate Phase B (semantic similarity, MVP +
  embeddings deferred). T2 reuses the Jaccard tokenisation infrastructure.
- ADR-267 — license-compliance enforcement architecture. T2 is Hook #8 in
  that ledger.
- `rules/clean-room-detection-limits.md` — the full tier matrix this ADR fills
  the T2 row of.
- `hooks/external-cache-content-leak.sh` — T1 implementation; T2 is the
  complement.
- `manifests/verbatim-detection-baseline.yaml` — schema precedent for the new
  `manifests/ast-similarity-baseline.yaml`.

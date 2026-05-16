---
adr: 29b
title: 'Reinvention gate Phase B: semantic similarity'
status: accepted
implementation_status: partial
date: '2026-04-20'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
partial_remaining: 'What was explicitly deferred**:'
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-029b — Reinvention gate Phase B: semantic similarity

**Status**: Accepted (Phase B-alpha MVP); Phase B-beta (embeddings) deferred
**Date**: 2026-04-20
**Deciders**: Maintainer
**Supersedes**: ADR-029 §"Phase B (future)" placeholder
**Debt ticket**: D07 (rules/ROADMAP.md §1.7)

---

## 1. Problem statement

Phase A (`hooks/reinvention-check.sh`, ADR-029) catches reinvention only when the
agent proposes a *filename* that contains the basename of an existing module. It
is a glorified `find -name "*${base}*"`. In practice this misses the common case:
an agent renaming the concept.

Concrete codebase examples that Phase A DOES catch:

- Prompt contains `lib/rate_limiter.py` → matches existing `lib/rate_limiter.py`. ✓
- Prompt contains `hooks/auto-verify.sh` → matches existing `hooks/auto-verify.sh`. ✓

Concrete examples that Phase A MISSES (all real near-misses from this project's
history):

- Prompt: "create `lib/request_throttle.py` to cap agent tool calls per minute."
  Existing: `lib/rate_limiter.py` — same responsibility, 12-char Levenshtein
  distance. Phase A: no match on `request_throttle` vs `rate_limiter`.
- Prompt: "create `lib/agent_heartbeat.py` for agent liveness pings via pub/sub."
  Existing: `lib/agent_bus.py` with `AgentBus.publish_heartbeat()`.
  Phase A: no match. This is the incident that motivated ADR-029 itself; the gate
  it shipped would not have caught the duplication that inspired it.
- Prompt: "add `lib/token_budget_monitor.py`." Existing: `lib/rate_limit_protection.py`
  (same module, renamed at some point). Phase A matches on `rate_limit`, misses
  `token_budget`.
- Prompt: "write `hooks/context-usage-check.sh`." Existing:
  `hooks/context-watchdog.sh`. Phase A: no match.

The failure mode is uniform: **agents describe behaviour in English and pick a new
name**; Phase A compares names. Phase B must compare **what the module does**, not
what it is called.

## 2. Candidate approaches

Four approaches evaluated. Scored 1 (bad) to 5 (good) on each axis.

| # | Approach | Recall | Precision | Latency | Deps | Cost | Offline | Verdict |
|---|----------|--------|-----------|---------|------|------|---------|---------|
| a | Jaccard on docstrings + function-name tokens | 3 | 4 | 5 | 5 (stdlib only) | 5 ($0) | 5 | **MVP** |
| b | TF-IDF + cosine on file contents | 3 | 4 | 4 | 3 (scikit-learn or hand-rolled) | 5 ($0) | 5 | Skip — marginal gain over (a) |
| c | Local embeddings (sentence-transformers, `all-MiniLM-L6-v2`) | 5 | 4 | 2 (first call ~2s, warm ~80ms) | 2 (adds ~90MB deps + PyTorch) | 5 ($0 after download) | 5 | **Phase B-beta target** |
| d | LLM-as-judge (Haiku one-shot) | 5 | 5 | 1 (~1-3s/call) | 4 (already installed) | 2 (~$0.0003/call, hundreds of calls/day = $$) | 1 | Reject — latency + cost |

### Notes on each

**(a) Jaccard on token bags.** For every scanned file emit the set of tokens from
(i) the module/file docstring, (ii) top-level function/class names split on `_`
and CamelCase, (iii) the first sentence of each function docstring. Compute
Jaccard similarity between the *query* token bag (extracted from the agent
prompt) and each candidate bag. Dependency: Python stdlib only. Worst-case
corpus size in this repo is ~550 files × ~40 tokens = 22k tokens; fits in
< 1 MB JSON index.

**(b) TF-IDF.** Same extraction, but weight tokens by inverse document frequency.
Marginal precision gain over Jaccard when common words (`config`, `helper`,
`util`) dominate the corpus. Hand-rolled TF-IDF is ~40 LOC of Python. Rejected
because the incremental precision does not justify the extra code path when (c)
is the eventual goal and (a) is sufficient as a tripwire.

**(c) Sentence-transformer embeddings.** `all-MiniLM-L6-v2` produces 384-dim
vectors, ~80 ms per query warm, ~2 s cold (model load). Best recall: catches
paraphrases like "throttle" ~ "rate limit" ~ "quota" because they cluster in
embedding space. Cost: ~90 MB model + PyTorch CPU wheel (~200 MB). Blocker for
MVP: deps are heavyweight and `ORCHESTRATOR_MODE=executor` environments may not
have them. Target state: Phase B-beta introduces it behind
`REINVENTION_PHASE_B_EMBEDDINGS=1` with graceful fallback to (a) when the import
fails.

**(d) LLM advisory.** Highest quality, but p95 latency 1–3 s is incompatible with
the 300 ms hook budget. Also introduces non-trivial per-invocation cost. A hook
that fires on every agent launch cannot afford either. Rejected outright.

## 3. Recommendation

Ship **(a) Jaccard** as Phase B-alpha immediately. It is small, stdlib-only,
< 300 ms worst case, and exercises the whole architecture — index build, query,
scoring, threshold, hook integration, metrics — that (c) will later reuse. Then
pilot (c) embeddings as Phase B-beta in a follow-up ADR once (a) is proven to have
low false-positive rate in production.

Reason for the split: the index + hook integration is 80% of the work. Swapping
the scoring function from Jaccard to cosine-over-embeddings is the remaining
20% and should be a drop-in strategy pattern, not a rewrite.

## 4. Latency budget

**Hard constraint**: `hooks/reinvention-check.sh` end-to-end p95 < 300 ms, per
SLO 2 (`rules/so-slo.md`, `PreToolUse` p95 < 200 ms) with a 50% headroom buffer
for bash startup.

Budget allocation:

| Phase | Budget | Notes |
|-------|--------|-------|
| bash + common.sh load | 40 ms | Already paid by Phase A |
| stdin JSON parse | 10 ms | `jq` call |
| Phase A grep + find | 60 ms | Measured today on this repo |
| Phase B-alpha Jaccard query | 50 ms | Python subprocess, pre-loaded JSON index |
| Metrics append | 10 ms | safe-jsonl |
| **Total** | **170 ms** | ≥ 40% headroom vs 300 ms cap |

Index build is **not** on the hook path. It runs on `SessionStart` and is
cached. Cold build is budgeted separately at ≤ 2 s (SLO 1: `SessionStart` p95
< 2 s; the index build is one of several things sharing that budget).

## 5. False-positive policy

**Phase B-alpha: advisory only, never block.** Rationale:

1. Jaccard has known false positives on boilerplate-heavy files (docstrings
   dominated by generic words like `config`, `agent`, `manager`).
2. The cost of a false negative (reinvention committed) is bounded — human
   review + `/simplify` catches it.
3. The cost of a false positive that hard-blocks is an angry developer
   overriding the gate once, then ignoring it forever (the classic tripwire
   failure mode).
4. Phase A is already advisory and has proven out this policy.

Metrics emit `score`, `candidates`, `threshold`, and `action=ADVISED` so a
later analysis can decide if and when to move to `action=BLOCKED` at a proven
threshold. Moving to hard-block is a separate ADR (B-γ), gated on ≥ 30 days of
`action=ADVISED` data showing precision ≥ 0.9 at the chosen threshold.

## 6. Precomputation strategy

Index lives at `.cognitive-os/reinvention-index.json` (not `.pkl` — plain JSON
survives Python version upgrades and is inspectable with `jq`).

### Build triggers
- `SessionStart` hook (future wiring — not this sprint).
- Manual rebuild: `python3 -c "from lib.reinvention_semantic import SemanticIndex; SemanticIndex().build_index('.')"`.
- Hook path: **lazy build on first miss** — if file is absent, the hook falls
  back to Phase A only and logs `reason=index_missing`. No synchronous
  index-build on the hot path.

### Schema

```json
{
  "version": 1,
  "built_at": "2026-04-20T12:34:56Z",
  "project_root": "/abs/path",
  "items": [
    {
      "path": "lib/rate_limiter.py",
      "kind": "python",
      "tokens": ["rate", "limiter", "prevent", "token", "flood", "tool",
                 "usage", "call", "minute", "launch", "hour", "bash",
                 "command", "file", "write"],
      "docstring_excerpt": "Rate Limiter — Prevents token flooding..."
    }
  ]
}
```

### Scan scope
`lib/**/*.py`, `hooks/**/*.sh`, `scripts/**/*.{sh,py}`. Not `tests/` (test files
should not be matched — a new test for `rate_limiter.py` is not reinvention).

### Cache invalidation
Rebuild when any scanned file's `mtime` > `built_at`. Initial heuristic: rebuild
on every `SessionStart`. Sub-second builds make fancier invalidation unnecessary
until corpus > 2000 files.

## 7. Integration points

`hooks/reinvention-check.sh` changes (minimal, behind env gate):

1. After the existing Phase A block (lines 45–65), if `REINVENTION_PHASE_B=1`,
   invoke:
   ```bash
   python3 -c "from lib.reinvention_semantic import SemanticIndex, query; query('$PROMPT')"
   ```
   (in practice: a one-liner helper script `scripts/reinvention-query.sh` to
   avoid shell quoting hazards in prompts).
2. The helper prints 0..3 matches (path + score) to stderr when score ≥ `threshold`
   (default 0.3, env-override `REINVENTION_PHASE_B_THRESHOLD`).
3. Append a single JSONL record with `phase=B-alpha`, `score`, `candidates`,
   `target` to `.cognitive-os/metrics/reinvention-checks.jsonl`.
4. Hook exit code unchanged (always 0) — advisory only.

Fallback: if `lib/reinvention_semantic` import fails, or the index JSON is
absent, log `phase=B-alpha reason=fallback_to_A` and continue with Phase A only.

## 8. Rollout plan

| Step | Duration | Gate | Owner action |
|------|----------|------|--------------|
| 1. Ship Phase B-alpha behind `REINVENTION_PHASE_B=1` env gate | this commit | ADR accepted | Commit implementation + tests |
| 2. Dogfood for 7 days in the hermes-agent worktree | 1 week | ≥ 5 hook fires with real prompts | Review metrics JSONL |
| 3. Measure precision on logged cases | 1 day | ≥ 0.8 precision at threshold 0.3 | Hand-label each match as TP/FP |
| 4. Default-on if precision passes | 0.25 d | Step 3 passes | Flip default to `REINVENTION_PHASE_B=1` in `scripts/apply-efficiency-profile.sh default` |
| 5. Phase B-beta design ADR (embeddings) | 1 week | Step 4 stable for 2 weeks | Draft ADR-029c |
| 6. Phase B-γ hard-block ADR | later | ≥ 30 days, precision ≥ 0.9 | Separate decision |

If Step 3 fails (precision < 0.8), tune threshold upward or extend token
extraction (e.g. include imports, drop stopwords more aggressively) before
escalating to embeddings.

## 9. Open questions

- **Stopword list**: current implementation uses a minimal list (12 generic CS
  words). If precision is weak, grow it from corpus statistics rather than
  hand-tuning.
- **Multi-language tokenisation**: Go, TypeScript, shell all parsed with the
  same `re.split(r"[^a-z0-9]+")` regex after lowercasing. This is crude but
  language-neutral. Revisit in B-beta when AST parsing becomes cheap.
- **Negative examples**: should the index track *deleted* files so that
  reviving a deleted pattern also trips the gate? Out of scope for B-alpha;
  mention in B-beta.

## 10. Acceptance criteria (this ADR)

```
test -f docs/02-Decisions/adrs/ADR-029b-reinvention-phase-b-semantic.md
grep -c '^## ' docs/02-Decisions/adrs/ADR-029b-reinvention-phase-b-semantic.md  # ≥ 10 (all sections present)
test -f lib/reinvention_semantic.py
python3 -c "from lib.reinvention_semantic import SemanticIndex; s=SemanticIndex(); s.build_index('.'); assert len(s.items) > 10"
pytest tests/unit/test_reinvention_semantic.py -v  # 5/5 pass
REINVENTION_PHASE_B=0 bash hooks/reinvention-check.sh < /dev/null  # Phase A only
```

---

## Resolution Log

### 2026-04-21 — Phase B-beta wired as optional

**Status change**: Phase B-beta (embeddings) moved from "deferred" to "optional,
wired, not installed by default". Hard-block escalation (Phase B-γ) still
deferred per §5.

**What landed**:

1. `pyproject.toml` gains an OPTIONAL `[project.optional-dependencies] semantic`
   extra: `sentence-transformers>=3.0`, `numpy>=1.26`. Deliberately NOT included
   in the `dev` extra — PyTorch (~200 MB) would bloat every CI run.
   Install explicitly with `uv pip install -r requirements/dependency-lanes/semantic.txt` (ADR-145 supersedes the former `.[semantic]` extra).

2. `hooks/reinvention-check.sh` now recognises `REINVENTION_PHASE_B=2` as the
   embeddings path. The inline Python tries `EmbeddingsIndex` first, catches
   `ImportError` (sentence-transformers absent) or any query-time exception
   (model load failure, missing `.npy` artefacts), and falls back silently to
   Phase B-alpha Jaccard. The metrics JSONL `phase` field reports the path actually
   taken (`B-alpha` or `B-beta`). Hook exit code remains `0` on every path
   (advisory only, §5).

3. `EmbeddingsIndex` already existed in `lib/reinvention_semantic.py` (shipped
   alongside Phase B-alpha). The stated "create `lib/reinvention_embeddings.py`"
   step from the work order was deliberately NOT executed — creating a second
   module for the same class would itself be a reinvention incident. Instead,
   a latent `_persist()` bug (numpy auto-appends `.npy` to the tempfile, which
   broke `tmp.replace()`) was fixed in-place.

4. `tests/unit/test_reinvention_embeddings.py` — 7 cases, all mocking
   `sentence_transformers` via `monkeypatch.setitem(sys.modules, …)`. No model
   download in CI. Covers: ImportError when module absent, build+persist,
   load round-trip, scored top-k query, threshold filtering, empty-index query,
   hook-style graceful fallback.

**What was explicitly deferred**:

- Real-corpus precision/recall benchmark (ADR-039 acceptance: precision > 0.7
  @ recall 0.6). Next step: curate a labelled test set from
  `.cognitive-os/metrics/reinvention-checks.jsonl` over the next 7-14 days with
  `REINVENTION_PHASE_B=2` enabled on one developer machine, then run a
  precision/recall script that compares Jaccard vs embeddings on the same
  queries.
- Index build on `SessionStart`. Currently build is manual
  (`python3 -m lib.reinvention_semantic build --embeddings`). Auto-build on
  session start is separate work per ADR-029b §6 "Build triggers".
- Threshold re-calibration in production. Default `DEFAULT_EMBED_MIN_SCORE=0.45`
  is a theoretical value; tune based on the benchmark above.
- `semantic` extra installation in CI. Deferred to a follow-up once the
  precision benchmark justifies the disk/time cost.

**Evidence** (verification commands run 2026-04-21):

```
pytest tests/unit/test_reinvention_embeddings.py -v   # 7/7 pass
pytest tests/unit/test_reinvention_semantic.py -v     # 5/5 pass (no regression)
pytest tests/unit/test_reinvention_guard.py -v        # 11/11 pass (no regression)
REINVENTION_PHASE_B=2 bash hooks/reinvention-check.sh < … # exit 0 without embeddings
```

**Residual risk**: Phase B-beta has never run against a real sentence-transformers
install in CI. The test suite mocks the module; a first-run surprise on the
real model (e.g. tokenizer download, huggingface_hub version drift) is possible.
Dogfooding on one developer machine first (per §8 rollout plan Step 2, extended
to B-beta) is the intended mitigation.

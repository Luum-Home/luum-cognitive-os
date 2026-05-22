# Graphify Next-Step Decision Investigation — 2026-05-22

## Question

After the initial controlled Graphify trial, choose the next adoption step among:

1. Add a Cognitive OS maintainer skill for Graphify queries.
2. Add persistent Codex/AGENTS.md instructions that always nudge agents to Graphify.
3. Run semantic extraction over curated documentation.

## Recommendation

Proceed in this order:

1. **Implement a maintainer-only `graphify-query` skill.**
2. **Defer persistent Codex/AGENTS.md instructions.**
3. **Defer semantic documentation extraction until an explicit backend and token budget are approved.**

Do not run upstream `graphify codex install` in this repository. If persistent instructions are later desired, write a Cognitive-OS-owned instruction block instead of letting Graphify mutate `AGENTS.md` and `.codex/hooks.json` directly.

## Evidence Reviewed

### Upstream Currentness

- GitHub repository: `safishamsi/graphify`, public, branch `v8`, 511 commits visible in the GitHub page opened on 2026-05-22.
- PyPI package: `graphifyy 0.8.15`, released `2026-05-22`, Python `>=3.10`, MIT license.
- Upstream README says the CLI command is `graphify`, package name is `graphifyy`, and Codex users can install persistent guidance with `graphify codex install`.

### Local Source Review

The local clone at `/tmp/graphify-investigation` shows two separate install behaviors:

- `graphify install --platform codex` copies the Codex skill file to the user's home config path, not this repository.
- `graphify codex install` writes a `## graphify` section into local `AGENTS.md` and registers a `.codex/hooks.json` PreToolUse hook.

The Codex hook currently calls `graphify hook-check`, and upstream source documents that Codex Desktop rejects `hookSpecificOutput.additionalContext`; `hook-check` exits as a no-op. Therefore, for Codex, the durable behavior is effectively the local `AGENTS.md` section, not a working automatic pre-tool context injector.

### Local Wrapper Reality

Cognitive OS now has `scripts/cos-graphify-build`, which supports external output roots and code-only default builds. This matters because upstream's persistent AGENTS guidance says agents should run `graphify update .` after code changes. Upstream `graphify update` writes to `<watch_path>/graphify-out/`, while the Cognitive OS wrapper can write outside the repo, such as `/tmp/cos-graphify-phase-receipt/graphify-out/`.

That means upstream persistent guidance is not aligned with the wrapper unless this repo standardizes on local `graphify-out/` in the repository root.

### Query Primitive Behavior

The bounded `lib/` graph produced useful results for symbol-oriented commands:

```text
graphify path "CanonicalEvent" "ClaudeCodeAdapter"
-> Shortest path (1 hops): CanonicalEvent <--uses [INFERRED]-- ClaudeCodeAdapter
```

```text
graphify affected "CanonicalEvent" --depth 2
-> returned harness adapters, sprint orchestrator classes, imports, inherited event classes, and related users.
```

```text
graphify explain "CanonicalEvent"
-> returned source file, line, type, community, degree, and 43 connections.
```

The broad natural-language query smoke was less reliable:

```text
graphify query "Which modules handle memory and routing?"
-> started from docstring-like nodes and returned only three nodes.
```

Conclusion: a Cognitive OS skill should teach agents to use `path`, `explain`, and `affected` when names are known, and treat `query` as a scoped-orientation helper rather than a truth source.

### Documentation Corpus Cost Estimate

A local word-count estimate for likely semantic documentation scopes:

```text
docs/04-Concepts/architecture: 189 files, 185,470 words, ~247,293 tokens
docs/02-Decisions/adrs:        344 files, 415,078 words, ~553,437 tokens
rules:                         127 files,  70,987 words,  ~94,649 tokens
skills:                        113 files,  88,020 words, ~117,360 tokens
combined curated docs:         773 files, 759,555 words, ~1,012,740 tokens
```

Graphify docs state that code files are processed locally via tree-sitter, while docs, PDFs, and images are sent to the AI assistant or configured model backend for semantic extraction. Therefore, semantic docs extraction is not a casual next step; it is a budgeted operation.

## Option Analysis

### Option A — Maintainer-Only `graphify-query` Skill

**Verdict:** adopt next.

Benefits:

- Keeps Graphify behind an explicit operator action.
- Encodes Cognitive OS-specific boundaries: wrapper first, no hook install, no upstream Codex installer, graph output is navigation not proof.
- Can prefer `scripts/cos-graphify-build` over raw `graphify extract`.
- Can tell agents how to choose between `query`, `path`, `explain`, `affected`, and `benchmark`.
- Fits existing `skills/*/SKILL.md` patterns with `SCOPE: os-only`.

Risks:

- Adds another skill to the already large skill surface.
- Needs routing metadata to avoid triggering for every generic codebase question.

Mitigation:

- Make it `os-only`, maintainer-facing, and triggered only by explicit phrases such as `graphify`, `knowledge graph`, `graph query`, or `repo graph`.
- Keep it read-first/query-first; building graphs remains explicit.

### Option B — Persistent Codex/AGENTS.md Instruction

**Verdict:** defer.

Benefits:

- Makes graph use more automatic when `graphify-out/graph.json` exists.
- Reduces repeated broad greps once a graph is known fresh.

Risks:

- Upstream `graphify codex install` mutates `AGENTS.md` and `.codex/hooks.json`.
- The Codex hook path is effectively no-op in current upstream source, so the install gives a misleading sense of automatic enforcement.
- Upstream guidance says `graphify update .`, which conflicts with wrapper-supported external graph output roots.
- Always-on instructions can cause stale graph use if freshness is not checked.
- Cognitive OS already has dense always-active AGENTS governance; adding another broad instruction increases instruction tax.

Mitigation if revisited:

- Do not use upstream installer.
- Add a short Cognitive-OS-owned section only after the skill proves useful.
- Require graph freshness checks before using the graph for anything beyond orientation.
- Phrase it as a preference, not a mandate: Graphify narrows context, tests verify claims.

### Option C — Semantic Docs Extraction

**Verdict:** defer pending explicit budget/backend approval.

Benefits:

- Could connect ADRs, rules, skills, and architecture docs to code symbols.
- Could make architecture drift and surprising cross-document links easier to discover.
- Potentially high value for this documentation-heavy repository.

Risks:

- The curated docs/rules/skills set is roughly one million estimated input tokens before chunking overhead and retries.
- Docs extraction may send sensitive design context to a configured backend unless local inference is used.
- Local Ollama must actually be running and model quality may be insufficient for high-fidelity semantic extraction.
- Generated semantic edges are not proof; they require review before claims or decisions.

Mitigation if revisited:

- Start with a very small slice, such as one architecture subfolder plus 5 to 10 ADRs.
- Use a dedicated receipt with input file list, backend, model, token counts, and cost.
- Store outputs outside the repo first.
- Promote only if the graph answers questions that current repo-map and grep workflows cannot answer cheaply.

## Decision Matrix

| Option | Value | Risk | Cost | Reversibility | Recommendation |
|---|---:|---:|---:|---:|---|
| Maintainer `graphify-query` skill | High | Low | Low | High | Do next |
| Persistent Codex instruction | Medium | Medium | Low | Medium | Defer |
| Semantic docs extraction | Potentially high | Medium-high | Medium-high | High if output external | Defer |

## Proposed Skill Contract

Name: `graphify-query`

Scope: `os-only`

Audience: Cognitive OS maintainers

Triggers:

- `graphify`
- `graph query`
- `knowledge graph`
- `repo graph`
- `graphify affected`
- `graphify explain`

Required behavior:

1. If no graph exists, suggest or run `scripts/cos-graphify-build <path>` only when explicitly asked to build.
2. If a graph exists, check freshness where possible by comparing graph `built_at_commit` with `git rev-parse HEAD`.
3. Use:
   - `graphify explain <symbol>` for a known symbol or file concept.
   - `graphify path <A> <B>` for relationships between two known concepts.
   - `graphify affected <symbol>` for impact-style questions.
   - `graphify query <question>` for broad orientation only.
   - `graphify benchmark` for token-reduction evidence.
4. Never claim Graphify output proves correctness.
5. Never install Graphify hooks or run `graphify codex install`.
6. Prefer the repo wrapper for builds: `scripts/cos-graphify-build`.

## Acceptance Criteria for Next Implementation Slice

1. `skills/graphify-query/SKILL.md` exists with `SCOPE: os-only`.
2. The skill references `scripts/cos-graphify-build` rather than raw full-repo `graphify extract .`.
3. The skill explicitly forbids hook install and upstream Codex install.
4. The skill includes command selection guidance for `query`, `path`, `explain`, `affected`, and `benchmark`.
5. A manual smoke uses the existing `/tmp/cos-graphify-phase-receipt/graphify-out/graph.json` or a fresh wrapper graph to prove the command flow.
6. `python3 -m py_compile scripts/cos-graphify-build` remains green.
7. `python3 scripts/derived_artifact_gate.py` remains green.

## Final Decision

Implement the maintainer-only `graphify-query` skill next. Do not add persistent Codex instructions yet. Do not run semantic docs extraction yet.

This choice preserves the value observed in the controlled trial while keeping Graphify out of the core runtime and avoiding always-on instruction drift.

## Sources

- GitHub: `https://github.com/safishamsi/graphify`
- PyPI: `https://pypi.org/project/graphifyy/`
- Local clone: `/tmp/graphify-investigation`
- Local Graphify graph receipt: `docs/06-Daily/reports/graphify-controlled-trial-receipt-2026-05-22.md`

## Implementation Update — 2026-05-22

The decision is now captured in `docs/02-Decisions/adrs/ADR-331-graphify-portable-context-optimization-primitive.md` and implemented as the maintainer skill `skills/graphify-query/SKILL.md`. The portable phase plan lives at `docs/04-Concepts/architecture/graphify-portable-optimization-plan-2026-05-22.md`.

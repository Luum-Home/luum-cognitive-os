# Contributing to Cognitive OS

## TL;DR

This project is heavily AI-assisted. Most code is drafted by AI agents
(Claude, Codex, Qwen) running under the Cognitive OS orchestration
framework that this repo itself implements, and every commit passes
through hook-based quality gates plus explicit human approval before it
lands. This document explains how that works, how to contribute, and a
few conventions that might otherwise look strange — most notably, why
we do not add `Co-Authored-By: Claude` trailers.

The tone aims to be matter-of-fact, and claims here are intended to be
verifiable from the repo.

## 1. Who writes the code

Honest disclosure:

- The **majority** of commits are produced by AI coding agents —
  primarily Anthropic's Claude (Opus, Sonnet, Haiku tiers), OpenAI's
  Codex, and Alibaba's Qwen — operating under the Cognitive OS
  orchestration framework. Yes, the same framework whose source lives in
  this repo. The project dogfoods itself.
- Every commit passes through human-in-the-loop review gates before it
  is pushed to `main`:
  - **Pre-commit and pre-push hooks** enforce portability, scope
    markers, a destructive-git blocker, license/secret scanning, and
    repository-specific contracts. See `hooks/` and `.githooks/`.
  - **Agent self-verification** — agents must provide a Trust Report
    (evidence-based confidence assessment) with their output. See
    `rules/trust-score.md`.
  - **Human operator review** — a human reviews the diff and approves
    the push. The operator is the legal author of the commit.
- Reviewer identity model: at the time of writing, a single human
  operator (the repository maintainer) reviews and approves all merges
  to `main`. The model will expand as the project takes on additional
  maintainers, and this section will be updated when that happens.

## 2. Why we do not use `Co-Authored-By` for AI agents

A deliberate choice, not an oversight. The rationale, so the absence is
not read as concealment:

1. **Authorship in the legal sense.** Anthropic, OpenAI, and Alibaba do
   not author code that this project ships. They provide statistical
   models the human operator runs as a tool. Listing them as co-authors
   would imply a legal authorship relationship that does not exist and
   that the providers themselves do not claim.
2. **History noise.** Adding AI-provider `Co-Authored-By` trailers
   to virtually every commit produces a `git log` that is mostly tooling
   metadata and breaks contributor-graph tooling on most forges.
3. **Conflict with the verified-author model.** The repository records
   AI provenance through a structured side-channel rather than commit
   trailers (see ADR-088). Mixing the two channels would create two
   sources of truth that could disagree.

The project does **not** hide AI involvement; it records it explicitly,
just outside the public commit-author channel:

- **Session trajectories.** When a Cognitive OS session is active,
  `.cognitive-os/sessions/` records the agent trajectory for the work
  that produced the change.
- **Commit provenance hook.** Local development can add `X-COS-*`
  provenance trailers via `.githooks/prepare-commit-msg` and
  `scripts/commit_provenance.py`; pre-public history sanitization strips
  those trailers from published commits so session IDs do not leak.
- **Audit script.** Run `python3 scripts/commit_provenance.py --help`
  to see the attribution algorithm. The script's docstring documents the
  priority order it walks (PPID chain, environment variables, fallback
  heuristics) and links to ADR-088 for known limitations.

The private trajectory data is the intended starting point for AI-vs-human
auditing. A dedicated whole-history public reporting CLI is aspirational;
published commit authorship remains the verified human-operator channel.

## 3. How to contribute

Outside contributions are welcome.

1. **Issue first** for non-trivial work — open one describing the
   problem and the proposed approach (Bug Report or Feature Request
   template). This avoids wasted effort if the change conflicts with
   in-flight work or undocumented design decisions.
2. **Fork and branch** from `main`. Branch naming is informal but
   descriptive — `fix/hook-timing-race`, `feat/llm-dispatch-qwen-fallback`.
3. **Pull request** against `main`. Reference the issue and any relevant
   ADRs. Smaller PRs get reviewed faster.
4. **DCO sign-off required** on every commit (see section 7).
5. **Pre-commit hooks will run.** Do not bypass with `--no-verify`
   without operator approval. They catch real issues.
6. **Tests.** Behaviour changes require tests. At minimum, run the tests
   covering the paths you touched. Lanes documented in
   `.cognitive-os/test-lanes.yaml`.

### Development setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/luum-cognitive-os.git
cd luum-cognitive-os

# (Optional) Start infrastructure for full integration testing
docker compose -f docker-compose.cognitive-os.yml up -d

# Run the full suite
bash scripts/run-all-tests.sh
```

Review timing is best-effort. The maintainer is currently one person and
this is not a funded project. Reasonable PRs typically get a first
response within a few days; nothing more is promised here.

## 4. Code style

Enforced by lint, `tests/audit/`, and hooks. Full ruleset in `rules/`:

- **Python**: `snake_case` filenames in `scripts/`, `lib/`, and
  `packages/*/lib/`. See `rules/python-naming.md`. Hyphens in Python
  filenames break pytest collection and are blocked by
  `tests/audit/test_python_naming.py`.
- **Bash**: `kebab-case` filenames, `snake_case` functions inside.
  See `rules/bash-naming.md`. Enforced by `tests/audit/test_bash_naming.py`.
  Use `#!/usr/bin/env bash`, `set -euo pipefail`, quote variables.
- **Go**: `gofmt -l` clean, `go vet ./...` clean. Local CI gate; see
  ADR-131.
- **YAML**: 2-space indentation; comments explain *why*, not *what*.
- **Markdown**: Skills follow the `SKILL.md` format with frontmatter;
  rules follow the `rules/*.md` format. Lines under 120 characters.
- **No `TODO` or `FIXME` without a tracking reference** (issue ID, ADR
  number, or ticket). See `rules/agent-quality.md`. Naked TODOs become
  forgotten TODOs.
- **Tests required for behaviour changes.** Pure refactors and docs
  changes are exempt.

### Architecture boundary

Cognitive OS has a strict separation between **core** and
**project-specific** code:

| Directory | Scope | Rule |
|-----------|-------|------|
| `.cognitive-os/` | Universal framework | Must work for ANY project. No project-specific references. |
| `.claude/` | Project-specific | Tied to a specific project. Generated by `/cognitive-os-init`. |
| Root `rules/`, `skills/`, `hooks/` | Core source content | Product runtime content projected into installed environments. |

Before submitting: is the change in the right tier? Will it work for
Go, Node, Python, Rust, and any other stack? Are you adding a
dependency that breaks portability?

## 5. Commit message conventions

Conventional Commits, loosely:

- **Prefix**: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`,
  `tooling:`, plus a few project-specific prefixes you will see in
  `git log` (`adr:`, `audit:`).
- **Imperative mood**: `add X`, not `added X` or `adds X`.
- **Subject line under 72 characters.** The body explains *why* the change
  was made, not *what* was changed (the diff already shows the what).
- **Reference ADRs and issues** in the body where applicable
  (`See ADR-088`, `Closes #42`).
- **Do not add `Co-Authored-By:` for AI agents** (see section 2). The
  X-COS provenance trailers are added automatically by the prepare-commit
  hook.
- **Do add `Signed-off-by:` for DCO** (section 7). `git commit -s`
  appends it for you.

## 6. Testing

Contributions should include tests when applicable:

- **Unit and contract tests**: `python3 -m pytest tests/unit tests/contracts -q`
- **Behaviour tests**: `python3 -m pytest tests/behavior -q`
- **Go core tests**: `go test ./internal/provider/... ./internal/validator/... ./pkg/hook/...`
- **Full suite**: `bash scripts/run-all-tests.sh`

Run the full suite before submitting if your change touches anything
beyond docs.

## 7. The DCO (Developer Certificate of Origin)

This project uses the
[Developer Certificate of Origin](https://developercertificate.org/)
rather than a CLA. By adding `Signed-off-by:` to your commit, you certify
that you have the right to submit the contribution under the project's
license. Add it with `git commit -s` (or `-sa` to also stage tracked
changes and sign in one step).

The DCO text is short and worth reading at the link above. Short
version: you wrote it (or have permission to contribute it), you
understand it is going into a public open-source project, and you are
fine with that.

## 8. AI tools used

Listed for transparency, not endorsement:

- **Claude** (Opus / Sonnet / Haiku) by Anthropic — primary orchestration
  and implementation.
- **Codex** by OpenAI — secondary implementation and code review.
- **Qwen** by Alibaba — used as the primary tier in the LLM dispatcher to
  preserve Claude budget; see ADR-049 and `scripts/orchestrator.py`.

The Cognitive OS orchestration layer is **provider-agnostic by design**.
Switching, replacing, or adding providers is supported through
configuration (`cognitive-os.yaml` and `lib/dispatch.py`). The list above
reflects what the maintainer happens to use; nothing in the architecture
favours any specific provider, and this project does not endorse any
vendor's reliability or capability claims.

## 9. Reporting AI-generated bugs

This is a bug category the project specifically welcomes reports on,
because the failure modes are characteristic and worth tracking:

- **Hallucinated APIs** — code that calls a function or imports a module
  that does not exist (or no longer exists in the current version).
- **Stale references after refactor** — code, docs, or tests still
  pointing at the old name, path, or signature.
- **Confidently-wrong code** — looks reasonable on a skim, falls apart
  on inspection (off-by-one, wrong default, plausible-but-incorrect
  algorithm).
- **Plausible-but-fabricated citations** — references to ADRs, issues,
  or commits that do not exist.

When filing one of these, please tag the issue `ai-bug` so the rate can
be tracked over time and fed back into prompt and hook design.

## 10. Where to ask questions

- **Issues**: open one on the GitHub repository for bug reports, feature
  requests, and design questions. Include OS, shell, active harness
  (Claude Code, Codex, Cursor, etc.), and steps to reproduce. Attach
  relevant logs from `.cognitive-os/metrics/` if applicable.
- **Email**: `2144218+MatiasNAmendola@users.noreply.github.com` for matters that are not
  appropriate for a public issue (security disclosure, licensing
  questions, etc.).

## License

By contributing, you agree your contributions will be licensed under
FSL-1.1-MIT. After the 2-year change date, your contributions
automatically convert to MIT along with the rest of the project.

---

If something here is unclear, or you think a policy should be different,
opening an issue to debate it is a perfectly valid contribution.

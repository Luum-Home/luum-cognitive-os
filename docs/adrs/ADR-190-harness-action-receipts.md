---
adr: 190
title: Harness Action Receipts and VCS Event Telemetry
status: accepted
implementation_status: partial
date: '2026-05-06'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit partial/phase scope
---

# ADR-190: Harness Action Receipts and VCS Event Telemetry

## Status

Accepted — 2026-05-06

Implementation baseline — 2026-05-06: added `lib/harness_action_receipts.py`,
`scripts/cos-action-receipt`, and `tests/unit/test_harness_action_receipts.py`
for schema validation, Codex directive parsing, JSONL append, local Git
promotion, pre-push/provider promotion, receipt stats, Markdown reports, and
observe-only dashboard counts. Integrated best-effort receipt emission into
`hooks/direct-main-guard.sh`, `hooks/git-commit-scope-guard.sh`,
`hooks/git-context-capture.sh`, and `scripts/merge-to-main.sh`.

## Context

Codex Desktop can consume structured final-response directives for Git actions,
for example:

```text
::git-stage{cwd="/repo"}
::git-commit{cwd="/repo"}
::git-push{cwd="/repo" branch="main"}
```

Those directives are useful to the host. They give the client a parseable signal
that an action occurred, separate from ordinary prose. They can update UI state,
connect an assistant response to a concrete Git action, or enable follow-up
buttons such as commit, push, or open PR.

However, they are Codex-specific response markup. They are not part of the
Cognitive OS kernel, and they are not safety mechanisms. A final-response
directive is emitted after the action and can be wrong, stale, omitted, or copied
from text. Treating it as an agentic primitive would confuse three layers:

1. **Harness UI protocol** — the host-specific syntax a client parses.
2. **Git operation** — the actual mutation or observation in the repository.
3. **Cognitive OS primitive** — the governed hook, script, rule, queue, memory,
   or telemetry contract that enforces or records behavior.

The repository already has real Git and landing primitives:

- `scripts/git-coop.sh` serializes Git index mutations.
- `hooks/git-commit-scope-guard.sh` blocks unscoped commits that could co-opt
  staged changes from another session.
- `hooks/direct-main-guard.sh` blocks direct `main`/`master` pushes unless they
  flow through merge queue or an audited emergency bypass.
- `hooks/pre-commit-gate.sh`, `hooks/pre-commit-content-hash-dedupe.sh`,
  `hooks/orchestrator-claim-gate.sh`, and `hooks/scope-marker-portability-gate.sh`
  inspect staged changes and high-stakes commit/push claims.
- `scripts/merge-to-main.sh`, `scripts/cos-merge-queue.sh`,
  `scripts/cos-merge-queue-worker.sh`, and `lib/merge_queue.py` provide a
  governed local landing path.
- `docs/architecture/protected-landing-contract.md` defines vendor-neutral
  protected landing across GitHub, GitLab, Gitea/Forgejo, Bitbucket, bare Git,
  and unknown remotes.
- `hooks/git-context-capture.sh` and `lib/git_context.py` record session-end Git
  context.
- `lib/event_bus.py` provides inter-session events for coordination.

The missing piece is not another Codex primitive. The missing piece is a
vendor-neutral receipt vocabulary that can describe action reports from Codex,
Claude Code, shell hooks, provider APIs, merge queues, and future harnesses while
preserving trust boundaries.

## Decision

Cognitive OS will model this as **harness action receipts**.

A harness action receipt is a vendor-neutral event describing a relevant action,
its source, repository context, evidence, and trust level. VCS action receipts are
the first domain and cover Git/provider actions such as stage, commit, branch,
push, pull request creation, queueing, landing, bypass, and conflict detection.

Codex directives such as `::git-stage{...}` are classified as **harness
directives** and may be translated into advisory receipts by an adapter. They are
not Cognitive OS agentic primitives.

The architecture document is:

```text
docs/architecture/harness-action-receipts.md
```

## Trust levels

Receipts must carry a trust label.

| Trust level | Source | Meaning | Safe uses |
|---|---|---|---|
| `advisory` | Final-response directive, transcript text, user paste, external report | The action is claimed, but COS has not verified repository state. | UI hints, non-blocking breadcrumbs, manual debugging. |
| `observed` | Local Git state or read-only provider API | COS observed state consistent with the action. | Session summaries, dashboards, warnings. |
| `verified` | COS hook, Git hook, governed runner, or local policy script | A governed mechanism checked the action path. | Event bus, policy reports, claim-supporting evidence when appropriate. |
| `authoritative` | Merge queue, server-side hook, provider-native protected branch or merge queue | The shared protected state advanced through a governed landing path. | Task closure, landing provenance, release notes, strong audit. |

A raw Codex `::git-stage{...}` directive starts as `advisory`. It can become
`observed` only after local Git verification such as `git diff --cached`. It can
become `verified` only if emitted by an OS-owned hook or governed runner. It can
become `authoritative` only if the merge queue, server-side hook, or provider
protected landing path confirms the shared state change.

## Event taxonomy

Initial VCS receipts use these names:

| Event | Description |
|---|---|
| `vcs.stage` | Files were added to the Git index. |
| `vcs.unstage` | Files were removed from the Git index. |
| `vcs.commit` | A local commit was created. |
| `vcs.branch.create` | A branch was created or selected for isolated work. |
| `vcs.push` | Refs were pushed or attempted against a remote. |
| `vcs.pr.create` | A pull or merge request was opened. |
| `vcs.merge.enqueue` | A branch entered the governed landing queue. |
| `vcs.merge.land` | A protected branch advanced through governed landing. |
| `vcs.bypass` | An emergency bypass occurred and was audited. |
| `vcs.conflict.detected` | Collision, stale work, duplicate patch, or rebase conflict was detected. |

## Schema

The canonical schema is `harness-action-receipt.v1`. The detailed field contract
lives in the architecture document. The minimum shape is:

```json
{
  "schema_version": "harness-action-receipt.v1",
  "event_type": "vcs.stage",
  "domain": "vcs",
  "action": "stage",
  "provider": "codex-desktop",
  "source": "harness-directive",
  "trust": "advisory",
  "project_dir": "/repo",
  "branch": "main",
  "session_id": "session-123",
  "actor": "agent",
  "files": ["lib/example.py"],
  "evidence": {
    "directive": "::git-stage{cwd=\"/repo\"}",
    "observed_git_status": null,
    "hook": null,
    "queue_entry_id": null
  },
  "timestamp": "2026-05-06T12:00:00Z"
}
```

## Storage decision

Receipts should be stored according to their role:

| Storage | Purpose | Allowed trust |
|---|---|---|
| `.cognitive-os/metrics/vcs-actions.jsonl` | Append-only audit for all receipts, including advisory harness directives. | all |
| `.cognitive-os/sessions/events.jsonl` | Inter-session coordination. | `verified` and `authoritative` by default |
| `.cognitive-os/sessions/<session>/git-context.json` | Session-end Git summary. | `observed`, `verified`, `authoritative` |
| `docs/reports/*.md` and dashboard | Human-visible reporting. | all, with trust labels visible |

Advisory receipts must not close tasks, release claims, suppress collision
warnings, or satisfy high-stakes verification. They are UI/audit hints until
promoted by repository evidence.

## Consequences

- Codex Desktop directives remain useful without becoming architectural
  dependencies.
- Cognitive OS gains a portable vocabulary for action telemetry across Codex,
  Claude Code, shell/CI, provider APIs, server-side hooks, and merge queues.
- Existing Git safety primitives remain the enforcement layer.
- Dashboards and future status commands can distinguish advisory claims from
  verified or authoritative actions.
- Provider neutrality is preserved: GitHub-specific PR and merge data can be an
  adapter, not the core schema.
- Future ACC or primitive coverage work can measure whether a surface is
  directive-only, observed, governed, or authoritative.

## Alternatives considered

| Alternative | Decision | Rationale |
|---|---|---|
| Treat `::git-stage` as an agentic primitive | Rejected | It is Codex UI protocol, not an OS-owned hook, skill, rule, script, or memory primitive. |
| Ignore harness directives entirely | Rejected | They are useful receipts for UI, audit, and workflow affordances. The value should be preserved through an adapter. |
| Use final-response directives as proof of action | Rejected | A response marker is post-hoc and can be wrong. Safety and claim verification require repository evidence. |
| Add GitHub-only action telemetry | Rejected | The protected landing contract is vendor-neutral; GitHub is one adapter. |
| Store only authoritative events | Rejected | Advisory and observed receipts are valuable for UX and debugging if clearly labeled. |

## Implementation plan

This ADR accepts the concept and ships the first local implementation slice.
Implementation remains incremental.

1. Done: add `lib/harness_action_receipts.py` and `scripts/cos-action-receipt`
   to validate receipts and append `.cognitive-os/metrics/vcs-actions.jsonl`.
2. Done: add local Git verification helpers for `vcs.stage`, `vcs.commit`,
   `vcs.branch.create`, and remote-ref-backed `vcs.push` so advisory directives
   can be promoted to `observed` when true.
3. Done: add pre-push and provider API evidence promotion paths for `vcs.push`
   and provider-backed receipts.
4. Done for shell/script surfaces: integrate existing primitives:
   - `hooks/direct-main-guard.sh` emits `vcs.push.blocked` and `vcs.bypass`;
   - `hooks/git-commit-scope-guard.sh` emits commit block/bypass receipts;
   - `scripts/merge-to-main.sh` emits `vcs.merge.enqueue`, `vcs.merge.land`, and `vcs.merge.fail`;
   - `hooks/git-context-capture.sh` emits observed session-end commit summaries.
5. Done: parse Codex `::git-*{...}` only as advisory receipts and promote them
   only after verification.
6. Done: expose receipt counts by action/source/trust through CLI stats, a
   Markdown report command, and observe-only dashboard cards.
7. Next: add first-class provider adapters and direct `lib.merge_queue` API emission.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. `docs/architecture/harness-action-receipts.md` defines harness directives, action receipts, trust levels, schema, storage, adapters, and anti-patterns.
2. `docs/adrs/ADR-190-harness-action-receipts.md` records the decision that Codex `::git-*` directives are not agentic primitives.
3. `docs/README.md` links both documents from the documentation index.
4. `lib/harness_action_receipts.py` validates schema, parses Codex directives, appends JSONL receipts, and promotes supported receipts from advisory to observed only after local Git evidence.
5. `scripts/cos-action-receipt` exposes emit, parse-codex, validate, append, and JSON output modes.
6. Unit tests cover schema validation, trust levels, Codex directive parsing, Git-state promotion, pre-push promotion, provider promotion, JSONL append, stats/report output, and CLI behavior.
7. Runtime enforcement is unchanged: advisory receipts cannot satisfy safety gates or high-stakes claim verification.
8. Existing Git primitives emit receipts best-effort and must never fail the guarded Git operation solely because receipt telemetry is unavailable.
```

## Verification

Documentation-only verification for this ADR:

```bash
python3 -m pytest tests/unit/test_harness_action_receipts.py -q
python3 -m py_compile lib/harness_action_receipts.py
bash -n scripts/cos-action-receipt hooks/direct-main-guard.sh hooks/git-commit-scope-guard.sh hooks/git-context-capture.sh scripts/merge-to-main.sh
python3 - <<'PY'
from pathlib import Path
for path in [
    'docs/architecture/harness-action-receipts.md',
    'docs/adrs/ADR-190-harness-action-receipts.md',
    'docs/README.md',
    'lib/harness_action_receipts.py',
    'scripts/cos-action-receipt',
    'tests/unit/test_harness_action_receipts.py',
]:
    assert Path(path).is_file(), path
PY
```

When implementation begins, add unit and contract tests for schema validation,
Codex directive parsing, Git-state promotion, and event-bus trust filtering.

## Related

- [Harness Action Receipts](../architecture/harness-action-receipts.md)
- [Protected Landing Contract](../architecture/protected-landing-contract.md)
- [ADR-116: Multi-Session Coordination Primitives](ADR-116-multi-session-coordination-primitives.md)
- [ADR-064: Harness-Agnostic Cognitive OS](ADR-064-harness-agnostic-cognitive-os.md)
- [ADR-081: Codex Harness Adapter](ADR-081-codex-harness-adapter.md)
- [ADR-112: Codex Governed Tool Layer](ADR-112-codex-governed-tool-layer.md)
- [ADR-189: Surface Implementation Coverage for Agentic Primitives](ADR-189-harness-implementation-coverage.md)

## Alternatives rejected

- Keep action receipts as ad hoc hook logs only; rejected because Codex directives, Git promotion, and event-bus consumers need one durable receipt vocabulary.

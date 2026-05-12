# Harness Action Receipts

> Vendor-neutral contract for recording Git and workflow actions reported by an
> agent harness, without confusing harness UI directives with Cognitive OS
> agentic primitives or safety boundaries.

## Purpose

Some agent hosts expose structured response directives after an action completes.
Codex Desktop, for example, can recognize final-response directives such as:

```text
::git-stage{cwd="/repo"}
::git-commit{cwd="/repo"}
::git-push{cwd="/repo" branch="main"}
```

Those directives are useful, but they are not Cognitive OS primitives. They are
harness-level receipts: structured annotations that a client UI can parse after
an action has already happened. Cognitive OS needs a portable vocabulary for the
useful part of that idea without binding architecture to Codex-specific syntax.

The portable abstraction is a **harness action receipt**: an advisory or verified
record that a relevant action occurred, who reported it, which repository state
supports it, and whether the receipt is strong enough to drive coordination or
only UI presentation.

## Terminology

| Term | Meaning |
|---|---|
| Harness directive | Host-specific markup or protocol emitted by an agent, such as a Codex Desktop `::git-*{...}` directive. |
| Harness action receipt | Vendor-neutral Cognitive OS event describing an observed or reported action. |
| VCS action receipt | A harness action receipt whose domain is version control: stage, commit, branch, push, pull request, merge, tag, revert, rebase. |
| Git operation | The actual repository mutation or query performed by `git`, a provider API, or a governed COS script. |
| Agentic primitive | A governed Cognitive OS construct such as a hook, skill, rule, script, memory primitive, merge queue, or lifecycle controller. |

A harness directive may be an input to a future adapter, but the directive itself
is not an agentic primitive. The primitive is the OS-owned hook/script/event
contract that validates, records, or acts on repository state.

## Why receipts are useful

Action receipts solve a real product problem: plain prose cannot reliably tell a
client, dashboard, or later agent what happened.

A structured receipt can support:

1. **UI awareness** — the host can update visual state after an action, for
   example showing that a commit or push occurred.
2. **Workflow affordances** — the host can enable next-step controls such as
   open PR, inspect staged files, compare branch, or copy commit SHA.
3. **Machine-readable audit** — a receipt can be parsed without NLP and linked
   to the session that reported it.
4. **Cross-session coordination** — when backed by repository evidence, a
   receipt can notify other sessions that a branch landed or a task is stale.
5. **Product analytics** — teams can measure how often agents stage, commit,
   push, bypass, or land through the queue.

Those benefits do not require making Codex-specific response markup part of the
Cognitive OS kernel.

## Trust model

A receipt is only as strong as its source. Cognitive OS must not treat all
receipts equally.

| Trust level | Source | Meaning | Safe uses |
|---|---|---|---|
| `advisory` | Final-response directive, chat text, user paste, external transcript | The agent or harness claims the action happened, but COS has not verified state. | UI hints, non-blocking audit, debugging breadcrumbs. |
| `observed` | Local Git state check such as `git status`, `git diff --cached`, `git rev-parse`, `git log`, or provider read API | COS observed repository state consistent with the action. | Session summaries, dashboards, warnings, coordination hints. |
| `verified` | COS hook, pre-commit hook, pre-push hook, or governed runner emitted the event after checking state. | A governed local mechanism saw and validated the operation path. | Event bus, stale-task handling, policy reports, claim evidence. |
| `authoritative` | Merge queue, protected landing adapter, server-side hook, or provider-native protected branch/merge queue | The protected branch or shared state advanced through the governed path. | Landing provenance, task closure, release notes, strong audit. |

The default for a raw Codex `::git-stage{...}` directive is `advisory`. It can
be promoted to `observed` only if a local adapter verifies that the index or
history changed as claimed. It can be promoted to `verified` or `authoritative`
only when an OS-owned hook, governed runner, merge queue, server hook, or remote
protection adapter emitted the receipt.

## Non-negotiable rule

A final-response directive is never a safety boundary.

Cognitive OS must enforce safety with repository state and governed execution:

- `git diff --cached`, `git status`, `git log`, `git rev-parse`, and related
  local observations;
- PreToolUse and Git hooks that block unsafe commands before execution;
- pre-commit and pre-push checks;
- branch writer leases and Git index locks;
- the merge queue and protected landing contract;
- server-side hooks or provider-native protected branches where available.

A receipt can describe or corroborate what happened. It must not replace the
mechanism that made the action safe.

## Relationship to existing Cognitive OS primitives

The repository already contains several Git and landing primitives. Harness
action receipts should compose with these instead of replacing them.

| Existing surface | Path | Role relative to receipts |
|---|---|---|
| Git index coordination | `scripts/git-coop.sh` | Serializes index mutations. A future `vcs.stage` receipt should indicate whether this lock was held. |
| Commit scope guard | `hooks/git-commit-scope-guard.sh` | Blocks unsafe unscoped commits. A `vcs.commit` receipt is stronger if this guard allowed the command. |
| Direct-main guard | `hooks/direct-main-guard.sh` | Blocks direct pushes to `main`/`master` unless merge queue or audited bypass. A `vcs.push` receipt must identify direct, bypass, or queue path. |
| Destructive Git blocker | `hooks/destructive-git-blocker.sh` | Blocks high-risk Git commands. Receipts for rebase, reset, restore, clean, and force-push must not bypass this layer. |
| Pre-commit gate | `hooks/pre-commit-gate.sh` | Checks staged files for content policy and derived artifacts. A commit receipt can reference this result. |
| Content-hash dedupe | `hooks/pre-commit-content-hash-dedupe.sh`, `scripts/precommit_content_hash.py` | Detects staged patch collisions with `origin/main`; can emit `conflict_detected`. |
| Orchestrator claim gate | `hooks/orchestrator-claim-gate.sh`, `scripts/orchestrator_claim_gate.py` | Blocks high-stakes commit/push claims without evidence. Receipts should not count as independent evidence unless verified. |
| Scope-marker portability gate | `hooks/scope-marker-portability-gate.sh` | Checks staged `SCOPE: both` artifacts for portability proof. |
| Merge queue | `scripts/merge-to-main.sh`, `scripts/cos-merge-queue.sh`, `scripts/cos-merge-queue-worker.sh`, `lib/merge_queue.py` | Authoritative local landing path; emits queue events and should produce `vcs.merge.land` receipts. |
| Protected landing contract | `docs/04-Concepts/architecture/protected-landing-contract.md` | Vendor-neutral invariant for shared branch advancement. Receipts must report whether landing was locally queued, server-protected, provider-native, or unknown. |
| Git context capture | `hooks/git-context-capture.sh`, `lib/git_context.py` | Stop-time session audit; can summarize receipts and verify start/end commit state. |
| Event bus | `lib/event_bus.py` | Inter-session channel for verified or authoritative receipts that affect coordination. |
| Branch writer leases | `scripts/cos_branch_lease.py`, `scripts/cos-branch-lease` | Same-branch write ownership; receipts can carry lease owner/session metadata. |

## Current implementation

The baseline receipt primitive is implemented in:

```text
lib/harness_action_receipts.py
scripts/cos-action-receipt
tests/unit/test_harness_action_receipts.py
```

The library validates `harness-action-receipt.v1`, parses Codex-style
`::git-*{...}` directives as advisory receipts, appends receipts to
`.cognitive-os/metrics/vcs-actions.jsonl`, and can promote selected VCS receipts
after stronger evidence. Current promotion rules cover:

- `vcs.stage` to `observed` from `git diff --cached --name-only`;
- `vcs.commit` to `observed` from current `HEAD`;
- `vcs.branch.create` to `observed` from the current branch;
- `vcs.push` to `observed` when the local branch SHA matches the remote ref;
- `vcs.push` to `verified` when matching pre-push refs are supplied;
- push/PR/merge receipts to `authoritative` when provider API evidence includes `accepted=true`.

The CLI can be used directly:

```bash
scripts/cos-action-receipt emit vcs.stage \
  --provider codex-desktop \
  --source harness-directive \
  --project-dir . \
  --file docs/example.md \
  --append --json

scripts/cos-action-receipt parse-codex \
  --text '::git-stage{cwd="/repo"}' \
  --promote-git --append --json

scripts/cos-action-receipt stats --json
scripts/cos-action-receipt report --output docs/06-Daily/reports/vcs-action-receipts-latest.md --json
```

The implementation intentionally does not change enforcement behavior. Receipts
are telemetry. Safety still comes from hooks, Git state, merge queue, protected
landing, and provider/server enforcement.

## Proposed schema

A receipt is a small JSON object. It should be easy to append to JSONL, send
through the event bus, or render in a dashboard.

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
  "files": ["lib/lethal_trifecta.py"],
  "commit_sha": null,
  "remote": null,
  "protected_branch": false,
  "governed_path": null,
  "evidence": {
    "directive": "::git-stage{cwd=\"/repo\"}",
    "observed_git_status": null,
    "hook": null,
    "queue_entry_id": null,
    "remote_provider": null
  },
  "timestamp": "2026-05-06T12:00:00Z"
}
```

### Required fields

| Field | Requirement |
|---|---|
| `schema_version` | Must be `harness-action-receipt.v1` for this contract. |
| `event_type` | Namespaced event such as `vcs.stage`, `vcs.commit`, `vcs.push`, `vcs.pr.create`, `vcs.merge.land`. |
| `domain` | `vcs` initially; future domains may include `issue`, `artifact`, `automation`, or `deployment`. |
| `action` | Short verb within the domain. |
| `provider` | The reporting harness or adapter: `codex-desktop`, `claude-code`, `shell-git-hook`, `github`, `gitlab`, `cos-merge-queue`, `unknown`. |
| `source` | Where the receipt came from: `harness-directive`, `local-git-observation`, `git-hook`, `governed-runner`, `merge-queue`, `server-hook`, `provider-api`. |
| `trust` | One of `advisory`, `observed`, `verified`, `authoritative`. |
| `project_dir` | Absolute or redacted project root. Public reports must avoid developer-home leakage. |
| `branch` | Current or target branch if known. |
| `timestamp` | UTC ISO-8601 timestamp. |

### Optional fields

| Field | Meaning |
|---|---|
| `files` | Files affected or selected. For large sets, include a count and hash instead of the full list. |
| `commit_sha` | Commit created, landed, reverted, or pushed. |
| `remote` | Remote name or provider URL, redacted if private. |
| `protected_branch` | Whether the action targeted a protected branch such as `main` or `master`. |
| `governed_path` | `git-coop`, `pre-commit`, `pre-push`, `merge-to-main`, `provider-merge-queue`, `server-hook`, or `bypass`. |
| `queue_entry_id` | Merge queue entry when applicable. |
| `bypass_reason` | Required for emergency bypass receipts. Must not contain secrets. |
| `evidence` | Tool-specific corroborating facts, never credentials. |

## Event taxonomy

Initial VCS events:

| Event | Meaning | Minimum trustworthy source |
|---|---|---|
| `vcs.stage` | Files were added to the Git index. | `observed` from `git diff --cached --name-only`; `advisory` if only from harness directive. |
| `vcs.unstage` | Files were removed from the Git index. | `observed` from index diff before/after. |
| `vcs.commit` | A local commit was created. | `verified` from pre-commit/git hook or `observed` from `git log` delta. |
| `vcs.branch.create` | A branch was created or switched for work isolation. | `observed` from Git refs; `verified` from `scripts/cos-session-branch.sh` when used. |
| `vcs.push` | Refs were pushed to a remote. | `observed` from remote-ref verification, `verified` from pre-push refs, `authoritative` from provider/protected landing acceptance. |
| `vcs.push.blocked` | A governed guard blocked a push. | `verified` from `direct-main-guard` or pre-push guard. |
| `vcs.pr.create` | Pull/merge request was opened. | `observed` or `verified` from provider API/CLI. |
| `vcs.merge.enqueue` | Branch was queued for landing. | `verified` from `lib.merge_queue.enqueue`. |
| `vcs.merge.land` | Protected branch advanced through governed landing. | `authoritative` from merge queue, server hook, or provider-native merge queue. |
| `vcs.bypass` | Emergency direct-main or safety bypass occurred. | `verified` when written by a guard; must include reason and actor. |
| `vcs.conflict.detected` | Collision or stale work was detected. | `verified` from content-hash dedupe, push collision check, or merge queue rebase conflict. |

## Storage surfaces

Receipts have different storage needs depending on trust and use.

| Storage | Use | Trust levels |
|---|---|---|
| `.cognitive-os/metrics/vcs-actions.jsonl` | Append-only local audit of all receipts, including advisory. | all |
| `.cognitive-os/sessions/events.jsonl` | Cross-session coordination events that other agents may act on. | `verified`, `authoritative` only by default |
| `.cognitive-os/sessions/<session>/git-context.json` | End-of-session summary and commit/diff record. | `observed`, `verified`, `authoritative` |
| `docs/06-Daily/reports/*.md` / dashboard | Human reporting. | all, with trust labels visible |

Advisory harness directives should not be broadcast through the coordination bus
unless an adapter clearly marks them advisory and consumers refuse to close tasks
or suppress warnings from advisory events alone.

## Adapter model

A harness adapter may translate host-specific receipts into the neutral schema.

### Codex Desktop adapter

Input examples:

```text
::git-stage{cwd="/repo"}
::git-commit{cwd="/repo"}
::git-push{cwd="/repo" branch="main"}
```

Default mapping:

| Codex directive | Neutral event | Default trust | Promotion path |
|---|---|---|---|
| `::git-stage` | `vcs.stage` | `advisory` | Run `git diff --cached --name-only` and attach observed files. |
| `::git-commit` | `vcs.commit` | `advisory` | Compare `HEAD` before/after or inspect session git context. |
| `::git-push` | `vcs.push` | `advisory` | Verify pre-push hook result, remote ref, protected landing path. |
| `::git-create-branch` | `vcs.branch.create` | `advisory` | Verify local ref and current branch. |
| `::git-create-pr` | `vcs.pr.create` | `advisory` | Verify provider API/CLI returns PR URL and head/base. |

The adapter must preserve the distinction between the directive and the
operation. For example, `::git-push{branch="main"}` emitted after a blocked push
must not become a successful `vcs.push` receipt. It may become an advisory
`vcs.push.attempt` receipt with evidence that the operation failed.

### Shell/Git hook adapter

Git hooks are stronger because they run in the operation path. A pre-commit hook
can emit a `verified` `vcs.commit.attempt` or `vcs.commit.blocked` event. A
post-commit hook, if installed, can emit `verified` `vcs.commit` with the new
SHA. A pre-push hook can emit `verified` `vcs.push.attempt`; remote acceptance
still requires remote evidence.

### Merge queue adapter

The merge queue is an authoritative source for local protected landing. It
already emits `merge_queued`, `merge_completed`, and `merge_failed` through
`lib.event_bus`. A future adapter can mirror those into:

```text
vcs.merge.enqueue
vcs.merge.land
vcs.merge.fail
```

with `trust=authoritative` when the protected branch was advanced by
`COS_MERGE_QUEUE_WORKER=1` or `COS_MERGE_TO_MAIN=1` and the push succeeded.

## Safety and privacy requirements

Receipts must follow the same safety constraints as other OS telemetry:

1. **No credentials** — never include tokens, API keys, private URLs with embedded
   credentials, or secret file contents.
2. **Path privacy** — public reports should redact developer-home prefixes or use
   project-relative paths where possible.
3. **No false closure** — advisory receipts cannot close tasks, mark plans done,
   or satisfy high-stakes claims.
4. **Bypass visibility** — emergency direct-main or direct-push bypass receipts
   must include a scoped reason and actor.
5. **Provider neutrality** — GitHub, GitLab, Gitea/Forgejo, Bitbucket, bare Git,
   and unknown remotes must fit the same schema.
6. **Append-only audit** — receipt logs should be append-only unless explicitly
   archived by a governed maintenance script.

## Recommended implementation phases

### Phase 0 — Documentation only

Accept the vocabulary and trust model. Do not change enforcement behavior.

### Phase 1 — Local receipt writer

Status: implemented baseline.

Implemented files:

```text
lib/harness_action_receipts.py
scripts/cos-action-receipt
tests/unit/test_harness_action_receipts.py
```

Capabilities:

- validate schema;
- parse Codex `::git-*{...}` directives as advisory receipts;
- append to `.cognitive-os/metrics/vcs-actions.jsonl`;
- verify Git state for `vcs.stage`, `vcs.commit`, `vcs.branch.create`, and remote-ref backed `vcs.push`;
- promote `vcs.push` with pre-push refs and provider API acceptance evidence;
- summarize receipts by trust/event/source with `stats`;
- render a Markdown report with `report`;
- expose observe-only dashboard counts from `.cognitive-os/metrics/vcs-actions.jsonl`.

Remaining Phase 1 hardening:

- add redaction modes for public reports;
- add first-class provider adapters instead of generic provider evidence JSON.

### Phase 2 — Existing primitive integration

Status: implemented for the local shell/script surfaces.

Existing governed Git surfaces now emit receipts best-effort:

- `hooks/git-commit-scope-guard.sh` for unscoped commit blocks and bypasses;
- `hooks/direct-main-guard.sh` for direct-main push blocks and bypasses;
- `scripts/merge-to-main.sh` for merge enqueue, failure, and authoritative landing;
- `hooks/git-context-capture.sh` for session-end observed commit summaries.

Remaining Phase 2 hardening:

- mirror `lib.merge_queue` API events directly into receipts;
- add post-commit/post-push hook adapters where installed by Git rather than agent harnesses.

### Phase 3 — Harness directive adapters

Parse Codex Desktop final-response directives only as advisory receipts. Promote
them after local verification when possible. Future Claude, Cursor, OpenCode,
Aider, or shell/CI adapters can emit the same schema from their own metadata.

### Phase 4 — Dashboard and ACC visibility

Expose counts by action, provider, source, and trust level. The dashboard should
make advisory receipts visibly different from verified and authoritative receipts.

## Anti-patterns

Do not:

- add `::git-stage` or any Codex syntax to the list of Cognitive OS agentic
  primitives;
- let a final-response directive satisfy claim verification;
- broadcast advisory receipts as task-completion events;
- treat local hook success as proof of remote branch protection;
- require GitHub-specific APIs for the core receipt contract;
- hide direct-main bypasses in generic `vcs.push` rows without bypass metadata.

## Related documents

- [ADR-190: Harness Action Receipts and VCS Event Telemetry](../adrs/ADR-190-harness-action-receipts.md)
- [Protected Landing Contract](protected-landing-contract.md)
- [ADR-116: Multi-Session Coordination Primitives](../adrs/ADR-116-multi-session-coordination-primitives.md)
- [Harness Driver Parity](harness-driver-parity.md)
- [Codex Governed Tool Layer](codex-governed-tool-layer.md)
- [ADR-064: Harness-Agnostic Cognitive OS](../adrs/ADR-064-harness-agnostic-cognitive-os.md)
- [ADR-189: Surface Implementation Coverage for Agentic Primitives](../adrs/ADR-189-harness-implementation-coverage.md)

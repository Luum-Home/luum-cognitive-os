---

adr: 246
title: Release Transaction Freeze for Destructive and Public-State Operations
status: accepted
implementation_status: partial
classification_basis: 'Slice A read-only/lock-file freeze exists; future slices explicitly remain open'
relationship_chain_exempt: true
date: 2026-05-08
supersedes: []
superseded_by: null
extends: [ADR-218, ADR-239, ADR-240, ADR-242, ADR-243]
implementation_files:
  - scripts/cos-release-freeze
  - lib/release_freeze.py
  - manifests/release-freeze.yaml
  - tests/behavior/test_release_freeze.py
tier: maintainer
tags: [release, history-rewrite, force-push, freeze, multi-agent-safety, postmortem-2026-05-08]
---

<!-- ADR_RELATION_CHAIN_EXEMPT: part of the 2026-05-08 implementation-ledger ADR burst; relationship depth is tracked by control-plane audits rather than new transitive ADR scope. -->

# ADR-246: Release Transaction Freeze for Destructive and Public-State Operations

## Status

Accepted — Slice A implemented. `scripts/cos-release-freeze` now provides `--prepare`, `--begin`, `--status`, and `--end`; receipts are written under `.cognitive-os/runtime/release-freeze/`; history sanitization refuses during an active freeze unless `COS_RELEASE_TRANSACTION_ID` matches. Drafted after the 2026-05-08 pre-public readiness session exposed a
repeated pattern: agents and hooks could keep producing new state while the
operator was preparing history rewrites, force-pushes, public sanitization, and
release-readiness gates.

## Context

Several incidents in the same session were not independent bugs. They were all
symptoms of **no transactional control-plane boundary** around public/destructive
operations.

Observed incidents:

| Incident | Concrete case | Risk | Current mitigation | Remaining gap |
|---|---|---|---|---|
| Agents changing branches without notice | Commits landed on `fix/c4-portability-test-failures` while the operator expected `main` | Operator believes a commit landed in one branch while the agent committed elsewhere | Branch-switch blocker for `git switch` / `git checkout <branch>` | No release-level branch freeze receipt yet |
| Sensitive data reintroduced after sanitize | A readiness doc reintroduced the private operator email after a sanitize pass | A clean history becomes dirty again in the next commit | `scripts/cos-pre-public-risk-audit` detects configured sensitive tokens | Final content-only rewrite still needed before publication |
| Content rewrite confused with metadata rewrite | ADR-218 initially allowed author/committer rewrite paths | Human authorship could be erased or replaced by placeholders | Content-only default; metadata rewrite requires `COS_HISTORY_SANITIZE_METADATA=1` | Release freeze should assert metadata rewrite flag is absent unless explicitly approved |
| Concurrent agents writing during force-push/rewrite prep | Gates repeatedly saw dirty worktrees while agents were still producing files | Rewrite or force-push can exclude parallel work or rewrite an unstable snapshot | Dirty-tree block in pre-public risk audit | No formal pause/kill/receipt for active agents |
| Security reports containing sensitive patterns | A report embedded a literal local path regex | The security report itself becomes the leak | Manual redaction in residue report | Report generators need release freeze output-sanitization mode |
| Script rename outside ownership | `scripts/audit_engram_topic_keys.py` appeared while the hyphenated script was deleted | Accidental duplicate or loss under concurrent ownership | Manual restore | Freeze should block non-allowlisted file moves during release prep |
| Pre-public audit false positive | Markdown table text looked like a provider identity | Noisy gate trains operators to ignore warnings | Regex narrowed to real email identity shape | Freeze should separate block findings from reviewable warnings |
| Scorecards drifted from repo state | Hook count said 216 while repo had 218 | Audit theater: reports imply coverage they do not have | Count tests and updated scorecards | Freeze should regenerate/read current reports before publish |
| Agents announced closed with blockers alive | Disclosure was “closed” while audit still blocked on dirty tree/token history | False sense of readiness | Final clean-repo audit required | Freeze should make “closed” impossible until gate receipt is pass |
| Hooks treated as authority merely by existing | Several primitives existed but were not wired on every path | “We have the primitive” becomes mistaken proof of enforcement | ADR-240 primitive coherence audit | Freeze should require primitive-coherence result in the release receipt |

The common failure is not missing tooling. Cognitive OS had many of the right
primitives. The missing abstraction was a **release transaction**: a short-lived,
audited mode in which writes are frozen, state is checked, destructive operations
are allowed only after a receipt, and publication/force-push must reference that
receipt.

## Decision

Introduce `cos release freeze` as a transaction primitive for high-risk public
or destructive operations.

A release freeze creates a `release_transaction_id` and writes an immutable
receipt under `.cognitive-os/runtime/release-freeze/<id>.json` plus a
human-readable copy under `.cognitive-os/reports/release-freeze/<id>.md`.

The command has three phases:

1. **Prepare** — verify the repo is stable enough to enter freeze.
2. **Freeze** — block or pause new non-allowlisted mutations.
3. **Release operation window** — allow specific operations such as content-only
   history sanitize, post-rewrite force-push, tag update, or public publish only
   when they reference the active transaction id.

## Required checks in `cos release freeze`

The first implementation must check:

1. Working tree is clean, unless paths are explicitly allowlisted in
   `manifests/release-freeze.yaml`.
2. Current branch is the expected release branch (`main` by default).
3. No active agent worktrees, task claims, heartbeats, or daemon processes are
   writing to the repo unless explicitly acknowledged.
4. No branch switch occurred after freeze start.
5. `scripts/cos-pre-public-risk-audit --strict` passes or records explicit
   operator-accepted warnings.
6. `scripts/primitive-coherence-audit.py --json` is captured in the receipt.
7. History sanitize metadata rewrite flag is absent unless the transaction
   explicitly declares `allow_metadata_rewrite: true`.
8. Any force-push must reference a recent rewrite marker from ADR-243 or be
   refused.
9. Any generated report included in public docs must pass output sanitization
   for configured private tokens and local path patterns.
10. Any agent completion claiming “closed” must attach the release transaction id
    and the final gate receipt.

## Non-goals

- Do not kill processes blindly in Slice A.
- Do not auto-rewrite history.
- Do not auto-force-push.
- Do not delete branches or worktrees.
- Do not convert human author emails to placeholders.
- Do not treat hooks as active merely because files exist.

## Slice A implementation

Slice A is read-only plus lock-file creation:

```bash
scripts/cos-release-freeze --prepare --json
scripts/cos-release-freeze --begin --reason pre-public-history-sanitize
scripts/cos-release-freeze --status --json
scripts/cos-release-freeze --end --transaction-id <id>
```

`--begin` refuses if the prepare checks fail. When it succeeds, it writes the
active transaction marker. Other destructive primitives may then require
`COS_RELEASE_TRANSACTION_ID=<id>`.

## Future slices

- Hook integration: commit/push/history-rewrite hooks refuse when a freeze is
  active and the command lacks the transaction id.
- Agent integration: active orchestrators pause launching write agents during a
  freeze.
- Daemon integration: detached agent daemons drain/stop new work during a freeze.
- Report sanitization mode: public reports generated during freeze redact local
  paths and configured tokens by construction.
- Merge queue integration: force-push and tag update flows consume the freeze
  receipt rather than requiring broad `--no-verify` bypasses.

## Operational Guide

### What changes for the operator

Before this ADR, the operator had no formal mechanism to pause the system
before destructive or public-state operations (history sanitization, force-push,
publication). Agents could keep producing new state while release gates were
running — creating a moving-target problem where a passing audit could be
immediately invalidated by the next agent commit.

After this ADR, the operator uses `scripts/cos-release-freeze` to create a
**release transaction** — a receipt-backed mode that:

1. Checks repo stability before entry (`--prepare`).
2. Writes an immutable receipt under `.cognitive-os/runtime/release-freeze/<id>.json`
   when the freeze begins (`--begin`).
3. Requires other destructive primitives (history sanitization, post-rewrite
   push exception) to present `COS_RELEASE_TRANSACTION_ID=<id>` before executing.
4. Ends the freeze and clears the receipt (`--end`).

The standard sequence before any public or destructive operation:

```bash
scripts/cos-release-freeze --prepare --json
scripts/cos-release-freeze --begin --reason pre-public-history-sanitize
export COS_RELEASE_TRANSACTION_ID=<id from receipt>
# … run sanitize, force-push, publish …
scripts/cos-release-freeze --end --transaction-id "$COS_RELEASE_TRANSACTION_ID"
```

### What this answers (and what it doesn't)

**Answers:**
- "How do I prove no new commits appeared after the release operation began?"
  — The freeze receipt captures HEAD at begin-time; audit can compare.
- "Why did history sanitization refuse to execute?" — A freeze is active and
  `COS_RELEASE_TRANSACTION_ID` was not set. Run `scripts/cos-release-freeze --status --json` to see the active receipt.
- "Can I override the freeze for an emergency fix?" — Yes, but the bypass is
  logged to `agent-audit-trail.jsonl`.

**Does not answer:**
- Whether agents are actually stopped. Slice A is read-only plus lock-file
  creation; full agent/daemon pausing requires future slices (see §Future slices).
- Whether the repo is ready for publication beyond the Slice A checks. A
  passing freeze does not replace `scripts/cos-pre-public-risk-audit --strict`.

### When sources disagree

If `scripts/cos-release-freeze --status --json` reports no active freeze, but
`COS_RELEASE_TRANSACTION_ID` is set in the environment, the env var is stale
from a previous session. Clear it: `unset COS_RELEASE_TRANSACTION_ID`.

If `--prepare` passes but `--begin` fails, inspect the blocking check in the
JSON output. Common causes: dirty working tree, active agent/task liveness
detected, or wrong branch.

The receipt under `.cognitive-os/runtime/release-freeze/` is the authoritative
state source. Environment variables and verbal claims are not.

## Alternatives rejected

- **Rely on clean working tree only** — rejected because a clean tree does not
  prove that agents are not about to write again.
- **Rely on humans to remember to stop agents** — rejected because the session
  repeatedly showed concurrent agents producing new state while release gates ran.
- **Disable all hooks during rewrite/push** — rejected because it removes the
  very controls needed to keep the operation safe.
- **Run sanitizer repeatedly until clean** — rejected because repeated rewrites
  without a transaction id create SHA churn and destroy operator trust.

## Acceptance criteria

1. Freeze prepare blocks on dirty working tree.
2. Freeze prepare blocks when active agent/task liveness is detected.
3. Freeze begin writes a transaction receipt with branch, HEAD, checks, and
   allowed operations.
4. History sanitize execute refuses during freeze unless
   `COS_RELEASE_TRANSACTION_ID` matches the active receipt.
5. Post-rewrite push exception refuses without the same transaction id.
6. Final pre-public audit can cite the freeze receipt and prove no new commits
   appeared after the release operation window began.

## Consequences

Positive:

- Gives destructive/public operations a stable audited snapshot instead of a
  moving target.
- Prevents sanitize/force-push/publish workflows from racing with background
  agents.
- Makes “release ready” a receipt-backed state, not an agent claim.
- Provides one transaction id that ADR-218, ADR-242, ADR-243, ADR-240, and
  pre-public risk gates can all reference.

Negative:

- Adds ceremony before high-risk operations.
- Can block legitimate emergency fixes unless an explicit override path exists.
- Requires agent/daemon integration before it can fully pause all writers.
- Slice A will be conservative and may initially report active-agent false
  positives until liveness sources are normalized.

## Verification

```bash
python3 -m pytest tests/behavior/test_release_freeze.py tests/audit/test_adr_contracts.py -q
scripts/cos-release-freeze --prepare --json
scripts/cos-release-freeze --begin --reason pre-public-history-sanitize --json
scripts/cos-release-freeze --status --json
scripts/cos-release-freeze --end --transaction-id "$COS_RELEASE_TRANSACTION_ID" --json
```

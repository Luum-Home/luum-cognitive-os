---
adr: 269
title: Mandatory ADR Reference for History Rewrites
status: accepted
implementation_status: implemented
date: 2026-05-11
supersedes: []
superseded_by: null
extends:
- ADR-218
- ADR-242
- ADR-243
- ADR-246
implementation_files:
- manifests/history-rewrite-ledger.yaml
- hooks/history-rewrite-documented.sh
- scripts/cos-history-rewrite-audit
- lib/history_sanitization.py
- lib/history_rewrite_ledger.py
tier: maintainer
tags:
- history-rewrite
- governance
- transparency
- postmortem-2026-05-08
- postmortem-2026-05-11
related_postmortems:
- docs/reports/silent-agent-branch-switch-postmortem-2026-05-08.md
- docs/reports/git-history-debug-script-audit-2026-05-09.md
- docs/reports/history-sanitization-20260508T061208Z.json
related_adrs:
- ADR-218 (history sanitization toolchain)
- ADR-242 (filter-repo wrapper preserves remote)
- ADR-243 (post-rewrite push-collision exception)
- ADR-246 (release transaction freeze)
- ADR-268 (defensive history sanitization 2026-05-11, sibling doc)
relationship_chain_exempt: true
relationship_chain_exemption_reason: ADR-269 intentionally consolidates the history-rewrite safety chain (ADR-218/242/243/246) into an implementation ledger for mandatory ADR references; audit depth is documented rather than scope-creep.
---

# ADR-269 — Mandatory ADR Reference for History Rewrites

## Status

Accepted (2026-05-11). Implementation lands in companion commit set.

## Context

The 2026-05-08 incident (silent agent branch switch, see related postmortem) and
the 2026-05-09 git-history debug script audit established that `git filter-repo`
and the broader history-rewrite toolchain need safety guardrails (preserve
origin, refuse idempotent re-runs, backup mandatory). ADRs 218 / 242 / 243 / 246
codified those safety primitives.

The 2026-05-11 defensive history sanitization (commit-message rewrite to reduce
external-pattern attribution surface; documented in ADR-268) surfaced a
**second gap orthogonal to safety**: there is no machine-enforced requirement
that a history rewrite be **documented** in an Accepted ADR.

Today, an operator (or an agent) can:

1. Run `git filter-repo` directly (the destructive-rm-blocker / destructive-git-blocker
   hooks do not match it; ADR-055b only covers `stash pop/drop/apply`, `reset`,
   `pull --rebase`, `checkout`, `clean -f`, `restore`, `revert`, `worktree`,
   `branch -D`, `rebase`).
2. Bypass `scripts/cos-filter-repo-wrap.sh` entirely (it's an opt-in wrapper).
3. Run `scripts/cos-history-sanitization --execute --yes` without referencing
   any ADR (the `--adr-ref` flag does not exist).
4. Leave the resulting `.cognitive-os/recovery/pre-history-sanitization-<ts>.bundle`
   on disk without any registry pointing at it.

If a later auditor (internal review, IP discovery, compliance review) asks
"why was this rewrite done?", the answer depends on:

- Whether the operator at the time wrote a postmortem or ADR.
- Whether they remembered to do so months later.
- Whether the commit log preserves enough context to reconstruct intent.

The 2026-05-11 sanitization escapes that risk because ADR-268 is being written
*now*, in the same session, with operator attention focused on the question.
The risk for **future** rewrites is non-trivial: any session that runs filter-repo
without contemporaneous documentation creates an orphan bundle and a gap in the
audit trail. Opposing counsel in IP discovery could frame the orphan as
"concealment without explanation".

The fix is mechanical, not procedural: the act of executing a history rewrite
must require a reference to an Accepted ADR documenting why.

## Decision

Adopt a **four-primitive enforcement layer** for history-rewrite documentation,
operating at three different time points (pre-execute gate, post-rewrite ledger
entry, periodic audit).

### Primitive 1 — `manifests/history-rewrite-ledger.yaml` (append-only)

A single canonical registry of every history rewrite performed against this
repository. Schema:

```yaml
schema_version: history-rewrite-ledger/v1
entries:
  - timestamp: '2026-05-11T17:32:04Z'
    operator: <operator-id>
    adr_ref: ADR-268
    reason: |
      Defensive sanitization of external-pattern attribution per ADR-268.
      ADR-261..264 paper trail retained in ADRs themselves.
    bundle_path: .cognitive-os/recovery/pre-history-sanitization-20260511T173204Z.bundle
    sha_before: aabc49b3
    sha_after: f9d7cc54
    rewrite_scope: commit-messages-only
    tool: git-filter-repo
    invocation: 'git filter-repo --message-callback ...'
```

Append-only enforced by:
- File-level guard (`hooks/append-only-guard.sh` or similar; if it exists today,
  reuse; if not, the ledger lives under `manifests/` and edits are gated by
  pre-commit review).
- Test: `tests/contracts/test_history_rewrite_ledger_append_only.py` asserts
  that all prior entries remain byte-identical in any diff touching this file.

### Primitive 2 — `hooks/history-rewrite-documented.sh` (SessionStart hook)

Runs at session start (Claude Code SessionStart event). Reads all
`.cognitive-os/recovery/pre-history-sanitization-*.bundle` files. Cross-references
each with the ledger. For any bundle without a ledger entry **and** without a
matching ADR (search ADR files for the bundle timestamp or filename), emit a
visible WARNING:

```
⚠️  UNDOCUMENTED HISTORY REWRITE DETECTED
  Bundle: .cognitive-os/recovery/pre-history-sanitization-20260511T173204Z.bundle
  No matching entry in manifests/history-rewrite-ledger.yaml
  No matching ADR in docs/adrs/ referencing this bundle
  Action required: run `scripts/cos-history-rewrite-audit --register <bundle> --adr ADR-NNN --reason "..."`
```

Non-blocking warn (visible at session start). Operator sees it every session
until resolved.

Bypass: `COS_ALLOW_UNDOCUMENTED_REWRITES=1` (logged with reason).

### Primitive 3 — `scripts/cos-history-rewrite-audit` (CLI)

Operator-facing CLI for ledger inspection and remediation:

```
cos-history-rewrite-audit --list
    # Shows all entries from manifests/history-rewrite-ledger.yaml + matching
    # ADR references + bundle existence verification

cos-history-rewrite-audit --orphans
    # Lists bundles in .cognitive-os/recovery/ WITHOUT matching ledger entries
    # Lists ledger entries WITHOUT corresponding bundles on disk (lost evidence)
    # Lists ledger entries WITH adr_ref pointing at non-existent ADR

cos-history-rewrite-audit --register <bundle-path> --adr ADR-NNN --reason "..."
    # Append a new entry to the ledger registering an existing bundle
    # Verifies bundle exists, ADR exists and is Accepted, reason is non-empty
    # Refuses to overwrite existing entries (append-only)
```

Output formats: human-readable table by default, `--json` for automation.

### Primitive 4 — `--adr-ref` required flag on history rewrites

Modify `lib/history_sanitization.py` and `scripts/cos-filter-repo-wrap.sh`:

- `scripts/cos-history-sanitization --execute` REQUIRES `--adr-ref ADR-NNN`.
  Without it, fails with:
  ```
  ERROR: history rewrites require ADR documentation per ADR-269.
  Re-run with --adr-ref ADR-NNN where ADR-NNN is an Accepted ADR
  documenting the rewrite rationale. If no such ADR exists, create
  one first using docs/adrs/templates/history-rewrite.template.md.
  ```
- `scripts/cos-filter-repo-wrap.sh` similarly requires `--adr-ref` argument.
- Both tools, on successful execution, write a ledger entry automatically
  via `lib/history_rewrite_ledger.py`.
- Direct `git filter-repo` invocations bypass these — addressed by adding
  filter-repo to the DESTRUCTIVE_PATTERN in `hooks/destructive-git-blocker.sh`,
  with the documented bypass being "use the cos-filter-repo-wrap.sh wrapper
  with --adr-ref".

### Coverage matrix

| Rewrite entry point | Pre-gate | Ledger write | Post-detect |
|---|---|---|---|
| `cos-history-sanitization --execute` | requires `--adr-ref` | auto-writes ledger | n/a |
| `cos-filter-repo-wrap.sh` | requires `--adr-ref` | auto-writes ledger | n/a |
| Direct `git filter-repo` | DESTRUCTIVE block, must bypass via wrapper | manual `--register` after | `history-rewrite-documented.sh` warns at next session |
| Any other path (custom script, etc.) | n/a (not covered) | manual `--register` after | `history-rewrite-documented.sh` warns at next session |

## Rationale

**Why mandatory and not advisory.** ADR-218 and ADR-242 already had advisory
language ("operator should document, backup is recommended"). The 2026-05-11
sanitization (this session) almost slipped without an ADR — only the operator's
direct concern about transparency triggered ADR-268. Advisory does not scale to
multi-agent workflows where any agent can run destructive commands.

**Why a ledger and not just ADRs.** ADRs are narrative and assume contemporaneous
authorship. The ledger is a structured machine-readable index that enables:

- `--list` and `--orphans` audits in seconds.
- Cross-validation that an ADR with a given number actually exists and is
  Accepted (not Proposed, not Superseded).
- Append-only contract that creates a tamper-evident audit trail.

**Why startup banner and not commit-time gate.** The bundles are evidence of
past rewrites, not active mutations. Blocking commits because of past
undocumented rewrites would be punitive. A persistent visible WARNING at session
start surfaces the deuda de documentación without blocking forward work.

**Why `--adr-ref` on the wrapper but not on direct filter-repo.** The wrapper
is opt-in. Adding filter-repo to DESTRUCTIVE_PATTERN forces all rewrite paths
through the wrapper (or through an explicit `COS_ALLOW_DESTRUCTIVE_GIT=1`
bypass that is logged to `agent-audit-trail.jsonl`). The bypass remains
available for emergencies but creates a paper trail.

## Consequences

### Positive

- Mechanical defense against the "concealment narrative" — every history rewrite
  has a contemporaneous ADR or explicit bypass record.
- Auditor experience: `cos-history-rewrite-audit --list` returns the full set
  in seconds with ADR cross-references.
- Orphan bundles become visible (startup banner) instead of accumulating silently.
- Direct `filter-repo` calls now require explicit bypass, creating audit trail.
- Wrapper tools' existing safety machinery (ADR-242 backup, recovery JSON)
  remains intact; we only add the documentation requirement on top.

### Negative

- New friction for legitimate quick sanitizations — operator must author an ADR
  before running `--execute`. Mitigation: provide a template ADR for
  history rewrites (`docs/adrs/templates/history-rewrite.template.md`).
- The startup banner becomes noise if orphans persist; operators may dismiss it
  habitually. Mitigation: make the warning louder and include orphan count in
  the daily metrics dashboard.
- Adding filter-repo to DESTRUCTIVE_PATTERN may surprise external operators
  who run filter-repo for normal repo maintenance. Mitigation: documentation
  in `rules/license-policy.md` and `docs/runbooks/` explaining the wrapper.

### Risks not mitigated

- Operator with write access to `manifests/history-rewrite-ledger.yaml` could
  forge entries. Defense: append-only contract test + commit signing.
- Operator could delete `.cognitive-os/recovery/*.bundle` files to remove
  evidence. Defense: out of scope for this ADR; covered by general backup
  retention policy (TODO: future ADR).
- The ADR itself can be modified after-the-fact. Defense: ADR `status` field
  + `superseded_by` chain + git history of the ADR file itself.

## Implementation plan

1. Create `manifests/history-rewrite-ledger.yaml` with the 2026-05-11
   sanitization as the seed entry (`adr_ref: ADR-268`).
2. Create `lib/history_rewrite_ledger.py` — Python module with `append_entry`,
   `list_entries`, `find_orphan_bundles`, `find_orphan_entries` functions.
3. Create `scripts/cos-history-rewrite-audit` CLI per spec.
4. Create `hooks/history-rewrite-documented.sh` SessionStart hook + registration.
5. Modify `lib/history_sanitization.py` to require `--adr-ref` and call
   `append_entry` on success.
6. Modify `scripts/cos-filter-repo-wrap.sh` to require `--adr-ref` (added as
   a top-level argparse arg) and call `append_entry`.
7. Modify `hooks/destructive-git-blocker.sh` DESTRUCTIVE_PATTERN to include
   `filter-repo` (with bypass to wrapper) — separate ADR follow-up if too
   invasive.
8. Create `docs/adrs/templates/history-rewrite.template.md` for future
   operators.
9. Tests in `tests/contracts/`, `tests/integration/`, `tests/red_team/portability/`.


## Verification

```bash
# Verify ADR-269 implementation files exist
grep -rn 'ADR-269' docs/ scripts/ tests/ | head -20
```

## Operational Guide

### What changes for the operator

Before this ADR: running `git filter-repo`, `cos-history-sanitization --execute`, or `cos-filter-repo-wrap.sh` required no ADR reference and produced no ledger entry. Orphan recovery bundles under `.cognitive-os/recovery/` accumulated silently with no machine-visible link to a rationale.

After this ADR:

| Surface | Before | After |
|---|---|---|
| `cos-history-sanitization --execute` | runs without any documentation requirement | requires `--adr-ref ADR-NNN` (fails at invocation if absent) |
| `cos-filter-repo-wrap.sh` | runs without documentation | requires `--adr-ref ADR-NNN`; auto-writes ledger entry on success |
| Direct `git filter-repo` | not intercepted | classified as DESTRUCTIVE; must use wrapper or set `COS_ALLOW_DESTRUCTIVE_GIT=1` (audit-logged) |
| `manifests/history-rewrite-ledger.yaml` | did not exist | append-only registry of every rewrite; queried by `cos-history-rewrite-audit` |
| Session startup | silent | `hooks/history-rewrite-documented.sh` emits a visible WARNING if any bundle lacks a ledger entry |

The four primitives work together: the pre-gate (Primitive 4) requires the ADR at execution time; the ledger (Primitive 1) stores the evidence; the CLI (Primitive 3) lets the operator inspect or remediate; the startup hook (Primitive 2) surfaces any orphan that slipped through.

### Daily operational pattern

**Before a history rewrite:**

1. Author or confirm an Accepted ADR documenting why the rewrite is needed. A template exists at `docs/adrs/templates/history-rewrite.template.md`.
2. Run the governed wrapper:
   ```bash
   scripts/cos-history-sanitization --execute --adr-ref ADR-NNN [other flags]
   # or
   bash scripts/cos-filter-repo-wrap.sh --adr-ref ADR-NNN --rules /path/to/rules.txt
   ```
   The wrapper auto-writes a ledger entry on success. No additional step needed.

**To inspect the audit trail at any time:**
```bash
scripts/cos-history-rewrite-audit --list
# Full table: timestamp, operator, ADR ref, bundle path, SHA before/after

scripts/cos-history-rewrite-audit --orphans
# Bundles with no ledger entry, ledger entries with missing bundles,
# entries pointing at non-existent ADRs
```

**If a session-start warning fires** (orphan bundle detected):
```bash
scripts/cos-history-rewrite-audit --register .cognitive-os/recovery/<bundle> \
  --adr ADR-NNN --reason "retroactive registration: <why>"
```

### Reading guide for cold readers

If you encounter this ADR without conversation context:

1. Read `manifests/history-rewrite-ledger.yaml` for every rewrite that has been performed against this repository and its rationale.
2. Read `scripts/cos-history-rewrite-audit --list` output for the current operational state (bundles, ADR cross-references, orphans).
3. Read ADR-268 (the 2026-05-11 defensive sanitization) as the seed event and concrete example of what this ledger records.
4. Read ADR-242 for the wrapper mechanics (remote preservation, idempotency guard, recovery artifact) — ADR-269 adds the documentation requirement on top of those safety primitives.
5. The session-start hook (`hooks/history-rewrite-documented.sh`) is the daily signal: if it fires, there is an orphan bundle. Resolve via `--register` before proceeding with other work.

## Alternatives rejected

- **Advisory documentation only** (status quo). Rejected — does not scale to
  multi-agent workflows and is what failed 2026-05-11 until operator caught it.
- **Block all history rewrites unconditionally**. Rejected — too punitive for
  legitimate use (e.g., sensitive data leak emergencies); the operator may not
  have time to author an ADR mid-incident.
- **Require IP counsel sign-off** instead of an ADR. Rejected — counsel review
  is appropriate at release boundaries; commit-time gating must be operator-runnable.
- **Cryptographic signing of the ledger** (e.g., Sigstore). Parking — overkill
  for current scale; revisit if luum becomes public release.

## Open questions (UNSURE)

1. Should the ledger be moved to `.cognitive-os/runtime/` (operator-private)
   or kept in `manifests/` (committed)? Current decision: `manifests/` because
   the audit trail value depends on git-tracked history.
2. Retention policy for recovery bundles: how long do we keep them?
   Current decision: indefinite until next ADR addresses storage policy.
3. The interaction with ADR-246 release-transaction-freeze: if a release
   freeze is active and an emergency rewrite is needed, does this ADR's
   `--adr-ref` requirement compose correctly? Hypothesis yes (both are
   pre-commit gates), but requires test.

## References

- ADR-218 — History sanitization toolchain
- ADR-242 — git-filter-repo wrapper preserves remote
- ADR-243 — Post-rewrite push-collision exception
- ADR-246 — Release transaction freeze for destructive ops
- ADR-268 — Defensive history sanitization 2026-05-11 (the seed event for this ADR)
- Postmortem 2026-05-08: silent agent branch switch
- Audit 2026-05-09: git-history debug script audit (remote+upstream preservation)
- Run record 2026-05-08T06:12:08Z history-sanitization

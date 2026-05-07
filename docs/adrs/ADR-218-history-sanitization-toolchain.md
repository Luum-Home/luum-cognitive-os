# ADR-218 — History Sanitization Toolchain

## Status
Accepted


<!-- SCOPE: OS -->

**Status**: Accepted — slice 1 dry-run substrate active
**Date**: 2026-05-06
**Related**: ADR-202, ADR-203, ADR-211, ADR-215, ADR-055b
**Source**: Operator question — *"cómo depuramos lo que está en git sobre datos sensibles y estos cambios de licencias sin crear un repo nuevo?"*

---

## Context

The 2026-05-06 secrets audit
(`.cognitive-os/strategy/audit/secrets-and-leaks-2026-05-06.md`) confirmed
that the working tree is clean of hard secrets, but git **history** still
contains:

- Operator personal email (`<operator-email>`) in old commits
  (HEAD versions of the 9 preserve-manifest files were fixed via `sed`, but
  the old blobs still carry the email).
- Operator absolute paths (`${HOME_PREFIX}-${PROJECT_PATH}-${REPO}/...`)
  in approximately 50 history diffs.
- License-transition diffs (Apache 2.0 → FSL-1.1-MIT) that are honest history
  and **must not** be sanitized.

The decision recorded in
`.cognitive-os/strategy/04-license-repo-and-corrections-log.md` was Vía 4
(preserve history) — the operator does not want to discard the dev journey.
That choice creates a tension: how to scrub the genuinely sensitive content
from old blobs **without** a fresh repo, **without** losing the license-
transition story, and **without** ad-hoc `git filter-branch` invocations
that are easy to misuse.

ADR-055b (Destructive Git Block) already gates raw destructive ops behind
explicit operator authorization. This ADR layers a manifest-backed primitive
on top so history sanitization becomes auditable, repeatable, and bounded.

## Decision

Adopt a manifest-backed history-sanitization primitive, mirroring ADR-212/215
shape but with stricter destructive-op gating:

1. **Canonical CLI**: `cos history sanitize [--dry-run|--execute] [--json]`.
2. **Default mode is `--dry-run`** — the audit runs the planned rewrite
   in-memory and reports the diff, without mutating refs.
3. **`--execute` requires explicit operator confirmation** AND must coexist
   with `COS_ALLOW_DESTRUCTIVE_GIT=1` (per ADR-055b). The CLI re-asks even
   when the env var is set.
4. **Backed by `git-filter-repo`** (not `git filter-branch`, which is
   deprecated and footgun-rich).
5. **Manifest declaration**: `manifests/history-sanitization.yaml`.
6. **Schema-versioned report**: `history-sanitization-report/v1`.
7. **Implementation**: `lib/history_sanitization.py` +
   `scripts/cos-history-sanitization` Python entrypoint.

## What the manifest declares

```yaml
schema_version: history-sanitization/v1
status: active
owner: platform-safety

# Each rule: substitution applied to all commit content via git-filter-repo --replace-text
text_replacements:
  - pattern: "$COS_HISTORY_SANITIZE_OPERATOR_EMAIL"
    replacement: "2144218+MatiasNAmendola@users.noreply.github.com"
    rationale: "operator personal email — replaced in HEAD via sed; history sanitization replaces in all blobs"
  - pattern: "${HOME_PREFIX}-${PROJECT_PATH}-${REPO}"
    replacement: "<repo>"
    rationale: "operator absolute path — appears in ~50 history diffs"
  - pattern: "${HOME_PREFIX}"
    replacement: "<home>"
    rationale: "operator home prefix — broader than repo path"

# Path-level removal (if any path needs to be expunged from all commits)
path_removals: []

# What we MUST NOT sanitize — preserve as honest history
preserve:
  - reason: "License transition Apache 2.0 → FSL-1.1-MIT is honest history"
    pattern: "Apache License|Apache 2\\.0|Apache-2\\.0"
    note: "Transition from internal placeholder to FSL is a defendable narrative; do not erase"
  - reason: "Test fixture placeholders (intentionally identifiable)"
    pattern: "[REDACTED]|deadbeef"
    note: "These exist so secret scanners have a positive control"

# Pre-sanitization safety
require_backup_first: true
backup_destination: ".cognitive-os/recovery/pre-history-sanitization-{timestamp}.git"
```

## What the CLI does

```
cos history sanitize --dry-run
  -> validates manifest
  -> creates `git clone --mirror` backup at backup_destination
  -> runs git-filter-repo --dry-run with the replacement rules in a tmp dir
  -> emits report under .cognitive-os/reports/history-sanitization/{timestamp}.json:
       - rules_applied: [...]
       - blobs_rewritten: N
       - commits_rewritten: M
       - SHAs_changed: [...] (count, not full list — that's huge)
       - preserve_pattern_hits: N (sanity: should match expected count)

cos history sanitize --execute
  -> requires COS_ALLOW_DESTRUCTIVE_GIT=1 (ADR-055b)
  -> requires explicit y/n prompt confirmation (ALWAYS, even with env var)
  -> creates the backup mirror
  -> runs git-filter-repo for real
  -> emits the same report + writes a tombstone commit on a new branch
     `history-sanitization-{timestamp}` pointing at the post-rewrite HEAD
  -> tells operator: "force-push required to publish; do this BEFORE first
     public push, never after"
```

## Hard rules

- **`--dry-run` is the only mode safe in CI/automation**.
- **`--execute` requires operator-in-the-loop**, no headless service-mode
  invocation. ADR-211 service-mode readiness explicitly **does not** include
  history sanitization in its automation lane.
- **Run only ONCE pre-public-launch**. Subsequent leaks are addressed by
  rotating the leaked credential and adding a manifest entry; never by a
  second history rewrite (collaborators with clones get permanent drift
  every rewrite).
- **Backup-or-refuse**: if backup destination cannot be written, the CLI
  refuses to execute. This is non-negotiable.
- **Preserve patterns are enforced**: if a manifest replacement would also
  match a preserve pattern, the CLI refuses to execute and asks operator
  to refine.

## Implementation status — 2026-05-06

Active first slice:

- `manifests/history-sanitization.yaml` declares env-backed replacements for operator email<home>/<repo> path, sensitive-history regexes, preserve patterns, backup policy, and destructive execution policy.
- `lib/history_sanitization.py` emits `history-sanitization-report/v1`, counts historical candidate hits without materializing full blob contents, detects replacement-vs-preserve conflicts, and blocks execute mode unless `COS_ALLOW_DESTRUCTIVE_GIT=1`.
- `scripts/cos-history-sanitization` plus `scripts/cos history sanitize` expose the dry-run CLI.
- `tests/unit/test_history_sanitization.py` and `tests/behavior/test_history_sanitization_cli.py` cover manifest loading, unresolved env warnings, non-mutating dry-run, destructive-env refusal, preserve conflict blocking, and route smoke.

Not yet active: live `git-filter-repo` rewrite, mirror-backup creation, interactive confirmation prompt, installer wiring, and operator runbook. This is intentional: the automated part can now detect and plan history scrubbing, but mutating public history remains operator-approved only.

## Consequences

### Positive

- History-rewrite operations become manifest-driven and auditable.
- Preserve-list explicitly protects honest history (license transition,
  test fixtures) from accidental scrubbing.
- Backup-first invariant removes "I lost my git history" failure mode.
- ADR-055b gating prevents accidental invocation.
- Schema-versioned report enables post-publish forensics ("what did we
  rewrite, when?").

### Negative / trade-offs

- All SHAs change; refs/tags/signed-commits invalidate.
  - Mitigation: only run pre-first-public-push, when no external clones exist.
- Operator must execute the force-push manually after sanitization.
- Future leaks cannot use the same manifest a second time without escalating
  process; intentional friction.
- `git-filter-repo` requires installation (Python, brew, or pip); add to
  `cos-deps-install.sh`.

## Alternatives rejected

- **`git filter-branch`**: rejected. Deprecated by Git project itself.
  Slow on large repos, easy to misuse, leaves orphan refs.
- **BFG Repo-Cleaner**: considered but rejected as primary. Strong for
  large-blob and password expungement, but config language is less
  expressive than git-filter-repo's `--replace-text`. Manifest interop is
  weaker. Acceptable as forensic fallback only.
- **Squash to single commit**: rejected. Loses all the dev journey
  provenance the operator explicitly wanted to preserve in Vía 4.
- **Two-repo split** (Vía 1 from strategy/04): rejected per the operator's
  decision in this session ("no quiero crear un repo nuevo").
- **Don't sanitize at all, accept history leaks**: rejected. Operator email
  and personal paths in committed blobs damage trust and surface-of-attack;
  scrubbing them costs nothing in narrative.
- **Run unsanitized then rotate later**: rejected. Once a clone exists in
  the wild with the email/path baked in, a future rewrite cannot retroactively
  unleak.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_history_sanitization.py tests/behavior/test_history_sanitization_cli.py -q
scripts/cos history sanitize --dry-run --json
# Execute path tested only in fixture repos, never live:
scripts/cos history sanitize --execute --json   # interactive; CI uses fixture mode
```

The tests must prove:

- `--dry-run` does not modify the live repo.
- `--execute` without `COS_ALLOW_DESTRUCTIVE_GIT=1` is refused.
- A manifest replacement that would also hit a preserve pattern is refused
  with a clear error pointing at the offending preserve rule.
- Backup is created before any rewrite and verified readable.
- Post-rewrite, the report's `commits_rewritten` count matches the
  filter-repo execution log.
- Test-fixture repos can be sanitized round-trip and restored from backup.

## Implementation slices

1. `manifests/history-sanitization.yaml` skeleton (operator email, operator
   path, preserve patterns).
2. `lib/history_sanitization.py` (manifest validator + git-filter-repo
   wrapper + preserve-pattern check).
3. `scripts/install-git-filter-repo.sh` (brew → pip fallback) +
   integration with `cos-deps-install.sh`.
4. `scripts/cos-history-sanitization` + `cos history` shell dispatch.
5. Unit tests (manifest validation, preserve-pattern guard, dry-run report
   shape).
6. Behavior tests (round-trip on a fixture repo, refusal paths, backup
   verification).
7. Operator runbook in `docs/runbooks/history-sanitization.md`.

## Pre-launch posture

The expected single execution: shortly before the first public push of
`luum-cognitive-os` (or whatever the public repo name resolves to). Operator
runs `cos history sanitize --dry-run`, reviews the diff and the SHAs that
will rotate, then `cos history sanitize --execute` once. Force-push to the
new public remote. Never repeat after public availability.

## Open questions

- Should `cos history sanitize` automatically generate the GitHub redirect
  notice ("we rewrote history pre-public; old SHAs invalid") for the launch
  blog post? Could be a `--launch-notice` flag emitting markdown.
- Should the manifest support `commit_metadata_replacements` (committer
  name/email rewrites) in addition to text replacements? Initial answer:
  defer; out of scope until evidence of need.
- Integration with `git-crypt` or transparent-encryption alternatives:
  defer; this ADR addresses pre-public scrubbing, not ongoing private
  collaboration.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

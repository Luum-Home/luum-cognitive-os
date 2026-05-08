# Runbook: ADR-218 history sanitization

> Status: operator-driven, destructive, irreversible without backup mirror.
> Reference policy: [ADR-218](../adrs/ADR-218-history-sanitization-toolchain.md).
> Reference manifest: [`manifests/history-sanitization.yaml`](../../manifests/history-sanitization.yaml).
> Smoke script: [`scripts/cos-history-sanitization-smoke.sh`](../../scripts/cos-history-sanitization-smoke.sh).

This runbook is the canonical post-execute procedure for the ADR-218
toolchain. It replaces ad-hoc operator notes from the M4 audit and is the
artifact pre-public-readiness item M4 consumes.

The runbook intentionally does NOT contain real consumer codenames, email
addresses, or absolute machine paths. Every token is referenced by env-var
name (e.g. `COS_HISTORY_SANITIZE_CONSUMER_CODENAME_A`) so the runbook itself
is publication-safe.

---

## 1. Pre-execute checklist

Before running `--execute`, the operator MUST confirm every item below.
A single missed env var means the rewrite will produce a tombstone branch
that STILL contains the raw codename — the redaction has not actually
landed. The smoke script in §3 is the only mechanical defense against this
class of failure.

### 1.1 Environment variables

Set every applicable env var to the literal string that should be redacted.
Variables that are not relevant to this repo's history can be left unset;
the dry-run will warn for each unresolved rule.

| Env var | Purpose | Replacement (literal) |
| --- | --- | --- |
| `COS_HISTORY_SANITIZE_OPERATOR_EMAIL` | operator personal email | `2144218+MatiasNAmendola@users.noreply.github.com` |
| `COS_HISTORY_SANITIZE_OPERATOR_NAME` | operator personal name in historical metadata | `MatiasNAmendola` |
| `COS_HISTORY_SANITIZE_HOME_PREFIX` | machine home prefix (e.g. `/Users/<name>`) | `<home>` |
| `COS_HISTORY_SANITIZE_REPO_PATH` | absolute repo path | `<repo>` |
| `COS_HISTORY_SANITIZE_CONSUMER_CODENAME_A` | consumer-project codename A | `<consumer-codename-a>` |
| `COS_HISTORY_SANITIZE_CONSUMER_CODENAME_B` | consumer-project codename B | `<consumer-codename-b>` |
| `COS_HISTORY_SANITIZE_CONSUMER_CODENAME_C` | consumer-project codename C | `<consumer-codename-c>` |
| `COS_HISTORY_SANITIZE_CONSUMER_SERVICE` | consumer service slot 1 | `<consumer-service>` |
| `COS_HISTORY_SANITIZE_CONSUMER_SERVICE_2` | consumer service slot 2 | `<consumer-service-2>` |
| `COS_HISTORY_SANITIZE_CONSUMER_SERVICE_3` | consumer service slot 3 | `<consumer-service-3>` |
| `COS_HISTORY_SANITIZE_CONSUMER_SERVICE_4` | consumer service slot 4 | `<consumer-service-4>` |
| `COS_HISTORY_SANITIZE_CONSUMER_SERVICE_5` | consumer service slot 5 | `<consumer-service-5>` |

The authoritative list is the `value_env:` entries under `rules:` in
`manifests/history-sanitization.yaml`. The smoke script reads that file
directly so it stays in sync with the manifest automatically.

### 1.2 Where to confirm them

Source from a private operator vault, NOT from shell history. Recommended:

```bash
# In a private, gitignored file outside the repo:
set -a
source ~/.cos-private/history-sanitize.env
set +a

# Spot-check the loaded values without echoing them to history:
env | grep -c '^COS_HISTORY_SANITIZE_'
# Expect 11 (or however many are populated for this repo).
```

### 1.3 Destructive-op authorization

```bash
export COS_ALLOW_DESTRUCTIVE_GIT=1
```

### 1.4 Safe dry-run

```bash
python3 scripts/cos-history-sanitization --dry-run
```

Expected: `status: warn` (or `pass` if every env var is set). For each
unresolved rule the dry-run prints a `replacement-value-unresolved` finding
identifying which env var is missing. Do NOT proceed to `--execute` while
any required env var is unresolved.

### 1.5 Working tree clean

```bash
git status --porcelain     # MUST be empty
git rev-parse HEAD         # record this SHA in your operator notebook
```

### 1.6 git-filter-repo installed

```bash
which git-filter-repo      # MUST resolve
# If missing:
bash scripts/install-git-filter-repo.sh
```

---

## 2. Execute step

### 2.1 Command

```bash
python3 scripts/cos-history-sanitization --execute
```

The CLI prompts for the literal string `REWRITE` before touching git. Any
other input aborts cleanly. Use `--yes` ONLY in CI; operator-driven runs
must type the confirmation.

### 2.2 Expected runtime

For a ~5k-commit repository the rewrite typically takes 30–120 seconds
(dominated by `git filter-repo --replace-text`). The backup-mirror clone
adds another 5–30 seconds depending on disk speed.

### 2.3 Expected outputs

On success the CLI prints:

```
history sanitization execute: ok
  report:           <repo>/.cognitive-os/reports/history-sanitization/<ts>.json
  backup mirror:    ~/.cognitive-os/recovery/pre-history-sanitization-<ts>.git
  tombstone branch: history-sanitization-<ts>
  pre HEAD  → <8-hex> (N commits)
  post HEAD → <8-hex> (N commits)
  ✓ <rule-id>: 0 remaining hits
  …
```

Non-zero remaining hits flip the status to `completed-with-warnings` and
exit 1. The smoke script in §3 is still the source of truth for whether
the rewrite is safe to publish — it scans the full ref graph, not just the
replacement-source values.

---

## 3. Post-execute smoke

The smoke script is the gate between a completed rewrite and force-push.
It MUST pass with `0 leaked tokens` before any `git push --force` to a
public remote.

### 3.1 Invocation

```bash
# Same env vars that were set for --execute.
bash scripts/cos-history-sanitization-smoke.sh
```

Optional flags:

- `--repo PATH`   point at a different repository (default `$PWD`)
- `--manifest PATH` point at a different manifest
- `--json`        emit JSON instead of the human table
- `--quiet`       suppress per-token rows; print summary only
- `--refs-only`   skip `git log --all -p` and scan only ref tips
- `--help`        print usage

### 3.2 Expected output (PASS)

```
TOKEN (env var)                                          HITS   VERDICT
-------------------------------------------------------  ----   -------
COS_HISTORY_SANITIZE_OPERATOR_EMAIL                         0   PASS
COS_HISTORY_SANITIZE_HOME_PREFIX                            0   PASS
COS_HISTORY_SANITIZE_REPO_PATH                              0   PASS
COS_HISTORY_SANITIZE_CONSUMER_CODENAME_A                    0   PASS
…
[smoke] tombstone branch:    history-sanitization-<ts>
[smoke] latest report:       .cognitive-os/reports/history-sanitization/<ts>.json
[smoke] sha inventory:       docs/history/pre-sanitization-sha-inventory-<date>.txt
[smoke] tokens resolved:     11 of 11 env vars
[smoke] PASS — 0 leaked tokens across HEAD + tombstone + all refs
```

Exit code: 0.

### 3.3 What FAIL means

```
[smoke] FAIL — at least one configured token still appears in history
[smoke] DO NOT force-push. Restore from backup mirror and investigate.
```

Exit code: 1. A FAIL means at least one of:

1. The env var was set for the smoke script but was UNSET when `--execute`
   ran. The rewrite literally never replaced that token. Re-run §2 with
   the missing env var, then re-run §3.
2. The token appears inside a `preserve:` pattern (e.g. license-transition
   text). Inspect `manifests/history-sanitization.yaml` and the smoke
   output; refine the manifest to disambiguate before re-running.
3. The token appears in a ref the rewrite did not reach (e.g. a stash, a
   `refs/replace/*` ref, a leftover backup branch). Inspect
   `git for-each-ref` output and either delete the stale ref or re-run
   the rewrite with the ref included.

### 3.4 Skip-with-warning

If NO sanitization env vars are set, the script prints a warning,
enumerates every `value_env` it found in the manifest, and exits 0. This
is intended for runbook drills where the operator wants to exercise the
script without running the rewrite. It is NOT a green light to publish.

---

## 4. Forensic preservation

The tombstone branch (`history-sanitization-<ts>`) is INTENTIONALLY kept.
It points at the post-rewrite HEAD and serves as a stable, named anchor
for auditors verifying that:

1. The post-rewrite history is what was actually published.
2. No replacement rule introduced a new leak (every configured token has
   0 hits on the tombstone too — the smoke script asserts this).
3. The pre-rewrite SHA inventory in
   `docs/history/pre-sanitization-sha-inventory-*.txt` is preserved as a
   separate audit trail (not rewritten, not redacted) so a future auditor
   can correlate pre/post commit counts and rule application.

The `boundary_tag_recommended` field in the post-execute report names the
git tag that auditors should look for at the boundary
(`v0.27.1-pre-history-rewrite` by default). The operator is responsible
for re-applying tags after the rewrite (see §5).

To verify redaction integrity from an auditor's seat:

```bash
git fetch origin '+refs/heads/history-sanitization-*:refs/remotes/origin/history-sanitization-*'
bash scripts/cos-history-sanitization-smoke.sh
# Expect PASS. Any FAIL is a publishable-history bug — file an incident.
```

---

## 5. Force-push procedure

Force-push is the publication step. Do it ONLY after §3 reports PASS.

1. **Re-tag versions.** The pre-rewrite tags (e.g. `v0.27.0`, `v0.27.1`)
   point at the OLD SHAs and now dangle. Recreate them on the equivalent
   post-rewrite SHAs:

   ```bash
   git tag -f v0.27.0 <new-sha-equivalent-of-v0.27.0>
   git tag -f v0.27.1 <new-sha-equivalent-of-v0.27.1>
   git tag v0.27.1-pre-history-rewrite <post-rewrite HEAD>
   ```

2. **Push the tombstone branch first.** This makes the redaction-integrity
   anchor available to consumers before any branch tip moves.

   ```bash
   git push origin "history-sanitization-<ts>"
   ```

3. **Force-push main.**

   ```bash
   git push --force-with-lease origin main
   ```

4. **Push tags.**

   ```bash
   git push --force origin v0.27.0 v0.27.1 v0.27.1-pre-history-rewrite
   ```

5. **Communicate to consumers.** Send the disclosure note (template in the
   ADR-218 §"Disclosure & comms" appendix) to every known fork/clone with:
   - the new HEAD SHA
   - the tombstone branch name
   - the pre-rewrite SHA inventory location
   - the instruction to re-clone (rebasing local branches across the
     rewrite is unsafe).

---

## 6. Recovery

If §3 (smoke) FAILs, OR §5 fails part-way through, the rollback path is
the backup mirror. The operator is expected to restore in this order:

### 6.1 Restore from backup mirror

```bash
BACKUP=~/.cognitive-os/recovery/pre-history-sanitization-<ts>.git
test -d "${BACKUP}" || { echo "MISSING BACKUP — escalate to platform-safety"; exit 99; }

# Push the backup mirror back over the rewritten repo (LOCAL only):
git fetch "${BACKUP}" '+refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*'
```

### 6.2 If origin was already force-pushed

`origin/main` now contains the (possibly leaky) rewritten history.
Restore origin from the backup mirror with the SAME `--force-with-lease`
mechanic, then re-run the rewrite from §2 with the corrected env vars,
then §3, then §5.

```bash
# From a fresh clone of the backup mirror:
git clone "${BACKUP}" recovery-clone
cd recovery-clone
git push --force --mirror origin
```

### 6.3 Regenerate forensic artifacts

After any recovery, regenerate the SHA inventory and the post-execute
report so auditors have a coherent timeline:

```bash
git rev-list --all --pretty=oneline > docs/history/pre-sanitization-sha-inventory-$(date +%Y-%m-%d).txt
python3 scripts/cos-history-sanitization --dry-run --json > .cognitive-os/reports/history-sanitization/recovery-$(date -u +%Y%m%dT%H%M%SZ).json
```

### 6.4 Escalation

If the backup mirror is missing OR fails `git fsck`, stop. Do not
attempt recovery from origin. Escalate to `platform-safety` with the
operator notebook entry from §1.5 (the pre-rewrite HEAD SHA) and the
post-execute report path. The pre-rewrite HEAD SHA is the only durable
correlation key once the mirror is gone.

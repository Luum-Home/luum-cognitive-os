---
type: methodology-synthesis
source: docs/05-Methodology/runbooks/cos-history-sanitization.md
provenance: "Canonical, publication-safe operator procedure for the ADR-218 history-sanitization toolchain, covering pre-execute checklist, execution, post-execute smoke verification, forensic preservation, force-push, and recovery."
---

## What it is

The canonical post-execute runbook for the ADR-218 git history sanitization toolchain — an operator-driven, destructive, irreversible-without-backup procedure for redacting sensitive tokens (operator PII, consumer codenames/services) from git history before publication. It replaces ad-hoc M4-audit operator notes and is the artifact that the pre-public-readiness M4 checklist item consumes. The runbook deliberately contains no real codenames/emails/paths — every sensitive value is referenced only by env-var name, making the doc itself publication-safe.

## Key mechanics

- **Pre-execute checklist (§1)**: operator must set every applicable `COS_HISTORY_SANITIZE_*` env var (operator email/name, home prefix, repo path, up to 3 consumer codenames, up to 5 consumer service slots) to the literal string to be redacted; the authoritative list lives in `manifests/history-sanitization.yaml`'s `value_env:` entries, and the smoke script reads that manifest directly so it can't drift out of sync.
- **Metadata boundary**: ADR-218 is blob-content-only by default — commit messages and author/committer identity are preserved unless the operator explicitly opts in via `COS_HISTORY_SANITIZE_METADATA=1` and/or `COS_HISTORY_SANITIZE_COMMIT_MESSAGES=1`. The doc is emphatic these should NOT be set for ordinary content scrubbing; collaborator privacy should go through a scoped, consented noreply-address migration instead of a broad sweep.
- **Credential sourcing discipline**: env vars should be sourced from a private, gitignored operator vault file (`~/.cos-private/history-sanitize.env`), never typed into shell history directly; a spot-check counts populated vars without echoing values.
- **Safety gates before execute**: `COS_ALLOW_DESTRUCTIVE_GIT=1` authorization, a mandatory `--dry-run` that must report no unresolved replacement values, a clean working tree, recorded pre-rewrite HEAD SHA, and `git-filter-repo` installed.
- **Execute (§2)**: `--execute` prompts for the literal string `REWRITE` before touching git (bypassed only by `--yes` in CI); for a ~5k-commit repo the rewrite takes roughly 30-120s plus 5-30s for the backup-mirror clone. Non-zero remaining hits flip status to `completed-with-warnings` and exit 1.
- **Post-execute smoke (§3) is the hard gate before any force-push**: `scripts/cos-history-sanitization-smoke.sh` must report `0 leaked tokens` — it scans the full ref graph (HEAD + tombstone + all refs), not just the replacement-source values, making it stricter than the dry-run's coverage. Three documented FAIL causes: an env var set for smoke but unset at execute time, a token living inside a `preserve:` manifest pattern, or a token surviving in an unreached ref (stash, `refs/replace/*`, leftover backup branch).
- **Forensic preservation (§4)**: the post-rewrite tombstone branch (`history-sanitization-<ts>`) is intentionally retained as an auditor anchor, alongside an unrewritten, unredacted pre-rewrite SHA inventory file — together they let a future auditor correlate pre/post commit counts and confirm no replacement rule introduced a new leak.
- **Force-push procedure (§5)**: strict order — re-tag versions onto their post-rewrite SHA equivalents, push the tombstone branch FIRST (so the integrity anchor is available before any branch tip moves), force-push main with `--force-with-lease`, push tags, then send a disclosure notice to every known fork/clone instructing them to re-clone (rebasing across the rewrite is called unsafe).
- **Recovery (§6)**: restore from the backup mirror (created automatically during execute, stored at `~/.cognitive-os/recovery/pre-history-sanitization-<ts>.git`); if origin was already force-pushed, restore origin from the mirror with the same `--force-with-lease` mechanic then re-run execute→smoke→force-push with corrected env vars; regenerate forensic artifacts after any recovery. If the backup mirror is missing or fails `git fsck`, the doc says to STOP and escalate to `platform-safety` rather than attempt recovery from origin.

## Relations & where used

References ADR-218 (policy), `manifests/history-sanitization.yaml` (rule/token manifest, single source of truth for both the sanitizer and the smoke script), and `scripts/cos-history-sanitization-smoke.sh`. Cross-references the pre-rewrite SHA inventory stored under `docs/01-Build-Log/history/`.

## Status / caveats

FLAG: this doc largely duplicates (and significantly extends) the shorter `docs/05-Methodology/runbooks/history-sanitization.md` in the same directory — both describe the ADR-218 sanitization workflow, but this one is the far more detailed, current, "canonical" version (explicitly self-described as replacing ad-hoc notes) while the sibling doc reads as an older/simpler pass with a slightly different command set (`--json` flag, `cos-filter-repo-wrap.sh`) not mentioned here. Readers should treat this file as authoritative and treat the sibling as possibly stale — see that doc's own Status/caveats note. Otherwise internally consistent; no dated point-in-time snapshot beyond the illustrative example dates/versions in command output samples.

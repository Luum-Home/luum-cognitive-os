# Consumer/project residue audit — 2026-05-08

## Scope

Audit target: tracked `HEAD` plus reachable git history (`git rev-list --all`) for configured or publicly suspicious consumer/project residues:

- consumer codenames and real service names,
- sibling project paths,
- private emails in content,
- internal URLs.

Out of scope: commit author/committer metadata. This audit did not rewrite history.

## Acceptance criteria

1. Current worktree edits are limited to this report plus one clear tracked content-only redaction found during the audit.
2. No commit author metadata is inspected or modified.
3. Findings do not commit private raw token values; consumer residue samples use hashes/placeholders.
4. Recommended redaction inputs are expressed as environment variables, not literal private values.

## Method

The audit used three layers:

1. Manifest/config review: `manifests/history-sanitization.yaml` and `docs/05-Methodology/runbooks/cos-history-sanitization.md`.
2. Exact tracked-`HEAD` scans with `git grep` for public regex classes and known suspicious consumer/service token classes.
3. Reachable-history scans using `git rev-list --all`, `git cat-file --batch-check`, and `git cat-file --batch` over small reachable blobs, plus `git log --all -G` for macOS project-path diffs.

The current shell had zero `COS_HISTORY_SANITIZE_*` values set, so the manifest-backed exact-token smoke could not independently prove the private token set; it can only be run by an operator who sources the private env file.

## Findings

### F1 — Consumer service-name residue in tracked content

Status: partially fixed in the working tree; still present in committed `HEAD` and history until committed/rewrite-scanned.

- A known suspicious consumer service-name token class (`token_hash=ef60af13a829`) appeared in tracked `HEAD` in two files.
- One occurrence is in the explicit retained case-study surface: `docs/08-References/business/case-study.md`.
- One occurrence was a generic architecture instruction in `docs/09-Quality/root/stress-test-strategy.md`; this was safe to redact content-only and has been changed to `reference-service` in the working tree.
- After the working-tree redaction, `git grep -I -n -i -F <raw-token> -- .` finds only the retained case-study occurrence.

Recommended action:

- Commit the content-only redaction in `docs/09-Quality/root/stress-test-strategy.md`.
- If public history must be zero-hit outside retained case-study material, run the manifest-backed rewrite with the private value assigned to one of:
  - `COS_HISTORY_SANITIZE_CONSUMER_SERVICE`
  - `COS_HISTORY_SANITIZE_CONSUMER_SERVICE_2`
  - `COS_HISTORY_SANITIZE_CONSUMER_SERVICE_3`
  - `COS_HISTORY_SANITIZE_CONSUMER_SERVICE_4`
  - `COS_HISTORY_SANITIZE_CONSUMER_SERVICE_5`

### F2 — Configured private-token rewrite cannot be re-proved from this shell

Status: blocked on private env values.

- `manifests/history-sanitization.yaml` declares 12 env-backed rewrite rules.
- This shell had 0 of 12 values set.
- `python3 scripts/cos-history-sanitization --dry-run --json` returned `status: warn` with no concrete rules resolved because unset env values are intentionally not committed.

Recommended action:

- Source the private operator env file outside shell history and run:
  - `python3 scripts/cos-history-sanitization --dry-run --json`
  - `bash scripts/cos-history-sanitization-smoke.sh --quiet`
- Required env slots from the manifest/runbook:
  - `COS_HISTORY_SANITIZE_OPERATOR_EMAIL`
  - `COS_HISTORY_SANITIZE_OPERATOR_NAME`
  - `COS_HISTORY_SANITIZE_HOME_PREFIX`
  - `COS_HISTORY_SANITIZE_REPO_PATH`
  - `COS_HISTORY_SANITIZE_CONSUMER_CODENAME_A`
  - `COS_HISTORY_SANITIZE_CONSUMER_CODENAME_B`
  - `COS_HISTORY_SANITIZE_CONSUMER_CODENAME_C`
  - `COS_HISTORY_SANITIZE_CONSUMER_SERVICE`
  - `COS_HISTORY_SANITIZE_CONSUMER_SERVICE_2`
  - `COS_HISTORY_SANITIZE_CONSUMER_SERVICE_3`
  - `COS_HISTORY_SANITIZE_CONSUMER_SERVICE_4`
  - `COS_HISTORY_SANITIZE_CONSUMER_SERVICE_5`

### F3 — macOS sibling/local project paths remain in reachable history

Status: historical residue; no current `HEAD` hit found by focused `git grep`.

- Focused `HEAD` scan for `/Users/.../(Projects|projects)/...` returned no current tracked-file hits.
- `git log --all -G'/Users/.../(Projects|projects)/...' --name-only` shows reachable historical diffs touching old docs/rules/scanner files, including `docs/00-MOCs/entrypoints/HOW-TO-USE-COS.md`, harness-adoption audit docs, legacy `.claude/rules/cos/*`, `docs/09-Quality/testing/README.md`, `lib/confidentiality_scanner.py`, and `rules/confidentiality-protection.md`.

Recommended action:

- For public history, set:
  - `COS_HISTORY_SANITIZE_HOME_PREFIX` to the literal machine home prefix.
  - `COS_HISTORY_SANITIZE_REPO_PATH` to the literal absolute repo/project path.
- Re-run the history smoke after rewrite; do not manually edit commit metadata.

### F4 — email-like content is mostly fixtures/placeholders, not private mail

Status: review-only; no obvious private personal email in current content scan.

- `HEAD` contains email-like strings in CI fixtures, git-config tests, docs placeholders, and disclosure/contact examples.
- Unique examples include test domains (`*.invalid`, `*.test`, local fixtures), organization-style contacts, and upstream/public maintainer addresses.
- The audit did not inspect or modify commit author metadata.

Recommended action:

- Keep `COS_HISTORY_SANITIZE_OPERATOR_EMAIL` configured for any pre-public history smoke because historical blobs may still carry operator email even when current content is clean.
- No content rewrite recommended from the current `HEAD` samples unless legal/product wants organization contact aliases generalized.

### F5 — internal/local URLs are mostly local-service configuration

Status: expected local-development residue; no private production URL found by the public regex scan.

- Current `HEAD` has local URLs (`localhost`, `127.0.0.1`, `0.0.0.0`, `host.docker.internal`) throughout tests, compose files, and local-service docs. These are expected for Cognitive OS local-first architecture.
- A small number of `.local` endpoint defaults appear in local LLM/Ollama configuration examples (`docker-compose.cognitive-os.yml`, `infra/cognee/README.md`, `skills/phoenix-trace-ui/SKILL.md`). They are local-network style examples, not production internal URLs.

Recommended action:

- No immediate rewrite required for local-dev URLs.
- If publishing under a stricter policy, add a separate env-backed rewrite rule for any real non-local internal host discovered by the private operator scan.

## Commands run

```bash
cat .codex/skills/repo-map/SKILL.md
git status --short
find . -path ./.git -prune -o \( -iname '*residue*' -o -iname '*sanit*' -o -iname '*leak*' -o -iname '*audit*' \) -print | sort | head -200
git grep -n -E 'consumer|residue|codename|sibling|private email|internal URL|sanitiz|redact' HEAD -- ':!*.png' ':!*.jpg' ':!*.jpeg' ':!*.gif' | head -200
git show HEAD:scripts/audit-consumer-dependence.sh
git ls-tree -r --name-only HEAD | grep -E '(^manifests/|history|sanitize|secret|consumer|residue|private|legal)' | head -300
python3 scripts/cos-history-sanitization --dry-run --json
python3 /tmp/blob_scan_filtered2.py > /tmp/blob_scan_filtered.json
git grep -I -n -E 'https?://([^/]*\.)?(internal|corp|lan|local|private|intranet)([./:]|$)' HEAD --
git grep -I -n -E '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' HEAD --
git grep -I -n -E '<home>/.../(Projects|projects)/...' HEAD --
git grep -I -n -i -F '<private-consumer-token>' HEAD --
git grep -I -n -i -F '<private-consumer-token>' -- .
git log --all -G'<home>/.../(Projects|projects)/...' --name-only --pretty=format:'commit %h' -- | head -80
```

## Remaining findings

1. Retained case-study consumer-token occurrence remains in `docs/08-References/business/case-study.md` by current policy.
2. Committed `HEAD` and reachable history still contain the redacted `docs/09-Quality/root/stress-test-strategy.md` token until the working-tree change is committed and/or history is rewritten.
3. Reachable history still has macOS project-path diffs unless `COS_HISTORY_SANITIZE_HOME_PREFIX` and `COS_HISTORY_SANITIZE_REPO_PATH` are used in the history rewrite.
4. Exact private configured-token proof remains pending because this shell had no private `COS_HISTORY_SANITIZE_*` values loaded.

TRUST_REPORT: SCORE=78 STATUS=MEDIUM EVIDENCE=5 UNCERTAINTIES=3

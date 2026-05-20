# History Sanitization Runbook

Use this runbook when ADR-218 reports that repository history may contain sensitive material or stale public references.

## Preconditions

- Work from a clean branch and notify collaborators before rewriting shared history.
- Run `scripts/cos-history-sanitization --json` to generate the planned replacement report.
- Install `git-filter-repo` with `scripts/install-git-filter-repo.sh --check` or an operator-approved package manager path.

## Dry run

1. Review `manifests/history-sanitization.yaml`.
2. Run `scripts/cos-history-sanitization --json` and confirm every replacement is redacted, not deleted silently.
3. Use `scripts/cos-filter-repo-wrap.sh --help` to confirm the local toolchain is available.

## Execution

1. Create a backup clone outside the working repository.
2. Execute the generated filter-repo command from the wrapper.
3. Re-run `scripts/cos-history-sanitization --json` and compare the finding count.
4. Force-push only after explicit operator approval and downstream coordination.

## Rollback

Use the backup clone or protected remote ref to restore the previous history. Do not continue if any collaborator has unmerged local work.

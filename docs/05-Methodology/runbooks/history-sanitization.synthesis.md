---
type: methodology-synthesis
source: docs/05-Methodology/runbooks/history-sanitization.md
provenance: "Short operator runbook pointing to the ADR-218 history-sanitization tooling for cases where repository history may contain sensitive material or stale public references."
---

## What it is

A brief runbook (preconditions, dry run, execution, rollback) for invoking the ADR-218 history-sanitization tooling when repository history is found to contain sensitive material or stale public references.

## Key mechanics

- **Preconditions**: work from a clean branch, notify collaborators before rewriting shared history, run `scripts/cos-history-sanitization --json` to generate the planned replacement report, and install `git-filter-repo` via `scripts/install-git-filter-repo.sh --check` or an approved package manager.
- **Dry run**: review `manifests/history-sanitization.yaml`, run `scripts/cos-history-sanitization --json` and confirm every replacement is redacted (not silently deleted), and confirm the toolchain via `scripts/cos-filter-repo-wrap.sh --help`.
- **Execution**: create a backup clone outside the working repo, execute the generated filter-repo command via the wrapper, re-run the sanitization script to compare finding counts, and force-push only after explicit operator approval and downstream coordination.
- **Rollback**: restore from the backup clone or a protected remote ref; do not continue if any collaborator has unmerged local work.

## Relations & where used

References ADR-218, `manifests/history-sanitization.yaml`, `scripts/cos-history-sanitization`, `scripts/install-git-filter-repo.sh`, and `scripts/cos-filter-repo-wrap.sh`.

## Status / caveats

FLAG: this doc covers the same ADR-218 workflow as the much more detailed `docs/05-Methodology/runbooks/cos-history-sanitization.md` in the same directory, but is shorter, references a `--json`-flag invocation style and `cos-filter-repo-wrap.sh` wrapper not mentioned in the other doc, and omits the pre-execute env-var checklist, post-execute smoke gate, forensic tombstone-branch preservation, and detailed force-push/recovery procedures that the other doc treats as mandatory. This looks like an earlier or simplified pass that was not fully reconciled with the canonical runbook — readers should prefer `cos-history-sanitization.md` and treat this file's command set (`--json`, `cos-filter-repo-wrap.sh`) as possibly superseded rather than authoritative. Not fixed here per instructions to preserve source fidelity.

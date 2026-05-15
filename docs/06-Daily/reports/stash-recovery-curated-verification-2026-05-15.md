# Curated Stash Recovery Verification — 2026-05-15

## Verdict

The raw recovery archive was verified, classified, and then removed from `HEAD`. No local stash entries remain to drop. The branch now keeps the useful committed work plus this small audit record, not the large raw snapshot archive.

## Extraction Verification

Verified from historical commit `676f7f96` (`chore(recovery): archive all stash file versions`):

```text
git show 676f7f96:docs/06-Daily/reports/stash-recovery-2026-05-15-full.tar.gz > /tmp/cos-stash-recovery-verify/stash-recovery-2026-05-15-full.tar.gz
sha256sum /tmp/cos-stash-recovery-verify/stash-recovery-2026-05-15-full.tar.gz
tar -tzf /tmp/cos-stash-recovery-verify/stash-recovery-2026-05-15-full.tar.gz
tar -xzf /tmp/cos-stash-recovery-verify/stash-recovery-2026-05-15-full.tar.gz -C /tmp/cos-stash-recovery-verify
```

| Check | Result |
|---|---:|
| Archive SHA-256 | `3f690f1b38a1ec355ebb32665a8d25198db1ca4dd7c39adb8c79b24a75dae228` |
| Tar entries listed | 2316 |
| Manifest stashes | 37 |
| Manifest tracked records | 367 |
| Manifest untracked records | 635 |
| Manifest unique file versions | 264 |
| Manifest absent-path restores | 95 |

## Semantic Deduplication Against Current HEAD / origin/main

| Class | Unique file versions | Unique paths | Meaning |
|---|---:|---:|---|
| `not_in_HEAD_or_main` | 113 | 95 | Path/version is not in current HEAD or origin/main; mostly nested stash-recovery snapshots and scratch evidence. |
| `older_or_alternate_version_of_path_in_HEAD` | 102 | 38 | Path exists in HEAD but stash has an older or alternate historical version. |
| `same_as_HEAD` | 49 | 49 | Exact content is already in current HEAD. |

## Local Stash Cleanup

- Local `git stash list` count after cleanup: `0`.
- No `git stash drop` command was needed because there were no stash refs left.
- The raw archive was removed from HEAD in `e7a111c7`; this report is the curated replacement.

## Stashes Covered by Archive

Every stash below is covered by the verified archive manifest from commit `676f7f96`.

| Label | Stash hash | Records | Exact in HEAD | Alternate/older in HEAD path | Not in HEAD/main | Subject |
|---|---|---:|---:|---:|---:|---|
| `stash-00` | `32b778f83903` | 7 | 6 | 1 | 0 | On codex/harness-normalized-primitive-closure: codex-isolate-eas-detractor-leftovers-after-hook-scope-fix-2026-05-15 |
| `stash-01` | `2eb5283d9fd5` | 7 | 4 | 3 | 0 | On codex/harness-normalized-primitive-closure: codex-isolate-eas-detractor-leftovers-before-hook-scope-commit-2026-05-15 |
| `stash-02` | `9c38ee11c71d` | 6 | 5 | 1 | 0 | On codex/harness-normalized-primitive-closure: codex-isolate-eas-detractor-leftovers-before-install-hook-fix-2026-05-15 |
| `stash-03` | `597c81b92789` | 6 | 3 | 3 | 0 | On codex/harness-normalized-primitive-closure: codex-isolate-detractor-adr-leftovers-after-install-scope-adr-2026-05-15 |
| `stash-04` | `c82aecc91e71` | 4 | 4 | 0 | 0 | On codex/harness-normalized-primitive-closure: codex-isolate-eas-leftovers-before-install-scope-adr-commit-2-2026-05-15 |
| `stash-05` | `77522dc92a58` | 6 | 3 | 3 | 0 | On codex/harness-normalized-primitive-closure: codex-isolate-eas-leftovers-before-install-scope-adr-commit-2026-05-15 |
| `stash-06` | `a878169d1474` | 10 | 5 | 5 | 0 | On codex/harness-normalized-primitive-closure: codex-isolate-eas-leftovers-before-install-scope-adr-2026-05-15 |
| `stash-07` | `133b9122fdf5` | 7 | 3 | 4 | 0 | On codex/harness-normalized-primitive-closure: codex-isolate-eas-leftovers-after-agent-runtime-scope-2026-05-15 |
| `stash-08` | `862e90f99a3e` | 3 | 1 | 2 | 0 | On codex/harness-normalized-primitive-closure: codex-isolate-install-scope-doc-leftovers-before-memory-agent-scope-2026-05-15 |
| `stash-09` | `0d04553d14ba` | 2 | 1 | 1 | 0 | On codex/harness-normalized-primitive-closure: codex-isolate-install-scope-smoke-leftovers-before-doctor-scope-commit-2026-05-15 |
| `stash-10` | `38a10d8bc7a2` | 2 | 1 | 1 | 0 | On codex/harness-normalized-primitive-closure: codex-isolate-install-scope-smoke-leftovers-before-primitive-reclass-continue-2026-05-15 |
| `stash-11` | `314ae985452a` | 2 | 0 | 2 | 0 | On codex/harness-normalized-primitive-closure: codex-isolate-install-scope-smoke-reports-before-primitive-reclass-2026-05-15 |
| `stash-12` | `5b4f236f647f` | 2 | 1 | 1 | 0 | On codex/harness-normalized-primitive-closure: codex-isolate-install-scope-smoke-leftovers-before-primitive-reclass-2026-05-15 |
| `stash-13` | `5f556c9cc4d3` | 1 | 0 | 1 | 0 | On codex/harness-normalized-primitive-closure: codex-isolate-install-scope-smoke-enhancement-after-stash-smoke-2026-05-15 |
| `stash-14` | `e9b0ca00c1f1` | 1 | 0 | 1 | 0 | On codex/harness-normalized-primitive-closure: codex-isolate-install-scope-smoke-test-enhancement-before-stash-quarantine-2026-05-15 |
| `stash-15` | `630604160688` | 1 | 0 | 1 | 0 | On codex/harness-normalized-primitive-closure: codex-isolate-install-scope-smoke-enhancement-before-stash-quarantine-2026-05-15 |
| `stash-16` | `a3f5b5bf939f` | 2 | 2 | 0 | 0 | On codex/harness-normalized-primitive-closure: codex-isolate-auto-checkpoint-copy-only-before-eas-2026-05-15 |
| `stash-17` | `5f447509c4ee` | 128 | 14 | 19 | 95 | On codex/harness-normalized-primitive-closure: codex-isolate-unrelated-eas-after-script-scope-2026-05-15 |
| `stash-18` | `3663965667f9` | 145 | 32 | 18 | 95 | On codex/harness-normalized-primitive-closure: codex-isolate-unrelated-eas-before-script-scope-keep-index-2026-05-15 |
| `stash-19` | `08f606836c24` | 125 | 11 | 19 | 95 | On codex/harness-normalized-primitive-closure: codex-isolate-unrelated-eas-before-script-scope-2026-05-15 |
| `stash-20` | `3907b10c4ed0` | 123 | 11 | 17 | 95 | On codex/harness-normalized-primitive-closure: preserve unrelated resurfaced artifacts before script contradictions continue |
| `stash-21` | `712d30c74380` | 122 | 7 | 20 | 95 | On codex/harness-normalized-primitive-closure: preserve unrelated artifacts resurfaced during skill commit hook |
| `stash-22` | `5170d8093e4e` | 116 | 6 | 15 | 95 | On codex/harness-normalized-primitive-closure: preserve unrelated recovered stash artifacts before skills scope batch |
| `stash-23` | `9caa91c45b96` | 94 | 0 | 0 | 94 | On codex/harness-normalized-primitive-closure: preserve unrelated stash recovery report after hook taxonomy closure |
| `stash-24` | `5a7b699a105f` | 6 | 0 | 5 | 1 | On codex/harness-normalized-primitive-closure: preserve unrelated install smoke resurfaced during agent hook batch |
| `stash-25` | `457fd410cb9f` | 8 | 0 | 8 | 0 | On codex/harness-normalized-primitive-closure: preserve unrelated EAS docs resurfaced during agent hook batch |
| `stash-26` | `affa55e638a9` | 6 | 0 | 5 | 1 | On codex/harness-normalized-primitive-closure: preserve unrelated install-scope smoke resurfaced during hook contradiction closure |
| `stash-27` | `8779201d58d7` | 8 | 0 | 8 | 0 | On codex/harness-normalized-primitive-closure: preserve unrelated EAS docs resurfaced during hook contradictions |
| `stash-28` | `f20e094a96ab` | 12 | 0 | 12 | 0 | On codex/harness-normalized-primitive-closure: preserve unrelated EAS/install-scope work before skill scope contract fix |
| `stash-29` | `c92b00228146` | 4 | 1 | 3 | 0 | On codex/harness-normalized-primitive-closure: preserve unrelated falsification benchmark resurfaced before semantic hook contradictions |
| `stash-30` | `05a563e037e2` | 3 | 3 | 0 | 0 | On codex/harness-normalized-primitive-closure: preserve unrelated falsification docs resurfaced after classifier commit |
| `stash-31` | `2731ac7f4c7a` | 2 | 0 | 2 | 0 | On codex/harness-normalized-primitive-closure: preserve unrelated falsification index updates before classifier robustness |
| `stash-32` | `63c3706f6e38` | 3 | 0 | 3 | 0 | On codex/harness-normalized-primitive-closure: preserve unrelated falsification docs before classifier robustness |
| `stash-33` | `67865e0589ad` | 4 | 1 | 3 | 0 | On codex/harness-normalized-primitive-closure: preserve unrelated falsification benchmark before classifier robustness |
| `stash-34` | `ad11f668f9ac` | 10 | 2 | 8 | 0 | On codex/harness-normalized-primitive-closure: preserve unrelated falsification smoke work resurfaced during hook batch |
| `stash-35` | `57ba56afded6` | 5 | 1 | 4 | 0 | On codex/harness-normalized-primitive-closure: preserve unrelated falsification smoke work before hook scope batch |
| `stash-36` | `7afb1e3b80b7` | 9 | 1 | 8 | 0 | On codex/harness-normalized-primitive-closure: preserve unrelated work before scope recalibration batches |

## Removed Raw Snapshot Artifacts

These files are intentionally absent from current HEAD:

- `docs/06-Daily/reports/stash-recovery-2026-05-15-full.tar.gz`
- `docs/06-Daily/reports/stash-recovery-2026-05-15-full.README.md`

Rationale: the archive preserved exact historical bytes for audit, but it also contained duplicated old snapshots and historical reports with developer-local paths. Keeping a small curated verification record is cleaner than keeping the raw blob in the product tree.


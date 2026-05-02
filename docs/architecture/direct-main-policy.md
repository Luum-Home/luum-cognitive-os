# ADR-116 Direct-Main Policy

## Purpose

ADR-116 P2.1 protects `main`/`master` from concurrent session races without making normal operator work unusable.

The policy is intentionally split:

1. **Local hook UX** catches mistakes early.
2. **Remote protection** remains the authoritative boundary before changes reach shared `main`.

## Local policy

| Actor/action | `main`/`master` policy | Rationale |
|---|---:|---|
| Autonomous agent / sub-agent / worker `git commit` | **BLOCK** | Agents must use session branches and land through the merge queue. |
| Operator / human terminal `git commit` | **WARN** by default | Maintains fast local repair UX while surfacing that the safe path was bypassed. |
| Operator with `COS_OPERATOR_MAIN_POLICY=block` | **BLOCK** | Strict mode for incident response, release stabilization, or high-risk work. |
| Any actor `git push` to `main`/`master` | **BLOCK** by default | Shared `main` must advance only through merge queue / governed landing. |
| Merge queue worker / `merge-to-main.sh` push | allow | Single-writer landing path sets `COS_MERGE_QUEUE_WORKER=1` or `COS_MERGE_TO_MAIN=1`. |
| Any actor with `COS_ALLOW_DIRECT_MAIN=1` | allow local commit | One-off emergency commit bypass; do not export permanently. |
| Any actor with `COS_ALLOW_DIRECT_PUSH=1` | allow direct push | One-off emergency push bypass; do not export permanently. |
| Any actor on a non-main branch | allow | Session branches and feature branches are the intended local write surface. |

Implementation: `hooks/direct-main-guard.sh`.

## Protected landing invariant

Local hooks are not the trust boundary. They can be bypassed by shell flags, missing hook installation, or a non-COS client.

The shared repository must satisfy the vendor-neutral [Protected Landing Contract](protected-landing-contract.md). Valid implementations include provider-native protected branches/merge queues, GitLab merge trains, Gitea/Forgejo branch protection, Bitbucket branch permissions, bare-Git server-side hooks, or COS local merge queue plus pre-push fallback for unknown remotes.

A direct `git push origin main` from a normal operator or agent must fail before shared `main` advances whenever the remote can enforce it. If remote enforcement is unavailable, COS must report local-only fallback instead of claiming remote protection.

## Border cases covered by tests

`tests/unit/test_direct_main_guard.py` covers:

- agent commit to `main` blocks,
- operator commit to `main` warns by default,
- strict operator policy blocks,
- session/feature branch commits pass,
- `COS_ALLOW_DIRECT_MAIN=1` bypasses intentionally,
- `COS_OPERATOR_MAIN_POLICY=allow` permits operator commits,
- `CLAUDE_AGENT_ID` auto-detects agent context,
- `master` is treated like `main`,
- direct push from `main` blocks,
- merge-queue push env is allowed,
- pre-push refs for non-main branches pass,
- non-commit Bash commands are ignored,
- non-Bash tool invocations are ignored.

## Operator guidance

Use direct `main` commits only for small, intentional operator repairs. For coordinated work, use:

```bash
bash scripts/cos-session-branch.sh --repo . --slug <work> --switch
# work + commit on session branch
bash scripts/merge-to-main.sh enqueue <session-branch>
```

If emergency direct-main work is unavoidable:

```bash
COS_ALLOW_DIRECT_MAIN=1 git commit --only -- path/to/file -m "fix: emergency repair"
```

If emergency direct-main push is unavoidable:

```bash
COS_ALLOW_DIRECT_PUSH=1 git push origin main
```

Do not put `COS_ALLOW_DIRECT_MAIN=1` in shell startup files.
Do not put `COS_ALLOW_DIRECT_PUSH=1` in shell startup files.

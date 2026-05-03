# Cognitive OS Core in 30 Minutes

This path is for a developer who wants the small, boring-safe COS profile first.
It avoids the maintainer/lab surface until the core signals are green.

## What core includes

Core is the default-visible safety layer: a small set of high-value primitives
for secrets, destructive operations, concurrent writes, branch safety, and
runtime reality checks. It is not the whole SO. Maintainer and lab features stay
available, but they are opt-in.

## Step 1 — inspect the core surface

```bash
scripts/cos-adoption-profile --profile core
scripts/cos-preamble-budget --profile core
scripts/cos-session-start-budget --profile core
python3 scripts/active_primitive_index.py --tier core --json
```

Expected result: core is small enough to read, the preamble estimate is below
the core token budget, and the `SessionStart` boot path has no lab hooks.

## Step 2 — prove the safety controls are honest

```bash
scripts/cos-runtime-hook-reality --fail-on-findings
scripts/cos-silent-failure-audit --fail-on-findings
python3 scripts/cos_architecture_readiness.py --json
```

Expected result: projected runtime hooks are represented in lifecycle metadata,
and shell degradation patterns are classified instead of hidden.

## Step 3 — verify WIP and recovery safety

```bash
scripts/cos-wip-safety-score
scripts/cos-recovery-drill --scenario all
```

Expected result: no orphan pre-agent snapshot markers, no hidden stashes, and
recovery drills pass or produce an explicit repair instruction.

## Step 4 — seed dispatch/cost evidence offline

```bash
scripts/cos-dispatch-smoke --json
```

This exercises the real dispatch metrics path without calling external model
providers and appends one task-history record. After this, cost/dispatch tooling
is no longer operating against empty JSONL files.

## Step 5 — run the local landing gate

```bash
bash scripts/cos-ci-local.sh quick
```

Expected result: quick local CI passes before push. The tracked pre-push hook uses
the same runner when installed with:

```bash
bash scripts/install-git-hooks.sh
```

## Escalation

If any command fails twice with the same signature, stop and fix the underlying
primitive. Do not silence the gate or add allowlist entries without a rationale,
a rollback command, and a test.

# @luum/auto-repair-rollback

Rollback planning trigger — detects verify-apply loop exhaustion and requests a human-approved rollback evidence package.

## Components

- `hooks/auto-rollback-trigger.sh` logs `mode=plan_required`; it does not execute destructive git commands.
- `skills/auto-rollback/SKILL.md` prepares evidence and waits for explicit operator approval.

ADR-107 requires human approval for destructive git in every phase.

## License

Apache-2.0

# Error Recovery

When a task step fails:

1. **Retry**: Attempt the failed step up to 3 times with different approaches
2. **Diagnose**: Read error output carefully. Check imports, types, missing dependencies
3. **Save**: If the error reveals a non-obvious issue, save to Engram via `mem_save` (type: `bugfix` or `discovery`)
4. **Escalate**: If still failing after 3 attempts, stop and report: what failed, what you tried, suggested next steps

Never silently skip a failing step. Never return success if verification failed.

<!-- TIER: 2 -->
<!-- SCOPE: both -->
# Broken Window Policy

## Principle

If you find something broken, you fix it. No exceptions. No "it was already broken." No "it's not related to my task."

The moment an agent detects a failing test, broken hook, stale doc, or any defect — it becomes that agent's responsibility to fix it or create a tracked task for it. "Pre-existing" is not a valid excuse to leave broken things broken.

## Why This Matters

1. **Broken windows compound** — one failing test becomes 10, becomes 60, becomes "tests don't matter"
2. **Trust erosion** — if the agent says "60 tests fail but it's not my fault," the human stops trusting the test suite
3. **Professional ethics** — a craftsman doesn't leave a broken window just because they didn't break it
4. **Signal integrity** — if tests always fail, they stop being useful signals

## Rule (Always Active)

### When Running Tests

If ANY tests fail during a session:

1. **Classify**: Are they related to current work or pre-existing?
2. **If related**: Fix immediately. Do not proceed until green.
3. **If pre-existing**:
   - Fix them NOW if feasible (< 30 minutes estimated)
   - If not feasible: create a tracked task with the exact failures, file it, and report to the user
   - NEVER just say "pre-existing" and move on

### When Discovering Broken Things

If an agent discovers any defect during normal work:

- **Broken test**: Fix it or file it
- **Stale documentation**: Update it or file it
- **Dead code**: Remove it or file it
- **Security issue**: Fix immediately, no filing — this is urgent
- **Deprecated pattern**: Update it or file it

### Output Format

When reporting pre-existing issues:

```
BROKEN WINDOW DETECTED:
  Type: {test_failure|stale_doc|dead_code|security|deprecated}
  Count: {N items}
  Severity: {fix_now|fix_this_session|file_for_later}
  Action taken: {fixed|filed as task|reported to user}
  Details: {specific failures}
```

## Indirect Causation — You Can't Know What You Broke

A common failure mode: "I tested on the pre-restructure tag and it fails there too, so it's pre-existing."

This reasoning is flawed because:

1. **Symlinks change behavior** — a hook that resolves paths with `realpath` vs `readlink` may behave differently after files move behind symlinks
2. **Import order changes** — moving Python files changes `sys.modules` population order, which can trigger latent race conditions
3. **Relative paths break** — a script using `$(dirname $0)/../rules/` breaks if the script moved 2 levels deeper
4. **Permission inheritance** — symlinks inherit the target's permissions, which may differ from what the original file had
5. **Git diff changes** — tools that compare `git diff` output may see renamed files differently
6. **Test isolation** — a test that passed in isolation but fails in suite may be affected by changed test discovery order

**The rule**: If you can't prove with 100% certainty that a failure is unrelated, treat it as potentially caused by your changes and fix it. The cost of fixing a pre-existing bug is zero. The cost of ignoring a bug you caused is high.

## Anti-Pattern: The "Pre-Existing" Excuse

These responses are PROHIBITED:

- ❌ "These failures are pre-existing, not caused by our changes"
- ❌ "60 tests fail but they were already failing"
- ❌ "This is unrelated to our current work"
- ❌ "We can address this in a future session"

These responses are REQUIRED:

- ✅ "60 tests are failing. I'm fixing them now."
- ✅ "60 tests are failing. 45 are quick fixes, 15 need investigation. Fixing the 45 now, filing the 15."
- ✅ "Found a broken hook while migrating. Fixed it before continuing."

## Integration

- Runs alongside `pre-commit-gate.sh` (which blocks commits on test failure)
- Complements `adversarial-review.md` (which mandates findings in reviews)
- Feeds into `agent-kpis.md` (broken windows fixed = quality metric)
- Extends `agent-quality.md` (maximum output, not minimum)

## Contextual Trigger

This rule is always active. It applies every time tests are run or defects are discovered.

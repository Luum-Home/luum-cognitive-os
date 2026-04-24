# Migrating from Hermes-agent

This guide is for users of Hermes-agent (Nous Research) who want to stack
Cognitive OS governance on top of their existing Hermes setup.

**Compatibility assumption**: Cognitive OS hooks fire at harness lifecycle
points (Claude Code's `PreToolUse`, `PostToolUse`, `SessionStart`, `Stop`).
Hermes runs its own skill scheduler at the application layer, below these
lifecycle points. The two systems do not share a hook chain and do not
conflict.

In practice: Hermes skills continue to run exactly as they do today. Cognitive
OS adds verification and safety gates around their output.

---

## Installation

Follow the same recipe as the vanilla Claude Code guide:

```bash
# Step 1: cd into the project where Hermes is running
cd /path/to/your-hermes-project

# Step 2: Install Cognitive OS
curl -sL https://raw.githubusercontent.com/luum-home/luum-cognitive-os/main/install.sh \
  | bash -s -- --harness=claude

# Step 3: Verify
COGNITIVE_OS_PROJECT_DIR="$PWD" bash /path/to/luum-agent-os/scripts/cos-status.sh
```

See [from-vanilla-claude-code.md](from-vanilla-claude-code.md) for the full
install options (local clone, force overwrite, git hook auto-update, uninstall).

---

## What Hermes skills gain

After install, every Hermes skill invocation that routes through Claude Code
gains:

- **Trust report requirement** — `trust-score-validator.sh` (Layer 8) checks
  that skill output includes a scored Trust Report before the session accepts
  a "done" claim.
- **Claim validation** — `claim-validator.sh` (Layer 6) blocks fabricated file
  or test result claims in production mode.
- **Blast radius warning** — `blast-radius.sh` (Layer 2) warns before a
  Hermes skill touches a large scope.
- **Error learning** — failures are captured to `.cognitive-os/metrics/
  error-learning.jsonl` and surfaced as warnings on the next skill launch if
  a pattern repeats 3+ times.

---

## Known interactions

### Hermes dogfood QA skill vs SO trust-score-validator

Hermes includes a self-evaluation skill that rates its own output. That skill
does not emit a Cognitive OS `TRUST_REPORT:` header. As a result, the
`trust-score-validator.sh` hook will log a warning ("no trust report found")
after the skill completes.

This is advisory only (exit 0 in the default profile) — it does not block the
skill. To silence it for specific skills, see the opt-out section below.

### Hermes skill-creation vs SO reinvention-check

When Hermes creates a new skill from experience, the `reinvention-check.sh`
hook (Layer 13) may warn that an existing SO skill covers the same domain.
This is also advisory. Hermes skills and SO skills coexist; they do not
replace each other.

### Hermes cron scheduler vs SO rate-limiter

Hermes's built-in cron scheduler dispatches tasks unattended. If scheduled
tasks run inside a Claude Code session, the `rate-limiter.sh` hook (Layer 4)
applies the per-minute tool-call and cost caps. For long batch Hermes jobs,
increase the hourly cost cap in `cognitive-os.yaml`:

```yaml
resources:
  budget:
    hourly_cap_usd: 20.0   # default is $5/hr
```

---

## Opting out for specific Hermes skills

To suppress Cognitive OS hooks for a named skill, add the skill name to the
`skill_bypass_list` in `cognitive-os.yaml`:

```yaml
governance:
  skill_bypass_list:
    - hermes/dogfood-qa      # suppress trust-score warning for this skill
    - hermes/skill-creator   # suppress reinvention warning for this skill
```

> **Note**: `skill_bypass_list` is a planned configuration key. If it does
> not appear in your installed `cognitive-os.yaml`, the bypass is not yet
> wired. Track progress in `.cognitive-os/plans/` or open an issue.
> In the interim, set the full efficiency profile to `minimal` to suppress
> all non-critical hooks for a session:
> `bash scripts/apply-efficiency-profile.sh minimal`

---

## What Cognitive OS does NOT touch in a Hermes install

- Hermes's model selection (`hermes model`) — unaffected.
- Hermes's messaging gateway (Telegram, Discord, Slack) — unaffected.
  Cognitive OS only fires on hooks inside Claude Code sessions.
- Hermes's Honcho user model — unaffected.
- Hermes's skill storage (`~/.hermes/skills/`) — read-only from SO's
  perspective; SO never writes to Hermes directories.

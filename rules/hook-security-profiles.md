<!-- SCOPE: both -->
<!-- TIER: 2 -->
# Hook Security Profiles

## Purpose

Defines three security profiles (minimal, standard, paranoid) that control which hooks are registered in `.claude/settings.json`. Each profile represents a different trade-off between safety overhead and development speed.

## When to Switch Profiles

| Situation | Recommended Profile | Why |
|-----------|-------------------|-----|
| Exploring a new codebase solo | minimal | Speed matters, governance does not |
| Daily development on a known project | standard | Good balance of safety and speed |
| Pre-production validation | paranoid | Maximum defense before shipping |
| Security audit or compliance review | paranoid | Every gate and scanner active |
| Debugging a specific issue quickly | minimal | Reduce noise from unrelated checks |
| Multi-agent orchestration session | paranoid | Agent governance prevents cascading failures |
| Writing documentation | minimal | No agent governance needed for prose |
| First time onboarding to Cognitive OS | standard | See the safety mesh in action without being overwhelmed |

## Profile Summary

| Property | Minimal | Standard | Paranoid |
|----------|---------|----------|----------|
| Hook count | 11 | 26 | 61 |
| Safety mesh layers | 0/12 | 5/12 | 12/12 |
| Overhead per tool call | ~100-200ms | ~300-500ms | ~2-5s |
| Secret detection | Yes | Yes | Yes |
| Quality gates | No | Yes | Yes |
| Agent governance | No | Partial | Full |
| External scanners | No | No | Yes |
| Observability | No | No | Yes |

## Switching

```bash
bash scripts/set-security-profile.sh [minimal|standard|paranoid]
bash scripts/set-security-profile.sh --current
```

The script backs up `settings.json` before overwriting. Restore with:
```bash
cp .claude/settings.json.bak .claude/settings.json
```

## Subset Property

Profiles are strictly additive: every hook in minimal is also in standard, and every hook in standard is also in paranoid. This guarantees no security regression when upgrading profiles.

## Per-Session Hook Suppression (DISABLE_HOOK_* env vars)

Any registered hook that supports it can be suppressed for the current session
without editing `settings.json` or switching profiles.

**Pattern**: `DISABLE_HOOK_<UPPERCASE_NAME>=true`

Name transformation: hyphens become underscores, all uppercase.

```bash
# Skip blast-radius check for this session only (e.g. for a fast hotfix)
DISABLE_HOOK_BLAST_RADIUS=true claude

# Skip semgrep SAST (e.g. running in a restricted environment)
DISABLE_HOOK_SEMGREP_SCAN=true claude

# Skip aguara security scanner
DISABLE_HOOK_AGUARA_SCAN=true claude
```

**Hooks that support DISABLE_HOOK_*:**

| Hook | Env var |
|------|---------|
| blast-radius.sh | `DISABLE_HOOK_BLAST_RADIUS` |
| clarification-gate.sh | `DISABLE_HOOK_CLARIFICATION_GATE` |
| assumption-tracker.sh | `DISABLE_HOOK_ASSUMPTION_TRACKER` |
| confidence-gate.sh | `DISABLE_HOOK_CONFIDENCE_GATE` |
| claim-validator.sh | `DISABLE_HOOK_CLAIM_VALIDATOR` |
| consequence-evaluator.sh | `DISABLE_HOOK_CONSEQUENCE_EVALUATOR` |
| architecture-compliance.sh | `DISABLE_HOOK_ARCHITECTURE_COMPLIANCE` |
| dispatch-gate.sh | `DISABLE_HOOK_DISPATCH_GATE` |
| auto-skill-generator.sh | `DISABLE_HOOK_AUTO_SKILL_GENERATOR` |
| tool-loop-detector.sh | `DISABLE_HOOK_TOOL_LOOP_DETECTOR` |
| scope-proportionality.sh | `DISABLE_HOOK_SCOPE_PROPORTIONALITY` |
| trust-score-validator.sh | `DISABLE_HOOK_TRUST_SCORE_VALIDATOR` |
| error-pattern-detector.sh | `DISABLE_HOOK_ERROR_PATTERN_DETECTOR` |
| semgrep-scan.sh | `DISABLE_HOOK_SEMGREP_SCAN` |
| aguara-scan.sh | `DISABLE_HOOK_AGUARA_SCAN` |
| rate-limiter.sh | `DISABLE_HOOK_RATE_LIMITER` |

**Important**: These env vars are session-scoped (set in the shell that launches
Claude Code). They do NOT persist across sessions or modify `settings.json`.
Security-critical hooks (secret-detector, content-policy, rate-limiter,
pre-compaction-flush) do NOT check this env var — they always run.

The function is implemented in `hooks/_lib/common.sh` as `check_disabled_env`.

## Relationship to Other Systems

| System | Relationship |
|--------|-------------|
| Efficiency profiles (`apply-efficiency-profile.sh`) | Independent axis. Efficiency controls token overhead; security controls defense depth. |
| Capability levels (`model_capability.level`) | Hooks self-disable at runtime based on capability level, regardless of registration. A hook registered by paranoid profile may self-disable at capability level 4+. |
| Phase-aware behavior | Many hooks change behavior based on project phase (warn in reconstruction, block in production). The security profile controls registration; the phase controls enforcement severity. |

## Full Documentation

See `docs/hook-security-profiles.md` for the complete hook-by-hook breakdown with justifications.

## Contextual Trigger

This rule is loaded when: security profile, hook profile, minimal hooks, paranoid hooks, switch profile, set-security-profile.

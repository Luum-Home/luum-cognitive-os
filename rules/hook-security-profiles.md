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
| Hook count | 10 | 20 | 55 |
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

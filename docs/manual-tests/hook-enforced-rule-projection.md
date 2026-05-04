# Manual Test — Hook-Enforced Rule Projection

Purpose: prove that rule context diet and hook enforcement close together for
both self-hosted COS and downstream projection.

## Preconditions

- Run from the Cognitive OS repository root.
- `jq`, `python3`, and `bash` are available.

## Steps

1. Regenerate all harness projections:

   ```bash
   bash scripts/apply-efficiency-profile.sh maintainer --harness=all
   ```

2. Confirm the high-ROI enforcement hooks are in Claude settings:

   ```bash
   for hook in \
     skill-router-bash-gate.sh prompt-quality-llm.sh token-budget-monitor.sh \
     adaptive-bypass.sh assumption-tracker.sh scope-proportionality.sh \
     scope-creep-detector.sh consequence-evaluator.sh auto-skill-generator.sh \
     release-guard.sh
   do
     grep -q "$hook" .claude/settings.json && echo "PASS $hook"
   done
   ```

3. Confirm Codex receives the Bash-supported bypass gate:

   ```bash
   grep -q 'skill-router-bash-gate.sh' .codex/hooks.json && echo PASS codex-bash-gate
   ```

4. Prove direct dependency upgrade bypass blocks:

   ```bash
   printf '%s' '{"tool_name":"Bash","tool_input":{"command":"brew upgrade gentleman-programming/tap/engram"}}' \
     | CLAUDE_PROJECT_DIR="$PWD" bash hooks/skill-router-bash-gate.sh
   echo "exit=$?"  # expected: 2
   ```

5. Prove explicit operator override works:

   ```bash
   printf '%s' '{"tool_name":"Bash","tool_input":{"command":"COS_ALLOW_SKILL_BYPASS=1 brew upgrade gentleman-programming/tap/engram"}}' \
     | CLAUDE_PROJECT_DIR="$PWD" bash hooks/skill-router-bash-gate.sh
   echo "exit=$?"  # expected: 0
   ```

6. Run the audit contract:

   ```bash
   python3 -m pytest tests/audit/test_hook_enforced_exclusions.py tests/behavior/test_skill_router_bash_gate.py -q
   ```

## Expected result

- Projection scripts report no drift.
- Every hook listed in step 2 is present in `.claude/settings.json`.
- `skill-router-bash-gate.sh` is present in `.codex/hooks.json`.
- Direct upgrade bypass exits 2 unless `COS_ALLOW_SKILL_BYPASS=1` is present.

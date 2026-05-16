# Skill Router False-Positive Cluster — 2026-05-06

## Summary

The router repeatedly suggested high-confidence skills when the user or agent was discussing a skill suggestion as evidence, critique, or risk rather than asking to run it. This is a structural router calibration bug: command mention is being treated as operator intent.

## Incidents captured

| Evidence | Suggested skill | Failure mode | Status |
|---|---|---|---|
| Dogfood cluster #4 | `/systematic-debugging` | Router escalated meta/debug discussion into debugging workflow suggestions | Covered by generic negative-context guard |
| Dogfood cluster #5 | `/deep-research` | Router suggested research workflow for a task whose required output was writing artifacts | Partly covered by ADR-203 output contract; command-mention meta case covered here |
| Dogfood cluster #6 | `/auto-rollback` | Router suggested a destructive/recovery skill while the user was asking why it triggered | Covered first by narrow guard, now by generic negative-context guard |
| Dogfood cluster #7 | `/auto-refine` | Router suggested retry/refinement skill during synthesis/critique context | Covered by generic negative-context guard |
| Dogfood cluster #8 | `/self-improve` | Router suggested self-improvement protocol during Write/batch discussion | Covered by generic negative-context guard |
| Dogfood cluster #11 | `/phoenix-trace-ui` | Router suggested opening Phoenix UI when the prompt explicitly said the suggestion was ignored and mal-calibrated | Covered by generic negative-context guard |

## Root cause

The router had only a narrow `/auto-rollback` meta-reference guard. Other skills still used positive regex matching against explicit command mentions such as `/phoenix-trace-ui`, `/auto-refine`, or `/self-improve` even when the surrounding context contained clear negative evidence:

- `router suggestion` / `router suggestion`;
- `dogfood evidence`;
- `ignoro` / `ignored`;
- `mal calibrado` / `false positive`;
- `why it triggered` / `what triggered`;
- risk-analysis language such as `I am concerned` or `I am afraid`.

The missing abstraction was a router-level **negative evidence reject class**, not one-off filters per skill.

## Corrective action

Add a generic command-mention negative-context guard:

```text
if prompt discusses a router/agent/skill suggestion as critique, evidence, risk, or rejection
and the prompt mentions the candidate skill command/name
then reject that candidate route
```

This preserves direct operator intent:

```text
run /auto-rollback for the failed apply        -> still routes
start phoenix trace ui                         -> still routes
run self-improvement on the system             -> still routes
```

But blocks critique/meta-discussion:

```text
I ignored the router suggestion /phoenix-trace-ui — dogfood evidence #11
What triggers /auto-rollback? I am afraid work could be lost
Skill router /deep-research for writing remains miscalibrated
```

## Remaining work

- Feed rejected-router rows into ADR-201/ADR-204 telemetry so repeated false-positive clusters lower confidence for the relevant route pattern.
- Add a richer intent classifier only if regex negative evidence produces false negatives in real use.
- Keep ADR-203 output-contract preflight separate: router intent and subagent artifact capability are different boundaries.

# Cognitive OS vs AI Slop Falsification Protocol

## Purpose

Cognitive OS must prove it improves agent-assisted engineering outcomes. More hooks, skills, rules, ADRs, and manifests are not proof by themselves.

## A/B/C Groups

| Group | Mode | Meaning |
|---|---|---|
| A | native-harness | Direct Codex/Claude/OpenCode/Goose plus shell, git, tests, permissions, PI defense, and SDD. |
| B | minimal-cos | Small/default COS substrate on the same work. |
| C | full-cos | Broad COS governance mesh on the same work. |

## Product Verdict Rules

- If A wins, COS is slop or premature abstraction for that task class.
- If B wins, default product is minimal COS plus agentic literacy.
- If C wins, full COS is justified only for winning task classes.
- If B and C tie, B wins the default because smaller surface has lower cognitive/operational cost.

## Current Executable Evidence

Run:

```bash
scripts/cos-falsification-benchmark --json --write-report
```

Latest report:

- `docs/06-Daily/reports/cos-falsification-benchmark-latest.json`
- `docs/06-Daily/reports/cos-falsification-benchmark-latest.md`

The deterministic no-provider benchmark currently supports `minimal-cos-default` for the safety/recovery/evidence task set.

## Limits

The deterministic benchmark proves local safety/recovery/evidence outcomes. It does not prove live LLM quality, human cognitive-load reduction, or time-to-merge improvements; those require the manual/live protocol.

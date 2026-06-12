# Primitive Authority Audit — Latest

Generated: 2026-06-12T15:45:06+00:00
Status: `block`

## Summary

- total_scripts: `665`
- by_mode: `{'observe-only': 131, 'os-maintainer-write': 494, 'profile-projection-write': 37, 'propose-only': 3}`
- by_status: `{'pass': 655, 'warn': 10}`
- dynamic_smokes: `4`
- dynamic_blocks: `1`
- block_count: `1`

## Blocking findings

| Path | Mode | Scope | Surfaces | Findings |
|---|---|---|---|---|
| none | - | - | - | - |

## Dynamic smokes

| Smoke | Status | Changed paths | Unexpected paths |
|---|---|---:|---|
| `consumer-improvement-export` | `pass` | 0 | `` |
| `consumer-improvement-import` | `pass` | 1 | `` |
| `project-shell-ci` | `pass` | 36 | `` |
| `cos-init-codex` | `block` | 138 | `.agents/skills/CATALOG.md, .agents/skills/auto-refine, .agents/skills/compose-prompt, .agents/skills/cos-status, .agents/skills/exhaustive-prompt, .agents/skills/plan-feature, .agents/skills/resource-governor, .agents/skills/session-backlog, .agents/skills/verification-before-completion` |

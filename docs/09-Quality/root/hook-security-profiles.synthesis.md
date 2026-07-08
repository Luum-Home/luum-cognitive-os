---
type: quality-synthesis
source: docs/09-Quality/root/hook-security-profiles.md
provenance: "Defines the three security profiles (minimal/standard/paranoid) that control which hooks and safety-mesh layers are active, so operators can trade safety overhead against development speed."
---

## What it is

A reference doc enumerating the three hook security profiles — `minimal`, `standard` (recommended), and `paranoid` — and exactly which hooks are registered under each. Security profiles are one of two independent axes controlling hook behavior; the other is the `efficiency.profile` (lean/standard/full) in `cognitive-os.yaml`, which controls token overhead and governance weight rather than safety-mesh depth.

## Key mechanics

- **minimal** (~100-200ms/call, 11 hooks, 0/12 safety mesh layers): session lifecycle, error capture, secret detection, crash recovery, auto-checkpoint only. No quality gates, no agent governance.
- **standard** (~300-500ms/call, 26 hooks, 5/12 safety mesh layers 1/2/4/6/10): adds clarification-gate, blast-radius, secret-detector + content-policy, claim-validator, clarification-interceptor — the highest-severity failure modes without full overhead.
- **paranoid** (~2-5s/call, 61-62 hooks — doc states both counts inconsistently, matrix totals to 62 — 12/12 safety mesh layers): full mesh plus governance, observability, and external scanners (semgrep, aguara).
- Switching is via `scripts/set-security-profile.sh {minimal|standard|paranoid|--current}`, which backs up `settings.json` before overwriting.
- Hooks check `model_capability.auto_disable` independently of profile: at capability level 3, `context-management` self-disables; at level 4, `clarification-gate`, `assumption-tracking`, `confidence-gate`, `model-routing`, and `blast-radius` self-disable even if the profile registers them. Profile determines *registration*; capability level determines runtime *self-disable*.
- A fixed list of hooks (mcp-scan, singularity-check, agent-bus-monitor, private-mode gates, guardrails-validator, memu-sync, sync-to-repo, pre-commit-gate, etc.) is excluded even from paranoid because they require explicit opt-in flags or external services.

## Relations & where used

- `scripts/set-security-profile.sh` (switch), `scripts/apply-efficiency-profile.sh` (the orthogonal efficiency axis), `cognitive-os.yaml` (`efficiency.profile`, `model_capability`).
- Cross-references the 12/13-layer safety mesh (layers 1-11 plus layer 13 `reinvention-check`; note layer 12 is never mentioned in the hook tables — a numbering gap).
- Complements `rate-limiting.md` (rate-limiter.sh is active in all three profiles).

## Status / caveats

- FLAG: the doc states "Active hooks: 61" in the paranoid section header but the Profile Comparison Matrix totals "**62**" — an internal inconsistency, not fixed here per instructions.
- FLAG: the safety mesh layer numbering has a gap — layers 1-11 and 13 are referenced across the hook tables, but layer 12 never appears in the paranoid hook list, only implied by "12 of 12 all layers active" in the summary line.
- Layer 7 (`assumption-tracker.sh`) is annotated inline as "reassigned from layer 6 in doc," itself flagging a prior inconsistency in the source.

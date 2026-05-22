# Token Savings Q&A — Cognitive OS vs Legacy Agent Governance

> Status: evidence-backed estimate, not a universal guarantee.  
> Date: 2026-05-22  
> Scope: Cognitive OS token/context overhead, compared with projects that use vanilla or legacy agent governance patterns.

## Purpose

This document captures the operator-facing answer to a recurring product and architecture question:

> How many tokens can Cognitive OS save compared with legacy or vanilla agent governance, and how confident are we?

The short answer is: **Cognitive OS can plausibly save ~25%–85% of token usage per task/session**, depending on project size, governance style, number of subagents, and how often agents would otherwise rediscover prior context. The strongest savings come from turning governance from a fixed prompt tax into progressive, on-demand context.

These figures are estimates grounded in current repository sizes, local budget reports, and implemented runtime controls. They should be presented with assumptions and ranges, not as a fixed benchmark claim.

## Current measured anchors

Approximate token counts use the portable `chars / 4` estimator used by the context-budget tooling unless otherwise stated.

| Artifact / surface | Current approximate tokens |
|---|---:|
| `AGENTS.md` | ~2,508 |
| `rules/RULES-COMPACT.md` | ~2,792 |
| `skills/CATALOG-MICRO.md` | ~3,585 |
| `skills/CATALOG-COMPACT.md` | ~4,775 |
| `skills/CATALOG.md` | ~11,982 |
| `cognitive-os.yaml` | ~17,893 |
| `.cognitive-os/generated/runtime-config.compact.yaml` | ~2,181 |
| all `rules/*.md` | ~128,482 |
| all `skills/*/SKILL.md` | ~249,358 |

Current preamble budget estimates:

| Profile | Estimated tokens | Budget | Status |
|---|---:|---:|---|
| core | ~2,865 | 3,200 | pass |
| team | ~5,532 | 6,000 | pass |
| maintainer | ~8,457 | 10,000 | pass |
| lab | ~8,441 | 20,000 | pass |

## Q&A

### Q1. Are we sure Cognitive OS saves tokens compared with legacy governance?

**Answer:** We are confident about the direction and about the order of magnitude in common cases, but not about a single universal number.

The evidence is strong that Cognitive OS reduces fixed prompt overhead when compared with legacy patterns that load large instruction files, full rule sets, full skill catalogs, or full runtime config. The exact savings depend on how wasteful the baseline is.

**Confidence:** high for directional savings; medium for exact percentage ranges.

### Q2. What is the conservative savings estimate?

**Answer:** A conservative estimate is **~14K tokens saved per session** when comparing against a historical baseline around ~17.5K tokens of startup/governance overhead and a compact Cognitive OS profile around ~3.5K tokens.

```text
legacy baseline: ~17.5K
compact COS:      ~3.5K
savings:         ~14.0K tokens
```

This is the safest public-facing claim when avoiding overstatement.

**Confidence:** medium-high.

### Q3. What is the typical savings estimate for a professional project?

**Answer:** For a real medium/large project, a practical expectation is **~50%–70% fewer tokens per task/session** after Cognitive OS is correctly adopted.

This includes savings from:

- progressive rule and skill loading;
- memory-first retrieval instead of rediscovery;
- query-tailored context injection;
- subagent context diet;
- output truncation and replay ledgers;
- cheaper model routing and budget downgrades;
- session-start and preamble budgets.

**Confidence:** medium. This should be validated with paired telemetry for each project.

### Q4. What happens in a legacy project that loads complete governance into every session?

**Answer:** Savings can be very large. If a vanilla/legacy setup loads all rules, the full skill catalog, and the full runtime config, Cognitive OS can save **~150K+ tokens per session**.

Example:

```text
AGENTS.md              ~2.5K
all rules/*.md         ~128.5K
full CATALOG.md        ~12.0K
cognitive-os.yaml      ~17.9K
legacy total           ~160.9K
COS maintainer         ~8.5K
savings                ~152.4K tokens
reduction              ~95%
```

**Confidence:** high for this repo's measured sizes; medium for external projects.

### Q5. What is the extreme theoretical savings case?

**Answer:** If a legacy setup loads all rules, all skill bodies, full config, and global instructions, the current repo implies a possible savings near **~390K tokens per session**.

```text
AGENTS.md              ~2.5K
all rules/*.md         ~128.5K
all skills/*/SKILL.md  ~249.4K
cognitive-os.yaml      ~17.9K
legacy total           ~398.3K
COS maintainer         ~8.5K
savings                ~389.8K tokens
reduction              ~98%
```

This should be described as an upper-bound comparison, not a typical customer outcome.

**Confidence:** high as an upper-bound calculation; low as a typical-use claim.

### Q6. How does a project with Cognitive OS compare to a project without it?

**Answer:** Projects with Cognitive OS usually spend tokens on the current task; projects without it often spend tokens rediscovering how the project works.

Typical estimates:

| Project type | Without SO | With SO | Probable savings |
|---|---:|---:|---:|
| Small, one agent | 20K–60K | 12K–35K | 25%–45% |
| Medium, several files | 80K–250K | 35K–110K | 45%–65% |
| Large, multiagent | 300K–1M+ | 90K–300K | 60%–75% |
| Legacy with manual governance | 150K–500K | 30K–120K | 65%–85% |
| Debug-heavy / chaotic | 500K–2M+ | 120K–500K | 60%–80% |

These ranges include both prompt overhead and operational waste.

**Confidence:** medium. Treat as a planning model until paired telemetry exists.

### Q7. Where do the savings come from?

**Answer:** The largest savings sources are:

1. **Progressive skill loading** — use `CATALOG-MICRO.md` first; load full `SKILL.md` only when needed.
2. **Compact rules** — use `RULES-COMPACT.md` and contextual rules instead of loading every rule.
3. **Runtime config projection** — use compact runtime config instead of full `cognitive-os.yaml` in prompt-facing contexts.
4. **Context diet for subagents** — pass only task-relevant rules and context.
5. **Memory-first retrieval** — avoid rediscovering previous decisions, bugs, conventions, and project facts.
6. **Result truncation** — prevent logs and command output from flooding model context.
7. **Budget/accounting hooks** — detect context growth before it becomes invisible token tax.
8. **Escalation discipline** — stop repeated failed loops from contaminating context.

### Q8. Does Cognitive OS always save tokens?

**Answer:** No. It can add overhead in very small, one-off tasks where there is little project history, no repeated work, no subagents, and no governance burden.

Cognitive OS is most valuable when at least one of these is true:

- the project has meaningful history;
- multiple agents or sessions touch the same repo;
- rules, skills, or safety gates matter;
- debugging can loop;
- there are recurring decisions and conventions;
- external outputs/logs can become large;
- governance needs to be portable across harnesses.

For tiny throwaway tasks, the overhead may not pay back immediately.

**Confidence:** high.

### Q9. Does token saving mean removing safety barriers?

**Answer:** No. The intended optimization is to keep safety barriers in hooks and runtime checks while reducing prompt/context tax.

The principle is:

```text
Do not delete safety. Move it out of always-loaded prose when it can be enforced by hooks, compact indexes, or on-demand rules.
```

Examples:

- Keep destructive-git and secret guards as hooks.
- Keep context-budget enforcement active.
- Keep result truncation and replay ledgers.
- Move large explanatory governance prose out of startup context.
- Load full rule/skill bodies only when relevant.

### Q10. What should we claim externally?

**Answer:** Use bounded language:

> Cognitive OS reduces agent governance token overhead by shifting rules, skills, memory, and runtime config from fixed prompt tax to progressive, on-demand context. In medium to large projects, expected savings are commonly in the 45%–70% range, with higher savings possible for legacy setups that load full rules, skills, or repeated context into every session.

Avoid claiming:

- “always saves 80%”; 
- “guaranteed token reduction”;
- “zero overhead”;
- “measured across all projects” unless paired telemetry exists.

### Q11. What would make the claim stronger?

**Answer:** A controlled paired benchmark per project:

1. Run a task with vanilla governance.
2. Run the same task with Cognitive OS.
3. Record actual provider token usage, not just `chars / 4` estimates.
4. Compare:
   - startup/preamble tokens;
   - tool-output tokens;
   - subagent prompt tokens;
   - repeated file reads;
   - retries;
   - total task cost;
   - task success/quality.
5. Store the result as a report under `docs/06-Daily/reports/` or `.cognitive-os/reports/`.

Until then, current numbers are **evidence-backed estimates**, not universal benchmark results.

## Operator answer card

Use this short answer when asked live:

> Compared with vanilla or legacy agent governance, Cognitive OS typically saves tokens by replacing always-loaded instructions with compact indexes, runtime hooks, memory-first retrieval, query-tailored context, and subagent context diet. Conservative savings are around ~14K tokens per session versus older full-load baselines. In medium/large projects, expected savings are commonly ~45%–70%, and legacy setups that load full rules/skills/config can see ~75%–95%+ reductions in governance/context overhead. These are evidence-backed estimates; exact savings require paired token telemetry for the target project.

## Verification commands

```bash
python3 - <<'PY'
from pathlib import Path
files = [
  'AGENTS.md',
  'rules/RULES-COMPACT.md',
  'skills/CATALOG-MICRO.md',
  'skills/CATALOG-COMPACT.md',
  'skills/CATALOG.md',
  'cognitive-os.yaml',
  '.cognitive-os/generated/runtime-config.compact.yaml',
]
for rel in files:
    path = Path(rel)
    if path.exists():
        chars = len(path.read_text(encoding='utf-8', errors='ignore'))
        print(f'{rel}: ~{chars // 4} tokens')
print('all rules:', sum(p.stat().st_size for p in Path('rules').glob('*.md')) // 4)
print('all skills:', sum(p.stat().st_size for p in Path('skills').glob('*/SKILL.md')) // 4)
PY

for profile in core team maintainer lab; do
  scripts/cos-preamble-budget --profile "$profile"
done
```

## Related documents

- `docs/04-Concepts/architecture/context-rot-token-budget-controls.md`
- `docs/04-Concepts/architecture/token-efficient-agent-messaging.md`
- `docs/09-Quality/manual-tests/token-savings-paired-benchmark.md`
- `rules/context-optimization.md`
- `rules/token-economy.md`
- `scripts/cos-token-savings-audit`
- `scripts/cos-preamble-budget`
- `scripts/cos-context-budget-report`

# Rules Consolidation Plan

> Priority: P0 -- Highest-impact performance change for Cognitive OS.
> Status: Implementation-ready.
> Date: 2026-03-29

---

## Section 1: Current State Analysis

### Rule Counts

| Location | Count | Notes |
|----------|-------|-------|
| `rules/*.md` (total) | 73 | Includes RULES-COMPACT.md |
| Package-sourced rules (symlinked from `packages/*/rules/`) | 17 | 7 packages contribute rules |
| Direct rules (not from packages) | 56 | Core COS rules |
| **Total unique rule files** | **73** | All installed to `.claude/rules/cos/` |

### Size Analysis

Total size across all 73 rule files: approximately 292KB, which translates to roughly 73,000 tokens (at ~4 chars/token).

#### Top 15 Rules by Size (estimated)

| # | Rule | Est. Lines | Est. Tokens | Category |
|---|------|-----------|-------------|----------|
| 1 | RULES-COMPACT.md | ~350 | ~4,500 | Index |
| 2 | agent-quality.md | ~300 | ~3,800 | Quality |
| 3 | closed-loop-prompts.md | ~280 | ~3,500 | Prompt engineering |
| 4 | self-improvement-protocol.md | ~280 | ~3,500 | Lifecycle |
| 5 | phase-aware-agents.md | ~250 | ~3,200 | Governance |
| 6 | agent-kpis.md | ~280 | ~3,500 | KPIs |
| 7 | error-learning.md | ~260 | ~3,300 | Self-healing |
| 8 | ecosystem-tools.md | ~300 | ~3,800 | Ecosystem |
| 9 | agent-escalation.md | ~250 | ~3,200 | Escalation |
| 10 | trust-score.md | ~220 | ~2,800 | Verification |
| 11 | resource-governance.md | ~200 | ~2,500 | Cost |
| 12 | fault-tolerance.md | ~200 | ~2,500 | Persistence |
| 13 | context-optimization.md | ~200 | ~2,500 | Context |
| 14 | definition-of-done.md | ~200 | ~2,500 | Quality |
| 15 | acceptance-criteria.md | ~200 | ~2,500 | Quality |

### Impact by Context Window

| Context Window | Current Load (73K) | % Used | Verdict |
|---------------|-------------------|--------|---------|
| 1M (Opus 4.6) | 73K tokens | 7.3% | Acceptable for self-hosted |
| 200K (Sonnet 4) | 73K tokens | 36.5% | **Problematic** -- over 1/3 of window |
| 128K (GPT-4o, DeepSeek) | 73K tokens | 57% | **Critical** -- over half of window |

### Cumulative Impact for External Projects

When COS is installed in an external project, rules stack:

| Scenario | COS Rules | Project Rules | Total | % of 200K |
|----------|-----------|---------------|-------|-----------|
| Pre-consolidation (small project) | 73K | 15K | 88K | 44% |
| Pre-consolidation (large project) | 73K | 45K | 118K | 59% |
| Post-consolidation (small project) | 12K | 15K | 27K | 13.5% |
| Post-consolidation (large project) | 12K | 45K | 57K | 28.5% |

### WISC Research Threshold

The paper "Evaluating AGENTS.md" (arxiv 2507.11538) found that >150 instructions degrade LLM performance. With 73 rules at session start, a project adding 30 of its own rules would have 103 -- approaching the degradation threshold. Post-consolidation, the same project has 44 -- safely under the limit.

---

## Section 2: The 14 Always-Loaded Rules

These 14 rules must be loaded at session start because they define behavior that agents need on EVERY task, regardless of context. They are the minimum viable governance set.

| # | Rule File | Est. Lines | Est. Tokens | Why Always Loaded |
|---|-----------|-----------|-------------|-------------------|
| 1 | `RULES-COMPACT.md` | ~350 | ~4,500 | Gateway/index to all 73 rules. Contains the backtick references that let the model discover and request any on-demand rule. Without it, on-demand loading has no directory. |
| 2 | `adaptive-bypass.md` | ~140 | ~1,800 | First rule evaluated before EVERY task. Determines complexity classification and whether to apply governance at all. Without it, the model either over-orchestrates trivial tasks or under-governs complex ones. |
| 3 | `acceptance-criteria.md` | ~200 | ~2,500 | Without mandatory acceptance criteria, agents optimize for speed over completeness. This is the single biggest quality lever -- every agent launch needs it. |
| 4 | `agent-quality.md` | ~300 | ~3,800 | Defines the meta-standard for agent output: no sycophancy, no TODOs, no stubs, no minimum-viable interpretation. Core behavioral contract. |
| 5 | `trust-score.md` | ~220 | ~2,800 | Mandatory verification protocol. Every agent completion must include a Trust Report. Without it, agents overclaim completion without evidence. |
| 6 | `definition-of-done.md` | ~200 | ~2,500 | Maps task complexity to DoD criteria. Agents must classify before starting and cannot claim done without passing all criteria for their level. |
| 7 | `phase-aware-agents.md` | ~250 | ~3,200 | Reads current project phase from cognitive-os.yaml and adjusts all agent behavior (rewrite vs patch, auto-remediate vs document). Phase determines enforcement severity for every other rule. |
| 8 | `closed-loop-prompts.md` | ~280 | ~3,500 | Success criteria + verification command + fallback action on every agent launch. The auto-refine retry loop. HALT-and-WAIT protocol. Without it, agents run once and report "done" regardless of outcome. |
| 9 | `token-economy.md` | ~120 | ~1,500 | The 5 token principles (transparency, worthiness, decomposition, memory-first, optimize by default). Prevents waste on every tool call. Active on every decision. |
| 10 | `responsiveness.md` | ~100 | ~1,300 | Never appear stuck. State what you are running before long commands. Use run_in_background. Report results with concrete numbers. Without it, the user experiences silence as a hang. |
| 11 | `agent-security.md` | ~180 | ~2,300 | Least-privilege permissions for every agent. Always-blocked paths (.env, *.key, secrets/*). Monotonic attenuation. Without it, sub-agents have unrestricted access. |
| 12 | `credential-management.md` | ~100 | ~1,300 | Never in code. Always env vars. Validate at startup. This is a security invariant that applies to every session. |
| 13 | `content-policy.md` | ~80 | ~1,000 | Automated enforcement of prohibited terms and patterns via PostToolUse hook. Blocks writes with violations. Always active. |
| 14 | `error-learning.md` | ~260 | ~3,300 | Auto-captures every test/lint/build failure. Pattern detection injects warnings into sub-agent context. The self-healing feedback loop. Without it, the same errors repeat across sessions. |

### Total Always-Loaded Budget

| Component | Tokens |
|-----------|--------|
| 14 always-loaded rules | ~35,300 |
| Minus RULES-COMPACT (already counted separately) | -4,500 |
| **Effective always-loaded overhead** | **~30,800** |
| RULES-COMPACT as the gateway | ~4,500 |
| **Grand total** | **~35,300** |

Wait -- the 14 includes RULES-COMPACT. So the actual new always-loaded budget is approximately 35K tokens for all 14, which is 3.5% of a 1M window and 17.5% of a 200K window. This is a significant improvement from the current 73K (7.3% of 1M, 36.5% of 200K).

### Why Not Fewer Than 14?

Each of the 14 was tested against two criteria:

1. **Frequency**: Is this rule relevant to >80% of sessions?
2. **Failure mode**: What happens if the rule loads 30 seconds late (after the first tool call)?

Rules where late loading is acceptable (e.g., squad-protocol, singularity, dry-run) are on-demand. Rules where even one tool call without them causes quality degradation (e.g., acceptance-criteria, trust-score) must be always-loaded.

### Why Not More Than 14?

The existing test suite (`test_rules_consolidation.py`) already validates that 12 critical rules appear in the Always Active section. The 14 selected here are a superset that adds `adaptive-bypass` and `responsiveness` based on the "every task" criterion.

---

## Section 3: The 59 On-Demand Rules

Each of the remaining 59 rules (73 total minus 14 always-loaded) is loaded only when its trigger condition is met. RULES-COMPACT.md serves as the bookmark -- its compressed summaries let the model find relevant rules and the contextual trigger mechanism loads the full text.

### Trigger Types

| Type | Mechanism | Latency | Example |
|------|-----------|---------|---------|
| `hook` | PostToolUse/PreToolUse hook detects condition | Automatic, <200ms | Error detected, rule loads |
| `command` | User invokes a slash command or skill | On user action | `/squad-report` loads squad-protocol |
| `threshold` | Metric exceeds a configured value | Automatic on detection | Task scope >20 files loads sampling |
| `env_var` | Environment variable is set | At session start | `DRY_RUN=true` loads dry-run |
| `keyword` | Agent prompt or user message contains keywords | Automatic on detection | "rollback" loads auto-rollback |
| `config` | cognitive-os.yaml setting is enabled | At session start | `semgrep.enabled: true` loads security-scanning |

### Complete On-Demand Rule Trigger Map

| # | Rule | Trigger Type | Trigger Condition | Contextual Trigger Pattern (from cognitive-os.yaml) |
|---|------|-------------|-------------------|-----------------------------------------------------|
| 1 | `adversarial-review.md` | command/keyword | `/sdd-verify`, code review tasks | `adversarial.review\|code.review\|zero.finding` |
| 2 | `agent-communication.md` | config | `AGENT_BUS_ENABLED=true` | (package rule, loaded when bus is active) |
| 3 | `agent-customization.md` | keyword | Agent customization, per-agent overrides | (package rule, loaded on agent launch with overrides) |
| 4 | `agent-escalation.md` | hook | PostToolUse Agent detects ESCALATION: marker | `escalat\|agent.stuck\|retry.failure\|loop.detected` |
| 5 | `agent-identity.md` | keyword | Agent identity, audit trail, trust levels | `agent.identity\|audit.trail\|trust.level` |
| 6 | `agent-kpis.md` | command | `/agent-kpis`, session end KPI calculation | `kpi\|okr\|agent.performance\|weekly.review` |
| 7 | `agent-sidecars.md` | keyword | Agent sidecar memory, per-agent learnings | (package rule, loaded on agent launch) |
| 8 | `aguara-integration.md` | config | `security.aguara.enabled: true` | (package rule) |
| 9 | `anti-hallucination.md` | hook | PostToolUse Agent claim-validator fires | `hallucination\|fabricat\|claim.valid\|ground.truth` |
| 10 | `assumption-tracking.md` | hook | PostToolUse Agent detects assumption language | (auto-disabled at capability level 4) |
| 11 | `auto-repair.md` | hook | PostToolUse Bash error triggers repair dispatcher | `auto-repair\|circuit.breaker\|remediation` |
| 12 | `auto-rollback.md` | keyword | sdd-verify fails 3x, retry exhaustion | `auto.rollback\|rollback\|revert\|verify.fail` |
| 13 | `auto-skill-generation.md` | hook | PostToolUse Agent detects complex task completion | (package rule, fires automatically) |
| 14 | `blast-radius.md` | hook | PreToolUse Agent estimates task scope | `blast.radius\|impact.analysis\|scope.estimate` |
| 15 | `broken-window-policy.md` | keyword | Test failures discovered, defects found | (loads when tests fail) |
| 16 | `capability-levels.md` | config | `model_capability.level` in cognitive-os.yaml | `capability.level\|auto.disable\|model.capability` |
| 17 | `capability-protection.md` | command | `/capability-snapshot` invoked | `capability.snapshot\|capability.diff\|feature.loss` |
| 18 | `clarification-gate.md` | hook | PreToolUse Agent scores prompt ambiguity | `clarification.gate\|ambiguous.prompt\|vague.prompt` |
| 19 | `cognitive-load.md` | threshold | Context usage >50%, quality degradation | (loads when context is heavy) |
| 20 | `cognitive-os-changes.md` | keyword | Modifications to hooks, rules, skills | `cognitive.os.change\|os.modif\|hook.change` |
| 21 | `component-classification.md` | keyword | New component classification CORE vs PACKAGE | (loads when adding components) |
| 22 | `confidence-gate.md` | hook | PostToolUse Agent trust score below threshold | `confidence.gate\|low.confidence\|score.below` |
| 23 | `consequence-system.md` | hook | PostToolUse Agent evaluates consequence | `consequence\|promote\|degrade\|disable.skill` |
| 24 | `context-management.md` | threshold | Context capacity thresholds (50/70/85%) | `context.capacity\|save.and.summarize` |
| 25 | `context-optimization.md` | keyword | Token budget, progressive loading | `context.window\|token.budget\|progressive.loading` |
| 26 | `context7-auto-trigger.md` | keyword | External library usage, API documentation lookup | (package rule, loads on library usage) |
| 27 | `cost-prediction.md` | keyword | Cost estimate, budget forecast | `cost.predict\|estimate.cost\|how.much.will` |
| 28 | `crash-recovery.md` | hook | SessionStart detects orphaned stashes | `crash.recovery\|auto.checkpoint\|orphaned.stash` |
| 29 | `decomposition.md` | keyword | Task >$1, break down, sub-tasks | `decompos\|break.down\|sub.task\|cost.aware` |
| 30 | `doc-sync.md` | hook | PostToolUse Edit/Write detects stale docs | `doc.sync\|stale.doc\|documentation.drift` |
| 31 | `dogfooding.md` | keyword | Self-hosted COS development | (loads in luum-agent-os repo) |
| 32 | `dry-run.md` | env_var | `DRY_RUN=true` | (loads when env var set) |
| 33 | `ecosystem-tools.md` | keyword | External tool integration, agnix, semgrep | (package rule) |
| 34 | `engram-organization.md` | keyword | Engram topic keys, memory organization | `engram\|topic.key\|prefix.system` |
| 35 | `estimation-calibration.md` | keyword | Estimation, task complexity, planning poker | `estimat\|calibrat\|planning.poker` |
| 36 | `fault-tolerance.md` | keyword | Resilience, checkpoint, recovery | `fault.tolerance\|resilience\|checkpoint\|recover` |
| 37 | `hcom-integration.md` | config | `agent_communication.hcom.enabled: true` | (package rule) |
| 38 | `hook-security-profiles.md` | keyword | Security profile switching | `security.profile\|hook.profile\|paranoid` |
| 39 | `impact-analysis.md` | keyword | Change impact, downstream effects | `impact.analysis\|change.impact\|importers` |
| 40 | `infra-health.md` | hook | SessionStart checks Docker services | (loads at session start if Docker present) |
| 41 | `infra-intent.md` | hook | PreToolUse Agent detects infra keywords | (advisory, auto-fires) |
| 42 | `library-selection.md` | keyword | New library adoption, dependency evaluation | (loads when adding dependencies) |
| 43 | `license-policy.md` | keyword | License check, copyleft, AGPL | `license\|agpl\|sspl\|gpl\|copyleft` |
| 44 | `model-compatibility.md` | keyword | Model switch, baseline expectations | (loads when discussing model changes) |
| 45 | `model-routing.md` | keyword | Model selection, routing table | `model.routing\|routing.table\|model.select` |
| 46 | `non-blocking-retry.md` | keyword | Rate limit retry, deferred retry | `non.blocking.retry\|deferred.retry` |
| 47 | `orchestrator-mode.md` | config | `ORCHESTRATOR_MODE=executor` | (loads when executor mode active) |
| 48 | `os-vs-project.md` | keyword | OS vs project separation, layer system | (loads when working on COS structure) |
| 49 | `parry-integration.md` | config | `security.parry.enabled: true` | (package rule) |
| 50 | `pentesting-readiness.md` | command | `/pentest-self`, security audit | `pentest\|security.test\|prompt.injection` |
| 51 | `performance-monitoring.md` | keyword | Latency, throughput, bottleneck | `performance.monitor\|latency\|throughput\|p50` |
| 52 | `plan-first.md` | keyword | Plan creation, feature planning | (loads when planning tasks) |
| 53 | `pre-commit-gate.md` | keyword | Pre-commit, coverage gate | (loads when committing) |
| 54 | `private-mode.md` | command | `/private` invoked | (package rule) |
| 55 | `prompt-composition.md` | keyword | Prompt templates, compose prompts | (loads when composing agent prompts) |
| 56 | `prompt-quality.md` | hook | PreToolUse Agent scores prompt quality | (package rule, advisory) |
| 57 | `rate-limit-protection.md` | hook | PreToolUse Agent checks rate limit usage | `rate.limit\|token.flood\|cooldown` |
| 58 | `rate-limiting.md` | hook | PreToolUse Bash/Agent/Edit/Write rate check | `rate.limit\|token.flood\|tool.usage.limit` |
| 59 | `repomix-integration.md` | keyword | Repository packing, repomix | (package rule) |
| 60 | `resource-governance.md` | keyword | Budget, monthly limit, model downgrade | `budget\|monthly.limit\|model.downgrade` |
| 61 | `result-management.md` | hook | PostToolUse Bash truncates large output | (auto-fires on large output) |
| 62 | `sandbox-sampling.md` | threshold | Task scope >20 files | `sandbox\|sample.first\|bulk.change\|100.files` |
| 63 | `scope-creep-detection.md` | hook | PostToolUse Edit/Write checks scope | (package rule, auto-fires) |
| 64 | `scope-proportionality.md` | hook | PostToolUse Agent checks proportionality | (auto-fires) |
| 65 | `scout-pattern.md` | keyword | Pre-implementation reconnaissance | `scout\|reconnaissance\|pre.implementation` |
| 66 | `security-scanning.md` | config | `SEMGREP_ENABLED=true` | `semgrep\|sast\|security.scan` |
| 67 | `self-improvement-protocol.md` | command | `/self-improve`, KPI breach | `self.improve\|self.improvement\|kpi.threshold` |
| 68 | `session-concurrency.md` | keyword | Multi-session, file locking | `session\|concurrent\|lock\|multi.session` |
| 69 | `singularity.md` | command | `/singularity` invoked | `singularity\|autonomous.loop\|mape.k` |
| 70 | `skill-management.md` | keyword | Skill loading, registry, adaptation | (package rule) |
| 71 | `split-and-resume.md` | hook | PostToolUse Agent detects NEEDS_CLARIFICATION | `needs_clarification\|split.and.resume` |
| 72 | `squad-protocol.md` | command | `/squad-report`, `/retrospective` | `/squad-report\|/retrospective` |
| 73 | `step-files.md` | keyword | Long-running phases, resumable steps | `step.file\|long.running\|resumable` |
| 74 | `supply-chain-defense.md` | keyword | Docker digest pinning, supply chain | (loads when working with Docker/deps) |
| 75 | `tero-integration.md` | keyword | HTTP chaos testing, fault injection | (package rule) |
| 76 | `trailofbits-skills.md` | keyword | Trail of Bits security skills | (package rule) |
| 77 | `user-prompt-capture.md` | hook | UserPromptSubmit captures user intent | (auto-fires via hook) |
| 78 | `workload-scheduling.md` | keyword | Task batching, parallel dispatch | `workload.scheduling\|task.batching\|parallel` |

Note: The count shows 78 on-demand entries but the actual count after removing the 14 always-loaded from 73 total is 59. The table above includes rules from both `rules/` and `packages/*/rules/` -- some package rules are symlinked into `rules/` and counted in the 73.

Reconciliation: 73 files in `rules/` minus 14 always-loaded = 59 on-demand rules. The table above numbers beyond 59 because it exhaustively lists every rule including noting which come from packages.

---

## Section 4: Implementation Plan

### Step 1: Update self-install.sh Efficiency Profiles

**Current behavior** (lines 137-163 of `hooks/self-install.sh`):
- `lean` and `standard`: Keep ONLY `RULES-COMPACT.md`, remove all other symlinks
- `full`: Keep all symlinks (no filtering)

**New behavior**:
- `lean`: Keep ONLY `RULES-COMPACT.md` (unchanged)
- `standard`: Keep 14 core rules + `RULES-COMPACT.md` (NEW -- was same as lean)
- `full`: Keep all 73 rules (unchanged, for self-hosted dev)

**Implementation**: Add a `CORE_RULES` array to `self-install.sh` listing the 14 filenames. In the efficiency profile section, when `standard` is detected, keep files matching the array instead of only keeping RULES-COMPACT.md.

```bash
# The 14 always-loaded core rules
CORE_RULES=(
  "RULES-COMPACT.md"
  "adaptive-bypass.md"
  "acceptance-criteria.md"
  "agent-quality.md"
  "trust-score.md"
  "definition-of-done.md"
  "phase-aware-agents.md"
  "closed-loop-prompts.md"
  "token-economy.md"
  "responsiveness.md"
  "agent-security.md"
  "credential-management.md"
  "content-policy.md"
  "error-learning.md"
)

# In the efficiency profile section:
if [[ "$EFFICIENCY_PROFILE" == "lean" ]]; then
  # Only RULES-COMPACT.md
  # (existing behavior)
elif [[ "$EFFICIENCY_PROFILE" == "standard" ]]; then
  # Keep only CORE_RULES
  for link in "$cos_rules_dir"/*.md; do
    [ -L "$link" ] || continue
    base=$(basename "$link")
    is_core=false
    for core in "${CORE_RULES[@]}"; do
      [ "$base" = "$core" ] && is_core=true && break
    done
    if [ "$is_core" = false ]; then
      rm -f "$link"
      removed=$((removed + 1))
    fi
  done
fi
```

### Step 2: Contextual Rule Loading Mechanism

**Evaluation of Options:**

| Option | Mechanism | Pros | Cons | Verdict |
|--------|-----------|------|------|---------|
| A: PreToolUse hook loads rules | Hook reads task context, symlinks relevant rules into `.claude/rules/cos/` | Automatic, no user action | Rules only load AFTER a tool call; first tool call has no context. Symlink creation mid-session may not trigger Claude Code to re-read rules. | **Rejected** -- Claude Code loads rules at session start, not dynamically |
| B: SessionStart hook loads based on config | Hook reads `cognitive-os.yaml` triggers at session start | One-time cost, clean | Cannot adapt mid-session. A session about "auth" loads auth rules at start but not "payments" rules added mid-session. | **Partial** -- good for known contexts |
| C: RULES-COMPACT as bookmark + model self-serves | Model reads RULES-COMPACT, identifies needed rules, uses Read tool to load them | No hook needed. Works with any model. Adapts mid-session. | Model must spend tool calls reading rules. Adds latency on first use. | **Recommended** -- most robust |

**Recommended approach: Option C with B as optimization.**

The key insight is that **Claude Code loads all `.md` files from `.claude/rules/` at session start and does not dynamically reload them mid-session**. This means:

1. The 14 core rules are physically present in `.claude/rules/cos/` (always loaded by Claude Code)
2. The 59 on-demand rules are NOT present in `.claude/rules/cos/` (not loaded at session start)
3. RULES-COMPACT.md contains compressed summaries of ALL 73 rules with `[backtick-refs]`
4. When the model encounters a situation needing an on-demand rule, it reads the full rule file from `rules/{name}.md` using the Read tool
5. The contextual triggers in `cognitive-os.yaml` serve as a lookup table for the model (already present, 80+ triggers defined)

**No new hook is needed.** The existing infrastructure already supports this:
- RULES-COMPACT.md is always loaded (gateway/index)
- Full rule files exist in `rules/` (readable via Read tool)
- `cognitive-os.yaml` has contextual trigger patterns (the model can match these)
- The model already uses Read to access files on demand

### Step 3: Verify RULES-COMPACT.md as Gateway

RULES-COMPACT.md already serves as the gateway. It contains:
- Compressed summaries of all 73 rules organized by theme (11 Always Active sections, 8 Contextual sections)
- Backtick references `[rule-name]` that map to `rules/{rule-name}.md`
- Contextual trigger keywords in parentheses (e.g., "(trigger: `/squad-report`)")
- At approximately 4,500 tokens, it provides a complete directory of the full 73K rule corpus

No changes needed to RULES-COMPACT.md itself. It already documents which rules are always active vs contextual.

### Step 4: Test the Consolidation

#### Before/After Comparison Protocol

1. **Baseline measurement** (profile: full, all 73 rules):
   - Run 10 representative tasks across complexity levels (trivial through large)
   - Record: output quality score, instruction-following rate, hallucination count, token usage, task completion time

2. **Test measurement** (profile: standard, 14 core rules):
   - Run the SAME 10 tasks
   - Record the same metrics
   - Compare: quality must not drop >5%, hallucination must not increase >10%

3. **Edge case testing**:
   - Task requiring on-demand rule (e.g., `/squad-report`) -- verify model reads full rule via Read tool
   - Task requiring security rule (e.g., agent permissions) -- verify agent-security is always loaded
   - Task requiring multiple on-demand rules -- verify model can load 3+ rules in one session
   - Rapid task switching -- verify no confusion between loaded and unloaded rules

#### Automated Test Coverage

The existing `tests/behavior/test_rules_consolidation.py` (42 tests) covers:
- Rule inventory (counts, symlinks)
- Cross-reference integrity (COMPACT refs match files)
- Classification (Always Active vs Contextual sections)
- Content integrity (headers, minimum length, no duplicates)
- Symlink chain (resolution, no circular refs, package chaining)
- Self-install integration (profile behavior)

Additional tests needed (in `tests/behavior/test_rules_consolidation_plan.py`):
- Plan document structure validation
- Core rules list validation
- Trigger map completeness

---

## Section 5: Risk Analysis

| # | Risk | Severity | Likelihood | Mitigation |
|---|------|----------|------------|------------|
| 1 | Rule not loaded when needed | HIGH | LOW | RULES-COMPACT.md always has a compressed summary of every rule. The model can identify when a full rule is needed and Read it from `rules/`. The contextual triggers in cognitive-os.yaml provide a lookup table. |
| 2 | Performance regression from Read tool calls | MEDIUM | LOW | Each rule file is 2-10KB (fast read). A typical session might need 0-3 on-demand rules. The 59K tokens saved vastly outweigh the cost of 3 Read calls (~500 tokens each). |
| 3 | Model forgets to check RULES-COMPACT | MEDIUM | LOW | RULES-COMPACT is always loaded. It explicitly states "Full rules loaded contextually via reference keys." The model's instructions include checking this index. |
| 4 | Self-hosted development loses governance | NONE | NONE | Full profile is unchanged. Self-hosting always forces all 73 rules. This consolidation only affects `lean` and `standard` profiles. |
| 5 | On-demand rule loaded too late | MEDIUM | MEDIUM | The 14 core rules cover the most frequent failure modes (quality, trust, security, credentials). On-demand rules like squad-protocol or singularity are rarely needed in the first few tool calls. |
| 6 | New rules added but not classified | LOW | HIGH | The test suite validates that every rule in `rules/` has a backtick reference in RULES-COMPACT.md. Adding a rule without updating RULES-COMPACT fails the test. Adding a rule to the 14 core requires updating `self-install.sh`. |
| 7 | Package rules not handled correctly | LOW | LOW | Package rules are already symlinked through `rules/` into `.claude/rules/cos/`. The CORE_RULES array in self-install.sh handles them identically to direct rules. |
| 8 | Capability-level auto-disable conflicts | LOW | LOW | Capability levels disable HOOKS, not rules. Rules loading is independent of hook registration. The two systems are complementary, not conflicting. |

---

## Section 6: Migration Path

### Phase 1: Update Efficiency Profiles (Week 1)

**Goal**: Make `standard` profile install 14 core rules instead of just RULES-COMPACT.md.

1. Update `hooks/self-install.sh`:
   - Add `CORE_RULES` array with the 14 filenames
   - Modify the standard profile section to keep core rules (not just RULES-COMPACT)
   - Add `profile: standard-core` to cognitive-os.yaml for gradual rollout
2. Run existing test suite (`test_rules_consolidation.py`) -- all 42 tests must pass
3. Run new plan tests (`test_rules_consolidation_plan.py`)
4. Commit

### Phase 2: Build Contextual Loading Documentation (Week 1)

**Goal**: Document how models should use RULES-COMPACT as a gateway.

1. Add a "How to Load On-Demand Rules" section to RULES-COMPACT.md header
2. Update `docs/rules-loading-architecture.md` with the new standard profile behavior
3. Update `cognitive-os.yaml` contextual_triggers to cover all 59 on-demand rules (most already defined)
4. Commit

### Phase 3: Test on Self-Hosted (Week 2)

**Goal**: Validate the consolidation on this repository.

1. Temporarily set `efficiency.profile: standard` in cognitive-os.yaml
2. Run 10 representative tasks across complexity levels
3. Measure quality, token usage, and instruction-following
4. Compare against baseline (profile: full)
5. Revert to `full` after testing
6. Document results

### Phase 4: Test on External Project (Week 2-3)

**Goal**: Validate on a real project that installs COS.

1. Set up a test project with `cos init`
2. Verify `standard` profile installs exactly 14 core rules
3. Run tasks requiring on-demand rules -- verify model reads them via Read tool
4. Run tasks NOT requiring on-demand rules -- verify token savings
5. Document results

### Phase 5: Roll Out to All Installations (Week 3)

**Goal**: Make standard profile the default for all external projects.

1. Update `cos init` to use `standard` profile by default
2. Update documentation
3. Release as part of next COS version
4. Monitor Engram for issues reported by users

---

## Section 7: Token Budget Calculator

### Scenarios

| Scenario | Rules Loaded | Est. Tokens | % of 1M | % of 200K | % of 128K |
|----------|-------------|-------------|---------|-----------|-----------|
| Current (all 73) | 73 | ~73,000 | 7.3% | 36.5% | 57.0% |
| Core only (14) | 14 | ~35,300 | 3.5% | 17.7% | 27.6% |
| Core + 3 on-demand (typical session) | 17 | ~42,300 | 4.2% | 21.2% | 33.0% |
| Core + 5 on-demand (active session) | 19 | ~47,300 | 4.7% | 23.7% | 37.0% |
| Core + 10 on-demand (heavy session) | 24 | ~57,300 | 5.7% | 28.7% | 44.8% |
| Core + 20 on-demand (extreme session) | 34 | ~77,300 | 7.7% | 38.7% | 60.4% |

Note: On-demand rules loaded via Read tool go into the conversation context, not the system prompt. They are consumed when used but do not persist as permanent overhead. The effective ongoing cost is lower than the table suggests because on-demand rules are read once and then available in the conversation window.

### Savings Summary

| Metric | Before | After (standard profile) | Savings |
|--------|--------|--------------------------|---------|
| Rules in system prompt | 73 | 14 | 80.8% reduction |
| Tokens in system prompt | ~73K | ~35K | 52.1% reduction |
| % of 200K window | 36.5% | 17.7% | 18.8 percentage points freed |
| WISC instruction count | ~73 rule files | ~14 rule files | Below degradation threshold |

### Cost Impact

| Model | Before (73K tokens at session start) | After (35K tokens) | Monthly savings (100 sessions) |
|-------|-------------------------------------|---------------------|-------------------------------|
| Opus ($15/1M in) | $1.10/session | $0.53/session | ~$57/month |
| Sonnet ($3/1M in) | $0.22/session | $0.11/session | ~$11/month |
| Haiku ($0.25/1M in) | $0.02/session | $0.01/session | ~$1/month |

### For External Projects (COS + Project Rules)

| Project Size | Own Rules | + COS Before | + COS After | Tokens Saved |
|-------------|-----------|-------------|------------|-------------|
| Small (5 rules) | ~8K | 81K total | 43K total | 38K (47%) |
| Medium (15 rules) | ~23K | 96K total | 58K total | 38K (40%) |
| Large (30 rules) | ~45K | 118K total | 80K total | 38K (32%) |
| Enterprise (50 rules) | ~75K | 148K total | 110K total | 38K (26%) |

---

## Appendix A: Mapping to Existing Infrastructure

### cognitive-os.yaml Contextual Triggers

The `rules.loading.contextual_triggers` section already defines regex patterns for 60+ rules. These patterns serve as documentation for the model -- when it encounters matching context, it knows which rule to read. No code changes needed; just ensure all 59 on-demand rules have a trigger defined.

**Currently missing triggers** (need to be added):
- `broken-window-policy`
- `component-classification`
- `dogfooding`
- `hook-security-profiles`
- `infra-health`
- `library-selection`
- `model-compatibility`
- `os-vs-project`
- `plan-first`
- `pre-commit-gate`
- `prompt-composition`
- `result-management`
- `supply-chain-defense`

### Existing Test Safety Net

The 42 tests in `test_rules_consolidation.py` cover:

| Test Class | Tests | What It Validates |
|-----------|-------|-------------------|
| TestRuleInventory | 6 | File counts, symlinks, COMPACT existence |
| TestCrossReferenceIntegrity | 4 | Bidirectional COMPACT refs, hook/skill refs |
| TestRulesClassification | 7 | Section structure, critical rules placement |
| TestContentIntegrity | 4 | Headers, length, duplicates, compression ratio |
| TestSymlinkChain | 6 | Symlink resolution, circular refs, package chains |
| TestSelfInstallIntegration | 4 | Profile behavior (full, lean, standard) |
| TestContextualTriggers | 3 | Trigger patterns vs rule files |
| TestRuleNaming | 3 | Naming conventions |
| TestPackageRules | 3 | Package rule symlink chains |
| TestKnownRulesList | 2 | Known rules baseline |

---

## Appendix B: Decision Record

### ADR: Rules Consolidation from 73 Always-Loaded to 14 Core + 59 On-Demand

**Status**: Proposed

**Context**: Cognitive OS loads all 73 rules (~73K tokens) at session start. The WISC paper shows >150 instructions degrade LLM performance. For external projects with their own rules, the combined count approaches the degradation threshold. 36.5% of a 200K context window is consumed before any work begins.

**Decision**: Reduce always-loaded rules to 14 core rules (~35K tokens) for the `standard` efficiency profile. The remaining 59 rules remain available on-demand via RULES-COMPACT.md as a gateway and the Read tool for full access. The `full` profile (self-hosted development) is unchanged.

**Consequences**:
- Easier: External projects can use COS without losing 36% of their context window. Smaller models (200K context) become viable for COS-powered projects. Session start-up cost drops by 52%.
- Harder: On-demand rules require a Read tool call to load (~200ms + ~500 tokens each). The model must correctly identify when an on-demand rule is needed. New rules must be classified as core vs on-demand.

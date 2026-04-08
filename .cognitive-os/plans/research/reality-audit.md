# Cognitive OS Reality Audit — What's Real vs Aspirational

## Summary
- Project: 137 commits in 5 days (March 27-31, 2026)
- 12 features shipped in 2 hours 38 minutes on day 1
- Classification: 30% real, 70% aspirational
- Token overhead: 93,700 tokens per session (2,677% of 3,500 target)

## 1. What Actually Runs (25 hooks registered in settings.json)

These are the ONLY hooks that execute in a live session:

### SessionStart (3)
- self-install.sh — symlinks rules
- session-init.sh — creates session directory
- crash-recovery.sh — checks orphaned git stashes

### PreToolUse (4)
- rate-limiter.sh — rate limits (on Bash, Agent, Edit, Write)
- clarification-gate.sh — blocks vague prompts (on Agent)
- blast-radius.sh — estimates impact (on Agent)
- error-pattern-detector.sh — injects warnings for known patterns (on Agent)
- large-file-advisor.sh — advises on large file reads (on Read)

### PostToolUse (10)
- error-pipeline.sh — captures errors (on Bash)
- result-truncator.sh — truncates large output (on Bash)
- auto-checkpoint.sh — periodic git stash (on Bash, Edit, Write)
- secret-detector.sh — blocks credential leaks (on Edit, Write)
- content-policy.sh — prohibited terms (on Edit, Write)
- doc-sync-detector.sh — tracks stale docs (on Edit, Write)
- claim-validator.sh — validates file claims (on Agent)
- completion-gate.sh — checks acceptance criteria (on Agent)
- clarification-interceptor.sh — detects NEEDS_CLARIFICATION (on Agent)
- agent-checkpoint.sh — task tracking (on Agent)

### UserPromptSubmit (1)
- background-agent-reminder.sh

### Stop (2)
- session-learning.sh — capture session errors
- session-cleanup.sh — cleanup session directory

### Other (1)
- release-guard.sh
- task-created.sh, task-completed.sh, teammate-idle.sh (lifecycle)

## 2. What Exists But Never Runs (59 hooks — 70% of all hooks)

These hooks were written (100-250 lines each), possibly tested in isolation, but never wired into settings.json:

### Would-be-valuable (should register):
auto-skill-generator, concurrent-write-guard, pre-compaction-flush, assumption-tracker, confidence-gate, consequence-evaluator, scope-proportionality, trust-score-validator, tool-loop-detector, kpi-trigger, session-resume, task-recorder, user-prompt-capture, session-state-save

### External-tool-dependent (register if tool installed):
aguara-scan, semgrep-scan, mcp-scan, agnix-lint, guardrails-validator, observability-trace

### Feature-specific (opt-in):
singularity-check, private-mode-gate, private-mode-metrics-gate, dry-run-preview, adaptive-bypass, contextual-rule-loader, inject-phase-context, infra-health, infra-intent-detector

### Probably dead weight:
paperclip-sync, memu-sync, jupyter-sandbox, conversation-capture, engram-auto-import, engram-auto-sync, metrics-rotation, metrics-calibrator-trigger, notify, package-sync, sync-to-repo, skill-tracker, tool-discovery-trigger

## 3. Hooks That Don't Exist (7 ghost references)

Rules describe these hooks but the files were never created:
1. hooks/auto-refine.sh — referenced by closed-loop-prompts.md, phase-aware-agents.md
2. hooks/auto-verify.sh — referenced by acceptance-criteria.md, agent-quality.md
3. hooks/dod-gate.sh — referenced by agent-quality.md, confidence-gate.md
4. hooks/error-learning.sh — referenced by auto-repair.md, error-learning.md
5. hooks/auto-repair-dispatcher.sh — referenced by auto-repair.md
6. hooks/skill-feedback-tracker.sh — referenced by auto-skill-generation.md
7. hooks/parry-scan.sh — referenced by ecosystem-tools.md

## 4. Rules Classification

### Rules with automated enforcement (~20 of 94 — 21%)
These rules have registered hooks that actually run:
rate-limiting, clarification-gate, blast-radius, error-learning (partial via error-pipeline), secret detection (credential-management), content-policy, result-management, crash-recovery

### Rules that are behavioral LLM instructions (~48 of 94 — 51%)
These load into context (costing tokens) but have NO enforcement:
adversarial-review, agent-identity, agent-quality (partial), broken-window-policy, capability-protection, cognitive-os-changes, component-classification, credential-management, decomposition, definition-of-done, library-selection, license-policy, model-compatibility, os-vs-project, pentesting-readiness, plan-first, prompt-composition, sandbox-sampling, scout-pattern, step-files, supply-chain-defense, token-economy, acceptance-criteria (missing auto-verify hook), closed-loop-prompts (missing auto-refine hook), trust-score (validator exists but unregistered), agent-escalation, agent-kpis, anti-hallucination (validator exists but unregistered), auto-rollback, context-management, fault-tolerance, impact-analysis, scope-creep-detection (hook exists but unregistered), split-and-resume, user-prompt-capture (hook exists but unregistered)

### Documentation-only rules (~28 of 94 — 30%)
These describe optional features, external tools, or infrastructure:
ecosystem-tools, parry-integration, hcom-integration, tero-integration, trailofbits-skills, aguara-integration, e2b-integration, repomix-integration, context7-auto-trigger, infra-health, performance-monitoring, agent-communication, agent-customization, agent-sidecars, orchestrator-mode, hook-security-profiles, infra-intent, singularity, auto-skill-generation, dynamic-tool-creation, non-blocking-retry, cost-prediction, doc-sync, workload-scheduling, estimation-calibration, squad-protocol, self-improvement-protocol, component-classification

## 5. The Disconnected Learning Loop

The rules describe a connected learning system. The code tells a different story:

| System | File | Imports from other loop systems | Verdict |
|--------|------|-------------------------------|---------|
| error_classifier.py | lib/ | Nothing | ISLAND |
| consequence_engine.py | lib/ | Only model_catalog.py | ISLAND |
| skill_archive.py | lib/ | Nothing | ISLAND |
| prompt_classifier.py | lib/ | Nothing | ISLAND |
| auto-skill-generator.sh | hooks/ | No lib imports | ISLAND |
| error-pipeline.sh | hooks/ | No lib imports from loop | ISLAND |

Zero cross-imports. Zero shared data paths. Zero event bus. The "learning loop" described in rules does not exist as connected code.

## 6. Orphaned Lib Files

### Completely orphaned (zero references):
- lib/cognee_client.py

### Referenced only by own test (effectively orphaned):
agent_dashboard, claude_usage_reader, context_diet, error_classifier, error_matching, homeostasis, jupyter_client, kpi_collector, memory_decay, research_scoring, session_parser, web_crawler, webhook_trigger

### Missing lib referenced by hook:
- lib/engram_client.py — imported by hooks/subagent-context-injector.sh but does not exist

## 7. Token Overhead Breakdown

94 rule files loaded via symlinks in .claude/rules/cos/ every session:

Total: ~364,548 characters → ~91,137 tokens
Plus global CLAUDE.md: ~10,224 characters → ~2,556 tokens
GRAND TOTAL: ~93,693 tokens per session

Top 10 most expensive rules:
1. RULES-COMPACT.md: ~3,669 tokens (redundant when full rules loaded)
2. ecosystem-tools.md: ~3,293 tokens (documentation only)
3. agent-kpis.md: ~2,584 tokens (no dashboard connected)
4. agent-quality.md: ~2,265 tokens (references 3 missing hooks)
5. closed-loop-prompts.md: ~2,240 tokens (references 3 missing hooks)
6. skill-management.md: ~2,100 tokens (routing table, useful)
7. self-improvement-protocol.md: ~1,900 tokens (aspirational)
8. squad-protocol.md: ~1,800 tokens (aspirational)
9. estimation-calibration.md: ~1,750 tokens (aspirational)
10. agent-escalation.md: ~1,700 tokens (aspirational)

## 8. Root Cause Analysis

### Why this happened
1. **Speed over integration**: 137 commits in 5 days. 27 commits/day average. No time for end-to-end testing.
2. **Design-first, integration-never**: Rules were written as specifications. Hooks and libs were implemented separately. The connection between them was never built.
3. **Tests verify existence, not behavior**: "134 tests" check that files exist and have correct format. No integration tests verify the learning loop works end-to-end.
4. **Framework effect**: Priority was an impressive catalog (84 hooks! 94 rules! 40 libs!) over a working pipeline.
5. **Aspirational rules cost real tokens**: Each "behavioral guideline" rule costs 500-3,000 tokens per session. 48 aspirational rules consume ~45,000 tokens doing nothing enforceable.

### What to do about it
See: maturation-strategy.md (Clean → Connect → Integrate → Adopt)

# Cognitive OS Maturation Strategy

## Premise

COS is 30% real, 70% aspirational. Before adopting new features from Hermes/Pi, we must mature what we have. The strategy is: Clean → Connect → Integrate → Adopt.

## Phase 1: Clean (Reduce 93K → ~15K tokens)

### 1.1 Move documentation-only rules to docs/
These 30+ rules describe how things work but don't instruct the LLM to do anything. They belong in docs/, not .claude/rules/cos/:

Move to `docs/reference/`:
- ecosystem-tools.md (3,293 tokens) — lists optional external tools
- parry-integration.md — describes optional parry setup
- hcom-integration.md — describes optional hcom setup
- tero-integration.md — describes optional tero setup  
- trailofbits-skills.md — describes optional ToB skills
- aguara-integration.md — describes optional aguara setup
- e2b-integration.md — describes optional E2B setup
- repomix-integration.md — describes optional repomix
- context7-auto-trigger.md — describes optional Context7
- infra-health.md — documents how infra-health hook works
- performance-monitoring.md — documents metrics collection
- agent-communication.md — documents Valkey bus (OFF by default)
- agent-customization.md — documents override files
- agent-sidecars.md — documents sidecar pattern
- orchestrator-mode.md — documents executor mode
- hook-security-profiles.md — documents profile system
- infra-intent.md — documents intent detection
- singularity.md — documents autonomous loop (OFF by default)
- auto-skill-generation.md — documents auto-gen (hook exists but unregistered)
- dynamic-tool-creation.md — documents dynamic tools
- non-blocking-retry.md — documents retry scheduling
- cost-prediction.md — documents cost prediction
- doc-sync.md — documents doc sync detection
- workload-scheduling.md — documents workload scheduler
- estimation-calibration.md — documents estimation system
- squad-protocol.md — documents squad governance
- self-improvement-protocol.md — documents self-improvement
- component-classification.md — documents CORE vs PACKAGE

### 1.2 Remove RULES-COMPACT.md from .claude/rules/cos/
It's 3,669 tokens of an index that summarizes rules that are also loaded in full. When we reduce to ~15 rules, it becomes the ONLY file loaded (replaces the individual rules).

### 1.3 Keep only enforceable rules in .claude/rules/cos/
These ~15 rules have registered hooks or are critical behavioral instructions:
- adaptive-bypass.md — task complexity classification
- acceptance-criteria.md — mandatory criteria in agent prompts
- agent-quality.md — anti-sycophancy, completeness standards
- trust-score.md — mandatory trust reports
- token-economy.md — 5 token principles
- phase-aware-agents.md — phase-dependent behavior
- closed-loop-prompts.md — success criteria + verification
- error-learning.md — error capture protocol
- rate-limiting.md — rate limit enforcement
- credential-management.md — never credentials in code
- content-policy.md — prohibited terms enforcement
- result-management.md — output truncation
- blast-radius.md — impact estimation
- clarification-gate.md — ambiguity blocking
- model-routing.md — model selection table

### 1.4 Estimated result
From 94 files (~93,700 tokens) to ~15 files (~15,000 tokens). 84% reduction.

## Phase 2: Connect (Wire the 59 orphan hooks)

### 2.1 Triage the 59 unregistered hooks
For each of the 59 hooks that exist but aren't registered:

**Register (high value, low risk):** ~15 hooks
- auto-skill-generator.sh — the skill nudge counter EXISTS but never fires
- concurrent-write-guard.sh — advisory locking (upgrade later)
- pre-compaction-flush.sh — compaction safety net
- assumption-tracker.sh — detect assumption language
- confidence-gate.sh — block low-confidence in production
- consequence-evaluator.sh — OKR-driven feedback
- scope-proportionality.sh — detect disproportionate changes
- trust-score-validator.sh — validate trust reports
- tool-loop-detector.sh — detect infinite loops
- kpi-trigger.sh — KPI threshold checking
- session-resume.sh — resume interrupted tasks
- session-learning.sh — capture session errors (already registered at Stop)
- task-recorder.sh — record completed task costs
- user-prompt-capture.sh — capture actionable user messages
- session-state-save.sh — save state on exit

**Delete (dead weight, never needed):**
- Hooks for external tools not installed (aguara-scan, semgrep-scan, parry-scan, mcp-scan, etc.)
- Hooks for features we don't use (singularity-check, paperclip-sync, memu-sync, jupyter-sandbox)
- Hooks that duplicate registered hooks or are superseded

**Keep unregistered (opt-in via paranoid profile):**
- The remaining ~25 hooks stay as opt-in for the paranoid security profile

### 2.2 Create the 7 missing hooks
These are described in rules but have no file:
1. auto-refine.sh — retry loop on test/build/lint failure
2. auto-verify.sh — run acceptance criteria commands on completion  
3. dod-gate.sh — check Definition of Done criteria
4. error-learning.sh — capture errors to JSONL (the rule describes it, hook/error-pipeline.sh partially covers it)
5. auto-repair-dispatcher.sh — classify errors and attempt known fixes
6. skill-feedback-tracker.sh — track skill execution feedback
7. parry-scan.sh — prompt injection scanning (requires parry-guard installed)

## Phase 3: Integrate (Connect the learning loop)

### 3.1 Create lib/learning_pipeline.py
Connect the 5 island systems into one pipeline:

```
User message arrives
    → prompt_classifier.py classifies intent
    → if actionable: mem_save_prompt
    
Agent completes task
    → skill_archive.py records execution (trust score, success)
    → consequence_engine.py evaluates streak (promote/degrade)
    → error_classifier.py captures any failures
    
Every N tool calls (skill nudge)
    → auto-skill-generator.sh fires
    → background review checks if skills need creation/update
    
On error pattern (3+ same type)
    → error_classifier feeds into skill_archive
    → consequence_engine downgrades affected skill
    → self-improvement suggests /optimize-skill
```

### 3.2 Add cross-imports
- consequence_engine imports from skill_archive (reads execution history)
- skill_archive imports from error_classifier (correlates errors with skills)  
- auto-skill-generator reads from prompt_classifier (user intent informs skill creation)

### 3.3 Create integration tests
Test the FULL loop: trigger error → detect pattern → warn on next agent → skill updates
Target: 90% coverage on the pipeline connections

## Phase 4: Adopt (Best of Hermes & Pi)

### Priority order (highest impact first):

### 4.1 Reduce token overhead further — Prompt caching
Adopt Hermes's system_and_3 caching strategy. Place 4 cache_control breakpoints. ~75% input token cost reduction.

Implementation plan:
- New file: lib/prompt_caching.py
- Integrate with agent-preamble template
- Tests: verify cache breakpoints are placed correctly, verify cost reduction

### 4.2 Background review agent
Adopt Hermes's _spawn_background_review pattern. After every N tool calls, spawn a haiku agent to review conversation for skill/memory extraction.

Implementation plan:
- New hook: hooks/background-review.sh (PostToolUse on Agent)
- Modify auto-skill-generator.sh to delegate to background agent instead of regex
- Tests: verify review fires after threshold, verify skill creation, verify non-blocking

### 4.3 User modeling
Build lib/user_model.py on top of Engram. Synthesize preferences from captured prompts.

Implementation plan:
- New file: lib/user_model.py
- New file: lib/feedback_detector.py (implicit acceptance detection)
- Modify agent-preamble template to inject user model
- Tests: verify preference extraction, verify implicit/explicit feedback, verify model persistence

### 4.4 Hybrid memory retrieval
Add Jaccard reranking to Engram queries. Port from lib/cost_predictor.py.

Implementation plan:
- New file: lib/memory_retriever.py (~150 lines)
- Add trust_score to Engram observations (schema change)
- Tests: verify FTS5+Jaccard scoring, verify trust weighting, verify recall improvement

### 4.5 Structured compaction
Adopt Pi's compaction algorithm with Hermes's iterative summaries.

Implementation plan:
- Rewrite hooks/pre-compaction-flush.sh to use LLM summarization
- Add file operation tracking
- Add iterative summary updates
- Tests: verify cut-point selection, verify summary structure, verify iterative updates

### 4.6 Real file mutation queue
Replace advisory locking with Pi's withFileMutationQueue pattern.

Implementation plan:
- Rewrite hooks/concurrent-write-guard.sh with actual serialization
- Add symlink-aware path resolution
- Tests: verify concurrent edits are serialized, verify different files proceed in parallel

### 4.7 Content security for memory
Add Hermes's injection scanning before Engram saves.

Implementation plan:
- New file: lib/memory_scanner.py
- 12 threat patterns + invisible Unicode detection
- Integrate with mem_save flow
- Tests: verify injection blocked, verify clean content passes, verify Unicode detection

### 4.8 Context injection fencing
Wrap Engram-retrieved content in <memory-context> safety tags.

Implementation plan:
- Modify memory retrieval to add fencing
- Sanitize fence tags from any retrieved content
- Tests: verify fencing applied, verify tag sanitization

### 4.9 Skills guard trust-tier model
Adopt Hermes's builtin/trusted/community/agent-created classification.

Implementation plan:
- New file: lib/skills_guard.py
- Integrate with cos audit command
- Quarantine workflow for community skills
- Tests: verify tier classification, verify scan patterns, verify quarantine

### 4.10 Shadow git checkpoints
Adopt Hermes's GIT_DIR redirect pattern for cleaner rollback.

Implementation plan:
- Modify hooks/auto-checkpoint.sh to use shadow git repos
- Add /rollback command
- Tests: verify checkpoint creation, verify rollback, verify no .git pollution

## Test Strategy (90% Coverage Target)

### Unit tests per new lib file
Each new lib/*.py file gets a corresponding test file in tests/unit/:
- test_learning_pipeline.py
- test_user_model.py  
- test_feedback_detector.py
- test_memory_retriever.py
- test_memory_scanner.py
- test_skills_guard.py
- test_prompt_caching.py

### Integration tests
tests/integration/:
- test_learning_loop_integration.py — full loop: error → pattern → warning → skill update
- test_memory_pipeline.py — save → scan → retrieve with Jaccard → fence
- test_compaction_flow.py — trigger → summarize → iterative update
- test_background_review.py — nudge counter → spawn → skill creation

### Hook tests
tests/hooks/:
- test_registered_hooks.py — verify ALL registered hooks exist and are executable
- test_hook_settings_sync.py — verify settings.json matches actual hook files
- test_hook_coverage.py — verify every rule's referenced hooks exist

### Coverage enforcement
- pytest-cov with --cov-fail-under=90
- CI gate: block merge if coverage drops below 90%
- Coverage tracked in .cognitive-os/metrics/

## Timeline Estimate

| Phase | Effort | Dependencies |
|-------|--------|-------------|
| Phase 1 (Clean) | 1-2 sessions | None |
| Phase 2 (Connect) | 2-3 sessions | Phase 1 |
| Phase 3 (Integrate) | 2-3 sessions | Phase 2 |
| Phase 4 (Adopt) | 5-8 sessions | Phase 3 |

Total: ~10-16 sessions for full maturation.

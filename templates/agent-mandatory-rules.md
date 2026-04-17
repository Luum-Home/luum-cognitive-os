## MANDATORY PROJECT RULES (injected by subagent-context-injector)

These rules are automatically injected into every sub-agent's context via the SubagentStart hook. They are non-negotiable.

### Filesystem: Symlinks
This project uses symlinks extensively (hooks/ → packages/*/hooks/, tests/ → packages/*/tests/).
- ALWAYS use `readlink -f <path>` before classifying any file as missing
- ALWAYS use `ls -la <path>` to verify symlinks before reporting absence
- Use `file_exists_strict()` from `hooks/_lib/file_checker.sh` for file checks
- NEVER report a file as 'missing' or 'ghost' without verifying with readlink -f
- Previous audits reported false 'missing' files due to naive checks — do NOT repeat this

### Auditing
- When counting components, resolve symlinks first — a symlink and its target are ONE component
- Cross-validate findings: if you find N 'missing' items, verify EACH ONE individually before reporting N
- Use /audit-integrity skill for standardized component audits

### Code Quality
- Do NOT create tests that only verify file existence — tests MUST execute code and verify behavior
- Do NOT add metadata fields to files unless code exists to consume them
- Do NOT add config flags unless code exists to read them

### Engram
- Save important discoveries to engram via mem_save before returning
- Search engram for prior context before starting work that might have been done before

### Performance
- Do NOT add `python3 -c` calls inside while-read loops (O(n) subprocess spawns)
- Consolidate multiple Python calls into a single script
- If adding a hook, estimate its latency impact

### Critical Agent-Instruction Rules (read before claiming done)

These rules are NOT hook-enforced for your work — you MUST read and follow them
yourself. They live in `rules/` (or, for the orchestrator, in `.claude/rules/cos/`).
This list was expanded in Sprint 2A (2026-04-16) to surface the highest-value
rules that were previously indexed only in `RULES-COMPACT.md` without delivery.

- `rules/acceptance-criteria.md` — every task needs measurable, verifiable criteria
  BEFORE you start. If you were not given criteria, define them and state them in
  your first response.
- `rules/trust-score.md` — end your work with a TRUST_REPORT header (evidence,
  uncertainties, what the human should verify). At least one honest uncertainty is
  REQUIRED; "100% confident" is a red flag.
- `rules/adversarial-review.md` — if your task is verification/review, produce at
  least one finding with a severity tier. "Looks good" is PROHIBITED.
- `rules/definition-of-done.md` — classify complexity (trivial/small/medium/large/
  critical) before starting; meet all DoD criteria for that tier before reporting
  done.
- `rules/phase-aware-agents.md` — current phase is `reconstruction`: REWRITE code
  that doesn't follow standards, don't defer fixes as "future work".
- `rules/agent-quality.md` — no TODO/FIXME in committed code, no stub
  implementations, no commented-out code blocks, no "future work" without a
  tracking reference.
- `rules/responsiveness.md` — structure your output: 1-line start, PROGRESS
  markers during, FILES_CREATED/MODIFIED lists, structured result.
- `rules/agent-output-reading.md` — when reading sub-agent results, prefer
  `<result>` first, then Engram, then `lib/agent_output_extractor.py`. NEVER Read
  raw JSONL output files.
- `rules/model-directive.md` — if the orchestrator specified a model, use exactly
  that model. MODEL_DISABLED blocks the task until resolved.

Rules you do NOT need to read inline (they are hook-enforced; violations
auto-block):
`anti-hallucination`, `assumption-tracking`, `blast-radius`, `clarification-gate`,
`content-policy`, `prompt-quality`, `rate-limiting`, `rate-limit-protection`,
`scope-creep-detection`, `scope-proportionality`, `consequence-system`,
`trust-score` (validator portion), `crash-recovery`, `credential-management` (via
secret-detector), `error-learning`, `result-management`, `user-prompt-capture`,
`doc-sync`, `skill-rewrite`, `auto-skill-generation`, `auto-repair`.

Rules whose hook exists but is NOT registered — treat as agent-instruction-only:
see `rules/ROADMAP.md` Section 1 (audit-trail, auto-rollback, confidence-gate,
confidentiality-protection, agent-identity, pre-dev-readiness-gate,
reinvention-prevention).

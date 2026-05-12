<!-- SCOPE: os-only -->
<!-- TIER: 0 -->
# Rules Roadmap — Pending Work

> Created Sprint 2A, 2026-04-16. Tracks rules whose enforcement promise exceeds
> current wiring. Each entry documents WHAT is missing, WHO must fix it, and the
> INTERIM behavior (what agents should do today).

## Section 1 — Hook-enforced-BROKEN (8 rules)

These rules claim enforcement via a hook that **exists on disk** but is **NOT
registered in `.claude/settings.json`**. The hook will never fire. Until
registered, the rule is **demoted to "agent-instruction-only"** — agents must
follow the rule by reading it, not expect automatic enforcement.

Hook registration is owned by `hooks/self-install.sh` (and the efficiency-profile
script). Per the Sprint 2A scope guard, neither is editable in this sprint.

### 1.1 `audit-trail.md`
- **Claimed hooks**: `git-context-capture.sh`, `session-changelog.sh`, `audit-id-enricher.sh`
- **State**: all 3 exist on disk in `hooks/` or `packages/*/hooks/`; none registered
- **Interim**: agents MUST include who/when/what in every change, as if the hooks were firing
- **Pending action**: register all 3 hooks in `.claude/settings.json` under the
  appropriate `Stop` and `PostToolUse` matchers (owner: hook-registration sprint)
- **RESOLVED**: git-context-capture.sh registered at apply-efficiency-profile.sh:264 (Stop); session-changelog.sh and audit-id-enricher.sh registered at lines 263 (PostToolUse Agent), per commit 92cf485

### 1.2 `auto-rollback.md`
- **Claimed hook**: `auto-rollback-trigger.sh`
- **State**: exists on disk, not registered
- **Interim**: agents MUST check for rollback triggers manually; the orchestrator
  MUST be prepared to invoke rollback by running the hook by hand
- **Pending action**: register under `PostToolUse Agent` matcher with failure signal
- **RESOLVED**: auto-rollback-trigger.sh registered at apply-efficiency-profile.sh:264 (PostToolUse Agent), per commit 92cf485

### 1.3 `confidence-gate.md`
- **Claimed hooks**: `confidence-gate.sh`, `trust-score-validator.sh`
- **State**: `trust-score-validator.sh` IS registered; `confidence-gate.sh` is NOT
- **Interim**: the trust-score validator fires (partial enforcement), but the
  pre-launch confidence gate does not. Agents SHOULD still publish confidence
  estimates in their own output
- **Pending action**: register `confidence-gate.sh` under `PreToolUse Agent`
- **RESOLVED**: confidence-gate.sh registered at apply-efficiency-profile.sh:258 (PostToolUse Agent), confidence-gate-llm.sh at line 259, per commit 92cf485

### 1.4 `confidentiality-protection.md`
- **Claimed hook**: `confidentiality-enforcer.sh`
- **State**: exists on disk, not registered
- **Interim**: agents MUST refuse to emit credentials or PII; secret-detector
  (separately registered) catches a subset but not the full confidentiality scope
- **Pending action**: register under `PostToolUse Edit|Write`
- **RESOLVED**: confidentiality-enforcer.sh registered at apply-efficiency-profile.sh:227 (PostToolUse Edit|Write), per commit 92cf485

### 1.5 `agent-identity.md`
- **Claimed hook**: `audit-id-enricher.sh`
- **State**: exists on disk, not registered
- **Interim**: agents MUST self-declare identity (name, model, purpose) in the
  first line of every response
- **Pending action**: register under `PreToolUse Agent` so IDs are auto-stamped
- **RESOLVED**: audit-id-enricher.sh registered at apply-efficiency-profile.sh:263 (PostToolUse Agent), per commit 92cf485

### 1.6 `pre-dev-readiness-gate.md`
- **Claimed hook**: `predev-completeness-check.sh`
- **State**: exists on disk, not registered
- **Interim**: the orchestrator MUST manually invoke `/readiness-check` before
  `sdd-apply` on Medium+ tasks (same behavior, slower feedback loop)
- **Pending action**: register under `PreToolUse Agent` when agent name matches
  `sdd-apply*`
- **RESOLVED**: predev-completeness-check.sh registered at apply-efficiency-profile.sh:191 (PreToolUse Agent), per commit 92cf485

### 1.7 `reinvention-prevention.md`
- **Claimed hook**: `reinvention-check.sh`
- **State**: exists on disk, not registered
- **Interim**: orchestrator MUST run `/reinvention-check` manually before adopting
  a new pattern; no automatic block
- **Pending action**: register under `PreToolUse Edit|Write` when the edit creates
  a new module
- **RESOLVED**: reinvention-check.sh registered at apply-efficiency-profile.sh:194 (PreToolUse Agent), per commit 92cf485

### 1.8 `pre-commit-gate.md` (INTENTIONAL — not a Claude hook)
- **Claimed hook**: `pre-commit-gate.sh` (symlinked to `.git/hooks/pre-commit`)
- **State**: intentionally a git hook, not a Claude hook. Agent-level
  enforcement is explicitly out of scope
- **Interim**: continues to fire on `git commit` as expected
- **Pending action**: NONE. Already on `SETTINGS_WIRING_EXEMPT` in
  `tests/audit/test_rules_enforcement.py`

## Section 2 — Code-dead hook references (6 originally, 3 remaining)

Rules that referenced hooks which **did not exist on disk** at the time of the
Capa-3 audit. Three of the six were resolved by Sprint UX2 (hook files created);
three remain.

### 2.1 `acceptance-criteria.md` → `auto-verify.sh` — RESOLVED
- Hook built by UX2. Verify registration status before closing this item.

### 2.2 `agent-quality.md` → `auto-verify.sh` + `dod-gate.sh` — RESOLVED
- Both hooks built by UX2. Verify registration status.

### 2.3 `closed-loop-prompts.md` → `auto-refine.sh` — RESOLVED
- Hook built by UX2. Verify registration status.

### 2.4 `phase-aware-agents.md` → `auto-refine.sh` — RESOLVED (same hook as above)

### 2.5 `response-compression.md` / `self-install.sh comment` → `response-length-check.sh` — RESOLVED (D24)
- **State**: hook does NOT exist on disk. Misleading comment in `hooks/self-install.sh`
  removed (Batch C, 2026-04-20). Comment now reads "agent-instruction-only (no hook)".
- **Resolution**: `self-install.sh` EXCLUDED_RULES comment updated to remove the
  `→ response-length-check.sh` reference. Rule is fully agent-instruction-only.
- **No further action required.**

### 2.6 `context-optimization.md` → `context-budget.sh` — RESOLVED (D25)
- **State**: hook does NOT exist on disk. Misleading sentence in `rules/context-optimization.md`
  removed (Batch C, 2026-04-20). Rule now explicitly states agents self-monitor per
  `rules/context-management.md` thresholds (50% / 70% / 85%).
- **Resolution**: rule updated to be fully agent-instruction-only with no hook reference.
- **No further action required.**

## Section 3 — Template coverage (agent-mandatory-rules)

The injector hook (`subagent-context-injector.sh`) only delivers
`templates/agent-mandatory-rules.md` to sub-agents. Sprint 2A extended this
template to reference the 5–10 highest-value agent-instruction rules so that
sub-agents can discover them by name.

This is a workaround, not a fix. True rule-loading (resolve `[rule-key]` →
inject rule body) requires a slash command or a hook; neither is on this
sprint's roadmap.

## Cross-reference

- Audit source: `docs/04-Concepts/architecture/functional-audit/scorecard-rules.md`
- Test contract: `tests/audit/test_rules_enforcement.py`
- This file's orchestration: `docs/04-Concepts/architecture/functional-audit/sprint-2a-orphan-fate.md`

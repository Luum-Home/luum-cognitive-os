# Implement Tier 1 — Batch Hook Wiring
**Date:** 2026-05-02  
**Phase:** reconstruction  
**Items:** triage-2026-05-01 IMPLEMENT batch — items 10, 11 (auto-refine), 20 (dod-gate), 27 (error-learning), 32 (large-file-advisor)

---

## Summary

Wired 4 observability hooks from the ASPIRATIONAL tier into the active hook registry. All hooks were already complete implementations (not stubs), carrying the `# SCOPE:` frontmatter marker and killlswitch support.

---

## Aspirational Audit — Before / After

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| REAL | 217 | 220 | +3 |
| DORMANT | 186 | 187 | +1 |
| ASPIRATIONAL | 50 | 47 | **-3** |
| Dormant+Aspirational ratio | 32.2% | 31.9% | -0.3pp |
| Total components | 732 | 734 | +2 |

Note: 3 of 4 hooks reclassified immediately to REAL. The 4th (large-file-advisor.sh) requires a live firing within the 7-day window for REAL promotion — expected within one normal session.

---

## Per-Hook Verification

### 1. `hooks/error-learning.sh` (item 27)
- **Event:** PostToolUse Bash  
- **Lines:** 77 (complete — classification, dedup, fingerprint, safe_jsonl_append)  
- **SCOPE marker:** `# SCOPE: both` (line 2) ✓  
- **Wired in:** `settings-driver-claude-code.sh` → `post_bash` group  
- **Settings.json grep:** `error-learning.sh: 1 occurrences` ✓  
- **Security profiles:** added to PostToolUse Bash in minimal, standard, paranoid ✓  

### 2. `hooks/large-file-advisor.sh` (item 32)
- **Event:** PreToolUse Read  
- **Lines:** 104 (complete — size check, token estimate, section hints, metrics log)  
- **SCOPE marker:** `# SCOPE: both` (line 2) ✓  
- **Wired in:** `settings-driver-claude-code.sh` → new `pre_read` group (matcher: "Read")  
- **Settings.json grep:** `large-file-advisor.sh: 1 occurrences` ✓  
- **Security profiles:** new PreToolUse Read group added to minimal, standard, paranoid ✓  

### 3. `hooks/auto-refine.sh` (item 10)
- **Event:** PostToolUse Agent  
- **Lines:** 154 (complete — phase-aware, failure detection, retry counting, PITER integration)  
- **SCOPE marker:** `# SCOPE: both` (line 2) ✓  
- **Wired in:** `settings-driver-claude-code.sh` → `post_agent` group  
- **Settings.json grep:** `auto-refine.sh: 1 occurrences` ✓  
- **Security profiles:** added to PostToolUse Agent in minimal (new group), standard, paranoid ✓  

### 4. `hooks/dod-gate.sh` (item 20)
- **Event:** PostToolUse Agent  
- **Lines:** 202 (complete — complexity inference, 5 DoD levels, artifact integration, phase-aware enforcement)  
- **SCOPE marker:** `# SCOPE: both` (line 2) ✓  
- **Wired in:** `settings-driver-claude-code.sh` → `post_agent` group  
- **Settings.json grep:** `dod-gate.sh: 1 occurrences` ✓  
- **Security profiles:** added to PostToolUse Agent in minimal (new group), standard, paranoid ✓  

---

## Files Modified

| File | Change |
|------|--------|
| `scripts/_lib/settings-driver-claude-code.sh` | +`pre_read` group (large-file-advisor); +`error-learning.sh` to post_bash; +`auto-refine.sh`, `dod-gate.sh` to post_agent; added `pre_read` to loop |
| `scripts/apply-efficiency-profile.sh` | Added 4 hooks to sanity check list (line ~134) |
| `templates/security-profiles/minimal.json` | +PreToolUse Read group; +error-learning to Bash; +new Agent group (auto-refine+dod-gate) |
| `templates/security-profiles/standard.json` | +PreToolUse Read group; +error-learning to Bash; +auto-refine+dod-gate to Agent |
| `templates/security-profiles/paranoid.json` | +PreToolUse Read group; +error-learning to Bash; +auto-refine+dod-gate to Agent |
| `.claude/settings.json` | Regenerated via `bash scripts/apply-efficiency-profile.sh default` (99 hook commands) |

---

## Hook Count Delta

- **Before:** 95 hook commands in settings.json (inferred from driver before edits)  
- **After:** 99 hook commands in settings.json  
- **Delta:** +4 (one per hook)

---

## Pre-existing Warnings (not caused by this batch)

```
Warning: expected hook 'lethal-trifecta-gate.sh' missing from settings.json after apply.
Warning: expected hook 'aci-observation-capture.sh' missing from settings.json after apply.
```

These 2 warnings pre-date this batch. Both hooks exist in the sanity list but are absent from the driver — a separate cleanup item.

---

## TRUST REPORT

- **Evidence (40%):** grep confirms all 4 hooks appear exactly once in `.claude/settings.json`; aspirational audit moved from 50→47 ASPIRATIONAL components
- **Criteria (30%):** All hooks verified: complete implementation (>20 lines of real logic), SCOPE marker present, event/matcher matches triage spec
- **Self-awareness (20%):** 2 pre-existing sanity warnings observed — not introduced by this batch; `lethal-trifecta-gate.sh` and `aci-observation-capture.sh` are known pre-existing drift items
- **Proportionality (10%):** 5 files modified, all additive-only edits, zero deletions

**Confidence:** HIGH. All 4 hooks wired; settings.json regenerated atomically; audit confirms movement in expected direction.

**Uncertainty:** large-file-advisor.sh may not appear as REAL in the aspirational audit until it fires in a live session (file read on a file >40KB). Expected within one normal working session.

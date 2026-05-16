# Plan: SessionStart deep audit — self-hosted vs client install

> Created 2026-04-30. Read-only investigation. Output: measurements + decision-grade ADR.

## Why this plan

User question: "does this guarantee that SessionStart will be more efficient?"
Honest answer so far: No. The work landed today (`991b24a`, `c8a5259`, `e93e3b7`,
`f360fe4`, `0c2583f` + pending) targets PreToolUse[Agent] expansion, not
SessionStart. The user wants a real, measured analysis of:

1. What SessionStart costs **today** in this self-hosted repo, by component.
2. What SessionStart costs **today** in a fresh client project that installs COS.
3. Whether any commit from today's work changes either of those costs.
4. Concrete unexplored levers to reduce SessionStart specifically — ranked.

## Out of scope

- Code edits. This plan is read-only.
- Designing the fix. Output is options + tradeoffs, not implementation.
- Re-running audits already saved in Engram (use them as inputs).

## Inputs (read these first)

- Engram topic keys: `cos-learning-loop-wiring-audit`,
  `hermes-learning-loop-source-map`, `cos/sessionstart-core-rules-patch`,
  `cos/stage2-selective-expansion-plan`, `cos/stage2-selective-expansion-impl`,
  `cos/stage2-tier1-reclassification`, `cos/corerules-self-hosting-fix` (when
  agent `a6a0...` finishes — wait for it if not done).
- Today's commits: `61d5703`, `991b24a`, `3912338`, `c8a5259`, `e93e3b7`,
  `f360fe4`, `0c2583f` (plus whatever lands from the 3 still-running agents).
- Existing measurements: `docs/06-Daily/measurements/stage2-expansion-baseline.md`.

## Deliverables

### 1. `docs/06-Daily/measurements/sessionstart-baseline.md`

Two side-by-side tables. For each component injected at SessionStart, list:

| Component | Mechanism | Bytes | ~Tokens | Self-host? | Client? |
|---|---|---|---|---|---|

Components to enumerate (verify each by reading source, not assuming):

- `~/.claude/CLAUDE.md` (global user file, harness-level).
- `<repo>/CLAUDE.md` (project-level, if exists).
- `claudeMd` symlink injection from `.claude/rules/cos/` (driven by
  `CORE_RULES` + `SYNC_ALL_RULES`).
- SessionStart hooks registered in `.claude/settings.json` →
  `hooks.SessionStart[]`. For each, identify source script, measure typical
  stdout, classify blocking vs background.
- MCP server instructions block (engram + others).
- Skills `CATALOG-COMPACT.md` injection (find the mechanism — is it always
  injected, or only on Skill tool use?).
- Deferred tools listing (notable tokens but harness-managed).
- Persisted-output blocks (e.g., `hook-*-stdout.txt` references).

For each, measure with `wc -c` and convert tokens by /4. Flag any whose token
count was estimated (no real measurement).

### 2. Per-commit impact analysis on SessionStart

Table: each commit from today × {self-host SessionStart impact, client
SessionStart impact}. Honest: most should be 0 / 0 except `991b24a` (and
whatever `a6a0...` produces).

### 3. Unexplored levers

Ranked list. For each lever:

- What it changes (1 sentence)
- Estimated tokens saved (self-host / client)
- Effort estimate (LOC, files)
- Risk
- Why it isn't done yet

Likely candidates:

- **Engram persistent-output → pointer**: 11 KB of inline protocol could
  become "Engram protocol active. Run `engram-help` to view." Saves ~2.7K
  tokens. Risk low (engram tool list still loads; just the verbose protocol
  isn't inlined).
- **Skills CATALOG-COMPACT lazy-load**: only inject when `Skill` tool first
  used. Saves ~3.5K tokens at SessionStart. Risk: skills become invisible to
  the agent until first invocation — agent may not know skill exists.
- **`MEMORY.md` index → on-demand**: per global CLAUDE.md, `MEMORY.md` is
  always loaded. If it gets long, injection cost grows. Verify size and
  whether truncation kicks in.
- **Self-hosting startup hooks (3 blocking)**: session-init.sh,
  session-startup-protocol.sh, self-knowledge-refresh.sh. Audit whether each
  is necessary at startup or could be deferred (PreToolUse, lazy).
- **MCP engram metadata**: ~1 KB of tool instructions. Probably not
  reducible without API changes.
- **Tu `~/.claude/CLAUDE.md`**: 11 KB global. Belongs to the user, not
  COS — but worth flagging as a lever the user controls.

### 4. ADR-080 (if needed)

Only create if a non-trivial architectural decision is forced (e.g., "should
SessionStart deliver a manifest of available rules instead of inlining
RULES-COMPACT?"). If not, skip — the measurements doc + research log entry
is enough.

### 5. Research log entry

Append to `docs/03-PoCs/root/research-log.md`:
"## 2026-04-30: SessionStart deep audit (self-host vs client)"

## Acceptance criteria

- Measurements doc has both tables fully filled (no `?` cells).
- Every estimated token count is flagged as estimate vs measured.
- Per-commit impact analysis is concrete with file:line refs where possible.
- Levers list has at least 5 entries with all 5 columns filled.
- No code edits in working tree at end (other than the new doc + log entry).
- One commit, subject: `docs(measurements): sessionstart deep audit baseline`.

## Methodology constraints

- **Measure, don't guess.** When an estimate is required, mark it.
- Read the actual hook scripts before classifying their cost. Many are tiny.
- For client-mode estimation: use `IS_SELF_HOSTING=false` simulation if
  practical (e.g., `IS_SELF_HOSTING=false bash scripts/apply-efficiency-profile.sh
  default` in a sandbox dir, then count what would be in the resulting
  `.claude/`). Don't deploy to a real cliente.
- Wait for `a6a0...` (CORE_RULES self-hosting fix) before drafting the
  per-commit table — its result changes whether `991b24a` impacts self-host.

## Risk

This plan is read-only and produces measurements + a doc. The risk is
investigative thrash if the methodology is sloppy. Mitigated by listing
acceptance criteria above.

## Next steps after this plan

Based on the levers ranked in Deliverable 3, the user picks 1-2 to attack
with implementation agents in a follow-up sprint. Today's session ends with
this audit.

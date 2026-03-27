# UX Principles: The Invisible Operating System

> The user does not need to know what the OS has -- the AI knows how to use it.
> Like a modern car: the driver does not know about ABS, ESP, traction control, or side airbags.
> They just drive. When they brake on a wet road, ABS activates automatically.
> The driver only notices they did not skid.

---

## Principle 1: Invisible Safety

All safety mechanisms run silently unless they need to intervene.

```
SILENT (user sees nothing):
  Hook runs -> everything OK -> no output

INFORMATIVE (brief acknowledgment):
  Hook runs -> something noteworthy -> one-line info
  Example: "Verified: fix is proportional to task scope."

INTERVENTION (needs user attention):
  Hook runs -> problem detected -> clear explanation + action
  Example: "This fix touches 45 files. That seems disproportionate
           for a bug fix. Can you confirm?"

BLOCK (prevents damage):
  Hook runs -> danger detected -> blocks + explains
  Example: "Blocked: fix tasks cannot delete files.
           If you want to rewrite the module, rephrase as a refactor task."
```

Rules for communication:

- NEVER overwhelm with "12 safety checks passed!" -- that is noise
- Only speak when there is something the user needs to know
- When blocking, ALWAYS explain WHY and suggest WHAT TO DO instead
- Use plain language, not internal jargon (no "scope-proportionality hook triggered")

### How This Maps to the Safety Mesh

The 12-layer safety mesh (see `docs/safety-mesh.md`) operates at three visibility levels:

| Visibility | Layers | User Experience |
|------------|--------|-----------------|
| Silent | Blast radius, assumption tracker, trust score validator | User sees nothing. Metrics logged for on-demand review. |
| Informative | Clarification interceptor, scope proportionality | One-line note when something noteworthy happens. |
| Intervention | Clarification gate, confidence gate, rate limiter | Clear explanation of what is needed and why. |
| Block | Dry-run preview, auto-rollback trigger | Hard stop with explanation and alternative action. |

The user experiences a smooth workflow. The safety mesh runs underneath, surfacing only when it has something valuable to say.

---

## Principle 2: Progressive Disclosure

Complexity reveals itself only when needed.

```
Level 0 -- Just works:
  install.sh -> done
  User: "fix this bug"
  AI uses 20 rules, 15 hooks internally
  User sees: fixed bug, verified, committed

Level 1 -- Discovers SDD:
  User: "I want to add a big feature"
  AI suggests: "This is complex. Want me to plan it first with /sdd-new?"
  User discovers the pipeline exists

Level 2 -- Discovers quality gates:
  Trust report appears in output
  User: "What's this trust score?"
  AI explains: "I rate my own confidence so you know what to double-check"

Level 3 -- Power user:
  User runs cos map, cos perf, /planning-poker
  Full visibility into the system internals
```

The key: THE SYSTEM NEVER DUMPS ITS FULL CAPABILITY ON THE USER. Features reveal themselves contextually when they are relevant.

### What This Means Concretely

| User Action | What Happens Internally | What the User Sees |
|-------------|------------------------|--------------------|
| "Fix this bug" | Clarification gate scores the prompt. Blast radius estimates scope. Error learning checks for known patterns. Model router picks the cheapest capable model. | The bug gets fixed. |
| "Add authentication" | SDD pipeline suggested. 8 phases orchestrated. Adversarial review runs. Trust score calculated. | A suggestion to plan first, then results delivered in stages. |
| "Why did you pick sonnet?" | Model routing table consulted. Cost data retrieved. | A clear explanation of the cost-performance tradeoff. |
| `cos map trust-score` | System knowledge graph queried. Dependency tree rendered. | Full dependency visualization across all 5 layers. |

---

## Principle 3: The AI Is the Driver

```
Traditional tool:
  User -> reads docs -> configures tool -> uses tool -> gets result

Cognitive OS:
  User -> describes what they want -> AI orchestrates everything -> result
         The AI knows about:
         - 55+ rules (follows them automatically)
         - 12 safety layers (activates them automatically)
         - Model routing (picks the cheapest capable model)
         - Memory (searches Engram before re-exploring)
         - Quality gates (verifies before claiming done)

         The user knows about:
         - What they asked for
         - The result they got
         - Any decisions that need their input
```

### The Implication for Documentation

Traditional tools need extensive user documentation because the user operates the tool. Cognitive OS needs minimal user documentation because the AI operates the tool. The documentation that matters is:

1. **For the user**: What can I ask for? What will I get? (This is `faq.md` and `getting-started.md`.)
2. **For the AI**: How do I operate the OS? (This is rules, skills, hooks -- consumed by the LLM, not the human.)
3. **For contributors**: How do I extend the OS? (This is `how-to-extend.md` and `architecture-principles.md`.)

The user never needs to read `rules/trust-score.md`. The AI reads it and applies it automatically.

---

## Principle 4: Speak Only When Valuable

Every message to the user must pass this test:

1. Does the user NEED to know this? (security block = yes, routine check = no)
2. Does knowing this help them DECIDE something? (model choice = maybe, hook name = no)
3. Is this ACTIONABLE? (suggest alternative = yes, explain internals = no)

### Communication Budget

| Situation | Budget | Example |
|-----------|--------|---------|
| Routine success | 0 tokens (silent) | Hook ran, everything passed -- say nothing |
| Noteworthy event | 1 line | "Switching to a more efficient model for this task." |
| Intervention | 2-3 lines | Warning + suggestion for the user |
| Block | 5+ lines | Explanation + alternative + enough context to unblock |

### What This Means for Agent Output

The responsiveness protocol (see `rules/responsiveness.md`) requires proactive communication -- never appearing stuck. But proactive does not mean verbose. The balance:

- BEFORE a long operation: state what you are doing (1 line)
- DURING: silence unless something noteworthy happens
- AFTER: report the result with concrete numbers, not internal process details
- ON FAILURE: explain what failed and what you will do about it

---

## Principle 5: Cost Transparency Without Noise

The user should be ABLE to see costs, not FORCED to see them.

```
WRONG:
  "Action complete. Cost: $0.03. Tokens: 1,245 in, 387 out.
   Model: sonnet. Context: 42% used. Budget: 87% remaining."
   -- Nobody asked for this on every action

RIGHT:
  (silently tracks everything)
  At session end: "Session cost: $2.34 across 15 actions"
  On demand: user runs `cos perf` for full dashboard
  On threshold: "Budget 80% used -- switching to more efficient models"
```

### When Cost Information Surfaces

| Trigger | What the User Sees |
|---------|-------------------|
| Normal operation | Nothing. Costs tracked silently. |
| Budget threshold (80%) | One-line note about model switching. |
| Budget critical (95%) | Clear warning that capabilities are being reduced. |
| Budget exhausted (100%) | Block with explanation and recovery options. |
| User asks | Full dashboard via `cos perf`. |
| Session end | Summary line with total cost. |

---

## Principle 6: Error Messages Are Teaching Moments

When something goes wrong, do not just report the error -- help the user succeed:

```
BAD:
  "Error: clarification-gate score 72, threshold 60, BLOCKED"

GOOD:
  "I need more details before I can start this task safely.

   Specifically:
   - Which files should I modify?
   - What framework are you using?

   This helps me give you better results faster."
```

### Translation Guide

| Internal Language | User-Facing Language |
|-------------------|---------------------|
| "clarification-gate BLOCK, score 72" | "I need more details before starting." |
| "blast-radius CRITICAL, security keywords detected" | "This change touches security-sensitive code. Let me break it into smaller, safer steps." |
| "confidence-gate BLOCK, trust score 35" | "I am not confident enough in this result to proceed. Here is what I would recommend verifying." |
| "scope-proportionality violation" | "This fix grew larger than expected. Can you confirm you want changes to all 45 files?" |
| "rate-limiter BLOCK, 31/30 tools per minute" | "I am working too fast. Pausing briefly to maintain quality." |
| "assumption-tracker WARNING, 4 assumptions" | "I made several assumptions here. Let me list them so you can confirm." |

---

## Principle 7: The Hood Is Always Available

For users who WANT to understand the internals:

```
"How did you decide to use sonnet instead of opus?"
-> Explain model routing

"What safety checks ran on my last task?"
-> Show the hook chain that fired

"How much did this session cost?"
-> Show cost dashboard

"What would break if I modify this file?"
-> Run cos map
```

The system is transparent ON DEMAND. Never opaque, never overwhelming.

### On-Demand Introspection Tools

| Question | Tool | What It Shows |
|----------|------|---------------|
| "What is the system doing?" | `cos perf` | Cost, token usage, model routing, session metrics |
| "What depends on this?" | `cos map <component>` | Full dependency tree across all 5 architecture layers |
| "Is the system healthy?" | `/cognitive-os-status` | Hooks registered, rules loaded, skills available, metrics state |
| "What happened in past sessions?" | Engram search | Decisions, discoveries, bug fixes from prior sessions |
| "What tests cover this?" | `cos test` | TUI dashboard with color-coded pass/fail and timing |

---

## Anti-Patterns

| Anti-Pattern | Why It Is Bad | What To Do Instead |
|---|---|---|
| "12 hooks executed successfully" | Noise -- user does not care about hook count | Say nothing (success is silent) |
| "WARN: blast-radius HIGH" | Internal jargon -- user does not know what blast-radius means | "This change affects many files. Want me to break it into smaller steps?" |
| Showing the full safety mesh on every task | Overwhelming -- user thinks the tool is paranoid | Only show when intervening |
| Requiring config before first use | Friction -- user leaves before starting | Works with zero config, customize later |
| Dumping metrics in normal output | Irrelevant during work -- relevant in review | Track silently, show in `cos perf` on demand |
| Error messages with hook names and exit codes | Debugging info, not user info | Plain language explanation + suggestion |
| "I ran 55 rules and all passed" | Self-congratulatory noise | Silence. The user assumes things work unless told otherwise. |
| Explaining the architecture unprompted | Nobody asked -- this is a tool, not a lecture | Only explain when the user asks "how" or "why" |

---

## How This Maps to Our Architecture

The 5-layer architecture (see `docs/architecture-principles.md`) maps directly to user visibility:

| Layer | User Visibility | Example |
|---|---|---|
| Rules (Layer 1) | INVISIBLE -- AI follows them automatically | "Do not use AGPL libraries" -- user is never told, AGPL libraries are just never suggested |
| Skills (Layer 2) | CONTEXTUAL -- suggested when relevant | "This is complex, want to use /sdd-new?" |
| Hooks (Layer 3) | SILENT unless intervening | Safety checks run on every action, only speak on issues |
| Libs (Layer 4) | ON DEMAND via CLI tools | `cos perf`, `cos map`, `cos test` |
| Externals (Layer 5) | INVISIBLE -- infrastructure details hidden | Docker services start and stop silently |

### The Visibility Gradient

```
Most visible                                    Least visible
     |                                               |
     v                                               v
  User asks    Intervention    Noteworthy    Silent    Invisible
  (on demand)   (blocks)       (1 line)     (logged)  (automatic)
     |              |              |            |          |
  cos map     confidence     model switch   metrics    rules
  cos perf    gate block                    logging    followed
              rate limit                               hooks pass
```

Inner layers are more invisible. Outer layers have more surface area for user interaction. This mirrors the stability gradient from `architecture-principles.md`: the most stable components (rules) are also the most invisible.

---

## Summary

Seven principles that govern how Cognitive OS communicates with users:

1. **Invisible Safety** -- Safety runs silently. Speak only when intervening.
2. **Progressive Disclosure** -- Features reveal themselves when relevant, not all at once.
3. **The AI Is the Driver** -- The user describes intent. The AI operates the machinery.
4. **Speak Only When Valuable** -- Every message must be needed, helpful for decisions, or actionable.
5. **Cost Transparency Without Noise** -- Track everything silently. Surface on demand or at thresholds.
6. **Error Messages Are Teaching Moments** -- Plain language, not jargon. Explain why and suggest what next.
7. **The Hood Is Always Available** -- Full transparency on demand. Never opaque, never overwhelming.

The north star: the user should feel like they are working with a capable colleague who handles complexity quietly and only interrupts when something genuinely needs their attention.

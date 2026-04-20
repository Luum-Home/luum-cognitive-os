<!-- SCOPE: both -->
---
name: red-team
description: "Red team testing for agent prompts — detects injection, jailbreak, and manipulation vulnerabilities"
triggers: ["/red-team", "/redteam", "/promptfoo"]
audience: os-dev
version: 1.0.0
---

# /red-team

> Run adversarial red team tests against agent prompts using Promptfoo.


## Instructions

Run Promptfoo red team tests against the agent preamble and sample prompts to detect prompt injection, jailbreak, and manipulation vulnerabilities.

### Step 1: Verify Promptfoo Installation

Check if promptfoo is available:

```bash
npx promptfoo@latest --version
```

If not installed, inform the user:
> Promptfoo is not available. Install with: `npm install -g promptfoo` or run via `npx promptfoo@latest`.
> See: scripts/install-promptfoo.sh

### Step 2: Locate Test Configuration

Check for the Promptfoo config file:

```bash
test -f .promptfoo/config.yaml && echo "Config found" || echo "Config missing"
```

If missing, inform the user that `.promptfoo/config.yaml` needs to be created. The default config is included with the Cognitive OS.

### Step 3: Run Red Team Tests

Execute the red team evaluation:

```bash
cd "$CLAUDE_PROJECT_DIR"
npx promptfoo@latest eval --config .promptfoo/config.yaml --output .cognitive-os/metrics/red-team-results.json 2>&1 | tail -30
```

### Step 4: Parse and Report Results

Read the results file and produce a structured report:

1. Count total test cases, passed, and failed
2. Classify failures by category:
   - **Prompt Injection**: Agent followed injected instructions
   - **Jailbreak**: Agent bypassed safety guidelines
   - **Data Exfiltration**: Agent leaked sensitive context
   - **Role Confusion**: Agent adopted an unauthorized persona
   - **Instruction Override**: Agent ignored system prompt constraints

3. Output report in adversarial review format:

```
=== RED TEAM REPORT ===

Total tests: N
Passed: N (X%)
Failed: N (Y%)

### [BLOCKER] {category}: {test description}
**What**: {what the agent did wrong}
**Why**: {security implication}
**Recommendation**: {how to fix the prompt}

=== END RED TEAM REPORT ===
```

### Step 5: Save Results

Save the report to `.cognitive-os/metrics/red-team-results.jsonl`:

```json
{
  "timestamp": "ISO-8601",
  "total_tests": N,
  "passed": N,
  "failed": N,
  "pass_rate": 0.XX,
  "categories": {"prompt_injection": N, "jailbreak": N, ...}
}
```

If failures are found, save key findings to Engram:

```
mem_save(
  title: "Red team findings: {date}",
  type: "discovery",
  scope: "project",
  topic_key: "security/red-team-results",
  content: "{summary of findings with categories and counts}"
)
```

### Step 6: Recommendations

Based on results, suggest:
- For prompt injection failures: strengthen the agent preamble with explicit injection defense
- For jailbreak failures: add more specific refusal patterns to templates
- For data exfiltration: review what context is passed to agents
- For instruction override: reinforce immutable instructions in system prompt

## Success Criteria

- Promptfoo runs without errors
- All test cases execute (no skipped tests)
- Results are saved to metrics JSONL
- Report uses adversarial review format (BLOCKER/CONCERN/SUGGESTION)
- Pass rate is reported with concrete numbers

## References

- GitHub: promptfoo/promptfoo
- Docs: promptfoo.dev
- Related rule: rules/pentesting-readiness.md
- Related rule: rules/security-scanning.md

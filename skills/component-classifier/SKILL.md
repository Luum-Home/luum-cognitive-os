---
name: primitive-classifier
description: 'Use when adding new functionality to determine if it belongs in the
  OS kernel or should be a cos package. Purpose: Classify a new agentic primitive
  (skill, hook, rule, lib) as CORE or PACKAGE.'
allowed-tools:
- Read
- Grep
- Bash
- mcp__plugin_engram_engram__mem_search
audience: os-dev
summary_line: Classify a new agentic primitive (skill, hook, rule, lib) as CORE or
  PACKAGE.
version: 1.0.0
platforms:
- claude-code
prerequisites: []
routing_intents:
- intent: classify_agentic_primitive_scope
  description: User needs to decide whether a new skill, hook, rule, or library helper
    belongs in the OS kernel or should ship as a package.
  confidence: 0.88
- intent: evaluate_core_vs_package_boundary
  description: User is designing new Cognitive OS functionality and needs boundary
    guidance before implementation, not a usage map of existing primitives.
  confidence: 0.84
triggers:
- primitive-classifier
- /primitive-classifier
- Agentic Primitive Classifier
- Classify a new agentic primitive (skill, hook, rule, lib) as CORE or PACKAGE
---
<!-- SCOPE: os-only -->
# Agentic Primitive Classifier

## When to Use
- Before creating a new skill, hook, rule, or lib
- When reviewing PRs that add new agentic primitives
- During restructure to validate classifications

## Classification Criteria

### CORE — Stays in the OS kernel
An agentic primitive is CORE if ANY of these are true:
1. **The OS cannot boot without it** (session-init, crash-recovery)
2. **It enforces fundamental governance** (rate-limiter, content-policy, secret-detector)
3. **It's the package manager itself** (cos CLI, lockfile, security gates)
4. **It manages the OS lifecycle** (cognitive-os-init, cognitive-os-test)
5. **It's required by >50% of other agentic primitives** (model_router, cost_dashboard)

### PACKAGE — Optional add-on
An agentic primitive is PACKAGE if ALL of these are true:
1. **The OS works without it** (removing it doesn't break boot or basic functionality)
2. **It integrates an external tool** (parry, agnix, repomix, hcom)
3. **It serves a specific domain** (security auditing, DevOps, research)
4. **It can be installed/removed independently** (no circular deps with CORE)

### Decision Tree

```
Is the OS broken if this agentic primitive is removed?
├── YES → CORE
└── NO
    ├── Does it integrate an external tool?
    │   ├── YES → PACKAGE
    │   └── NO
    │       ├── Do >50% of agentic primitives depend on it?
    │       │   ├── YES → CORE
    │       │   └── NO → PACKAGE
    │       └── Is it domain-specific (security, DevOps, ML)?
    │           ├── YES → PACKAGE
    │           └── NO → Probably CORE, review with maintainer
```

## Steps

1. **Read the agentic primitive** — understand what it does
2. **Check dependencies** — what depends on it? `grep -rl "{primitive}" hooks/ rules/ skills/ lib/`
3. **Apply decision tree** — walk through the criteria
4. **Check existing audit** — `docs/06-Daily/root/component-audit.md` for precedent
5. **Output classification** with reasoning

## Output Format

```
CLASSIFICATION: {CORE|PACKAGE}
PRIMITIVE: {name}
TYPE: {skill|hook|rule|lib|agent|template}
REASONING: {1-2 sentences}
PACKAGE NAME: {if PACKAGE: @luum/xxx}
DEPENDENCIES: {what this agentic primitive needs}
DEPENDENTS: {what needs this agentic primitive}
```

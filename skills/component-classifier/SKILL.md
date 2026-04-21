<!-- SCOPE: both -->
---
name: component-classifier
description: "Classify a new component (skill, hook, rule, lib) as CORE or PACKAGE. Use when adding new functionality to determine if it belongs in the OS kernel or should be a cos package."
allowed-tools:
  - Read
  - Grep
  - Bash
  - mcp__plugin_engram_engram__mem_search
audience: os-dev
summary_line: "\"Classify a new component (skill, hook, rule, lib) as CORE or PACKAGE."

---

# Component Classifier

## When to Use
- Before creating a new skill, hook, rule, or lib
- When reviewing PRs that add new components
- During restructure to validate classifications

## Classification Criteria

### CORE — Stays in the OS kernel
A component is CORE if ANY of these are true:
1. **The OS cannot boot without it** (session-init, crash-recovery)
2. **It enforces fundamental governance** (rate-limiter, content-policy, secret-detector)
3. **It's the package manager itself** (cos CLI, lockfile, security gates)
4. **It manages the OS lifecycle** (cognitive-os-init, cognitive-os-test)
5. **It's required by >50% of other components** (model_router, cost_dashboard)

### PACKAGE — Optional add-on
A component is PACKAGE if ALL of these are true:
1. **The OS works without it** (removing it doesn't break boot or basic functionality)
2. **It integrates an external tool** (parry, agnix, repomix, hcom)
3. **It serves a specific domain** (security auditing, DevOps, research)
4. **It can be installed/removed independently** (no circular deps with CORE)

### Decision Tree

```
Is the OS broken if this component is removed?
├── YES → CORE
└── NO
    ├── Does it integrate an external tool?
    │   ├── YES → PACKAGE
    │   └── NO
    │       ├── Do >50% of components depend on it?
    │       │   ├── YES → CORE
    │       │   └── NO → PACKAGE
    │       └── Is it domain-specific (security, DevOps, ML)?
    │           ├── YES → PACKAGE
    │           └── NO → Probably CORE, review with maintainer
```

## Steps

1. **Read the component** — understand what it does
2. **Check dependencies** — what depends on it? `grep -rl "{component}" hooks/ rules/ skills/ lib/`
3. **Apply decision tree** — walk through the criteria
4. **Check existing audit** — `docs/component-audit.md` for precedent
5. **Output classification** with reasoning

## Output Format

```
CLASSIFICATION: {CORE|PACKAGE}
COMPONENT: {name}
TYPE: {skill|hook|rule|lib|agent|template}
REASONING: {1-2 sentences}
PACKAGE NAME: {if PACKAGE: @luum/xxx}
DEPENDENCIES: {what this component needs}
DEPENDENTS: {what needs this component}
```

# Migration inventory: components → agentic primitives

Generated: 2026-04-29
Total hits scanned: 116
Class A (migrate): 64
Class B (keep): 15
Class C (keep): 31
Ambiguous: 6

Status update: 2026-04-30 — migrated the clear Class A occurrences in
active docs, skill contracts, package-manager surfaces, runtime messages,
manifests, and selected archive/business docs. Remaining tracked uses of
`component` should be treated as one of: generic software terminology
(UI, infrastructure, K8s, test-pyramid layers), proper nouns/filenames
(`component-classifier`, `component-scope-classification.md`,
`component_usage_tracker`), or separate rename work that needs backwards
compatibility.

---

## File: AGENTS.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 13 | "universal OS **components** in `hooks/`, `rules/`, `skills/`" | A | "universal OS agentic primitives in `hooks/`, `rules/`, `skills/`" |
| 19 | `| Component | Location | Purpose |` (table header where rows are hooks, rules, skills, memory, MCP) | A | `| Primitive | Location | Purpose |` |
| 55 | "### Carve-out: '**component**' remains valid" (policy section — the heading itself) | B | (no change — this heading announces the carve-out policy; renaming it would contradict the carve-out) |
| 57 | `"Component" is **not** banned — it is reserved for generic software-engineering contexts` | B | (no change — this is the policy statement defining the exception) |
| 59 | "UI/frontend **components** (React, Vue, Web Components)" | B | (no change — explicitly listed as a valid generic use) |
| 60 | "Microservice **components** in a service mesh" | B | (no change — explicitly listed carve-out) |
| 61 | "Build or test **components** (pytest component, Makefile component)" | B | (no change — explicitly listed carve-out) |
| 62 | "Third-party library **components**" | B | (no change — explicitly listed carve-out) |
| 64 | "Writing 'OS **component**' when the referent is a skill or hook is imprecise" | A | "Writing 'OS agentic primitive' when the referent is a skill or hook is imprecise" — wait: this sentence is *teaching* the correct term, not using "component" to mean a primitive. Keep as-is; it is part of the migration rationale itself. | AMBIGUOUS |
| 68 | `tests/audit/test_vocabulary_agentic_primitives.py` will flag "OS **component**" as a drift violation | B | (no change — this is a string literal describing the drift condition to detect) |

---

## File: README.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 8 | `![REAL Components](…real-components.json)` badge URL/alt-text | AMBIGUOUS | Badge label tracks the REAL/DORMANT/UNWIRED metric (a health score for the OS's agentic primitives). Could become "REAL Primitives". Pending badge URL alignment — mark ambiguous until badge infra is updated. |

---

## File: CHANGELOG.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 17 | "compare canonical Cognitive OS **components** against Claude/Codex driver projections" | A | "compare canonical Cognitive OS agentic primitives against Claude/Codex driver projections" |
| 104 | "all 12 procedural sections (stack detection, mode **components**, dir structure, rules/hooks/skills install…)" | C | (no change — "mode components" refers to procedural install sections, not agentic primitives) |
| 308 | "`/component-reality-check` — drill-down into REAL/DORMANT/ASPIRATIONAL/METADATA classification" | AMBIGUOUS | Skill name is a proper noun/slash-command. The description is agentic (skills, hooks, rules). Keep skill name; description could say "drill-down into REAL/DORMANT classification of agentic primitives". |
| 384 | "checking **component** wiring" | A | "checking agentic primitive wiring" |
| 655 | "4 **components** identified for reclassification to packages/" | A | "4 agentic primitives identified for reclassification to packages/" |
| 724 | "System Knowledge Graph: 232 **components**, 430 edges" | A | "System Knowledge Graph: 232 agentic primitives, 430 edges" |
| 731 | "**Component** Linter: overlap detection, size warnings, registration checks" | A | "Primitive Linter: overlap detection, size warnings, registration checks" |

---

## File: .claude/plugins/hermes-agent/AGENTS.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| (no hits) | — | — | — |

---

## File: .claude/plugins/pi-mono/AGENTS.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 64 | `│   ├── src/components/      # Ink components (branding, markdown, prompts, pickers, etc.)` | B | (no change — React/Ink UI components, explicitly carved out) |
| 216 | `| Surface | Ink component | Gateway method |` | B | (no change — table header for Ink UI framework components) |

---

## File: cmd/cos/README.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 3 | "A package manager for AI agent **components**: skills, rules, hooks, agents, and templates." | A | "A package manager for agentic primitives: skills, rules, hooks, agents, and templates." |
| 7 | "`cos` manages the lifecycle of reusable AI agent **components**." | A | "`cos` manages the lifecycle of reusable agentic primitives." |
| 108 | `\| \`cos map [component]\` \| Show the system knowledge graph \|` | A | `\| \`cos map [primitive]\` \| Show the system knowledge graph \|` (also update the CLI flag/arg if applicable) |

---

## File: skills/CATALOG-COMPACT.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 37 | `component-classifier` skill entry: "Classify a new **component** (skill, hook, rule, lib) as CORE or PACKAGE." | A | "Classify a new agentic primitive (skill, hook, rule, lib) as CORE or PACKAGE." |
| 38 | `component-reality-check` skill entry: "Classify every SO **component** into REAL / DORMANT / UNWIRED / METADATA" | A | "Classify every SO agentic primitive into REAL / DORMANT / UNWIRED / METADATA" |
| 43 | `harness-audit`: "Evaluate harness **components** (hooks, rules, skills) for continued relevance." | A | "Evaluate harness agentic primitives (hooks, rules, skills) for continued relevance." |
| 73 | `cognitive-os-status`: "Full health check of all Cognitive OS **components**" | A | "Full health check of all Cognitive OS agentic primitives" |

---

## File: skills/CATALOG.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 20 | `component-classifier`: "Classify new **components** as CORE or PACKAGE" | A | "Classify new agentic primitives as CORE or PACKAGE" |
| 25 | `harness-audit`: "Evaluate harness **components** for relevance, identify retirement candidates" | A | "Evaluate harness agentic primitives for relevance, identify retirement candidates" |
| 210 | `cognitive-os-status`: "Full health check of all Cognitive OS **components**" | A | "Full health check of all Cognitive OS agentic primitives" |
| 213 | `component-classifier` description: "Classify a new **component** (skill, hook, rule, lib) as CORE or PACKAGE." | A | "Classify a new agentic primitive (skill, hook, rule, lib) as CORE or PACKAGE." |
| 214 | `component-reality-check` description: "Measure declared-but-unwired vs real **components** of the SO" | A | "Measure declared-but-unwired vs real agentic primitives of the SO" |
| 242 | `harness-audit`: "Evaluate harness **components** (hooks, rules, skills) for continued relevance." | A | "Evaluate harness agentic primitives (hooks, rules, skills) for continued relevance." |

---

## File: docs/architecture/FROZEN-BACKLOG.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 34 | "**Components** that already exist (Apache-2.0):" (listing hooks for engram sync package) | A | "Agentic primitives that already exist (Apache-2.0):" |
| 59 | "581 **components** classified: 126 CORE, 453 EXTENSION, 2 REMOVE" | A | "581 agentic primitives classified: 126 CORE, 453 EXTENSION, 2 REMOVE" |
| 64 | "141 commits…added many **components** directly to root. Some are core…but others are extensions" | A | "141 commits…added many agentic primitives directly to root." |
| 245 | `## COMPONENTS WAITING FOR ACTIVATION` (section heading, items are hooks) | A | `## AGENTIC PRIMITIVES WAITING FOR ACTIVATION` |

---

## File: docs/architecture/LESSONS-LEARNED.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 17 | "not enough when you're shipping 60+ **components**. Each one can have invisible degradation." | A | "not enough when you're shipping 60+ agentic primitives. Each one can have invisible degradation." |
| 19 | "When a session produces >20 new **components** without benchmarking." | A | "When a session produces >20 new agentic primitives without benchmarking." |
| 34 | "353 aspirational **components** discovered in the audit" | A | "353 aspirational agentic primitives discovered in the audit" |
| 122 | "More than 10 **components** added in a single commit" | A | "More than 10 agentic primitives added in a single commit" |

---

## File: docs/architecture/POST-MORTEM-2026-04.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 13 | "The Cognitive OS grew from zero to 375+ **components** in 18 days." | A | "The Cognitive OS grew from zero to 375+ agentic primitives in 18 days." |
| 56 | "353 aspirational **components** cataloged" | A | "353 aspirational agentic primitives cataloged" |
| 142 | "Aspirational **components**: 353+ undocumented" | A | "Aspirational agentic primitives: 353+ undocumented" |
| 150 | "Aspirational **components**: 0 of the discovered 353 remain" | A | "Aspirational agentic primitives: 0 of the discovered 353 remain" |
| 207 | "if you can generate 60 **components** in one commit, you need automated checks" | A | "if you can generate 60 agentic primitives in one commit, you need automated checks" |
| 236 | "Documentation of **components** is uneven — many skills/hooks/libs still have stale docs" | A | "Documentation of agentic primitives is uneven — many skills/hooks/libs still have stale docs" |
| 263 | "353 aspirational **components**, 67 false tests, three wrong audits" | A | "353 aspirational agentic primitives, 67 false tests, three wrong audits" |

---

## File: docs/adrs/ADR-006-agpl-license-compliance.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 14 | "Replace all AGPL-licensed infrastructure **components** with permissively-licensed alternatives" | C | (no change — refers to Redis, MinIO: external infrastructure services, not agentic primitives) |
| 21 | "block AGPL/SSPL/GPL dependencies for any **component** distributed with the OS" | C | (no change — "component" here means any software dependency/package, generic software use) |
| 31 | "All infrastructure **components** are now MIT, Apache 2.0, or BSD-3 licensed" | C | (no change — refers to Redis/Valkey, MinIO/SeaweedFS infrastructure) |

---

## File: docs/adrs/ADR-009-package-architecture.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 10 | "Cognitive OS had grown to 375+ **components** (72+ skills, 55+ rules, 57+ hooks, 40+ libs)" | A | "Cognitive OS had grown to 375+ agentic primitives (72+ skills, 55+ rules, 57+ hooks, 40+ libs)" |
| 14 | "Perform a full audit of every **component** and restructure the codebase into CORE and PACKAGE" | A | "Perform a full audit of every agentic primitive and restructure the codebase into CORE and PACKAGE" |
| 16 | "**CORE (82 components)**: 9 skills, 24 hooks, 38 rules, 8 libs, 3 templates, plus the Go CLI." | A | "**CORE (82 agentic primitives)**: 9 skills, 24 hooks, 38 rules, 8 libs, 3 templates, plus the Go CLI." |
| 17 | "**PACKAGE (227 components)**: 93 skills, 41 hooks, 44 rules, 41 libs, 3 agents, 5 templates." | A | "**PACKAGE (227 agentic primitives)**: 93 skills, 41 hooks, 44 rules, 41 libs, 3 agents, 5 templates." |
| 31 | "Add metadata tags to **components** instead of moving files." | A | "Add metadata tags to agentic primitives instead of moving files." |
| 33 | "AI agent **components** (skills, hooks, rules) don't fit the file structure assumptions of language-specific package managers." | A | "agentic primitives (skills, hooks, rules) don't fit the file structure assumptions of language-specific package managers." |
| 37 | "Only 22% of **components** are truly CORE; 78% are optional." | A | "Only 22% of agentic primitives are truly CORE; 78% are optional." |

---

## File: docs/adrs/ADR-017-stabilization-freeze.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 10 | "the OS had accumulated 375+ **components** but many were not wired into the running system" | A | "the OS had accumulated 375+ agentic primitives but many were not wired into the running system" |
| 10b | "Each session added new **components** but the wiring rate was declining" | A | "Each session added new agentic primitives but the wiring rate was declining" |
| 10c | "**components** were built but could not be trusted to work" | A | "agentic primitives were built but could not be trusted to work" |
| 22 | "Health checks confirming **components** work at runtime, not just at import time." | A | "Health checks confirming agentic primitives work at runtime, not just at import time." |
| 25 | "Wiring validator hook: detects unregistered **components** at commit time." | A | "Wiring validator hook: detects unregistered agentic primitives at commit time." |
| 27 | "**Component** usage tracker: identifies dead weight **components**." | A | "Primitive usage tracker: identifies dead-weight agentic primitives." |
| 31 | "Each new feature adds **components** that need wiring." | A | "Each new feature adds agentic primitives that need wiring." |
| 32 | "many unwired **components** are valuable — they just need connection points." | A | "many unwired agentic primitives are valuable — they just need connection points." |
| 39 | "once wired, **components** cannot silently become unwired." | A | "once wired, agentic primitives cannot silently become unwired." |
| 41 | "building **components** is easy, wiring them into a working system is the hard part." | A | "building agentic primitives is easy, wiring them into a working system is the hard part." |

---

## File: docs/adrs/ADR-019-scope-tagging.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 10 | "Cognitive OS **components** serve two distinct audiences" | A | "Cognitive OS agentic primitives serve two distinct audiences" |
| 10b | "`self-install.sh` and `cos install` installed all **components** everywhere" | A | "`self-install.sh` and `cos install` installed all agentic primitives everywhere" |
| 10c | "OS-internal tools like `register-component` or `release-os` were being deployed into user projects" | A | "OS-internal tools like `register-primitive` or `release-os` were being deployed…" — NOTE: `register-component` is a script name (proper noun); only the surrounding prose should change: "OS-internal agentic primitives like `register-component` or `release-os`…" |
| 14 | "Add scope tags to all **components** across three categories" | A | "Add scope tags to all agentic primitives across three categories" |
| 16 | "`os-only`: Internal to the OS…Examples: release-os, register-component, wiring-validator, component-classifier." | A | "`os-only`: Internal to the OS agentic primitives…" (names remain as proper nouns) |
| 27 | "The scope classification was deferred during the initial rules-to-hooks plan" | — | No "component" on this line — skip |
| 31 | "Move os-only **components** to an `internal/` directory." | A | "Move os-only agentic primitives to an `internal/` directory." |
| 32 | "Check scope at execution time and skip inapplicable **components**." | A | "Check scope at execution time and skip inapplicable agentic primitives." |
| 33 | "Let users see all **components**." | A | "Let users see all agentic primitives." |
| 37 | "`self-install.sh` can filter **components** by scope during installation" | A | "`self-install.sh` can filter agentic primitives by scope during installation" |
| 40 | "many **components** lacked clear audience boundaries, forcing explicit classification decisions for all 375+ **components**." | A | "many agentic primitives lacked clear audience boundaries, forcing explicit classification decisions for all 375+ agentic primitives." |

---

## File: docs/adrs/ADR-020-contamination-fix.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 10 | "some **components** accumulated project-specific references" | A | "some agentic primitives accumulated project-specific references" |
| 14 | "remove all project-specific contamination from OS **components**" | A | "remove all project-specific contamination from OS agentic primitives" |
| 19 | "Ensure all OS **components** work generically across any project" | A | "Ensure all OS agentic primitives work generically across any project" |
| 34 | "All OS **components** became truly generic and reusable across projects." | A | "All OS agentic primitives became truly generic and reusable across projects." |
| 38 | "validates that os-only **components** do not reference project-specific paths." | A | "validates that os-only agentic primitives do not reference project-specific paths." |

---

## File: docs/adrs/ADR-021-vendor-agnostic-with-adapters.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 90 | "Existing OS **components** stay as-is. Adapters are added incrementally" | A | "Existing OS agentic primitives stay as-is. Adapters are added incrementally" |
| 98 | `| OS component | Claude Code equivalent | Status |` table header | A | `| OS primitive | Claude Code equivalent | Status |` |

---

## File: docs/adrs/ADR-026-r2-r3-design-review.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 252 | "Defer schema validation (Option C **components**) to a future ADR?" | C | (no change — "Option C components" are config loader code modules in a Go refactor decision, generic software architecture) |

---

## File: docs/adrs/ADR-026a-decisions.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 104 | "D2.4 — Defer schema validation (Option C **components**) to a future ADR?" | C | (no change — same as ADR-026; refers to code architecture modules) |
| 107 | same quoted question | C | (no change) |

---

## File: docs/adrs/README.md  <!-- moved 2026-04-30 (ADR-087); architecture/adrs/README.md removed 2026-05-12 -->

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 18 | ADR title: "Package Architecture -- 375 **Components** Reclassified" | A | "Package Architecture -- 375 Agentic Primitives Reclassified" |
| 28 | ADR title: "Scope Tagging -- **Component** Audience Classification" | A | "Scope Tagging -- Agentic Primitive Audience Classification" |

---

## File: docs/architecture/behavioral-test-contracts.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 89 | `## Operational Component` (section heading; content is the `test-contract-repair` skill) | A | `## Operational Agentic Primitive` |

---

## File: docs/architecture/bootstrap-portability.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 145 | "secondary user-facing scripts such as `component-lint.sh`, `startup-benchmark.sh`…" | AMBIGUOUS | `component-lint.sh` is a script filename (proper noun). The sentence is describing the script by name — cannot rename here. Mark as proper-noun reference; no prose change needed, but the script itself could be renamed `primitive-lint.sh` in a separate pass. |

---

## File: docs/architecture/core-vs-extensions-audit-2026-04-20.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 9 | `| Surface | Components | File count | Target at v1.0 | Feasibility |` (table header) | A | `| Surface | Primitives | File count | Target at v1.0 | Feasibility |` |
| 17 | "126 CORE **components** of 581 total = **22% core, 78% extensions/remove**" | A | "126 CORE agentic primitives of 581 total = 22% core, 78% extensions/remove" |
| 49 | `| component | current path | class | new path | reason |` (table header column) | A | `| primitive | current path | class | new path | reason |` |
| 124 | `| component | current path | class | reason |` (table header column) | A | `| primitive | current path | class | reason |` |
| 239 | "`harness-audit`, `component-classifier`, `audit-website`, `trust-audit` → cos-verification-audit" | A | Script names are proper nouns. Surrounding prose does not use "component" here — no change needed. |
| 256 | "…`component-lint.sh`…" (list of scripts in migration plan) | AMBIGUOUS | `component-lint.sh` is a filename/proper noun. The list is a migration plan item; rename the file separately. No prose change here. |
| 262 | `| component | reason |` (table header column) | A | `| primitive | reason |` |
| 282 | "Every **component** has a class. Zero 'unclassified'." | A | "Every agentic primitive has a class. Zero 'unclassified'." |

---

## File: docs/architecture/core-vs-extensions-migration-plan.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 174 | "`docs/patterns/{plan-first,dogfooding,os-vs-project,ecosystem-tools,component-classification…}` (via `git mv`)" | A | Reference to a filename `component-classification.md` — proper noun (file path). The prose does not use "component" generically here. No prose change; the file rename is a separate task. |

---

## File: docs/architecture/cos-dispatch/README.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 38 | `## Component Architecture` (section heading for the cos-dispatch binary's internal Go package structure) | C | (no change — this documents the software architecture of a Go binary, not agentic primitives) |

---

## File: docs/architecture/cos-dispatch/adr-detection.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 11 | `### Component: ADRDetector` (Go module/type heading) | C | (no change — Go software architecture subsystem label) |
| 152 | `### Component: ADRGenerator` (Go module/type heading) | C | (no change — Go software architecture subsystem label) |

---

## File: docs/architecture/cos-dispatch/adrs/002-transformer-separate-interface.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 28 | "A **component** that needs both validation and transformation implements both interfaces" | C | (no change — refers to a Go struct implementing two interfaces; generic software architecture) |

---

## File: docs/architecture/cos-dispatch/test-strategy.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 21 | `| **Component** |` (test layer name — "Component tests" as opposed to "Unit tests" / "Integration tests") | C | (no change — this is the standard software test pyramid terminology) |
| 25 | "**Component** tests catch driver, schema, and connection-pool issues" | C | (no change — test pyramid terminology) |
| 38 | `- [ ] **Component**: tracker_test.go opens a real SQLite file` | C | (no change — test layer label) |
| 42 | `- [ ] **Component**: eager failure_sequences` | C | (no change — test layer label) |
| 79 | `- [ ] **Component**: after generation, generated_artifacts contains a row` | C | (no change — test layer label) |
| 167 | "DO NOT use `:memory:` for **Component**, Integration, or Binary layer tests." | C | (no change — test pyramid terminology) |

---

## File: docs/architecture/cos-update-vs-cos-cli-responsibility-analysis.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 16 | `## Components Inspected` (section heading listing two scripts for analysis) | C | (no change — "Components Inspected" is a generic analysis heading for two bash scripts) |
| 41 | "Package manager for reusable AI agent **components**." | A | "Package manager for reusable agentic primitives." |

---

## File: docs/architecture/cos-vs-project-overlap-analysis.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 7 | `| reference-project Component | COS Equivalent | Overlap | Owner |` (table header) | C | (no change — "reference-project Component" is a proper column referencing UI/feature components from a reference project, including frontend commands) |
| 13 | "`/plan-design-system-component`" | B | (no change — this is a slash-command name for Atomic Design/Storybook UI component planning) |

---

## File: docs/architecture/cross-harness-authoring.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 52 | "new **components** look portable in theory while staying tied to one file layout" | A | "new agentic primitives look portable in theory while staying tied to one file layout" |
| 57 | "Every significant **component** should be split mentally into two layers." | A | "Every significant agentic primitive should be split mentally into two layers." |
| 61 | "The stable meaning of the **component**:" | A | "The stable meaning of the agentic primitive:" |
| 99 | "Use these states when evaluating a feature or **component**." | A | "Use these states when evaluating a feature or agentic primitive." |
| 163 | "Before calling a new **component** portable, verify:" | A | "Before calling a new agentic primitive portable, verify:" |
| 184 | "Is this **component** authored once at the behavioral level?" | A | "Is this agentic primitive authored once at the behavioral level?" |

---

## File: docs/architecture/cross-platform-ci.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 8 | "The gate has four **components**:" | C | (no change — refers to CI gate sub-systems: shell linter, Docker, smoke suite, Makefile targets) |
| 10 | `| Component | Purpose |` table header (items are lint script, smoke script, Dockerfile, Makefile) | C | (no change — CI infrastructure components) |

---

## File: docs/architecture/cross-runtime-portability.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 13 | `| Component | Count | Coupling | Notes |` table header (items: Rules, Skills, Hooks, Settings, Event names) | A | `| Primitive | Count | Coupling | Notes |` |
| 25 | `| Component | Issue | Fix |` table header (items: settings.json, Hook event names — agentic layer) | A | `| Primitive | Issue | Fix |` |

---

## File: docs/architecture/functional-audit/f1-cleanup.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 32 | "…`docs/component-audit.md`, and others" | A | Filename reference. The document being cited is an audit of agentic components — rename the file in a separate pass. No prose change here beyond the filename. |

---

## File: docs/architecture/functional-audit/scorecard-install-scripts.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 148 | "extend `test_uninstall_removes_cos_components` or add a new regression test" | A | "extend `test_uninstall_removes_cos_primitives` or add a new regression test" — NOTE: this changes a test function name; coordinate with actual test rename in `tests/`. |

---

## File: docs/architecture/functional-audit/scorecard-rules.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 116 | "`component-classification.md`" (in a list of contextual rule filenames) | A | `component-classification.md` is a filename/proper noun. The rule itself can be renamed `primitive-classification.md`; prose here does not need rewriting, only a file rename tracked separately. |

---

## File: docs/architecture/functional-audit/scorecard-skills.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 54 | "`component-classifier`" in a comma-separated skill list | A | Proper noun (skill name). The skill itself can be renamed; prose here is a list of names. |

---

## File: docs/architecture/functional-audit/sprint-2a-orphan-fate.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 102 | "`component-classification.md` \| Taxonomy reference (CORE vs PACKAGE)" | A | Filename reference; rename the file in a separate pass. |
| 174 | "`component-classification.md`" in a git-mv list | A | Filename reference; rename the file in a separate pass. |

---

## File: docs/architecture/functional-audit/startup-baseline-2026-04-20.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 50 | `| Component | Bytes | Est. Tokens | Notes |` table header (items: CLAUDE.md, rules, skills catalog) | A | `| Primitive | Bytes | Est. Tokens | Notes |` |

---

## File: docs/architecture/harness-adoption-gap/scripts-audit-A-root-installers.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 22 | "delegates all **component** sync to `cos-init.sh --standard`" | A | "delegates all agentic primitive sync to `cos-init.sh --standard`" |

---

## File: docs/architecture/harness-adoption-gap/scripts-audit-C-updaters.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 187 | "# Remove ONLY COS-managed **components** (namespaced under cos/)." | A | "# Remove ONLY COS-managed agentic primitives (namespaced under cos/)." — NOTE: this is a comment inside a quoted bash block. |

---

## File: docs/architecture/harness-adoption-gap/scripts-audit-D-profile-uninstall.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 34 | "extend `test_uninstall_removes_cos_components` or add a new regression test" | A | "extend `test_uninstall_removes_cos_primitives` or add a new regression test" — NOTE: test function rename; coordinate with tests/. |

---

## File: docs/architecture/memory-lifecycle.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 86 | `| Purpose | Component | Output / Effect |` (Save Surfaces table header; items are hooks, libs) | A | `| Purpose | Primitive | Output / Effect |` |
| 97 | `| Purpose | Component | Output / Effect |` (Recovery Surfaces table header; items are hooks, libs) | A | `| Purpose | Primitive | Output / Effect |` |
| 107 | `| Purpose | Component | Contract |` (Protection Surfaces table header; items are libs) | A | `| Purpose | Primitive | Contract |` |

---

## File: docs/architecture/observability-backend-evaluation-2026-04-24.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 82 | "prefer permissive, lightweight, local-first **components**" (referring to MLflow, Langfuse, Valkey) | C | (no change — refers to third-party observability tools/services; infrastructure context) |

---

## File: docs/architecture/path-portability-and-privacy.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 8 | "state into AI-facing **components**." | A | "state into AI-facing agentic primitives." |
| 63 | "Projects that install Cognitive OS inherit the same rule: AI-facing **components** such as hooks, skills, rules, docs, MCP config snippets, and tests" | A | "AI-facing agentic primitives such as hooks, skills, rules, docs, MCP config snippets, and tests" |
| 68 | "consumer project before committing AI **components**." | A | "consumer project before committing agentic primitives." |

---

## File: docs/architecture/plans-reconciliation-2026-04-21.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 17 | "`component-scope-classification.md` \| SUPERSEDED \| …\| 506+ **components** tagged, filter wired." | A | "506+ agentic primitives tagged, filter wired." (and rename `component-scope-classification.md` → `primitive-scope-classification.md` in a separate pass) |
| 27 | "Three pillars…all have shipped **components** + ADR." | AMBIGUOUS | "shipped components" here could mean "shipped implementation pieces" in a generic software sense (truncation, cache, payload are not skills/hooks/rules). Mark ambiguous — could be C (code modules) or A (if they include hook implementations). Needs author confirmation. |

---

## File: docs/architecture/project-consumption-patterns.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 48 | "`ui-ux-architecture.md` # Component architecture (Opus)" | B | (no change — refers to UI/UX component architecture for Atomic Design/Storybook in a reference project) |

---

## File: docs/architecture/stabilization-roadmap.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 59 | "Stale references to deleted **components**: no active docs contamination found" | A | "Stale references to deleted agentic primitives: no active docs contamination found" |
| 109 | "Aspirational **components** \| ~150 \| <20" | A | "Aspirational agentic primitives \| ~150 \| <20" |

---

## File: docs/architecture/tooling-stack-rationalization.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 101 | "Does this duplicate logic already provided by another **component**?" | C | (no change — checklist question about any tool/library in the tech stack; generic software) |

---

## File: docs/architecture/why-skills-and-rules-became-claude-centered.md

| Line | Context | Class | Proposed rewrite (Class A only) |
|---|---|---|---|
| 66 | "`.cognitive-os/` for universal OS **components**" | A | "`.cognitive-os/` for universal OS agentic primitives" |

---

## Summary by class

### Class A — to migrate (64)

High-density files:
- `docs/adrs/ADR-019-scope-tagging.md` — 10 hits (every occurrence of "component" refers to skills/hooks/rules)
- `docs/adrs/ADR-017-stabilization-freeze.md` — 10 hits (wiring, registration, lifecycle of OS primitives)
- `docs/adrs/ADR-009-package-architecture.md` — 7 hits (375 skills/hooks/rules/libs reclassification)
- `docs/architecture/POST-MORTEM-2026-04.md` — 7 hits (aspirational hooks/skills/rules count)
- `docs/adrs/ADR-020-contamination-fix.md` — 5 hits (OS hooks/skills/rules contamination)
- `docs/adrs/ADR-021-vendor-agnostic-with-adapters.md` — 2 hits (OS primitives + table header)
- `docs/architecture/cross-harness-authoring.md` — 6 hits (portability of skills/hooks/rules)
- `AGENTS.md` — 2 prose hits (architecture table + description)
- `CHANGELOG.md` — 5 hits (primitive counts, wiring, linter)
- `cmd/cos/README.md` — 3 hits (cos manages skills/hooks/rules/agents)
- `skills/CATALOG-COMPACT.md` and `skills/CATALOG.md` — 10 hits combined (skill descriptions)
- `docs/architecture/memory-lifecycle.md` — 3 hits (table headers for hooks/libs)
- `docs/architecture/path-portability-and-privacy.md` — 3 hits (hooks, skills, rules, docs)

Selected list:
- AGENTS.md:13 — "universal OS components"
- AGENTS.md:19 — Architecture table header
- CHANGELOG.md:17 — Canonical OS components (harness parity)
- CHANGELOG.md:384 — component wiring
- CHANGELOG.md:655 — 4 components for reclassification
- CHANGELOG.md:724 — Knowledge Graph component count
- CHANGELOG.md:731 — Component Linter
- cmd/cos/README.md:3 — AI agent components: skills, rules, hooks
- cmd/cos/README.md:7 — lifecycle of reusable AI agent components
- cmd/cos/README.md:108 — `cos map [component]`
- skills/CATALOG-COMPACT.md:37,38,43,73 — skill description text
- skills/CATALOG.md:20,25,210,213,214,242 — skill description text
- docs/architecture/FROZEN-BACKLOG.md:34,59,64,245 — primitives/backlog items
- docs/architecture/LESSONS-LEARNED.md:17,19,34,122 — lesson data points
- docs/architecture/POST-MORTEM-2026-04.md:13,56,142,150,207,236,263 — mortem metrics
- docs/adrs/ADR-009-package-architecture.md:10,14,16,17,31,33,37 — all hits
- docs/adrs/ADR-017-stabilization-freeze.md:10,22,25,27,31,32,39,41 — all hits
- docs/adrs/ADR-019-scope-tagging.md:10,14,16,31,32,33,37,40 — all hits
- docs/adrs/ADR-020-contamination-fix.md:10,14,19,34,38 — all hits
- docs/adrs/ADR-021-vendor-agnostic-with-adapters.md:90,98 — all hits
- docs/adrs/README.md:18,28 (was docs/architecture/adrs/README.md, removed 2026-05-12) — ADR titles
- docs/architecture/behavioral-test-contracts.md:89 — section heading
- docs/architecture/core-vs-extensions-audit-2026-04-20.md:9,17,49,124,262,282 — table headers + prose
- docs/architecture/cos-update-vs-cos-cli-responsibility-analysis.md:41 — package manager description
- docs/architecture/cross-harness-authoring.md:52,57,61,99,163,184 — all hits
- docs/architecture/cross-runtime-portability.md:13,25 — table headers
- docs/architecture/functional-audit/startup-baseline-2026-04-20.md:50 — table header
- docs/architecture/harness-adoption-gap/scripts-audit-A-root-installers.md:22 — component sync
- docs/architecture/harness-adoption-gap/scripts-audit-C-updaters.md:187 — comment in bash block
- docs/architecture/harness-adoption-gap/scripts-audit-D-profile-uninstall.md:34 — test function reference
- docs/architecture/memory-lifecycle.md:86,97,107 — table headers
- docs/architecture/path-portability-and-privacy.md:8,63,68 — AI-facing components
- docs/architecture/stabilization-roadmap.md:59,109 — stale refs + aspirational count
- docs/architecture/why-skills-and-rules-became-claude-centered.md:66 — universal OS components

### Class B — keep (15)

All instances in `AGENTS.md:55–68` where "component" is used in the carve-out policy definition itself (the policy explaining when "component" remains valid), plus:
- `.claude/plugins/pi-mono/AGENTS.md:64,216` — Ink UI framework components (React/Ink)
- `docs/architecture/cos-vs-project-overlap-analysis.md:13` — `/plan-design-system-component` slash-command (Atomic Design)
- `docs/architecture/project-consumption-patterns.md:48` — "Component architecture (Opus)" for UI/UX in a reference project

### Class C — keep (31)

Grouped by reason:

**Infrastructure/dependencies** (ADR-006, observability):
- `docs/adrs/ADR-006-agpl-license-compliance.md:14,21,31` — Redis, MinIO, software licensing
- `docs/architecture/observability-backend-evaluation-2026-04-24.md:82` — MLflow, Langfuse, Valkey
- `docs/architecture/tooling-stack-rationalization.md:101` — generic tool duplication checklist

**Go software architecture** (cos-dispatch):
- `docs/architecture/cos-dispatch/README.md:38` — Go binary component diagram
- `docs/architecture/cos-dispatch/adr-detection.md:11,152` — Go type headings (ADRDetector, ADRGenerator)
- `docs/architecture/cos-dispatch/adrs/002-transformer-separate-interface.md:28` — Go interface pattern
- `docs/adrs/ADR-026-r2-r3-design-review.md:252` — config loader code modules
- `docs/adrs/ADR-026a-decisions.md:104,107` — config loader code modules

**Test pyramid terminology** (cos-dispatch/test-strategy.md):
- Lines 21, 25, 38, 42, 79, 167 — "Component test" as test layer name (Unit/Component/Integration/Binary)

**CI gate sub-systems** (cross-platform-ci.md):
- Lines 8, 10 — lint script, Docker, smoke suite, Makefile: CI infrastructure

**Procedural install sections** (CHANGELOG.md:104):
- "mode components" = 12 procedural sections in `cos-init.sh`, not agentic primitives

**Generic analysis heading** (cos-update-vs-cos-cli-responsibility-analysis.md:16):
- "## Components Inspected" heading for two bash scripts under analysis

**Table column for a reference-project's features** (cos-vs-project-overlap-analysis.md:7):
- Column header grouping frontend commands and UI features

### Ambiguous (6)

- `AGENTS.md:64` — The sentence teaches the correct term ("OS component" → "OS primitive") but uses "OS component" as the thing to avoid. Keeping the sentence is the right call; it is part of the migration rationale, not a drift violation.
- `README.md:8` — "REAL Components" badge. Badge label tracks health of agentic primitives but is also a metric name that may be referenced in badge JSON URLs. Migrating requires coordinating badge infrastructure.
- `CHANGELOG.md:308` — `/component-reality-check` skill name in a description. The skill name is a proper noun; the description text around it is migratable, but the slash-command itself needs a rename tracked separately.
- `docs/architecture/bootstrap-portability.md:145` — `component-lint.sh` filename in a sentence listing scripts. Prose references a proper noun; the file rename is a separate task.
- `docs/architecture/core-vs-extensions-audit-2026-04-20.md:256` — `component-lint.sh` in a migration plan list. Same as above.
- `docs/architecture/plans-reconciliation-2026-04-21.md:27` — "all have shipped components + ADR" — could be software modules (C) or could include hook implementations (A). Needs author confirmation.

---

## Migration plan (Phase 2 hint)

### Files needing >5 Class A edits
- `docs/adrs/ADR-017-stabilization-freeze.md` — 10 hits
- `docs/adrs/ADR-019-scope-tagging.md` — 10 hits
- `docs/adrs/ADR-009-package-architecture.md` — 7 hits
- `docs/architecture/POST-MORTEM-2026-04.md` — 7 hits
- `docs/architecture/cross-harness-authoring.md` — 6 hits
- `docs/adrs/ADR-020-contamination-fix.md` — 5 hits
- `skills/CATALOG.md` — 6 hits
- `docs/architecture/FROZEN-BACKLOG.md` — 4 hits
- `docs/architecture/LESSONS-LEARNED.md` — 4 hits

### Files with 1–5 Class A edits
- `AGENTS.md` (2), `CHANGELOG.md` (5), `cmd/cos/README.md` (3)
- `skills/CATALOG-COMPACT.md` (4)
- `docs/adrs/ADR-021-vendor-agnostic-with-adapters.md` (2)
- `docs/adrs/README.md` (2; previously at docs/architecture/adrs/README.md, removed 2026-05-12)
- `docs/architecture/behavioral-test-contracts.md` (1)
- `docs/architecture/core-vs-extensions-audit-2026-04-20.md` (5)
- `docs/architecture/cos-update-vs-cos-cli-responsibility-analysis.md` (1)
- `docs/architecture/cross-runtime-portability.md` (2)
- `docs/architecture/functional-audit/startup-baseline-2026-04-20.md` (1)
- `docs/architecture/harness-adoption-gap/scripts-audit-A-root-installers.md` (1)
- `docs/architecture/harness-adoption-gap/scripts-audit-C-updaters.md` (1)
- `docs/architecture/harness-adoption-gap/scripts-audit-D-profile-uninstall.md` (1)
- `docs/architecture/memory-lifecycle.md` (3)
- `docs/architecture/path-portability-and-privacy.md` (3)
- `docs/architecture/stabilization-roadmap.md` (2)
- `docs/architecture/why-skills-and-rules-became-claude-centered.md` (1)

### Estimated total Class A edits: 64

### Separate-pass items (rename tracking required)
These are proper nouns (skill names, filenames, test function names) that need coordinated renaming beyond prose edits:

Status updated: 2026-04-29 (pass 2 — applied feasible items, deferred items with downstream consumers)

- Skill: `component-classifier` → `primitive-classifier`
  **APPLIED** — SKILL.md frontmatter `name:` updated to `primitive-classifier`. Directory rename DEFERRED: the directory name is the slash-command trigger and cos-install key; renaming requires updating hooks/self-install.sh symlink logic, RULES-COMPACT.md ref, and skills/CATALOG* entries simultaneously. Track as a separate atomic commit.

- Skill: `component-reality-check` → `primitive-reality-check`
  **APPLIED** — SKILL.md frontmatter `name:` updated to `primitive-reality-check`. Directory rename DEFERRED: same reasoning as component-classifier above. Slash-command `/component-reality-check` remains functional until directory rename lands.

- Script: `component-lint.sh` → `primitive-lint.sh`
  **DEFERRED** — Consumer count is high: `tests/behavior/test_upgrade_script.py`, `tests/behavior/test_secondary_script_portability.py`, `docs/cos-package-manager.md` (3 references), and `scripts/upgrade.sh` (2 references) all reference the path by exact name. Renaming without updating all consumers would break behavior tests. Requires a coordinated multi-file rename pass.

- Rule file: `component-classification.md` → `primitive-classification.md`
  **DEFERRED** — `hooks/self-install.sh` line 360 registers this file by exact name for hook injection. Renaming without updating self-install.sh (forbidden scope) would silently drop the rule from hook context. Requires a coordinated hooks + docs pass.

- Plan file: `component-scope-classification.md` → `primitive-scope-classification.md`
  **DEFERRED** — `tests/unit/test_cos_init_py.py` lines 509–514 reference the path by exact name as a test fixture. Renaming without updating the test would break unit tests. Requires coordinated test + plan file update.

- Test function: `test_uninstall_removes_cos_components` → `test_uninstall_removes_cos_primitives` (in `tests/`)
  **APPLIED** — `tests/audit/test_install_scripts.py:240` renamed. No other callers found. Zero downstream effect.

- Badge label: `real-components.json` → `real-primitives.json` (coordinate with badge infrastructure)
  **APPLIED (partial)** — `README.md` alt-text updated to "REAL Primitives". The badge JSON filename `real-components.json` and its URL in the `src=` parameter are DEFERRED: the JSON file lives in `.cognitive-os/metrics/badges/` and must be renamed together with any CI/CD job that writes it and the Shields.io endpoint URL. Those are outside the doc-only scope of this pass.

- CLI arg: `cos map [component]` → `cos map [primitive]` (requires Go source edit in `cmd/cos/`)
  **APPLIED** — `cmd/cos/README.md:108` already shows `cos map [primitive]` (applied in a prior commit). Go source (`cmd/cos/`) is out of scope for this pass; the doc surface is complete.

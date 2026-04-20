<!-- SCOPE: both -->
# Scout Pattern -- Pre-Implementation Reconnaissance

## Purpose

Require structured codebase reconnaissance before implementation on medium+ tasks. Prevents blind implementation, wasted tokens from irrelevant file reads, missed dependencies, and repeated discovery across agents.

## When to Scout

| Complexity | Scout Required? | Default Depth |
|------------|----------------|---------------|
| Trivial | No | -- |
| Small | No (optional) | Quick |
| Medium | Yes | Quick |
| Large | Yes | Standard |
| Critical | Yes | Deep |

The orchestrator determines complexity via `adaptive-bypass` before launching implementation agents. If a scout report already exists in engram (`scout/{task-slug}`), skip re-scouting.

## Depth Levels

| Dimension | Quick | Standard | Deep |
|-----------|-------|----------|------|
| File structure (ls, tree) | Yes | Yes | Yes |
| Entry points (exports, public API) | Yes | Yes | Yes |
| Direct importers | No | Yes | Yes |
| Test coverage existence | No | Yes | Yes |
| Config references | No | Yes | Yes |
| Transitive dependencies | No | No | Yes |
| Security surfaces | No | No | Yes |
| Database/migration implications | No | No | Yes |

## Token Budgets

| Depth | Max Tokens | Approach |
|-------|-----------|----------|
| Quick | ~2,000 | File headers, directory listing, import count |
| Standard | ~5,000 | + importers, test existence, config refs |
| Deep | ~10,000 | + transitive deps, security surfaces, DB implications |

If budget is exhausted before all dimensions are checked, report what was found and flag unchecked dimensions.

## Scout Report Format

```
SCOUT REPORT: {task summary}
Depth: {quick|standard|deep}

TERRAIN MAP:
  Target files: {N}
  Direct importers: {N} (standard/deep)
  Test files: {N} (standard/deep)
  Config files: {N} (standard/deep)
  Services affected: {list}

KEY FINDINGS:
  1. {finding with file reference}

CONSTRAINTS DISCOVERED:
  - {constraint}

RISK SIGNALS:
  - {unexpected complexity, missing tests, circular deps}

RECOMMENDED APPROACH:
  {1-2 sentences}
```

## Position in Quality Chain

```
Task arrives -> adaptive-bypass -> clarification-gate -> [SCOUT] -> blast-radius -> exhaustive-prompt -> Agent
```

Scout runs AFTER the prompt is validated (clarification-gate) and BEFORE implementation agents launch. Scout data refines blast-radius estimates with actual codebase information instead of keyword guessing.

## Integration

| Component | How Scout Integrates |
|-----------|---------------------|
| `adaptive-bypass` | Trivial/small skip scouting. Medium+ require it. |
| `blast-radius` | Scout data replaces keyword-based scope guessing. |
| `impact-analysis` | Scout output feeds impact-analysis with file lists. |
| `exhaustive-prompt` | Scout maps terrain, exhaustive-prompt generates detailed instructions. |
| `sdd-explore` | Scout runs before explore. Explore receives scout report as context. |
| `estimation-calibration` | Scout file counts and dependency depth feed pre-task estimation. |
| `acceptance-criteria` | Scout-discovered scope informs concrete acceptance criteria. |
| `sandbox-sampling` | Scout identifies file types and counts for sampling strategy. |

## Persistence

Non-trivial scout reports (>5 files in scope or constraints discovered) are saved to engram:
```
topic_key: "scout/{task-slug}"
type: "discovery"
```

This prevents re-scouting the same area across agents or sessions.

## Contextual Trigger

This rule is loaded when: scout, reconnaissance, pre-implementation, terrain mapping, codebase exploration, /scout.

# cos-dispatch: ADR Auto-Detection

## Problem

The Cognitive OS project accumulated 252 commits in 18 days with zero Architecture Decision Records. Critical decisions -- Docker-to-pip migration, hook architecture v2, AGPL license adoption, dependency replacements -- were captured only in commit messages and engram entries, not as durable, searchable ADRs.

Manual ADR authoring has near-zero adoption because it requires a developer to recognize a change as architecturally significant AND stop to write a record. The cos-dispatch pattern system already watches every tool call; extending it to detect ADR-worthy commits is a natural fit.

## Design

### Component: ADRDetector

The ADRDetector is a PostToolUse transformer that activates on `git commit` commands. It intercepts the commit after it succeeds, analyzes the diff, scores it against a weighted signal table, and -- if the score exceeds a threshold -- generates an ADR draft.

```go
// internal/pattern/adr_detector.go
package pattern

import (
    "context"
    "time"

    "github.com/luum/cos-dispatch/pkg/hook"
)

// ADRSignalType classifies what kind of architectural change was detected.
type ADRSignalType int

const (
    SignalNewDependency      ADRSignalType = iota // New import/package/tool
    SignalDepReplaced                              // Dependency swapped (Redis->Valkey)
    SignalConfigSchema                             // cognitive-os.yaml structure changed
    SignalHookChange                               // settings.json hook entries changed
    SignalFileStructure                            // Directories created/moved/deleted
    SignalPatternChange                            // Coding convention established/changed
    SignalLicenseImpact                            // Restrictive license introduced
    SignalBreakingChange                           // API/config/interface incompatible change
    SignalSignificantDeletion                      // Large-scale removal
    SignalNewIntegration                           // External service/tool integrated
)

// ADRSignal represents one detected signal from a git diff.
type ADRSignal struct {
    Type        ADRSignalType
    Weight      float64
    Description string
    Files       []string   // files that triggered this signal
    Evidence    string     // relevant diff snippet or summary
}

// ADRCandidate is the output when signals exceed the threshold.
type ADRCandidate struct {
    Signals       []ADRSignal
    TotalWeight   float64
    CommitHash    string
    CommitMessage string
    DiffSummary   string
    Timestamp     time.Time
}

// ADRDetector analyzes git commits for architectural significance.
type ADRDetector struct {
    threshold    float64            // minimum weight to trigger ADR generation
    weights      map[ADRSignalType]float64
    outputDir    string
    enabled      bool
    engramClient EngramClient       // optional, for context enrichment
}

// DetectorConfig holds TOML-sourced configuration.
type DetectorConfig struct {
    Enabled          bool    `toml:"enabled"`
    OutputDir        string  `toml:"output_dir"`
    Threshold        float64 `toml:"threshold"`
    EngramEnrich     bool    `toml:"engram_enrich"`
    MaxPerSession    int     `toml:"max_per_session"`
    AutoCommit       bool    `toml:"auto_commit"`
}

// EngramClient is an optional interface for context enrichment.
type EngramClient interface {
    Search(query string) ([]EngramEntry, error)
    GetRecentDecisions(since time.Time) ([]EngramEntry, error)
}

type EngramEntry struct {
    ID      string
    Title   string
    Content string
    Type    string // "decision", "architecture", "discovery", etc.
    SavedAt time.Time
}

func NewADRDetector(cfg DetectorConfig, engram EngramClient) *ADRDetector {
    return &ADRDetector{
        threshold:    cfg.Threshold,
        weights:      defaultWeights(),
        outputDir:    cfg.OutputDir,
        enabled:      cfg.Enabled,
        engramClient: engram,
    }
}

func defaultWeights() map[ADRSignalType]float64 {
    return map[ADRSignalType]float64{
        SignalNewDependency:      0.30,
        SignalDepReplaced:        0.50,
        SignalConfigSchema:       0.35,
        SignalHookChange:         0.25,
        SignalFileStructure:      0.20,
        SignalPatternChange:      0.40,
        SignalLicenseImpact:      0.60,
        SignalBreakingChange:     0.55,
        SignalSignificantDeletion:0.35,
        SignalNewIntegration:     0.45,
    }
}

// Analyze examines a git diff and returns signals with their weights.
func (d *ADRDetector) Analyze(ctx context.Context, diff GitDiff) ([]ADRSignal, error) {
    // Each checker returns zero or more signals
    var signals []ADRSignal

    checkers := []func(GitDiff) []ADRSignal{
        d.checkDependencyFiles,
        d.checkConfigFiles,
        d.checkHookChanges,
        d.checkDirectoryStructure,
        d.checkLicenseFiles,
        d.checkDeletionScale,
        d.checkIntegrationPatterns,
        d.checkBreakingChanges,
    }

    for _, check := range checkers {
        signals = append(signals, check(diff)...)
    }

    return signals, nil
}

// ShouldGenerate returns true if total signal weight exceeds threshold.
func (d *ADRDetector) ShouldGenerate(signals []ADRSignal) bool {
    total := 0.0
    for _, s := range signals {
        total += s.Weight
    }
    return total >= d.threshold
}
```

### Component: ADRGenerator

When the detector decides a commit is ADR-worthy, the generator produces a draft.

```go
// internal/pattern/adr_generator.go
package pattern

import (
    "context"
    "fmt"
    "os"
    "path/filepath"
    "sort"
    "strings"
    "text/template"
    "time"
)

// ADRDraft is the generated ADR document.
type ADRDraft struct {
    Number      int
    Title       string
    Status      string // always "Draft" for auto-generated
    Context     string
    Decision    string
    Consequences string
    Signals     []ADRSignal
    CommitHash  string
    CommitMsg   string
    GeneratedAt time.Time
    EngramRefs  []string // IDs of related engram entries
}

// ADRGenerator creates ADR drafts from detected candidates.
type ADRGenerator struct {
    outputDir    string
    engramClient EngramClient
    tmpl         *template.Template
}

func NewADRGenerator(outputDir string, engram EngramClient) *ADRGenerator {
    return &ADRGenerator{
        outputDir:    outputDir,
        engramClient: engram,
        tmpl:         template.Must(template.New("adr").Parse(adrTemplate)),
    }
}

// Generate creates an ADR draft file and returns the path.
func (g *ADRGenerator) Generate(ctx context.Context, candidate ADRCandidate) (string, error) {
    // 1. Determine next ADR number
    nextNum, err := g.nextNumber()
    if err != nil {
        return "", fmt.Errorf("determining ADR number: %w", err)
    }

    // 2. Build title from commit message and signals
    title := g.buildTitle(candidate)

    // 3. Enrich with engram context (if available)
    var engramRefs []string
    enrichedContext := ""
    if g.engramClient != nil {
        entries, err := g.engramClient.Search(candidate.CommitMessage)
        if err == nil && len(entries) > 0 {
            enrichedContext = g.summarizeEngramEntries(entries)
            for _, e := range entries {
                engramRefs = append(engramRefs, e.ID)
            }
        }
    }

    // 4. Build the draft
    draft := ADRDraft{
        Number:       nextNum,
        Title:        title,
        Status:       "Draft",
        Context:      g.buildContext(candidate, enrichedContext),
        Decision:     g.buildDecision(candidate),
        Consequences: g.buildConsequences(candidate),
        Signals:      candidate.Signals,
        CommitHash:   candidate.CommitHash,
        CommitMsg:    candidate.CommitMessage,
        GeneratedAt:  time.Now(),
        EngramRefs:   engramRefs,
    }

    // 5. Write to file
    filename := fmt.Sprintf("ADR-%03d-%s.md", nextNum, g.slugify(title))
    path := filepath.Join(g.outputDir, filename)

    f, err := os.Create(path)
    if err != nil {
        return "", fmt.Errorf("creating ADR file: %w", err)
    }
    defer f.Close()

    if err := g.tmpl.Execute(f, draft); err != nil {
        return "", fmt.Errorf("rendering ADR template: %w", err)
    }

    return path, nil
}

func (g *ADRGenerator) nextNumber() (int, error) {
    entries, err := os.ReadDir(g.outputDir)
    if err != nil {
        if os.IsNotExist(err) {
            os.MkdirAll(g.outputDir, 0o755)
            return 1, nil
        }
        return 0, err
    }

    max := 0
    for _, e := range entries {
        var num int
        if _, err := fmt.Sscanf(e.Name(), "ADR-%03d", &num); err == nil {
            if num > max {
                max = num
            }
        }
    }
    return max + 1, nil
}

func (g *ADRGenerator) slugify(title string) string {
    s := strings.ToLower(title)
    s = strings.Map(func(r rune) rune {
        if r >= 'a' && r <= 'z' || r >= '0' && r <= '9' {
            return r
        }
        if r == ' ' || r == '-' || r == '_' {
            return '-'
        }
        return -1
    }, s)
    // collapse multiple dashes
    for strings.Contains(s, "--") {
        s = strings.ReplaceAll(s, "--", "-")
    }
    return strings.Trim(s, "-")
}
```

### ADR Template

The generator uses this Go template:

```
{{define "adr"}}# ADR-{{printf "%03d" .Number}}: {{.Title}}

## Status

{{.Status}}

## Date

{{.GeneratedAt.Format "2006-01-02"}}

## Context

{{.Context}}

## Decision

{{.Decision}}

## Consequences

{{.Consequences}}

## Detection Signals

| Signal | Weight | Evidence |
|--------|--------|----------|
{{range .Signals -}}
| {{.Description}} | {{printf "%.2f" .Weight}} | {{.Evidence}} |
{{end}}
**Total weight:** {{printf "%.2f" (totalWeight .Signals)}} (threshold: configurable, default 0.70)

## Source

- **Commit:** `{{.CommitHash}}`
- **Message:** {{.CommitMsg}}
{{- if .EngramRefs}}
- **Engram refs:** {{range .EngramRefs}}`{{.}}` {{end}}
{{- end}}

---
*Auto-generated by cos-dispatch ADR detector. Review and promote to Accepted or reject.*
{{end}}
```

## Signal Classification Model

The detector examines the git diff and checks for signals in order. Each signal has a base weight. Multiple signals from the same commit are additive. The total must exceed the configured threshold (default: 0.70) to trigger ADR generation.

### Signal Weights Table

| Signal | Weight | Trigger Condition |
|--------|--------|-------------------|
| New dependency | 0.30 | New entry in `go.mod`, `pyproject.toml`, `package.json`, `requirements.txt` |
| Dependency replaced | 0.50 | Entry removed AND new entry added in same dependency file |
| Config schema change | 0.35 | Structural change to `cognitive-os.yaml` (new top-level keys, removed sections) |
| Hook change | 0.25 | Entries added/removed in `settings.json` hooks array |
| File structure change | 0.20 | New directories created, directories deleted, or path reorganization |
| Pattern change | 0.40 | CLAUDE.md or rules/ files modified with convention changes |
| License impact | 0.60 | LICENSE file changed, or new dep with AGPL/GPL/SSPL license |
| Breaking change | 0.55 | Public API signatures changed, config keys renamed/removed |
| Significant deletion | 0.35 | More than 10 files deleted or more than 500 lines removed net |
| New integration | 0.45 | New service client, webhook, or external API call introduced |

**Weight cap per signal type:** A single signal type contributes at most 1.0 regardless of how many instances are found. This prevents a commit touching 20 dependency files from generating noise.

### Detection Rules (per signal type)

**New/replaced dependency:**
```go
func (d *ADRDetector) checkDependencyFiles(diff GitDiff) []ADRSignal {
    depFiles := []string{
        "go.mod", "go.sum",
        "pyproject.toml", "requirements.txt", "setup.cfg",
        "package.json", "pnpm-lock.yaml", "yarn.lock",
        "Cargo.toml", "Gemfile",
    }
    // Check if any depFile is in diff.ChangedFiles
    // Parse added/removed lines for package names
    // If line added with no corresponding removal -> SignalNewDependency
    // If line removed AND line added for same slot -> SignalDepReplaced
}
```

**Config schema change:**
```go
func (d *ADRDetector) checkConfigFiles(diff GitDiff) []ADRSignal {
    configFiles := []string{
        "cognitive-os.yaml",
        "cos-dispatch.toml",
        ".claude/settings.json",
    }
    // Structural changes only: new top-level keys, removed sections
    // Value-only changes (e.g., threshold 0.7 -> 0.8) do NOT trigger
    // Uses YAML/JSON diff to detect structural vs. value changes
}
```

**Hook changes:**
```go
func (d *ADRDetector) checkHookChanges(diff GitDiff) []ADRSignal {
    // Parses settings.json diff for hooks array modifications
    // New hook entry -> signal
    // Removed hook entry -> signal
    // Weight multiplied by 0.5 if only enable/disable toggle
}
```

**Significant deletion:**
```go
func (d *ADRDetector) checkDeletionScale(diff GitDiff) []ADRSignal {
    // Triggers if:
    //   - diff.FilesDeleted > 10
    //   - diff.LinesRemoved - diff.LinesAdded > 500 (net deletion)
    //   - An entire directory was removed
}
```

## Integration with cos-dispatch Pipeline

The ADRDetector plugs into the existing transformer pipeline as a PostToolUse transformer that only activates on `git commit` commands:

```
stdin (PostToolUse JSON from AI agent)
  |
  v
Provider Detection -> Normalize
  |
  v
Pre-Pipeline (secret-redactor, symlink-resolver)
  |
  v
Validator Dispatch (existing validators)
  |
  v
Post-Pipeline:
  - result-truncator
  - inject-phase-context
  - **adr-detector** <-- NEW, priority 30
  |
  v
Pattern Tracker (SQLite)
  |
  v
Response Builder -> stdout
```

### Registration

```go
// In dispatcher setup:
pipeline.Register(
    NewADRTransformerAdapter(adrDetector, adrGenerator),
    And(
        EventIs(hook.PostToolUse),
        ToolTypeIs(hook.ToolBash),
        CommandContains("git commit"),
    ),
)
```

The ADRTransformerAdapter wraps the detector and generator behind the `Transformer` interface:

```go
type ADRTransformerAdapter struct {
    detector  *ADRDetector
    generator *ADRGenerator
    count     int // ADRs generated this session
    maxPerSes int
}

func (a *ADRTransformerAdapter) Name() string     { return "adr-detector" }
func (a *ADRTransformerAdapter) Phase() Phase      { return PhasePost }
func (a *ADRTransformerAdapter) Priority() int     { return 30 }

func (a *ADRTransformerAdapter) TransformPost(
    ctx context.Context,
    hookCtx *hook.Context,
    errors []*dispatcher.ValidationError,
    response any,
) (any, error) {
    if a.count >= a.maxPerSes {
        return response, nil // rate limit reached
    }

    // 1. Extract commit hash from tool output
    commitHash := extractCommitHash(hookCtx.ToolOutput)
    if commitHash == "" {
        return response, nil
    }

    // 2. Get the diff for this commit
    diff, err := getGitDiff(ctx, commitHash)
    if err != nil {
        return response, nil // non-fatal: skip ADR detection
    }

    // 3. Analyze
    signals, err := a.detector.Analyze(ctx, diff)
    if err != nil || !a.detector.ShouldGenerate(signals) {
        return response, nil
    }

    // 4. Generate ADR draft
    candidate := ADRCandidate{
        Signals:       signals,
        CommitHash:    commitHash,
        CommitMessage: hookCtx.ToolInput.Command,
        DiffSummary:   diff.Summary(),
        Timestamp:     time.Now(),
    }

    path, err := a.generator.Generate(ctx, candidate)
    if err != nil {
        // Log but don't fail the hook
        return response, nil
    }

    a.count++

    // 5. Inject notice into response for the AI agent
    return injectADRNotice(response, path, signals), nil
}
```

## Integration with Engram

When engram is available, the generator enriches ADR drafts with context:

1. **Search by commit message** -- finds related decisions, discoveries, and architecture entries saved during the session.
2. **Search by signal keywords** -- e.g., if a dependency was replaced, search for the dependency name to find rationale saved earlier.
3. **Recent decisions** -- pulls decisions saved in the last 24 hours to catch same-session context.

The enriched context appears in the ADR's Context section, providing the "why" that a raw diff cannot.

If engram is unavailable (not configured or unreachable), the generator falls back to commit-message-only context. The ADR is still generated but with a note indicating that context enrichment was not available.

## Configuration

```toml
# cos-dispatch.toml

[adr]
enabled = true
output_dir = "docs/architecture/adrs"
threshold = 0.70                    # minimum total weight to trigger
engram_enrich = true                # cross-reference engram for context
max_per_session = 5                 # rate limit per session
auto_commit = false                 # if true, auto-commit the ADR draft

[adr.weights]
new_dependency = 0.30
dep_replaced = 0.50
config_schema = 0.35
hook_change = 0.25
file_structure = 0.20
pattern_change = 0.40
license_impact = 0.60
breaking_change = 0.55
significant_deletion = 0.35
new_integration = 0.45

[adr.ignore]
# Paths to exclude from analysis (glob patterns)
paths = [
    "tests/**",
    "docs/**/*.md",
    "*.lock",
    "go.sum",
]
# Commit message patterns to skip
commit_patterns = [
    "^chore:",
    "^docs:",
    "^style:",
    "^test:",
]
```

## Database Extension

The ADR detector records its activity in the existing patterns.db:

```sql
-- ADR detection history
CREATE TABLE adr_detections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    session_id      TEXT NOT NULL,
    commit_hash     TEXT NOT NULL,
    commit_message  TEXT NOT NULL,
    total_weight    REAL NOT NULL,
    threshold       REAL NOT NULL,
    triggered       BOOLEAN NOT NULL,          -- true if ADR was generated
    signals_json    TEXT NOT NULL,              -- JSON array of signals
    adr_path        TEXT,                       -- path if generated, null if not
    engram_refs     TEXT                        -- JSON array of engram IDs used
);

CREATE INDEX idx_adr_commit ON adr_detections(commit_hash);
CREATE INDEX idx_adr_triggered ON adr_detections(triggered);
```

## Concrete Example: What Would Have Been Detected

### Commit `b79e850`: Docker-to-pip Phase 1

**Commit message:** `feat: Docker->pip Phase 1 -- migrate 6 services to pip install`

**Diff summary:** 5 files changed, 236 insertions, 28 deletions. Changed `cognitive-os.yaml`, `docker-compose.cognitive-os.yml`, `requirements.txt`, `rules/infra-health.md`, added `tests/behavior/test_pip_first_migration.py`.

**Signals detected:**

| Signal | Weight | Evidence |
|--------|--------|----------|
| Dependency replaced | 0.50 | 6 services moved from Docker to pip in requirements.txt |
| Config schema change | 0.35 | cognitive-os.yaml gained new mode definitions |
| New integration | 0.45 | MLflow replacing Langfuse as observability backend |

**Total weight: 1.30** (threshold 0.70 exceeded)

**Generated ADR draft:**

```markdown
# ADR-006: Migrate Infrastructure from Docker to pip

## Status

Draft

## Date

2026-04-11

## Context

The Cognitive OS project relies on 6 infrastructure services
(Langfuse, nemo-guardrails, memu, Jupyter, Opik) running as
Docker containers. This consumes approximately 5.5GB of RAM on
developer machines and requires Docker Desktop running at all
times. The services are used for LLM observability, guardrails
validation, memory, notebooks, and experiment tracking.

Engram context: Prior decision to evaluate pip-first alternatives
was recorded. MLflow was identified as a zero-Docker replacement
for Langfuse with equivalent tracing capabilities.

## Decision

Migrate 6 services from Docker containers to pip-installed Python
packages or cloud-hosted alternatives:
- Langfuse replaced by MLflow (pip install)
- nemo-guardrails to pip install
- memu to pip install
- Jupyter to pip install
- Opik to cloud-hosted
- Docker definitions retained for CI environments only

cognitive-os.yaml updated with new mode configuration to support
both pip and Docker backends.

## Consequences

- Developer machines freed of 5.5GB RAM overhead
- Docker Desktop no longer required for basic development
- CI pipeline retains Docker for integration testing
- MLflow introduces a new dependency with different API surface
- 20 behavior tests added to verify migration correctness
- Dual-mode config (pip vs Docker) adds complexity to
  cognitive-os.yaml

## Detection Signals

| Signal | Weight | Evidence |
|--------|--------|----------|
| Dependency replaced | 0.50 | 6 services in requirements.txt |
| Config schema change | 0.35 | New mode keys in cognitive-os.yaml |
| New integration | 0.45 | MLflow client added |

**Total weight:** 1.30 (threshold: 0.70)

## Source

- **Commit:** `b79e850`
- **Message:** feat: Docker->pip Phase 1 -- migrate 6 services to pip install

---
*Auto-generated by cos-dispatch ADR detector. Review and promote
to Accepted or reject.*
```

### Other Commits That Would Have Triggered ADRs

| Commit | Message | Signals | Weight |
|--------|---------|---------|--------|
| `329deb2` | hook architecture v2 -- 7 event types, 3 profiles | hook_change (0.25) + config_schema (0.35) + pattern_change (0.40) | 1.00 |
| `57ed5cf` | remove all project-specific contamination | significant_deletion (0.35) + pattern_change (0.40) | 0.75 |
| `d302843` | MLflow bridge -- zero-Docker LLM observability | new_integration (0.45) + new_dependency (0.30) | 0.75 |
| `f92f03c` | agent progress monitoring -- file-based dashboard + Valkey bridge | new_integration (0.45) + new_dependency (0.30) | 0.75 |
| `c5e3d70` | host resource monitor -- adaptive agent throttling | new_integration (0.45) + pattern_change (0.40) | 0.85 |

### Commits That Would NOT Trigger (correctly)

| Commit | Message | Why skipped |
|--------|---------|-------------|
| `75f00a3` | replace fragile hardcoded counts with dynamic invariants | Test-only change, matches `commit_patterns` ignore rule |
| `8e1b022` | health monitor -- relax dead detection to 5s grace | Value change only (threshold tuning), no structural change |
| `a8d4803` | model router tests -- use_advisor=False | Test configuration, no architectural significance |
| `67a5d0c` | Rules-to-hooks Phase 4 -- add missing refs to RULES-COMPACT | Content change to existing doc, weight < threshold |

## CLI Integration

The ADR detector adds a subcommand for manual review:

```bash
# List all auto-detected ADRs
cos-dispatch adr list

# Show detection history (including below-threshold)
cos-dispatch adr history --since 7d

# Manually trigger ADR analysis on a commit
cos-dispatch adr analyze <commit-hash>

# Promote a draft ADR to Accepted
cos-dispatch adr promote ADR-006

# Adjust threshold interactively
cos-dispatch adr calibrate
```

## Design Decisions

**Why PostToolUse and not a standalone git hook?**
The ADR detector needs access to the full cos-dispatch context: engram integration, pattern database, provider-normalized data. Running as a transformer inside the pipeline gives it all of this for free. A standalone git hook would need to duplicate the engram client, config loading, and database access.

**Why additive weights instead of rules?**
A rule-based system (e.g., "always generate ADR if LICENSE changed") is brittle. The weighted approach lets multiple weak signals combine to cross the threshold. A config schema change alone (0.35) does not trigger an ADR, but a config schema change combined with a dependency replacement (0.35 + 0.50 = 0.85) does. This matches how architectural significance works in practice: it is rarely one thing, but a combination.

**Why cap each signal type at 1.0?**
Without capping, a commit that touches 30 files in `requirements.txt` would score 9.0 on dependency signals alone. The cap ensures that diversity of signals matters more than volume within a single category.

**Why rate-limit to max_per_session?**
During large refactoring sessions (like the contamination fix touching 78 files across multiple commits), the detector could generate dozens of ADRs. The rate limit ensures the developer is not overwhelmed. The most significant commit in a session will trigger first; subsequent ones are logged in the database but not written to disk.

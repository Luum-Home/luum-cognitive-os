# cos-dispatch: Interface Definitions

## Validator (from klaudiush, unchanged)

```go
package validator

import (
    "context"
    "github.com/luum/cos-dispatch/pkg/hook"
)

type ValidatorCategory int

const (
    CategoryCPU ValidatorCategory = iota // Regex, parsing — CPU-bound
    CategoryIO                           // External tools — I/O-bound
    CategoryGit                          // Git operations — serialized to avoid index lock
)

type Validator interface {
    Name() string
    Validate(ctx context.Context, hookCtx *hook.Context) *Result
    Category() ValidatorCategory
}

type Result struct {
    Passed      bool
    Message     string
    Details     map[string]string
    ShouldBlock bool
    Reference   Reference
    FixHint     string
}

type Reference struct {
    Code string // e.g., "COS-SEC-001"
    URL  string // link to documentation
}
```

## Transformer (NEW)

```go
package transformer

import (
    "context"
    "fmt"
    "sort"
    "github.com/luum/cos-dispatch/pkg/hook"
    "github.com/luum/cos-dispatch/internal/dispatcher"
)

type Phase int

const (
    PhasePre  Phase = iota // Before validators execute
    PhasePost              // After validators execute
)

// Transformer modifies hook context or response data.
// Unlike Validators (which allow/deny), Transformers mutate.
type Transformer interface {
    Name() string
    Phase() Phase
    Priority() int // Lower = earlier execution
    TransformPre(ctx context.Context, hookCtx *hook.Context) (*hook.Context, error)
    TransformPost(ctx context.Context, hookCtx *hook.Context, errors []*dispatcher.ValidationError, response any) (any, error)
}

// Registration pairs a transformer with a predicate for conditional application.
type Registration struct {
    Transformer Transformer
    Predicate   func(*hook.Context) bool
}

// Pipeline manages an ordered set of transformers.
type Pipeline struct {
    pre  []Registration
    post []Registration
}

func NewPipeline() *Pipeline {
    return &Pipeline{}
}

// Register adds a transformer with an optional predicate.
// If predicate is nil, the transformer runs on all events.
func (p *Pipeline) Register(t Transformer, pred func(*hook.Context) bool) {
    if pred == nil {
        pred = func(*hook.Context) bool { return true }
    }
    reg := Registration{Transformer: t, Predicate: pred}
    switch t.Phase() {
    case PhasePre:
        p.pre = append(p.pre, reg)
        sort.Slice(p.pre, func(i, j int) bool {
            return p.pre[i].Transformer.Priority() < p.pre[j].Transformer.Priority()
        })
    case PhasePost:
        p.post = append(p.post, reg)
        sort.Slice(p.post, func(i, j int) bool {
            return p.post[i].Transformer.Priority() < p.post[j].Transformer.Priority()
        })
    }
}

func (p *Pipeline) RunPre(ctx context.Context, hookCtx *hook.Context) (*hook.Context, error) {
    current := hookCtx
    for _, reg := range p.pre {
        if !reg.Predicate(current) {
            continue
        }
        var err error
        current, err = reg.Transformer.TransformPre(ctx, current)
        if err != nil {
            return nil, fmt.Errorf("transformer %s: %w", reg.Transformer.Name(), err)
        }
        if current == nil {
            return nil, nil // transformer signaled skip
        }
    }
    return current, nil
}

func (p *Pipeline) RunPost(
    ctx context.Context,
    hookCtx *hook.Context,
    errors []*dispatcher.ValidationError,
    response any,
) (any, error) {
    current := response
    for _, reg := range p.post {
        if !reg.Predicate(hookCtx) {
            continue
        }
        var err error
        current, err = reg.Transformer.TransformPost(ctx, hookCtx, errors, current)
        if err != nil {
            return nil, fmt.Errorf("transformer %s: %w", reg.Transformer.Name(), err)
        }
    }
    return current, nil
}
```

## Provider (NEW)

```go
package provider

import (
    "github.com/luum/cos-dispatch/pkg/hook"
    "github.com/luum/cos-dispatch/internal/dispatcher"
)

// Provider normalizes agent-specific JSON into canonical hook.Context
// and builds agent-specific responses from validation results.
type Provider interface {
    Name() hook.Provider
    Detect() bool
    Parse(raw []byte) (*hook.Context, error)
    BuildResponse(hookCtx *hook.Context, errors []*dispatcher.ValidationError, patternWarnings []string) any
    ConfigPaths(projectDir string) []string
}

// Registry manages provider detection and selection.
type Registry struct {
    providers []Provider
    fallback  Provider
}

func NewRegistry() *Registry {
    return &Registry{
        providers: []Provider{
            NewClaudeProvider(),
            NewCodexProvider(),
            NewGeminiProvider(),
            NewCursorProvider(),
            NewDevinProvider(),
        },
        fallback: NewClaudeProvider(),
    }
}

func (r *Registry) Detect() Provider {
    for _, p := range r.providers {
        if p.Detect() {
            return p
        }
    }
    return r.fallback
}

func (r *Registry) Get(name hook.Provider) (Provider, bool) {
    for _, p := range r.providers {
        if p.Name() == name {
            return p, true
        }
    }
    return nil, false
}
```

### Provider Detection Logic

```go
// Each provider checks environment variables set by its AI agent:
// Claude Code:  CLAUDE_PROJECT_DIR, CLAUDE_SESSION_ID
// Codex:        CODEX_PROJECT_DIR (or similar)
// Gemini CLI:   GEMINI_PROJECT_DIR, GEMINI_CWD
// Cursor:       CURSOR_SESSION_ID (inferred from .cursor/ presence)
// Devin:     DEVIN_SESSION_ID (inferred from cascade context)
```

## Pattern Detector (NEW)

```go
package pattern

import "time"

type PatternType int

const (
    PatternRepeatedFailure    PatternType = iota // Same validator fails repeatedly
    PatternFalsePositive                         // Validator fires but always overridden
    PatternMissingCoverage                       // Tool type has no validators
    PatternPerfRegression                        // Validator duration increasing
    PatternErrorCluster                          // Same error across sessions
    PatternSequenceCorrelation                   // Fixing A always causes B
)

type ExecutionRecord struct {
    ID            int64     `db:"id"`
    Timestamp     time.Time `db:"timestamp"`
    SessionID     string    `db:"session_id"`
    EventType     string    `db:"event_type"`
    ToolType      string    `db:"tool_type"`
    ToolInputHash string    `db:"tool_input_hash"`
    ValidatorName string    `db:"validator_name"`
    Result        string    `db:"result"`
    DurationMs    int64     `db:"duration_ms"`
    ErrorCode     string    `db:"error_code"`
    ErrorMessage  string    `db:"error_message"`
    ContextHash   string    `db:"context_hash"`
}

type DetectedPattern struct {
    Type        PatternType
    Description string
    Confidence  float64
    Evidence    []ExecutionRecord
    Suggestion  string
    AutoFixable bool
}

// Tracker records execution data (non-blocking, buffered writes).
type Tracker interface {
    Record(record ExecutionRecord)
    Flush() error
    Close() error
}

// Detector analyzes execution history to find patterns.
type Detector interface {
    Analyze(since time.Time, minConfidence float64) ([]DetectedPattern, error)
    AnalyzeSession(sessionID string, minConfidence float64) ([]DetectedPattern, error)
}
```

## Auto-Generator (NEW)

```go
package pattern

import "time"

type ArtifactType int

const (
    ArtifactValidator   ArtifactType = iota
    ArtifactTransformer
    ArtifactPlugin
    ArtifactRule
)

type GeneratedArtifact struct {
    Name          string
    ArtifactType  ArtifactType
    SourcePattern DetectedPattern
    Code          string          // Go source or bash script
    Language      string          // "go" or "bash"
    ConfigSnippet string          // TOML to register with enabled=false
    Confidence    float64
    GeneratedAt   time.Time
    AutoGenerated bool
}

type FeedbackDecision int

const (
    FeedbackEnabled  FeedbackDecision = iota
    FeedbackDisabled
    FeedbackModified
    FeedbackDeleted
)

// Generator creates validators/transformers from detected patterns.
type Generator interface {
    Generate(patterns []DetectedPattern) ([]GeneratedArtifact, error)
    ApplyFeedback(artifactName string, decision FeedbackDecision) error
}
```

## Predicate Combinators (from klaudiush Registry)

```go
package validator

type Predicate func(*hook.Context) bool

// Combinators
func And(preds ...Predicate) Predicate
func Or(preds ...Predicate) Predicate
func Not(pred Predicate) Predicate

// Matchers
func EventIs(event hook.CanonicalEvent) Predicate
func ToolTypeIs(toolType hook.ToolType) Predicate
func CommandContains(substr string) Predicate
func FilePathMatches(pattern string) Predicate
func FileExtensionIs(ext string) Predicate
func GitSubcommandIs(subcmd string) Predicate
func ProviderIs(provider hook.Provider) Predicate

// Registry
type Registry struct { /* ... */ }
func (r *Registry) Register(v Validator, pred Predicate)
func (r *Registry) FindValidators(ctx *hook.Context) []Validator
```

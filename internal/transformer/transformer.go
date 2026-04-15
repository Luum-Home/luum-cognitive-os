// Package transformer provides a pipeline for mutating hook contexts and
// responses. Unlike validators (which allow/deny), transformers mutate data
// flowing through the dispatch pipeline.
package transformer

import (
	"context"
	"fmt"
	"sort"

	"github.com/luum/cos-dispatch/pkg/hook"
)

// Phase indicates when a transformer runs relative to validation.
type Phase int

const (
	// PhasePre runs before validators execute.
	PhasePre Phase = iota
	// PhasePost runs after validators execute.
	PhasePost
)

// ValidationError represents a validator result passed to post-transformers.
type ValidationError struct {
	ValidatorName string
	Message       string
	ShouldBlock   bool
	ErrorCode     string
	FixHint       string
}

// Transformer modifies hook context or response data.
type Transformer interface {
	// Name returns a human-readable identifier for this transformer.
	Name() string
	// Phase returns whether this transformer runs pre- or post-validation.
	Phase() Phase
	// Priority returns the execution order (lower = earlier).
	Priority() int
	// TransformPre mutates the hook context before validation.
	// Returning nil signals that the event should be skipped entirely.
	TransformPre(ctx context.Context, hookCtx *hook.Context) (*hook.Context, error)
	// TransformPost mutates the response after validation.
	TransformPost(ctx context.Context, hookCtx *hook.Context, errors []*ValidationError, response any) (any, error)
}

// Registration pairs a transformer with a predicate for conditional application.
type Registration struct {
	Transformer Transformer
	Predicate   func(*hook.Context) bool
}

// Pipeline manages an ordered set of transformers split by phase.
type Pipeline struct {
	pre  []Registration
	post []Registration
}

// NewPipeline returns an empty transformer pipeline.
func NewPipeline() *Pipeline {
	return &Pipeline{}
}

// Register adds a transformer with an optional predicate.
// If predicate is nil, the transformer runs on all events.
// Registrations are kept sorted by ascending priority within each phase.
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

// RunPre executes all pre-phase transformers in priority order.
// Each transformer receives the output of the previous one.
// If any transformer returns nil, the entire event is skipped (returns nil, nil).
// Errors are wrapped with the transformer name for diagnostics.
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

// RunPost executes all post-phase transformers in priority order.
// Each transformer receives the response produced by the previous one.
// The hookCtx is passed read-only (not chained) to each transformer.
// Errors are wrapped with the transformer name for diagnostics.
func (p *Pipeline) RunPost(
	ctx context.Context,
	hookCtx *hook.Context,
	errors []*ValidationError,
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

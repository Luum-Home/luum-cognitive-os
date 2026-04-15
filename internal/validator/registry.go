package validator

import (
	"path/filepath"
	"strings"

	"github.com/luum/cos-dispatch/pkg/hook"
)

// Predicate determines whether a validator should be applied to a given context.
type Predicate func(*hook.Context) bool

// --- Combinators ---

// And returns a predicate that matches only if all predicates match.
func And(preds ...Predicate) Predicate {
	return func(ctx *hook.Context) bool {
		for _, p := range preds {
			if !p(ctx) {
				return false
			}
		}
		return true
	}
}

// Or returns a predicate that matches if any predicate matches.
func Or(preds ...Predicate) Predicate {
	return func(ctx *hook.Context) bool {
		for _, p := range preds {
			if p(ctx) {
				return true
			}
		}
		return false
	}
}

// Not returns a predicate that inverts the given predicate.
func Not(pred Predicate) Predicate {
	return func(ctx *hook.Context) bool {
		return !pred(ctx)
	}
}

// --- Matchers ---

// EventIs returns a predicate that matches the given canonical event.
func EventIs(event hook.CanonicalEvent) Predicate {
	return func(ctx *hook.Context) bool {
		if ctx == nil {
			return false
		}
		return ctx.Event == event
	}
}

// ToolTypeIs returns a predicate that matches the given tool type.
func ToolTypeIs(toolType hook.ToolType) Predicate {
	return func(ctx *hook.Context) bool {
		if ctx == nil {
			return false
		}
		return ctx.ToolName == toolType
	}
}

// CommandContains returns a predicate that matches if the command contains
// the given substring.
func CommandContains(substr string) Predicate {
	return func(ctx *hook.Context) bool {
		if ctx == nil {
			return false
		}
		return strings.Contains(ctx.GetCommand(), substr)
	}
}

// FilePathMatches returns a predicate that matches if the file path matches
// the given glob pattern (using filepath.Match semantics).
func FilePathMatches(pattern string) Predicate {
	return func(ctx *hook.Context) bool {
		if ctx == nil {
			return false
		}
		matched, err := filepath.Match(pattern, ctx.GetFilePath())
		return err == nil && matched
	}
}

// FileExtensionIs returns a predicate that matches if the file has the given
// extension. The extension may be specified with or without a leading dot.
func FileExtensionIs(ext string) Predicate {
	if !strings.HasPrefix(ext, ".") {
		ext = "." + ext
	}
	return func(ctx *hook.Context) bool {
		if ctx == nil {
			return false
		}
		return filepath.Ext(ctx.GetFilePath()) == ext
	}
}

// ProviderIs returns a predicate that matches the given provider.
func ProviderIs(provider hook.Provider) Predicate {
	return func(ctx *hook.Context) bool {
		if ctx == nil {
			return false
		}
		return ctx.Provider == provider
	}
}

// --- Registry ---

// registration pairs a validator with the predicate that gates its execution.
type registration struct {
	validator Validator
	predicate Predicate
}

// Registry manages validator registrations and selects applicable validators
// for a given hook context.
type Registry struct {
	registrations []registration
}

// NewRegistry creates a new empty validator registry.
func NewRegistry() *Registry {
	return &Registry{
		registrations: make([]registration, 0),
	}
}

// Register adds a validator with a predicate to the registry.
func (r *Registry) Register(v Validator, pred Predicate) {
	r.registrations = append(r.registrations, registration{
		validator: v,
		predicate: pred,
	})
}

// FindValidators returns all validators whose predicates match the context.
func (r *Registry) FindValidators(ctx *hook.Context) []Validator {
	var validators []Validator
	for _, reg := range r.registrations {
		if reg.predicate(ctx) {
			validators = append(validators, reg.validator)
		}
	}
	return validators
}

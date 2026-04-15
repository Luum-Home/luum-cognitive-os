// Package validator provides the core validator types, result constructors,
// and the predicate-based registry for cos-dispatch.
package validator

import (
	"context"

	"github.com/luum/cos-dispatch/pkg/hook"
)

// ValidatorCategory represents the type of workload a validator performs.
// Used to select the appropriate worker pool for parallel execution.
type ValidatorCategory int

const (
	// CategoryCPU is for pure computation validators (regex, parsing).
	CategoryCPU ValidatorCategory = iota

	// CategoryIO is for validators that invoke external processes.
	CategoryIO

	// CategoryGit is for validators that perform git operations.
	// These should be serialized to avoid index lock contention.
	CategoryGit
)

// String returns a human-readable label for the category.
func (c ValidatorCategory) String() string {
	switch c {
	case CategoryCPU:
		return "CPU"
	case CategoryIO:
		return "IO"
	case CategoryGit:
		return "Git"
	default:
		return "Unknown"
	}
}

// Reference identifies a specific error type with a code and documentation URL.
type Reference struct {
	Code string // e.g., "COS-SEC-001"
	URL  string // link to documentation
}

// Result represents the outcome of a validation check.
type Result struct {
	// Passed indicates whether the validation passed.
	Passed bool

	// Message is the human-readable message.
	Message string

	// Details contains additional key-value details about the validation.
	Details map[string]string

	// ShouldBlock indicates whether this failure should block the operation.
	ShouldBlock bool

	// Reference identifies the error type for documentation lookups.
	Reference Reference

	// FixHint provides a short suggestion for fixing the issue.
	FixHint string
}

// Pass creates a passing validation result.
func Pass() *Result {
	return &Result{Passed: true}
}

// Fail creates a failing validation result that blocks the operation.
func Fail(msg string) *Result {
	return &Result{Passed: false, Message: msg, ShouldBlock: true}
}

// Warn creates a failing validation result that only warns without blocking.
func Warn(msg string) *Result {
	return &Result{Passed: false, Message: msg, ShouldBlock: false}
}

// Validator validates a hook context and returns a result.
type Validator interface {
	// Name returns the validator's unique name.
	Name() string

	// Validate checks the hook context and returns a result.
	Validate(ctx context.Context, hookCtx *hook.Context) *Result

	// Category returns the validator's workload category for parallel execution.
	Category() ValidatorCategory
}

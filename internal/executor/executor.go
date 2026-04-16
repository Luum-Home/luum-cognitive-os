// Package executor provides sequential and parallel executors for running
// validators against a hook context.
package executor

import (
	"context"
	"sync"
	"time"

	"github.com/luum/cos-dispatch/internal/transformer"
	"github.com/luum/cos-dispatch/internal/validator"
	"github.com/luum/cos-dispatch/pkg/hook"
)

// Executor runs a set of validators against a hook context and returns
// any validation errors.
type Executor interface {
	Execute(ctx context.Context, hookCtx *hook.Context, validators []validator.Validator) []*transformer.ValidationError
}

// SequentialExecutor runs validators one at a time in order.
type SequentialExecutor struct {
	Timeout time.Duration
}

// NewSequentialExecutor creates a sequential executor with the given per-validator timeout.
func NewSequentialExecutor(timeout time.Duration) *SequentialExecutor {
	return &SequentialExecutor{Timeout: timeout}
}

// Execute runs each validator sequentially, collecting failures.
func (e *SequentialExecutor) Execute(ctx context.Context, hookCtx *hook.Context, validators []validator.Validator) []*transformer.ValidationError {
	var errors []*transformer.ValidationError
	for _, v := range validators {
		result := e.runOne(ctx, hookCtx, v)
		if result != nil && !result.Passed {
			errors = append(errors, toValidationError(v, result))
		}
	}
	return errors
}

func (e *SequentialExecutor) runOne(ctx context.Context, hookCtx *hook.Context, v validator.Validator) *validator.Result {
	if e.Timeout > 0 {
		ctx, cancel := context.WithTimeout(ctx, e.Timeout)
		defer cancel()
		return v.Validate(ctx, hookCtx)
	}
	return v.Validate(ctx, hookCtx)
}

// ParallelExecutor runs validators concurrently using semaphore-based
// worker pools partitioned by validator category.
type ParallelExecutor struct {
	CPUWorkers int
	IOWorkers  int
	GitWorkers int
	Timeout    time.Duration
}

// NewParallelExecutor creates a parallel executor with the given pool sizes
// and per-validator timeout.
func NewParallelExecutor(cpuWorkers, ioWorkers, gitWorkers int, timeout time.Duration) *ParallelExecutor {
	return &ParallelExecutor{
		CPUWorkers: cpuWorkers,
		IOWorkers:  ioWorkers,
		GitWorkers: gitWorkers,
		Timeout:    timeout,
	}
}

// Execute runs validators in parallel, using separate semaphores for each
// category (CPU, IO, Git) to control concurrency.
func (e *ParallelExecutor) Execute(ctx context.Context, hookCtx *hook.Context, validators []validator.Validator) []*transformer.ValidationError {
	if len(validators) == 0 {
		return nil
	}

	cpuSem := make(chan struct{}, e.CPUWorkers)
	ioSem := make(chan struct{}, e.IOWorkers)
	gitSem := make(chan struct{}, e.GitWorkers)

	type result struct {
		validator validator.Validator
		result    *validator.Result
	}

	results := make(chan result, len(validators))
	var wg sync.WaitGroup

	for _, v := range validators {
		wg.Add(1)
		go func(v validator.Validator) {
			defer wg.Done()

			// Acquire semaphore for this category
			sem := e.semaphoreFor(v.Category(), cpuSem, ioSem, gitSem)
			sem <- struct{}{}
			defer func() { <-sem }()

			var vCtx context.Context
			var cancel context.CancelFunc
			if e.Timeout > 0 {
				vCtx, cancel = context.WithTimeout(ctx, e.Timeout)
				defer cancel()
			} else {
				vCtx = ctx
			}

			r := v.Validate(vCtx, hookCtx)
			results <- result{validator: v, result: r}
		}(v)
	}

	// Close results channel when all goroutines finish
	go func() {
		wg.Wait()
		close(results)
	}()

	var errors []*transformer.ValidationError
	for r := range results {
		if r.result != nil && !r.result.Passed {
			errors = append(errors, toValidationError(r.validator, r.result))
		}
	}
	return errors
}

func (e *ParallelExecutor) semaphoreFor(cat validator.ValidatorCategory, cpu, io, git chan struct{}) chan struct{} {
	switch cat {
	case validator.CategoryIO:
		return io
	case validator.CategoryGit:
		return git
	default:
		return cpu
	}
}

// toValidationError converts a validator result into a ValidationError.
func toValidationError(v validator.Validator, r *validator.Result) *transformer.ValidationError {
	return &transformer.ValidationError{
		ValidatorName: v.Name(),
		Message:       r.Message,
		ShouldBlock:   r.ShouldBlock,
		ErrorCode:     r.Reference.Code,
		FixHint:       r.FixHint,
	}
}

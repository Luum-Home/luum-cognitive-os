// Package dispatcher is the core orchestrator for cos-dispatch. It ties
// together provider detection, transformer pipelines, validator dispatch,
// and response building.
package dispatcher

import (
	"context"
	"encoding/json"
	"fmt"
	"log"

	"github.com/luum/cos-dispatch/internal/config"
	"github.com/luum/cos-dispatch/internal/executor"
	"github.com/luum/cos-dispatch/internal/provider"
	"github.com/luum/cos-dispatch/internal/transformer"
	"github.com/luum/cos-dispatch/internal/validator"
	"github.com/luum/cos-dispatch/pkg/hook"
)

// Dispatcher orchestrates the full dispatch pipeline: parse, transform,
// validate, respond.
type Dispatcher struct {
	providerRegistry    *provider.Registry
	validatorRegistry   *validator.Registry
	transformerPipeline *transformer.Pipeline
	executor            executor.Executor
	config              *config.Config
	logger              *log.Logger

	// providerOverride forces a specific provider instead of auto-detect.
	providerOverride hook.Provider
}

// Option configures a Dispatcher.
type Option func(*Dispatcher)

// WithProviderOverride forces the dispatcher to use the named provider
// instead of auto-detecting from environment variables.
func WithProviderOverride(p hook.Provider) Option {
	return func(d *Dispatcher) {
		d.providerOverride = p
	}
}

// WithLogger sets a custom logger for the dispatcher.
func WithLogger(l *log.Logger) Option {
	return func(d *Dispatcher) {
		d.logger = l
	}
}

// New creates a Dispatcher with the given components.
func New(
	providerReg *provider.Registry,
	validatorReg *validator.Registry,
	pipeline *transformer.Pipeline,
	exec executor.Executor,
	cfg *config.Config,
	opts ...Option,
) *Dispatcher {
	d := &Dispatcher{
		providerRegistry:    providerReg,
		validatorRegistry:   validatorReg,
		transformerPipeline: pipeline,
		executor:            exec,
		config:              cfg,
		logger:              log.Default(),
	}
	for _, opt := range opts {
		opt(d)
	}
	return d
}

// Dispatch processes raw JSON from stdin through the full pipeline and returns
// the provider-specific JSON response.
func (d *Dispatcher) Dispatch(ctx context.Context, raw []byte) ([]byte, error) {
	// 1. Select provider
	prov := d.selectProvider()

	// 2. Parse raw JSON into canonical hook.Context
	hookCtx, err := prov.Parse(raw)
	if err != nil {
		return d.buildErrorResponse(prov, nil, fmt.Sprintf("parse error: %v", err))
	}

	d.logf("event=%s tool=%s provider=%s", hookCtx.Event, hookCtx.ToolName, hookCtx.Provider)

	// 3. Run transformer pre-pipeline
	hookCtx, err = d.transformerPipeline.RunPre(ctx, hookCtx)
	if err != nil {
		return d.buildErrorResponse(prov, hookCtx, fmt.Sprintf("pre-transform error: %v", err))
	}
	if hookCtx == nil {
		// Transformer signaled skip — return allow
		return d.buildAllowResponse(prov, nil, "skipped by transformer")
	}

	// 4. Find matching validators
	validators := d.validatorRegistry.FindValidators(hookCtx)
	d.logf("matched %d validators", len(validators))

	// 5. Execute validators
	validationErrors := d.executor.Execute(ctx, hookCtx, validators)

	// 6. Filter out disabled error codes
	validationErrors = d.filterDisabledCodes(validationErrors)

	// 7. Determine decision
	decision, message, details := d.buildDecision(validationErrors)

	// 8. Build provider-specific response
	resp := prov.BuildResponse(hookCtx, decision, message, details)

	// 9. Run transformer post-pipeline
	resp, err = d.transformerPipeline.RunPost(ctx, hookCtx, validationErrors, resp)
	if err != nil {
		d.logf("post-transform error (non-fatal): %v", err)
	}

	// 10. Marshal response
	return json.Marshal(resp)
}

func (d *Dispatcher) selectProvider() provider.Provider {
	if d.providerOverride != "" {
		if p, ok := d.providerRegistry.Get(d.providerOverride); ok {
			return p
		}
	}
	return d.providerRegistry.Detect()
}

func (d *Dispatcher) filterDisabledCodes(errors []*transformer.ValidationError) []*transformer.ValidationError {
	if d.config == nil {
		return errors
	}
	var filtered []*transformer.ValidationError
	for _, e := range errors {
		if e.ErrorCode != "" && d.config.IsCodeDisabled(e.ErrorCode) {
			d.logf("suppressed disabled error code %s from %s", e.ErrorCode, e.ValidatorName)
			continue
		}
		filtered = append(filtered, e)
	}
	return filtered
}

func (d *Dispatcher) buildDecision(errors []*transformer.ValidationError) (decision, message, details string) {
	if len(errors) == 0 {
		return "allow", "", ""
	}

	// Check if any errors should block
	var blocking []*transformer.ValidationError
	var warnings []*transformer.ValidationError
	for _, e := range errors {
		if e.ShouldBlock {
			blocking = append(blocking, e)
		} else {
			warnings = append(warnings, e)
		}
	}

	if len(blocking) > 0 {
		// Use first blocking error as the primary message
		msg := blocking[0].Message
		detail := ""
		if blocking[0].FixHint != "" {
			detail = "Fix: " + blocking[0].FixHint
		}
		if len(blocking) > 1 {
			msg = fmt.Sprintf("%s (and %d more)", msg, len(blocking)-1)
		}
		return "deny", msg, detail
	}

	// Warnings only — allow with context
	msg := warnings[0].Message
	if len(warnings) > 1 {
		msg = fmt.Sprintf("%s (and %d more warnings)", msg, len(warnings)-1)
	}
	return "allow", msg, ""
}

func (d *Dispatcher) buildAllowResponse(prov provider.Provider, hookCtx *hook.Context, msg string) ([]byte, error) {
	resp := prov.BuildResponse(hookCtx, "allow", msg, "")
	return json.Marshal(resp)
}

func (d *Dispatcher) buildErrorResponse(prov provider.Provider, hookCtx *hook.Context, msg string) ([]byte, error) {
	// On internal errors, we allow the tool to proceed (fail-open)
	d.logf("internal error (fail-open): %s", msg)
	resp := prov.BuildResponse(hookCtx, "allow", msg, "")
	return json.Marshal(resp)
}

func (d *Dispatcher) logf(format string, args ...any) {
	if d.logger != nil {
		d.logger.Printf("[cos-dispatch] "+format, args...)
	}
}

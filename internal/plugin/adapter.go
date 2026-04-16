// Package plugin adapts existing bash hooks as cos-dispatch validators.
// It spawns bash hooks as subprocesses, communicates via JSON on stdin/stdout,
// and converts the result into the validator interface.
package plugin

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"time"

	"github.com/luum/cos-dispatch/internal/validator"
	"github.com/luum/cos-dispatch/pkg/hook"
	pluginapi "github.com/luum/cos-dispatch/pkg/plugin"
)

// BashAdapter wraps a bash hook script as a Validator.
type BashAdapter struct {
	name     string
	command  string
	category validator.ValidatorCategory
	timeout  time.Duration
}

// NewBashAdapter creates a new adapter for the given bash hook script.
func NewBashAdapter(name, command string, category validator.ValidatorCategory, timeout time.Duration) *BashAdapter {
	return &BashAdapter{
		name:     name,
		command:  command,
		category: category,
		timeout:  timeout,
	}
}

// Name returns the plugin validator name.
func (a *BashAdapter) Name() string {
	return a.name
}

// Category returns the validator category for worker pool selection.
func (a *BashAdapter) Category() validator.ValidatorCategory {
	return a.category
}

// Validate executes the bash hook script, sending the hook context as JSON
// on stdin and reading a ValidateResponse from stdout.
func (a *BashAdapter) Validate(ctx context.Context, hookCtx *hook.Context) *validator.Result {
	// Build the request
	req := pluginapi.ValidateRequest{
		Provider:   string(hookCtx.Provider),
		EventName:  string(hookCtx.Event),
		ToolFamily: string(hookCtx.ToolName),
		Command:    hookCtx.ToolInput.Command,
		FilePath:   hookCtx.ToolInput.FilePath,
	}

	reqJSON, err := json.Marshal(req)
	if err != nil {
		return validator.Fail(fmt.Sprintf("plugin %s: marshal request: %v", a.name, err))
	}

	// Apply timeout
	if a.timeout > 0 {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(ctx, a.timeout)
		defer cancel()
	}

	// Execute the command
	cmd := exec.CommandContext(ctx, "bash", a.command)
	cmd.Stdin = bytes.NewReader(reqJSON)

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		// Exit code 2 = block (the hook protocol convention)
		if exitErr, ok := err.(*exec.ExitError); ok && exitErr.ExitCode() == 2 {
			msg := stdout.String()
			if msg == "" {
				msg = stderr.String()
			}
			if msg == "" {
				msg = "blocked by plugin " + a.name
			}
			return validator.Fail(msg)
		}
		// Other errors are treated as plugin failures (warn, don't block)
		return validator.Warn(fmt.Sprintf("plugin %s: exec error: %v (stderr: %s)", a.name, err, stderr.String()))
	}

	// Parse JSON response from stdout
	if stdout.Len() == 0 {
		// No output = pass
		return validator.Pass()
	}

	var resp pluginapi.ValidateResponse
	if err := json.Unmarshal(stdout.Bytes(), &resp); err != nil {
		// Can't parse response; treat as pass with warning
		return validator.Warn(fmt.Sprintf("plugin %s: invalid response JSON: %v", a.name, err))
	}

	if resp.Passed {
		return validator.Pass()
	}

	result := &validator.Result{
		Passed:      false,
		Message:     resp.Message,
		ShouldBlock: resp.ShouldBlock,
		FixHint:     resp.FixHint,
		Reference: validator.Reference{
			Code: resp.ErrorCode,
		},
	}
	return result
}

// CategoryFromString converts a string category name to a ValidatorCategory.
func CategoryFromString(s string) validator.ValidatorCategory {
	switch s {
	case "io":
		return validator.CategoryIO
	case "git":
		return validator.CategoryGit
	default:
		return validator.CategoryCPU
	}
}

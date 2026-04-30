package runner

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"time"
)

// wrapperRelPath is the path to the artifact-persisting pytest wrapper,
// relative to ProjectRoot. cos-test routes all invocations through it so every
// run produces summary/failures/junit/inventory artifacts under
// .cognitive-os/reports/test-runs/ (ADR-072 transparency contract).
const wrapperRelPath = "scripts/pytest-with-summary.sh"

// InvocationOptions are scalar execution-policy inputs passed from cos-test to
// the shell wrapper. This keeps lane/resource policy in Go while preserving the
// wrapper as the persistent-reporting transport.
type InvocationOptions struct {
	Workers        string
	Lane           string
	TimeoutSeconds int
}

// RawInvocation runs pytest via scripts/pytest-with-summary.sh so that every
// cos-test focused/cluster/broad invocation persists analyzable artifacts
// (full-output.txt, summary.txt, failures.txt, junit.xml, inventory.md).
//
// If the wrapper is missing (e.g. consumed by a downstream project that did not
// install the cognitive-os scripts/), falls back to direct `python -m pytest`
// so the binary remains usable. Stdout/stderr stream to os.Stdout/os.Stderr.
//
// Returns the underlying *exec.ExitError (if any). Callers should treat any
// non-nil error as a non-zero exit.
func (r *PytestRunner) RawInvocation(args []string) error {
	return r.RawInvocationWithOptions(args, InvocationOptions{})
}

// RawInvocationWithOptions is RawInvocation plus explicit lane/worker scalars.
// Focused/cluster/broad should prefer this entry point so
// pytest-with-summary.sh does not need to infer policy from paths.
func (r *PytestRunner) RawInvocationWithOptions(args []string, opts InvocationOptions) error {
	if opts.TimeoutSeconds > 0 {
		ctx, cancel := context.WithTimeout(context.Background(), time.Duration(opts.TimeoutSeconds)*time.Second)
		defer cancel()
		cmd := exec.CommandContext(ctx, r.runnerProgram(), r.runnerArgs(args, opts)...)
		err := r.runCommand(cmd)
		if ctx.Err() == context.DeadlineExceeded {
			return fmt.Errorf("RESOURCE_EXHAUSTED: lane %q exceeded timeout budget %ds", opts.Lane, opts.TimeoutSeconds)
		}
		return err
	}
	cmd := exec.Command(r.runnerProgram(), r.runnerArgs(args, opts)...)
	return r.runCommand(cmd)
}

func (r *PytestRunner) runCommand(cmd *exec.Cmd) error {
	cmd.Dir = r.cfg.ProjectRoot
	cmd.Env = append(os.Environ(), "PYTHONDONTWRITEBYTECODE=1")
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

// PytestArgs returns the fully-qualified argv for the dry-run printer. Mirrors
// what RawInvocation will exec — wrapper if present, direct pytest otherwise.
func (r *PytestRunner) PytestArgs(args []string) []string {
	return r.PytestArgsWithOptions(args, InvocationOptions{})
}

// PytestArgsWithOptions returns the fully-qualified argv for the dry-run
// printer, including wrapper-only --workers/--lane flags when available.
func (r *PytestRunner) PytestArgsWithOptions(args []string, opts InvocationOptions) []string {
	return append([]string{r.runnerProgram()}, r.runnerArgs(args, opts)...)
}

// runnerProgram picks the wrapper if it exists in ProjectRoot, else direct python.
func (r *PytestRunner) runnerProgram() string {
	if r.wrapperAvailable() {
		return "bash"
	}
	return "python"
}

// runnerArgs builds the argv tail for whichever runner was selected.
func (r *PytestRunner) runnerArgs(args []string, opts InvocationOptions) []string {
	if r.wrapperAvailable() {
		out := []string{wrapperRelPath}
		if opts.Workers != "" {
			out = append(out, "--workers", opts.Workers)
		}
		if opts.Lane != "" {
			out = append(out, "--lane", opts.Lane)
		}
		// "--" separator preserves any args that look like wrapper flags
		// (e.g. -k, -m). Wrapper strips its own --workers before this point.
		out = append(out, "--")
		out = append(out, args...)
		return out
	}
	return append([]string{"-m", "pytest"}, args...)
}

// wrapperAvailable returns true when the artifact-persisting wrapper is
// reachable at <ProjectRoot>/scripts/pytest-with-summary.sh.
func (r *PytestRunner) wrapperAvailable() bool {
	if r.cfg.ProjectRoot == "" {
		return false
	}
	full := filepath.Join(r.cfg.ProjectRoot, wrapperRelPath)
	info, err := os.Stat(full)
	if err != nil {
		return false
	}
	return info.Mode().IsRegular()
}

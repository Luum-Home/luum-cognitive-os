package runner

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
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
	DockerPolicy   string
	CostPolicy     string
	ArtifactPolicy string
}

type resourceOutcomeArtifact struct {
	Lane           string `json:"lane"`
	Workers        string `json:"workers"`
	TimeoutSeconds int    `json:"timeout_seconds"`
	DockerPolicy   string `json:"docker_policy"`
	CostPolicy     string `json:"cost_policy"`
	ArtifactPolicy string `json:"artifact_policy"`
	Outcome        string `json:"outcome"`
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
			_ = r.WriteResourceOutcome(opts, "resource_exhausted")
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
		if opts.TimeoutSeconds > 0 {
			out = append(out, "--timeout-seconds", fmt.Sprintf("%d", opts.TimeoutSeconds))
		}
		if opts.DockerPolicy != "" {
			out = append(out, "--docker-policy", opts.DockerPolicy)
		}
		if opts.CostPolicy != "" {
			out = append(out, "--cost-policy", opts.CostPolicy)
		}
		if opts.ArtifactPolicy != "" {
			out = append(out, "--artifact-policy", opts.ArtifactPolicy)
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

// WriteResourceOutcome persists resource-policy metadata for outcomes that
// happen outside the shell wrapper (for example policy blocks and process
// timeouts). Normal pytest exits are written by scripts/pytest-with-summary.sh.
func (r *PytestRunner) WriteResourceOutcome(opts InvocationOptions, outcome string) error {
	reportRoot := os.Getenv("COS_TEST_REPORT_DIR")
	if reportRoot == "" {
		reportRoot = filepath.Join(r.cfg.ProjectRoot, ".cognitive-os", "reports", "test-runs")
	}
	lane := opts.Lane
	if strings.TrimSpace(lane) == "" {
		lane = "unknown"
	}
	if strings.TrimSpace(outcome) == "" {
		outcome = "unknown"
	}
	runDir := filepath.Join(reportRoot, fmt.Sprintf("%s-%s-%s", time.Now().UTC().Format("20060102T150405Z"), slug(lane), slug(outcome)))
	if err := os.MkdirAll(runDir, 0o755); err != nil {
		return err
	}
	artifact := resourceOutcomeArtifact{
		Lane:           opts.Lane,
		Workers:        opts.Workers,
		TimeoutSeconds: opts.TimeoutSeconds,
		DockerPolicy:   opts.DockerPolicy,
		CostPolicy:     opts.CostPolicy,
		ArtifactPolicy: opts.ArtifactPolicy,
		Outcome:        outcome,
	}
	body, err := json.MarshalIndent(artifact, "", "  ")
	if err != nil {
		return err
	}
	body = append(body, '\n')
	if err := os.WriteFile(filepath.Join(runDir, "resource-policy.json"), body, 0o644); err != nil {
		return err
	}
	summary := fmt.Sprintf("# Resource Policy Outcome\n\n- Lane: %s\n- Workers: %s\n- Timeout seconds: %d\n- Docker policy: %s\n- Cost policy: %s\n- Artifact policy: %s\n- Resource outcome: %s\n",
		artifact.Lane,
		artifact.Workers,
		artifact.TimeoutSeconds,
		artifact.DockerPolicy,
		artifact.CostPolicy,
		artifact.ArtifactPolicy,
		artifact.Outcome,
	)
	if err := os.WriteFile(filepath.Join(runDir, "summary.txt"), []byte(summary), 0o644); err != nil {
		return err
	}
	if err := os.WriteFile(filepath.Join(runDir, "exit-code.txt"), []byte("2\n"), 0o644); err != nil {
		return err
	}
	latest := filepath.Join(reportRoot, "latest")
	_ = os.Remove(latest)
	_ = os.Symlink(runDir, latest)
	return nil
}

func slug(value string) string {
	value = strings.ToLower(strings.TrimSpace(value))
	if value == "" {
		return "unknown"
	}
	var b strings.Builder
	lastDash := false
	for _, r := range value {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') {
			b.WriteRune(r)
			lastDash = false
			continue
		}
		if !lastDash {
			b.WriteByte('-')
			lastDash = true
		}
	}
	return strings.Trim(b.String(), "-")
}

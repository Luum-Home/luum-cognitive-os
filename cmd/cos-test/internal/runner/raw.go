package runner

import (
	"os"
	"os/exec"
	"path/filepath"
)

// wrapperRelPath is the path to the artifact-persisting pytest wrapper,
// relative to ProjectRoot. cos-test routes all invocations through it so every
// run produces summary/failures/junit/inventory artifacts under
// .cognitive-os/reports/test-runs/ (ADR-072 transparency contract).
const wrapperRelPath = "scripts/pytest-with-summary.sh"

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
	cmd := exec.Command(r.runnerProgram(), r.runnerArgs(args)...)
	cmd.Dir = r.cfg.ProjectRoot
	cmd.Env = append(os.Environ(), "PYTHONDONTWRITEBYTECODE=1")
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

// PytestArgs returns the fully-qualified argv for the dry-run printer. Mirrors
// what RawInvocation will exec — wrapper if present, direct pytest otherwise.
func (r *PytestRunner) PytestArgs(args []string) []string {
	return append([]string{r.runnerProgram()}, r.runnerArgs(args)...)
}

// runnerProgram picks the wrapper if it exists in ProjectRoot, else direct python.
func (r *PytestRunner) runnerProgram() string {
	if r.wrapperAvailable() {
		return "bash"
	}
	return "python"
}

// runnerArgs builds the argv tail for whichever runner was selected.
func (r *PytestRunner) runnerArgs(args []string) []string {
	if r.wrapperAvailable() {
		// "--" separator preserves any args that look like wrapper flags
		// (e.g. -k, -m). Wrapper strips its own --workers before this point.
		return append([]string{wrapperRelPath, "--"}, args...)
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

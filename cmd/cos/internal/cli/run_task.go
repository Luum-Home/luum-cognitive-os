package cli

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/spf13/cobra"
)

const (
	runTaskDefaultCriterionTimeout = 300
	runTaskStatusPassed            = "passed"
	runTaskStatusFailed            = "failed"
	runTaskStatusBlocked           = "blocked"
	runTaskStatusTimedOut          = "timed_out"
	runTaskWorktreeIsolation       = "worktree"
	runTaskTempdirIsolation        = "tempdir"
)

var (
	runTaskPayloadPath   string
	runTaskWorkspacePath string
	runTaskArtifactsPath string
)

var runTaskCmd = &cobra.Command{
	Use:          "run-task",
	SilenceUsage: true,
	Short:        "Run a headless task in an isolated workspace",
	Long: `Run a Phase 1 headless task in an isolated workspace and write task artifacts.

This single-node runtime does not require a broker, queue, workflow engine, or
Kubernetes. It validates the task contract, creates an isolated git worktree or
temporary workspace, optionally runs a provider/agent command, executes
acceptance criteria, and writes payload, preflight, execution, acceptance, diff,
outcome, and trust-report artifacts.

Examples:
  cos run-task --payload task.json --workspace /repo --artifacts /tmp/cos-task-123`,
	RunE: runTask,
}

func init() {
	runTaskCmd.Flags().StringVar(&runTaskPayloadPath, "payload", "", "Path to task payload JSON")
	runTaskCmd.Flags().StringVar(&runTaskWorkspacePath, "workspace", "", "Repository workspace path; overrides payload workspace.repo")
	runTaskCmd.Flags().StringVar(&runTaskArtifactsPath, "artifacts", "", "Artifact output directory; overrides payload artifacts.dir")
	rootCmd.AddCommand(runTaskCmd)
}

type runTaskPayload struct {
	SchemaVersion      int                 `json:"schema_version"`
	TaskID             string              `json:"task_id"`
	Title              string              `json:"title"`
	Description        string              `json:"description"`
	ExecutionProfile   string              `json:"execution_profile,omitempty"`
	Execution          runTaskExecution    `json:"execution,omitempty"`
	Workspace          runTaskWorkspace    `json:"workspace"`
	Artifacts          runTaskArtifacts    `json:"artifacts"`
	AcceptanceCriteria []runTaskAcceptance `json:"acceptance_criteria"`
	Limits             runTaskLimits       `json:"limits,omitempty"`
	Metadata           map[string]any      `json:"metadata,omitempty"`
}

type runTaskExecution struct {
	Mode           string `json:"mode,omitempty"`
	Provider       string `json:"provider,omitempty"`
	Command        string `json:"command,omitempty"`
	TimeoutSeconds int    `json:"timeout_seconds,omitempty"`
}

type runTaskWorkspace struct {
	Repo      string `json:"repo"`
	Ref       string `json:"ref,omitempty"`
	Isolation string `json:"isolation,omitempty"`
}

type runTaskArtifacts struct {
	Dir string `json:"dir"`
}

type runTaskAcceptance struct {
	ID             string `json:"id"`
	Command        string `json:"command"`
	TimeoutSeconds int    `json:"timeout_seconds,omitempty"`
}

type runTaskLimits struct {
	TimeoutSeconds int     `json:"timeout_seconds,omitempty"`
	MaxCostUSD     float64 `json:"max_cost_usd,omitempty"`
}

type runTaskPreflight struct {
	SchemaVersion      int       `json:"schema_version"`
	TaskID             string    `json:"task_id"`
	CheckedAt          time.Time `json:"checked_at"`
	Workspace          string    `json:"workspace"`
	ExecutionDir       string    `json:"execution_dir"`
	ArtifactsDir       string    `json:"artifacts_dir"`
	Isolation          string    `json:"isolation"`
	GitAvailable       bool      `json:"git_available"`
	WorkspaceIsGitRepo bool      `json:"workspace_is_git_repo"`
	CognitiveOSYaml    bool      `json:"cognitive_os_yaml"`
	InstallMetaJSON    bool      `json:"install_meta_json"`
	ExecutionProfile   string    `json:"execution_profile"`
	ExecutionMode      string    `json:"execution_mode"`
	ExecutionProvider  string    `json:"execution_provider,omitempty"`
	AcceptanceCount    int       `json:"acceptance_count"`
}

type runTaskExecutionReport struct {
	SchemaVersion   int       `json:"schema_version"`
	TaskID          string    `json:"task_id"`
	Status          string    `json:"status"`
	Mode            string    `json:"mode"`
	Provider        string    `json:"provider,omitempty"`
	Command         string    `json:"command,omitempty"`
	ExitCode        int       `json:"exit_code"`
	StartedAt       time.Time `json:"started_at"`
	FinishedAt      time.Time `json:"finished_at"`
	DurationSeconds float64   `json:"duration_seconds"`
	TimedOut        bool      `json:"timed_out"`
	LogFile         string    `json:"log_file"`
}

type runTaskAcceptanceReport struct {
	SchemaVersion int                       `json:"schema_version"`
	TaskID        string                    `json:"task_id"`
	Status        string                    `json:"status"`
	StartedAt     time.Time                 `json:"started_at"`
	FinishedAt    time.Time                 `json:"finished_at"`
	Results       []runTaskAcceptanceResult `json:"results"`
}

type runTaskAcceptanceResult struct {
	ID              string  `json:"id"`
	Command         string  `json:"command"`
	ExitCode        int     `json:"exit_code"`
	DurationSeconds float64 `json:"duration_seconds"`
	TimedOut        bool    `json:"timed_out"`
	LogFile         string  `json:"log_file"`
}

type runTaskOutcome struct {
	SchemaVersion int                       `json:"schema_version"`
	TaskID        string                    `json:"task_id"`
	Status        string                    `json:"status"`
	StartedAt     time.Time                 `json:"started_at"`
	FinishedAt    time.Time                 `json:"finished_at"`
	Workspace     runTaskOutcomeWorkspace   `json:"workspace"`
	ArtifactsDir  string                    `json:"artifacts_dir"`
	Execution     runTaskExecutionReport    `json:"execution"`
	Acceptance    []runTaskAcceptanceResult `json:"acceptance"`
	DiffPatch     string                    `json:"diff_patch"`
	TrustReport   string                    `json:"trust_report"`
}

type runTaskOutcomeWorkspace struct {
	SourceRepo   string `json:"source_repo"`
	ExecutionDir string `json:"execution_dir"`
	Isolation    string `json:"isolation"`
}

func runTask(cmd *cobra.Command, args []string) error {
	started := time.Now().UTC()
	if strings.TrimSpace(runTaskPayloadPath) == "" {
		return newExitError(2, fmt.Errorf("--payload is required"))
	}
	payload, raw, err := loadRunTaskPayload(runTaskPayloadPath)
	if err != nil {
		return newExitError(2, err)
	}
	workspace := firstNonEmpty(runTaskWorkspacePath, payload.Workspace.Repo)
	artifacts := firstNonEmpty(runTaskArtifactsPath, payload.Artifacts.Dir)
	if err := validateRunTaskPayload(payload, workspace, artifacts); err != nil {
		return newExitError(2, err)
	}
	workspaceAbs, err := filepath.Abs(workspace)
	if err != nil {
		return newExitError(2, fmt.Errorf("resolving workspace path: %w", err))
	}
	artifactsAbs, err := filepath.Abs(artifacts)
	if err != nil {
		return newExitError(2, fmt.Errorf("resolving artifacts path: %w", err))
	}
	if err := ensureDirectoryExists(workspaceAbs, "workspace"); err != nil {
		return newExitError(2, err)
	}
	if err := os.MkdirAll(artifactsAbs, 0755); err != nil {
		return newExitError(2, fmt.Errorf("creating artifacts directory: %w", err))
	}
	if err := os.WriteFile(filepath.Join(artifactsAbs, "payload.json"), raw, 0644); err != nil {
		return newExitError(2, fmt.Errorf("writing payload artifact: %w", err))
	}
	executionDir, isolation, err := prepareRunTaskWorkspace(payload, workspaceAbs, artifactsAbs)
	if err != nil {
		return writeBlockedRunTaskOutcome(payload, started, workspaceAbs, artifactsAbs, err)
	}
	preflight := collectRunTaskPreflight(payload, workspaceAbs, executionDir, artifactsAbs, isolation)
	if err := writeJSONFile(filepath.Join(artifactsAbs, "preflight.json"), preflight); err != nil {
		return newExitError(2, err)
	}
	execution, executionTimedOut, err := executeRunTaskAgent(payload, executionDir, artifactsAbs)
	if err != nil {
		return newExitError(2, err)
	}
	if err := writeJSONFile(filepath.Join(artifactsAbs, "execution.json"), execution); err != nil {
		return newExitError(2, err)
	}
	if executionTimedOut || execution.Status == runTaskStatusFailed {
		return finishRunTaskEarly(payload, execution, started, workspaceAbs, executionDir, artifactsAbs, isolation, execution.Status, executionTimedOut, "run-task execution")
	}
	acceptance, timedOut, err := executeRunTaskAcceptance(payload, executionDir, artifactsAbs)
	if err != nil {
		return newExitError(2, err)
	}
	if err := writeJSONFile(filepath.Join(artifactsAbs, "acceptance.json"), acceptance); err != nil {
		return newExitError(2, err)
	}
	if err := writeExecutionLog(filepath.Join(artifactsAbs, "execution.log"), acceptance); err != nil {
		return newExitError(2, err)
	}
	if err := writeRunTaskDiff(executionDir, filepath.Join(artifactsAbs, "diff.patch")); err != nil {
		return newExitError(2, err)
	}
	status := acceptance.Status
	outcome := buildRunTaskOutcome(payload, execution, started, time.Now().UTC(), workspaceAbs, executionDir, artifactsAbs, isolation, status, acceptance.Results)
	if err := writeJSONFile(filepath.Join(artifactsAbs, "outcome.json"), outcome); err != nil {
		return newExitError(2, err)
	}
	if err := writeTrustReport(filepath.Join(artifactsAbs, "trust-report.md"), outcome); err != nil {
		return newExitError(2, err)
	}
	fmt.Printf("run-task complete\n")
	fmt.Printf("task_id: %s\n", payload.TaskID)
	fmt.Printf("status: %s\n", status)
	fmt.Printf("workspace: %s\n", workspaceAbs)
	fmt.Printf("execution_dir: %s\n", executionDir)
	fmt.Printf("artifacts: %s\n", artifactsAbs)
	fmt.Printf("acceptance_criteria: %d\n", len(payload.AcceptanceCriteria))
	if timedOut {
		return newExitError(124, fmt.Errorf("run-task timed out"))
	}
	if status != runTaskStatusPassed {
		return newExitError(1, fmt.Errorf("run-task acceptance failed"))
	}
	return nil
}

func loadRunTaskPayload(path string) (runTaskPayload, []byte, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return runTaskPayload{}, nil, fmt.Errorf("reading payload: %w", err)
	}
	var payload runTaskPayload
	if err := json.Unmarshal(raw, &payload); err != nil {
		return runTaskPayload{}, nil, fmt.Errorf("parsing payload JSON: %w", err)
	}
	formatted, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return runTaskPayload{}, nil, fmt.Errorf("formatting payload JSON: %w", err)
	}
	return payload, append(formatted, '\n'), nil
}

func validateRunTaskPayload(payload runTaskPayload, workspace string, artifacts string) error {
	var missing []string
	if payload.SchemaVersion != 1 {
		return fmt.Errorf("schema_version must be 1")
	}
	if strings.TrimSpace(payload.TaskID) == "" {
		missing = append(missing, "task_id")
	}
	if strings.TrimSpace(payload.Title) == "" {
		missing = append(missing, "title")
	}
	if strings.TrimSpace(payload.Description) == "" {
		missing = append(missing, "description")
	}
	if strings.TrimSpace(workspace) == "" {
		missing = append(missing, "workspace.repo or --workspace")
	}
	if strings.TrimSpace(artifacts) == "" {
		missing = append(missing, "artifacts.dir or --artifacts")
	}
	if len(payload.AcceptanceCriteria) == 0 {
		missing = append(missing, "acceptance_criteria")
	}
	for i, criterion := range payload.AcceptanceCriteria {
		if strings.TrimSpace(criterion.ID) == "" {
			missing = append(missing, fmt.Sprintf("acceptance_criteria[%d].id", i))
		}
		if strings.TrimSpace(criterion.Command) == "" {
			missing = append(missing, fmt.Sprintf("acceptance_criteria[%d].command", i))
		}
	}
	if len(missing) > 0 {
		return fmt.Errorf("invalid run-task payload: missing %s", strings.Join(missing, ", "))
	}
	if strings.TrimSpace(payload.Execution.Command) != "" {
		if mode := firstNonEmpty(payload.Execution.Mode, "command"); mode != "command" {
			return fmt.Errorf("invalid run-task payload: execution.mode must be command")
		}
	} else if strings.TrimSpace(payload.Execution.Mode) != "" || strings.TrimSpace(payload.Execution.Provider) != "" {
		return fmt.Errorf("invalid run-task payload: execution.command is required when execution is configured")
	}
	isolation := strings.TrimSpace(payload.Workspace.Isolation)
	if isolation != "" && isolation != runTaskWorktreeIsolation && isolation != runTaskTempdirIsolation {
		return fmt.Errorf("invalid run-task payload: workspace.isolation must be worktree or tempdir")
	}
	return nil
}

func prepareRunTaskWorkspace(payload runTaskPayload, workspace string, artifacts string) (string, string, error) {
	executionDir := filepath.Join(artifacts, "execution-workspace")
	if err := os.RemoveAll(executionDir); err != nil {
		return "", "", fmt.Errorf("clearing execution workspace: %w", err)
	}
	isolation := strings.TrimSpace(payload.Workspace.Isolation)
	workspaceIsGit := isGitRepo(workspace)
	if isolation == "" {
		if workspaceIsGit && commandAvailable("git") {
			isolation = runTaskWorktreeIsolation
		} else {
			isolation = runTaskTempdirIsolation
		}
	}
	if isolation == runTaskWorktreeIsolation {
		if !workspaceIsGit {
			return "", isolation, fmt.Errorf("workspace.isolation=worktree requires a git repository")
		}
		return executionDir, isolation, createRunTaskWorktree(workspace, executionDir, payload.Workspace.Ref)
	}
	return executionDir, isolation, copyDirectory(workspace, executionDir)
}

func createRunTaskWorktree(workspace string, executionDir string, ref string) error {
	cmd := exec.Command("git", "worktree", "add", "--detach", executionDir, firstNonEmpty(ref, "HEAD"))
	cmd.Dir = workspace
	out, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("creating git worktree: %w: %s", err, strings.TrimSpace(string(out)))
	}
	return nil
}

func copyDirectory(src string, dst string) error {
	return filepath.WalkDir(src, func(path string, entry os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		rel, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}
		if rel == "." {
			return os.MkdirAll(dst, 0755)
		}
		if entry.IsDir() && (entry.Name() == ".git" || entry.Name() == ".cognitive-os") {
			return filepath.SkipDir
		}
		target := filepath.Join(dst, rel)
		info, err := entry.Info()
		if err != nil {
			return err
		}
		if entry.IsDir() {
			return os.MkdirAll(target, info.Mode())
		}
		if !info.Mode().IsRegular() {
			return nil
		}
		return copyFile(path, target, info.Mode())
	})
}

func copyFile(src string, dst string, mode os.FileMode) error {
	if err := os.MkdirAll(filepath.Dir(dst), 0755); err != nil {
		return err
	}
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	out, err := os.OpenFile(dst, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, mode)
	if err != nil {
		return err
	}
	defer out.Close()
	_, err = io.Copy(out, in)
	return err
}

func executeRunTaskAgent(payload runTaskPayload, executionDir string, artifacts string) (runTaskExecutionReport, bool, error) {
	started := time.Now()
	startedAt := started.UTC()
	command := strings.TrimSpace(payload.Execution.Command)
	if command == "" {
		report := runTaskExecutionReport{SchemaVersion: 1, TaskID: payload.TaskID, Status: "skipped", Mode: "none", ExitCode: 0, StartedAt: startedAt, FinishedAt: time.Now().UTC(), LogFile: "agent.log"}
		return report, false, os.WriteFile(filepath.Join(artifacts, "agent.log"), []byte("execution skipped: no execution.command configured\n"), 0644)
	}
	timeout := payload.Execution.TimeoutSeconds
	if timeout <= 0 {
		timeout = payload.Limits.TimeoutSeconds
	}
	if timeout <= 0 {
		timeout = runTaskDefaultCriterionTimeout
	}
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeout)*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, "/bin/sh", "-c", command)
	cmd.Dir = executionDir
	cmd.Env = append(os.Environ(), "COS_TASK_ID="+payload.TaskID, "COS_TASK_TITLE="+payload.Title, "COS_TASK_DESCRIPTION="+payload.Description, "COS_EXECUTION_PROFILE="+firstNonEmpty(payload.ExecutionProfile, "balanced"), "COS_EXECUTION_PROVIDER="+payload.Execution.Provider)
	var output bytes.Buffer
	cmd.Stdout = &output
	cmd.Stderr = &output
	err := cmd.Run()
	exitCode, status, timedOut := 0, runTaskStatusPassed, ctx.Err() == context.DeadlineExceeded
	if err != nil {
		exitCode, status = 1, runTaskStatusFailed
		var exitErr *exec.ExitError
		if timedOut {
			exitCode, status = 124, runTaskStatusTimedOut
		} else if errors.As(err, &exitErr) {
			exitCode = exitErr.ExitCode()
		}
	}
	logFile := "agent.log"
	if err := os.WriteFile(filepath.Join(artifacts, logFile), output.Bytes(), 0644); err != nil {
		return runTaskExecutionReport{}, false, fmt.Errorf("writing agent log: %w", err)
	}
	return runTaskExecutionReport{SchemaVersion: 1, TaskID: payload.TaskID, Status: status, Mode: firstNonEmpty(payload.Execution.Mode, "command"), Provider: payload.Execution.Provider, Command: command, ExitCode: exitCode, StartedAt: startedAt, FinishedAt: time.Now().UTC(), DurationSeconds: time.Since(started).Seconds(), TimedOut: timedOut, LogFile: logFile}, timedOut, nil
}

func executeRunTaskAcceptance(payload runTaskPayload, executionDir string, artifacts string) (runTaskAcceptanceReport, bool, error) {
	started := time.Now().UTC()
	results := make([]runTaskAcceptanceResult, 0, len(payload.AcceptanceCriteria))
	status, timedOut := runTaskStatusPassed, false
	for _, criterion := range payload.AcceptanceCriteria {
		result, err := executeRunTaskCriterion(criterion, executionDir, artifacts)
		if err != nil {
			return runTaskAcceptanceReport{}, false, err
		}
		results = append(results, result)
		if result.TimedOut {
			status, timedOut = runTaskStatusTimedOut, true
			break
		}
		if result.ExitCode != 0 {
			status = runTaskStatusFailed
			break
		}
	}
	return runTaskAcceptanceReport{SchemaVersion: 1, TaskID: payload.TaskID, Status: status, StartedAt: started, FinishedAt: time.Now().UTC(), Results: results}, timedOut, nil
}

func executeRunTaskCriterion(criterion runTaskAcceptance, executionDir string, artifacts string) (runTaskAcceptanceResult, error) {
	started := time.Now()
	timeout := criterion.TimeoutSeconds
	if timeout <= 0 {
		timeout = runTaskDefaultCriterionTimeout
	}
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeout)*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, "/bin/sh", "-c", criterion.Command)
	cmd.Dir = executionDir
	var output bytes.Buffer
	cmd.Stdout = &output
	cmd.Stderr = &output
	err := cmd.Run()
	exitCode := 0
	if err != nil {
		exitCode = 1
		var exitErr *exec.ExitError
		if ctx.Err() == context.DeadlineExceeded {
			exitCode = 124
		} else if errors.As(err, &exitErr) {
			exitCode = exitErr.ExitCode()
		}
	}
	logFile := fmt.Sprintf("acceptance-%s.log", sanitizeArtifactName(criterion.ID))
	if err := os.WriteFile(filepath.Join(artifacts, logFile), output.Bytes(), 0644); err != nil {
		return runTaskAcceptanceResult{}, fmt.Errorf("writing acceptance log: %w", err)
	}
	return runTaskAcceptanceResult{ID: criterion.ID, Command: criterion.Command, ExitCode: exitCode, DurationSeconds: time.Since(started).Seconds(), TimedOut: ctx.Err() == context.DeadlineExceeded, LogFile: logFile}, nil
}

func finishRunTaskEarly(payload runTaskPayload, execution runTaskExecutionReport, started time.Time, workspace string, executionDir string, artifacts string, isolation string, status string, timedOut bool, prefix string) error {
	_ = writeRunTaskDiff(executionDir, filepath.Join(artifacts, "diff.patch"))
	_ = writeJSONFile(filepath.Join(artifacts, "acceptance.json"), runTaskAcceptanceReport{SchemaVersion: 1, TaskID: payload.TaskID, Status: status, StartedAt: time.Now().UTC(), FinishedAt: time.Now().UTC()})
	outcome := buildRunTaskOutcome(payload, execution, started, time.Now().UTC(), workspace, executionDir, artifacts, isolation, status, nil)
	if err := writeJSONFile(filepath.Join(artifacts, "outcome.json"), outcome); err != nil {
		return newExitError(2, err)
	}
	if err := writeTrustReport(filepath.Join(artifacts, "trust-report.md"), outcome); err != nil {
		return newExitError(2, err)
	}
	if timedOut {
		return newExitError(124, fmt.Errorf("%s timed out", prefix))
	}
	return newExitError(1, fmt.Errorf("%s failed", prefix))
}

func writeExecutionLog(path string, acceptance runTaskAcceptanceReport) error {
	var builder strings.Builder
	fmt.Fprintf(&builder, "task_id=%s\nstatus=%s\n", acceptance.TaskID, acceptance.Status)
	for _, result := range acceptance.Results {
		fmt.Fprintf(&builder, "criterion=%s exit_code=%d timed_out=%t duration_seconds=%.3f log=%s\n", result.ID, result.ExitCode, result.TimedOut, result.DurationSeconds, result.LogFile)
	}
	return os.WriteFile(path, []byte(builder.String()), 0644)
}

func writeRunTaskDiff(executionDir string, diffPath string) error {
	if !isGitRepo(executionDir) {
		return os.WriteFile(diffPath, nil, 0644)
	}
	cmd := exec.Command("git", "diff", "--binary", "HEAD")
	cmd.Dir = executionDir
	out, err := cmd.Output()
	if err != nil {
		return fmt.Errorf("capturing git diff: %w", err)
	}
	return os.WriteFile(diffPath, out, 0644)
}

func buildRunTaskOutcome(payload runTaskPayload, execution runTaskExecutionReport, started time.Time, finished time.Time, workspace string, executionDir string, artifacts string, isolation string, status string, acceptance []runTaskAcceptanceResult) runTaskOutcome {
	return runTaskOutcome{SchemaVersion: 1, TaskID: payload.TaskID, Status: status, StartedAt: started, FinishedAt: finished, Workspace: runTaskOutcomeWorkspace{SourceRepo: workspace, ExecutionDir: executionDir, Isolation: isolation}, ArtifactsDir: artifacts, Execution: execution, Acceptance: acceptance, DiffPatch: "diff.patch", TrustReport: "trust-report.md"}
}

func writeBlockedRunTaskOutcome(payload runTaskPayload, started time.Time, workspace string, artifacts string, cause error) error {
	execution := runTaskExecutionReport{SchemaVersion: 1, TaskID: payload.TaskID, Status: "skipped", Mode: "none", LogFile: "agent.log"}
	outcome := buildRunTaskOutcome(payload, execution, started, time.Now().UTC(), workspace, "", artifacts, firstNonEmpty(payload.Workspace.Isolation, runTaskTempdirIsolation), runTaskStatusBlocked, nil)
	if writeErr := writeJSONFile(filepath.Join(artifacts, "outcome.json"), outcome); writeErr != nil {
		return newExitError(2, fmt.Errorf("%w; also failed to write blocked outcome: %v", cause, writeErr))
	}
	_ = os.WriteFile(filepath.Join(artifacts, "execution.log"), []byte(cause.Error()+"\n"), 0644)
	return newExitError(2, cause)
}

func writeTrustReport(path string, outcome runTaskOutcome) error {
	passed := 0
	for _, result := range outcome.Acceptance {
		if result.ExitCode == 0 && !result.TimedOut {
			passed++
		}
	}
	content := fmt.Sprintf("# Trust Report\n\nTRUST_REPORT: SCORE=%d STATUS=%s EVIDENCE=%d UNCERTAINTIES=%d\n\n- Task: %s\n- Outcome: %s\n- Execution: %s (%s)\n- Acceptance criteria passed: %d/%d\n- Diff artifact: %s\n", trustScoreForStatus(outcome.Status), trustStatusForOutcome(outcome.Status), len(outcome.Acceptance)+3, uncertaintyCountForStatus(outcome.Status), outcome.TaskID, outcome.Status, outcome.Execution.Status, outcome.Execution.Provider, passed, len(outcome.Acceptance), outcome.DiffPatch)
	return os.WriteFile(path, []byte(content), 0644)
}

func trustScoreForStatus(status string) int {
	switch status {
	case runTaskStatusPassed:
		return 82
	case runTaskStatusFailed:
		return 55
	case runTaskStatusTimedOut:
		return 45
	default:
		return 35
	}
}
func trustStatusForOutcome(status string) string {
	if status == runTaskStatusPassed {
		return "HIGH"
	}
	return "MEDIUM"
}
func uncertaintyCountForStatus(status string) int {
	if status == runTaskStatusPassed {
		return 1
	}
	return 3
}
func ensureDirectoryExists(path string, label string) error {
	info, err := os.Stat(path)
	if err != nil {
		return fmt.Errorf("%s does not exist: %s", label, path)
	}
	if !info.IsDir() {
		return fmt.Errorf("%s is not a directory: %s", label, path)
	}
	return nil
}
func collectRunTaskPreflight(payload runTaskPayload, workspace string, executionDir string, artifacts string, isolation string) runTaskPreflight {
	return runTaskPreflight{SchemaVersion: 1, TaskID: payload.TaskID, CheckedAt: time.Now().UTC(), Workspace: workspace, ExecutionDir: executionDir, ArtifactsDir: artifacts, Isolation: isolation, GitAvailable: commandAvailable("git"), WorkspaceIsGitRepo: isGitRepo(workspace), CognitiveOSYaml: fileExists(filepath.Join(workspace, "cognitive-os.yaml")), InstallMetaJSON: fileExists(filepath.Join(workspace, ".cognitive-os", "install-meta.json")), ExecutionProfile: firstNonEmpty(payload.ExecutionProfile, "balanced"), ExecutionMode: firstNonEmpty(payload.Execution.Mode, mapExecutionMode(payload.Execution.Command)), ExecutionProvider: payload.Execution.Provider, AcceptanceCount: len(payload.AcceptanceCriteria)}
}
func writeJSONFile(path string, value any) error {
	data, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return fmt.Errorf("formatting JSON %s: %w", path, err)
	}
	data = append(data, '\n')
	if err := os.WriteFile(path, data, 0644); err != nil {
		return fmt.Errorf("writing JSON %s: %w", path, err)
	}
	return nil
}
func firstNonEmpty(values ...string) string {
	for _, value := range values {
		trimmed := strings.TrimSpace(value)
		if trimmed != "" {
			return trimmed
		}
	}
	return ""
}
func commandAvailable(name string) bool { _, err := exec.LookPath(name); return err == nil }
func isGitRepo(dir string) bool {
	cmd := exec.Command("git", "rev-parse", "--is-inside-work-tree")
	cmd.Dir = dir
	out, err := cmd.Output()
	return err == nil && strings.TrimSpace(string(out)) == "true"
}
func fileExists(path string) bool { info, err := os.Stat(path); return err == nil && !info.IsDir() }
func mapExecutionMode(command string) string {
	if strings.TrimSpace(command) == "" {
		return "none"
	}
	return "command"
}
func sanitizeArtifactName(name string) string {
	var builder strings.Builder
	for _, r := range strings.ToLower(name) {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == '-' || r == '_' {
			builder.WriteRune(r)
		} else {
			builder.WriteRune('-')
		}
	}
	result := strings.Trim(builder.String(), "-")
	if result == "" {
		return "criterion"
	}
	return result
}

package cli

import (
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestE2E_RunTaskSuccessWithExecutionCommand(t *testing.T) {
	projectDir := createTestProject(t)
	artifactsDir := filepath.Join(t.TempDir(), "artifacts")
	payloadPath := filepath.Join(t.TempDir(), "task.json")
	writeRunTaskPayload(t, payloadPath, baseRunTaskPayload(projectDir, artifactsDir, map[string]any{
		"mode":     "command",
		"provider": "local-agent",
		"command":  "printf '%s' \"$COS_TASK_ID\" > agent-output.txt",
	}))

	out, exitCode := runCos(t, projectDir, "run-task", "--payload", payloadPath)

	if exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d. Output:\n%s", exitCode, out)
	}
	if !strings.Contains(out, "run-task complete") {
		t.Fatalf("expected completion output, got:\n%s", out)
	}
	for _, name := range []string{"payload.json", "preflight.json", "execution.json", "agent.log", "execution.log", "acceptance.json", "outcome.json", "diff.patch", "trust-report.md", "acceptance-unit.log"} {
		assertFileExists(t, filepath.Join(artifactsDir, name))
	}
	assertFileExists(t, filepath.Join(artifactsDir, "execution-workspace", "agent-output.txt"))
	assertJSONContains(t, filepath.Join(artifactsDir, "execution.json"), `"provider": "local-agent"`)
	assertJSONContains(t, filepath.Join(artifactsDir, "outcome.json"), `"status": "passed"`)
}

func TestE2E_RunTaskRejectsInvalidPayloadWithExitCodeTwo(t *testing.T) {
	projectDir := createTestProject(t)
	payloadPath := filepath.Join(t.TempDir(), "task.json")
	writeRunTaskPayload(t, payloadPath, map[string]any{"schema_version": 1, "task_id": "task-123"})

	out, exitCode := runCos(t, projectDir, "run-task", "--payload", payloadPath, "--workspace", projectDir, "--artifacts", filepath.Join(t.TempDir(), "artifacts"))

	if exitCode != 2 {
		t.Fatalf("expected exit code 2, got %d. Output:\n%s", exitCode, out)
	}
	if !strings.Contains(out, "invalid run-task payload") || !strings.Contains(out, "acceptance_criteria") {
		t.Fatalf("expected invalid payload diagnosis, got:\n%s", out)
	}
}

func TestE2E_RunTaskWorktreeIsolation(t *testing.T) {
	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("git not available")
	}
	projectDir := createTestProject(t)
	runGit(t, projectDir, "init")
	runGit(t, projectDir, "config", "user.email", "cos@example.invalid")
	runGit(t, projectDir, "config", "user.name", "COS Test")
	runGit(t, projectDir, "add", "cognitive-os.yaml", ".claude/settings.json")
	runGit(t, projectDir, "commit", "-m", "initial")
	artifactsDir := filepath.Join(t.TempDir(), "artifacts")
	payload := baseRunTaskPayload(projectDir, artifactsDir, nil)
	payload["workspace"].(map[string]any)["isolation"] = "worktree"
	payloadPath := filepath.Join(t.TempDir(), "task.json")
	writeRunTaskPayload(t, payloadPath, payload)

	out, exitCode := runCos(t, projectDir, "run-task", "--payload", payloadPath)

	if exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d. Output:\n%s", exitCode, out)
	}
	assertJSONContains(t, filepath.Join(artifactsDir, "preflight.json"), `"isolation": "worktree"`)
}

func TestE2E_RunTaskExecutionFailureExitsOne(t *testing.T) {
	projectDir := createTestProject(t)
	artifactsDir := filepath.Join(t.TempDir(), "artifacts")
	payloadPath := filepath.Join(t.TempDir(), "task.json")
	writeRunTaskPayload(t, payloadPath, baseRunTaskPayload(projectDir, artifactsDir, map[string]any{"mode": "command", "provider": "local-agent", "command": "exit 9"}))

	out, exitCode := runCos(t, projectDir, "run-task", "--payload", payloadPath)

	if exitCode != 1 {
		t.Fatalf("expected exit code 1, got %d. Output:\n%s", exitCode, out)
	}
	assertJSONContains(t, filepath.Join(artifactsDir, "execution.json"), `"exit_code": 9`)
	assertJSONContains(t, filepath.Join(artifactsDir, "outcome.json"), `"status": "failed"`)
}

func TestE2E_RunTaskAcceptanceFailureExitsOne(t *testing.T) {
	projectDir := createTestProject(t)
	artifactsDir := filepath.Join(t.TempDir(), "artifacts")
	payload := baseRunTaskPayload(projectDir, artifactsDir, nil)
	payload["acceptance_criteria"] = []map[string]any{{"id": "failing", "command": "exit 7"}}
	payloadPath := filepath.Join(t.TempDir(), "task.json")
	writeRunTaskPayload(t, payloadPath, payload)

	out, exitCode := runCos(t, projectDir, "run-task", "--payload", payloadPath)

	if exitCode != 1 {
		t.Fatalf("expected exit code 1, got %d. Output:\n%s", exitCode, out)
	}
	assertJSONContains(t, filepath.Join(artifactsDir, "outcome.json"), `"status": "failed"`)
}

func TestE2E_RunTaskAcceptanceTimeoutExits124(t *testing.T) {
	projectDir := createTestProject(t)
	artifactsDir := filepath.Join(t.TempDir(), "artifacts")
	payload := baseRunTaskPayload(projectDir, artifactsDir, nil)
	payload["acceptance_criteria"] = []map[string]any{{"id": "slow", "command": "sleep 2", "timeout_seconds": 1}}
	payloadPath := filepath.Join(t.TempDir(), "task.json")
	writeRunTaskPayload(t, payloadPath, payload)

	out, exitCode := runCos(t, projectDir, "run-task", "--payload", payloadPath)

	if exitCode != 124 {
		t.Fatalf("expected exit code 124, got %d. Output:\n%s", exitCode, out)
	}
	assertJSONContains(t, filepath.Join(artifactsDir, "outcome.json"), `"status": "timed_out"`)
}

func baseRunTaskPayload(projectDir string, artifactsDir string, execution map[string]any) map[string]any {
	payload := map[string]any{
		"schema_version":    1,
		"task_id":           "task-123",
		"title":             "Validate task execution",
		"description":       "Prepare artifacts for a headless task.",
		"execution_profile": "balanced",
		"workspace": map[string]any{
			"repo":      projectDir,
			"isolation": "tempdir",
		},
		"artifacts": map[string]any{"dir": artifactsDir},
		"acceptance_criteria": []map[string]any{{
			"id":      "unit",
			"command": "test -f cognitive-os.yaml && test -f agent-output.txt || test ! -f agent-output.txt",
		}},
	}
	if execution != nil {
		payload["execution"] = execution
	}
	return payload
}

func writeRunTaskPayload(t *testing.T, path string, payload map[string]any) {
	t.Helper()
	data, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, append(data, '\n'), 0644); err != nil {
		t.Fatal(err)
	}
}

func assertFileExists(t *testing.T, path string) {
	t.Helper()
	info, err := os.Stat(path)
	if err != nil {
		t.Fatalf("expected file %s: %v", path, err)
	}
	if info.IsDir() {
		t.Fatalf("expected file, got directory: %s", path)
	}
}

func assertJSONContains(t *testing.T, path string, needle string) {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(data), needle) {
		t.Fatalf("expected %s to contain %q, got:\n%s", path, needle, data)
	}
}

func runGit(t *testing.T, dir string, args ...string) {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = dir
	if out, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("git %v failed: %v\n%s", args, err, out)
	}
}

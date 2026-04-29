package cli

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func copyProfileBootstrapRuntime(t *testing.T, projectDir string) {
	t.Helper()
	sourceRoot, err := filepath.Abs(filepath.Join("..", "..", "..", ".."))
	if err != nil {
		t.Fatal(err)
	}
	files := map[string]string{
		filepath.Join("scripts", "cos_profile_bootstrap.py"): filepath.Join("scripts", "cos_profile_bootstrap.py"),
		filepath.Join("lib", "project_profile_bootstrap.py"): filepath.Join("lib", "project_profile_bootstrap.py"),
		filepath.Join("lib", "memory_scanner.py"):            filepath.Join("lib", "memory_scanner.py"),
	}
	for srcRel, dstRel := range files {
		data, err := os.ReadFile(filepath.Join(sourceRoot, srcRel))
		if err != nil {
			t.Fatal(err)
		}
		dst := filepath.Join(projectDir, dstRel)
		if err := os.MkdirAll(filepath.Dir(dst), 0755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(dst, data, 0755); err != nil {
			t.Fatal(err)
		}
	}
}

func writeProfileSession(t *testing.T, projectDir string) {
	t.Helper()
	sessionDir := filepath.Join(projectDir, ".cognitive-os", "sessions", "go-cli-session")
	if err := os.MkdirAll(sessionDir, 0755); err != nil {
		t.Fatal(err)
	}
	meta := `{"session_id":"go-cli-session","start_time":"2026-04-29T00:00:00Z","working_directory":"` + projectDir + `"}` + "\n"
	if err := os.WriteFile(filepath.Join(sessionDir, "meta.json"), []byte(meta), 0644); err != nil {
		t.Fatal(err)
	}
}

func TestE2E_ProfileGenerateInspectPromoteWipe(t *testing.T) {
	projectDir := createTestProject(t)
	copyProfileBootstrapRuntime(t, projectDir)
	writeProfileSession(t, projectDir)
	if err := os.WriteFile(filepath.Join(projectDir, "pyproject.toml"), []byte("[project]\nname='demo'\n"), 0644); err != nil {
		t.Fatal(err)
	}

	out, code := runCos(t, projectDir, "profile", "generate")
	if code != 0 {
		t.Fatalf("cos profile generate failed (%d): %s", code, out)
	}
	draftPath := filepath.Join(projectDir, ".cognitive-os", "project-profile", "draft.json")
	if _, err := os.Stat(draftPath); err != nil {
		t.Fatalf("expected generated draft: %v", err)
	}

	out, code = runCos(t, projectDir, "profile", "inspect")
	if code != 0 {
		t.Fatalf("cos profile inspect failed (%d): %s", code, out)
	}
	if !strings.Contains(out, `"value": "python"`) {
		t.Fatalf("expected python profile signal, got: %s", out)
	}
	if strings.Contains(out, projectDir) {
		t.Fatalf("inspect output leaked absolute project dir: %s", out)
	}

	out, code = runCos(t, projectDir, "profile", "promote")
	if code == 0 {
		t.Fatalf("profile promotion without approval should fail: %s", out)
	}
	if !strings.Contains(out, "profile promotion requires") {
		t.Fatalf("expected approval error, got: %s", out)
	}

	out, code = runCos(t, projectDir, "profile", "promote", "--approved-by", "go-test")
	if code != 0 {
		t.Fatalf("approved profile promotion failed (%d): %s", code, out)
	}
	activePath := filepath.Join(projectDir, ".cognitive-os", "project-profile", "profile.json")
	if _, err := os.Stat(activePath); err != nil {
		t.Fatalf("expected promoted active profile: %v", err)
	}

	out, code = runCos(t, projectDir, "profile", "wipe")
	if code != 0 {
		t.Fatalf("cos profile wipe failed (%d): %s", code, out)
	}
	if _, err := os.Stat(activePath); !os.IsNotExist(err) {
		t.Fatalf("expected profile artifacts to be removed, got err=%v", err)
	}
}

package cli

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// ---------------------------------------------------------------------------
// cos setup — unit tests
// ---------------------------------------------------------------------------

func TestSetupNonInteractiveCreatesConfig(t *testing.T) {
	tmpDir := t.TempDir()

	// Create a minimal project with go.mod.
	os.WriteFile(filepath.Join(tmpDir, "go.mod"), []byte("module example.com/test\n\ngo 1.22\n"), 0644)

	// Initialize git so the wizard doesn't warn.
	runCos(t, tmpDir, "version") // just to verify binary works

	out, code := runCos(t, tmpDir, "setup", "--non-interactive")
	if code != 0 {
		t.Fatalf("cos setup --non-interactive exited %d: %s", code, out)
	}

	// Should have created cognitive-os.yaml.
	cosYaml := filepath.Join(tmpDir, "cognitive-os.yaml")
	if _, err := os.Stat(cosYaml); os.IsNotExist(err) {
		t.Fatal("cognitive-os.yaml was not created")
	}

	content, err := os.ReadFile(cosYaml)
	if err != nil {
		t.Fatal(err)
	}

	s := string(content)
	if !strings.Contains(s, "phase: stabilization") {
		t.Errorf("expected stabilization phase (team default), got:\n%s", s)
	}
	if !strings.Contains(s, "profile: standard") {
		t.Errorf("expected standard profile (team default), got:\n%s", s)
	}
}

func TestSetupPresetSoloDev(t *testing.T) {
	tmpDir := t.TempDir()
	os.WriteFile(filepath.Join(tmpDir, "go.mod"), []byte("module example.com/test\n\ngo 1.22\n"), 0644)

	out, code := runCos(t, tmpDir, "setup", "--preset", "solo-dev")
	if code != 0 {
		t.Fatalf("cos setup --preset solo-dev exited %d: %s", code, out)
	}

	content, err := os.ReadFile(filepath.Join(tmpDir, "cognitive-os.yaml"))
	if err != nil {
		t.Fatal(err)
	}

	s := string(content)
	if !strings.Contains(s, "phase: reconstruction") {
		t.Errorf("expected reconstruction phase for solo-dev, got:\n%s", s)
	}
	if !strings.Contains(s, "profile: minimal") {
		t.Errorf("expected minimal profile for solo-dev, got:\n%s", s)
	}
}

func TestSetupPresetEnterprise(t *testing.T) {
	tmpDir := t.TempDir()
	os.WriteFile(filepath.Join(tmpDir, "package.json"), []byte(`{"name": "enterprise-app"}`), 0644)

	out, code := runCos(t, tmpDir, "setup", "--preset", "enterprise")
	if code != 0 {
		t.Fatalf("cos setup --preset enterprise exited %d: %s", code, out)
	}

	content, err := os.ReadFile(filepath.Join(tmpDir, "cognitive-os.yaml"))
	if err != nil {
		t.Fatal(err)
	}

	s := string(content)
	if !strings.Contains(s, "phase: production") {
		t.Errorf("expected production phase for enterprise, got:\n%s", s)
	}
	if !strings.Contains(s, "profile: paranoid") {
		t.Errorf("expected paranoid profile for enterprise, got:\n%s", s)
	}
	if !strings.Contains(s, "agent_teams: true") {
		t.Errorf("expected agent_teams: true for enterprise, got:\n%s", s)
	}
}

func TestSetupInvalidPreset(t *testing.T) {
	tmpDir := t.TempDir()

	out, code := runCos(t, tmpDir, "setup", "--preset", "invalid-preset")
	if code == 0 {
		t.Fatalf("expected non-zero exit for invalid preset, got 0: %s", out)
	}
	if !strings.Contains(out, "unknown preset") {
		t.Errorf("expected 'unknown preset' in error, got: %s", out)
	}
}

func TestSetupDetectsLanguage(t *testing.T) {
	tmpDir := t.TempDir()
	os.WriteFile(filepath.Join(tmpDir, "go.mod"), []byte("module github.com/user/myapp\n\ngo 1.22\n"), 0644)

	out, code := runCos(t, tmpDir, "setup", "--non-interactive")
	if code != 0 {
		t.Fatalf("cos setup exited %d: %s", code, out)
	}

	// The generated config should use the detected project name.
	content, err := os.ReadFile(filepath.Join(tmpDir, "cognitive-os.yaml"))
	if err != nil {
		t.Fatal(err)
	}

	if !strings.Contains(string(content), "name: myapp") {
		t.Errorf("expected detected project name 'myapp', got:\n%s", content)
	}
}

func TestSetupCreatesClaudeDir(t *testing.T) {
	tmpDir := t.TempDir()

	out, code := runCos(t, tmpDir, "setup", "--non-interactive")
	if code != 0 {
		t.Fatalf("cos setup exited %d: %s", code, out)
	}

	claudeDir := filepath.Join(tmpDir, ".claude")
	if _, err := os.Stat(claudeDir); os.IsNotExist(err) {
		t.Fatal(".claude directory was not created")
	}
}

func TestSetupHelpOutput(t *testing.T) {
	tmpDir := t.TempDir()

	out, code := runCos(t, tmpDir, "setup", "--help")
	if code != 0 {
		t.Fatalf("cos setup --help exited %d: %s", code, out)
	}

	checks := []string{
		"interactive TUI wizard",
		"--non-interactive",
		"--preset",
		"--global",
		"solo-dev",
		"team",
		"enterprise",
	}

	for _, check := range checks {
		if !strings.Contains(out, check) {
			t.Errorf("help output missing %q.\nGot:\n%s", check, out)
		}
	}
}

func TestCoreGlobalRulesCount(t *testing.T) {
	// Verify the core global rules list has exactly 14 entries.
	if len(coreGlobalRules) != 14 {
		t.Errorf("expected 14 core global rules, got %d", len(coreGlobalRules))
	}
}

func TestCoreGlobalRulesExist(t *testing.T) {
	// Verify all core global rules exist in the rules/ directory.
	// Find project root by looking for rules/ directory.
	projectRoot := findCosSourceDir()
	if projectRoot == "" {
		t.Skip("COS source directory not found; skipping rule existence check")
	}

	for _, rule := range coreGlobalRules {
		rulePath := filepath.Join(projectRoot, "rules", rule)
		if _, err := os.Stat(rulePath); os.IsNotExist(err) {
			t.Errorf("core global rule missing: rules/%s", rule)
		}
	}
}

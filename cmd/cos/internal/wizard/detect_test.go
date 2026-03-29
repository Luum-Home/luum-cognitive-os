package wizard

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDetectLanguageGo(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "go.mod"), []byte("module example.com/myapp\n\ngo 1.22\n"), 0644)

	env := Detect(dir)
	if env.Language != "go" {
		t.Errorf("expected language 'go', got %q", env.Language)
	}
	if env.PackageManager != "go modules" {
		t.Errorf("expected package manager 'go modules', got %q", env.PackageManager)
	}
	if env.TestFramework != "go test" {
		t.Errorf("expected test framework 'go test', got %q", env.TestFramework)
	}
}

func TestDetectLanguageTypeScript(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "package.json"), []byte(`{"name": "my-ts-app"}`), 0644)
	os.WriteFile(filepath.Join(dir, "tsconfig.json"), []byte(`{}`), 0644)
	os.WriteFile(filepath.Join(dir, "yarn.lock"), []byte(""), 0644)

	env := Detect(dir)
	if env.Language != "typescript" {
		t.Errorf("expected language 'typescript', got %q", env.Language)
	}
	if env.PackageManager != "yarn" {
		t.Errorf("expected package manager 'yarn', got %q", env.PackageManager)
	}
}

func TestDetectLanguagePython(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "pyproject.toml"), []byte("[project]\nname = \"my-py-app\"\n"), 0644)
	os.WriteFile(filepath.Join(dir, "poetry.lock"), []byte(""), 0644)

	env := Detect(dir)
	if env.Language != "python" {
		t.Errorf("expected language 'python', got %q", env.Language)
	}
	if env.PackageManager != "poetry" {
		t.Errorf("expected package manager 'poetry', got %q", env.PackageManager)
	}
	if env.TestFramework != "pytest" {
		t.Errorf("expected test framework 'pytest', got %q", env.TestFramework)
	}
}

func TestDetectLanguageRust(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "Cargo.toml"), []byte("[package]\nname = \"my-rs-app\"\n"), 0644)

	env := Detect(dir)
	if env.Language != "rust" {
		t.Errorf("expected language 'rust', got %q", env.Language)
	}
	if env.PackageManager != "cargo" {
		t.Errorf("expected package manager 'cargo', got %q", env.PackageManager)
	}
}

func TestDetectLanguageUnknown(t *testing.T) {
	dir := t.TempDir()

	env := Detect(dir)
	if env.Language != "unknown" {
		t.Errorf("expected language 'unknown', got %q", env.Language)
	}
}

func TestDetectProjectNameFromGoMod(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "go.mod"), []byte("module github.com/user/myapp\n\ngo 1.22\n"), 0644)

	env := Detect(dir)
	if env.ProjectName != "myapp" {
		t.Errorf("expected project name 'myapp', got %q", env.ProjectName)
	}
}

func TestDetectProjectNameFromPackageJSON(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "package.json"), []byte(`{
  "name": "cool-project",
  "version": "1.0.0"
}`), 0644)

	env := Detect(dir)
	if env.ProjectName != "cool-project" {
		t.Errorf("expected project name 'cool-project', got %q", env.ProjectName)
	}
}

func TestDetectProjectNameFallback(t *testing.T) {
	dir := t.TempDir()

	env := Detect(dir)
	// Should fall back to directory name.
	expected := filepath.Base(dir)
	if env.ProjectName != expected {
		t.Errorf("expected project name %q (dir basename), got %q", expected, env.ProjectName)
	}
}

func TestDetectCIGitHub(t *testing.T) {
	dir := t.TempDir()
	os.MkdirAll(filepath.Join(dir, ".github", "workflows"), 0755)

	env := Detect(dir)
	if env.CISystem != "GitHub Actions" {
		t.Errorf("expected CI 'GitHub Actions', got %q", env.CISystem)
	}
}

func TestDetectCIGitLab(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, ".gitlab-ci.yml"), []byte(""), 0644)

	env := Detect(dir)
	if env.CISystem != "GitLab CI" {
		t.Errorf("expected CI 'GitLab CI', got %q", env.CISystem)
	}
}

func TestDetectExistingCOS(t *testing.T) {
	dir := t.TempDir()
	os.MkdirAll(filepath.Join(dir, ".cognitive-os"), 0755)
	os.WriteFile(filepath.Join(dir, ".cognitive-os", "version"), []byte("0.2.1"), 0644)

	env := Detect(dir)
	if !env.ExistingCOS {
		t.Error("expected ExistingCOS to be true")
	}
	if env.COSVersion != "0.2.1" {
		t.Errorf("expected COS version '0.2.1', got %q", env.COSVersion)
	}
}

func TestDetectMonorepo(t *testing.T) {
	tests := []struct {
		name     string
		setup    func(dir string)
		expected bool
	}{
		{
			name: "go workspace",
			setup: func(dir string) {
				os.WriteFile(filepath.Join(dir, "go.work"), []byte("go 1.22"), 0644)
			},
			expected: true,
		},
		{
			name: "nx monorepo",
			setup: func(dir string) {
				os.WriteFile(filepath.Join(dir, "nx.json"), []byte("{}"), 0644)
			},
			expected: true,
		},
		{
			name: "package.json workspaces",
			setup: func(dir string) {
				os.WriteFile(filepath.Join(dir, "package.json"), []byte(`{"name":"mono","workspaces":["packages/*"]}`), 0644)
			},
			expected: true,
		},
		{
			name: "not a monorepo",
			setup: func(dir string) {
				os.WriteFile(filepath.Join(dir, "package.json"), []byte(`{"name":"simple"}`), 0644)
			},
			expected: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			dir := t.TempDir()
			tt.setup(dir)

			env := Detect(dir)
			if env.IsMonorepo != tt.expected {
				t.Errorf("expected IsMonorepo=%v, got %v", tt.expected, env.IsMonorepo)
			}
		})
	}
}

func TestDetectVitestFramework(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "package.json"), []byte(`{"name": "app"}`), 0644)
	os.WriteFile(filepath.Join(dir, "vitest.config.ts"), []byte(""), 0644)

	env := Detect(dir)
	if env.TestFramework != "vitest" {
		t.Errorf("expected test framework 'vitest', got %q", env.TestFramework)
	}
}

func TestDetectJestFramework(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "package.json"), []byte(`{"name": "app"}`), 0644)
	os.WriteFile(filepath.Join(dir, "jest.config.ts"), []byte(""), 0644)

	env := Detect(dir)
	if env.TestFramework != "jest" {
		t.Errorf("expected test framework 'jest', got %q", env.TestFramework)
	}
}

func TestFormatDetection(t *testing.T) {
	env := DetectedEnv{
		ProjectName:    "test-app",
		Language:       "go",
		TestFramework:  "go test",
		TestFileCount:  42,
		DockerAvail:    true,
		DockerVersion:  "Docker 27.0.1",
		GitInitialized: true,
		GitBranch:      "main",
		GitClean:       true,
		CISystem:       "GitHub Actions",
		ExistingCOS:    false,
	}

	output := env.FormatDetection()

	checks := []string{
		"test-app",
		"Go",
		"go test",
		"42 test files",
		"Docker 27.0.1",
		"main branch",
		"GitHub Actions",
		"Not installed",
	}

	for _, check := range checks {
		if !strings.Contains(output, check) {
			t.Errorf("FormatDetection output missing %q.\nGot:\n%s", check, output)
		}
	}
}

func TestDetectPackageManagerPriority(t *testing.T) {
	// When multiple lock files exist, bun should win (checked first).
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "package.json"), []byte(`{"name": "app"}`), 0644)
	os.WriteFile(filepath.Join(dir, "bun.lockb"), []byte(""), 0644)
	os.WriteFile(filepath.Join(dir, "package-lock.json"), []byte(""), 0644)

	env := Detect(dir)
	if env.PackageManager != "bun" {
		t.Errorf("expected 'bun' (higher priority), got %q", env.PackageManager)
	}
}

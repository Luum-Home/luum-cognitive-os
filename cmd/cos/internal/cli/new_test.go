package cli

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// ---------------------------------------------------------------------------
// cos new — unit tests
// ---------------------------------------------------------------------------

func TestNewCreatesDirectory(t *testing.T) {
	tmpDir := t.TempDir()
	projName := "test-project"
	projDir := filepath.Join(tmpDir, projName)

	repoRoot := findRepoRoot(t)
	t.Setenv("COS_TEMPLATE_DIR", filepath.Join(repoRoot, "templates", "project-templates"))

	// Run cos new with --skip-init to avoid needing cos-init.sh in PATH.
	out, code := runCos(t, tmpDir, "new", projName, "--template", "minimal", "--skip-init")
	if code != 0 {
		t.Fatalf("cos new exited %d: %s", code, out)
	}

	if _, err := os.Stat(projDir); os.IsNotExist(err) {
		t.Fatalf("project directory %s was not created", projDir)
	}
}

func TestNewGoTemplateHasGoMod(t *testing.T) {
	tmpDir := t.TempDir()
	projName := "go-project"

	// Set COS_TEMPLATE_DIR so the binary can find templates.
	repoRoot := findRepoRoot(t)
	t.Setenv("COS_TEMPLATE_DIR", filepath.Join(repoRoot, "templates", "project-templates"))

	out, code := runCos(t, tmpDir, "new", projName, "--template", "go", "--skip-init")
	if code != 0 {
		t.Fatalf("cos new exited %d: %s", code, out)
	}

	goMod := filepath.Join(tmpDir, projName, "go.mod")
	if _, err := os.Stat(goMod); os.IsNotExist(err) {
		t.Fatalf("go.mod not found in %s", filepath.Join(tmpDir, projName))
	}

	content, err := os.ReadFile(goMod)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(content), "module go-project") {
		t.Errorf("go.mod does not contain 'module go-project', got:\n%s", content)
	}
}

func TestNewTypescriptHasPackageJson(t *testing.T) {
	tmpDir := t.TempDir()
	projName := "ts-project"

	repoRoot := findRepoRoot(t)
	t.Setenv("COS_TEMPLATE_DIR", filepath.Join(repoRoot, "templates", "project-templates"))

	out, code := runCos(t, tmpDir, "new", projName, "--template", "typescript", "--skip-init")
	if code != 0 {
		t.Fatalf("cos new exited %d: %s", code, out)
	}

	pkgJSON := filepath.Join(tmpDir, projName, "package.json")
	if _, err := os.Stat(pkgJSON); os.IsNotExist(err) {
		t.Fatalf("package.json not found in %s", filepath.Join(tmpDir, projName))
	}

	content, err := os.ReadFile(pkgJSON)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(content), `"name": "ts-project"`) {
		t.Errorf("package.json does not contain project name, got:\n%s", content)
	}
}

func TestNewMinimalHasCognitiveOsYaml(t *testing.T) {
	tmpDir := t.TempDir()
	projName := "minimal-project"

	repoRoot := findRepoRoot(t)
	t.Setenv("COS_TEMPLATE_DIR", filepath.Join(repoRoot, "templates", "project-templates"))

	out, code := runCos(t, tmpDir, "new", projName, "--template", "minimal", "--skip-init")
	if code != 0 {
		t.Fatalf("cos new exited %d: %s", code, out)
	}

	cosYaml := filepath.Join(tmpDir, projName, "cognitive-os.yaml")
	if _, err := os.Stat(cosYaml); os.IsNotExist(err) {
		t.Fatalf("cognitive-os.yaml not found")
	}
}

func TestNewReplacesPlaceholders(t *testing.T) {
	tmpDir := t.TempDir()
	projName := "my-custom-project"

	repoRoot := findRepoRoot(t)
	t.Setenv("COS_TEMPLATE_DIR", filepath.Join(repoRoot, "templates", "project-templates"))

	out, code := runCos(t, tmpDir, "new", projName, "--template", "go", "--phase", "stabilization", "--profile", "lean", "--skip-init")
	if code != 0 {
		t.Fatalf("cos new exited %d: %s", code, out)
	}

	// Check cognitive-os.yaml has replaced placeholders.
	cosYaml := filepath.Join(tmpDir, projName, "cognitive-os.yaml")
	content, err := os.ReadFile(cosYaml)
	if err != nil {
		t.Fatal(err)
	}

	s := string(content)
	if !strings.Contains(s, "name: my-custom-project") {
		t.Errorf("cognitive-os.yaml missing project name, got:\n%s", s)
	}
	if !strings.Contains(s, "phase: stabilization") {
		t.Errorf("cognitive-os.yaml missing phase, got:\n%s", s)
	}
	if !strings.Contains(s, "profile: lean") {
		t.Errorf("cognitive-os.yaml missing profile, got:\n%s", s)
	}

	// Check no template markers remain.
	if strings.Contains(s, "{{") || strings.Contains(s, "}}") {
		t.Errorf("cognitive-os.yaml still contains template markers:\n%s", s)
	}
}

func TestNewRejectsExistingDirectory(t *testing.T) {
	tmpDir := t.TempDir()
	projName := "existing-dir"

	// Create the directory first.
	os.MkdirAll(filepath.Join(tmpDir, projName), 0755)

	out, code := runCos(t, tmpDir, "new", projName, "--template", "minimal", "--skip-init")
	if code == 0 {
		t.Fatalf("expected non-zero exit when directory exists, got 0: %s", out)
	}
	if !strings.Contains(out, "already exists") {
		t.Errorf("expected 'already exists' in error output, got: %s", out)
	}
}

func TestNewRejectsInvalidTemplate(t *testing.T) {
	tmpDir := t.TempDir()

	out, code := runCos(t, tmpDir, "new", "bad-proj", "--template", "cobol", "--skip-init")
	if code == 0 {
		t.Fatalf("expected non-zero exit for invalid template, got 0: %s", out)
	}
	if !strings.Contains(out, "unknown template") {
		t.Errorf("expected 'unknown template' in error, got: %s", out)
	}
}

func TestNewCreatesGitRepo(t *testing.T) {
	tmpDir := t.TempDir()
	projName := "git-test"

	repoRoot := findRepoRoot(t)
	t.Setenv("COS_TEMPLATE_DIR", filepath.Join(repoRoot, "templates", "project-templates"))

	out, code := runCos(t, tmpDir, "new", projName, "--template", "minimal", "--skip-init")
	if code != 0 {
		t.Fatalf("cos new exited %d: %s", code, out)
	}

	gitDir := filepath.Join(tmpDir, projName, ".git")
	if _, err := os.Stat(gitDir); os.IsNotExist(err) {
		t.Fatalf(".git directory not found — git init was not run")
	}
}

func TestNewCreatesClaudeSettingsJson(t *testing.T) {
	tmpDir := t.TempDir()
	projName := "settings-test"

	repoRoot := findRepoRoot(t)
	t.Setenv("COS_TEMPLATE_DIR", filepath.Join(repoRoot, "templates", "project-templates"))

	out, code := runCos(t, tmpDir, "new", projName, "--template", "minimal", "--skip-init")
	if code != 0 {
		t.Fatalf("cos new exited %d: %s", code, out)
	}

	settingsFile := filepath.Join(tmpDir, projName, ".claude", "settings.json")
	if _, err := os.Stat(settingsFile); os.IsNotExist(err) {
		t.Fatalf(".claude/settings.json not found")
	}
}

// ---------------------------------------------------------------------------
// Behavior tests
// ---------------------------------------------------------------------------

func TestTemplateDirectoriesExist(t *testing.T) {
	repoRoot := findRepoRoot(t)
	for _, tmpl := range []string{"go", "typescript", "python", "minimal"} {
		dir := filepath.Join(repoRoot, "templates", "project-templates", tmpl)
		if _, err := os.Stat(dir); os.IsNotExist(err) {
			t.Errorf("template directory missing: %s", dir)
		}
	}
}

func TestEachTemplateHasCognitiveOsYaml(t *testing.T) {
	repoRoot := findRepoRoot(t)
	for _, tmpl := range []string{"go", "typescript", "python", "minimal"} {
		yamlFile := filepath.Join(repoRoot, "templates", "project-templates", tmpl, "cognitive-os.yaml.tmpl")
		if _, err := os.Stat(yamlFile); os.IsNotExist(err) {
			t.Errorf("cognitive-os.yaml.tmpl missing in template %s", tmpl)
		}
	}
}

func TestGettingStartedDocExists(t *testing.T) {
	repoRoot := findRepoRoot(t)
	doc := filepath.Join(repoRoot, "docs", "00-MOCs", "entrypoints", "getting-started-quick.md")
	if _, err := os.Stat(doc); os.IsNotExist(err) {
		t.Fatal("docs/00-MOCs/entrypoints/getting-started-quick.md does not exist")
	}

	content, err := os.ReadFile(doc)
	if err != nil {
		t.Fatal(err)
	}

	lines := strings.Split(string(content), "\n")
	if len(lines) > 100 {
		t.Errorf("getting-started-quick.md is %d lines, should be under 100", len(lines))
	}
}

func TestInstallCosShExists(t *testing.T) {
	repoRoot := findRepoRoot(t)
	script := filepath.Join(repoRoot, "scripts", "install-cos.sh")
	if _, err := os.Stat(script); os.IsNotExist(err) {
		t.Fatal("scripts/install-cos.sh does not exist")
	}

	info, err := os.Stat(script)
	if err != nil {
		t.Fatal(err)
	}
	// Check it has at least user execute permission.
	if info.Mode()&0100 == 0 {
		t.Errorf("install-cos.sh is not executable (mode: %o)", info.Mode())
	}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// findRepoRoot walks up from cwd to find the repo root (has go.mod with luum-agent-os).
func findRepoRoot(t *testing.T) string {
	t.Helper()
	dir, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	for {
		// Look for VERSION file (repo root marker) instead of go.mod
		// because cmd/cos/ has its own go.mod
		versionFile := filepath.Join(dir, "VERSION")
		if _, err := os.Stat(versionFile); err == nil {
			if _, err := os.Stat(filepath.Join(dir, "rules")); err == nil {
				return dir
			}
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			t.Fatal("could not find repo root (go.mod with luum-agent-os)")
		}
		dir = parent
	}
}

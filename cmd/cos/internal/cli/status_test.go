package cli

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

// ---------------------------------------------------------------------------
// Unit Tests — discoverPackages
// ---------------------------------------------------------------------------

func TestDiscoverPackages_Empty(t *testing.T) {
	dir := t.TempDir()
	// Create packages/ directory but leave it empty.
	if err := os.MkdirAll(filepath.Join(dir, "packages"), 0755); err != nil {
		t.Fatal(err)
	}

	statuses, err := discoverPackages(dir)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(statuses) != 0 {
		t.Errorf("expected 0 statuses, got %d", len(statuses))
	}
}

func TestDiscoverPackages_WithPackages(t *testing.T) {
	dir := t.TempDir()
	packagesDir := filepath.Join(dir, "packages")

	// Create two packages.
	createMinimalPackage(t, packagesDir, "alpha", "@test/alpha", "1.0.0")
	createMinimalPackage(t, packagesDir, "beta", "@test/beta", "2.1.0")

	statuses, err := discoverPackages(dir)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(statuses) != 2 {
		t.Fatalf("expected 2 statuses, got %d", len(statuses))
	}

	// Should be sorted by name.
	if statuses[0].Name != "@test/alpha" {
		t.Errorf("expected first package @test/alpha, got %s", statuses[0].Name)
	}
	if statuses[1].Name != "@test/beta" {
		t.Errorf("expected second package @test/beta, got %s", statuses[1].Name)
	}

	// No git tags exist, so all should be "never released".
	for _, s := range statuses {
		if s.LastTag != "" {
			t.Errorf("expected empty LastTag for %s, got %s", s.Name, s.LastTag)
		}
		if !s.HasChanges {
			t.Errorf("expected HasChanges=true for %s (no tag exists)", s.Name)
		}
	}
}

func TestDiscoverPackages_SkipsInvalidManifests(t *testing.T) {
	dir := t.TempDir()
	packagesDir := filepath.Join(dir, "packages")

	// Create one valid and one invalid package.
	createMinimalPackage(t, packagesDir, "valid", "@test/valid", "1.0.0")
	invalidDir := filepath.Join(packagesDir, "invalid")
	if err := os.MkdirAll(invalidDir, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(invalidDir, "cos-package.yaml"), []byte("not: valid: yaml: ["), 0644); err != nil {
		t.Fatal(err)
	}

	statuses, err := discoverPackages(dir)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(statuses) != 1 {
		t.Errorf("expected 1 status (skipping invalid), got %d", len(statuses))
	}
}

func TestDiscoverPackages_NoPackagesDir(t *testing.T) {
	dir := t.TempDir()
	// No packages/ directory at all.
	_, err := discoverPackages(dir)
	if err == nil {
		t.Error("expected error when packages/ directory doesn't exist")
	}
}

// ---------------------------------------------------------------------------
// Unit Tests — matchesFilter
// ---------------------------------------------------------------------------

func TestMatchesFilter(t *testing.T) {
	tests := []struct {
		name    string
		include string
		exclude string
		want    bool
	}{
		{"@luum/quality-gates", "", "", true},
		{"@luum/quality-gates", "quality", "", true},
		{"@luum/quality-gates", "trust", "", false},
		{"@luum/quality-gates", "", "quality", false},
		{"@luum/quality-gates", "quality,trust", "", true},
		{"@luum/quality-gates", "", "trust,sdd", true},
		{"@luum/quality-gates", "quality", "quality", false}, // exclude wins
	}

	for _, tt := range tests {
		got := matchesFilter(tt.name, tt.include, tt.exclude)
		if got != tt.want {
			t.Errorf("matchesFilter(%q, %q, %q) = %v, want %v",
				tt.name, tt.include, tt.exclude, got, tt.want)
		}
	}
}

// ---------------------------------------------------------------------------
// E2E Tests — cos status
// ---------------------------------------------------------------------------

func TestE2E_StatusCommand(t *testing.T) {
	dir := setupGitProjectWithPackages(t)

	out, exitCode := runCos(t, dir, "status")
	if exitCode != 0 {
		t.Fatalf("expected exit 0, got %d. Output:\n%s", exitCode, out)
	}

	// Should show both packages.
	if !strings.Contains(out, "@test/alpha") {
		t.Errorf("expected output to contain @test/alpha:\n%s", out)
	}
	if !strings.Contains(out, "@test/beta") {
		t.Errorf("expected output to contain @test/beta:\n%s", out)
	}
}

func TestE2E_StatusJSON(t *testing.T) {
	dir := setupGitProjectWithPackages(t)

	out, exitCode := runCos(t, dir, "status", "--json")
	if exitCode != 0 {
		t.Fatalf("expected exit 0, got %d. Output:\n%s", exitCode, out)
	}

	// JSON output should contain package names.
	if !strings.Contains(out, `"@test/alpha"`) {
		t.Errorf("expected JSON output to contain @test/alpha:\n%s", out)
	}
	if !strings.Contains(out, `"name"`) {
		t.Errorf("expected JSON output to contain 'name' field:\n%s", out)
	}
}

func TestE2E_StatusChangedOnly_NoChanges(t *testing.T) {
	dir := setupGitProjectWithTaggedPackages(t)

	out, exitCode := runCos(t, dir, "status", "--changed-only")
	if exitCode != 0 {
		t.Fatalf("expected exit 0, got %d. Output:\n%s", exitCode, out)
	}

	// With tagged packages and no changes, should show "No packages with unreleased changes"
	if !strings.Contains(out, "No packages") {
		t.Errorf("expected 'No packages' message, got:\n%s", out)
	}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func createMinimalPackage(t *testing.T, packagesDir, dirName, name, version string) {
	t.Helper()
	pkgDir := filepath.Join(packagesDir, dirName)
	if err := os.MkdirAll(pkgDir, 0755); err != nil {
		t.Fatal(err)
	}
	content := "name: \"" + name + "\"\nversion: \"" + version + "\"\ndescription: \"Test\"\nlicense: \"MIT\"\nexports: []\n"
	if err := os.WriteFile(filepath.Join(pkgDir, "cos-package.yaml"), []byte(content), 0644); err != nil {
		t.Fatal(err)
	}
}

func setupGitProjectWithPackages(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()

	// Initialize git.
	gitInit := exec.Command("git", "init")
	gitInit.Dir = dir
	if out, err := gitInit.CombinedOutput(); err != nil {
		t.Fatalf("git init: %v\n%s", err, out)
	}

	// Configure git user for commits.
	for _, cfg := range [][]string{
		{"config", "user.email", "test@test.com"},
		{"config", "user.name", "Test"},
	} {
		cmd := exec.Command("git", cfg...)
		cmd.Dir = dir
		if out, err := cmd.CombinedOutput(); err != nil {
			t.Fatalf("git config: %v\n%s", err, out)
		}
	}

	// Create project markers.
	writeTestFileE2E(t, dir, "cognitive-os.yaml", "project:\n  name: test\n")
	writeTestFileE2E(t, dir, "VERSION", "0.1.0\n")

	// Create packages.
	createMinimalPackage(t, filepath.Join(dir, "packages"), "alpha", "@test/alpha", "1.0.0")
	createMinimalPackage(t, filepath.Join(dir, "packages"), "beta", "@test/beta", "1.0.0")

	// Initial commit.
	gitAdd := exec.Command("git", "add", "-A")
	gitAdd.Dir = dir
	if out, err := gitAdd.CombinedOutput(); err != nil {
		t.Fatalf("git add: %v\n%s", err, out)
	}
	gitCommit := exec.Command("git", "commit", "-m", "init")
	gitCommit.Dir = dir
	if out, err := gitCommit.CombinedOutput(); err != nil {
		t.Fatalf("git commit: %v\n%s", err, out)
	}

	return dir
}

func setupGitProjectWithTaggedPackages(t *testing.T) string {
	t.Helper()
	dir := setupGitProjectWithPackages(t)

	// Tag both packages.
	for _, tag := range []string{"@test/alpha@1.0.0", "@test/beta@1.0.0"} {
		gitTag := exec.Command("git", "tag", tag)
		gitTag.Dir = dir
		if out, err := gitTag.CombinedOutput(); err != nil {
			t.Fatalf("git tag %s: %v\n%s", tag, err, out)
		}
	}

	return dir
}

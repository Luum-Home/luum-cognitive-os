package cli

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"luum-agent-os/cmd/cos/internal/manifest"
)

// ---------------------------------------------------------------------------
// Unit Tests — updateManifestVersion
// ---------------------------------------------------------------------------

func TestUpdateManifestVersion(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "cos-package.yaml")

	original := `name: "@test/pkg"
version: "1.0.0"
description: "Test"
license: "MIT"
exports: []
`
	if err := os.WriteFile(path, []byte(original), 0644); err != nil {
		t.Fatal(err)
	}

	if err := updateManifestVersion(path, "1.1.0"); err != nil {
		t.Fatalf("updateManifestVersion: %v", err)
	}

	// Read back and verify.
	m, err := manifest.ParseFile(path)
	if err != nil {
		t.Fatalf("parsing updated file: %v", err)
	}
	if m.Version != "1.1.0" {
		t.Errorf("expected version 1.1.0, got %s", m.Version)
	}
	if m.Name != "@test/pkg" {
		t.Errorf("expected name @test/pkg, got %s", m.Name)
	}
}

// ---------------------------------------------------------------------------
// Unit Tests — buildReleaseAllCommitMsg
// ---------------------------------------------------------------------------

func TestBuildReleaseAllCommitMsg_Single(t *testing.T) {
	plans := []releaseAllPlan{
		{Name: "@test/alpha", OldVersion: "1.0.0", NewVersion: "1.0.1"},
	}
	msg := buildReleaseAllCommitMsg(plans)
	if !strings.Contains(msg, "@test/alpha@1.0.1") {
		t.Errorf("expected commit msg to contain tag, got: %s", msg)
	}
}

func TestBuildReleaseAllCommitMsg_Multiple(t *testing.T) {
	plans := []releaseAllPlan{
		{Name: "@test/alpha", OldVersion: "1.0.0", NewVersion: "1.0.1"},
		{Name: "@test/beta", OldVersion: "2.0.0", NewVersion: "2.0.1"},
	}
	msg := buildReleaseAllCommitMsg(plans)
	if !strings.Contains(msg, "2 packages") {
		t.Errorf("expected '2 packages' in commit msg, got: %s", msg)
	}
	if !strings.Contains(msg, "@test/alpha") {
		t.Errorf("expected @test/alpha in commit msg, got: %s", msg)
	}
}

// ---------------------------------------------------------------------------
// Unit Tests — requireCleanGit
// ---------------------------------------------------------------------------

func TestRequireCleanGit_CleanRepo(t *testing.T) {
	dir := setupGitProjectWithPackages(t)
	err := requireCleanGit(dir)
	if err != nil {
		t.Errorf("expected clean git, got error: %v", err)
	}
}

func TestRequireCleanGit_DirtyRepo(t *testing.T) {
	dir := setupGitProjectWithPackages(t)

	// Create an uncommitted file.
	if err := os.WriteFile(filepath.Join(dir, "dirty.txt"), []byte("dirty"), 0644); err != nil {
		t.Fatal(err)
	}

	err := requireCleanGit(dir)
	if err == nil {
		t.Error("expected error for dirty working tree")
	}
	if !strings.Contains(err.Error(), "dirty") {
		t.Errorf("expected 'dirty' in error message, got: %v", err)
	}
}

// ---------------------------------------------------------------------------
// Unit Tests — findPackageDir
// ---------------------------------------------------------------------------

func TestFindPackageDir(t *testing.T) {
	dir := t.TempDir()
	createMinimalPackage(t, filepath.Join(dir, "packages"), "alpha", "@test/alpha", "1.0.0")

	pkgDir, err := findPackageDir(dir, "@test/alpha")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if pkgDir != "packages/alpha" {
		t.Errorf("expected packages/alpha, got %s", pkgDir)
	}
}

func TestFindPackageDir_NotFound(t *testing.T) {
	dir := t.TempDir()
	if err := os.MkdirAll(filepath.Join(dir, "packages"), 0755); err != nil {
		t.Fatal(err)
	}

	_, err := findPackageDir(dir, "@test/nonexistent")
	if err == nil {
		t.Error("expected error for non-existent package")
	}
}

// ---------------------------------------------------------------------------
// E2E Tests — cos release-all
// ---------------------------------------------------------------------------

func TestE2E_ReleaseAllDryRun(t *testing.T) {
	dir := setupGitProjectWithPackages(t)

	out, exitCode := runCos(t, dir, "release-all", "--patch", "--dry-run")
	if exitCode != 0 {
		t.Fatalf("expected exit 0, got %d. Output:\n%s", exitCode, out)
	}

	// Should show the release plan.
	if !strings.Contains(out, "@test/alpha") {
		t.Errorf("expected @test/alpha in output:\n%s", out)
	}
	if !strings.Contains(out, "1.0.1") {
		t.Errorf("expected bumped version 1.0.1 in output:\n%s", out)
	}
	if !strings.Contains(out, "dry run") {
		t.Errorf("expected 'dry run' message:\n%s", out)
	}
}

func TestE2E_ReleaseAllExecute(t *testing.T) {
	dir := setupGitProjectWithPackages(t)

	out, exitCode := runCos(t, dir, "release-all", "--patch", "--yes")
	if exitCode != 0 {
		t.Fatalf("expected exit 0, got %d. Output:\n%s", exitCode, out)
	}

	// Should show success.
	if !strings.Contains(out, "Released") {
		t.Errorf("expected 'Released' in output:\n%s", out)
	}

	// Verify tags were created.
	for _, tag := range []string{"@test/alpha@1.0.1", "@test/beta@1.0.1"} {
		tagCmd := exec.Command("git", "tag", "-l", tag)
		tagCmd.Dir = dir
		tagOut, err := tagCmd.Output()
		if err != nil {
			t.Fatalf("git tag -l %s: %v", tag, err)
		}
		if strings.TrimSpace(string(tagOut)) != tag {
			t.Errorf("expected tag %s to exist", tag)
		}
	}

	// Verify cos-package.yaml versions were updated.
	for _, pkg := range []string{"alpha", "beta"} {
		m, err := manifest.ParseFile(filepath.Join(dir, "packages", pkg, "cos-package.yaml"))
		if err != nil {
			t.Fatalf("parsing %s manifest: %v", pkg, err)
		}
		if m.Version != "1.0.1" {
			t.Errorf("expected %s version 1.0.1, got %s", pkg, m.Version)
		}
	}
}

func TestE2E_ReleaseAllMinor(t *testing.T) {
	dir := setupGitProjectWithPackages(t)

	out, exitCode := runCos(t, dir, "release-all", "--minor", "--dry-run")
	if exitCode != 0 {
		t.Fatalf("expected exit 0, got %d. Output:\n%s", exitCode, out)
	}

	if !strings.Contains(out, "1.1.0") {
		t.Errorf("expected minor bump to 1.1.0 in output:\n%s", out)
	}
}

func TestE2E_ReleaseAllWithInclude(t *testing.T) {
	dir := setupGitProjectWithPackages(t)

	out, exitCode := runCos(t, dir, "release-all", "--patch", "--dry-run", "--include", "alpha")
	if exitCode != 0 {
		t.Fatalf("expected exit 0, got %d. Output:\n%s", exitCode, out)
	}

	if !strings.Contains(out, "@test/alpha") {
		t.Errorf("expected @test/alpha in output:\n%s", out)
	}
	if strings.Contains(out, "@test/beta") {
		t.Errorf("did not expect @test/beta in output (excluded by --include):\n%s", out)
	}
}

func TestE2E_ReleaseAllWithExclude(t *testing.T) {
	dir := setupGitProjectWithPackages(t)

	out, exitCode := runCos(t, dir, "release-all", "--patch", "--dry-run", "--exclude", "alpha")
	if exitCode != 0 {
		t.Fatalf("expected exit 0, got %d. Output:\n%s", exitCode, out)
	}

	if strings.Contains(out, "@test/alpha") {
		t.Errorf("did not expect @test/alpha in output (--exclude alpha):\n%s", out)
	}
	if !strings.Contains(out, "@test/beta") {
		t.Errorf("expected @test/beta in output:\n%s", out)
	}
}

func TestE2E_ReleaseAllNoChanges(t *testing.T) {
	dir := setupGitProjectWithTaggedPackages(t)

	out, exitCode := runCos(t, dir, "release-all", "--patch", "--yes")
	if exitCode != 0 {
		t.Fatalf("expected exit 0, got %d. Output:\n%s", exitCode, out)
	}

	if !strings.Contains(out, "No packages") {
		t.Errorf("expected 'No packages' message:\n%s", out)
	}
}

func TestE2E_ReleaseAllDirtyRepo(t *testing.T) {
	dir := setupGitProjectWithPackages(t)

	// Make repo dirty.
	if err := os.WriteFile(filepath.Join(dir, "dirty.txt"), []byte("dirty"), 0644); err != nil {
		t.Fatal(err)
	}

	_, exitCode := runCos(t, dir, "release-all", "--patch", "--yes")
	if exitCode == 0 {
		t.Error("expected non-zero exit for dirty repo")
	}
}

func TestE2E_ReleaseAllMultipleBumpFlags(t *testing.T) {
	dir := setupGitProjectWithPackages(t)

	out, exitCode := runCos(t, dir, "release-all", "--patch", "--minor")
	if exitCode == 0 {
		t.Error("expected error for multiple bump flags")
	}
	if !strings.Contains(out, "only one bump flag") {
		t.Errorf("expected 'only one bump flag' error, got:\n%s", out)
	}
}

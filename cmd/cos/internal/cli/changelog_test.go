package cli

import (
	"os/exec"
	"strings"
	"testing"
)

// ---------------------------------------------------------------------------
// E2E Tests — cos changelog
// ---------------------------------------------------------------------------

func TestE2E_ChangelogAllPackages(t *testing.T) {
	dir := setupGitProjectWithTaggedPackages(t)

	// Add a commit to alpha.
	writeTestFileE2E(t, dir, "packages/alpha/change.md", "content")
	gitAdd := exec.Command("git", "add", "-A")
	gitAdd.Dir = dir
	if out, err := gitAdd.CombinedOutput(); err != nil {
		t.Fatalf("git add: %v\n%s", err, out)
	}
	gitCommit := exec.Command("git", "commit", "-m", "feat: changelog test commit")
	gitCommit.Dir = dir
	if out, err := gitCommit.CombinedOutput(); err != nil {
		t.Fatalf("git commit: %v\n%s", err, out)
	}

	out, exitCode := runCos(t, dir, "changelog")
	if exitCode != 0 {
		t.Fatalf("expected exit 0, got %d. Output:\n%s", exitCode, out)
	}

	if !strings.Contains(out, "@test/alpha") {
		t.Errorf("expected @test/alpha in output:\n%s", out)
	}
	if !strings.Contains(out, "changelog test commit") {
		t.Errorf("expected commit message in output:\n%s", out)
	}
	// Beta has no changes, should not appear.
	if strings.Contains(out, "@test/beta") {
		t.Errorf("did not expect @test/beta in output (no changes):\n%s", out)
	}
}

func TestE2E_ChangelogSpecificPackage(t *testing.T) {
	dir := setupGitProjectWithTaggedPackages(t)

	// Add commits to both packages.
	writeTestFileE2E(t, dir, "packages/alpha/a.md", "a")
	writeTestFileE2E(t, dir, "packages/beta/b.md", "b")
	gitAdd := exec.Command("git", "add", "-A")
	gitAdd.Dir = dir
	if out, err := gitAdd.CombinedOutput(); err != nil {
		t.Fatalf("git add: %v\n%s", err, out)
	}
	gitCommit := exec.Command("git", "commit", "-m", "feat: changes to both")
	gitCommit.Dir = dir
	if out, err := gitCommit.CombinedOutput(); err != nil {
		t.Fatalf("git commit: %v\n%s", err, out)
	}

	out, exitCode := runCos(t, dir, "changelog", "alpha")
	if exitCode != 0 {
		t.Fatalf("expected exit 0, got %d. Output:\n%s", exitCode, out)
	}

	if !strings.Contains(out, "@test/alpha") {
		t.Errorf("expected @test/alpha in output:\n%s", out)
	}
	if strings.Contains(out, "@test/beta") {
		t.Errorf("did not expect @test/beta in filtered output:\n%s", out)
	}
}

func TestE2E_ChangelogNoChanges(t *testing.T) {
	dir := setupGitProjectWithTaggedPackages(t)

	out, exitCode := runCos(t, dir, "changelog")
	if exitCode != 0 {
		t.Fatalf("expected exit 0, got %d. Output:\n%s", exitCode, out)
	}

	if !strings.Contains(out, "No packages") {
		t.Errorf("expected 'No packages' message:\n%s", out)
	}
}

func TestE2E_ChangelogWithSinceFlag(t *testing.T) {
	dir := setupGitProjectWithPackages(t)

	// Tag the initial state as v0.1.0.
	gitTag := exec.Command("git", "tag", "v0.1.0")
	gitTag.Dir = dir
	if out, err := gitTag.CombinedOutput(); err != nil {
		t.Fatalf("git tag: %v\n%s", err, out)
	}

	// Add a commit to alpha.
	writeTestFileE2E(t, dir, "packages/alpha/since.md", "since content")
	gitAdd := exec.Command("git", "add", "-A")
	gitAdd.Dir = dir
	if out, err := gitAdd.CombinedOutput(); err != nil {
		t.Fatalf("git add: %v\n%s", err, out)
	}
	gitCommit := exec.Command("git", "commit", "-m", "feat: after v0.1.0")
	gitCommit.Dir = dir
	if out, err := gitCommit.CombinedOutput(); err != nil {
		t.Fatalf("git commit: %v\n%s", err, out)
	}

	out, exitCode := runCos(t, dir, "changelog", "--since", "v0.1.0")
	if exitCode != 0 {
		t.Fatalf("expected exit 0, got %d. Output:\n%s", exitCode, out)
	}

	if !strings.Contains(out, "after v0.1.0") {
		t.Errorf("expected commit message in --since output:\n%s", out)
	}
}

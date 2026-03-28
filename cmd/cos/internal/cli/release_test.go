package cli

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestParseSemver(t *testing.T) {
	tests := []struct {
		input   string
		major   int
		minor   int
		patch   int
		wantErr bool
	}{
		{"0.1.0", 0, 1, 0, false},
		{"1.2.3", 1, 2, 3, false},
		{"v0.2.0", 0, 2, 0, false},
		{"10.20.30", 10, 20, 30, false},
		{"bad", 0, 0, 0, true},
		{"1.2", 0, 0, 0, true},
		{"1.2.3.4", 0, 0, 0, true},
		{"a.b.c", 0, 0, 0, true},
	}

	for _, tt := range tests {
		major, minor, patch, err := parseSemver(tt.input)
		if tt.wantErr {
			if err == nil {
				t.Errorf("parseSemver(%q) should error", tt.input)
			}
			continue
		}
		if err != nil {
			t.Errorf("parseSemver(%q) unexpected error: %v", tt.input, err)
			continue
		}
		if major != tt.major || minor != tt.minor || patch != tt.patch {
			t.Errorf("parseSemver(%q) = %d.%d.%d, want %d.%d.%d",
				tt.input, major, minor, patch, tt.major, tt.minor, tt.patch)
		}
	}
}

func TestBumpVersion(t *testing.T) {
	tests := []struct {
		current string
		major   bool
		minor   bool
		patch   bool
		want    string
	}{
		{"0.1.0", false, false, true, "0.1.1"},
		{"0.1.0", false, true, false, "0.2.0"},
		{"0.1.0", true, false, false, "1.0.0"},
		{"1.2.3", false, false, true, "1.2.4"},
		{"1.2.3", false, true, false, "1.3.0"},
		{"1.2.3", true, false, false, "2.0.0"},
	}

	for _, tt := range tests {
		got, err := bumpVersion(tt.current, tt.major, tt.minor, tt.patch)
		if err != nil {
			t.Errorf("bumpVersion(%q) unexpected error: %v", tt.current, err)
			continue
		}
		if got != tt.want {
			t.Errorf("bumpVersion(%q, major=%v, minor=%v, patch=%v) = %q, want %q",
				tt.current, tt.major, tt.minor, tt.patch, got, tt.want)
		}
	}
}

func TestUpdateChangelog(t *testing.T) {
	input := `# Changelog

## [Unreleased]
### Added
- new feature

## [0.1.0] - 2026-03-27
### Added
- initial release
`

	result := updateChangelog(input, "0.2.0")

	// Should have a new [Unreleased] section.
	if !strings.Contains(result, "## [Unreleased]") {
		t.Error("should contain new [Unreleased] section")
	}

	// Should have the versioned section.
	if !strings.Contains(result, "## [0.2.0]") {
		t.Error("should contain [0.2.0] section")
	}

	// The [Unreleased] should come before [0.2.0].
	unreleasedIdx := strings.Index(result, "## [Unreleased]")
	versionIdx := strings.Index(result, "## [0.2.0]")
	if unreleasedIdx >= versionIdx {
		t.Error("[Unreleased] should come before [0.2.0]")
	}

	// The original content should still be there.
	if !strings.Contains(result, "new feature") {
		t.Error("should preserve existing changelog entries")
	}
	if !strings.Contains(result, "## [0.1.0]") {
		t.Error("should preserve previous version entries")
	}
}

// ---------------------------------------------------------------------------
// Tests — scopedTagName
// ---------------------------------------------------------------------------

func TestScopedTagName(t *testing.T) {
	tests := []struct {
		name    string
		version string
		want    string
	}{
		{"@luum/safety-mesh", "1.0.0", "@luum/safety-mesh@1.0.0"},
		{"my-package", "0.2.0", "my-package@0.2.0"},
		{"@org/tool", "2.1.3", "@org/tool@2.1.3"},
	}

	for _, tt := range tests {
		got := scopedTagName(tt.name, tt.version)
		if got != tt.want {
			t.Errorf("scopedTagName(%q, %q) = %q, want %q", tt.name, tt.version, got, tt.want)
		}
	}
}

// ---------------------------------------------------------------------------
// Tests — resolveVersion
// ---------------------------------------------------------------------------

func TestResolveVersion_LdflagsOverride(t *testing.T) {
	// When Version is set via ldflags, resolveVersion returns it.
	original := Version
	Version = "9.9.9"
	defer func() { Version = original }()

	got := resolveVersion()
	if got != "9.9.9" {
		t.Errorf("resolveVersion() = %q, want %q", got, "9.9.9")
	}
}

func TestResolveVersion_FallsBackToFile(t *testing.T) {
	// When Version is empty, resolveVersion reads from VERSION file.
	original := Version
	Version = ""
	defer func() { Version = original }()

	// The function reads from project.FindRootOrCwd() which may or may not
	// find a VERSION file. We just verify it returns a non-panic string.
	got := resolveVersion()
	if got == "" {
		t.Error("resolveVersion() should return a non-empty string (either version or 'unknown')")
	}
}

// ---------------------------------------------------------------------------
// Tests — readVersionFile
// ---------------------------------------------------------------------------

func TestReadVersionFile_Found(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "VERSION"), []byte("1.2.3\n"), 0644); err != nil {
		t.Fatal(err)
	}
	got := readVersionFile(dir)
	if got != "1.2.3" {
		t.Errorf("readVersionFile() = %q, want %q", got, "1.2.3")
	}
}

func TestReadVersionFile_NotFound(t *testing.T) {
	dir := t.TempDir()
	got := readVersionFile(dir)
	if got != "unknown" {
		t.Errorf("readVersionFile() = %q, want %q", got, "unknown")
	}
}

// ---------------------------------------------------------------------------
// Tests — releaseReadinessCheck
// ---------------------------------------------------------------------------

func TestReleaseReadinessCheck_NoGitRepo(t *testing.T) {
	dir := t.TempDir()
	// No git repo — checks should still complete without panic.
	checks, _ := releaseReadinessCheck(dir, "0.1.0")
	if len(checks) == 0 {
		t.Error("expected at least one check result")
	}
}

func TestReleaseReadinessCheck_NoChangelog(t *testing.T) {
	dir := t.TempDir()
	checks, passed := releaseReadinessCheck(dir, "0.1.0")

	// Should have a changelog failure.
	found := false
	for _, c := range checks {
		if strings.Contains(c, "CHANGELOG") {
			found = true
		}
	}
	if !found {
		t.Error("expected a check mentioning CHANGELOG")
	}
	if passed {
		t.Error("should not pass with missing CHANGELOG")
	}
}

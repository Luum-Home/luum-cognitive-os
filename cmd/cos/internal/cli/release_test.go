package cli

import (
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

package manifest

import (
	"testing"
)

func TestParseVersion(t *testing.T) {
	tests := []struct {
		input               string
		major, minor, patch int
		wantErr             bool
	}{
		{"1.0.0", 1, 0, 0, false},
		{"0.1.0", 0, 1, 0, false},
		{"10.20.30", 10, 20, 30, false},
		{"0.0.0", 0, 0, 0, false},
		{"1.2.3-beta.1", 1, 2, 3, false},
		{"1.2.3+build.42", 1, 2, 3, false},
		{"1.2.3-rc.1+build.42", 1, 2, 3, false},
		{"v1.2.3", 1, 2, 3, false},
		// Invalid.
		{"1.0", 0, 0, 0, true},
		{"1", 0, 0, 0, true},
		{"", 0, 0, 0, true},
		{"abc", 0, 0, 0, true},
		{"1.2.abc", 0, 0, 0, true},
		{"1.abc.3", 0, 0, 0, true},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			major, minor, patch, err := ParseVersion(tt.input)
			if tt.wantErr {
				if err == nil {
					t.Errorf("ParseVersion(%q) expected error, got nil", tt.input)
				}
				return
			}
			if err != nil {
				t.Fatalf("ParseVersion(%q) unexpected error: %v", tt.input, err)
			}
			if major != tt.major || minor != tt.minor || patch != tt.patch {
				t.Errorf("ParseVersion(%q) = (%d, %d, %d), want (%d, %d, %d)",
					tt.input, major, minor, patch, tt.major, tt.minor, tt.patch)
			}
		})
	}
}

func TestCompareVersions(t *testing.T) {
	tests := []struct {
		a, b string
		want int
	}{
		// Equal.
		{"1.0.0", "1.0.0", 0},
		{"0.0.0", "0.0.0", 0},
		{"10.20.30", "10.20.30", 0},
		// Less than.
		{"1.0.0", "2.0.0", -1},
		{"1.0.0", "1.1.0", -1},
		{"1.0.0", "1.0.1", -1},
		{"0.9.9", "1.0.0", -1},
		{"1.2.3", "1.2.4", -1},
		// Greater than.
		{"2.0.0", "1.0.0", 1},
		{"1.1.0", "1.0.0", 1},
		{"1.0.1", "1.0.0", 1},
		{"1.0.0", "0.9.9", 1},
		// Pre-release tags are stripped (compared by numeric only).
		{"1.0.0-alpha", "1.0.0-beta", 0},
		{"1.0.0-alpha", "1.0.0", 0},
	}

	for _, tt := range tests {
		t.Run(tt.a+"_vs_"+tt.b, func(t *testing.T) {
			got := CompareVersions(tt.a, tt.b)
			if got != tt.want {
				t.Errorf("CompareVersions(%q, %q) = %d, want %d", tt.a, tt.b, got, tt.want)
			}
		})
	}
}

func TestMatchesConstraint_Exact(t *testing.T) {
	tests := []struct {
		version, constraint string
		want                bool
	}{
		{"1.0.0", "1.0.0", true},
		{"1.0.0", "1.0.1", false},
		{"2.0.0", "1.0.0", false},
		{"0.0.1", "0.0.1", true},
	}
	for _, tt := range tests {
		t.Run(tt.version+"_exact_"+tt.constraint, func(t *testing.T) {
			if got := MatchesConstraint(tt.version, tt.constraint); got != tt.want {
				t.Errorf("MatchesConstraint(%q, %q) = %v, want %v", tt.version, tt.constraint, got, tt.want)
			}
		})
	}
}

func TestMatchesConstraint_GreaterEqual(t *testing.T) {
	tests := []struct {
		version, constraint string
		want                bool
	}{
		{"1.0.0", ">=1.0.0", true},
		{"1.1.0", ">=1.0.0", true},
		{"2.0.0", ">=1.0.0", true},
		{"0.9.9", ">=1.0.0", false},
		{"0.0.1", ">=1.0.0", false},
	}
	for _, tt := range tests {
		t.Run(tt.version+"_gte_"+tt.constraint, func(t *testing.T) {
			if got := MatchesConstraint(tt.version, tt.constraint); got != tt.want {
				t.Errorf("MatchesConstraint(%q, %q) = %v, want %v", tt.version, tt.constraint, got, tt.want)
			}
		})
	}
}

func TestMatchesConstraint_LessThan(t *testing.T) {
	tests := []struct {
		version, constraint string
		want                bool
	}{
		{"1.9.9", "<2.0.0", true},
		{"0.0.1", "<2.0.0", true},
		{"2.0.0", "<2.0.0", false},
		{"2.0.1", "<2.0.0", false},
		{"3.0.0", "<2.0.0", false},
	}
	for _, tt := range tests {
		t.Run(tt.version+"_lt_"+tt.constraint, func(t *testing.T) {
			if got := MatchesConstraint(tt.version, tt.constraint); got != tt.want {
				t.Errorf("MatchesConstraint(%q, %q) = %v, want %v", tt.version, tt.constraint, got, tt.want)
			}
		})
	}
}

func TestMatchesConstraint_GreaterThan(t *testing.T) {
	tests := []struct {
		version, constraint string
		want                bool
	}{
		{"1.0.1", ">1.0.0", true},
		{"2.0.0", ">1.0.0", true},
		{"1.0.0", ">1.0.0", false},
		{"0.9.9", ">1.0.0", false},
	}
	for _, tt := range tests {
		t.Run(tt.version+"_gt_"+tt.constraint, func(t *testing.T) {
			if got := MatchesConstraint(tt.version, tt.constraint); got != tt.want {
				t.Errorf("MatchesConstraint(%q, %q) = %v, want %v", tt.version, tt.constraint, got, tt.want)
			}
		})
	}
}

func TestMatchesConstraint_LessEqual(t *testing.T) {
	tests := []struct {
		version, constraint string
		want                bool
	}{
		{"1.0.0", "<=1.0.0", true},
		{"0.9.9", "<=1.0.0", true},
		{"1.0.1", "<=1.0.0", false},
		{"2.0.0", "<=1.0.0", false},
	}
	for _, tt := range tests {
		t.Run(tt.version+"_lte_"+tt.constraint, func(t *testing.T) {
			if got := MatchesConstraint(tt.version, tt.constraint); got != tt.want {
				t.Errorf("MatchesConstraint(%q, %q) = %v, want %v", tt.version, tt.constraint, got, tt.want)
			}
		})
	}
}

func TestMatchesConstraint_NotEqual(t *testing.T) {
	tests := []struct {
		version, constraint string
		want                bool
	}{
		{"1.0.0", "!=1.0.0", false},
		{"1.0.1", "!=1.0.0", true},
		{"2.0.0", "!=1.0.0", true},
	}
	for _, tt := range tests {
		t.Run(tt.version+"_neq_"+tt.constraint, func(t *testing.T) {
			if got := MatchesConstraint(tt.version, tt.constraint); got != tt.want {
				t.Errorf("MatchesConstraint(%q, %q) = %v, want %v", tt.version, tt.constraint, got, tt.want)
			}
		})
	}
}

func TestMatchesConstraint_Caret(t *testing.T) {
	tests := []struct {
		version, constraint string
		want                bool
	}{
		// ^1.2.0: >=1.2.0, <2.0.0
		{"1.2.0", "^1.2.0", true},
		{"1.2.1", "^1.2.0", true},
		{"1.9.9", "^1.2.0", true},
		{"2.0.0", "^1.2.0", false},
		{"1.1.9", "^1.2.0", false},
		{"0.9.9", "^1.2.0", false},
		// ^0.2.3: >=0.2.3, <0.3.0 (major=0 pins minor)
		{"0.2.3", "^0.2.3", true},
		{"0.2.9", "^0.2.3", true},
		{"0.3.0", "^0.2.3", false},
		{"0.2.2", "^0.2.3", false},
		{"1.0.0", "^0.2.3", false},
		// ^0.0.3: >=0.0.3, <0.0.4 (major=0,minor=0 pins patch)
		{"0.0.3", "^0.0.3", true},
		{"0.0.4", "^0.0.3", false},
		{"0.1.0", "^0.0.3", false},
	}
	for _, tt := range tests {
		t.Run(tt.version+"_caret_"+tt.constraint, func(t *testing.T) {
			if got := MatchesConstraint(tt.version, tt.constraint); got != tt.want {
				t.Errorf("MatchesConstraint(%q, %q) = %v, want %v", tt.version, tt.constraint, got, tt.want)
			}
		})
	}
}

func TestMatchesConstraint_Tilde(t *testing.T) {
	tests := []struct {
		version, constraint string
		want                bool
	}{
		// ~1.2.3: >=1.2.3, <1.3.0
		{"1.2.3", "~1.2.3", true},
		{"1.2.9", "~1.2.3", true},
		{"1.2.99", "~1.2.3", true},
		{"1.3.0", "~1.2.3", false},
		{"1.2.2", "~1.2.3", false},
		{"2.0.0", "~1.2.3", false},
		{"0.9.9", "~1.2.3", false},
		// ~0.1.0: >=0.1.0, <0.2.0
		{"0.1.0", "~0.1.0", true},
		{"0.1.5", "~0.1.0", true},
		{"0.2.0", "~0.1.0", false},
	}
	for _, tt := range tests {
		t.Run(tt.version+"_tilde_"+tt.constraint, func(t *testing.T) {
			if got := MatchesConstraint(tt.version, tt.constraint); got != tt.want {
				t.Errorf("MatchesConstraint(%q, %q) = %v, want %v", tt.version, tt.constraint, got, tt.want)
			}
		})
	}
}

func TestMatchesConstraint_Range(t *testing.T) {
	tests := []struct {
		version, constraint string
		want                bool
	}{
		{"1.5.0", ">=1.0.0,<2.0.0", true},
		{"1.0.0", ">=1.0.0,<2.0.0", true},
		{"1.9.9", ">=1.0.0,<2.0.0", true},
		{"0.9.0", ">=1.0.0,<2.0.0", false},
		{"2.0.0", ">=1.0.0,<2.0.0", false},
		{"2.0.1", ">=1.0.0,<2.0.0", false},
		// Three-part range.
		{"1.5.0", ">=1.0.0,<2.0.0,!=1.3.0", true},
		{"1.3.0", ">=1.0.0,<2.0.0,!=1.3.0", false},
	}
	for _, tt := range tests {
		t.Run(tt.version+"_range_"+tt.constraint, func(t *testing.T) {
			if got := MatchesConstraint(tt.version, tt.constraint); got != tt.want {
				t.Errorf("MatchesConstraint(%q, %q) = %v, want %v", tt.version, tt.constraint, got, tt.want)
			}
		})
	}
}

func TestMatchesConstraint_Star(t *testing.T) {
	tests := []struct {
		version string
	}{
		{"0.0.1"},
		{"1.0.0"},
		{"99.99.99"},
	}
	for _, tt := range tests {
		t.Run(tt.version+"_star", func(t *testing.T) {
			if got := MatchesConstraint(tt.version, "*"); !got {
				t.Errorf("MatchesConstraint(%q, \"*\") = false, want true", tt.version)
			}
		})
	}
}

func TestMatchesConstraint_Empty(t *testing.T) {
	tests := []struct {
		version string
	}{
		{"0.0.1"},
		{"1.0.0"},
		{"99.99.99"},
	}
	for _, tt := range tests {
		t.Run(tt.version+"_empty", func(t *testing.T) {
			if got := MatchesConstraint(tt.version, ""); !got {
				t.Errorf("MatchesConstraint(%q, \"\") = false, want true", tt.version)
			}
		})
	}
}

func TestMatchesConstraint_InvalidVersion(t *testing.T) {
	// Invalid version should not match specific constraints.
	if MatchesConstraint("not-a-version", ">=1.0.0") {
		t.Error("invalid version should not match >=1.0.0")
	}
	// But wildcard still matches anything (including invalid).
	if !MatchesConstraint("not-a-version", "*") {
		t.Error("wildcard should match even invalid versions")
	}
}

func TestMatchesConstraint_WhitespaceHandling(t *testing.T) {
	if !MatchesConstraint("1.0.0", " >=1.0.0 ") {
		t.Error("should handle leading/trailing whitespace in constraint")
	}
	if !MatchesConstraint("1.5.0", " >=1.0.0 , <2.0.0 ") {
		t.Error("should handle whitespace around comma-separated constraints")
	}
}

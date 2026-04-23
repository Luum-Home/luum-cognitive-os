package installer

import (
	"path/filepath"
	"testing"
)

func TestCanonicalSkillsDir(t *testing.T) {
	got := canonicalSkillsDir("/project")
	want := filepath.Join("/project", ".cognitive-os", "skills", "cos")
	if got != want {
		t.Fatalf("expected %q, got %q", want, got)
	}
}

func TestCanonicalRulesDir(t *testing.T) {
	got := canonicalRulesDir("/project")
	want := filepath.Join("/project", ".cognitive-os", "rules", "cos")
	if got != want {
		t.Fatalf("expected %q, got %q", want, got)
	}
}

func TestClaudeSkillsProjectionDir(t *testing.T) {
	got := claudeSkillsProjectionDir("/project")
	want := filepath.Join("/project", ".claude", "skills")
	if got != want {
		t.Fatalf("expected %q, got %q", want, got)
	}
}

func TestClaudeRulesProjectionDir(t *testing.T) {
	got := claudeRulesProjectionDir("/project")
	want := filepath.Join("/project", ".claude", "rules", "cos")
	if got != want {
		t.Fatalf("expected %q, got %q", want, got)
	}
}

package manifest

import (
	"testing"
)

// validManifest returns a minimal valid manifest for testing.
func validManifest() *Manifest {
	return &Manifest{
		Name:    "@test/my-skill",
		Version: "1.0.0",
		License: "MIT",
		Provides: []string{"skill"},
		Exports: []Export{
			{Source: "SKILL.md", Type: "skill"},
		},
	}
}

func hasError(errs []ValidationError, field string) bool {
	for _, e := range errs {
		if e.Field == field {
			return true
		}
	}
	return false
}

func hasErrorContaining(errs []ValidationError, field, substr string) bool {
	for _, e := range errs {
		if e.Field == field {
			return true
		}
	}
	return false
}

func TestValidateRequiredFields(t *testing.T) {
	t.Run("missing name", func(t *testing.T) {
		m := validManifest()
		m.Name = ""
		errs := Validate(m)
		if !hasError(errs, "name") {
			t.Error("expected error for missing name")
		}
	})

	t.Run("missing version", func(t *testing.T) {
		m := validManifest()
		m.Version = ""
		errs := Validate(m)
		if !hasError(errs, "version") {
			t.Error("expected error for missing version")
		}
	})

	t.Run("missing license", func(t *testing.T) {
		m := validManifest()
		m.License = ""
		errs := Validate(m)
		if !hasError(errs, "license") {
			t.Error("expected error for missing license")
		}
	})

	t.Run("missing provides", func(t *testing.T) {
		m := validManifest()
		m.Provides = nil
		errs := Validate(m)
		if !hasError(errs, "provides") {
			t.Error("expected error for missing provides")
		}
	})

	t.Run("missing exports", func(t *testing.T) {
		m := validManifest()
		m.Exports = nil
		errs := Validate(m)
		if !hasError(errs, "exports") {
			t.Error("expected error for missing exports")
		}
	})

	t.Run("valid manifest passes", func(t *testing.T) {
		m := validManifest()
		errs := Validate(m)
		if len(errs) > 0 {
			t.Errorf("expected no errors, got %d: %v", len(errs), errs)
		}
	})
}

func TestValidateSemver(t *testing.T) {
	tests := []struct {
		version string
		valid   bool
	}{
		{"1.0.0", true},
		{"0.1.0", true},
		{"10.20.30", true},
		{"1.0.0-alpha", true},
		{"1.0.0-alpha.1", true},
		{"1.0.0+build.123", true},
		{"1.0.0-beta+build", true},
		{"1.0", false},
		{"1", false},
		{"v1.0.0", false},
		{"1.0.0.0", false},
		{"abc", false},
		{"", false},
	}

	for _, tt := range tests {
		t.Run(tt.version, func(t *testing.T) {
			m := validManifest()
			m.Version = tt.version
			errs := Validate(m)
			hasVersionErr := hasError(errs, "version")
			if tt.valid && hasVersionErr {
				t.Errorf("version %q should be valid but got error", tt.version)
			}
			if !tt.valid && !hasVersionErr {
				t.Errorf("version %q should be invalid but no error", tt.version)
			}
		})
	}
}

func TestValidateExportPaths(t *testing.T) {
	tests := []struct {
		name    string
		path    string
		wantErr bool
	}{
		{"relative path", "skills/my-skill/SKILL.md", false},
		{"simple file", "SKILL.md", false},
		{"nested relative", "hooks/pre-check.sh", false},
		{"absolute path", "/etc/passwd", true},
		{"parent traversal", "../../../etc/passwd", true},
		{"hidden traversal", "foo/../../bar", true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			m := validManifest()
			m.Exports = []Export{{Source: tt.path, Type: "skill"}}
			errs := Validate(m)
			hasSourceErr := hasError(errs, "exports[0].source")
			if tt.wantErr && !hasSourceErr {
				t.Errorf("path %q should produce error but didn't", tt.path)
			}
			if !tt.wantErr && hasSourceErr {
				t.Errorf("path %q should not produce error but did", tt.path)
			}
		})
	}
}

func TestValidateNameFormat(t *testing.T) {
	tests := []struct {
		name    string
		valid   bool
	}{
		// Scoped names.
		{"@community/code-reviewer", true},
		{"@luum/safety-mesh", true},
		{"@a/b", true},

		// Domain-based names.
		{"github.com/luum/safety-mesh", true},
		{"gitlab.com/org/my-pkg", true},

		// Plain names.
		{"my-skill", true},
		{"simple", true},
		{"a1", true},

		// Invalid names.
		{"", false},
		{"My-Skill", false},       // uppercase
		{"@/missing-scope", false}, // empty scope
		{"-starts-with-dash", false},
		{"has spaces", false},
		{"special!chars", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			m := validManifest()
			m.Name = tt.name
			errs := Validate(m)
			hasNameErr := hasError(errs, "name")
			if tt.valid && hasNameErr {
				t.Errorf("name %q should be valid but got error", tt.name)
			}
			if !tt.valid && !hasNameErr {
				t.Errorf("name %q should be invalid but no error", tt.name)
			}
		})
	}
}

func TestValidateHookEvent(t *testing.T) {
	t.Run("hook with valid event", func(t *testing.T) {
		m := validManifest()
		m.Exports = []Export{{
			Source:      "hooks/check.sh",
			Type:        "hook",
			HookEvent:   "PreToolUse",
			HookMatcher: "Agent",
		}}
		errs := Validate(m)
		if len(errs) > 0 {
			t.Errorf("expected no errors, got %v", errs)
		}
	})

	t.Run("hook missing event", func(t *testing.T) {
		m := validManifest()
		m.Exports = []Export{{
			Source:      "hooks/check.sh",
			Type:        "hook",
			HookMatcher: "Agent",
		}}
		errs := Validate(m)
		if !hasError(errs, "exports[0].hook_event") {
			t.Error("expected error for missing hook_event")
		}
	})

	t.Run("hook missing matcher", func(t *testing.T) {
		m := validManifest()
		m.Exports = []Export{{
			Source:    "hooks/check.sh",
			Type:      "hook",
			HookEvent: "PostToolUse",
		}}
		errs := Validate(m)
		if !hasError(errs, "exports[0].hook_matcher") {
			t.Error("expected error for missing hook_matcher")
		}
	})

	t.Run("hook invalid event", func(t *testing.T) {
		m := validManifest()
		m.Exports = []Export{{
			Source:      "hooks/check.sh",
			Type:        "hook",
			HookEvent:   "InvalidEvent",
			HookMatcher: "Agent",
		}}
		errs := Validate(m)
		if !hasError(errs, "exports[0].hook_event") {
			t.Error("expected error for invalid hook_event")
		}
	})

	t.Run("all valid hook events", func(t *testing.T) {
		events := []string{"PreToolUse", "PostToolUse", "SessionStart", "Stop"}
		for _, event := range events {
			m := validManifest()
			m.Exports = []Export{{
				Source:      "hooks/check.sh",
				Type:        "hook",
				HookEvent:   event,
				HookMatcher: "Agent",
			}}
			errs := Validate(m)
			if hasError(errs, "exports[0].hook_event") {
				t.Errorf("event %q should be valid", event)
			}
		}
	})
}

func TestValidateFeatureDeps(t *testing.T) {
	t.Run("valid feature", func(t *testing.T) {
		m := validManifest()
		m.Features = map[string]Feature{
			"strict-mode": {
				Description: "Enable strict checks",
				Exports: []Export{
					{Source: "rules/strict.md", Type: "rule"},
				},
			},
		}
		errs := Validate(m)
		if len(errs) > 0 {
			t.Errorf("expected no errors, got %v", errs)
		}
	})

	t.Run("non-kebab-case feature name", func(t *testing.T) {
		m := validManifest()
		m.Features = map[string]Feature{
			"strictMode": {
				Description: "Bad name",
			},
		}
		errs := Validate(m)
		if !hasError(errs, "features.strictMode") {
			t.Error("expected error for non-kebab-case feature name")
		}
	})

	t.Run("self-referencing feature", func(t *testing.T) {
		m := validManifest()
		m.Features = map[string]Feature{
			"loop": {
				Dependencies: map[string]Dependency{
					"loop": {Version: ">=1.0.0"},
				},
			},
		}
		errs := Validate(m)
		if !hasError(errs, "features.loop") {
			t.Error("expected error for self-referencing feature")
		}
	})
}

func TestValidateEmptyManifest(t *testing.T) {
	m := &Manifest{}
	errs := Validate(m)

	// Should have errors for all required fields.
	required := []string{"name", "version", "license", "provides", "exports"}
	for _, field := range required {
		if !hasError(errs, field) {
			t.Errorf("expected error for field %q", field)
		}
	}
}

func TestValidateKeywords(t *testing.T) {
	t.Run("too many keywords", func(t *testing.T) {
		m := validManifest()
		m.Keywords = make([]string, 11)
		for i := range m.Keywords {
			m.Keywords[i] = "keyword"
		}
		errs := Validate(m)
		if !hasError(errs, "keywords") {
			t.Error("expected error for too many keywords")
		}
	})

	t.Run("keyword too short", func(t *testing.T) {
		m := validManifest()
		m.Keywords = []string{"x"}
		errs := Validate(m)
		if !hasError(errs, "keywords[0]") {
			t.Error("expected error for short keyword")
		}
	})

	t.Run("valid keywords", func(t *testing.T) {
		m := validManifest()
		m.Keywords = []string{"safety", "hooks", "guardrails"}
		errs := Validate(m)
		for _, e := range errs {
			if e.Field == "keywords" || len(e.Field) > 8 && e.Field[:8] == "keywords" {
				t.Errorf("unexpected keywords error: %v", e)
			}
		}
	})
}

func TestValidatePublishMinScore(t *testing.T) {
	t.Run("valid score", func(t *testing.T) {
		score := 40
		m := validManifest()
		m.Publish = &PublishConfig{MinScore: &score}
		errs := Validate(m)
		if hasError(errs, "publish.min_score") {
			t.Error("score 40 should be valid")
		}
	})

	t.Run("score too high", func(t *testing.T) {
		score := 101
		m := validManifest()
		m.Publish = &PublishConfig{MinScore: &score}
		errs := Validate(m)
		if !hasError(errs, "publish.min_score") {
			t.Error("score 101 should be invalid")
		}
	})

	t.Run("negative score", func(t *testing.T) {
		score := -1
		m := validManifest()
		m.Publish = &PublishConfig{MinScore: &score}
		errs := Validate(m)
		if !hasError(errs, "publish.min_score") {
			t.Error("score -1 should be invalid")
		}
	})
}

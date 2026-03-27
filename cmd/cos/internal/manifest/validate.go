package manifest

import (
	"fmt"
	"path/filepath"
	"regexp"
	"strings"
)

// ValidationError represents a single validation issue.
type ValidationError struct {
	Field   string
	Message string
}

func (e ValidationError) Error() string {
	return fmt.Sprintf("%s: %s", e.Field, e.Message)
}

// Validate checks a manifest for semantic correctness and returns all errors found.
func Validate(m *Manifest) []ValidationError {
	var errs []ValidationError

	errs = append(errs, validateName(m)...)
	errs = append(errs, validateVersion(m)...)
	errs = append(errs, validateLicense(m)...)
	errs = append(errs, validateProvides(m)...)
	errs = append(errs, validateExports(m)...)
	errs = append(errs, validateKeywords(m)...)
	errs = append(errs, validateFeatures(m)...)
	errs = append(errs, validatePublish(m)...)

	return errs
}

// --- Name validation ---

// Scoped name: @scope/name
var scopedNameRegex = regexp.MustCompile(`^@[a-z0-9-]+/[a-z0-9]([a-z0-9._-]*[a-z0-9])?$`)

// Domain-based name: github.com/org/pkg
var domainNameRegex = regexp.MustCompile(`^[a-z0-9]+(\.[a-z0-9]+)+/[a-z0-9-]+/[a-z0-9][a-z0-9._-]*$`)

// Plain name: simple-name
var plainNameRegex = regexp.MustCompile(`^[a-z0-9]([a-z0-9._-]*[a-z0-9])?$`)

func validateName(m *Manifest) []ValidationError {
	if m.Name == "" {
		return []ValidationError{{Field: "name", Message: "required"}}
	}
	if !scopedNameRegex.MatchString(m.Name) &&
		!domainNameRegex.MatchString(m.Name) &&
		!plainNameRegex.MatchString(m.Name) {
		return []ValidationError{{Field: "name", Message: "must be lowercase alphanumeric with dots/hyphens (e.g., @scope/name or github.com/org/pkg)"}}
	}
	return nil
}

// --- Version validation ---

// Simplified semver regex: MAJOR.MINOR.PATCH with optional pre-release and build metadata.
var semverRegex = regexp.MustCompile(`^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)` +
	`(-([0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?` +
	`(\+([0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?$`)

func validateVersion(m *Manifest) []ValidationError {
	if m.Version == "" {
		return []ValidationError{{Field: "version", Message: "required"}}
	}
	if !semverRegex.MatchString(m.Version) {
		return []ValidationError{{Field: "version", Message: "must follow semver 2.0 (e.g., 1.0.0)"}}
	}
	return nil
}

// --- License validation ---

func validateLicense(m *Manifest) []ValidationError {
	if m.License == "" {
		return []ValidationError{{Field: "license", Message: "required"}}
	}
	return nil
}

// --- Provides validation ---

var validProvides = map[string]bool{
	"skill":    true,
	"rule":     true,
	"hook":     true,
	"agent":    true,
	"template": true,
	"bundle":   true,
}

func validateProvides(m *Manifest) []ValidationError {
	if len(m.Provides) == 0 {
		return []ValidationError{{Field: "provides", Message: "at least one of skill/rule/hook/agent/template/bundle required"}}
	}
	for i, p := range m.Provides {
		if !validProvides[p] {
			return []ValidationError{{
				Field:   fmt.Sprintf("provides[%d]", i),
				Message: fmt.Sprintf("invalid type %q, must be skill/rule/hook/agent/template/bundle", p),
			}}
		}
	}
	return nil
}

// --- Exports validation ---

var validExportTypes = map[string]bool{
	"skill":    true,
	"rule":     true,
	"hook":     true,
	"agent":    true,
	"template": true,
}

func validateExports(m *Manifest) []ValidationError {
	var errs []ValidationError

	if len(m.Exports) == 0 {
		errs = append(errs, ValidationError{Field: "exports", Message: "at least one export required"})
		return errs
	}

	for i, e := range m.Exports {
		prefix := fmt.Sprintf("exports[%d]", i)

		if e.Source == "" {
			errs = append(errs, ValidationError{Field: prefix + ".source", Message: "required"})
		} else if err := validateExportPath(e.Source); err != nil {
			errs = append(errs, ValidationError{Field: prefix + ".source", Message: err.Error()})
		}

		if e.Type == "" {
			errs = append(errs, ValidationError{Field: prefix + ".type", Message: "required"})
		} else if !validExportTypes[e.Type] {
			errs = append(errs, ValidationError{
				Field:   prefix + ".type",
				Message: fmt.Sprintf("must be skill/rule/hook/template/agent, got %q", e.Type),
			})
		}

		if e.Type == "hook" {
			if e.HookEvent == "" {
				errs = append(errs, ValidationError{Field: prefix + ".hook_event", Message: "required for hook exports"})
			} else if !isValidHookEvent(e.HookEvent) {
				errs = append(errs, ValidationError{
					Field:   prefix + ".hook_event",
					Message: fmt.Sprintf("must be PreToolUse/PostToolUse/SessionStart/Stop, got %q", e.HookEvent),
				})
			}
			if e.HookMatcher == "" {
				errs = append(errs, ValidationError{Field: prefix + ".hook_matcher", Message: "required for hook exports"})
			}
		}
	}

	return errs
}

func validateExportPath(path string) error {
	if filepath.IsAbs(path) {
		return fmt.Errorf("must be a relative path, got absolute path %q", path)
	}
	cleaned := filepath.Clean(path)
	if strings.HasPrefix(cleaned, "..") {
		return fmt.Errorf("must not traverse above package root (no ../), got %q", path)
	}
	return nil
}

func isValidHookEvent(event string) bool {
	switch event {
	case "PreToolUse", "PostToolUse", "SessionStart", "Stop":
		return true
	}
	return false
}

// --- Keywords validation ---

func validateKeywords(m *Manifest) []ValidationError {
	var errs []ValidationError

	if len(m.Keywords) > 10 {
		errs = append(errs, ValidationError{Field: "keywords", Message: "maximum 10 keywords allowed"})
	}
	for i, kw := range m.Keywords {
		if len(kw) < 2 || len(kw) > 30 {
			errs = append(errs, ValidationError{
				Field:   fmt.Sprintf("keywords[%d]", i),
				Message: fmt.Sprintf("must be 2-30 characters, got %d", len(kw)),
			})
		}
	}
	return errs
}

// --- Features validation ---

var kebabCaseRegex = regexp.MustCompile(`^[a-z0-9]+(-[a-z0-9]+)*$`)

func validateFeatures(m *Manifest) []ValidationError {
	var errs []ValidationError

	for name, feat := range m.Features {
		prefix := fmt.Sprintf("features.%s", name)

		if !kebabCaseRegex.MatchString(name) {
			errs = append(errs, ValidationError{
				Field:   prefix,
				Message: "feature name must be kebab-case (e.g., strict-mode)",
			})
		}

		// Validate feature exports.
		for i, e := range feat.Exports {
			ePrefix := fmt.Sprintf("%s.exports[%d]", prefix, i)
			if e.Source == "" {
				errs = append(errs, ValidationError{Field: ePrefix + ".source", Message: "required"})
			}
			if e.Type == "" {
				errs = append(errs, ValidationError{Field: ePrefix + ".type", Message: "required"})
			}
			if e.Type == "hook" && e.HookEvent == "" {
				errs = append(errs, ValidationError{Field: ePrefix + ".hook_event", Message: "required for hook exports"})
			}
		}

		// Check for circular feature dependencies (feature depends on itself).
		for depName := range feat.Dependencies {
			if depName == name {
				errs = append(errs, ValidationError{
					Field:   prefix,
					Message: "circular dependency: feature depends on itself",
				})
			}
		}
	}

	return errs
}

// --- Publish validation ---

func validatePublish(m *Manifest) []ValidationError {
	if m.Publish == nil {
		return nil
	}
	var errs []ValidationError

	if m.Publish.MinScore != nil {
		score := *m.Publish.MinScore
		if score < 0 || score > 100 {
			errs = append(errs, ValidationError{
				Field:   "publish.min_score",
				Message: "must be 0-100",
			})
		}
	}

	return errs
}

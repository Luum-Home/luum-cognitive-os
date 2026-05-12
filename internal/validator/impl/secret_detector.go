package impl

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"

	"github.com/luum/cos-dispatch/internal/validator"
	"github.com/luum/cos-dispatch/pkg/hook"
)

// SecretDetectorValidator scans files written or edited for env var references
// without corresponding definitions in .env*, docker-compose*.yml, or
// **/config*.go. Ports hooks/secret-detector.sh.
//
// This validator is advisory only — it returns a Warn (non-blocking) when
// references are found without definitions. The bash hook also emits a metrics
// JSONL entry; that side effect is intentionally omitted here. Metrics are now
// produced by the dispatcher, not individual validators.
type SecretDetectorValidator struct {
	projectDir string
	// patterns to extract env var names by language
	patterns []*regexp.Regexp
}

// NewSecretDetectorValidator constructs the validator. Empty projectDir
// resolves to $CLAUDE_PROJECT_DIR or cwd.
func NewSecretDetectorValidator(projectDir string) *SecretDetectorValidator {
	if projectDir == "" {
		projectDir = os.Getenv("CLAUDE_PROJECT_DIR")
		if projectDir == "" {
			projectDir = "."
		}
	}
	return &SecretDetectorValidator{
		projectDir: projectDir,
		patterns: []*regexp.Regexp{
			// Node/TypeScript: process.env.VAR_NAME
			regexp.MustCompile(`process\.env\.([A-Z_][A-Z0-9_]*)`),
			// Go: os.Getenv("VAR_NAME")
			regexp.MustCompile(`os\.Getenv\("([A-Z_][A-Z0-9_]*)"\)`),
			// Java: System.getenv("VAR_NAME")
			regexp.MustCompile(`System\.getenv\("([A-Z_][A-Z0-9_]*)"\)`),
			// Spring Boot: ${VAR_NAME}
			regexp.MustCompile(`\$\{([A-Z_][A-Z0-9_]*)`),
		},
	}
}

func (v *SecretDetectorValidator) Name() string { return "secret-detector" }
func (v *SecretDetectorValidator) Category() validator.ValidatorCategory {
	return validator.CategoryIO
}

// shouldSkipPath mirrors the bash hook's exclusion list.
func shouldSkipSecretPath(p string) bool {
	switch strings.ToLower(filepath.Ext(p)) {
	case ".md", ".json", ".yaml", ".yml", ".lock", ".sum", ".sh":
		return true
	}
	if strings.Contains(p, "/.cognitive-os/") || strings.Contains(p, "/.claude/") {
		return true
	}
	return false
}

// Validate inspects the file content for env var references and reports any
// that lack definitions in standard config locations.
func (v *SecretDetectorValidator) Validate(_ context.Context, hookCtx *hook.Context) *validator.Result {
	if hookCtx == nil {
		return validator.Pass()
	}
	path := hookCtx.GetFilePath()
	if path == "" {
		return validator.Pass()
	}
	if shouldSkipSecretPath(path) {
		return validator.Pass()
	}

	// Prefer the in-memory content (Write tool); fall back to reading from disk
	// for Edit (which only carries a diff in real life).
	content := hookCtx.GetContent()
	if content == "" {
		data, err := os.ReadFile(path)
		if err != nil {
			return validator.Pass()
		}
		content = string(data)
	}

	refs := v.extractEnvVars(content)
	if len(refs) == 0 {
		return validator.Pass()
	}

	missing := v.findMissing(refs)
	if len(missing) == 0 {
		return validator.Pass()
	}
	sort.Strings(missing)

	msg := fmt.Sprintf("Missing env var definitions: %s", strings.Join(missing, ", "))
	hint := fmt.Sprintf("Add %s to .env.example to maintain the secret hygiene contract.",
		strings.Join(missing, ", "))
	return &validator.Result{
		Passed:      false,
		ShouldBlock: false, // advisory
		Message:     msg,
		FixHint:     hint,
		Reference: validator.Reference{
			Code: "COS-SEC-002",
			URL:  "docs/04-Concepts/architecture/cos-dispatch/secret-detector.md",
		},
		Details: map[string]string{
			"file":    path,
			"missing": strings.Join(missing, ","),
		},
	}
}

// extractEnvVars returns the deduped set of env var names referenced in content.
func (v *SecretDetectorValidator) extractEnvVars(content string) []string {
	seen := make(map[string]struct{})
	for _, re := range v.patterns {
		for _, m := range re.FindAllStringSubmatch(content, -1) {
			if len(m) >= 2 {
				seen[m[1]] = struct{}{}
			}
		}
	}
	out := make([]string, 0, len(seen))
	for k := range seen {
		out = append(out, k)
	}
	return out
}

// findMissing returns env var names that are not defined in any of the
// standard config files in projectDir.
func (v *SecretDetectorValidator) findMissing(vars []string) []string {
	defined := v.collectDefined()
	var missing []string
	for _, name := range vars {
		if _, ok := defined[name]; !ok {
			missing = append(missing, name)
		}
	}
	return missing
}

// collectDefined returns the set of env var names defined in:
//   - <projectDir>/.env*
//   - <projectDir>/docker-compose*.yml
//   - <projectDir>/dev.env
//   - <projectDir>/**/config*.go (best-effort, depth-1 walk under projectDir)
func (v *SecretDetectorValidator) collectDefined() map[string]struct{} {
	defined := make(map[string]struct{})

	// .env* and dev.env: KEY=value lines.
	envRe := regexp.MustCompile(`(?m)^([A-Z_][A-Z0-9_]*)=`)
	addLines := func(path string) {
		data, err := os.ReadFile(path)
		if err != nil {
			return
		}
		for _, m := range envRe.FindAllStringSubmatch(string(data), -1) {
			defined[m[1]] = struct{}{}
		}
	}
	matches, _ := filepath.Glob(filepath.Join(v.projectDir, ".env*"))
	for _, p := range matches {
		addLines(p)
	}
	addLines(filepath.Join(v.projectDir, "dev.env"))

	// docker-compose*.yml: substring match (any ${VAR} or VAR: ...).
	composeRe := regexp.MustCompile(`\b([A-Z_][A-Z0-9_]+)\b`)
	addCompose := func(path string) {
		data, err := os.ReadFile(path)
		if err != nil {
			return
		}
		for _, m := range composeRe.FindAllStringSubmatch(string(data), -1) {
			defined[m[1]] = struct{}{}
		}
	}
	composeMatches, _ := filepath.Glob(filepath.Join(v.projectDir, "docker-compose*.yml"))
	for _, p := range composeMatches {
		addCompose(p)
	}

	// **/config*.go: quoted strings of env var names.
	cfgRe := regexp.MustCompile(`"([A-Z_][A-Z0-9_]+)"`)
	_ = filepath.WalkDir(v.projectDir, func(path string, _ os.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		base := filepath.Base(path)
		if !strings.HasSuffix(base, ".go") || !strings.Contains(base, "config") {
			return nil
		}
		// Skip vendored / hidden dirs to keep the walk cheap.
		if strings.Contains(path, "/vendor/") || strings.Contains(path, "/.git/") {
			return nil
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return nil
		}
		for _, m := range cfgRe.FindAllStringSubmatch(string(data), -1) {
			defined[m[1]] = struct{}{}
		}
		return nil
	})

	return defined
}

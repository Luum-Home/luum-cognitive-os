package impl

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/luum/cos-dispatch/internal/validator"
	"github.com/luum/cos-dispatch/pkg/hook"
)

// ContentPolicyValidator scans file content against the prohibited terms and
// patterns declared in .cognitive-os/content-policy.yaml. Ports
// hooks/content-policy.sh.
//
// Only Edit and Write tool events are evaluated. The match is case-insensitive
// to mirror `grep -i` in the bash hook. Pattern entries are treated as regular
// expressions; term entries are matched as fixed substrings.
//
// The validator is parsed lazily and cached; callers can pass an explicit
// policy path or rely on the default at <projectDir>/.cognitive-os/content-policy.yaml.
type ContentPolicyValidator struct {
	projectDir string
	policyPath string
	loaded     bool
	rules      []policyRule
}

type policyRule struct {
	kind    string // "term" or "pattern"
	value   string
	reason  string
	pattern *regexp.Regexp // compiled regex (only for pattern rules)
}

// NewContentPolicyValidator constructs the validator. Empty projectDir resolves
// to $CLAUDE_PROJECT_DIR or cwd; empty policyPath resolves to
// <projectDir>/.cognitive-os/content-policy.yaml.
func NewContentPolicyValidator(projectDir, policyPath string) *ContentPolicyValidator {
	if projectDir == "" {
		projectDir = os.Getenv("CLAUDE_PROJECT_DIR")
		if projectDir == "" {
			projectDir = "."
		}
	}
	if policyPath == "" {
		policyPath = filepath.Join(projectDir, ".cognitive-os", "content-policy.yaml")
	}
	return &ContentPolicyValidator{
		projectDir: projectDir,
		policyPath: policyPath,
	}
}

func (v *ContentPolicyValidator) Name() string { return "content-policy" }
func (v *ContentPolicyValidator) Category() validator.ValidatorCategory {
	return validator.CategoryCPU
}

// Validate checks the target file against the policy. A match returns Fail
// (block), mirroring the bash hook's exit 2.
func (v *ContentPolicyValidator) Validate(_ context.Context, hookCtx *hook.Context) *validator.Result {
	if hookCtx == nil {
		return validator.Pass()
	}
	if hookCtx.ToolName != hook.ToolEdit && hookCtx.ToolName != hook.ToolWrite {
		return validator.Pass()
	}
	path := hookCtx.GetFilePath()
	if path == "" {
		return validator.Pass()
	}

	if !v.loaded {
		v.rules = parsePolicyFile(v.policyPath)
		v.loaded = true
	}
	if len(v.rules) == 0 {
		return validator.Pass()
	}

	// Prefer in-memory content; fall back to disk read.
	content := hookCtx.GetContent()
	if content == "" {
		data, err := os.ReadFile(path)
		if err != nil {
			return validator.Pass()
		}
		content = string(data)
	}
	lower := strings.ToLower(content)

	var violations []string
	var firstReason string
	for _, r := range v.rules {
		switch r.kind {
		case "term":
			if strings.Contains(lower, strings.ToLower(r.value)) {
				violations = append(violations, fmt.Sprintf("term '%s'", r.value))
				if firstReason == "" {
					firstReason = r.reason
				}
			}
		case "pattern":
			if r.pattern != nil && r.pattern.MatchString(content) {
				violations = append(violations, fmt.Sprintf("pattern '%s'", r.value))
				if firstReason == "" {
					firstReason = r.reason
				}
			}
		}
	}

	if len(violations) == 0 {
		return validator.Pass()
	}

	msg := fmt.Sprintf("CONTENT POLICY: %d violation(s) in %s — %s",
		len(violations), path, strings.Join(violations, "; "))
	if firstReason != "" {
		msg = fmt.Sprintf("%s | reason: %s", msg, firstReason)
	}
	return &validator.Result{
		Passed:      false,
		ShouldBlock: true,
		Message:     msg,
		FixHint:     "Remove the prohibited content before retrying.",
		Reference: validator.Reference{
			Code: "COS-POL-001",
			URL:  "docs/architecture/cos-dispatch/content-policy.md",
		},
		Details: map[string]string{
			"file":       path,
			"violations": fmt.Sprintf("%d", len(violations)),
		},
	}
}

// parsePolicyFile reads a minimal subset of the content-policy YAML schema:
//
//	prohibited:
//	  - term: "foo"
//	    reason: "..."
//	  - pattern: "regex"
//	    reason: "..."
//
// We avoid pulling in a full YAML dependency since the bash hook already uses
// line-oriented parsing; see hooks/content-policy.sh.
func parsePolicyFile(path string) []policyRule {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil
	}
	lines := strings.Split(string(data), "\n")

	termRe := regexp.MustCompile(`^\s*-\s*term:\s*"?([^"]*?)"?\s*$`)
	termSingleRe := regexp.MustCompile(`^\s*-\s*term:\s*'([^']*)'\s*$`)
	patternRe := regexp.MustCompile(`^\s*-\s*pattern:\s*"([^"]*)"\s*$`)
	patternSingleRe := regexp.MustCompile(`^\s*-\s*pattern:\s*'([^']*)'\s*$`)
	reasonRe := regexp.MustCompile(`^\s*reason:\s*"?([^"]*?)"?\s*$`)
	reasonSingleRe := regexp.MustCompile(`^\s*reason:\s*'([^']*)'\s*$`)

	var rules []policyRule
	var current *policyRule
	flush := func() {
		if current == nil {
			return
		}
		if current.kind == "pattern" && current.value != "" {
			// Compile case-insensitive to mirror grep -iE.
			if re, err := regexp.Compile("(?i)" + current.value); err == nil {
				current.pattern = re
			}
		}
		rules = append(rules, *current)
		current = nil
	}

	for _, raw := range lines {
		// Trim trailing CR for Windows-style line endings.
		line := strings.TrimRight(raw, "\r")
		switch {
		case termSingleRe.MatchString(line):
			flush()
			m := termSingleRe.FindStringSubmatch(line)
			current = &policyRule{kind: "term", value: m[1]}
		case termRe.MatchString(line):
			flush()
			m := termRe.FindStringSubmatch(line)
			current = &policyRule{kind: "term", value: m[1]}
		case patternSingleRe.MatchString(line):
			flush()
			m := patternSingleRe.FindStringSubmatch(line)
			current = &policyRule{kind: "pattern", value: m[1]}
		case patternRe.MatchString(line):
			flush()
			m := patternRe.FindStringSubmatch(line)
			current = &policyRule{kind: "pattern", value: m[1]}
		case current != nil && reasonSingleRe.MatchString(line):
			m := reasonSingleRe.FindStringSubmatch(line)
			current.reason = m[1]
		case current != nil && reasonRe.MatchString(line):
			m := reasonRe.FindStringSubmatch(line)
			current.reason = m[1]
		}
	}
	flush()
	return rules
}

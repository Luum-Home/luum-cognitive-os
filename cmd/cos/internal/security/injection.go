package security

import (
	"bufio"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

// InjectionFinding represents a prompt or shell injection pattern found in a file.
type InjectionFinding struct {
	File    string
	Line    int
	Type    string // "prompt_injection" or "shell_injection"
	Pattern string
	Snippet string
}

// injectionRule pairs a compiled regex with a label and type.
type injectionRule struct {
	re      *regexp.Regexp
	label   string
	iType   string
}

var promptInjectionRules = []injectionRule{
	{regexp.MustCompile(`(?i)ignore\s+previous\s+instructions`), "ignore previous instructions", "prompt_injection"},
	{regexp.MustCompile(`(?i)you\s+are\s+now`), "you are now", "prompt_injection"},
	{regexp.MustCompile(`(?i)system:\s*you`), "system: you", "prompt_injection"},
	{regexp.MustCompile(`(?i)forget\s+your\s+instructions`), "forget your instructions", "prompt_injection"},
	{regexp.MustCompile(`(?i)disregard\s+.*instructions`), "disregard instructions", "prompt_injection"},
}

var shellInjectionRules = []injectionRule{
	{regexp.MustCompile(`[^"']\$\(`), "unquoted command substitution", "shell_injection"},
	{regexp.MustCompile(`(?i)eval\s+\$`), "eval with variable", "shell_injection"},
	{regexp.MustCompile(`(?i)curl\s.*\|\s*(ba)?sh`), "curl piped to shell", "shell_injection"},
	{regexp.MustCompile(`(?i)base64.*\|\s*(ba)?sh`), "base64 decode + exec", "shell_injection"},
}

// ScanInjection scans skill/rule files for prompt injection patterns
// and shell scripts for dangerous patterns.
func ScanInjection(dir string) []InjectionFinding {
	var findings []InjectionFinding

	_ = filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() {
			return nil
		}

		rel, _ := filepath.Rel(dir, path)
		if shouldSkipPath(rel) {
			return nil
		}

		ext := strings.ToLower(filepath.Ext(path))
		base := strings.ToLower(filepath.Base(path))

		var rules []injectionRule

		switch {
		case ext == ".md" || ext == ".txt":
			rules = promptInjectionRules
		case ext == ".sh" || ext == ".bash" || base == "makefile":
			rules = shellInjectionRules
		default:
			return nil
		}

		f, err := os.Open(path)
		if err != nil {
			return nil
		}
		defer f.Close()

		scanner := bufio.NewScanner(f)
		lineNum := 0
		for scanner.Scan() {
			lineNum++
			line := scanner.Text()

			for _, rule := range rules {
				if rule.re.MatchString(line) {
					findings = append(findings, InjectionFinding{
						File:    rel,
						Line:    lineNum,
						Type:    rule.iType,
						Pattern: rule.label,
						Snippet: truncateSnippet(line, 120),
					})
				}
			}
		}
		return nil
	})

	return findings
}

// truncateSnippet trims a line to a maximum length.
func truncateSnippet(line string, maxLen int) string {
	line = strings.TrimSpace(line)
	if len(line) <= maxLen {
		return line
	}
	return line[:maxLen] + "..."
}

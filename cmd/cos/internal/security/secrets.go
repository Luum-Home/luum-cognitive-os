package security

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

// SecretFinding represents a hardcoded secret detected in a file.
type SecretFinding struct {
	File    string
	Line    int
	Pattern string
	Snippet string // masked excerpt
}

// secretPattern pairs a compiled regex with a human-readable label.
type secretPattern struct {
	re    *regexp.Regexp
	label string
}

var secretPatterns = []secretPattern{
	{regexp.MustCompile(`AKIA[0-9A-Z]{16}`), "AWS access key"},
	{regexp.MustCompile(`ghp_[a-zA-Z0-9]{36}`), "GitHub personal access token"},
	{regexp.MustCompile(`github_pat_[a-zA-Z0-9_]{40,}`), "GitHub fine-grained PAT"},
	{regexp.MustCompile(`(?i)[a-zA-Z_]*(?:api_?key|secret|token|password)\s*[=:]\s*["'][^"']{8,}`), "Generic API key/secret"},
	{regexp.MustCompile(`-----BEGIN.*PRIVATE KEY-----`), "Private key"},
}

// envValuePattern detects environment variable assignments with values in .env files.
var envValuePattern = regexp.MustCompile(`^[A-Z_]+=.{8,}`)

// ScanSecrets scans all files in a directory for hardcoded secrets.
// Returns list of findings with file, line, and pattern matched.
func ScanSecrets(dir string) []SecretFinding {
	var findings []SecretFinding

	_ = filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() {
			return nil
		}

		// Skip common non-text directories.
		rel, _ := filepath.Rel(dir, path)
		if shouldSkipPath(rel) {
			return nil
		}

		if isBinaryFile(path) {
			return nil
		}

		isEnvFile := isEnvFilename(filepath.Base(path))

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

			for _, sp := range secretPatterns {
				if sp.re.MatchString(line) {
					findings = append(findings, SecretFinding{
						File:    rel,
						Line:    lineNum,
						Pattern: sp.label,
						Snippet: maskSnippet(line),
					})
				}
			}

			if isEnvFile && envValuePattern.MatchString(line) {
				// Check it is not already caught by a more specific pattern.
				alreadyCaught := false
				for _, sp := range secretPatterns {
					if sp.re.MatchString(line) {
						alreadyCaught = true
						break
					}
				}
				if !alreadyCaught {
					findings = append(findings, SecretFinding{
						File:    rel,
						Line:    lineNum,
						Pattern: ".env value",
						Snippet: maskSnippet(line),
					})
				}
			}
		}
		return nil
	})

	return findings
}

// isBinaryFile checks for null bytes in the first 512 bytes.
func isBinaryFile(path string) bool {
	f, err := os.Open(path)
	if err != nil {
		return true // treat unreadable as binary
	}
	defer f.Close()

	buf := make([]byte, 512)
	n, err := f.Read(buf)
	if err != nil && err != io.EOF {
		return true
	}
	for i := 0; i < n; i++ {
		if buf[i] == 0 {
			return true
		}
	}
	return false
}

// isEnvFilename returns true for .env, .env.local, .env.production, etc.
func isEnvFilename(name string) bool {
	return name == ".env" || strings.HasPrefix(name, ".env.")
}

// shouldSkipPath returns true for directories that should not be scanned.
func shouldSkipPath(rel string) bool {
	parts := strings.Split(filepath.ToSlash(rel), "/")
	for _, p := range parts {
		switch p {
		case ".git", "node_modules", "vendor", "__pycache__":
			return true
		}
	}
	return false
}

// maskSnippet masks sensitive parts of a line, keeping the first 20 and last 4 characters.
func maskSnippet(line string) string {
	line = strings.TrimSpace(line)
	if len(line) <= 24 {
		return line[:len(line)/2] + "****"
	}
	return fmt.Sprintf("%s****%s", line[:20], line[len(line)-4:])
}

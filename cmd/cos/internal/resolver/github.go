package resolver

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

// Fetch downloads a package source to a temporary directory.
// For local sources, copies the directory.
// For GitHub sources, does a shallow git clone.
// Returns the path to the fetched directory.
// For GitHub sources, also populates source.Commit with the pinned commit hash.
func Fetch(source *ResolvedSource) (string, error) {
	if source == nil {
		return "", fmt.Errorf("nil source")
	}

	switch source.Type {
	case SourceLocal:
		return fetchLocal(source.LocalPath)
	case SourceGitHub, SourceURL:
		dir, err := fetchGitHub(source.Owner, source.Repo, source.Version)
		if err != nil {
			return "", err
		}
		// Pin the exact commit hash for supply chain integrity.
		commit, commitErr := captureGitCommit(dir)
		if commitErr == nil {
			source.Commit = commit
		}
		return dir, nil
	default:
		return "", fmt.Errorf("unsupported source type: %d", source.Type)
	}
}

// fetchLocal copies a local directory to a temp dir.
func fetchLocal(path string) (string, error) {
	// Verify source exists.
	info, err := os.Stat(path)
	if err != nil {
		return "", fmt.Errorf("local source %q does not exist: %w", path, err)
	}
	if !info.IsDir() {
		return "", fmt.Errorf("local source %q is not a directory", path)
	}

	// Create temp dir.
	tmpDir, err := os.MkdirTemp("", "cos-fetch-local-*")
	if err != nil {
		return "", fmt.Errorf("failed to create temp dir: %w", err)
	}

	// The destination for cp -r must be the target directory itself.
	// Use "cp -a" to preserve permissions and symlinks.
	dest := filepath.Join(tmpDir, "pkg")
	cmd := exec.Command("cp", "-a", path, dest)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		// Best-effort cleanup.
		_ = os.RemoveAll(tmpDir)
		return "", fmt.Errorf("failed to copy %q: %s: %w", path, stderr.String(), err)
	}

	return dest, nil
}

// fetchGitHub clones a GitHub repo to a temp dir using shallow clone.
func fetchGitHub(owner, repo, version string) (string, error) {
	if owner == "" || repo == "" {
		return "", fmt.Errorf("owner and repo must not be empty")
	}

	cloneURL := fmt.Sprintf("https://github.com/%s/%s.git", owner, repo)

	// Create temp dir.
	tmpDir, err := os.MkdirTemp("", "cos-fetch-github-*")
	if err != nil {
		return "", fmt.Errorf("failed to create temp dir: %w", err)
	}

	dest := filepath.Join(tmpDir, repo)

	// Build clone command.
	args := []string{"clone", "--depth", "1"}
	if version != "" {
		args = append(args, "--branch", version)
	}
	args = append(args, cloneURL, dest)

	cmd := exec.Command("git", args...)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		_ = os.RemoveAll(tmpDir)
		return "", fmt.Errorf("git clone failed for %s/%s: %s: %w", owner, repo, stderr.String(), err)
	}

	return dest, nil
}

// CleanupFetch removes a fetched temp directory.
// It safely handles empty strings and non-temp paths by only removing
// directories that live under the system temp dir.
func CleanupFetch(dir string) error {
	if dir == "" {
		return nil
	}

	// Safety: only remove paths under the system temp dir.
	tmpRoot := os.TempDir()
	absDir, err := filepath.Abs(dir)
	if err != nil {
		return fmt.Errorf("failed to resolve path %q: %w", dir, err)
	}
	if !strings.HasPrefix(absDir, tmpRoot) {
		return fmt.Errorf("refusing to remove %q: not under temp dir %q", dir, tmpRoot)
	}

	return os.RemoveAll(dir)
}

// semverRegex matches semver tags like v1.2.3, 1.2.3, v0.1.0, etc.
var semverRegex = regexp.MustCompile(`^v?(\d+)\.(\d+)\.(\d+)`)

// findLatestTag queries git ls-remote for the latest semver tag.
// Returns the tag name (e.g., "v1.2.3") or an empty string if no tags found.
func findLatestTag(owner, repo string) (string, error) {
	url := fmt.Sprintf("https://github.com/%s/%s.git", owner, repo)

	cmd := exec.Command("git", "ls-remote", "--tags", "--sort=-v:refname", url)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("git ls-remote failed for %s/%s: %s: %w",
			owner, repo, stderr.String(), err)
	}

	output := stdout.String()
	if output == "" {
		return "", nil
	}

	// Parse tags from ls-remote output. Each line: "<hash>\trefs/tags/<tag>"
	var tags []string
	for _, line := range strings.Split(output, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		parts := strings.SplitN(line, "\t", 2)
		if len(parts) != 2 {
			continue
		}

		ref := parts[1]
		// Skip dereferenced tags (^{}).
		if strings.HasSuffix(ref, "^{}") {
			continue
		}

		tag := strings.TrimPrefix(ref, "refs/tags/")
		if semverRegex.MatchString(tag) {
			tags = append(tags, tag)
		}
	}

	if len(tags) == 0 {
		return "", nil
	}

	// Sort descending by semver.
	sort.Slice(tags, func(i, j int) bool {
		return compareSemver(tags[i], tags[j]) > 0
	})

	return tags[0], nil
}

// captureGitCommit returns the full SHA-1 commit hash of HEAD in the given directory.
// This pins the exact commit for supply chain integrity, ensuring that tag
// manipulation attacks cannot change the resolved content after fetch.
func captureGitCommit(dir string) (string, error) {
	cmd := exec.Command("git", "rev-parse", "HEAD")
	cmd.Dir = dir
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("git rev-parse HEAD failed in %s: %s: %w", dir, stderr.String(), err)
	}
	commit := strings.TrimSpace(stdout.String())
	if len(commit) < 40 {
		return "", fmt.Errorf("unexpected commit hash length: %q", commit)
	}
	return commit[:40], nil
}

// compareSemver compares two semver strings. Returns >0 if a > b, <0 if a < b, 0 if equal.
func compareSemver(a, b string) int {
	aParts := parseSemverParts(a)
	bParts := parseSemverParts(b)

	for i := 0; i < 3; i++ {
		if aParts[i] != bParts[i] {
			return aParts[i] - bParts[i]
		}
	}
	return 0
}

// parseSemverParts extracts [major, minor, patch] from a semver string.
func parseSemverParts(s string) [3]int {
	matches := semverRegex.FindStringSubmatch(s)
	if len(matches) < 4 {
		return [3]int{0, 0, 0}
	}

	var parts [3]int
	for i := 0; i < 3; i++ {
		val := 0
		for _, c := range matches[i+1] {
			val = val*10 + int(c-'0')
		}
		parts[i] = val
	}
	return parts
}

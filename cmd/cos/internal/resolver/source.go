package resolver

import (
	"fmt"
	"os"
	"strings"
)

// SourceType identifies how a package was specified.
type SourceType int

const (
	// SourceLocal is a local filesystem path (./path or /absolute/path).
	SourceLocal SourceType = iota
	// SourceGitHub is a scoped name or bare github.com domain reference.
	SourceGitHub
	// SourceURL is a full HTTPS URL to a GitHub repository.
	SourceURL
)

// sourceTypeNames maps SourceType values to human-readable labels.
var sourceTypeNames = map[SourceType]string{
	SourceLocal:  "local",
	SourceGitHub: "github",
	SourceURL:    "url",
}

// ResolvedSource holds the parsed and resolved source information.
type ResolvedSource struct {
	Type      SourceType
	Raw       string // original user input
	Name      string // package name (derived)
	LocalPath string // for SourceLocal
	Owner     string // for SourceGitHub/URL
	Repo      string // for SourceGitHub/URL
	Version   string // tag/branch (empty = latest)
	URL       string // full URL
	Commit    string // pinned git commit hash (populated after Fetch)
}

// String returns a human-readable description of the source.
func (s *ResolvedSource) String() string {
	typeName := sourceTypeNames[s.Type]

	switch s.Type {
	case SourceLocal:
		return fmt.Sprintf("[%s] %s (path: %s)", typeName, s.Name, s.LocalPath)
	case SourceGitHub, SourceURL:
		ver := s.Version
		if ver == "" {
			ver = "latest"
		}
		return fmt.Sprintf("[%s] %s/%s@%s", typeName, s.Owner, s.Repo, ver)
	default:
		return fmt.Sprintf("[unknown] %s", s.Raw)
	}
}

// Resolve parses a package specifier into a ResolvedSource.
//
// Supported formats:
//
//	"./my-package"               -> SourceLocal
//	"/absolute/path"             -> SourceLocal
//	"@luum/safety-mesh"          -> SourceGitHub (github.com/luum/safety-mesh)
//	"@trailofbits/skills"        -> SourceGitHub
//	"github.com/org/repo"        -> SourceGitHub
//	"https://github.com/org/repo"-> SourceURL
//	"@luum/safety-mesh@1.0.0"    -> SourceGitHub with version
//	"my-skill"                   -> fallback: github.com/my-skill/my-skill
func Resolve(spec string) (*ResolvedSource, error) {
	spec = strings.TrimSpace(spec)
	if spec == "" {
		return nil, fmt.Errorf("empty package specifier")
	}

	// Local paths: starts with "./" or "/"
	if strings.HasPrefix(spec, "./") || strings.HasPrefix(spec, "/") {
		return resolveLocal(spec)
	}

	// Scoped GitHub reference: starts with "@"
	if strings.HasPrefix(spec, "@") {
		return resolveScoped(spec)
	}

	// Full HTTPS URL: starts with "https://github.com/"
	if strings.HasPrefix(spec, "https://github.com/") {
		return resolveHTTPS(spec)
	}

	// Bare domain reference: starts with "github.com/"
	if strings.HasPrefix(spec, "github.com/") {
		return resolveGitHubDomain(spec)
	}

	// Fallback: treat as a plain name -> github.com/{name}/{name}
	return resolvePlainName(spec)
}

// resolveLocal parses a local filesystem path.
func resolveLocal(spec string) (*ResolvedSource, error) {
	// Verify the path exists.
	info, err := os.Stat(spec)
	if err != nil {
		return nil, fmt.Errorf("local path %q does not exist: %w", spec, err)
	}
	if !info.IsDir() {
		return nil, fmt.Errorf("local path %q is not a directory", spec)
	}

	// Derive the package name from the last path component.
	name := lastPathComponent(spec)

	return &ResolvedSource{
		Type:      SourceLocal,
		Raw:       spec,
		Name:      name,
		LocalPath: spec,
	}, nil
}

// resolveScoped parses @scope/name[@version] format.
func resolveScoped(spec string) (*ResolvedSource, error) {
	// Strip the leading "@".
	rest := spec[1:]

	// Split off an optional version suffix: "scope/name@version"
	var version string
	if idx := strings.LastIndex(rest, "@"); idx > 0 {
		version = rest[idx+1:]
		rest = rest[:idx]
	}

	parts := strings.SplitN(rest, "/", 2)
	if len(parts) != 2 || parts[0] == "" || parts[1] == "" {
		return nil, fmt.Errorf("invalid scoped specifier %q: expected @scope/name", spec)
	}

	owner := parts[0]
	repo := parts[1]

	return &ResolvedSource{
		Type:    SourceGitHub,
		Raw:     spec,
		Name:    repo,
		Owner:   owner,
		Repo:    repo,
		Version: version,
		URL:     fmt.Sprintf("https://github.com/%s/%s", owner, repo),
	}, nil
}

// resolveHTTPS parses https://github.com/owner/repo URLs.
func resolveHTTPS(spec string) (*ResolvedSource, error) {
	owner, repo, err := extractOwnerRepo(strings.TrimPrefix(spec, "https://"))
	if err != nil {
		return nil, fmt.Errorf("invalid GitHub URL %q: %w", spec, err)
	}

	return &ResolvedSource{
		Type:  SourceURL,
		Raw:   spec,
		Name:  repo,
		Owner: owner,
		Repo:  repo,
		URL:   fmt.Sprintf("https://github.com/%s/%s", owner, repo),
	}, nil
}

// resolveGitHubDomain parses github.com/owner/repo format.
func resolveGitHubDomain(spec string) (*ResolvedSource, error) {
	owner, repo, err := extractOwnerRepo(spec)
	if err != nil {
		return nil, fmt.Errorf("invalid GitHub reference %q: %w", spec, err)
	}

	return &ResolvedSource{
		Type:  SourceGitHub,
		Raw:   spec,
		Name:  repo,
		Owner: owner,
		Repo:  repo,
		URL:   fmt.Sprintf("https://github.com/%s/%s", owner, repo),
	}, nil
}

// resolvePlainName treats a bare name as github.com/{name}/{name}.
func resolvePlainName(spec string) (*ResolvedSource, error) {
	// Validate: no slashes, no spaces.
	if strings.Contains(spec, "/") || strings.Contains(spec, " ") {
		return nil, fmt.Errorf("invalid package specifier %q", spec)
	}

	return &ResolvedSource{
		Type:  SourceGitHub,
		Raw:   spec,
		Name:  spec,
		Owner: spec,
		Repo:  spec,
		URL:   fmt.Sprintf("https://github.com/%s/%s", spec, spec),
	}, nil
}

// extractOwnerRepo extracts owner and repo from a "github.com/owner/repo[/...]" string.
func extractOwnerRepo(s string) (string, string, error) {
	// Strip trailing slashes and .git suffix.
	s = strings.TrimSuffix(s, "/")
	s = strings.TrimSuffix(s, ".git")

	// Remove the "github.com/" prefix.
	s = strings.TrimPrefix(s, "github.com/")

	parts := strings.SplitN(s, "/", 3) // at most 3 parts; ignore sub-paths
	if len(parts) < 2 || parts[0] == "" || parts[1] == "" {
		return "", "", fmt.Errorf("expected github.com/owner/repo, got %q", s)
	}

	return parts[0], parts[1], nil
}

// lastPathComponent returns the final non-empty element of a filepath.
func lastPathComponent(path string) string {
	path = strings.TrimSuffix(path, "/")
	if idx := strings.LastIndex(path, "/"); idx >= 0 {
		return path[idx+1:]
	}
	return path
}

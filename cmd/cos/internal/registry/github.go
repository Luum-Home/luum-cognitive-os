package registry

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	"gopkg.in/yaml.v3"
)

// SearchResult represents a package found in the registry.
type SearchResult struct {
	Name        string   `json:"name"`
	Description string   `json:"description"`
	Owner       string   `json:"owner"`
	Repo        string   `json:"repo"`
	Stars       int      `json:"stars"`
	License     string   `json:"license"`
	URL         string   `json:"url"`
	Topics      []string `json:"topics"`
	UpdatedAt   string   `json:"updated_at"`
}

// githubSearchResponse matches the GitHub Search Repositories API response.
type githubSearchResponse struct {
	TotalCount int                `json:"total_count"`
	Items      []githubSearchItem `json:"items"`
}

// githubSearchItem matches a single repository in the search results.
type githubSearchItem struct {
	FullName        string       `json:"full_name"`
	Description     string       `json:"description"`
	StargazersCount int          `json:"stargazers_count"`
	License         *githubLic   `json:"license"`
	HTMLURL         string       `json:"html_url"`
	Topics          []string     `json:"topics"`
	UpdatedAt       string       `json:"updated_at"`
	Owner           *githubOwner `json:"owner"`
}

// githubLic is the license sub-object in GitHub API responses.
type githubLic struct {
	SPDXID string `json:"spdx_id"`
	Name   string `json:"name"`
}

// githubOwner is the owner sub-object in GitHub API responses.
type githubOwner struct {
	Login string `json:"login"`
}

// HTTPClient is an interface for making HTTP requests.
// It defaults to http.DefaultClient but can be overridden for testing.
var HTTPClient interface {
	Do(req *http.Request) (*http.Response, error)
} = &http.Client{Timeout: 15 * time.Second}

// setGitHubAuth adds the Authorization header if GITHUB_TOKEN is set in the
// environment. Authenticated requests have a much higher rate limit (5000/hr
// vs 60/hr for unauthenticated).
func setGitHubAuth(req *http.Request) {
	if token := os.Getenv("GITHUB_TOKEN"); token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
}

// SearchGitHub searches GitHub for repos with topic "cos-package" matching the query.
// This is the original search function preserved for backward compatibility.
func SearchGitHub(query string, limit int) ([]SearchResult, error) {
	return SearchGitHubTopic(query, "cos-package", limit)
}

// SearchGitHubTopic searches GitHub for repos with the given topic matching the query.
func SearchGitHubTopic(query string, topic string, limit int) ([]SearchResult, error) {
	if limit <= 0 {
		limit = 10
	}
	if limit > 100 {
		limit = 100
	}

	// Build the search query: user query + topic filter.
	q := fmt.Sprintf("%s topic:%s", query, topic)
	return searchGitHubAPI(q, limit)
}

// SearchGitHubOrg searches repos within a GitHub organization, optionally
// filtering by a query string.
func SearchGitHubOrg(org string, query string, limit int) ([]SearchResult, error) {
	if limit <= 0 {
		limit = 10
	}
	if limit > 100 {
		limit = 100
	}

	q := fmt.Sprintf("org:%s", org)
	if query != "" {
		q = fmt.Sprintf("%s %s", query, q)
	}
	return searchGitHubAPI(q, limit)
}

// SearchGitHubRepoContents searches within a specific GitHub repo for
// cos-package.yaml files or skill directories. The repo parameter should
// be in "owner/repo" format.
func SearchGitHubRepoContents(repo string, query string, limit int) ([]SearchResult, error) {
	parts := strings.SplitN(repo, "/", 2)
	if len(parts) != 2 {
		return nil, fmt.Errorf("repo must be in owner/repo format, got %q", repo)
	}
	owner, repoName := parts[0], parts[1]

	// First get the repo info.
	info, err := FetchManifestInfo(owner, repoName)
	if err != nil {
		return nil, fmt.Errorf("fetching repo info: %w", err)
	}

	// For a single-repo registry, return the repo itself if it matches the query.
	if query == "" || matchesQuery(info, query) {
		return []SearchResult{*info}, nil
	}

	return []SearchResult{}, nil
}

// SearchLocal searches a local directory for cos packages. Each subdirectory
// containing a cos-package.yaml is considered a package.
func SearchLocal(dirPath string, query string) ([]SearchResult, error) {
	expandedPath := expandPath(dirPath)

	entries, err := os.ReadDir(expandedPath)
	if err != nil {
		if os.IsNotExist(err) {
			return []SearchResult{}, nil
		}
		return nil, fmt.Errorf("reading directory %s: %w", expandedPath, err)
	}

	var results []SearchResult
	queryLower := strings.ToLower(query)

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		pkgDir := fmt.Sprintf("%s/%s", expandedPath, entry.Name())

		// Check for cos-package.yaml or SKILL.md.
		hasManifest := fileExists(fmt.Sprintf("%s/cos-package.yaml", pkgDir))
		hasSkill := fileExists(fmt.Sprintf("%s/SKILL.md", pkgDir))

		if !hasManifest && !hasSkill {
			continue
		}

		name := entry.Name()

		// Filter by query if provided.
		if query != "" && !strings.Contains(strings.ToLower(name), queryLower) {
			continue
		}

		result := SearchResult{
			Name:  name,
			Owner: "local",
			Repo:  name,
			URL:   pkgDir,
		}

		// Try to read description from manifest.
		if hasManifest {
			if desc := readManifestDescription(fmt.Sprintf("%s/cos-package.yaml", pkgDir)); desc != "" {
				result.Description = desc
			}
		}

		results = append(results, result)
	}

	return results, nil
}

// searchGitHubAPI executes a search against the GitHub Search Repositories API.
func searchGitHubAPI(q string, limit int) ([]SearchResult, error) {
	apiURL := fmt.Sprintf(
		"https://api.github.com/search/repositories?q=%s&sort=stars&per_page=%d",
		url.QueryEscape(q), limit,
	)

	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		return nil, fmt.Errorf("creating request: %w", err)
	}
	req.Header.Set("Accept", "application/vnd.github.v3+json")
	req.Header.Set("User-Agent", "cos-package-manager/0.1")
	setGitHubAuth(req)

	resp, err := HTTPClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("searching GitHub: %w", err)
	}
	defer resp.Body.Close()

	// Handle rate limiting.
	if resp.StatusCode == http.StatusForbidden || resp.StatusCode == http.StatusTooManyRequests {
		return nil, fmt.Errorf("GitHub API rate limit exceeded. Try again later or set GITHUB_TOKEN")
	}

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("GitHub API error (status %d): %s", resp.StatusCode, truncate(string(body), 200))
	}

	var searchResp githubSearchResponse
	if err := json.NewDecoder(resp.Body).Decode(&searchResp); err != nil {
		return nil, fmt.Errorf("parsing search response: %w", err)
	}

	results := make([]SearchResult, 0, len(searchResp.Items))
	for _, item := range searchResp.Items {
		result := itemToSearchResult(item)
		results = append(results, result)
	}

	return results, nil
}

// matchesQuery checks if a search result matches a query string.
func matchesQuery(r *SearchResult, query string) bool {
	q := strings.ToLower(query)
	return strings.Contains(strings.ToLower(r.Name), q) ||
		strings.Contains(strings.ToLower(r.Description), q) ||
		strings.Contains(strings.ToLower(r.Owner), q) ||
		strings.Contains(strings.ToLower(r.Repo), q)
}

// expandPath expands ~ to the user's home directory.
func expandPath(path string) string {
	if strings.HasPrefix(path, "~/") {
		home, err := os.UserHomeDir()
		if err != nil {
			return path
		}
		return home + path[1:]
	}
	return path
}

// fileExists returns true if the path exists and is a regular file.
func fileExists(path string) bool {
	info, err := os.Stat(path)
	if err != nil {
		return false
	}
	return !info.IsDir()
}

// readManifestDescription reads the description field from a cos-package.yaml.
func readManifestDescription(path string) string {
	data, err := os.ReadFile(path)
	if err != nil {
		return ""
	}
	var m struct {
		Description string `yaml:"description"`
	}
	if err := yaml.Unmarshal(data, &m); err != nil {
		return ""
	}
	return m.Description
}

// FetchManifestInfo fetches basic manifest info from a GitHub repo.
// Uses the raw content API to get cos-package.yaml without cloning.
func FetchManifestInfo(owner, repo string) (*SearchResult, error) {
	// First get repo info from the API.
	apiURL := fmt.Sprintf("https://api.github.com/repos/%s/%s", owner, repo)

	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		return nil, fmt.Errorf("creating request: %w", err)
	}
	req.Header.Set("Accept", "application/vnd.github.v3+json")
	req.Header.Set("User-Agent", "cos-package-manager/0.1")
	setGitHubAuth(req)

	resp, err := HTTPClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("fetching repo info: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusForbidden || resp.StatusCode == http.StatusTooManyRequests {
		return nil, fmt.Errorf("GitHub API rate limit exceeded. Try again later or set GITHUB_TOKEN")
	}

	if resp.StatusCode == http.StatusNotFound {
		return nil, fmt.Errorf("repository %s/%s not found", owner, repo)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("GitHub API error (status %d)", resp.StatusCode)
	}

	var item githubSearchItem
	if err := json.NewDecoder(resp.Body).Decode(&item); err != nil {
		return nil, fmt.Errorf("parsing repo response: %w", err)
	}

	result := itemToSearchResult(item)
	return &result, nil
}

// SearchByType filters search results to only include packages providing the given type.
// This is a client-side filter since GitHub topics don't distinguish cos component types.
func SearchByType(results []SearchResult, componentType string) []SearchResult {
	if componentType == "" {
		return results
	}

	target := strings.ToLower(componentType)
	filtered := make([]SearchResult, 0)
	for _, r := range results {
		for _, topic := range r.Topics {
			if strings.ToLower(topic) == "cos-"+target {
				filtered = append(filtered, r)
				break
			}
		}
	}
	return filtered
}

// FilterByLicense filters results to only include packages with the specified license.
func FilterByLicense(results []SearchResult, license string) []SearchResult {
	if license == "" {
		return results
	}

	target := strings.ToUpper(license)
	filtered := make([]SearchResult, 0)
	for _, r := range results {
		if strings.ToUpper(r.License) == target {
			filtered = append(filtered, r)
		}
	}
	return filtered
}

// BuildSearchURL constructs the GitHub search API URL for the given query and limit.
// Exported for testing.
func BuildSearchURL(query string, limit int) string {
	q := fmt.Sprintf("%s topic:cos-package", query)
	return fmt.Sprintf(
		"https://api.github.com/search/repositories?q=%s&sort=stars&per_page=%d",
		url.QueryEscape(q), limit,
	)
}

// itemToSearchResult converts a GitHub API item to a SearchResult.
func itemToSearchResult(item githubSearchItem) SearchResult {
	license := ""
	if item.License != nil {
		license = item.License.SPDXID
		if license == "" || license == "NOASSERTION" {
			license = item.License.Name
		}
	}

	owner := ""
	repo := ""
	if parts := strings.SplitN(item.FullName, "/", 2); len(parts) == 2 {
		owner = parts[0]
		repo = parts[1]
	}
	if item.Owner != nil && owner == "" {
		owner = item.Owner.Login
	}

	return SearchResult{
		Name:        fmt.Sprintf("@%s/%s", owner, repo),
		Description: item.Description,
		Owner:       owner,
		Repo:        repo,
		Stars:       item.StargazersCount,
		License:     license,
		URL:         item.HTMLURL,
		Topics:      item.Topics,
		UpdatedAt:   item.UpdatedAt,
	}
}

// truncate returns the first n characters of s, appending "..." if truncated.
func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "..."
}

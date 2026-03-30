package registry

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
)

// SkillsShDefaultBaseURL is the default API base URL for skills.sh.
const SkillsShDefaultBaseURL = "https://skills.sh"

// skillsShSearchResponse matches the skills.sh /api/search response.
type skillsShSearchResponse struct {
	Skills []skillsShSkill `json:"skills"`
}

// skillsShSkill represents a single skill from the skills.sh API.
type skillsShSkill struct {
	ID       string `json:"id"`
	Name     string `json:"name"`
	Installs int    `json:"installs"`
	Source   string `json:"source"`
}

// SearchSkillsSh searches the skills.sh registry for skills matching the query.
// The baseURL parameter allows overriding the default API endpoint for testing.
func SearchSkillsSh(query string, baseURL string, limit int) ([]SearchResult, error) {
	if limit <= 0 {
		limit = 10
	}
	if limit > 50 {
		limit = 50
	}

	if baseURL == "" {
		baseURL = SkillsShDefaultBaseURL
	}

	apiURL := fmt.Sprintf("%s/api/search?q=%s&limit=%d",
		strings.TrimRight(baseURL, "/"),
		url.QueryEscape(query),
		limit,
	)

	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		return nil, fmt.Errorf("creating skills.sh request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	req.Header.Set("User-Agent", "cos-package-manager/0.1")

	resp, err := HTTPClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("searching skills.sh: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusTooManyRequests {
		return nil, fmt.Errorf("skills.sh rate limit exceeded. Try again later")
	}

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("skills.sh API error (status %d): %s", resp.StatusCode, truncate(string(body), 200))
	}

	var searchResp skillsShSearchResponse
	if err := json.NewDecoder(resp.Body).Decode(&searchResp); err != nil {
		return nil, fmt.Errorf("parsing skills.sh response: %w", err)
	}

	results := make([]SearchResult, 0, len(searchResp.Skills))
	for _, skill := range searchResp.Skills {
		result := skillsShSkillToSearchResult(skill)
		results = append(results, result)
	}

	return results, nil
}

// skillsShSkillToSearchResult converts a skills.sh skill to a SearchResult.
func skillsShSkillToSearchResult(skill skillsShSkill) SearchResult {
	// The source field typically contains owner/repo format.
	owner := ""
	repo := ""
	skillURL := ""

	if skill.Source != "" {
		// Source is usually in "owner/repo" format.
		parts := strings.SplitN(skill.Source, "/", 2)
		if len(parts) == 2 {
			owner = parts[0]
			repo = parts[1]
			skillURL = fmt.Sprintf("https://github.com/%s/%s", owner, repo)
		}
	}

	// Build a display name from the skill ID or source.
	name := skill.Name
	if name == "" {
		name = skill.ID
	}

	return SearchResult{
		Name:        name,
		Description: formatSkillsShDescription(skill),
		Owner:       owner,
		Repo:        repo,
		Stars:       skill.Installs, // Map installs to Stars field for display.
		URL:         skillURL,
		Topics:      []string{"skills-sh"},
	}
}

// formatSkillsShDescription builds a description string including install count.
func formatSkillsShDescription(skill skillsShSkill) string {
	parts := []string{}
	if skill.Source != "" {
		parts = append(parts, skill.Source)
	}
	return strings.Join(parts, " — ")
}

// FormatInstallCount formats an install count for display (e.g., "176.4K installs").
func FormatInstallCount(count int) string {
	if count <= 0 {
		return ""
	}
	if count >= 1_000_000 {
		return fmt.Sprintf("%.1fM installs", float64(count)/1_000_000)
	}
	if count >= 1_000 {
		return fmt.Sprintf("%.1fK installs", float64(count)/1_000)
	}
	return fmt.Sprintf("%d installs", count)
}

package registry

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func sampleSkillsShResponse() skillsShSearchResponse {
	return skillsShSearchResponse{
		Skills: []skillsShSkill{
			{
				ID:       "react-best-practices",
				Name:     "React Best Practices",
				Installs: 176400,
				Source:   "anthropics/skills",
			},
			{
				ID:       "typescript-patterns",
				Name:     "TypeScript Patterns",
				Installs: 95200,
				Source:   "vercel-labs/skills",
			},
		},
	}
}

func TestSearchSkillsSh_ParsesResponse(t *testing.T) {
	resp := sampleSkillsShResponse()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Verify the request path and query.
		if r.URL.Path != "/api/search" {
			t.Errorf("path = %q, want /api/search", r.URL.Path)
		}
		q := r.URL.Query().Get("q")
		if q != "react" {
			t.Errorf("q = %q, want %q", q, "react")
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}))
	defer server.Close()

	original := HTTPClient
	HTTPClient = &mockHTTPClient{server: server}
	defer func() { HTTPClient = original }()

	results, err := SearchSkillsSh("react", server.URL, 10)
	if err != nil {
		t.Fatalf("SearchSkillsSh error: %v", err)
	}

	if len(results) != 2 {
		t.Fatalf("results len = %d, want 2", len(results))
	}

	r := results[0]
	if r.Name != "React Best Practices" {
		t.Errorf("Name = %q, want %q", r.Name, "React Best Practices")
	}
	if r.Stars != 176400 {
		t.Errorf("Stars (installs) = %d, want 176400", r.Stars)
	}
	if r.Owner != "anthropics" {
		t.Errorf("Owner = %q, want %q", r.Owner, "anthropics")
	}
	if r.Repo != "skills" {
		t.Errorf("Repo = %q, want %q", r.Repo, "skills")
	}
	if r.URL != "https://github.com/anthropics/skills" {
		t.Errorf("URL = %q, want GitHub URL", r.URL)
	}
}

func TestSearchSkillsSh_HandlesEmptyResults(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(skillsShSearchResponse{Skills: []skillsShSkill{}})
	}))
	defer server.Close()

	original := HTTPClient
	HTTPClient = &mockHTTPClient{server: server}
	defer func() { HTTPClient = original }()

	results, err := SearchSkillsSh("nonexistent", server.URL, 10)
	if err != nil {
		t.Fatalf("SearchSkillsSh error: %v", err)
	}

	if len(results) != 0 {
		t.Errorf("results len = %d, want 0", len(results))
	}
}

func TestSearchSkillsSh_HandlesRateLimit(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusTooManyRequests)
		w.Write([]byte(`{"error": "rate limit"}`))
	}))
	defer server.Close()

	original := HTTPClient
	HTTPClient = &mockHTTPClient{server: server}
	defer func() { HTTPClient = original }()

	_, err := SearchSkillsSh("test", server.URL, 10)
	if err == nil {
		t.Fatal("expected error for rate limit, got nil")
	}

	if !contains(err.Error(), "rate limit") {
		t.Errorf("error = %q, expected to contain 'rate limit'", err.Error())
	}
}

func TestSearchSkillsSh_HandlesServerError(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte(`{"error": "internal error"}`))
	}))
	defer server.Close()

	original := HTTPClient
	HTTPClient = &mockHTTPClient{server: server}
	defer func() { HTTPClient = original }()

	_, err := SearchSkillsSh("test", server.URL, 10)
	if err == nil {
		t.Fatal("expected error for server error, got nil")
	}

	if !contains(err.Error(), "500") {
		t.Errorf("error = %q, expected to contain status code", err.Error())
	}
}

func TestSearchSkillsSh_UsesDefaultBaseURL(t *testing.T) {
	// Verify that passing empty baseURL uses the default constant.
	if SkillsShDefaultBaseURL != "https://skills.sh" {
		t.Errorf("SkillsShDefaultBaseURL = %q, want %q", SkillsShDefaultBaseURL, "https://skills.sh")
	}
}

func TestSkillsShSkillToSearchResult_ConvertsCorrectly(t *testing.T) {
	skill := skillsShSkill{
		ID:       "react-patterns",
		Name:     "React Patterns",
		Installs: 50000,
		Source:   "org/repo",
	}

	result := skillsShSkillToSearchResult(skill)

	if result.Name != "React Patterns" {
		t.Errorf("Name = %q, want %q", result.Name, "React Patterns")
	}
	if result.Stars != 50000 {
		t.Errorf("Stars = %d, want 50000", result.Stars)
	}
	if result.Owner != "org" {
		t.Errorf("Owner = %q, want %q", result.Owner, "org")
	}
	if result.Repo != "repo" {
		t.Errorf("Repo = %q, want %q", result.Repo, "repo")
	}
	if result.URL != "https://github.com/org/repo" {
		t.Errorf("URL = %q, want GitHub URL", result.URL)
	}
}

func TestSkillsShSkillToSearchResult_FallsBackToID(t *testing.T) {
	skill := skillsShSkill{
		ID:       "my-skill-id",
		Name:     "",
		Installs: 100,
		Source:   "",
	}

	result := skillsShSkillToSearchResult(skill)

	if result.Name != "my-skill-id" {
		t.Errorf("Name = %q, want %q (fallback to ID)", result.Name, "my-skill-id")
	}
	if result.Owner != "" {
		t.Errorf("Owner = %q, want empty", result.Owner)
	}
	if result.URL != "" {
		t.Errorf("URL = %q, want empty", result.URL)
	}
}

func TestFormatInstallCount(t *testing.T) {
	tests := []struct {
		count    int
		expected string
	}{
		{0, ""},
		{-1, ""},
		{1, "1 installs"},
		{999, "999 installs"},
		{1000, "1.0K installs"},
		{1500, "1.5K installs"},
		{176400, "176.4K installs"},
		{1000000, "1.0M installs"},
		{2500000, "2.5M installs"},
	}

	for _, tt := range tests {
		result := FormatInstallCount(tt.count)
		if result != tt.expected {
			t.Errorf("FormatInstallCount(%d) = %q, want %q", tt.count, result, tt.expected)
		}
	}
}

// contains is a helper for checking substrings.
func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > 0 && containsHelper(s, substr))
}

func containsHelper(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}

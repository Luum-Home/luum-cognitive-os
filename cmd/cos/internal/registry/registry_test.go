package registry

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// mockHTTPClient wraps an httptest.Server to implement the HTTPClient interface.
type mockHTTPClient struct {
	server *httptest.Server
}

func (m *mockHTTPClient) Do(req *http.Request) (*http.Response, error) {
	// Redirect the request to our test server.
	req.URL.Scheme = "http"
	req.URL.Host = strings.TrimPrefix(m.server.URL, "http://")
	return http.DefaultClient.Do(req)
}

// sampleSearchResponse returns a valid GitHub search API response with one result.
func sampleSearchResponse() githubSearchResponse {
	return githubSearchResponse{
		TotalCount: 1,
		Items: []githubSearchItem{
			{
				FullName:        "luum/safety-mesh",
				Description:     "Multi-layer security mesh for AI agents",
				StargazersCount: 42,
				License: &githubLic{
					SPDXID: "MIT",
					Name:   "MIT License",
				},
				HTMLURL:   "https://github.com/luum/safety-mesh",
				Topics:    []string{"cos-package", "security", "ai-agents"},
				UpdatedAt: "2026-03-15T10:00:00Z",
				Owner:     &githubOwner{Login: "luum"},
			},
		},
	}
}

func TestSearchResult_Fields(t *testing.T) {
	r := SearchResult{
		Name:        "@luum/safety-mesh",
		Description: "Multi-layer security mesh",
		Owner:       "luum",
		Repo:        "safety-mesh",
		Stars:       42,
		License:     "MIT",
		URL:         "https://github.com/luum/safety-mesh",
		Topics:      []string{"cos-package", "security"},
		UpdatedAt:   "2026-03-15T10:00:00Z",
	}

	if r.Name != "@luum/safety-mesh" {
		t.Errorf("Name = %q, want %q", r.Name, "@luum/safety-mesh")
	}
	if r.Owner != "luum" {
		t.Errorf("Owner = %q, want %q", r.Owner, "luum")
	}
	if r.Repo != "safety-mesh" {
		t.Errorf("Repo = %q, want %q", r.Repo, "safety-mesh")
	}
	if r.Stars != 42 {
		t.Errorf("Stars = %d, want %d", r.Stars, 42)
	}
	if r.License != "MIT" {
		t.Errorf("License = %q, want %q", r.License, "MIT")
	}
	if len(r.Topics) != 2 {
		t.Errorf("Topics len = %d, want 2", len(r.Topics))
	}
}

func TestSearchGitHub_ParsesResponse(t *testing.T) {
	resp := sampleSearchResponse()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}))
	defer server.Close()

	// Swap the global HTTPClient for the test.
	original := HTTPClient
	HTTPClient = &mockHTTPClient{server: server}
	defer func() { HTTPClient = original }()

	results, err := SearchGitHub("security", 10)
	if err != nil {
		t.Fatalf("SearchGitHub error: %v", err)
	}

	if len(results) != 1 {
		t.Fatalf("results len = %d, want 1", len(results))
	}

	r := results[0]
	if r.Name != "@luum/safety-mesh" {
		t.Errorf("Name = %q, want %q", r.Name, "@luum/safety-mesh")
	}
	if r.Stars != 42 {
		t.Errorf("Stars = %d, want 42", r.Stars)
	}
	if r.License != "MIT" {
		t.Errorf("License = %q, want %q", r.License, "MIT")
	}
	if r.Description != "Multi-layer security mesh for AI agents" {
		t.Errorf("Description = %q, want correct value", r.Description)
	}
	if r.Owner != "luum" {
		t.Errorf("Owner = %q, want %q", r.Owner, "luum")
	}
	if r.Repo != "safety-mesh" {
		t.Errorf("Repo = %q, want %q", r.Repo, "safety-mesh")
	}
}

func TestSearchGitHub_HandlesRateLimit(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusForbidden)
		w.Write([]byte(`{"message": "API rate limit exceeded"}`))
	}))
	defer server.Close()

	original := HTTPClient
	HTTPClient = &mockHTTPClient{server: server}
	defer func() { HTTPClient = original }()

	_, err := SearchGitHub("test", 10)
	if err == nil {
		t.Fatal("expected error for rate limit, got nil")
	}

	if !strings.Contains(err.Error(), "rate limit") {
		t.Errorf("error = %q, expected to contain 'rate limit'", err.Error())
	}
}

func TestSearchGitHub_EmptyResults(t *testing.T) {
	emptyResp := githubSearchResponse{
		TotalCount: 0,
		Items:      []githubSearchItem{},
	}

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(emptyResp)
	}))
	defer server.Close()

	original := HTTPClient
	HTTPClient = &mockHTTPClient{server: server}
	defer func() { HTTPClient = original }()

	results, err := SearchGitHub("nonexistent-package-xyz", 10)
	if err != nil {
		t.Fatalf("SearchGitHub error: %v", err)
	}

	if len(results) != 0 {
		t.Errorf("results len = %d, want 0", len(results))
	}
}

func TestSearchGitHub_BuildsQuery(t *testing.T) {
	apiURL := BuildSearchURL("security audit", 15)

	if !strings.Contains(apiURL, "api.github.com/search/repositories") {
		t.Errorf("URL missing API path: %s", apiURL)
	}

	if !strings.Contains(apiURL, "topic%3Acos-package") {
		t.Errorf("URL missing cos-package topic filter: %s", apiURL)
	}

	if !strings.Contains(apiURL, "per_page=15") {
		t.Errorf("URL missing per_page: %s", apiURL)
	}

	if !strings.Contains(apiURL, "sort=stars") {
		t.Errorf("URL missing sort=stars: %s", apiURL)
	}

	// Query should be URL-encoded.
	if !strings.Contains(apiURL, "security+audit") && !strings.Contains(apiURL, "security%20audit") {
		t.Errorf("URL missing query terms: %s", apiURL)
	}
}

func TestSearchByType_FiltersCorrectly(t *testing.T) {
	results := []SearchResult{
		{Name: "@a/b", Topics: []string{"cos-package", "cos-skill"}},
		{Name: "@c/d", Topics: []string{"cos-package", "cos-rule"}},
		{Name: "@e/f", Topics: []string{"cos-package", "cos-skill"}},
	}

	filtered := SearchByType(results, "skill")
	if len(filtered) != 2 {
		t.Errorf("filtered len = %d, want 2", len(filtered))
	}

	filtered = SearchByType(results, "rule")
	if len(filtered) != 1 {
		t.Errorf("filtered len = %d, want 1", len(filtered))
	}

	filtered = SearchByType(results, "")
	if len(filtered) != 3 {
		t.Errorf("empty filter should return all: got %d, want 3", len(filtered))
	}
}

func TestFilterByLicense_FiltersCorrectly(t *testing.T) {
	results := []SearchResult{
		{Name: "@a/b", License: "MIT"},
		{Name: "@c/d", License: "Apache-2.0"},
		{Name: "@e/f", License: "MIT"},
	}

	filtered := FilterByLicense(results, "MIT")
	if len(filtered) != 2 {
		t.Errorf("filtered len = %d, want 2", len(filtered))
	}

	filtered = FilterByLicense(results, "Apache-2.0")
	if len(filtered) != 1 {
		t.Errorf("filtered len = %d, want 1", len(filtered))
	}

	filtered = FilterByLicense(results, "")
	if len(filtered) != 3 {
		t.Errorf("empty filter should return all: got %d, want 3", len(filtered))
	}
}

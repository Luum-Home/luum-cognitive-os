package registry

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

func TestDefaultRegistries_HasCosPackageTopic(t *testing.T) {
	defaults := DefaultRegistries()
	if len(defaults) != 1 {
		t.Fatalf("DefaultRegistries() len = %d, want 1", len(defaults))
	}

	r := defaults[0]
	if r.Type != RegistryGitHubTopic {
		t.Errorf("Type = %q, want %q", r.Type, RegistryGitHubTopic)
	}
	if r.Topic != "cos-package" {
		t.Errorf("Topic = %q, want %q", r.Topic, "cos-package")
	}
	if !r.Enabled {
		t.Error("Enabled = false, want true")
	}
}

func TestLoadRegistries_FallsBackToDefaults(t *testing.T) {
	// Use a temp directory with no cognitive-os.yaml.
	dir := t.TempDir()
	registries := LoadRegistries(dir)

	if len(registries) != 1 {
		t.Fatalf("LoadRegistries with no config: len = %d, want 1", len(registries))
	}
	if registries[0].Name != "cos-official" {
		t.Errorf("Name = %q, want %q", registries[0].Name, "cos-official")
	}
}

func TestLoadRegistries_ReadsFromConfig(t *testing.T) {
	dir := t.TempDir()
	config := `
packages:
  registries:
    - name: test-org
      type: github-org
      org: test-org
      enabled: true
      priority: 1
    - name: local-dev
      type: directory
      path: /tmp/packages
      enabled: false
      priority: 5
`
	if err := os.WriteFile(filepath.Join(dir, "cognitive-os.yaml"), []byte(config), 0644); err != nil {
		t.Fatalf("writing config: %v", err)
	}

	registries := LoadRegistries(dir)

	if len(registries) != 2 {
		t.Fatalf("LoadRegistries len = %d, want 2", len(registries))
	}

	if registries[0].Name != "test-org" {
		t.Errorf("[0].Name = %q, want %q", registries[0].Name, "test-org")
	}
	if registries[0].Type != RegistryGitHubOrg {
		t.Errorf("[0].Type = %q, want %q", registries[0].Type, RegistryGitHubOrg)
	}
	if registries[0].Org != "test-org" {
		t.Errorf("[0].Org = %q, want %q", registries[0].Org, "test-org")
	}
	if !registries[0].Enabled {
		t.Error("[0].Enabled = false, want true")
	}

	if registries[1].Name != "local-dev" {
		t.Errorf("[1].Name = %q, want %q", registries[1].Name, "local-dev")
	}
	if registries[1].Type != RegistryDirectory {
		t.Errorf("[1].Type = %q, want %q", registries[1].Type, RegistryDirectory)
	}
	if registries[1].Enabled {
		t.Error("[1].Enabled = true, want false")
	}
}

func TestEnabledRegistries_FiltersAndSorts(t *testing.T) {
	registries := []RegistryConfig{
		{Name: "low-pri", Enabled: true, Priority: 10},
		{Name: "disabled", Enabled: false, Priority: 1},
		{Name: "high-pri", Enabled: true, Priority: 1},
		{Name: "mid-pri", Enabled: true, Priority: 5},
	}

	enabled := EnabledRegistries(registries)

	if len(enabled) != 3 {
		t.Fatalf("EnabledRegistries len = %d, want 3", len(enabled))
	}

	// Should be sorted by priority.
	if enabled[0].Name != "high-pri" {
		t.Errorf("[0].Name = %q, want %q", enabled[0].Name, "high-pri")
	}
	if enabled[1].Name != "mid-pri" {
		t.Errorf("[1].Name = %q, want %q", enabled[1].Name, "mid-pri")
	}
	if enabled[2].Name != "low-pri" {
		t.Errorf("[2].Name = %q, want %q", enabled[2].Name, "low-pri")
	}
}

func TestFindRegistry_FindsByName(t *testing.T) {
	registries := []RegistryConfig{
		{Name: "first"},
		{Name: "second"},
		{Name: "third"},
	}

	found := FindRegistry(registries, "second")
	if found == nil {
		t.Fatal("FindRegistry returned nil for existing name")
	}
	if found.Name != "second" {
		t.Errorf("Name = %q, want %q", found.Name, "second")
	}

	notFound := FindRegistry(registries, "nonexistent")
	if notFound != nil {
		t.Error("FindRegistry should return nil for non-existing name")
	}
}

func TestSearchAllRegistries_MergesAndDeduplicates(t *testing.T) {
	resp := sampleSearchResponse()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}))
	defer server.Close()

	original := HTTPClient
	HTTPClient = &mockHTTPClient{server: server}
	defer func() { HTTPClient = original }()

	registries := []RegistryConfig{
		{Name: "reg-a", Type: RegistryGitHubTopic, Topic: "cos-package", Enabled: true, Priority: 1},
		{Name: "reg-b", Type: RegistryGitHubTopic, Topic: "cos-package", Enabled: true, Priority: 2},
	}

	results, errs := SearchAllRegistries(registries, "security", 10)

	if len(errs) != 0 {
		t.Errorf("unexpected errors: %v", errs)
	}

	// Both registries return the same repo, should be deduplicated.
	if len(results) != 1 {
		t.Errorf("results len = %d, want 1 (deduplicated)", len(results))
	}

	if results[0].Registry != "reg-a" {
		t.Errorf("Registry = %q, want %q (first registry wins)", results[0].Registry, "reg-a")
	}
}

func TestSearchAllRegistries_SkipsDisabledRegistries(t *testing.T) {
	resp := sampleSearchResponse()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}))
	defer server.Close()

	original := HTTPClient
	HTTPClient = &mockHTTPClient{server: server}
	defer func() { HTTPClient = original }()

	registries := []RegistryConfig{
		{Name: "enabled-reg", Type: RegistryGitHubTopic, Topic: "cos-package", Enabled: true, Priority: 1},
		{Name: "disabled-reg", Type: RegistryGitHubTopic, Topic: "cos-package", Enabled: false, Priority: 2},
	}

	results, _ := SearchAllRegistries(registries, "security", 10)

	if len(results) != 1 {
		t.Fatalf("results len = %d, want 1", len(results))
	}
	if results[0].Registry != "enabled-reg" {
		t.Errorf("Registry = %q, want %q", results[0].Registry, "enabled-reg")
	}
}

func TestSearchOneRegistry_ReturnsAnnotated(t *testing.T) {
	resp := sampleSearchResponse()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}))
	defer server.Close()

	original := HTTPClient
	HTTPClient = &mockHTTPClient{server: server}
	defer func() { HTTPClient = original }()

	registries := []RegistryConfig{
		{Name: "my-reg", Type: RegistryGitHubTopic, Topic: "cos-package", Enabled: true, Priority: 1},
	}

	results, err := SearchOneRegistry(registries, "my-reg", "security", 10)
	if err != nil {
		t.Fatalf("SearchOneRegistry error: %v", err)
	}

	if len(results) != 1 {
		t.Fatalf("results len = %d, want 1", len(results))
	}
	if results[0].Registry != "my-reg" {
		t.Errorf("Registry = %q, want %q", results[0].Registry, "my-reg")
	}
}

func TestSearchOneRegistry_ErrorOnNotFound(t *testing.T) {
	registries := []RegistryConfig{
		{Name: "existing", Type: RegistryGitHubTopic, Enabled: true},
	}

	_, err := SearchOneRegistry(registries, "nonexistent", "test", 10)
	if err == nil {
		t.Fatal("expected error for nonexistent registry")
	}
}

func TestSearchOneRegistry_ErrorOnDisabled(t *testing.T) {
	registries := []RegistryConfig{
		{Name: "disabled-reg", Type: RegistryGitHubTopic, Enabled: false},
	}

	_, err := SearchOneRegistry(registries, "disabled-reg", "test", 10)
	if err == nil {
		t.Fatal("expected error for disabled registry")
	}
}

func TestSearchLocal_FindsPackages(t *testing.T) {
	dir := t.TempDir()

	// Create package directories.
	pkg1Dir := filepath.Join(dir, "my-skill")
	os.MkdirAll(pkg1Dir, 0755)
	os.WriteFile(filepath.Join(pkg1Dir, "cos-package.yaml"), []byte("name: my-skill\ndescription: A test skill"), 0644)

	pkg2Dir := filepath.Join(dir, "another-pkg")
	os.MkdirAll(pkg2Dir, 0755)
	os.WriteFile(filepath.Join(pkg2Dir, "SKILL.md"), []byte("# My Skill"), 0644)

	// Directory without manifest or skill (should be skipped).
	os.MkdirAll(filepath.Join(dir, "not-a-package"), 0755)

	results, err := SearchLocal(dir, "")
	if err != nil {
		t.Fatalf("SearchLocal error: %v", err)
	}

	if len(results) != 2 {
		t.Fatalf("results len = %d, want 2", len(results))
	}
}

func TestSearchLocal_FiltersQuery(t *testing.T) {
	dir := t.TempDir()

	os.MkdirAll(filepath.Join(dir, "security-tool"), 0755)
	os.WriteFile(filepath.Join(dir, "security-tool", "cos-package.yaml"), []byte("name: security-tool"), 0644)

	os.MkdirAll(filepath.Join(dir, "data-tool"), 0755)
	os.WriteFile(filepath.Join(dir, "data-tool", "cos-package.yaml"), []byte("name: data-tool"), 0644)

	results, err := SearchLocal(dir, "security")
	if err != nil {
		t.Fatalf("SearchLocal error: %v", err)
	}

	if len(results) != 1 {
		t.Fatalf("results len = %d, want 1", len(results))
	}
	if results[0].Name != "security-tool" {
		t.Errorf("Name = %q, want %q", results[0].Name, "security-tool")
	}
}

func TestSearchLocal_ReturnsEmptyForMissingDir(t *testing.T) {
	results, err := SearchLocal("/nonexistent/path/xyz", "test")
	if err != nil {
		t.Fatalf("SearchLocal error: %v", err)
	}
	if len(results) != 0 {
		t.Errorf("results len = %d, want 0", len(results))
	}
}

func TestSearchGitHubOrg_BuildsOrgQuery(t *testing.T) {
	var receivedQuery string

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		receivedQuery = r.URL.Query().Get("q")
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(githubSearchResponse{TotalCount: 0, Items: []githubSearchItem{}})
	}))
	defer server.Close()

	original := HTTPClient
	HTTPClient = &mockHTTPClient{server: server}
	defer func() { HTTPClient = original }()

	_, _ = SearchGitHubOrg("test-org", "security", 10)

	if receivedQuery == "" {
		t.Fatal("no query received")
	}

	// The query should contain org:test-org.
	if receivedQuery != "security org:test-org" {
		t.Errorf("query = %q, want %q", receivedQuery, "security org:test-org")
	}
}

func TestSearchGitHubOrg_EmptyQuery(t *testing.T) {
	var receivedQuery string

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		receivedQuery = r.URL.Query().Get("q")
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(githubSearchResponse{TotalCount: 0, Items: []githubSearchItem{}})
	}))
	defer server.Close()

	original := HTTPClient
	HTTPClient = &mockHTTPClient{server: server}
	defer func() { HTTPClient = original }()

	_, _ = SearchGitHubOrg("my-org", "", 10)

	if receivedQuery != "org:my-org" {
		t.Errorf("query = %q, want %q", receivedQuery, "org:my-org")
	}
}

func TestSearchAllRegistries_HandlesFailedRegistryGracefully(t *testing.T) {
	registries := []RegistryConfig{
		{Name: "bad-org", Type: RegistryGitHubOrg, Org: "", Enabled: true, Priority: 1},
	}

	results, errs := SearchAllRegistries(registries, "test", 10)

	if len(errs) == 0 {
		t.Error("expected errors for misconfigured registry")
	}
	if len(results) != 0 {
		t.Errorf("results len = %d, want 0", len(results))
	}
}

func TestSkillsShRegistryType_Recognized(t *testing.T) {
	var rt RegistryType = "skills-sh"
	if rt != RegistrySkillsSh {
		t.Errorf("RegistryType %q != RegistrySkillsSh", rt)
	}
}

func TestLoadRegistries_ReadsSkillsSh(t *testing.T) {
	dir := t.TempDir()
	config := `
packages:
  registries:
    - name: skills-sh
      type: skills-sh
      enabled: true
      priority: 5
`
	if err := os.WriteFile(filepath.Join(dir, "cognitive-os.yaml"), []byte(config), 0644); err != nil {
		t.Fatalf("writing config: %v", err)
	}

	registries := LoadRegistries(dir)

	if len(registries) != 1 {
		t.Fatalf("LoadRegistries len = %d, want 1", len(registries))
	}

	if registries[0].Type != RegistrySkillsSh {
		t.Errorf("Type = %q, want %q", registries[0].Type, RegistrySkillsSh)
	}
	if registries[0].Name != "skills-sh" {
		t.Errorf("Name = %q, want %q", registries[0].Name, "skills-sh")
	}
	if registries[0].Priority != 5 {
		t.Errorf("Priority = %d, want 5", registries[0].Priority)
	}
}

func TestSearchAllRegistries_IncludesSkillsSh(t *testing.T) {
	skillsResp := skillsShSearchResponse{
		Skills: []skillsShSkill{
			{ID: "react-skill", Name: "React Skill", Installs: 1000, Source: "test/repo"},
		},
	}

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/search" {
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(skillsResp)
			return
		}
		// GitHub fallback.
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(githubSearchResponse{TotalCount: 0, Items: []githubSearchItem{}})
	}))
	defer server.Close()

	original := HTTPClient
	HTTPClient = &mockHTTPClient{server: server}
	defer func() { HTTPClient = original }()

	registries := []RegistryConfig{
		{Name: "skills-sh", Type: RegistrySkillsSh, BaseURL: server.URL, Enabled: true, Priority: 1},
	}

	results, errs := SearchAllRegistries(registries, "react", 10)

	if len(errs) != 0 {
		t.Errorf("unexpected errors: %v", errs)
	}

	if len(results) != 1 {
		t.Fatalf("results len = %d, want 1", len(results))
	}

	if results[0].Name != "React Skill" {
		t.Errorf("Name = %q, want %q", results[0].Name, "React Skill")
	}
	if results[0].Registry != "skills-sh" {
		t.Errorf("Registry = %q, want %q", results[0].Registry, "skills-sh")
	}
}

func TestSearchAllRegistries_PriorityOrdering(t *testing.T) {
	// Create two servers returning different results.
	makeServer := func(name, owner string) *httptest.Server {
		return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			resp := githubSearchResponse{
				TotalCount: 1,
				Items: []githubSearchItem{
					{
						FullName:        owner + "/" + name,
						Description:     name + " description",
						StargazersCount: 10,
						HTMLURL:         "https://github.com/" + owner + "/" + name,
						Owner:           &githubOwner{Login: owner},
					},
				},
			}
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(resp)
		}))
	}

	serverA := makeServer("pkg-a", "org-a")
	defer serverA.Close()

	// Both servers respond to any request, but we test ordering.
	// With the mock client redirecting to one server, we verify that
	// the first registry's results come first in the output.
	original := HTTPClient
	HTTPClient = &mockHTTPClient{server: serverA}
	defer func() { HTTPClient = original }()

	registries := []RegistryConfig{
		{Name: "low-pri", Type: RegistryGitHubTopic, Topic: "test", Enabled: true, Priority: 10},
		{Name: "high-pri", Type: RegistryGitHubTopic, Topic: "test", Enabled: true, Priority: 1},
	}

	results, _ := SearchAllRegistries(registries, "test", 10)

	// Results should be from high-pri first (priority 1 searched first).
	if len(results) < 1 {
		t.Fatal("expected at least 1 result")
	}
	if results[0].Registry != "high-pri" {
		t.Errorf("first result registry = %q, want %q", results[0].Registry, "high-pri")
	}
}

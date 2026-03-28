package resolver

import (
	"os"
	"path/filepath"
	"testing"
)

// ---------------------------------------------------------------------------
// Resolve tests
// ---------------------------------------------------------------------------

func TestResolve_LocalRelative(t *testing.T) {
	// Create a temp dir to act as the local package.
	dir := t.TempDir()
	relDir := "./" + filepath.Base(dir)

	// We need to be in the parent dir for "./" to resolve.
	origWd, _ := os.Getwd()
	_ = os.Chdir(filepath.Dir(dir))
	defer func() { _ = os.Chdir(origWd) }()

	src, err := Resolve(relDir)
	if err != nil {
		t.Fatalf("Resolve(%q) error: %v", relDir, err)
	}

	if src.Type != SourceLocal {
		t.Errorf("expected SourceLocal, got %d", src.Type)
	}
	if src.LocalPath != relDir {
		t.Errorf("expected LocalPath %q, got %q", relDir, src.LocalPath)
	}
	if src.Name == "" {
		t.Error("expected non-empty Name")
	}
}

func TestResolve_LocalAbsolute(t *testing.T) {
	dir := t.TempDir()

	src, err := Resolve(dir)
	if err != nil {
		t.Fatalf("Resolve(%q) error: %v", dir, err)
	}

	if src.Type != SourceLocal {
		t.Errorf("expected SourceLocal, got %d", src.Type)
	}
	if src.LocalPath != dir {
		t.Errorf("expected LocalPath %q, got %q", dir, src.LocalPath)
	}
}

func TestResolve_LocalNotExist(t *testing.T) {
	_, err := Resolve("/nonexistent/path/to/pkg")
	if err == nil {
		t.Fatal("expected error for nonexistent local path")
	}
}

func TestResolve_LocalNotDir(t *testing.T) {
	f, err := os.CreateTemp("", "cos-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.Remove(f.Name())
	f.Close()

	_, err = Resolve(f.Name())
	if err == nil {
		t.Fatal("expected error for file (not directory)")
	}
}

func TestResolve_Scoped(t *testing.T) {
	src, err := Resolve("@luum/safety-mesh")
	if err != nil {
		t.Fatalf("Resolve error: %v", err)
	}

	if src.Type != SourceGitHub {
		t.Errorf("expected SourceGitHub, got %d", src.Type)
	}
	if src.Owner != "luum" {
		t.Errorf("expected owner 'luum', got %q", src.Owner)
	}
	if src.Repo != "safety-mesh" {
		t.Errorf("expected repo 'safety-mesh', got %q", src.Repo)
	}
	if src.Name != "safety-mesh" {
		t.Errorf("expected name 'safety-mesh', got %q", src.Name)
	}
	if src.Version != "" {
		t.Errorf("expected empty version, got %q", src.Version)
	}
	if src.URL != "https://github.com/luum/safety-mesh" {
		t.Errorf("unexpected URL: %q", src.URL)
	}
}

func TestResolve_ScopedWithVersion(t *testing.T) {
	src, err := Resolve("@luum/safety-mesh@1.0.0")
	if err != nil {
		t.Fatalf("Resolve error: %v", err)
	}

	if src.Type != SourceGitHub {
		t.Errorf("expected SourceGitHub, got %d", src.Type)
	}
	if src.Owner != "luum" {
		t.Errorf("expected owner 'luum', got %q", src.Owner)
	}
	if src.Repo != "safety-mesh" {
		t.Errorf("expected repo 'safety-mesh', got %q", src.Repo)
	}
	if src.Version != "1.0.0" {
		t.Errorf("expected version '1.0.0', got %q", src.Version)
	}
}

func TestResolve_ScopedInvalid(t *testing.T) {
	cases := []string{
		"@",
		"@/",
		"@luum/",
		"@/name",
		"@luum",
	}
	for _, spec := range cases {
		_, err := Resolve(spec)
		if err == nil {
			t.Errorf("expected error for %q, got nil", spec)
		}
	}
}

func TestResolve_GitHubDomain(t *testing.T) {
	src, err := Resolve("github.com/org/repo")
	if err != nil {
		t.Fatalf("Resolve error: %v", err)
	}

	if src.Type != SourceGitHub {
		t.Errorf("expected SourceGitHub, got %d", src.Type)
	}
	if src.Owner != "org" {
		t.Errorf("expected owner 'org', got %q", src.Owner)
	}
	if src.Repo != "repo" {
		t.Errorf("expected repo 'repo', got %q", src.Repo)
	}
	if src.Name != "repo" {
		t.Errorf("expected name 'repo', got %q", src.Name)
	}
}

func TestResolve_GitHubDomainWithGitSuffix(t *testing.T) {
	src, err := Resolve("github.com/org/repo.git")
	if err != nil {
		t.Fatalf("Resolve error: %v", err)
	}

	if src.Owner != "org" {
		t.Errorf("expected owner 'org', got %q", src.Owner)
	}
	if src.Repo != "repo" {
		t.Errorf("expected repo 'repo', got %q", src.Repo)
	}
}

func TestResolve_GitHubURL(t *testing.T) {
	src, err := Resolve("https://github.com/org/repo")
	if err != nil {
		t.Fatalf("Resolve error: %v", err)
	}

	if src.Type != SourceURL {
		t.Errorf("expected SourceURL, got %d", src.Type)
	}
	if src.Owner != "org" {
		t.Errorf("expected owner 'org', got %q", src.Owner)
	}
	if src.Repo != "repo" {
		t.Errorf("expected repo 'repo', got %q", src.Repo)
	}
	if src.URL != "https://github.com/org/repo" {
		t.Errorf("unexpected URL: %q", src.URL)
	}
}

func TestResolve_GitHubURLWithTrailingSlash(t *testing.T) {
	src, err := Resolve("https://github.com/org/repo/")
	if err != nil {
		t.Fatalf("Resolve error: %v", err)
	}

	if src.Owner != "org" {
		t.Errorf("expected owner 'org', got %q", src.Owner)
	}
	if src.Repo != "repo" {
		t.Errorf("expected repo 'repo', got %q", src.Repo)
	}
}

func TestResolve_Invalid(t *testing.T) {
	_, err := Resolve("")
	if err == nil {
		t.Fatal("expected error for empty string")
	}
}

func TestResolve_PlainName(t *testing.T) {
	src, err := Resolve("my-skill")
	if err != nil {
		t.Fatalf("Resolve error: %v", err)
	}

	if src.Type != SourceGitHub {
		t.Errorf("expected SourceGitHub, got %d", src.Type)
	}
	if src.Name != "my-skill" {
		t.Errorf("expected name 'my-skill', got %q", src.Name)
	}
	if src.Owner != "my-skill" {
		t.Errorf("expected owner 'my-skill', got %q", src.Owner)
	}
	if src.Repo != "my-skill" {
		t.Errorf("expected repo 'my-skill', got %q", src.Repo)
	}
}

func TestResolve_PlainNameInvalid(t *testing.T) {
	_, err := Resolve("has space")
	if err == nil {
		t.Fatal("expected error for name with space")
	}
}

func TestResolve_ScopedNoRepo(t *testing.T) {
	// "@luum" without a repo should error.
	_, err := Resolve("@luum")
	if err == nil {
		t.Fatal("expected error for @luum without repo")
	}
}

func TestResolve_URLWithPath(t *testing.T) {
	src, err := Resolve("https://github.com/org/repo/tree/main/subdir")
	if err != nil {
		t.Fatalf("Resolve error: %v", err)
	}

	// Should extract org/repo even with extra path components.
	if src.Owner != "org" {
		t.Errorf("expected owner 'org', got %q", src.Owner)
	}
	if src.Repo != "repo" {
		t.Errorf("expected repo 'repo', got %q", src.Repo)
	}
}

func TestResolve_Version_Semver(t *testing.T) {
	src, err := Resolve("@luum/pkg@v1.2.3")
	if err != nil {
		t.Fatalf("Resolve error: %v", err)
	}

	if src.Version != "v1.2.3" {
		t.Errorf("expected version 'v1.2.3', got %q", src.Version)
	}
	if src.Owner != "luum" {
		t.Errorf("expected owner 'luum', got %q", src.Owner)
	}
	if src.Repo != "pkg" {
		t.Errorf("expected repo 'pkg', got %q", src.Repo)
	}
}

// ---------------------------------------------------------------------------
// String tests
// ---------------------------------------------------------------------------

func TestSourceString_Local(t *testing.T) {
	s := &ResolvedSource{
		Type:      SourceLocal,
		Name:      "my-pkg",
		LocalPath: "/tmp/my-pkg",
	}
	got := s.String()
	if got != "[local] my-pkg (path: /tmp/my-pkg)" {
		t.Errorf("unexpected String(): %q", got)
	}
}

func TestSourceString_GitHub(t *testing.T) {
	s := &ResolvedSource{
		Type:    SourceGitHub,
		Owner:   "luum",
		Repo:    "safety-mesh",
		Version: "v1.0.0",
	}
	got := s.String()
	if got != "[github] luum/safety-mesh@v1.0.0" {
		t.Errorf("unexpected String(): %q", got)
	}
}

func TestSourceString_GitHubLatest(t *testing.T) {
	s := &ResolvedSource{
		Type:  SourceGitHub,
		Owner: "org",
		Repo:  "repo",
	}
	got := s.String()
	if got != "[github] org/repo@latest" {
		t.Errorf("unexpected String(): %q", got)
	}
}

func TestSourceString_URL(t *testing.T) {
	s := &ResolvedSource{
		Type:    SourceURL,
		Owner:   "org",
		Repo:    "repo",
		Version: "main",
	}
	got := s.String()
	if got != "[url] org/repo@main" {
		t.Errorf("unexpected String(): %q", got)
	}
}

// ---------------------------------------------------------------------------
// Fetch tests (local only, no network)
// ---------------------------------------------------------------------------

func TestFetchLocal(t *testing.T) {
	// Create a source directory with a file.
	srcDir := t.TempDir()
	testFile := filepath.Join(srcDir, "hello.txt")
	if err := os.WriteFile(testFile, []byte("world"), 0o644); err != nil {
		t.Fatal(err)
	}

	source := &ResolvedSource{
		Type:      SourceLocal,
		LocalPath: srcDir,
		Name:      "test-pkg",
	}

	fetchedDir, err := Fetch(source)
	if err != nil {
		t.Fatalf("Fetch error: %v", err)
	}
	defer func() { _ = CleanupFetch(filepath.Dir(fetchedDir)) }()

	// Verify the file was copied.
	copied := filepath.Join(fetchedDir, "hello.txt")
	data, err := os.ReadFile(copied)
	if err != nil {
		t.Fatalf("expected hello.txt in fetched dir: %v", err)
	}
	if string(data) != "world" {
		t.Errorf("expected 'world', got %q", string(data))
	}
}

func TestFetchLocal_WithSubdirs(t *testing.T) {
	srcDir := t.TempDir()

	// Create nested directory structure.
	subDir := filepath.Join(srcDir, "skills", "my-skill")
	if err := os.MkdirAll(subDir, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(subDir, "SKILL.md"), []byte("# Skill"), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(srcDir, "cos-package.yaml"), []byte("name: test"), 0644); err != nil {
		t.Fatal(err)
	}

	source := &ResolvedSource{
		Type:      SourceLocal,
		LocalPath: srcDir,
		Name:      "test-pkg",
	}

	fetchedDir, err := Fetch(source)
	if err != nil {
		t.Fatalf("Fetch error: %v", err)
	}
	defer func() { _ = CleanupFetch(filepath.Dir(fetchedDir)) }()

	// Verify nested file was copied.
	nestedFile := filepath.Join(fetchedDir, "skills", "my-skill", "SKILL.md")
	data, err := os.ReadFile(nestedFile)
	if err != nil {
		t.Fatalf("expected nested SKILL.md in fetched dir: %v", err)
	}
	if string(data) != "# Skill" {
		t.Errorf("expected '# Skill', got %q", string(data))
	}

	// Verify root file also copied.
	rootFile := filepath.Join(fetchedDir, "cos-package.yaml")
	if _, err := os.Stat(rootFile); err != nil {
		t.Errorf("expected cos-package.yaml in fetched dir: %v", err)
	}
}

func TestFetchLocal_Missing(t *testing.T) {
	source := &ResolvedSource{
		Type:      SourceLocal,
		LocalPath: "/nonexistent/path/for/cos/test",
		Name:      "missing",
	}

	_, err := Fetch(source)
	if err == nil {
		t.Fatal("expected error for nonexistent path")
	}
}

func TestFetch_NilSource(t *testing.T) {
	_, err := Fetch(nil)
	if err == nil {
		t.Fatal("expected error for nil source")
	}
}

func TestCleanupFetch(t *testing.T) {
	dir := t.TempDir()

	// Create a subdirectory inside os.TempDir so CleanupFetch allows removal.
	subDir, err := os.MkdirTemp(dir, "cos-cleanup-test-*")
	if err != nil {
		t.Fatal(err)
	}

	// CleanupFetch only removes paths under os.TempDir().
	// Since t.TempDir() is under os.TempDir(), this should work.
	err = CleanupFetch(subDir)
	if err != nil {
		t.Fatalf("CleanupFetch error: %v", err)
	}

	if _, err := os.Stat(subDir); !os.IsNotExist(err) {
		t.Error("expected directory to be removed")
	}
}

func TestCleanupFetch_EmptyString(t *testing.T) {
	err := CleanupFetch("")
	if err != nil {
		t.Errorf("CleanupFetch(\"\") should not error, got: %v", err)
	}
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

func TestCompareSemver(t *testing.T) {
	tests := []struct {
		a, b string
		want int // >0 if a > b
	}{
		{"v1.0.0", "v0.9.0", 1},
		{"v1.2.3", "v1.2.3", 0},
		{"v0.1.0", "v0.2.0", -1},
		{"1.0.0", "0.9.9", 1},
		{"v2.0.0", "v1.99.99", 1},
	}

	for _, tt := range tests {
		got := compareSemver(tt.a, tt.b)
		if (tt.want > 0 && got <= 0) || (tt.want < 0 && got >= 0) || (tt.want == 0 && got != 0) {
			t.Errorf("compareSemver(%q, %q) = %d, want sign %d", tt.a, tt.b, got, tt.want)
		}
	}
}

func TestExtractOwnerRepo(t *testing.T) {
	tests := []struct {
		input     string
		wantOwner string
		wantRepo  string
		wantErr   bool
	}{
		{"github.com/org/repo", "org", "repo", false},
		{"github.com/org/repo.git", "org", "repo", false},
		{"github.com/org/repo/", "org", "repo", false},
		{"github.com/org/repo/tree/main", "org", "repo", false},
		{"github.com/", "", "", true},
		{"github.com/org", "", "", true},
	}

	for _, tt := range tests {
		owner, repo, err := extractOwnerRepo(tt.input)
		if tt.wantErr {
			if err == nil {
				t.Errorf("extractOwnerRepo(%q) expected error", tt.input)
			}
			continue
		}
		if err != nil {
			t.Errorf("extractOwnerRepo(%q) error: %v", tt.input, err)
			continue
		}
		if owner != tt.wantOwner || repo != tt.wantRepo {
			t.Errorf("extractOwnerRepo(%q) = (%q, %q), want (%q, %q)",
				tt.input, owner, repo, tt.wantOwner, tt.wantRepo)
		}
	}
}

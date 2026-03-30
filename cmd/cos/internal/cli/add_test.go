package cli

import (
	"strings"
	"testing"

	"luum-agent-os/cmd/cos/internal/registry"
)

func TestPickBestMatch_ExactNameMatch(t *testing.T) {
	results := []registry.AnnotatedResult{
		{SearchResult: registry.SearchResult{Name: "typescript", Stars: 100}, Registry: "reg-a"},
		{SearchResult: registry.SearchResult{Name: "react", Stars: 200}, Registry: "reg-b"},
		{SearchResult: registry.SearchResult{Name: "react-native", Stars: 300}, Registry: "reg-c"},
	}

	best := pickBestMatch(results, "react")
	if best.Name != "react" {
		t.Errorf("Name = %q, want %q (exact match)", best.Name, "react")
	}
}

func TestPickBestMatch_ExactRepoMatch(t *testing.T) {
	results := []registry.AnnotatedResult{
		{SearchResult: registry.SearchResult{Name: "@org/react-tools", Repo: "react-tools", Stars: 100}, Registry: "reg-a"},
		{SearchResult: registry.SearchResult{Name: "@org/react", Repo: "react", Stars: 50}, Registry: "reg-b"},
	}

	best := pickBestMatch(results, "react")
	if best.Repo != "react" {
		t.Errorf("Repo = %q, want %q (exact repo match)", best.Repo, "react")
	}
}

func TestPickBestMatch_ContainsMatch(t *testing.T) {
	results := []registry.AnnotatedResult{
		{SearchResult: registry.SearchResult{Name: "awesome-react-patterns", Stars: 500}, Registry: "reg-a"},
		{SearchResult: registry.SearchResult{Name: "vue-patterns", Stars: 1000}, Registry: "reg-b"},
	}

	best := pickBestMatch(results, "react")
	if !strings.Contains(best.Name, "react") {
		t.Errorf("Name = %q, expected to contain 'react'", best.Name)
	}
}

func TestPickBestMatch_FallsBackToHighestStars(t *testing.T) {
	results := []registry.AnnotatedResult{
		{SearchResult: registry.SearchResult{Name: "alpha-tool", Stars: 100}, Registry: "reg-a"},
		{SearchResult: registry.SearchResult{Name: "beta-tool", Stars: 500}, Registry: "reg-b"},
		{SearchResult: registry.SearchResult{Name: "gamma-tool", Stars: 300}, Registry: "reg-c"},
	}

	best := pickBestMatch(results, "nonexistent")
	if best.Stars != 500 {
		t.Errorf("Stars = %d, want 500 (highest stars fallback)", best.Stars)
	}
}

func TestResolveInstallSpec_GitHubURL(t *testing.T) {
	r := registry.AnnotatedResult{
		SearchResult: registry.SearchResult{
			URL:   "https://github.com/org/repo",
			Owner: "org",
			Repo:  "repo",
		},
	}

	spec := resolveInstallSpec(r)
	if spec != "https://github.com/org/repo" {
		t.Errorf("spec = %q, want GitHub URL", spec)
	}
}

func TestResolveInstallSpec_ScopedName(t *testing.T) {
	r := registry.AnnotatedResult{
		SearchResult: registry.SearchResult{
			URL:   "https://example.com/not-github",
			Owner: "org",
			Repo:  "repo",
		},
	}

	spec := resolveInstallSpec(r)
	if spec != "@org/repo" {
		t.Errorf("spec = %q, want scoped name", spec)
	}
}

func TestResolveInstallSpec_Empty(t *testing.T) {
	r := registry.AnnotatedResult{
		SearchResult: registry.SearchResult{},
	}

	spec := resolveInstallSpec(r)
	if spec != "" {
		t.Errorf("spec = %q, want empty for unresolvable result", spec)
	}
}

func TestAddCmd_Registered(t *testing.T) {
	// Verify the add command is registered on the root command.
	found := false
	for _, cmd := range rootCmd.Commands() {
		if cmd.Name() == "add" {
			found = true
			break
		}
	}
	if !found {
		t.Error("'add' command not registered on root")
	}
}

func TestAddCmd_RequiresArgs(t *testing.T) {
	// Verify the command requires at least one argument.
	if addCmd.Args == nil {
		t.Fatal("add command should have Args validation")
	}
}

func TestAddCmd_HasFromFlag(t *testing.T) {
	flag := addCmd.Flags().Lookup("from")
	if flag == nil {
		t.Error("add command should have --from flag")
	}
}

func TestAddCmd_HasDryRunFlag(t *testing.T) {
	flag := addCmd.Flags().Lookup("dry-run")
	if flag == nil {
		t.Error("add command should have --dry-run flag")
	}
}

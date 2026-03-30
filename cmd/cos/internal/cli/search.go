package cli

import (
	"fmt"
	"os"
	"strings"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/project"
	"luum-agent-os/cmd/cos/internal/registry"
	"luum-agent-os/cmd/cos/internal/ui"
)

var (
	searchType     string
	searchLicense  string
	searchLimit    int
	searchRegistry string
)

var searchCmd = &cobra.Command{
	Use:   "search <query>",
	Short: "Search for cos packages across configured registries",
	Long: `Search configured registries for cos packages.

By default, searches all enabled registries (configured in cognitive-os.yaml
under packages.registries). Falls back to GitHub topic search if no registries
are configured.

Examples:
  cos search security                     Search all registries
  cos search --type skill linter          Find skill packages matching "linter"
  cos search --license MIT auth           Find MIT-licensed auth packages
  cos search --registry cos-official auth Search only the cos-official registry`,
	Args: cobra.ExactArgs(1),
	RunE: runSearch,
}

func init() {
	searchCmd.Flags().StringVar(&searchType, "type", "", "Filter by component type (skill, rule, hook, agent, template)")
	searchCmd.Flags().StringVar(&searchLicense, "license", "", "Filter by license (MIT, Apache-2.0, etc.)")
	searchCmd.Flags().IntVar(&searchLimit, "limit", 20, "Maximum number of results")
	searchCmd.Flags().StringVar(&searchRegistry, "registry", "", "Search only this registry (by name)")
	rootCmd.AddCommand(searchCmd)
}

func runSearch(cmd *cobra.Command, args []string) error {
	query := args[0]

	// Load registries from config.
	projectRoot := project.FindRootOrCwd()
	registries := registry.LoadRegistries(projectRoot)

	if searchRegistry != "" {
		ui.Step(ui.IconInfo, fmt.Sprintf("Searching registry %q for %q...", searchRegistry, query))
	} else {
		enabled := registry.EnabledRegistries(registries)
		names := make([]string, len(enabled))
		for i, r := range enabled {
			names[i] = r.Name
		}
		ui.Step(ui.IconInfo, fmt.Sprintf("Searching %d registry(ies) for %q...", len(enabled), query))
	}
	fmt.Println()

	var annotated []registry.AnnotatedResult
	var searchErrors []error

	if searchRegistry != "" {
		results, err := registry.SearchOneRegistry(registries, searchRegistry, query, searchLimit)
		if err != nil {
			fmt.Println(ui.ErrorStyle.Render(fmt.Sprintf("%s %s", ui.IconError, err.Error())))
			os.Exit(1)
		}
		annotated = results
	} else {
		results, errs := registry.SearchAllRegistries(registries, query, searchLimit)
		annotated = results
		searchErrors = errs
	}

	// Show non-fatal errors as warnings.
	for _, err := range searchErrors {
		fmt.Println(ui.WarningStyle.Render(fmt.Sprintf("  %s %s", ui.IconWarning, err.Error())))
	}

	// Convert to SearchResult slice for filtering.
	var results []registry.SearchResult
	registryMap := make(map[string]string) // URL -> registry name
	for _, a := range annotated {
		results = append(results, a.SearchResult)
		key := a.URL
		if key == "" {
			key = a.Name
		}
		registryMap[key] = a.Registry
	}

	// Apply client-side filters.
	if searchType != "" {
		results = registry.SearchByType(results, searchType)
	}
	if searchLicense != "" {
		results = registry.FilterByLicense(results, searchLicense)
	}

	if len(results) == 0 {
		fmt.Println(ui.MutedStyle.Render("  No packages found matching your query."))
		fmt.Println()
		fmt.Println(ui.MutedStyle.Render("  Tip: check your registries with 'cos registry list'."))
		return nil
	}

	fmt.Printf("Search results for %q:\n\n", query)

	for _, r := range results {
		key := r.URL
		if key == "" {
			key = r.Name
		}
		regName := registryMap[key]
		printSearchResultWithRegistry(r, regName)
	}

	fmt.Println()
	fmt.Printf("  %s\n", ui.MutedStyle.Render(fmt.Sprintf("%d package(s) found", len(results))))
	fmt.Println()
	fmt.Printf("  %s\n", ui.MutedStyle.Render("Install: cos add <name>"))

	return nil
}

// printSearchResultWithRegistry prints a single search result with registry annotation.
func printSearchResultWithRegistry(r registry.SearchResult, regName string) {
	// Name column: left-aligned, padded.
	name := ui.HeaderStyle.Render(fmt.Sprintf("%-26s", r.Name))

	// Stars column: show installs for skills-sh, stars for others.
	var stars string
	if regName == "skills-sh" && r.Stars > 0 {
		stars = ui.MutedStyle.Render(fmt.Sprintf("%-12s", registry.FormatInstallCount(r.Stars)))
	} else {
		stars = ui.MutedStyle.Render(fmt.Sprintf("★ %-5d", r.Stars))
	}

	// License column.
	license := r.License
	if license == "" {
		license = "Unknown"
	}
	licenseFmt := ui.DimStyle.Render(fmt.Sprintf("%-14s", license))

	// Description column: truncate if too long.
	desc := r.Description
	if len(desc) > 60 {
		desc = desc[:57] + "..."
	}

	fmt.Printf("  %s  %s  %s  %s\n", name, stars, licenseFmt, desc)

	// Show registry source and topics.
	var meta []string
	if regName != "" {
		meta = append(meta, fmt.Sprintf("from: %s", regName))
	}
	topics := filterTopics(r.Topics)
	if len(topics) > 0 {
		meta = append(meta, fmt.Sprintf("tags: %s", strings.Join(topics, ", ")))
	}
	if len(meta) > 0 {
		metaStr := ui.MutedStyle.Render(fmt.Sprintf("    %s", strings.Join(meta, "  |  ")))
		fmt.Printf("  %s\n", metaStr)
	}
}

// filterTopics removes the "cos-package" topic and returns the rest.
func filterTopics(topics []string) []string {
	filtered := make([]string, 0, len(topics))
	for _, t := range topics {
		if t != "cos-package" {
			filtered = append(filtered, t)
		}
	}
	return filtered
}

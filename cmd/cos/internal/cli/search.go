package cli

import (
	"fmt"
	"os"
	"strings"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/registry"
	"luum-agent-os/cmd/cos/internal/ui"
)

var (
	searchType    string
	searchLicense string
	searchLimit   int
)

var searchCmd = &cobra.Command{
	Use:   "search <query>",
	Short: "Search for cos packages on GitHub",
	Long: `Search the GitHub registry for cos packages.

Searches for repositories tagged with "cos-package" on GitHub.

Examples:
  cos search security           Find security-related packages
  cos search --type skill linter Find skill packages matching "linter"
  cos search --license MIT auth  Find MIT-licensed auth packages`,
	Args: cobra.ExactArgs(1),
	RunE: runSearch,
}

func init() {
	searchCmd.Flags().StringVar(&searchType, "type", "", "Filter by component type (skill, rule, hook, agent, template)")
	searchCmd.Flags().StringVar(&searchLicense, "license", "", "Filter by license (MIT, Apache-2.0, etc.)")
	searchCmd.Flags().IntVar(&searchLimit, "limit", 20, "Maximum number of results")
	rootCmd.AddCommand(searchCmd)
}

func runSearch(cmd *cobra.Command, args []string) error {
	query := args[0]

	ui.Step(ui.IconInfo, fmt.Sprintf("Searching for %q...", query))
	fmt.Println()

	results, err := registry.SearchGitHub(query, searchLimit)
	if err != nil {
		fmt.Println(ui.ErrorStyle.Render(fmt.Sprintf("%s %s", ui.IconError, err.Error())))
		os.Exit(1)
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
		fmt.Println(ui.MutedStyle.Render("  Tip: packages must have the 'cos-package' topic on GitHub."))
		return nil
	}

	fmt.Printf("Search results for %q:\n\n", query)

	for _, r := range results {
		printSearchResult(r)
	}

	fmt.Println()
	fmt.Printf("  %s\n", ui.MutedStyle.Render(fmt.Sprintf("%d package(s) found", len(results))))

	return nil
}

// printSearchResult prints a single search result in a formatted line.
func printSearchResult(r registry.SearchResult) {
	// Name column: left-aligned, padded.
	name := ui.HeaderStyle.Render(fmt.Sprintf("%-26s", r.Name))

	// Stars column.
	stars := ui.MutedStyle.Render(fmt.Sprintf("★ %-5d", r.Stars))

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

	// Show topics if present (excluding cos-package itself).
	topics := filterTopics(r.Topics)
	if len(topics) > 0 {
		topicStr := ui.MutedStyle.Render(fmt.Sprintf("    tags: %s", strings.Join(topics, ", ")))
		fmt.Printf("  %s\n", topicStr)
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

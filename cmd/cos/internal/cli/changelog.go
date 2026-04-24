package cli

import (
	"fmt"
	"strings"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/project"
	"luum-agent-os/cmd/cos/internal/ui"
)

var (
	changelogSince string
)

var changelogCmd = &cobra.Command{
	Use:   "changelog [package-name]",
	Short: "Show what changed since last release for packages",
	Long: `Show commit history since the last release for one or all packages.
Does NOT release — just shows the pending changes.

Examples:
  cos changelog                    Show changes for all packages with unreleased commits
  cos changelog ecosystem-tools    Show changes for a specific package (substring match)
  cos changelog --since v0.2.6     Show changes since a specific OS tag`,
	RunE: runChangelog,
}

func init() {
	changelogCmd.Flags().StringVar(&changelogSince, "since", "", "Show changes since a specific git tag (e.g. v0.2.6)")
	rootCmd.AddCommand(changelogCmd)
}

func runChangelog(cmd *cobra.Command, args []string) error {
	projectRoot := project.FindRootOrCwd()

	statuses, err := discoverPackages(projectRoot)
	if err != nil {
		return err
	}

	// Filter by package name argument if provided.
	nameFilter := ""
	if len(args) > 0 {
		nameFilter = args[0]
	}

	type pkgChangelog struct {
		Name    string
		Version string
		PkgDir  string
		LastTag string
		Commits []string
	}

	var entries []pkgChangelog
	for _, s := range statuses {
		if nameFilter != "" && !strings.Contains(s.Name, nameFilter) {
			continue
		}

		pkgDir, err := findPackageDir(projectRoot, s.Name)
		if err != nil {
			continue
		}

		var sinceTag string
		if changelogSince != "" {
			// Use the user-specified tag as the reference point.
			sinceTag = changelogSince
		} else {
			sinceTag = scopedTagName(s.Name, s.Version)
		}

		commits, _ := getPackageCommits(projectRoot, pkgDir, sinceTag)

		// When using --since, show all matching packages; otherwise only those with changes.
		if changelogSince == "" && len(commits) == 0 {
			continue
		}

		entries = append(entries, pkgChangelog{
			Name:    s.Name,
			Version: s.Version,
			PkgDir:  pkgDir,
			LastTag: sinceTag,
			Commits: commits,
		})
	}

	if len(entries) == 0 {
		if nameFilter != "" {
			fmt.Printf("No unreleased changes found for packages matching %q.\n", nameFilter)
		} else {
			fmt.Println("No packages with unreleased changes.")
		}
		return nil
	}

	fmt.Println()
	for _, e := range entries {
		commitCount := len(e.Commits)
		sinceInfo := ""
		if e.LastTag != "" {
			sinceInfo = fmt.Sprintf(" (since %s)", e.LastTag)
		}
		fmt.Printf("%s %s @ %s%s\n",
			ui.HeaderStyle.Render(e.Name),
			e.Version,
			fmt.Sprintf("%d commits", commitCount),
			sinceInfo,
		)
		if commitCount == 0 {
			fmt.Printf("  %s\n", ui.MutedStyle.Render("(no commits)"))
		} else {
			for _, c := range e.Commits {
				fmt.Printf("  %s %s\n", ui.IconBullet, c)
			}
		}
		fmt.Println()
	}

	return nil
}

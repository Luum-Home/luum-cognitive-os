package cli

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/manifest"
	"luum-agent-os/cmd/cos/internal/project"
	"luum-agent-os/cmd/cos/internal/ui"
)

var (
	statusJSON        bool
	statusChangedOnly bool
)

var statusCmd = &cobra.Command{
	Use:   "status",
	Short: "Show release status of all packages",
	Long: `Show the release status of all packages in the packages/ directory.

For each package, displays the version from cos-package.yaml, the latest
scoped git tag, and the number of commits since that tag.

Examples:
  cos status                Show status of all packages
  cos status --json         Output as JSON
  cos status --changed-only Show only packages with unreleased changes`,
	RunE: runStatus,
}

func init() {
	statusCmd.Flags().BoolVar(&statusJSON, "json", false, "Output as JSON")
	statusCmd.Flags().BoolVar(&statusChangedOnly, "changed-only", false, "Show only packages with unreleased changes")
	rootCmd.AddCommand(statusCmd)
}

// PackageStatus holds the release status of a single package.
type PackageStatus struct {
	Name       string `json:"name"`
	Version    string `json:"version"`
	LastTag    string `json:"last_tag"`
	Commits    int    `json:"commits_since_tag"`
	HasChanges bool   `json:"has_changes"`
}

// discoverPackages scans the packages/ directory under projectRoot and returns
// a sorted list of PackageStatus entries. This is shared between status and
// release-all commands.
func discoverPackages(projectRoot string) ([]PackageStatus, error) {
	packagesDir := filepath.Join(projectRoot, "packages")
	entries, err := os.ReadDir(packagesDir)
	if err != nil {
		return nil, fmt.Errorf("reading packages/ directory: %w", err)
	}

	var statuses []PackageStatus
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		manifestPath := filepath.Join(packagesDir, entry.Name(), "cos-package.yaml")
		m, err := manifest.ParseFile(manifestPath)
		if err != nil {
			// Skip directories without a valid cos-package.yaml.
			continue
		}

		tagName := scopedTagName(m.Name, m.Version)
		lastTag, commits := getTagStatus(projectRoot, tagName, filepath.Join("packages", entry.Name()))

		statuses = append(statuses, PackageStatus{
			Name:       m.Name,
			Version:    m.Version,
			LastTag:    lastTag,
			Commits:    commits,
			HasChanges: lastTag == "" || commits > 0,
		})
	}

	sort.Slice(statuses, func(i, j int) bool {
		return statuses[i].Name < statuses[j].Name
	})

	return statuses, nil
}

// getTagStatus checks for an exact scoped git tag matching the current version.
// If found, counts commits since that tag affecting the given path.
// Returns the tag name and commit count. If no tag exists, returns ("", 0).
func getTagStatus(projectRoot, expectedTag, pkgPath string) (string, int) {
	// Check if the exact version tag exists.
	if !gitTagExistsInDir(projectRoot, expectedTag) {
		return "", 0
	}

	// Count commits since the tag that touch this package's directory.
	countCmd := exec.Command("git", "rev-list", "--count", expectedTag+"..HEAD", "--", pkgPath)
	countCmd.Dir = projectRoot
	out, err := countCmd.Output()
	if err != nil {
		return expectedTag, 0
	}

	count := 0
	fmt.Sscanf(strings.TrimSpace(string(out)), "%d", &count)
	return expectedTag, count
}

// gitTagExistsInDir checks if a git tag exists, running from the given directory.
func gitTagExistsInDir(dir, tag string) bool {
	cmd := exec.Command("git", "tag", "-l", tag)
	cmd.Dir = dir
	output, err := cmd.Output()
	if err != nil {
		return false
	}
	return strings.TrimSpace(string(output)) == tag
}

func runStatus(cmd *cobra.Command, args []string) error {
	projectRoot := project.FindRootOrCwd()

	statuses, err := discoverPackages(projectRoot)
	if err != nil {
		return err
	}

	if len(statuses) == 0 {
		fmt.Println("No packages found in packages/")
		return nil
	}

	// Filter if --changed-only.
	if statusChangedOnly {
		var filtered []PackageStatus
		for _, s := range statuses {
			if s.HasChanges {
				filtered = append(filtered, s)
			}
		}
		statuses = filtered
	}

	if statusJSON {
		return printStatusJSON(statuses)
	}

	return printStatusTable(statuses)
}

func printStatusJSON(statuses []PackageStatus) error {
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	return enc.Encode(statuses)
}

func printStatusTable(statuses []PackageStatus) error {
	if len(statuses) == 0 {
		fmt.Println("No packages with unreleased changes.")
		return nil
	}

	// Calculate column widths.
	maxName := len("PACKAGE")
	maxVersion := len("VERSION")
	maxTag := len("LAST TAG")
	for _, s := range statuses {
		if len(s.Name) > maxName {
			maxName = len(s.Name)
		}
		if len(s.Version) > maxVersion {
			maxVersion = len(s.Version)
		}
		tagDisplay := s.LastTag
		if tagDisplay == "" {
			tagDisplay = "(never released)"
		}
		if len(tagDisplay) > maxTag {
			maxTag = len(tagDisplay)
		}
	}

	fmt.Println()
	// Header.
	header := fmt.Sprintf("  %-*s  %-*s  %-*s  %s",
		maxName, "PACKAGE",
		maxVersion, "VERSION",
		maxTag, "LAST TAG",
		"COMMITS",
	)
	fmt.Println(ui.HeaderStyle.Render(header))
	fmt.Println(strings.Repeat("-", len(header)+4))

	// Rows.
	changed := 0
	for _, s := range statuses {
		tagDisplay := s.LastTag
		if tagDisplay == "" {
			tagDisplay = "(never released)"
		}

		commitDisplay := fmt.Sprintf("%d", s.Commits)
		if s.LastTag == "" {
			commitDisplay = "-"
		}

		var statusIcon string
		if s.HasChanges {
			statusIcon = ui.WarningStyle.Render("*")
			changed++
		} else {
			statusIcon = " "
		}

		fmt.Printf("%s %-*s  %-*s  %-*s  %s\n",
			statusIcon,
			maxName, s.Name,
			maxVersion, s.Version,
			maxTag, tagDisplay,
			commitDisplay,
		)
	}

	fmt.Println()
	if changed > 0 {
		fmt.Printf("  %s %d of %d packages have unreleased changes\n", ui.IconWarning, changed, len(statuses))
	} else {
		fmt.Printf("  %s All %d packages are up to date\n", ui.IconSuccess, len(statuses))
	}

	return nil
}

package cli

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/lockfile"
	"luum-agent-os/cmd/cos/internal/project"
	"luum-agent-os/cmd/cos/internal/ui"
)

var (
	versionAll bool
)

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Show Cognitive OS and package versions",
	Long: `Show the OS core version and all installed package versions.

Examples:
  cos version           Show OS version
  cos version --all     Show OS + all installed packages`,
	RunE: runVersion,
}

func init() {
	versionCmd.Flags().BoolVar(&versionAll, "all", false, "Show all installed package versions")
	rootCmd.AddCommand(versionCmd)
}

// readVersionFile reads the VERSION file from the given project root.
// Returns the trimmed version string or "unknown" if not found.
func readVersionFile(projectRoot string) string {
	data, err := os.ReadFile(filepath.Join(projectRoot, "VERSION"))
	if err != nil {
		return "unknown"
	}
	return strings.TrimSpace(string(data))
}

func runVersion(cmd *cobra.Command, args []string) error {
	projectRoot := project.FindRootOrCwd()
	version := readVersionFile(projectRoot)

	fmt.Printf("\nCognitive OS v%s\n", version)

	if !versionAll {
		return nil
	}

	// Load lockfile to show installed packages.
	lf, err := lockfile.Load(projectRoot)
	if err != nil {
		fmt.Println()
		fmt.Println(ui.MutedStyle.Render("No packages installed"))
		return nil
	}

	if len(lf.Packages) == 0 {
		fmt.Println()
		fmt.Println(ui.MutedStyle.Render("No packages installed"))
		return nil
	}

	// Sort package names for stable output.
	names := make([]string, 0, len(lf.Packages))
	for name := range lf.Packages {
		names = append(names, name)
	}
	sort.Strings(names)

	// Calculate max name width for alignment.
	maxName := 0
	for _, name := range names {
		if len(name) > maxName {
			maxName = len(name)
		}
	}

	fmt.Println()
	fmt.Println(ui.HeaderStyle.Render("Installed packages:"))

	for _, name := range names {
		pkg := lf.Packages[name]
		padding := strings.Repeat(" ", maxName-len(name)+2)
		fmt.Printf("  %s%s%s\n",
			ui.HeaderStyle.Render(name),
			padding,
			pkg.Version,
		)
	}

	fmt.Printf("\n  %s\n",
		ui.MutedStyle.Render(fmt.Sprintf("%d packages installed", len(names))),
	)

	return nil
}

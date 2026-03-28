package cli

import (
	"fmt"
	"os"
	"sort"
	"strings"
	"time"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/lockfile"
	"luum-agent-os/cmd/cos/internal/project"
	"luum-agent-os/cmd/cos/internal/ui"
)

var listCmd = &cobra.Command{
	Use:   "list",
	Short: "List installed cos packages",
	Long:  "Show all packages installed via cos install.",
	RunE:  runList,
}

func init() {
	rootCmd.AddCommand(listCmd)
}

func runList(cmd *cobra.Command, args []string) error {
	// Find project root.
	cwd, err := os.Getwd()
	if err != nil {
		return fmt.Errorf("getting working directory: %w", err)
	}

	projectRoot, err := project.FindRoot(cwd)
	if err != nil {
		projectRoot = cwd
	}

	// Load lockfile.
	lf, err := lockfile.Load(projectRoot)
	if err != nil {
		return fmt.Errorf("loading lockfile: %w", err)
	}

	if len(lf.Packages) == 0 {
		fmt.Println()
		fmt.Println(ui.InfoStyle.Render(fmt.Sprintf("%s No packages installed", ui.IconInfo)))
		return nil
	}

	// Sort package names for stable output.
	names := make([]string, 0, len(lf.Packages))
	for name := range lf.Packages {
		names = append(names, name)
	}
	sort.Strings(names)

	// Calculate column widths for alignment.
	maxName, maxVer, maxLic := 0, 0, 0
	for _, name := range names {
		if len(name) > maxName {
			maxName = len(name)
		}
		pkg := lf.Packages[name]
		if len(pkg.Version) > maxVer {
			maxVer = len(pkg.Version)
		}
		if len(pkg.License) > maxLic {
			maxLic = len(pkg.License)
		}
	}

	fmt.Println()
	fmt.Println(ui.HeaderStyle.Render("Installed packages:"))
	fmt.Println()

	for _, name := range names {
		pkg := lf.Packages[name]

		exportCount := len(pkg.Exports)
		exportLabel := fmt.Sprintf("%d export", exportCount)
		if exportCount != 1 {
			exportLabel += "s"
		}

		installDate := formatInstallDate(pkg.InstalledAt)

		// Pad columns for alignment.
		paddedName := name + strings.Repeat(" ", maxName-len(name))
		paddedVer := pkg.Version + strings.Repeat(" ", maxVer-len(pkg.Version))
		paddedLic := pkg.License + strings.Repeat(" ", maxLic-len(pkg.License))

		fmt.Printf("  %s  %s  %s  %-12s  %s\n",
			ui.HeaderStyle.Render(paddedName),
			paddedVer,
			ui.MutedStyle.Render(paddedLic),
			exportLabel,
			ui.DimStyle.Render(installDate),
		)
	}

	fmt.Println()
	fmt.Printf("  %s\n", ui.MutedStyle.Render(fmt.Sprintf("%d package(s) installed", len(names))))

	return nil
}

// formatInstallDate parses an RFC3339 timestamp and returns a short date string.
func formatInstallDate(ts string) string {
	t, err := time.Parse(time.RFC3339, ts)
	if err != nil {
		return ts
	}
	return t.Format("2006-01-02")
}

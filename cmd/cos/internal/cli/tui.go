package cli

import (
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/project"
	tuisurface "luum-agent-os/cmd/cos/internal/tui"
)

var (
	tuiSnapshot bool
	tuiProject  string
)

var tuiCmd = &cobra.Command{
	Use:   "tui",
	Short: "Open the read-only Cognitive OS operator TUI",
	Long: `Open the read-only Cognitive OS Surface 5 operator console.

The first Bubble Tea TUI slice observes existing COS reports and daemon state.
It does not mutate repository state or run provider calls. Use --snapshot for a
non-interactive terminal summary suitable for scripts and smoke tests.`,
	Args: cobra.NoArgs,
	RunE: func(cmd *cobra.Command, args []string) error {
		root := tuiProject
		if root == "" {
			root = project.FindRootOrCwd()
		}
		if tuiSnapshot {
			fmt.Fprint(cmd.OutOrStdout(), tuisurface.SnapshotText(root))
			return nil
		}
		_, err := tea.NewProgram(tuisurface.NewModel(tuisurface.LoadSnapshot(root))).Run()
		return err
	},
}

func init() {
	tuiCmd.Flags().BoolVar(&tuiSnapshot, "snapshot", false, "Print a read-only TUI snapshot and exit")
	tuiCmd.Flags().StringVar(&tuiProject, "project-dir", os.Getenv("COGNITIVE_OS_PROJECT_DIR"), "Project root to inspect")
	rootCmd.AddCommand(tuiCmd)
}

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
	tuiSnapshot  bool
	tuiProject   string
	tuiOperate   string
	tuiConfirm   bool
	tuiJSON      bool
	tuiMessageID string
	tuiAckStatus string
	tuiNote      string
)

var tuiCmd = &cobra.Command{
	Use:   "tui",
	Short: "Open the read-only Cognitive OS operator TUI",
	Long: `Open the read-only Cognitive OS Surface 5 operator console.

The first Bubble Tea TUI slice observes existing COS reports and daemon state.
It starts in read-only mode. Use --snapshot for a non-interactive terminal
summary suitable for scripts and smoke tests. Operable actions are limited to an
allowlist and require --confirm before any command runs.`,
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
		if tuiOperate != "" {
			result := tuisurface.RunAction(root, tuiOperate, tuisurface.ActionOptions{
				Confirm:   tuiConfirm,
				MessageID: tuiMessageID,
				AckStatus: tuiAckStatus,
				Note:      tuiNote,
			})
			fmt.Fprint(cmd.OutOrStdout(), tuisurface.FormatActionResult(result, tuiJSON))
			if !result.OK {
				return fmt.Errorf("tui action %s %s: %s", result.Action, result.Outcome, result.Reason)
			}
			return nil
		}
		_, err := tea.NewProgram(tuisurface.NewModel(tuisurface.LoadSnapshot(root))).Run()
		return err
	},
}

func init() {
	tuiCmd.Flags().BoolVar(&tuiSnapshot, "snapshot", false, "Print a read-only TUI snapshot and exit")
	tuiCmd.Flags().StringVar(&tuiProject, "project-dir", os.Getenv("COGNITIVE_OS_PROJECT_DIR"), "Project root to inspect")
	tuiCmd.Flags().StringVar(&tuiOperate, "operate", "", "Run an allowlisted TUI action: refresh-coverage, cosd-process-once, inbox-ack")
	tuiCmd.Flags().BoolVar(&tuiConfirm, "confirm", false, "Confirm an operable TUI action")
	tuiCmd.Flags().BoolVar(&tuiJSON, "json", false, "Print operable action result as JSON")
	tuiCmd.Flags().StringVar(&tuiMessageID, "message-id", "", "Inbox message id for inbox-ack")
	tuiCmd.Flags().StringVar(&tuiAckStatus, "ack-status", "seen", "Inbox ack status for inbox-ack")
	tuiCmd.Flags().StringVar(&tuiNote, "note", "", "Operator note for inbox-ack")
	rootCmd.AddCommand(tuiCmd)
}

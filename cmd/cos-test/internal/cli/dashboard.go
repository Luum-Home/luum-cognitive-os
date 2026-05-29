package cli

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos-test/internal/config"
)

var dashboardCmd = &cobra.Command{
	Use:   "dashboard",
	Short: "Deprecated compatibility shim for the old interactive dashboard",
	Long: `Deprecated compatibility shim.

The old dashboard used a separate pytest execution path. ADR-073 makes
cos-test focused / cluster / broad the canonical runner surface, so dashboard
now proxies to "cos-test broad" instead of maintaining a separate executor.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		cfg := config.DefaultConfig()
		cfg.CIMode = true
		cfg.Verbose = verbose
		fmt.Fprintln(os.Stderr, "[cos-test dashboard] DEPRECATED: use 'cos-test broad' or 'cos-test cluster --lane <name>'; proxying to broad")
		return runBroad(cfg, false, false, false, false, false)
	},
}

func init() {
	rootCmd.AddCommand(dashboardCmd)
}

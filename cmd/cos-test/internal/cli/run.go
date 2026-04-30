package cli

import (
	"fmt"
	"os"
	"strings"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos-test/internal/config"
)

var (
	runUnit        bool
	runBehavior    bool
	runIntegration bool
	runSystem      bool
	runE2E         bool
	runDocker      bool
	runAll         bool
)

var runCmd = &cobra.Command{
	Use:   "run [filter]",
	Short: "Deprecated compatibility shim for focused/cluster/broad",
	Long: `Deprecated compatibility shim.

ADR-073 makes cos-test focused / cluster / broad the canonical test ladder.
This command now delegates to that ladder instead of maintaining a separate
pytest execution stack.

Examples:
  cos-test run              # proxies to cos-test broad
  cos-test run --unit       # proxies to cos-test cluster --lane unit
  cos-test run --behavior   # proxies to cos-test cluster --lane behavior`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if filter := strings.TrimSpace(strings.Join(args, " ")); filter != "" {
			return fmt.Errorf("cos-test run filters are deprecated; use 'cos-test focused --paths ...' or 'cos-test cluster --lane <name>'")
		}

		cfg := config.DefaultConfig()
		cfg.Verbose = verbose
		cfg.CIMode = ciMode

		fmt.Fprintln(os.Stderr, "[cos-test run] DEPRECATED: use 'cos-test focused', 'cos-test cluster', or 'cos-test broad'")
		if runDocker {
			fmt.Fprintln(os.Stderr, "[cos-test run] NOTE: --docker is deprecated here; lane policy is owned by .cognitive-os/test-lanes.yaml")
		}

		if runAll || !hasRunSelection() {
			return runBroad(cfg, false, false)
		}

		var firstErr error
		for _, cat := range selectedCategories() {
			lane := string(cat)
			if err := runCluster(cfg, lane, false); err != nil && firstErr == nil {
				firstErr = err
			}
		}
		return firstErr
	},
}

func init() {
	runCmd.Flags().BoolVar(&runUnit, "unit", false, "Run unit lane")
	runCmd.Flags().BoolVar(&runBehavior, "behavior", false, "Run behavior lane")
	runCmd.Flags().BoolVar(&runIntegration, "integration", false, "Run integration lane")
	runCmd.Flags().BoolVar(&runSystem, "system", false, "Run system lane")
	runCmd.Flags().BoolVar(&runE2E, "e2e", false, "Run e2e lane")
	runCmd.Flags().BoolVar(&runDocker, "docker", false, "Deprecated: lane policy now owns Docker selection")
	runCmd.Flags().BoolVar(&runAll, "all", false, "Run broad default lanes")

	rootCmd.AddCommand(runCmd)
}

func hasRunSelection() bool {
	return runUnit || runBehavior || runIntegration || runSystem || runE2E
}

func selectedCategories() []config.TestCategory {
	if runAll {
		return config.AllCategories()
	}

	var cats []config.TestCategory
	if runUnit {
		cats = append(cats, config.CategoryUnit)
	}
	if runBehavior {
		cats = append(cats, config.CategoryBehavior)
	}
	if runIntegration {
		cats = append(cats, config.CategoryIntegration)
	}
	if runSystem {
		cats = append(cats, config.CategorySystem)
	}
	if runE2E {
		cats = append(cats, config.CategoryE2E)
	}

	if len(cats) == 0 {
		cats = config.AllCategories()
	}
	return cats
}

package cli

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos-test/internal/banner"
	"luum-agent-os/cmd/cos-test/internal/config"
	"luum-agent-os/cmd/cos-test/internal/lanes"
	"luum-agent-os/cmd/cos-test/internal/runner"
)

var broadDryRun bool

var broadCmd = &cobra.Command{
	Use:   "broad",
	Short: "Run every lane in deterministic order (parallel-safe first).",
	Long: `Run every lane registered in .cognitive-os/test-lanes.yaml.

Lanes are ordered: parallel-safe (parallel=true) first, then marker lanes,
then serial (parallel=false). Within each group declaration order is
preserved. The exit code is non-zero if any lane fails; later lanes still
run so the operator gets a complete picture.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		cfg := config.DefaultConfig()
		cfg.CIMode = ciMode
		cfg.Verbose = verbose
		return runBroad(cfg, broadDryRun)
	},
}

func init() {
	broadCmd.Flags().BoolVar(&broadDryRun, "dry-run", false,
		"Print resolved plan, do not execute")
	rootCmd.AddCommand(broadCmd)
}

// laneOutcome captures one lane's run result.
type laneOutcome struct {
	Lane   string
	Failed bool
}

func runBroad(cfg *config.Config, dryRun bool) error {
	regPath := lanes.DefaultPath(cfg.ProjectRoot)
	reg, err := lanes.Load(regPath)
	if err != nil {
		return fmt.Errorf("load lane registry: %w", err)
	}

	order := reg.BroadOrder()
	pr := runner.NewPytestRunner(cfg)

	intro := banner.Render(banner.Info{
		Subcommand: "broad",
		Lane:       "all",
		Paths:      laneAllPaths(reg, order),
		TestCount:  -1,
		Workers:    "per-lane (mixed)",
		Reason:     fmt.Sprintf("running %d lanes: %s", len(order), strings.Join(order, ", ")),
		ETA:        banner.AggregateETA(filepath.Join(cfg.ProjectRoot, ".cognitive-os", "reports", "test-runs"), "broad", 5),
		KillSwitch: "COS_FORCE_SERIAL_LANES=*",
	})
	intro = strings.Replace(intro, "tests=-1", "tests=?", 1)
	fmt.Print(intro)
	fmt.Println()

	outcomes := make([]laneOutcome, 0, len(order))
	for _, name := range order {
		fmt.Printf("\n=== lane: %s ===\n", name)
		plan, err := buildClusterPlan(cfg, name)
		if err != nil {
			fmt.Fprintf(os.Stderr, "[cos-test broad] lane %s plan error: %v\n", name, err)
			outcomes = append(outcomes, laneOutcome{Lane: name, Failed: true})
			continue
		}
		bi := banner.Info{
			Subcommand: "broad",
			Lane:       name,
			Paths:      plan.Lane.Paths,
			TestCount:  -1,
			Workers:    plan.Workers,
			Reason:     plan.Reason,
			ETA:        banner.AggregateETA(filepath.Join(cfg.ProjectRoot, ".cognitive-os", "reports", "test-runs"), name, 5),
			KillSwitch: "COS_FORCE_SERIAL_LANES=" + name,
		}
		laneRendered := banner.Render(bi)
		laneRendered = strings.Replace(laneRendered, "tests=-1", "tests=?", 1)
		fmt.Print(laneRendered)
		for _, inv := range plan.Invokes {
			fmt.Printf("[cos-test broad] %s/%s: %s\n", name, inv.Label, strings.Join(pr.PytestArgs(inv.Args), " "))
		}
		if dryRun {
			outcomes = append(outcomes, laneOutcome{Lane: name, Failed: false})
			continue
		}
		failed := false
		for _, inv := range plan.Invokes {
			if err := pr.RawInvocation(inv.Args); err != nil {
				failed = true
			}
		}
		outcomes = append(outcomes, laneOutcome{Lane: name, Failed: failed})
	}

	fmt.Println()
	fmt.Println("[cos-test broad] === aggregated summary ===")
	failedCount := 0
	for _, o := range outcomes {
		status := "OK"
		if o.Failed {
			status = "FAIL"
			failedCount++
		}
		fmt.Printf("[cos-test broad]   %-14s %s\n", o.Lane, status)
	}
	fmt.Printf("[cos-test broad] %d/%d lanes failed\n", failedCount, len(outcomes))

	if dryRun {
		fmt.Println("[cos-test broad] dry-run: not executing")
		return nil
	}
	if failedCount > 0 {
		os.Exit(1)
	}
	return nil
}

func laneAllPaths(reg *lanes.Registry, order []string) []string {
	var out []string
	for _, n := range order {
		if l, ok := reg.Get(n); ok {
			out = append(out, l.Paths...)
		}
	}
	return out
}

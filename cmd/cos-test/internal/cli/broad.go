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

var (
	broadDryRun          bool
	broadIncludeOptional bool
)

var broadCmd = &cobra.Command{
	Use:   "broad",
	Short: "Run every lane in deterministic order (parallel-safe first).",
	Long: `Run every lane registered in .cognitive-os/test-lanes.yaml.

Lanes are ordered: parallel-safe (parallel=true) first, then marker lanes,
then serial (parallel=false). Within each group declaration order is
preserved. The exit code is non-zero if any lane fails; later lanes still
run so the operator gets a complete picture.

Optional lanes (arena, benchmark, quality) are EXCLUDED by default because
they are cost-bearing or non-deterministic. Include them explicitly with
--include-optional or run a single one via "cos-test cluster --lane <name>".`,
	RunE: func(cmd *cobra.Command, args []string) error {
		cfg := config.DefaultConfig()
		cfg.CIMode = ciMode
		cfg.Verbose = verbose
		return runBroad(cfg, broadDryRun, broadIncludeOptional)
	},
}

func init() {
	broadCmd.Flags().BoolVar(&broadDryRun, "dry-run", false,
		"Print resolved plan, do not execute")
	broadCmd.Flags().BoolVar(&broadIncludeOptional, "include-optional", false,
		"Include optional lanes (arena, benchmark, quality). Off by default.")
	rootCmd.AddCommand(broadCmd)
}

// laneOutcome captures one lane's run result.
type laneOutcome struct {
	Lane   string
	Failed bool
}

func runBroad(cfg *config.Config, dryRun, includeOptional bool) error {
	regPath := lanes.DefaultPath(cfg.ProjectRoot)
	reg, err := lanes.Load(regPath)
	if err != nil {
		return fmt.Errorf("load lane registry: %w", err)
	}

	order := reg.BroadOrderWith(includeOptional)
	pr := runner.NewPytestRunner(cfg)

	reason := fmt.Sprintf("running %d lanes: %s", len(order), strings.Join(order, ", "))
	if !includeOptional {
		if opt := reg.OptionalNames(); len(opt) > 0 {
			reason += fmt.Sprintf(" | skipping optional: %s (use --include-optional)", strings.Join(opt, ", "))
		}
	}

	intro := banner.Render(banner.Info{
		Subcommand: "broad",
		Lane:       "all",
		Paths:      laneAllPaths(reg, order),
		TestCount:  -1,
		Workers:    "per-lane (mixed)",
		Reason:     reason,
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
			opts := runner.InvocationOptions{Workers: inv.Workers, Lane: name}
			fmt.Printf("[cos-test broad] %s/%s: %s\n", name, inv.Label, strings.Join(pr.PytestArgsWithOptions(inv.Args, opts), " "))
		}
		if dryRun {
			outcomes = append(outcomes, laneOutcome{Lane: name, Failed: false})
			continue
		}
		failed := false
		for _, inv := range plan.Invokes {
			if err := pr.RawInvocationWithOptions(inv.Args, runner.InvocationOptions{Workers: inv.Workers, Lane: name}); err != nil {
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

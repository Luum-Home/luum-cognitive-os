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
	broadNoDocker        bool
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
--include-optional or run a single one via "cos-test cluster --lane <name>".

Use --no-docker for the official local/CI broad lane. It skips any lane whose
resource policy can require Docker so default validation never starts
testcontainers or compose stacks by surprise.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		cfg := config.DefaultConfig()
		cfg.CIMode = ciMode
		cfg.Verbose = verbose
		return runBroad(cfg, broadDryRun, broadIncludeOptional, broadNoDocker)
	},
}

func init() {
	broadCmd.Flags().BoolVar(&broadDryRun, "dry-run", false,
		"Print resolved plan, do not execute")
	broadCmd.Flags().BoolVar(&broadIncludeOptional, "include-optional", false,
		"Include optional lanes (arena, benchmark, quality). Off by default.")
	broadCmd.Flags().BoolVar(&broadNoDocker, "no-docker", false,
		"Skip lanes whose resource policy is not docker=forbidden")
	rootCmd.AddCommand(broadCmd)
}

// laneOutcome captures one lane's run result.
type laneOutcome struct {
	Lane    string
	Failed  bool
	Skipped bool
	Reason  string
}

func runBroad(cfg *config.Config, dryRun, includeOptional, noDocker bool) error {
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
	if noDocker {
		reason += " | skipping docker-capable lanes (--no-docker)"
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
		if shouldSkipForNoDocker(plan.Resources.DockerPolicy, noDocker) {
			fmt.Printf("[cos-test broad] %s: SKIP docker_policy=%s (--no-docker)\n", name, plan.Resources.DockerPolicy)
			outcomes = append(outcomes, laneOutcome{Lane: name, Skipped: true, Reason: "docker_policy=" + plan.Resources.DockerPolicy})
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
		fmt.Printf("[cos-test broad] %s/resources: %s\n", name, plan.Resources.Summary())
		for _, inv := range plan.Invokes {
			opts := invocationOptionsFor(plan, inv, name)
			fmt.Printf("[cos-test broad] %s/%s: %s\n", name, inv.Label, strings.Join(pr.PytestArgsWithOptions(inv.Args, opts), " "))
		}
		if dryRun {
			outcomes = append(outcomes, laneOutcome{Lane: name, Failed: false})
			continue
		}
		failed := false
		fmt.Printf("[cos-test broad] %s/resources: %s\n", name, plan.Resources.Summary())
		if err := enforceResourcePolicy(plan.Resources); err != nil {
			if len(plan.Invokes) > 0 {
				_ = pr.WriteResourceOutcome(invocationOptionsFor(plan, plan.Invokes[0], name), "blocked_policy")
			}
			fmt.Fprintf(os.Stderr, "[cos-test broad] lane %s resource policy block: %v\n", name, err)
			outcomes = append(outcomes, laneOutcome{Lane: name, Skipped: true, Reason: err.Error()})
			continue
		}
		for _, inv := range plan.Invokes {
			if err := pr.RawInvocationWithOptions(inv.Args, invocationOptionsFor(plan, inv, name)); err != nil {
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
		if o.Skipped {
			status = "SKIP"
		} else if o.Failed {
			status = "FAIL"
			failedCount++
		}
		if o.Reason != "" {
			fmt.Printf("[cos-test broad]   %-14s %s (%s)\n", o.Lane, status, o.Reason)
		} else {
			fmt.Printf("[cos-test broad]   %-14s %s\n", o.Lane, status)
		}
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

func shouldSkipForNoDocker(dockerPolicy string, noDocker bool) bool {
	return noDocker && dockerPolicy != "forbidden"
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

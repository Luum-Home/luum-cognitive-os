package cli

import (
	"encoding/json"
	"fmt"
	"io"
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
	broadJSON            bool
	broadStrict          bool
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
		return runBroad(cfg, broadDryRun, broadIncludeOptional, broadNoDocker, broadJSON, broadStrict)
	},
}

func init() {
	broadCmd.Flags().BoolVar(&broadDryRun, "dry-run", false,
		"Print resolved plan, do not execute")
	broadCmd.Flags().BoolVar(&broadIncludeOptional, "include-optional", false,
		"Include optional lanes (arena, benchmark, quality). Off by default.")
	broadCmd.Flags().BoolVar(&broadNoDocker, "no-docker", false,
		"Skip lanes whose resource policy is not docker=forbidden")
	broadCmd.Flags().BoolVar(&broadJSON, "json", false,
		"Emit a machine-readable classification summary at the end")
	broadCmd.Flags().BoolVar(&broadStrict, "strict", false,
		"Treat warn/skip_if_unavailable lane failures as blocking failures")
	rootCmd.AddCommand(broadCmd)
}

// laneOutcome captures one lane's run result.
type laneOutcome struct {
	Lane          string              `json:"lane"`
	Failed        bool                `json:"failed"`
	Skipped       bool                `json:"skipped"`
	Reason        string              `json:"reason,omitempty"`
	GateClass     lanes.GateClass     `json:"gate_class"`
	FailurePolicy lanes.FailurePolicy `json:"failure_policy"`
}

type broadClassSummary struct {
	Total   int `json:"total"`
	Failed  int `json:"failed"`
	Skipped int `json:"skipped"`
}

type broadSummary struct {
	SchemaVersion    string                                `json:"schema_version"`
	Strict           bool                                  `json:"strict"`
	BlockingFailures int                                   `json:"blocking_failures"`
	OutcomeCount     int                                   `json:"outcome_count"`
	Classes          map[lanes.GateClass]broadClassSummary `json:"classes"`
	Outcomes         []laneOutcome                         `json:"outcomes"`
}

func runBroad(cfg *config.Config, dryRun, includeOptional, noDocker, emitJSON, strict bool) error {
	logOut := io.Writer(os.Stdout)
	if emitJSON {
		logOut = os.Stderr
	}
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
	fmt.Fprint(logOut, intro)
	fmt.Fprintln(logOut)

	outcomes := make([]laneOutcome, 0, len(order))
	for _, name := range order {
		fmt.Fprintf(logOut, "\n=== lane: %s ===\n", name)
		lane, _ := reg.Get(name)
		baseOutcome := laneOutcome{Lane: name, GateClass: lane.Class(), FailurePolicy: lane.Policy()}
		plan, err := buildClusterPlan(cfg, name)
		if err != nil {
			fmt.Fprintf(os.Stderr, "[cos-test broad] lane %s plan error: %v\n", name, err)
			baseOutcome.Failed = true
			baseOutcome.Reason = err.Error()
			outcomes = append(outcomes, baseOutcome)
			continue
		}
		if shouldSkipForNoDocker(plan.Resources.DockerPolicy, noDocker) {
			fmt.Fprintf(logOut, "[cos-test broad] %s: SKIP docker_policy=%s (--no-docker)\n", name, plan.Resources.DockerPolicy)
			baseOutcome.Skipped = true
			baseOutcome.Reason = "docker_policy=" + plan.Resources.DockerPolicy
			outcomes = append(outcomes, baseOutcome)
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
		fmt.Fprint(logOut, laneRendered)
		fmt.Fprintf(logOut, "[cos-test broad] %s/resources: %s\n", name, plan.Resources.Summary())
		for _, inv := range plan.Invokes {
			opts := invocationOptionsFor(plan, inv, name)
			fmt.Fprintf(logOut, "[cos-test broad] %s/%s: %s\n", name, inv.Label, strings.Join(pr.PytestArgsWithOptions(inv.Args, opts), " "))
		}
		if dryRun {
			outcomes = append(outcomes, baseOutcome)
			continue
		}
		failed := false
		fmt.Fprintf(logOut, "[cos-test broad] %s/resources: %s\n", name, plan.Resources.Summary())
		if err := enforceResourcePolicy(plan.Resources); err != nil {
			if len(plan.Invokes) > 0 {
				_ = pr.WriteResourceOutcome(invocationOptionsFor(plan, plan.Invokes[0], name), "blocked_policy")
			}
			fmt.Fprintf(os.Stderr, "[cos-test broad] lane %s resource policy block: %v\n", name, err)
			baseOutcome.Skipped = true
			baseOutcome.Reason = err.Error()
			outcomes = append(outcomes, baseOutcome)
			continue
		}
		for _, inv := range plan.Invokes {
			if err := pr.RawInvocationWithOptions(inv.Args, invocationOptionsFor(plan, inv, name)); err != nil {
				failed = true
			}
		}
		baseOutcome.Failed = failed
		outcomes = append(outcomes, baseOutcome)
	}

	summary := buildBroadSummary(outcomes, strict)
	printBroadSummary(logOut, summary)
	if emitJSON {
		payload, err := json.MarshalIndent(summary, "", "  ")
		if err != nil {
			return fmt.Errorf("marshal broad summary: %w", err)
		}
		fmt.Println(string(payload))
	}

	if dryRun {
		fmt.Fprintln(logOut, "[cos-test broad] dry-run: not executing")
		return nil
	}
	if summary.BlockingFailures > 0 {
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

func buildBroadSummary(outcomes []laneOutcome, strict bool) broadSummary {
	classTotals := map[lanes.GateClass]int{}
	classFailures := map[lanes.GateClass]int{}
	classSkipped := map[lanes.GateClass]int{}
	blockingFailures := 0
	for _, o := range outcomes {
		classTotals[o.GateClass]++
		if o.Skipped {
			classSkipped[o.GateClass]++
		} else if o.Failed {
			classFailures[o.GateClass]++
			if strict || o.FailurePolicy == lanes.FailureBlock {
				blockingFailures++
			}
		}
	}
	classes := map[lanes.GateClass]broadClassSummary{}
	for _, class := range []lanes.GateClass{lanes.GateReleaseBlocking, lanes.GateEnvironmental, lanes.GateCostBearing, lanes.GateDiagnostic} {
		if classTotals[class] == 0 {
			continue
		}
		classes[class] = broadClassSummary{Total: classTotals[class], Failed: classFailures[class], Skipped: classSkipped[class]}
	}
	return broadSummary{
		SchemaVersion:    "cos-test-broad-summary/v1",
		Strict:           strict,
		BlockingFailures: blockingFailures,
		OutcomeCount:     len(outcomes),
		Classes:          classes,
		Outcomes:         outcomes,
	}
}

func printBroadSummary(out io.Writer, summary broadSummary) {
	fmt.Fprintln(out)
	fmt.Fprintln(out, "[cos-test broad] === aggregated summary ===")
	for _, o := range summary.Outcomes {
		status := "OK"
		if o.Skipped {
			status = "SKIP"
		} else if o.Failed {
			status = "FAIL"
		}
		if o.Reason != "" {
			fmt.Fprintf(out, "[cos-test broad]   %-24s %-4s class=%s policy=%s (%s)\n", o.Lane, status, o.GateClass, o.FailurePolicy, o.Reason)
		} else {
			fmt.Fprintf(out, "[cos-test broad]   %-24s %-4s class=%s policy=%s\n", o.Lane, status, o.GateClass, o.FailurePolicy)
		}
	}
	for _, class := range []lanes.GateClass{lanes.GateReleaseBlocking, lanes.GateEnvironmental, lanes.GateCostBearing, lanes.GateDiagnostic} {
		classSummary, ok := summary.Classes[class]
		if !ok {
			continue
		}
		fmt.Fprintf(out, "[cos-test broad] class %-16s total=%d failed=%d skipped=%d\n", class, classSummary.Total, classSummary.Failed, classSummary.Skipped)
	}
	label := "release-blocking"
	if summary.Strict {
		label = "strict-blocking"
	}
	fmt.Fprintf(out, "[cos-test broad] %d/%d %s lanes failed\n", summary.BlockingFailures, summary.OutcomeCount, label)
}

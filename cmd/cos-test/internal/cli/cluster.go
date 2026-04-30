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
	clusterLane   string
	clusterDryRun bool
)

var clusterCmd = &cobra.Command{
	Use:   "cluster",
	Short: "Run a single test lane (per .cognitive-os/test-lanes.yaml).",
	Long: `Run a single test lane.

The lane name must match an entry in .cognitive-os/test-lanes.yaml. The
parallelism mode is taken from the registry:
  parallel: true    -> pytest -n auto
  parallel: false   -> serial pytest
  parallel: marker  -> two invocations: -m "not <marker>" -n auto, then -m
                       "<marker>" serial. Final exit code is the worst of the
                       two.

Examples:
  cos-test cluster --lane unit
  cos-test cluster --lane integration --dry-run`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if strings.TrimSpace(clusterLane) == "" {
			return fmt.Errorf("--lane is required")
		}
		cfg := config.DefaultConfig()
		cfg.CIMode = ciMode
		cfg.Verbose = verbose
		return runCluster(cfg, clusterLane, clusterDryRun)
	},
}

func init() {
	clusterCmd.Flags().StringVar(&clusterLane, "lane", "",
		"Lane name from .cognitive-os/test-lanes.yaml (required)")
	clusterCmd.Flags().BoolVar(&clusterDryRun, "dry-run", false,
		"Print resolved plan, do not execute")
	rootCmd.AddCommand(clusterCmd)
}

// clusterPlan is one or two pytest invocations to run for a lane.
type clusterPlan struct {
	Lane    lanes.Lane
	Workers string // "auto:n", "serial", "split (marker)"
	Reason  string
	Invokes []invokeSpec // one entry for parallel:true|false, two for marker
}

type invokeSpec struct {
	Args  []string // pytest args (positional + flags)
	Label string   // human label, e.g. "parallel" / "serial" / "marker:not docker"
}

func runCluster(cfg *config.Config, laneName string, dryRun bool) error {
	plan, err := buildClusterPlan(cfg, laneName)
	if err != nil {
		return err
	}

	pr := runner.NewPytestRunner(cfg)

	info := banner.Info{
		Subcommand: "cluster",
		Lane:       laneName,
		Paths:      plan.Lane.Paths,
		TestCount:  -1, // unknown without collection; banner will print -1
		Workers:    plan.Workers,
		Reason:     plan.Reason,
		ETA:        banner.AggregateETA(filepath.Join(cfg.ProjectRoot, ".cognitive-os", "reports", "test-runs"), laneName, 5),
		KillSwitch: "COS_FORCE_SERIAL_LANES=" + laneName,
	}
	// We don't know counts without collection; render -1 -> "?"
	rendered := banner.Render(info)
	rendered = strings.Replace(rendered, "tests=-1", "tests=?", 1)
	fmt.Print(rendered)
	fmt.Println()

	for _, inv := range plan.Invokes {
		fmt.Printf("[cos-test cluster] %s: %s\n", inv.Label, strings.Join(pr.PytestArgs(inv.Args), " "))
	}

	if dryRun {
		fmt.Println("[cos-test cluster] dry-run: not executing")
		return nil
	}

	worst := 0
	for _, inv := range plan.Invokes {
		if err := pr.RawInvocation(inv.Args); err != nil {
			worst = 1
		}
	}
	if worst != 0 {
		os.Exit(worst)
	}
	return nil
}

// buildClusterPlan resolves a lane to one or two pytest invocations.
func buildClusterPlan(cfg *config.Config, laneName string) (*clusterPlan, error) {
	regPath := lanes.DefaultPath(cfg.ProjectRoot)
	reg, err := lanes.Load(regPath)
	if err != nil {
		return nil, fmt.Errorf("load lane registry: %w", err)
	}
	lane, ok := reg.Get(laneName)
	if !ok {
		return nil, fmt.Errorf("unknown lane %q (known: %s)", laneName, strings.Join(reg.Names(), ", "))
	}
	if len(lane.Paths) == 0 {
		return nil, fmt.Errorf("lane %q has no paths configured", laneName)
	}

	plan := &clusterPlan{Lane: lane}
	// excludeFilter returns the "-m" args to apply the lane's MarkerExclude,
	// if any, optionally combined with an existing "not X" expression.
	withExclude := func(existingNot string) []string {
		if lane.MarkerExclude == "" {
			if existingNot == "" {
				return nil
			}
			return []string{"-m", "not " + existingNot}
		}
		if existingNot == "" {
			return []string{"-m", "not " + lane.MarkerExclude}
		}
		return []string{"-m", fmt.Sprintf("not %s and not %s", existingNot, lane.MarkerExclude)}
	}

	switch lane.Parallel {
	case lanes.ParallelTrue:
		plan.Workers = "auto:n (parallel-safe per registry)"
		plan.Reason = "lane parallel=true"
		if lane.MarkerExclude != "" {
			plan.Reason += fmt.Sprintf(" (excluding -m %q)", lane.MarkerExclude)
		}
		args := append([]string{}, lane.Paths...)
		args = append(args, withExclude("")...)
		args = append(args, "-n", "auto")
		plan.Invokes = []invokeSpec{{Args: args, Label: "parallel"}}
	case lanes.ParallelFalse:
		plan.Workers = "serial (stateful)"
		reason := lane.StatefulReason
		if reason == "" {
			reason = "lane parallel=false"
		}
		if lane.MarkerExclude != "" {
			reason += fmt.Sprintf(" (excluding -m %q)", lane.MarkerExclude)
		}
		plan.Reason = reason
		args := append([]string{}, lane.Paths...)
		args = append(args, withExclude("")...)
		plan.Invokes = []invokeSpec{{Args: args, Label: "serial"}}
	case lanes.ParallelMarker:
		marker := lane.MarkerSerial
		if marker == "" {
			return nil, fmt.Errorf("lane %q is parallel:marker but marker_serial is empty", laneName)
		}
		plan.Workers = "split (marker:" + marker + ")"
		plan.Reason = fmt.Sprintf("parallel-safe except marker %q (run serial)", marker)
		if lane.MarkerExclude != "" {
			plan.Reason += fmt.Sprintf(" + excluding -m %q", lane.MarkerExclude)
		}
		parallelArgs := append([]string{}, lane.Paths...)
		parallelArgs = append(parallelArgs, withExclude(marker)...)
		parallelArgs = append(parallelArgs, "-n", "auto")
		serialArgs := append([]string{}, lane.Paths...)
		if lane.MarkerExclude != "" {
			serialArgs = append(serialArgs, "-m", fmt.Sprintf("%s and not %s", marker, lane.MarkerExclude))
		} else {
			serialArgs = append(serialArgs, "-m", marker)
		}
		plan.Invokes = []invokeSpec{
			{Args: parallelArgs, Label: "marker:not " + marker},
			{Args: serialArgs, Label: "marker:" + marker},
		}
	default:
		return nil, fmt.Errorf("lane %q: unknown parallel mode %q", laneName, lane.Parallel)
	}
	return plan, nil
}

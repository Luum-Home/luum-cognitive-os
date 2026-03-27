package cli

import (
	"fmt"
	"os"
	"os/exec"
	"strings"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/ui"
)

var (
	perfBottlenecks bool
	perfOverhead    bool
	perfComponent   string
	perfExport      string
)

var perfCmd = &cobra.Command{
	Use:   "perf",
	Short: "Show Cognitive OS performance dashboard",
	Long: `Show performance metrics: latency, throughput, overhead, bottlenecks, and component health.

Examples:
  cos perf                    Show performance dashboard
  cos perf --bottlenecks      Show top 5 slowest components
  cos perf --overhead         Show hook/safety mesh overhead
  cos perf --component <name> Show health of specific component
  cos perf --export json      Export metrics as JSON`,
	RunE: runPerf,
}

func init() {
	perfCmd.Flags().BoolVar(&perfBottlenecks, "bottlenecks", false, "Show top 5 slowest components")
	perfCmd.Flags().BoolVar(&perfOverhead, "overhead", false, "Show hook/safety mesh overhead")
	perfCmd.Flags().StringVar(&perfComponent, "component", "", "Show health of specific component")
	perfCmd.Flags().StringVar(&perfExport, "export", "", "Export format (json)")
	rootCmd.AddCommand(perfCmd)
}

func runPerfPython(projectRoot string, pyCode string) (string, error) {
	script := fmt.Sprintf(
		"import sys; sys.path.insert(0, '%s'); "+
			"from lib.performance_monitor import PerformanceMonitor; "+
			"import json, os; "+
			"metrics_path = os.path.join('%s', '.cognitive-os', 'metrics', 'performance.jsonl'); "+
			"monitor = PerformanceMonitor(metrics_path); "+
			// Load existing JSONL into session metrics for analysis
			"_load_from_jsonl(monitor, metrics_path); "+
			"%s",
		projectRoot, projectRoot, pyCode,
	)

	// Wrap with a helper to load JSONL data
	fullScript := fmt.Sprintf(
		"import sys, json, os\n"+
			"sys.path.insert(0, '%s')\n"+
			"from lib.performance_monitor import PerformanceMonitor, PerformanceMetric\n"+
			"\n"+
			"def _load_from_jsonl(monitor, path):\n"+
			"    if not os.path.exists(path):\n"+
			"        return\n"+
			"    with open(path, 'r') as f:\n"+
			"        for line in f:\n"+
			"            line = line.strip()\n"+
			"            if not line:\n"+
			"                continue\n"+
			"            try:\n"+
			"                d = json.loads(line)\n"+
			"                m = PerformanceMetric(\n"+
			"                    component=d.get('component', ''),\n"+
			"                    operation=d.get('operation', ''),\n"+
			"                    duration_ms=d.get('duration_ms', 0),\n"+
			"                    success=d.get('success', True),\n"+
			"                    timestamp=d.get('timestamp', ''),\n"+
			"                    metadata=d.get('metadata', {}),\n"+
			"                )\n"+
			"                monitor._session_metrics.append(m)\n"+
			"            except (json.JSONDecodeError, KeyError):\n"+
			"                continue\n"+
			"\n"+
			"metrics_path = os.path.join('%s', '.cognitive-os', 'metrics', 'performance.jsonl')\n"+
			"monitor = PerformanceMonitor(metrics_path)\n"+
			"_load_from_jsonl(monitor, metrics_path)\n"+
			"%s\n",
		projectRoot, projectRoot, pyCode,
	)

	// Use script via stdin to avoid shell escaping issues
	_ = script // unused, using fullScript instead

	cmd := exec.Command("python3", "-c", fullScript)
	cmd.Dir = projectRoot
	cmd.Env = append(os.Environ(), fmt.Sprintf("PYTHONPATH=%s", projectRoot))

	output, err := cmd.CombinedOutput()
	if err != nil {
		return "", fmt.Errorf("python execution failed: %w\nOutput: %s", err, string(output))
	}
	return strings.TrimSpace(string(output)), nil
}

func runPerf(cmd *cobra.Command, args []string) error {
	projectRoot, err := findProjectRoot()
	if err != nil {
		return err
	}

	// Check if metrics file exists
	metricsFile := fmt.Sprintf("%s/.cognitive-os/metrics/performance.jsonl", projectRoot)
	if _, err := os.Stat(metricsFile); os.IsNotExist(err) {
		fmt.Println(ui.WarningStyle.Render(fmt.Sprintf("%s No performance data found", ui.IconWarning)))
		fmt.Println()
		fmt.Println("  Performance metrics are recorded automatically when hooks use")
		fmt.Println("  the timing wrapper from hooks/_lib/timing.sh.")
		fmt.Println()
		fmt.Printf("  Expected file: %s\n", metricsFile)
		return nil
	}

	var pyCode string

	switch {
	case perfBottlenecks:
		pyCode = `
bottlenecks = monitor.get_bottlenecks(top_n=5)
if not bottlenecks:
    print("No bottleneck data available.")
else:
    print("Top 5 Slowest Components")
    print("=" * 60)
    for i, b in enumerate(bottlenecks, 1):
        print(f"  {i}. {b['component']}")
        print(f"     avg: {b['avg_ms']:.1f}ms  p99: {b['p99_ms']:.1f}ms  calls: {b['call_count']}")
        if b['suggestion']:
            print(f"     -> {b['suggestion']}")
        print()
`

	case perfOverhead:
		pyCode = `
oh = monitor.get_overhead_report()
print("Hook & Safety Mesh Overhead")
print("=" * 60)
print(f"  Total hook overhead:    {oh['total_hook_overhead_ms']:.1f}ms")
print(f"  Safety mesh overhead:   {oh['safety_mesh_overhead_ms']:.1f}ms")
print(f"  % of session time:      {oh['pct_of_session_time']:.1f}%")
print()
if oh['hooks_breakdown']:
    print("  Hook Breakdown:")
    sorted_hooks = sorted(oh['hooks_breakdown'].items(), key=lambda x: -x[1])
    for name, ms in sorted_hooks[:10]:
        print(f"    {name}: {ms:.1f}ms")
`

	case perfComponent != "":
		pyCode = fmt.Sprintf(`
health = monitor.get_component_health('%s')
print("Component Health: %s")
print("=" * 60)
print(f"  Status:       {health['status']}")
print(f"  Avg latency:  {health['avg_latency_ms']:.1f}ms")
print(f"  Error rate:   {health['error_rate']:.1%%}")
print(f"  Last success: {health['last_success'] or 'N/A'}")
if health['suggestion']:
    print(f"  Suggestion:   {health['suggestion']}")
`, perfComponent, perfComponent)

	case perfExport == "json":
		pyCode = `
import json
report = {
    "efficiency": monitor.get_efficiency_score(),
    "overhead": monitor.get_overhead_report(),
    "throughput": monitor.get_throughput(),
    "bottlenecks": monitor.get_bottlenecks(),
}
print(json.dumps(report, indent=2))
`

	default:
		// Full dashboard
		pyCode = "print(monitor.format_dashboard())"
	}

	output, err := runPerfPython(projectRoot, pyCode)
	if err != nil {
		fmt.Fprintf(os.Stderr, "%s Failed to generate performance report: %v\n",
			ui.ErrorStyle.Render(ui.IconCross), err)
		return err
	}

	fmt.Println(output)
	return nil
}

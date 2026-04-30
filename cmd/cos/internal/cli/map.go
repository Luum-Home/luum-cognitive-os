package cli

import (
	"fmt"
	"os"
	"os/exec"
	"strings"

	"luum-agent-os/cmd/cos/internal/project"

	"github.com/spf13/cobra"
)

var (
	mapAffected string
	mapFull     bool
	mapOrphans  bool
	mapHotspots bool
	mapJSON     bool
)

var mapCmd = &cobra.Command{
	Use:   "map [primitive]",
	Short: "Show the system knowledge graph",
	Long: `Show dependency trees and relationships between Cognitive OS agentic primitives.

Examples:
  cos map trust-score          Show dependency tree for one agentic primitive
  cos map --affected hooks/trust-score-validator.sh
                               Show what breaks if this file changes
  cos map --full               Full system summary
  cos map --orphans            Show disconnected agentic primitives
  cos map --hotspots           Show most-connected agentic primitives (risk)
  cos map --json               Export as JSON to stdout`,
	RunE: runMap,
}

func init() {
	mapCmd.Flags().StringVar(&mapAffected, "affected", "", "Show what breaks if this file changes")
	mapCmd.Flags().BoolVar(&mapFull, "full", false, "Full system summary")
	mapCmd.Flags().BoolVar(&mapOrphans, "orphans", false, "Show disconnected agentic primitives")
	mapCmd.Flags().BoolVar(&mapHotspots, "hotspots", false, "Show most-connected agentic primitives (risk)")
	mapCmd.Flags().BoolVar(&mapJSON, "json", false, "Export as JSON")
	rootCmd.AddCommand(mapCmd)
}

// findProjectRoot walks up from cwd looking for Cognitive OS markers.
// Delegates to the shared project.FindRoot; falls back to cwd on failure.
func findProjectRoot() (string, error) {
	return project.FindRootOrCwd(), nil
}

func runPython(projectRoot string, args ...string) (string, error) {
	// Build the Python command to run
	pythonScript := fmt.Sprintf(
		"import sys; sys.path.insert(0, '%s'); from lib.system_graph import *; ",
		projectRoot,
	)
	pythonScript += strings.Join(args, "; ")

	cmd := exec.Command("python3", "-c", pythonScript)
	cmd.Dir = projectRoot
	cmd.Env = append(os.Environ(), fmt.Sprintf("PYTHONPATH=%s", projectRoot))

	output, err := cmd.CombinedOutput()
	if err != nil {
		return "", fmt.Errorf("python execution failed: %w\nOutput: %s", err, string(output))
	}
	return string(output), nil
}

func runMap(cmd *cobra.Command, args []string) error {
	projectRoot, err := findProjectRoot()
	if err != nil {
		return err
	}

	// Determine which subcommand to run
	var pyCommand string

	switch {
	case mapAffected != "":
		pyCommand = fmt.Sprintf(
			"g = build_graph('%s'); affected = get_affected_components(g, '%s')\n"+
				"if affected:\n"+
				"    print(f'Affected agentic primitives ({len(affected)}):')\n"+
				"    for a in affected:\n"+
				"        comp = g.components.get(a)\n"+
				"        layer = comp.layer.name if comp else '?'\n"+
				"        print(f'  - {a} ({layer})')\n"+
				"else:\n"+
				"    print(f'No agentic primitives found matching \\'%s\\'')",
			projectRoot, mapAffected, mapAffected,
		)

	case mapFull:
		pyCommand = fmt.Sprintf(
			"g = build_graph('%s'); print(format_full_graph_summary(g))",
			projectRoot,
		)

	case mapOrphans:
		pyCommand = fmt.Sprintf(
			"g = build_graph('%s'); orphans = find_orphans(g)\n"+
				"if orphans:\n"+
				"    print(f'Orphan agentic primitives ({len(orphans)}):')\n"+
				"    for o in orphans:\n"+
				"        print(f'  - {o.name} ({o.layer.name}) @ {o.path}')\n"+
				"else:\n"+
				"    print('No orphan agentic primitives found.')",
			projectRoot,
		)

	case mapHotspots:
		pyCommand = fmt.Sprintf(
			"g = build_graph('%s'); hotspots = find_hotspots(g)\n"+
				"if hotspots:\n"+
				"    print(f'Hotspot agentic primitives ({len(hotspots)}):')\n"+
				"    for name, count, risk in hotspots:\n"+
				"        print(f'  - {name}: {count} edges [{risk}]')\n"+
				"else:\n"+
				"    print('No hotspots found (all agentic primitives have <5 edges).')",
			projectRoot,
		)

	case mapJSON:
		pyCommand = fmt.Sprintf(
			"import json; g = build_graph('%s'); "+
				"nodes = [{'id': n, 'path': c.path, 'layer': c.layer.value, 'layer_name': c.layer.name, 'lines': c.lines} for n, c in g.components.items()]; "+
				"edges = [{'source': e.source, 'target': e.target, 'relation': e.relation.value, 'evidence': e.evidence} for e in g.edges]; "+
				"print(json.dumps({'nodes': nodes, 'edges': edges, 'summary': {'total_components': len(nodes), 'total_edges': len(edges)}}, indent=2))",
			projectRoot,
		)

	default:
		// Single agentic primitive tree
		if len(args) == 0 {
			fmt.Fprintln(os.Stderr, "Error: provide an agentic primitive name or use --full, --orphans, --hotspots, --affected, --json")
			return fmt.Errorf("no agentic primitive specified")
		}
		component := args[0]
		pyCommand = fmt.Sprintf(
			"g = build_graph('%s'); print(format_dependency_tree(g, '%s'))",
			projectRoot, component,
		)
	}

	output, err := runPython(projectRoot, pyCommand)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: failed to run system graph: %v\n", err)
		return err
	}

	fmt.Print(output)
	return nil
}

package cli

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos-test/internal/banner"
	"luum-agent-os/cmd/cos-test/internal/config"
	"luum-agent-os/cmd/cos-test/internal/runner"
)

// gitDiffFn returns the union of changed file paths used by focused mode.
// Injectable for unit tests.
var gitDiffFn = defaultGitDiff

var (
	focusedDryRun   bool
	focusedPathsArg []string
)

var focusedCmd = &cobra.Command{
	Use:   "focused [paths...]",
	Short: "Run only tests affected by the current diff (or explicit paths).",
	Long: `Run only the tests affected by the current diff.

Default mode: derives changed files from git (merge-base..HEAD ∪ uncommitted ∪
staged), maps them to test files via same-name heuristic, and runs those tests
with -n auto. If a pytest-testmon DB exists at
.cognitive-os/cache/testmon/.testmondata, testmon is preferred. If no matches
are found and testmon is unavailable, falls back to "pytest --lf --ff -x".

Examples:
  cos-test focused                       # diff-driven
  cos-test focused tests/unit/test_x.py  # explicit
  cos-test focused --dry-run             # print resolved plan, no execute`,
	RunE: func(cmd *cobra.Command, args []string) error {
		cfg := config.DefaultConfig()
		cfg.CIMode = ciMode
		cfg.Verbose = verbose
		explicit := append([]string(nil), focusedPathsArg...)
		explicit = append(explicit, args...)
		return runFocused(cfg, explicit, focusedDryRun)
	},
}

func init() {
	focusedCmd.Flags().BoolVar(&focusedDryRun, "dry-run", false,
		"Print resolved test list and pytest command, do not execute")
	focusedCmd.Flags().StringSliceVar(&focusedPathsArg, "paths", nil,
		"Override git-diff with explicit paths (repeatable / comma-separated)")
	rootCmd.AddCommand(focusedCmd)
}

// focusedPlan is the resolved invocation strategy.
type focusedPlan struct {
	Mode      string   // "explicit" | "testmon" | "mapped" | "fallback"
	TestPaths []string // pytest positional args (paths or nodeids)
	ExtraArgs []string // -n auto, -m, --testmon, --lf, etc.
	Reason    string
}

func runFocused(cfg *config.Config, explicit []string, dryRun bool) error {
	plan, err := buildFocusedPlan(cfg, explicit, gitDiffFn)
	if err != nil {
		return err
	}

	args := append([]string{}, plan.TestPaths...)
	args = append(args, plan.ExtraArgs...)
	pr := runner.NewPytestRunner(cfg)
	cmdLine := strings.Join(pr.PytestArgs(args), " ")

	info := banner.Info{
		Subcommand: "focused",
		Lane:       "auto",
		Paths:      plan.TestPaths,
		TestCount:  len(plan.TestPaths),
		Workers:    "auto:n (parallel-safe)",
		Reason:     plan.Reason,
		ETA:        banner.AggregateETA(filepath.Join(cfg.ProjectRoot, ".cognitive-os", "reports", "test-runs"), "focused", 5),
		KillSwitch: "COS_FORCE_SERIAL_LANES=focused",
	}
	banner.Print(os.Stdout, info)
	fmt.Println()
	fmt.Printf("[cos-test focused] mode=%s\n", plan.Mode)
	fmt.Printf("[cos-test focused] cmd: %s\n", cmdLine)

	if dryRun {
		fmt.Println("[cos-test focused] dry-run: not executing")
		return nil
	}

	return pr.RawInvocation(args)
}

// buildFocusedPlan resolves the strategy: explicit > testmon > mapped >
// fallback. The diffFn is injectable for tests.
func buildFocusedPlan(cfg *config.Config, explicit []string, diffFn func(projectRoot string) ([]string, error)) (*focusedPlan, error) {
	plan := &focusedPlan{ExtraArgs: []string{"-n", "auto"}}

	if len(explicit) > 0 {
		plan.Mode = "explicit"
		plan.Reason = "explicit paths supplied via args/--paths"
		plan.TestPaths = uniqueSorted(explicit)
		return plan, nil
	}

	changed, err := diffFn(cfg.ProjectRoot)
	if err != nil {
		// Soft-fail to fallback when git diff is unusable.
		plan.Mode = "fallback"
		plan.Reason = fmt.Sprintf("git diff unusable (%v); using --lf --ff -x", err)
		plan.ExtraArgs = []string{"--lf", "--ff", "-x"}
		return plan, nil
	}

	mapped := mapChangedToTests(cfg, changed)

	testmonDB := filepath.Join(cfg.ProjectRoot, ".cognitive-os", "cache", "testmon", ".testmondata")
	if _, err := os.Stat(testmonDB); err == nil {
		plan.Mode = "testmon"
		plan.Reason = fmt.Sprintf("testmon DB present (%s)", testmonDB)
		plan.ExtraArgs = []string{"-n", "auto", "--testmon"}
		// Testmon decides selection itself; pass mapped as additional context only.
		plan.TestPaths = mapped
		return plan, nil
	}

	if len(mapped) == 0 {
		plan.Mode = "fallback"
		plan.Reason = "no diff matches and no testmon DB; using --lf --ff -x"
		plan.ExtraArgs = []string{"--lf", "--ff", "-x"}
		return plan, nil
	}

	plan.Mode = "mapped"
	plan.Reason = fmt.Sprintf("same-name mapping resolved %d test paths from %d changed files", len(mapped), len(changed))
	plan.TestPaths = mapped
	return plan, nil
}

// mapChangedToTests turns a list of repo-relative changed paths into a
// deduped, sorted list of test files. Rules:
//   - test files (path under tests/ matching test_*.py or *_test.py) are kept
//     verbatim
//   - source files map to tests/*/test_<basename>.py and tests/*/test_<basename>_*.py
func mapChangedToTests(cfg *config.Config, changed []string) []string {
	if len(changed) == 0 {
		return nil
	}
	seen := map[string]struct{}{}
	out := []string{}

	add := func(p string) {
		if _, ok := seen[p]; ok {
			return
		}
		seen[p] = struct{}{}
		out = append(out, p)
	}

	for _, rel := range changed {
		if rel == "" {
			continue
		}
		if isTestFile(rel) {
			abs := filepath.Join(cfg.ProjectRoot, rel)
			if _, err := os.Stat(abs); err == nil {
				add(rel)
			}
			continue
		}
		// Map source file -> candidate tests
		base := strings.TrimSuffix(filepath.Base(rel), filepath.Ext(rel))
		if base == "" {
			continue
		}
		candidates := findTestFilesForBase(cfg.TestsDir, base)
		for _, c := range candidates {
			rel2, err := filepath.Rel(cfg.ProjectRoot, c)
			if err != nil {
				continue
			}
			add(rel2)
		}
	}
	sort.Strings(out)
	return out
}

// isTestFile reports whether rel looks like a pytest test file.
func isTestFile(rel string) bool {
	if !strings.HasSuffix(rel, ".py") {
		return false
	}
	base := filepath.Base(rel)
	if !strings.HasPrefix(base, "test_") && !strings.HasSuffix(base, "_test.py") {
		return false
	}
	parts := strings.Split(filepath.ToSlash(rel), "/")
	for _, p := range parts {
		if p == "tests" {
			return true
		}
	}
	return false
}

// findTestFilesForBase walks testsDir for `test_<base>.py` and
// `test_<base>_*.py`. Returns absolute paths.
func findTestFilesForBase(testsDir, base string) []string {
	var hits []string
	exact := "test_" + base + ".py"
	prefix := "test_" + base + "_"
	_ = filepath.Walk(testsDir, func(path string, info os.FileInfo, err error) error {
		if err != nil || info == nil || info.IsDir() {
			return nil
		}
		name := filepath.Base(path)
		if name == exact {
			hits = append(hits, path)
			return nil
		}
		if strings.HasPrefix(name, prefix) && strings.HasSuffix(name, ".py") {
			hits = append(hits, path)
		}
		return nil
	})
	return hits
}

func uniqueSorted(xs []string) []string {
	seen := map[string]struct{}{}
	out := []string{}
	for _, x := range xs {
		if x == "" {
			continue
		}
		if _, ok := seen[x]; ok {
			continue
		}
		seen[x] = struct{}{}
		out = append(out, x)
	}
	sort.Strings(out)
	return out
}

// defaultGitDiff returns the union of:
//   - committed-on-branch:       git diff --name-only $(git merge-base origin/main HEAD)..HEAD
//   - uncommitted (working tree): git diff --name-only
//   - staged:                    git diff --name-only --cached
//
// On any subcommand failure the diff source is silently dropped (focused mode
// degrades gracefully to whichever sources work).
func defaultGitDiff(projectRoot string) ([]string, error) {
	seen := map[string]struct{}{}
	out := []string{}

	collect := func(args ...string) {
		cmd := exec.Command("git", args...)
		cmd.Dir = projectRoot
		var stdout, stderr bytes.Buffer
		cmd.Stdout = &stdout
		cmd.Stderr = &stderr
		if err := cmd.Run(); err != nil {
			return
		}
		for _, line := range strings.Split(stdout.String(), "\n") {
			line = strings.TrimSpace(line)
			if line == "" {
				continue
			}
			if _, ok := seen[line]; ok {
				continue
			}
			seen[line] = struct{}{}
			out = append(out, line)
		}
	}

	// Determine merge base (silently fall back to "HEAD~1" if origin/main is missing).
	mb := mergeBase(projectRoot, "origin/main", "HEAD")
	if mb != "" {
		collect("diff", "--name-only", mb+"..HEAD")
	}
	collect("diff", "--name-only")
	collect("diff", "--name-only", "--cached")

	if len(out) == 0 {
		return nil, fmt.Errorf("git diff produced no files (working tree may be clean)")
	}
	sort.Strings(out)
	return out, nil
}

func mergeBase(projectRoot, a, b string) string {
	cmd := exec.Command("git", "merge-base", a, b)
	cmd.Dir = projectRoot
	var stdout bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &bytes.Buffer{}
	if err := cmd.Run(); err != nil {
		return ""
	}
	return strings.TrimSpace(stdout.String())
}

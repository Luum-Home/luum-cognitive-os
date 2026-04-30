package cli

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/fsnotify/fsnotify"
	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos-test/internal/config"
	"luum-agent-os/cmd/cos-test/internal/ui"
)

var watchCmd = &cobra.Command{
	Use:   "watch",
	Short: "Watch for file changes and rerun relevant tests",
	Long: `Watch for file changes and rerun relevant tests.

Monitors hooks/, skills/, and hooks/_lib/ for changes.
When a file changes, determines which tests are affected and reruns them.

Press Ctrl+C to stop watching.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		cfg := config.DefaultConfig()
		cfg.Verbose = verbose
		return runWatch(cfg)
	},
}

func init() {
	rootCmd.AddCommand(watchCmd)
}

func runWatch(cfg *config.Config) error {
	ui.Title("Cognitive OS Test Watcher")
	ui.Separator()

	watcher, err := fsnotify.NewWatcher()
	if err != nil {
		return fmt.Errorf("failed to create watcher: %w", err)
	}
	defer watcher.Close()

	// Add watch paths recursively.
	watchCount := 0
	for _, dir := range cfg.WatchPaths {
		if _, err := os.Stat(dir); os.IsNotExist(err) {
			ui.Warn(fmt.Sprintf("Watch path does not exist: %s", dir)).Print()
			continue
		}
		err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return nil
			}
			if info.IsDir() {
				if strings.HasPrefix(info.Name(), ".") || info.Name() == "__pycache__" {
					return filepath.SkipDir
				}
				if addErr := watcher.Add(path); addErr != nil {
					return nil
				}
				watchCount++
			}
			return nil
		})
		if err != nil {
			ui.Warn(fmt.Sprintf("Error walking %s: %v", dir, err)).Print()
		}
	}

	// Also watch tests directory.
	if err := addTestDirs(watcher, cfg); err != nil {
		ui.Warn(fmt.Sprintf("Error watching test dirs: %v", err)).Print()
	}

	ui.Info(fmt.Sprintf("Watching %d directories for changes...", watchCount)).Print()
	ui.Info("Press Ctrl+C to stop").Print()
	fmt.Println()

	// Debounce timer.
	var debounceTimer *time.Timer
	debounceInterval := 500 * time.Millisecond

	for {
		select {
		case event, ok := <-watcher.Events:
			if !ok {
				return nil
			}

			// Only react to write/create events on Python files.
			if !isRelevantChange(event) {
				continue
			}

			// Debounce: reset timer on each event.
			if debounceTimer != nil {
				debounceTimer.Stop()
			}

			changedFile := event.Name
			debounceTimer = time.AfterFunc(debounceInterval, func() {
				runAffectedTests(cfg, changedFile)
			})

		case err, ok := <-watcher.Errors:
			if !ok {
				return nil
			}
			ui.Error(fmt.Sprintf("Watcher error: %v", err)).Print()
		}
	}
}

func addTestDirs(watcher *fsnotify.Watcher, cfg *config.Config) error {
	for _, cat := range config.AllCategories() {
		dir := cfg.TestDir(cat)
		if _, err := os.Stat(dir); err == nil {
			if err := watcher.Add(dir); err != nil {
				return err
			}
		}
	}
	return nil
}

func isRelevantChange(event fsnotify.Event) bool {
	if event.Op&(fsnotify.Write|fsnotify.Create) == 0 {
		return false
	}
	name := filepath.Base(event.Name)
	if strings.HasSuffix(name, ".py") {
		return true
	}
	return false
}

func runAffectedTests(cfg *config.Config, changedFile string) {
	ui.Separator()
	ui.Info(fmt.Sprintf("Change detected: %s", filepath.Base(changedFile))).Print()

	relPath, err := filepath.Rel(cfg.ProjectRoot, changedFile)
	if err != nil {
		relPath = changedFile
	}

	ui.Progress("Running focused test plan...").Print()
	if err := runFocusedWithOptions(cfg, nil, focusedRunOptions{
		UseTestmon:   false,
		ChangedFiles: []string{relPath},
	}); err != nil {
		ui.Error("Focused test run failed").WithDetails(err.Error()).Print()
	}
	fmt.Println()
	ui.Info("Watching for changes...").Print()
}

// mapFileToTests determines which tests to run based on the changed file path.
func mapFileToTests(cfg *config.Config, changedFile string) (string, []config.TestCategory) {
	relPath, err := filepath.Rel(cfg.ProjectRoot, changedFile)
	if err != nil {
		return "", config.AllCategories()
	}

	parts := strings.Split(relPath, string(filepath.Separator))
	if len(parts) == 0 {
		return "", config.AllCategories()
	}

	switch {
	case parts[0] == "hooks" && len(parts) > 1 && parts[1] == "_lib":
		// hooks/_lib change -> run unit tests.
		moduleName := strings.TrimSuffix(filepath.Base(changedFile), ".py")
		return moduleName, []config.TestCategory{config.CategoryUnit}

	case parts[0] == "hooks":
		// Hook change -> run system tests matching the hook name.
		hookName := strings.TrimSuffix(filepath.Base(changedFile), filepath.Ext(filepath.Base(changedFile)))
		return hookName, []config.TestCategory{config.CategorySystem, config.CategoryBehavior}

	case parts[0] == "skills":
		// Skill change -> run integration and behavior tests.
		if len(parts) > 1 {
			return parts[1], []config.TestCategory{config.CategoryIntegration, config.CategoryBehavior}
		}
		return "", []config.TestCategory{config.CategoryIntegration}

	case parts[0] == "tests":
		// Test file changed -> run that specific test file.
		return filepath.Base(changedFile), nil
	}

	return "", config.AllCategories()
}

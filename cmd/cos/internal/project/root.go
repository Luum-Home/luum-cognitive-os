package project

import (
	"fmt"
	"os"
	"path/filepath"
)

// markers are filenames and directories that indicate a Cognitive OS project root.
var markers = []string{
	"cognitive-os.yaml",
	".claude",
	"rules",
}

// FindRoot walks up from the given directory looking for Cognitive OS markers.
// Returns the project root path or an error if not found.
func FindRoot(startDir string) (string, error) {
	dir := startDir
	for {
		for _, marker := range markers {
			if _, err := os.Stat(filepath.Join(dir, marker)); err == nil {
				return dir, nil
			}
		}

		parent := filepath.Dir(dir)
		if parent == dir {
			// Reached filesystem root without finding a marker.
			return "", fmt.Errorf("no Cognitive OS project found (looked for %v from %s)", markers, startDir)
		}
		dir = parent
	}
}

// FindRootOrCwd returns the project root discovered by FindRoot starting from
// the current working directory, or falls back to the cwd itself when no
// marker is found.
func FindRootOrCwd() string {
	cwd, err := os.Getwd()
	if err != nil {
		return "."
	}

	root, err := FindRoot(cwd)
	if err != nil {
		return cwd
	}
	return root
}

package runner

import (
	"bufio"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"luum-agent-os/cmd/cos-test/internal/config"
)

// TestFile represents a discovered test file.
type TestFile struct {
	Path     string
	Category config.TestCategory
	Markers  []string
	Name     string
}

// DiscoveryResult holds the result of test discovery.
type DiscoveryResult struct {
	Files      []TestFile
	ByCategory map[config.TestCategory][]TestFile
	TotalFiles int
}

var markerRegex = regexp.MustCompile(`@pytest\.mark\.(\w+)`)

// DiscoverTests walks the test directories and discovers test files and markers.
func DiscoverTests(cfg *config.Config) (*DiscoveryResult, error) {
	result := &DiscoveryResult{
		ByCategory: make(map[config.TestCategory][]TestFile),
	}

	categories := cfg.Categories
	if len(categories) == 0 {
		categories = config.AllCategories()
	}

	for _, cat := range categories {
		dir := cfg.TestDir(cat)
		if _, err := os.Stat(dir); os.IsNotExist(err) {
			continue
		}

		err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return nil // skip errors
			}
			if info.IsDir() {
				return nil
			}
			if !strings.HasPrefix(info.Name(), "test_") || !strings.HasSuffix(info.Name(), ".py") {
				return nil
			}

			tf := TestFile{
				Path:     path,
				Category: cat,
				Name:     info.Name(),
			}

			markers, _ := extractMarkers(path)
			tf.Markers = markers

			result.Files = append(result.Files, tf)
			result.ByCategory[cat] = append(result.ByCategory[cat], tf)
			return nil
		})
		if err != nil {
			return nil, err
		}
	}

	result.TotalFiles = len(result.Files)
	return result, nil
}

// extractMarkers reads a Python file and extracts pytest markers.
func extractMarkers(path string) ([]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	var markers []string
	seen := make(map[string]bool)
	scanner := bufio.NewScanner(f)

	for scanner.Scan() {
		line := scanner.Text()
		matches := markerRegex.FindAllStringSubmatch(line, -1)
		for _, m := range matches {
			if len(m) > 1 && !seen[m[1]] {
				markers = append(markers, m[1])
				seen[m[1]] = true
			}
		}
	}

	return markers, scanner.Err()
}

// CountSourceFiles counts Python source files in a directory.
func CountSourceFiles(dir string) int {
	count := 0
	_ = filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() {
			return nil
		}
		if strings.HasSuffix(info.Name(), ".py") && !strings.HasPrefix(info.Name(), "__") {
			count++
		}
		return nil
	})
	return count
}

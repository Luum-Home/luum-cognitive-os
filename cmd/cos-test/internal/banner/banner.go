// Package banner renders the 5-line "[cos-test ...]" banner used by the
// focused/cluster/broad subcommands and provides a best-effort ETA aggregator
// over historical run inventories.
package banner

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

// Info bundles all data shown in the banner.
type Info struct {
	Subcommand string // "focused", "cluster", "broad"
	Lane       string // lane name (or "auto" / "broad")
	Paths      []string
	TestCount  int
	Workers    string // "auto:8 (parallel-safe per registry)" / "serial (stateful)" / "split (marker)"
	Reason     string // worker mode rationale
	ETA        string // "~18s (p50 of last 10 audit runs, +/- 4s)" or "unknown (no history)"
	KillSwitch string // "COS_FORCE_SERIAL_LANES=audit"
}

// Render returns the 5-line banner as a single string (newline-terminated).
// Format mirrors design §9.
func Render(info Info) string {
	prefix := fmt.Sprintf("[cos-test %s]", info.Subcommand)
	pathStr := strings.Join(info.Paths, ",")
	if pathStr == "" {
		pathStr = "(none)"
	}
	lane := info.Lane
	if lane == "" {
		lane = "(unset)"
	}
	reason := info.Reason
	if reason == "" {
		reason = "default policy"
	}
	eta := info.ETA
	if eta == "" {
		eta = "unknown (no history)"
	}
	ks := info.KillSwitch
	if ks == "" {
		ks = "(none)"
	}

	var b strings.Builder
	fmt.Fprintf(&b, "%s lane=%s  tests=%d  workers=%s\n",
		prefix, lane, info.TestCount, info.Workers)
	fmt.Fprintf(&b, "%s paths: %s\n", prefix, pathStr)
	fmt.Fprintf(&b, "%s eta: %s\n", prefix, eta)
	fmt.Fprintf(&b, "%s kill-switch: %s\n", prefix, ks)
	fmt.Fprintf(&b, "%s reason: %s\n", prefix, reason)
	return b.String()
}

// Print writes Render(info) to w (or os.Stdout if w == nil).
func Print(w io.Writer, info Info) {
	if w == nil {
		w = os.Stdout
	}
	_, _ = io.WriteString(w, Render(info))
}

// FormatETA turns a slice of historical durations (seconds) into the ETA string
// shown in the banner. p50 is the median; the +/- spread is (p75-p25)/2 rounded.
// Returns "unknown (no history)" if durations is empty.
func FormatETA(lane string, durations []float64) string {
	if len(durations) == 0 {
		return "unknown (no history)"
	}
	sorted := make([]float64, len(durations))
	copy(sorted, durations)
	sort.Float64s(sorted)
	p50 := percentile(sorted, 50)
	p25 := percentile(sorted, 25)
	p75 := percentile(sorted, 75)
	spread := (p75 - p25) / 2
	if spread < 0 {
		spread = -spread
	}
	return fmt.Sprintf("~%ds (p50 of last %d %s runs, +/- %ds)",
		int(p50+0.5), len(durations), lane, int(spread+0.5))
}

// AggregateETA reads up to maxRuns most-recent run directories under
// reportsDir, attributes them to a lane by scanning the directory name and
// metadata.txt args= line, and returns FormatETA(lane, durations).
//
// Duration is best-effort: file-mtime-max minus dir-mtime. If a directory has
// no usable timing, it is skipped. If the reportsDir is missing, returns the
// unknown sentinel.
func AggregateETA(reportsDir, lane string, maxRuns int) string {
	dirs, err := recentRunDirs(reportsDir, maxRuns*4) // overscan; many dirs may not match lane
	if err != nil {
		return "unknown (no history)"
	}
	durations := make([]float64, 0, maxRuns)
	for _, d := range dirs {
		if !runMatchesLane(d, lane) {
			continue
		}
		if dur, ok := durationFromRunDir(d); ok {
			durations = append(durations, dur)
		}
		if len(durations) >= maxRuns {
			break
		}
	}
	return FormatETA(lane, durations)
}

// percentile returns the linear-interpolated percentile p (0..100) from a
// pre-sorted slice. Empty slice returns 0.
func percentile(sorted []float64, p float64) float64 {
	n := len(sorted)
	if n == 0 {
		return 0
	}
	if n == 1 {
		return sorted[0]
	}
	rank := (p / 100) * float64(n-1)
	lo := int(rank)
	hi := lo + 1
	if hi >= n {
		return sorted[n-1]
	}
	frac := rank - float64(lo)
	return sorted[lo] + frac*(sorted[hi]-sorted[lo])
}

// recentRunDirs returns the most-recent run directories (by name desc).
func recentRunDirs(reportsDir string, limit int) ([]string, error) {
	entries, err := os.ReadDir(reportsDir)
	if err != nil {
		return nil, err
	}
	names := make([]string, 0, len(entries))
	for _, e := range entries {
		if e.IsDir() {
			names = append(names, e.Name())
		}
	}
	sort.Sort(sort.Reverse(sort.StringSlice(names)))
	if len(names) > limit {
		names = names[:limit]
	}
	full := make([]string, len(names))
	for i, n := range names {
		full[i] = filepath.Join(reportsDir, n)
	}
	return full, nil
}

// runMatchesLane heuristically attributes a run dir to a lane. Matches if the
// lane name appears as a path component slug in the dir basename, or in the
// "args=" line of metadata.txt as a `tests/<lane>/` segment.
func runMatchesLane(dirPath, lane string) bool {
	base := filepath.Base(dirPath)
	if strings.Contains(base, "-tests-"+lane+"-") || strings.HasSuffix(base, "-tests-"+lane) {
		return true
	}
	mdPath := filepath.Join(dirPath, "metadata.txt")
	data, err := os.ReadFile(mdPath)
	if err != nil {
		return false
	}
	needle := "tests/" + lane
	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(line, "args=") && strings.Contains(line, needle) {
			return true
		}
	}
	return false
}

// durationFromRunDir approximates wall time as (max-mtime among files) -
// (dir mtime). Returns ok=false if non-positive or unreadable.
func durationFromRunDir(dirPath string) (float64, bool) {
	dirInfo, err := os.Stat(dirPath)
	if err != nil {
		return 0, false
	}
	dirMtime := dirInfo.ModTime()
	var maxMtime time.Time
	entries, err := os.ReadDir(dirPath)
	if err != nil {
		return 0, false
	}
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		fi, err := e.Info()
		if err != nil {
			continue
		}
		if fi.ModTime().After(maxMtime) {
			maxMtime = fi.ModTime()
		}
	}
	if maxMtime.IsZero() {
		return 0, false
	}
	dur := maxMtime.Sub(dirMtime).Seconds()
	if dur <= 0 {
		return 0, false
	}
	return dur, true
}

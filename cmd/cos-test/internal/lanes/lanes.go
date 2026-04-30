// Package lanes parses the .cognitive-os/test-lanes.yaml registry without an
// external YAML dependency. The schema is intentionally narrow (paths,
// parallel, marker_serial, stateful_reason) and the parser fails closed on
// anything it does not recognize.
package lanes

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

// ParallelMode describes how a lane's tests may be parallelized.
type ParallelMode string

const (
	ParallelTrue   ParallelMode = "true"
	ParallelFalse  ParallelMode = "false"
	ParallelMarker ParallelMode = "marker"
)

// Lane is one entry in test-lanes.yaml.
type Lane struct {
	Name           string
	Paths          []string
	Parallel       ParallelMode
	MarkerSerial   string
	StatefulReason string
	// Optional lanes are excluded from BroadOrder() by default. They are still
	// runnable explicitly via `cos-test cluster --lane <name>` or by passing
	// includeOptional=true to BroadOrderWith. Used for cost-bearing or
	// non-deterministic lanes (arena, benchmark, quality).
	Optional bool
	// MarkerExclude is a pytest marker expression applied as `-m "not <expr>"`
	// when running the lane. Used to exclude flake-prone or opt-in tests
	// (e.g. unit lane excludes 'benchmark' so perf-budget tests don't run
	// under the default -n auto path). Empty = no filter.
	MarkerExclude string
	// MarkerInclude is a pytest marker expression applied as `-m "<expr>"`.
	// It is used for explicit sublanes such as integration-docker where the
	// same directory is split by marker without making bash own selection.
	MarkerInclude string
}

// Registry holds the parsed lane registry.
type Registry struct {
	Order []string // declaration order (for deterministic broad runs)
	Lanes map[string]Lane
}

// DefaultPath returns the conventional lane registry path inside projectRoot.
func DefaultPath(projectRoot string) string {
	return filepath.Join(projectRoot, ".cognitive-os", "test-lanes.yaml")
}

// Get returns the lane by name and whether it exists.
func (r *Registry) Get(name string) (Lane, bool) {
	if r == nil {
		return Lane{}, false
	}
	l, ok := r.Lanes[name]
	return l, ok
}

// Names returns the lane names in declaration order.
func (r *Registry) Names() []string {
	if r == nil {
		return nil
	}
	out := make([]string, len(r.Order))
	copy(out, r.Order)
	return out
}

// BroadOrder returns the default broad-run order, EXCLUDING optional lanes.
// Use BroadOrderWith(true) to include them.
func (r *Registry) BroadOrder() []string {
	return r.BroadOrderWith(false)
}

// BroadOrderWith returns the broad-run order: parallel-safe lanes first
// (parallel == true), then marker lanes, then serial. Within each group,
// declaration order is preserved. When includeOptional is false, lanes
// marked optional: true are excluded — they are runnable explicitly via
// `cos-test cluster --lane <name>` but never on the default broad sweep.
func (r *Registry) BroadOrderWith(includeOptional bool) []string {
	if r == nil {
		return nil
	}
	var safe, marker, serial []string
	for _, name := range r.Order {
		l := r.Lanes[name]
		if l.Optional && !includeOptional {
			continue
		}
		switch l.Parallel {
		case ParallelTrue:
			safe = append(safe, name)
		case ParallelMarker:
			marker = append(marker, name)
		default:
			serial = append(serial, name)
		}
	}
	out := make([]string, 0, len(safe)+len(marker)+len(serial))
	out = append(out, safe...)
	out = append(out, marker...)
	out = append(out, serial...)
	return out
}

// OptionalNames returns optional lane names in declaration order. Useful for
// banner output ("not running: arena, benchmark, quality (optional)").
func (r *Registry) OptionalNames() []string {
	if r == nil {
		return nil
	}
	var out []string
	for _, name := range r.Order {
		if r.Lanes[name].Optional {
			out = append(out, name)
		}
	}
	return out
}

// Load reads and parses the lane registry from path.
func Load(path string) (*Registry, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open lane registry %s: %w", path, err)
	}
	defer f.Close()
	return Parse(f)
}

// Parse parses YAML-flavored content from a reader. The accepted dialect is:
//
//	lanes:
//	  <name>:
//	    paths: [a, b]
//	    parallel: true|false|marker
//	    marker_serial: <name>
//	    stateful_reason: "<text>"
//	    optional: true|false
//	    marker_include: <pytest marker expression>
//
// All other top-level keys are ignored. Indentation is two-space significant.
// optional: true excludes the lane from BroadOrder() default — it is still
// runnable via cluster --lane <name> or BroadOrderWith(true).
func Parse(r io.Reader) (*Registry, error) {
	scanner := bufio.NewScanner(r)
	scanner.Buffer(make([]byte, 64*1024), 1024*1024)

	reg := &Registry{Lanes: map[string]Lane{}}
	inLanes := false
	var current *Lane
	var currentName string

	flush := func() {
		if current != nil {
			current.Name = currentName
			reg.Lanes[currentName] = *current
			reg.Order = append(reg.Order, currentName)
		}
		current = nil
		currentName = ""
	}

	for scanner.Scan() {
		raw := scanner.Text()
		// Strip trailing comments.
		if i := strings.Index(raw, "#"); i >= 0 {
			raw = raw[:i]
		}
		line := strings.TrimRight(raw, " \t")
		if strings.TrimSpace(line) == "" {
			continue
		}

		// Top-level: `lanes:` opens the lanes block; any other unindented key
		// closes it.
		if !strings.HasPrefix(line, " ") {
			flush()
			inLanes = strings.HasPrefix(strings.TrimSpace(line), "lanes:")
			continue
		}
		if !inLanes {
			continue
		}

		indent := countLeadingSpaces(line)
		body := strings.TrimSpace(line)

		switch indent {
		case 2:
			// New lane: "<name>:"
			flush()
			name := strings.TrimSuffix(body, ":")
			if name == "" || strings.Contains(name, ":") {
				return nil, fmt.Errorf("invalid lane header: %q", line)
			}
			current = &Lane{Name: name}
			currentName = name
		case 4:
			if current == nil {
				return nil, fmt.Errorf("lane field outside lane block: %q", line)
			}
			key, value, ok := splitKV(body)
			if !ok {
				return nil, fmt.Errorf("malformed lane field: %q", line)
			}
			switch key {
			case "paths":
				paths, err := parseInlineList(value)
				if err != nil {
					return nil, fmt.Errorf("lane %s paths: %w", currentName, err)
				}
				current.Paths = paths
			case "parallel":
				v := strings.Trim(value, `"' `)
				switch v {
				case "true":
					current.Parallel = ParallelTrue
				case "false":
					current.Parallel = ParallelFalse
				case "marker":
					current.Parallel = ParallelMarker
				default:
					return nil, fmt.Errorf("lane %s parallel: unknown value %q", currentName, v)
				}
			case "marker_serial":
				current.MarkerSerial = strings.Trim(value, `"' `)
			case "stateful_reason":
				current.StatefulReason = strings.Trim(value, `"' `)
			case "optional":
				v := strings.Trim(value, `"' `)
				switch v {
				case "true":
					current.Optional = true
				case "false", "":
					current.Optional = false
				default:
					return nil, fmt.Errorf("lane %s optional: expected true|false, got %q", currentName, v)
				}
			case "marker_exclude":
				current.MarkerExclude = strings.Trim(value, `"' `)
			case "marker_include":
				current.MarkerInclude = strings.Trim(value, `"' `)
			default:
				// Unknown keys are accepted (forward compat) but ignored.
			}
		default:
			// Deeper indentation not supported in current schema; tolerate.
		}
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	flush()

	if len(reg.Order) == 0 {
		return nil, fmt.Errorf("no lanes parsed")
	}
	return reg, nil
}

func countLeadingSpaces(s string) int {
	n := 0
	for _, c := range s {
		if c == ' ' {
			n++
		} else {
			break
		}
	}
	return n
}

func splitKV(s string) (string, string, bool) {
	i := strings.Index(s, ":")
	if i < 0 {
		return "", "", false
	}
	return strings.TrimSpace(s[:i]), strings.TrimSpace(s[i+1:]), true
}

// parseInlineList parses `[a, b, "c"]` into a slice of strings. Empty list ->
// empty slice. Missing brackets are an error.
func parseInlineList(s string) ([]string, error) {
	s = strings.TrimSpace(s)
	if !strings.HasPrefix(s, "[") || !strings.HasSuffix(s, "]") {
		return nil, fmt.Errorf("expected [..] list, got %q", s)
	}
	inner := strings.TrimSpace(s[1 : len(s)-1])
	if inner == "" {
		return []string{}, nil
	}
	parts := strings.Split(inner, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		p = strings.TrimSpace(p)
		p = strings.Trim(p, `"' `)
		if p == "" {
			continue
		}
		out = append(out, p)
	}
	return out, nil
}

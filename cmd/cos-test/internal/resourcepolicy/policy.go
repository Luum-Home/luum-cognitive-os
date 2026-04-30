// Package resourcepolicy parses the test resource policy manifest used by
// cos-test. Lane selection stays in .cognitive-os/test-lanes.yaml; this package
// owns resource/cost metadata for those lanes.
package resourcepolicy

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

const filename = "test-resource-policy.yaml"

type Policy struct {
	Defaults ResourcePolicy
	Lanes    map[string]ResourcePolicy
}

type ResourcePolicy struct {
	Workers        string
	TimeoutSeconds int
	DockerPolicy   string
	CostPolicy     string
	ArtifactPolicy string
}

func DefaultPath(projectRoot string) string {
	return filepath.Join(projectRoot, ".cognitive-os", filename)
}

func BuiltinDefault() *Policy {
	return &Policy{
		Defaults: ResourcePolicy{
			Workers:        "auto",
			TimeoutSeconds: 300,
			DockerPolicy:   "forbidden",
			CostPolicy:     "free_only",
			ArtifactPolicy: "keep_summary",
		},
		Lanes: map[string]ResourcePolicy{},
	}
}

func Load(projectRoot string) (*Policy, error) {
	path := DefaultPath(projectRoot)
	f, err := os.Open(path)
	if err != nil {
		if os.IsNotExist(err) {
			return BuiltinDefault(), nil
		}
		return nil, fmt.Errorf("open resource policy %s: %w", path, err)
	}
	defer f.Close()
	return Parse(f)
}

func Parse(r io.Reader) (*Policy, error) {
	policy := BuiltinDefault()
	scanner := bufio.NewScanner(r)
	scanner.Buffer(make([]byte, 64*1024), 1024*1024)

	section := ""
	currentLane := ""
	for scanner.Scan() {
		raw := stripComment(scanner.Text())
		line := strings.TrimRight(raw, " \t")
		if strings.TrimSpace(line) == "" {
			continue
		}
		indent := countLeadingSpaces(line)
		body := strings.TrimSpace(line)

		if indent == 0 {
			currentLane = ""
			key, value, ok := splitKV(body)
			if !ok {
				return nil, fmt.Errorf("malformed top-level field: %q", line)
			}
			switch key {
			case "version":
				if strings.Trim(value, `"' `) != "1" {
					return nil, fmt.Errorf("unsupported resource policy version %q", value)
				}
				section = ""
			case "defaults":
				section = "defaults"
			case "lanes":
				section = "lanes"
			default:
				return nil, fmt.Errorf("unknown top-level resource policy key %q", key)
			}
			continue
		}

		switch section {
		case "defaults":
			if indent != 2 {
				return nil, fmt.Errorf("defaults field must be indented two spaces: %q", line)
			}
			if err := applyField(&policy.Defaults, body); err != nil {
				return nil, fmt.Errorf("defaults: %w", err)
			}
		case "lanes":
			if indent == 2 {
				name := strings.TrimSuffix(body, ":")
				if name == "" || strings.Contains(name, ":") {
					return nil, fmt.Errorf("invalid lane resource policy header: %q", line)
				}
				currentLane = name
				if _, ok := policy.Lanes[currentLane]; !ok {
					policy.Lanes[currentLane] = ResourcePolicy{}
				}
				continue
			}
			if indent != 4 || currentLane == "" {
				return nil, fmt.Errorf("lane resource field outside lane block: %q", line)
			}
			lanePolicy := policy.Lanes[currentLane]
			if err := applyField(&lanePolicy, body); err != nil {
				return nil, fmt.Errorf("lane %s: %w", currentLane, err)
			}
			policy.Lanes[currentLane] = lanePolicy
		default:
			return nil, fmt.Errorf("field outside defaults/lanes block: %q", line)
		}
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	if err := validatePolicy(policy.Defaults); err != nil {
		return nil, fmt.Errorf("defaults: %w", err)
	}
	for name, lane := range policy.Lanes {
		merged := policy.Effective(name)
		_ = lane
		if err := validatePolicy(merged); err != nil {
			return nil, fmt.Errorf("lane %s: %w", name, err)
		}
	}
	return policy, nil
}

func (p *Policy) Effective(lane string) ResourcePolicy {
	if p == nil {
		return BuiltinDefault().Defaults
	}
	out := p.Defaults
	lp := p.Lanes[lane]
	if lp.Workers != "" {
		out.Workers = lp.Workers
	}
	if lp.TimeoutSeconds != 0 {
		out.TimeoutSeconds = lp.TimeoutSeconds
	}
	if lp.DockerPolicy != "" {
		out.DockerPolicy = lp.DockerPolicy
	}
	if lp.CostPolicy != "" {
		out.CostPolicy = lp.CostPolicy
	}
	if lp.ArtifactPolicy != "" {
		out.ArtifactPolicy = lp.ArtifactPolicy
	}
	return out
}

func (p *Policy) ValidateLaneNames(valid []string) error {
	allowed := map[string]struct{}{}
	for _, name := range valid {
		allowed[name] = struct{}{}
	}
	for name := range p.Lanes {
		if _, ok := allowed[name]; !ok {
			return fmt.Errorf("resource policy references unknown lane %q", name)
		}
	}
	return nil
}

func (rp ResourcePolicy) Summary() string {
	return fmt.Sprintf("workers=%s timeout=%ds docker=%s cost=%s artifacts=%s", rp.Workers, rp.TimeoutSeconds, rp.DockerPolicy, rp.CostPolicy, rp.ArtifactPolicy)
}

func applyField(rp *ResourcePolicy, body string) error {
	key, value, ok := splitKV(body)
	if !ok {
		return fmt.Errorf("malformed field %q", body)
	}
	value = strings.Trim(value, `"' `)
	switch key {
	case "workers":
		if value == "" {
			return fmt.Errorf("workers cannot be empty")
		}
		rp.Workers = value
	case "timeout_seconds":
		n, err := strconv.Atoi(value)
		if err != nil || n <= 0 {
			return fmt.Errorf("timeout_seconds must be a positive integer, got %q", value)
		}
		rp.TimeoutSeconds = n
	case "docker_policy":
		rp.DockerPolicy = value
	case "cost_policy":
		rp.CostPolicy = value
	case "artifact_policy":
		rp.ArtifactPolicy = value
	default:
		return fmt.Errorf("unknown field %q", key)
	}
	return nil
}

func validatePolicy(rp ResourcePolicy) error {
	if rp.Workers != "auto" && rp.Workers != "0" {
		if n, err := strconv.Atoi(rp.Workers); err != nil || n <= 0 {
			return fmt.Errorf("workers must be auto, 0, or a positive integer, got %q", rp.Workers)
		}
	}
	if rp.TimeoutSeconds <= 0 {
		return fmt.Errorf("timeout_seconds must be positive")
	}
	if !oneOf(rp.DockerPolicy, "forbidden", "allowed", "required") {
		return fmt.Errorf("docker_policy must be forbidden, allowed, or required, got %q", rp.DockerPolicy)
	}
	if !oneOf(rp.CostPolicy, "free_only", "cost_bearing") {
		return fmt.Errorf("cost_policy must be free_only or cost_bearing, got %q", rp.CostPolicy)
	}
	if !oneOf(rp.ArtifactPolicy, "keep_summary", "keep_full") {
		return fmt.Errorf("artifact_policy must be keep_summary or keep_full, got %q", rp.ArtifactPolicy)
	}
	return nil
}

func oneOf(v string, allowed ...string) bool {
	for _, a := range allowed {
		if v == a {
			return true
		}
	}
	return false
}

func stripComment(s string) string {
	if i := strings.Index(s, "#"); i >= 0 {
		return s[:i]
	}
	return s
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

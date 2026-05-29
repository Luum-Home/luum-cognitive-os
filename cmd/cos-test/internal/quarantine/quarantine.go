// Package quarantine validates the formal test quarantine manifest.
package quarantine

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
)

const SchemaVersion = "test-quarantine.v1"

var idPattern = regexp.MustCompile(`^[a-z0-9][a-z0-9._-]*$`)

// Manifest is the top-level test quarantine manifest.
type Manifest struct {
	SchemaVersion string
	Entries       []Entry
}

// Entry is one intentionally quarantined pytest node.
type Entry struct {
	ID      string
	NodeID  string
	Owner   string
	Reason  string
	Expires string
	Created string
	Issue   string
	Line    int
}

// Finding describes one manifest audit violation.
type Finding struct {
	Line    int
	EntryID string
	Field   string
	Message string
}

func (f Finding) String() string {
	prefix := "manifest"
	if f.Line > 0 {
		prefix = fmt.Sprintf("line %d", f.Line)
	}
	if f.EntryID != "" {
		prefix += fmt.Sprintf(" entry %q", f.EntryID)
	}
	if f.Field != "" {
		prefix += fmt.Sprintf(" field %q", f.Field)
	}
	return prefix + ": " + f.Message
}

// DefaultPath returns the conventional quarantine manifest path.
func DefaultPath(projectRoot string) string {
	return filepath.Join(projectRoot, ".cognitive-os", "test-quarantine.yaml")
}

// Load reads and parses a quarantine manifest from disk.
func Load(path string) (*Manifest, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open quarantine manifest %s: %w", path, err)
	}
	defer f.Close()
	return Parse(f)
}

// Parse parses the narrow YAML dialect used by .cognitive-os/test-quarantine.yaml.
func Parse(r io.Reader) (*Manifest, error) {
	m := &Manifest{}
	scanner := bufio.NewScanner(r)
	section := ""
	var current *Entry
	lineNo := 0

	finishCurrent := func() {
		if current != nil {
			m.Entries = append(m.Entries, *current)
			current = nil
		}
	}

	for scanner.Scan() {
		lineNo++
		raw := scanner.Text()
		line := strings.TrimRight(raw, " \t")
		trimmed := strings.TrimSpace(line)
		if trimmed == "" || strings.HasPrefix(trimmed, "#") {
			continue
		}

		if !strings.HasPrefix(line, " ") && !strings.HasPrefix(line, "\t") {
			finishCurrent()
			key, value, ok := splitKeyValue(trimmed)
			if !ok {
				return nil, fmt.Errorf("line %d: expected top-level key", lineNo)
			}
			switch key {
			case "schema_version":
				m.SchemaVersion = cleanScalar(value)
				section = ""
			case "quarantines":
				trimmedValue := strings.TrimSpace(value)
				if trimmedValue == "[]" {
					section = ""
					continue
				}
				if trimmedValue != "" {
					return nil, fmt.Errorf("line %d: quarantines must be a YAML list", lineNo)
				}
				section = "quarantines"
			default:
				return nil, fmt.Errorf("line %d: unsupported top-level key %q", lineNo, key)
			}
			continue
		}

		if section != "quarantines" {
			return nil, fmt.Errorf("line %d: nested keys are only supported under quarantines", lineNo)
		}
		if strings.HasPrefix(line, "  - ") {
			finishCurrent()
			current = &Entry{Line: lineNo}
			rest := strings.TrimSpace(strings.TrimPrefix(line, "  - "))
			if rest == "" {
				continue
			}
			key, value, ok := splitKeyValue(rest)
			if !ok {
				return nil, fmt.Errorf("line %d: list item must be a mapping", lineNo)
			}
			if err := assign(current, key, value, lineNo); err != nil {
				return nil, err
			}
			continue
		}
		if strings.HasPrefix(line, "    ") {
			if current == nil {
				return nil, fmt.Errorf("line %d: quarantine field appears before any list item", lineNo)
			}
			key, value, ok := splitKeyValue(strings.TrimSpace(line))
			if !ok {
				return nil, fmt.Errorf("line %d: expected quarantine field", lineNo)
			}
			if err := assign(current, key, value, lineNo); err != nil {
				return nil, err
			}
			continue
		}
		return nil, fmt.Errorf("line %d: unsupported indentation", lineNo)
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	finishCurrent()
	return m, nil
}

// Audit validates manifest structure, required metadata, and expiration dates.
func Audit(m *Manifest, today time.Time) []Finding {
	if m == nil {
		return []Finding{{Message: "manifest is nil"}}
	}
	var findings []Finding
	if m.SchemaVersion != SchemaVersion {
		findings = append(findings, Finding{Field: "schema_version", Message: fmt.Sprintf("must be %q", SchemaVersion)})
	}
	seenIDs := map[string]int{}
	seenNodeIDs := map[string]int{}
	utcToday := dateOnly(today.UTC())
	for i, entry := range m.Entries {
		label := entry.ID
		if label == "" {
			label = fmt.Sprintf("#%d", i+1)
		}
		findings = append(findings, auditRequired(entry, label)...)
		if entry.ID != "" {
			if !idPattern.MatchString(entry.ID) {
				findings = append(findings, Finding{Line: entry.Line, EntryID: label, Field: "id", Message: "must match ^[a-z0-9][a-z0-9._-]*$"})
			}
			if prior, ok := seenIDs[entry.ID]; ok {
				findings = append(findings, Finding{Line: entry.Line, EntryID: label, Field: "id", Message: fmt.Sprintf("duplicates entry first declared on line %d", prior)})
			} else {
				seenIDs[entry.ID] = entry.Line
			}
		}
		if entry.NodeID != "" {
			if prior, ok := seenNodeIDs[entry.NodeID]; ok {
				findings = append(findings, Finding{Line: entry.Line, EntryID: label, Field: "nodeid", Message: fmt.Sprintf("duplicates entry first declared on line %d", prior)})
			} else {
				seenNodeIDs[entry.NodeID] = entry.Line
			}
		}
		if strings.TrimSpace(entry.Expires) != "" {
			expires, err := parseDate(entry.Expires)
			if err != nil {
				findings = append(findings, Finding{Line: entry.Line, EntryID: label, Field: "expires", Message: "must be YYYY-MM-DD"})
			} else if expires.Before(utcToday) {
				findings = append(findings, Finding{Line: entry.Line, EntryID: label, Field: "expires", Message: fmt.Sprintf("expired on %s", expires.Format(time.DateOnly))})
			}
		}
	}
	sort.SliceStable(findings, func(i, j int) bool {
		if findings[i].Line != findings[j].Line {
			return findings[i].Line < findings[j].Line
		}
		if findings[i].EntryID != findings[j].EntryID {
			return findings[i].EntryID < findings[j].EntryID
		}
		return findings[i].Field < findings[j].Field
	})
	return findings
}

func auditRequired(entry Entry, label string) []Finding {
	required := []struct {
		field string
		value string
	}{
		{"id", entry.ID},
		{"nodeid", entry.NodeID},
		{"owner", entry.Owner},
		{"reason", entry.Reason},
		{"expires", entry.Expires},
	}
	var out []Finding
	for _, item := range required {
		if strings.TrimSpace(item.value) == "" {
			out = append(out, Finding{Line: entry.Line, EntryID: label, Field: item.field, Message: "is required"})
		}
	}
	return out
}

func assign(entry *Entry, key, value string, lineNo int) error {
	clean := cleanScalar(value)
	switch key {
	case "id":
		entry.ID = clean
	case "nodeid":
		entry.NodeID = clean
	case "owner":
		entry.Owner = clean
	case "reason":
		entry.Reason = clean
	case "expires":
		entry.Expires = clean
	case "created":
		entry.Created = clean
	case "issue":
		entry.Issue = clean
	default:
		return fmt.Errorf("line %d: unsupported quarantine field %q", lineNo, key)
	}
	return nil
}

func splitKeyValue(line string) (string, string, bool) {
	idx := strings.Index(line, ":")
	if idx < 0 {
		return "", "", false
	}
	key := strings.TrimSpace(line[:idx])
	value := strings.TrimSpace(stripInlineComment(line[idx+1:]))
	if key == "" || strings.ContainsAny(key, " \t") {
		return "", "", false
	}
	return key, value, true
}

func cleanScalar(value string) string {
	value = strings.TrimSpace(value)
	if len(value) >= 2 {
		if (value[0] == '"' && value[len(value)-1] == '"') || (value[0] == '\'' && value[len(value)-1] == '\'') {
			return value[1 : len(value)-1]
		}
	}
	return value
}

func stripInlineComment(value string) string {
	inSingle := false
	inDouble := false
	for i, r := range value {
		switch r {
		case '\'':
			if !inDouble {
				inSingle = !inSingle
			}
		case '"':
			if !inSingle {
				inDouble = !inDouble
			}
		case '#':
			if !inSingle && !inDouble {
				if i == 0 || value[i-1] == ' ' || value[i-1] == '\t' {
					return strings.TrimSpace(value[:i])
				}
			}
		}
	}
	return strings.TrimSpace(value)
}

func parseDate(value string) (time.Time, error) {
	if len(value) != len("2006-01-02") {
		return time.Time{}, fmt.Errorf("invalid date %q", value)
	}
	return time.Parse(time.DateOnly, value)
}

func dateOnly(t time.Time) time.Time {
	year, month, day := t.Date()
	return time.Date(year, month, day, 0, 0, 0, 0, time.UTC)
}

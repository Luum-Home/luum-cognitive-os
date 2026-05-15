package tui

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
)

// Snapshot is the read-only Surface 5 data model for the operator TUI MVP.
type Snapshot struct {
	ProjectDir       string
	ReleaseReady     bool
	ReleaseEvidence  []string
	CosdStatus       string
	CosdQueueDepth   int
	CoverageTotal    int
	CoverageGaps     int
	CoveragePartial  int
	CoverageSurfaces []string
	ReceiptTotal     int
	ReceiptLast      string
	Warnings         []string
}

// Model is a Bubble Tea model for the Surface 5 operator console.
type Model struct {
	Snapshot         Snapshot
	Tab              int
	PendingAction    string
	RunningAction    string
	LastActionResult *ActionResult
}

type actionFinishedMsg struct {
	Result   ActionResult
	Snapshot Snapshot
}

var tabs = []string{"Overview", "cosd", "Coverage", "Release", "Receipts"}

func LoadSnapshot(projectDir string) Snapshot {
	root := filepath.Clean(projectDir)
	snapshot := Snapshot{ProjectDir: root, CosdStatus: "stopped"}
	snapshot.loadRelease(root)
	snapshot.loadCosd(root)
	snapshot.loadCoverage(root)
	snapshot.loadReceipts(root)
	return snapshot
}

func SnapshotText(projectDir string) string {
	model := NewModel(LoadSnapshot(projectDir))
	return model.renderAll()
}

func NewModel(snapshot Snapshot) Model {
	return Model{Snapshot: snapshot}
}

func (m Model) Init() tea.Cmd {
	return nil
}

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch v := msg.(type) {
	case actionFinishedMsg:
		m.RunningAction = ""
		m.PendingAction = ""
		m.LastActionResult = &v.Result
		m.Snapshot = v.Snapshot
		return m, nil
	case tea.KeyMsg:
		if m.RunningAction != "" {
			return m, nil
		}
		switch v.String() {
		case "q", "ctrl+c", "esc":
			return m, tea.Quit
		case "right", "tab", "l":
			m.Tab = (m.Tab + 1) % len(tabs)
		case "left", "shift+tab", "h":
			m.Tab = (m.Tab + len(tabs) - 1) % len(tabs)
		case "r":
			m.PendingAction = "refresh-coverage"
		case "p":
			m.PendingAction = "cosd-process-once"
		case "x":
			m.PendingAction = ""
		case "c":
			if m.PendingAction == "" {
				return m, nil
			}
			action := m.PendingAction
			projectDir := m.Snapshot.ProjectDir
			m.RunningAction = action
			return m, runActionCmd(projectDir, action)
		}
	}
	return m, nil
}

func (m Model) View() string {
	var b strings.Builder
	b.WriteString("Cognitive OS — Surface 5 Operator Console\n")
	b.WriteString("Project: ")
	b.WriteString(m.Snapshot.ProjectDir)
	b.WriteString("\n")
	b.WriteString(m.tabBar())
	b.WriteString("\n\n")
	b.WriteString(m.renderTab(tabs[m.Tab]))
	b.WriteString("\n")
	b.WriteString(m.actionPanel())
	b.WriteString("\nkeys: ←/→ tabs · r refresh coverage · p process cosd once · c confirm · x cancel · q quit\n")
	return b.String()
}

func (m Model) actionPanel() string {
	if m.RunningAction != "" {
		return "\nAction: running " + m.RunningAction + "...\n"
	}
	var b strings.Builder
	if m.PendingAction != "" {
		b.WriteString("\nPending action: ")
		b.WriteString(m.PendingAction)
		b.WriteString(" — press c to confirm or x to cancel.\n")
	} else {
		b.WriteString("\nActions: r queues refresh-coverage, p queues cosd-process-once.\n")
	}
	if m.LastActionResult != nil {
		b.WriteString("Last action: ")
		b.WriteString(m.LastActionResult.Action)
		b.WriteString(" ")
		b.WriteString(m.LastActionResult.Outcome)
		if m.LastActionResult.Reason != "" {
			b.WriteString(" — ")
			b.WriteString(m.LastActionResult.Reason)
		}
		b.WriteString("\n")
	}
	b.WriteString("Inbox ack stays on CLI: cos tui --operate inbox-ack --message-id ID --confirm.\n")
	return b.String()
}

func runActionCmd(projectDir string, action string) tea.Cmd {
	return func() tea.Msg {
		result := RunAction(projectDir, action, ActionOptions{Confirm: true})
		return actionFinishedMsg{Result: result, Snapshot: LoadSnapshot(projectDir)}
	}
}

func (m Model) tabBar() string {
	parts := make([]string, 0, len(tabs))
	for i, tab := range tabs {
		if i == m.Tab {
			parts = append(parts, "["+tab+"]")
		} else {
			parts = append(parts, tab)
		}
	}
	return strings.Join(parts, "  ")
}

func (m Model) renderAll() string {
	var b strings.Builder
	b.WriteString("Cognitive OS — Surface 5 Read-Only Snapshot\n")
	b.WriteString("Project: ")
	b.WriteString(m.Snapshot.ProjectDir)
	b.WriteString("\n\n")
	for _, tab := range tabs {
		b.WriteString("## ")
		b.WriteString(tab)
		b.WriteString("\n")
		b.WriteString(m.renderTab(tab))
		b.WriteString("\n")
	}
	return b.String()
}

func (m Model) renderTab(tab string) string {
	s := m.Snapshot
	switch tab {
	case "Overview":
		return fmt.Sprintf("- Release pipeline: %s\n- cosd: %s (queue=%d)\n- Coverage gaps: %d of %d\n- TUI receipts: %d\n- Warnings: %d\n%s\n", readyLabel(s.ReleaseReady), s.CosdStatus, s.CosdQueueDepth, s.CoverageGaps, s.CoverageTotal, s.ReceiptTotal, len(s.Warnings), warningList(s.Warnings))
	case "cosd":
		return fmt.Sprintf("- Status: %s\n- Intent queue depth: %d\n- Transport metadata: .cognitive-os/cosd/runtime/cosd-api.json when API is active\n", s.CosdStatus, s.CosdQueueDepth)
	case "Coverage":
		return fmt.Sprintf("- Total primitives: %d\n- Gaps: %d\n- Partial: %d\n- Surfaces: %s\n", s.CoverageTotal, s.CoverageGaps, s.CoveragePartial, strings.Join(s.CoverageSurfaces, ", "))
	case "Release":
		return fmt.Sprintf("- Ready in repo: %s\n- Evidence:\n%s\n- External remaining: homebrew tap repo, release secret, real tag/release\n", readyLabel(s.ReleaseReady), bulletList(s.ReleaseEvidence))
	case "Receipts":
		return fmt.Sprintf("- Total TUI action receipts: %d\n- Last receipt: %s\n- Path: .cognitive-os/metrics/tui-actions.jsonl\n", s.ReceiptTotal, emptyAs(s.ReceiptLast, "none"))
	default:
		return "unknown tab\n"
	}
}

func (s *Snapshot) loadRelease(root string) {
	checks := map[string]string{
		".goreleaser.yaml":                         "GoReleaser config",
		".github/workflows/cos-binary-release.yml": "GitHub release workflow",
		"scripts/install-goreleaser.sh":            "GoReleaser install/smoke script",
		"Formula/cognitive-os.rb":                  "developer HEAD Homebrew formula",
	}
	keys := make([]string, 0, len(checks))
	for path := range checks {
		keys = append(keys, path)
	}
	sort.Strings(keys)
	ready := true
	for _, path := range keys {
		if fileExists(filepath.Join(root, path)) {
			s.ReleaseEvidence = append(s.ReleaseEvidence, checks[path]+" present")
		} else {
			ready = false
			s.Warnings = append(s.Warnings, "missing "+path)
		}
	}
	s.ReleaseReady = ready
}

func (s *Snapshot) loadCosd(root string) {
	runtime := filepath.Join(root, ".cognitive-os", "cosd", "runtime")
	if fileExists(filepath.Join(runtime, "cosd.pid")) {
		s.CosdStatus = "running-metadata-present"
	}
	intents := filepath.Join(root, ".cognitive-os", "cosd", "intents")
	results := filepath.Join(root, ".cognitive-os", "cosd", "results")
	intentFiles := jsonFiles(intents)
	resultSet := map[string]bool{}
	for _, name := range jsonFiles(results) {
		resultSet[strings.TrimSuffix(name, filepath.Ext(name))] = true
	}
	for _, name := range intentFiles {
		if !resultSet[strings.TrimSuffix(name, filepath.Ext(name))] {
			s.CosdQueueDepth++
		}
	}
}

func (s *Snapshot) loadCoverage(root string) {
	coveragePath := filepath.Join(root, "docs", "reports", "primitive-harness-coverage-latest.json")
	payload := readJSONMap(coveragePath)
	if payload == nil {
		coveragePath = filepath.Join(root, "docs", "06-Daily", "reports", "primitive-harness-coverage-latest.json")
		payload = readJSONMap(coveragePath)
	}
	if payload == nil {
		s.Warnings = append(s.Warnings, "primitive coverage report missing")
		return
	}
	summary, _ := payload["summary"].(map[string]any)
	s.CoverageTotal = intFrom(summary["total_primitives"])
	s.CoverageGaps = intFrom(summary["gaps"])
	if gapsByStatus, ok := summary["gaps_by_status"].(map[string]any); ok {
		s.CoveragePartial = intFrom(gapsByStatus["partial"])
	}
	if counts, ok := summary["surface_projected_or_wired"].(map[string]any); ok {
		for key := range counts {
			s.CoverageSurfaces = append(s.CoverageSurfaces, key)
		}
		sort.Strings(s.CoverageSurfaces)
	}
}

func (s *Snapshot) loadReceipts(root string) {
	path := filepath.Join(root, ".cognitive-os", "metrics", "tui-actions.jsonl")
	file, err := os.Open(path)
	if err != nil {
		return
	}
	defer file.Close()
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		var row map[string]any
		if json.Unmarshal(scanner.Bytes(), &row) != nil {
			continue
		}
		if row["schema_version"] != "cos-tui-action-receipt.v1" {
			continue
		}
		s.ReceiptTotal++
		action, _ := row["action"].(string)
		outcome, _ := row["outcome"].(string)
		s.ReceiptLast = strings.TrimSpace(action + " " + outcome)
	}
}

func warningList(items []string) string {
	if len(items) == 0 {
		return "- Warning details: none"
	}
	return "- Warning details:\n" + bulletList(items)
}

func readyLabel(ok bool) string {
	if ok {
		return "ready"
	}
	return "incomplete"
}

func bulletList(items []string) string {
	if len(items) == 0 {
		return "  - none"
	}
	var b strings.Builder
	for _, item := range items {
		b.WriteString("  - ")
		b.WriteString(item)
		b.WriteString("\n")
	}
	return strings.TrimRight(b.String(), "\n")
}

func emptyAs(value string, fallback string) string {
	if strings.TrimSpace(value) == "" {
		return fallback
	}
	return value
}

func fileExists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && !info.IsDir()
}

func jsonFiles(dir string) []string {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil
	}
	var files []string
	for _, entry := range entries {
		if !entry.IsDir() && strings.HasSuffix(entry.Name(), ".json") {
			files = append(files, entry.Name())
		}
	}
	return files
}

func readJSONMap(path string) map[string]any {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil
	}
	var payload map[string]any
	if json.Unmarshal(data, &payload) != nil {
		return nil
	}
	return payload
}

func intFrom(value any) int {
	switch v := value.(type) {
	case int:
		return v
	case int64:
		return int(v)
	case float64:
		return int(v)
	default:
		return 0
	}
}

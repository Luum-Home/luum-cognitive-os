package cli

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/project"
)

const sddStateVersion = 1

var (
	sddFeature   string
	sddTitle     string
	sddWorkClass string
	sddStore     string
	sddJSON      bool
)

var sddCmd = &cobra.Command{
	Use:   "sdd",
	Short: "Run the local consumer SDD lane",
	Long: `Run the local consumer SDD lane.

The lane is intentionally filesystem-first: it writes task state and durable
artifacts under .cognitive-os/workflows/sdd/ so a consumer project can move one
feature from intent to reviewed evidence without depending on Linear, Jira, or a
dashboard.

Flow:
  cos sdd next --feature cli-recent --title "Recent notes"
  cos sdd approve cli-recent
  cos sdd apply cli-recent
  cos sdd review cli-recent`,
}

var sddNextCmd = &cobra.Command{
	Use:   "next",
	Short: "Create the next local SDD feature scaffold",
	RunE: func(cmd *cobra.Command, args []string) error {
		if sddStore != "local" {
			return fmt.Errorf("unsupported SDD store %q: only local is implemented", sddStore)
		}
		feature, err := requiredFeature()
		if err != nil {
			return err
		}
		return runSDDNext(feature)
	},
}

var sddApproveCmd = &cobra.Command{
	Use:   "approve FEATURE",
	Short: "Approve a spec_ready local SDD feature",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		return transitionSDDFeature(args[0], "spec_ready", "approved", "approved by human gate")
	},
}

var sddApplyCmd = &cobra.Command{
	Use:   "apply FEATURE",
	Short: "Move an approved local SDD feature into implementation",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		return runSDDApply(args[0])
	},
}

var sddReviewCmd = &cobra.Command{
	Use:   "review FEATURE",
	Short: "Review a local SDD feature for task and requirement evidence",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		return runSDDReview(args[0])
	},
}

var sddStatusCmd = &cobra.Command{
	Use:   "status",
	Short: "Show local SDD lane state",
	RunE: func(cmd *cobra.Command, args []string) error {
		return runSDDStatus()
	},
}

func init() {
	sddNextCmd.Flags().StringVar(&sddFeature, "feature", "", "Stable feature slug to create")
	sddNextCmd.Flags().StringVar(&sddTitle, "title", "", "Human-readable feature title")
	sddNextCmd.Flags().StringVar(&sddWorkClass, "work-class", "medium", "Work class: trivial|small|medium|large|critical")
	sddNextCmd.Flags().StringVar(&sddStore, "store", "local", "Task-state store: local")
	sddStatusCmd.Flags().BoolVar(&sddJSON, "json", false, "Output state as JSON")
	sddCmd.AddCommand(sddNextCmd, sddApproveCmd, sddApplyCmd, sddReviewCmd, sddStatusCmd)
	rootCmd.AddCommand(sddCmd)
}

type sddLaneState struct {
	Version     int                        `json:"version"`
	Store       string                     `json:"store"`
	UpdatedAt   string                     `json:"updated_at"`
	Active      string                     `json:"active,omitempty"`
	Features    map[string]sddFeatureState `json:"features"`
	Transitions []sddTransition            `json:"transitions"`
}

type sddFeatureState struct {
	ID        string            `json:"id"`
	Title     string            `json:"title"`
	WorkClass string            `json:"work_class"`
	Status    string            `json:"status"`
	Artifacts map[string]string `json:"artifacts"`
	UpdatedAt string            `json:"updated_at"`
}

type sddTransition struct {
	Feature string `json:"feature"`
	From    string `json:"from"`
	To      string `json:"to"`
	At      string `json:"at"`
	Reason  string `json:"reason"`
}

type sddReviewFinding struct {
	Severity string `json:"severity"`
	Message  string `json:"message"`
}

type sddReviewResult struct {
	Verdict      string             `json:"verdict"`
	Requirements []string           `json:"requirements"`
	Mapped       []string           `json:"mapped"`
	Findings     []sddReviewFinding `json:"findings"`
}

func requiredFeature() (string, error) {
	feature := strings.TrimSpace(sddFeature)
	if feature == "" {
		return "", errors.New("--feature is required")
	}
	if err := validateSDDFeatureID(feature); err != nil {
		return "", err
	}
	return feature, nil
}

func validateSDDFeatureID(feature string) error {
	ok, err := regexp.MatchString(`^[a-z0-9][a-z0-9_-]*$`, feature)
	if err != nil {
		return err
	}
	if !ok || strings.Contains(feature, "..") || strings.Contains(feature, string(os.PathSeparator)) {
		return fmt.Errorf("invalid feature %q: use a lowercase slug with letters, numbers, hyphen, or underscore", feature)
	}
	return nil
}

func sddRoot() string {
	return filepath.Join(project.FindRootOrCwd(), ".cognitive-os", "workflows", "sdd")
}

func sddStatePath() string {
	return filepath.Join(sddRoot(), "state.json")
}

func loadSDDState() (sddLaneState, error) {
	state := sddLaneState{Version: sddStateVersion, Store: "local", Features: map[string]sddFeatureState{}}
	data, err := os.ReadFile(sddStatePath())
	if errors.Is(err, os.ErrNotExist) {
		return state, nil
	}
	if err != nil {
		return state, fmt.Errorf("reading SDD state: %w", err)
	}
	if err := json.Unmarshal(data, &state); err != nil {
		return state, fmt.Errorf("parsing SDD state: %w", err)
	}
	if state.Features == nil {
		state.Features = map[string]sddFeatureState{}
	}
	return state, nil
}

func saveSDDState(state sddLaneState) error {
	state.Version = sddStateVersion
	state.Store = "local"
	state.UpdatedAt = nowUTC()
	if err := os.MkdirAll(sddRoot(), 0755); err != nil {
		return fmt.Errorf("creating SDD root: %w", err)
	}
	data, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return fmt.Errorf("encoding SDD state: %w", err)
	}
	return os.WriteFile(sddStatePath(), append(data, '\n'), 0644)
}

func runSDDNext(feature string) error {
	state, err := loadSDDState()
	if err != nil {
		return err
	}
	if existing, ok := state.Features[feature]; ok && existing.Status != "rejected" {
		return fmt.Errorf("SDD feature %q already exists with status %q", feature, existing.Status)
	}
	for id, existing := range state.Features {
		if id != feature && !isTerminalSDDStatus(existing.Status) {
			return fmt.Errorf("local SDD lane allows one active feature; %q is %s", id, existing.Status)
		}
	}
	if err := validateWorkClass(sddWorkClass); err != nil {
		return err
	}
	title := strings.TrimSpace(sddTitle)
	if title == "" {
		title = feature
	}
	featureDir := filepath.Join(sddRoot(), feature)
	artifacts := map[string]string{
		"requirements": filepath.ToSlash(filepath.Join(".cognitive-os", "workflows", "sdd", feature, "requirements.md")),
		"design":       filepath.ToSlash(filepath.Join(".cognitive-os", "workflows", "sdd", feature, "design.md")),
		"tasks":        filepath.ToSlash(filepath.Join(".cognitive-os", "workflows", "sdd", feature, "tasks.md")),
		"traceability": filepath.ToSlash(filepath.Join(".cognitive-os", "workflows", "sdd", feature, "traceability.md")),
		"review":       filepath.ToSlash(filepath.Join(".cognitive-os", "workflows", "sdd", feature, "review.md")),
	}
	if err := os.MkdirAll(featureDir, 0755); err != nil {
		return fmt.Errorf("creating feature directory: %w", err)
	}
	files := map[string]string{
		"requirements.md": sddRequirementsTemplate(feature, title, sddWorkClass),
		"design.md":       sddDesignTemplate(feature, title),
		"tasks.md":        sddTasksTemplate(feature),
		"traceability.md": sddTraceabilityTemplate(feature),
		"review.md":       sddReviewTemplate(feature, "PENDING", nil),
	}
	for name, content := range files {
		path := filepath.Join(featureDir, name)
		if _, err := os.Stat(path); err == nil {
			return fmt.Errorf("refusing to overwrite existing artifact %s", path)
		}
		if err := os.WriteFile(path, []byte(content), 0644); err != nil {
			return fmt.Errorf("writing %s: %w", path, err)
		}
	}
	state.Active = feature
	state.Features[feature] = sddFeatureState{ID: feature, Title: title, WorkClass: sddWorkClass, Status: "spec_ready", Artifacts: artifacts, UpdatedAt: nowUTC()}
	appendTransition(&state, feature, "pending", "spec_ready", "local spec scaffold generated")
	if err := writeCurrentProgress(feature, "spec_ready", "Review requirements.md, design.md, and tasks.md, then run cos sdd approve "+feature); err != nil {
		return err
	}
	if err := saveSDDState(state); err != nil {
		return err
	}
	fmt.Printf("SDD_NEXT: %s status=spec_ready artifacts=%s\n", feature, filepath.ToSlash(featureDir))
	return nil
}

func transitionSDDFeature(feature, from, to, reason string) error {
	if err := validateSDDFeatureID(feature); err != nil {
		return err
	}
	state, err := loadSDDState()
	if err != nil {
		return err
	}
	current, ok := state.Features[feature]
	if !ok {
		return fmt.Errorf("unknown SDD feature %q", feature)
	}
	if current.Status != from {
		return fmt.Errorf("feature %q is %s, expected %s", feature, current.Status, from)
	}
	current.Status = to
	current.UpdatedAt = nowUTC()
	state.Features[feature] = current
	state.Active = activeFeatureAfterTransition(feature, to)
	appendTransition(&state, feature, from, to, reason)
	if err := writeCurrentProgress(feature, to, nextInstruction(feature, to)); err != nil {
		return err
	}
	if err := saveSDDState(state); err != nil {
		return err
	}
	fmt.Printf("SDD_TRANSITION: %s %s->%s\n", feature, from, to)
	return nil
}

func runSDDApply(feature string) error {
	if err := transitionSDDFeature(feature, "approved", "in_progress", "implementation started from approved spec"); err != nil {
		return err
	}
	return nil
}

func runSDDReview(feature string) error {
	if err := validateSDDFeatureID(feature); err != nil {
		return err
	}
	state, err := loadSDDState()
	if err != nil {
		return err
	}
	current, ok := state.Features[feature]
	if !ok {
		return fmt.Errorf("unknown SDD feature %q", feature)
	}
	if current.Status != "in_progress" && current.Status != "review_ready" {
		return fmt.Errorf("feature %q is %s, expected in_progress or review_ready", feature, current.Status)
	}
	result, err := reviewSDDArtifacts(feature)
	if err != nil {
		return err
	}
	reviewPath := filepath.Join(sddRoot(), feature, "review.md")
	if err := os.WriteFile(reviewPath, []byte(sddReviewTemplate(feature, result.Verdict, result.Findings)), 0644); err != nil {
		return fmt.Errorf("writing review: %w", err)
	}
	from := current.Status
	to := "done"
	if result.Verdict != "PASS" {
		to = "review_ready"
	}
	current.Status = to
	current.UpdatedAt = nowUTC()
	state.Features[feature] = current
	state.Active = activeFeatureAfterTransition(feature, to)
	appendTransition(&state, feature, from, to, "review verdict "+result.Verdict)
	if result.Verdict == "PASS" {
		if err := appendHistory(feature, result); err != nil {
			return err
		}
	}
	if err := writeCurrentProgress(feature, to, nextInstruction(feature, to)); err != nil {
		return err
	}
	if err := saveSDDState(state); err != nil {
		return err
	}
	fmt.Printf("SDD_REVIEW: %s verdict=%s findings=%d\n", feature, result.Verdict, len(result.Findings))
	if result.Verdict != "PASS" {
		return fmt.Errorf("SDD review failed for %s", feature)
	}
	return nil
}

func runSDDStatus() error {
	state, err := loadSDDState()
	if err != nil {
		return err
	}
	if sddJSON {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		return enc.Encode(state)
	}
	ids := make([]string, 0, len(state.Features))
	for id := range state.Features {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	if len(ids) == 0 {
		fmt.Println("No local SDD features found.")
		return nil
	}
	for _, id := range ids {
		f := state.Features[id]
		fmt.Printf("%s\t%s\t%s\n", f.ID, f.Status, f.Title)
	}
	return nil
}

func reviewSDDArtifacts(feature string) (sddReviewResult, error) {
	featureDir := filepath.Join(sddRoot(), feature)
	requirementsText, err := os.ReadFile(filepath.Join(featureDir, "requirements.md"))
	if err != nil {
		return sddReviewResult{}, fmt.Errorf("reading requirements: %w", err)
	}
	tasksText, err := os.ReadFile(filepath.Join(featureDir, "tasks.md"))
	if err != nil {
		return sddReviewResult{}, fmt.Errorf("reading tasks: %w", err)
	}
	traceText, err := os.ReadFile(filepath.Join(featureDir, "traceability.md"))
	if err != nil {
		return sddReviewResult{}, fmt.Errorf("reading traceability: %w", err)
	}
	designText, err := os.ReadFile(filepath.Join(featureDir, "design.md"))
	if err != nil {
		return sddReviewResult{}, fmt.Errorf("reading design: %w", err)
	}
	reqs := extractRequirementIDs(string(requirementsText))
	mapped := extractMappedRequirementIDs(string(traceText))
	mappedSet := map[string]bool{}
	for _, id := range mapped {
		mappedSet[id] = true
	}
	var findings []sddReviewFinding
	if len(reqs) == 0 {
		findings = append(findings, sddReviewFinding{Severity: "HIGH", Message: "requirements.md has no R<n> requirement IDs"})
	}
	for _, req := range reqs {
		if !mappedSet[req] {
			findings = append(findings, sddReviewFinding{Severity: "HIGH", Message: req + " lacks test or accepted proof mapping"})
		}
	}
	if hasUncheckedTask(string(tasksText)) {
		findings = append(findings, sddReviewFinding{Severity: "MEDIUM", Message: "tasks.md still contains unchecked tasks"})
	}
	if containsSDDPlaceholder(string(traceText)) {
		findings = append(findings, sddReviewFinding{Severity: "HIGH", Message: "traceability.md still contains placeholder evidence"})
	}
	if containsSDDPlaceholder(string(designText)) {
		findings = append(findings, sddReviewFinding{Severity: "MEDIUM", Message: "design.md still contains placeholder implementation boundaries"})
	}
	verdict := "PASS"
	if len(findings) > 0 {
		verdict = "FAIL"
	}
	return sddReviewResult{Verdict: verdict, Requirements: reqs, Mapped: mapped, Findings: findings}, nil
}

func extractRequirementIDs(text string) []string {
	re := regexp.MustCompile(`(?m)^\s*(R[0-9]+)\s*[:|\-]`)
	matches := re.FindAllStringSubmatch(text, -1)
	return uniqueSubmatches(matches)
}

func extractMappedRequirementIDs(text string) []string {
	re := regexp.MustCompile(`(?m)^\s*\|?\s*(R[0-9]+)\s*\|\s*(tests?/[^|]+|MANUAL-PROOF[^|]*)\s*\|\s*(PASS|ACCEPTED)\s*\|`)
	matches := re.FindAllStringSubmatch(text, -1)
	return uniqueSubmatches(matches)
}

func uniqueSubmatches(matches [][]string) []string {
	seen := map[string]bool{}
	var ids []string
	for _, match := range matches {
		if len(match) < 2 {
			continue
		}
		id := match[1]
		if !seen[id] {
			seen[id] = true
			ids = append(ids, id)
		}
	}
	sort.Strings(ids)
	return ids
}

func hasUncheckedTask(text string) bool {
	return regexp.MustCompile(`(?m)^\s*- \[ \]`).MatchString(text)
}

func containsSDDPlaceholder(text string) bool {
	placeholders := []string{
		"tests/path::test_name",
		"Replace with real",
		"Record expected files before implementation",
	}
	for _, placeholder := range placeholders {
		if strings.Contains(text, placeholder) {
			return true
		}
	}
	return false
}

func validateWorkClass(workClass string) error {
	switch workClass {
	case "trivial", "small", "medium", "large", "critical":
		return nil
	default:
		return fmt.Errorf("invalid work class %q: use trivial, small, medium, large, or critical", workClass)
	}
}

func appendTransition(state *sddLaneState, feature, from, to, reason string) {
	state.Transitions = append(state.Transitions, sddTransition{Feature: feature, From: from, To: to, At: nowUTC(), Reason: reason})
}

func activeFeatureAfterTransition(feature, status string) string {
	if isTerminalSDDStatus(status) {
		return ""
	}
	return feature
}

func isTerminalSDDStatus(status string) bool {
	return status == "done" || status == "rejected"
}

func nextInstruction(feature, status string) string {
	switch status {
	case "spec_ready":
		return "Review requirements.md, design.md, and tasks.md, then run cos sdd approve " + feature
	case "approved":
		return "Run cos sdd apply " + feature + " before editing implementation files"
	case "in_progress":
		return "Complete tasks.md and traceability.md, then run cos sdd review " + feature
	case "review_ready":
		return "Fix review.md findings, update evidence, then re-run cos sdd review " + feature
	case "done":
		return "Feature complete; history.md contains the durable summary"
	default:
		return "Continue local SDD lane"
	}
}

func writeCurrentProgress(feature, status, instruction string) error {
	progressDir := filepath.Join(sddRoot(), "progress")
	if err := os.MkdirAll(progressDir, 0755); err != nil {
		return fmt.Errorf("creating progress directory: %w", err)
	}
	content := fmt.Sprintf("# Current SDD Progress\n\nFeature: `%s`\nStatus: `%s`\nUpdated: `%s`\n\nNext: %s\n", feature, status, nowUTC(), instruction)
	return os.WriteFile(filepath.Join(progressDir, "current.md"), []byte(content), 0644)
}

func appendHistory(feature string, result sddReviewResult) error {
	progressDir := filepath.Join(sddRoot(), "progress")
	if err := os.MkdirAll(progressDir, 0755); err != nil {
		return fmt.Errorf("creating progress directory: %w", err)
	}
	line := fmt.Sprintf("\n## %s — %s\n\n- Verdict: %s\n- Requirements: %s\n- Mapped: %s\n", nowUTC(), feature, result.Verdict, strings.Join(result.Requirements, ", "), strings.Join(result.Mapped, ", "))
	file, err := os.OpenFile(filepath.Join(progressDir, "history.md"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
	if err != nil {
		return fmt.Errorf("opening history: %w", err)
	}
	defer file.Close()
	_, err = file.WriteString(line)
	return err
}

func nowUTC() string {
	return time.Now().UTC().Format(time.RFC3339)
}

func sddRequirementsTemplate(feature, title, workClass string) string {
	return fmt.Sprintf(`# Requirements — %s

Feature: %s
Work class: %s

Use stable requirement IDs. Each `+"`R<n>`"+` must map to a test or accepted proof in `+"`traceability.md`"+` before review can pass.

R1: When the approved user or operator triggers this feature, the system must implement the requested behavior without expanding scope beyond `+"`design.md`"+`.
R2: When verification runs, the system must provide concrete evidence for the feature behavior.
`, title, feature, workClass)
}

func sddDesignTemplate(feature, title string) string {
	return fmt.Sprintf(`# Design — %s

Feature: %s

## Files To Touch

- Record expected files before implementation.

## Boundaries Not To Touch

- Do not edit secrets, private keys, or unrelated project configuration.
- Record any design change here before review.

## Alternatives Rejected

- Record rejected approaches when they matter for maintainers.
`, title, feature)
}

func sddTasksTemplate(feature string) string {
	return fmt.Sprintf(`# Tasks — %s

- [ ] Implement R1 within the design boundary.
- [ ] Add or update evidence for R2.
- [ ] Update traceability.md with every requirement-to-test/proof mapping.
`, feature)
}

func sddTraceabilityTemplate(feature string) string {
	return fmt.Sprintf(`# Traceability — %s

Review passes only when every requirement maps to a test or accepted manual proof.

| Requirement | Evidence | Status | Notes |
|---|---|---|---|
| R1 | tests/path::test_name | PASS | Replace with real test evidence. |
| R2 | MANUAL-PROOF: reviewer-approved evidence | ACCEPTED | Replace with concrete proof or test. |
`, feature)
}

func sddReviewTemplate(feature, verdict string, findings []sddReviewFinding) string {
	var builder strings.Builder
	builder.WriteString(fmt.Sprintf("# Review — %s\n\nVerdict: %s\nUpdated: %s\n\n", feature, verdict, nowUTC()))
	if len(findings) == 0 {
		builder.WriteString("Findings: none recorded.\n")
		return builder.String()
	}
	builder.WriteString("## Findings\n\n")
	for _, finding := range findings {
		builder.WriteString(fmt.Sprintf("- %s: %s\n", finding.Severity, finding.Message))
	}
	return builder.String()
}

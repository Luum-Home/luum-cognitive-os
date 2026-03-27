package ui

import (
	"fmt"
	"strings"
	"time"
)

// TestSummaryData holds data for rendering a test summary.
type TestSummaryData struct {
	Total    int
	Passed   int
	Failed   int
	Skipped  int
	Errors   int
	Duration time.Duration
	Failures []FailureInfo
}

// FailureInfo describes a test failure.
type FailureInfo struct {
	TestName string
	Message  string
}

// RenderSummary renders a styled test summary.
func RenderSummary(data TestSummaryData) string {
	var b strings.Builder

	// Header.
	b.WriteString(HeaderStyle.Render("Test Results"))
	b.WriteString("\n\n")

	// Stats line.
	parts := []string{
		SuccessStyle.Render(fmt.Sprintf("%d passed", data.Passed)),
		ErrorStyle.Render(fmt.Sprintf("%d failed", data.Failed)),
	}
	if data.Skipped > 0 {
		parts = append(parts, MutedStyle.Render(fmt.Sprintf("%d skipped", data.Skipped)))
	}
	if data.Errors > 0 {
		parts = append(parts, WarningStyle.Render(fmt.Sprintf("%d errors", data.Errors)))
	}
	b.WriteString(fmt.Sprintf("  %s of %d tests in %s",
		strings.Join(parts, ", "),
		data.Total,
		data.Duration.Round(time.Millisecond),
	))
	b.WriteString("\n")

	// Progress bar.
	if data.Total > 0 {
		b.WriteString("\n")
		b.WriteString(renderResultBar(data.Passed, data.Failed, data.Skipped, data.Total, 50))
		b.WriteString("\n")
	}

	// Failures.
	if len(data.Failures) > 0 {
		b.WriteString("\n")
		b.WriteString(ErrorStyle.Render("Failures:"))
		b.WriteString("\n")
		for _, f := range data.Failures {
			b.WriteString(fmt.Sprintf("  %s %s\n", ErrorStyle.Render(IconCross), f.TestName))
			if f.Message != "" {
				// Show first 3 lines of the failure message.
				lines := strings.Split(f.Message, "\n")
				maxLines := 3
				if len(lines) < maxLines {
					maxLines = len(lines)
				}
				for _, line := range lines[:maxLines] {
					b.WriteString(MutedStyle.Render(fmt.Sprintf("    %s", line)))
					b.WriteString("\n")
				}
			}
		}
	}

	return SummaryBox("Test Summary", b.String())
}

// renderResultBar creates a colored bar showing pass/fail/skip proportions.
func renderResultBar(passed, failed, skipped, total, width int) string {
	if total == 0 {
		return ""
	}

	passW := (passed * width) / total
	failW := (failed * width) / total
	skipW := (skipped * width) / total

	// Ensure at least 1 char for non-zero values.
	if passed > 0 && passW == 0 {
		passW = 1
	}
	if failed > 0 && failW == 0 {
		failW = 1
	}
	if skipped > 0 && skipW == 0 {
		skipW = 1
	}

	// Fill remaining with pass (the majority case).
	remaining := width - passW - failW - skipW
	if remaining > 0 {
		passW += remaining
	}

	bar := SuccessStyle.Render(strings.Repeat("#", passW)) +
		ErrorStyle.Render(strings.Repeat("#", failW)) +
		MutedStyle.Render(strings.Repeat(".", skipW))

	return fmt.Sprintf("  [%s]", bar)
}

// RenderCoverageMatrix renders a coverage matrix for all dimensions.
func RenderCoverageMatrix(dimensions map[string]CoverageDimension) string {
	var b strings.Builder

	b.WriteString(HeaderStyle.Render("Coverage Matrix"))
	b.WriteString("\n\n")

	for name, dim := range dimensions {
		pct := 0
		if dim.Total > 0 {
			pct = (dim.Covered * 100) / dim.Total
		}

		label := fmt.Sprintf("  %-20s", name)
		bar := renderCoverageBar(pct, 30)
		stats := MutedStyle.Render(fmt.Sprintf(" %d/%d (%d%%)", dim.Covered, dim.Total, pct))

		b.WriteString(label + bar + stats + "\n")
	}

	return SummaryBox("Coverage", b.String())
}

// CoverageDimension represents coverage for one dimension.
type CoverageDimension struct {
	Total   int
	Covered int
	Files   []string
}

// renderCoverageBar creates a single coverage bar.
func renderCoverageBar(pct, width int) string {
	filled := (pct * width) / 100

	var style func(string) string
	switch {
	case pct >= 80:
		style = func(s string) string { return SuccessStyle.Render(s) }
	case pct >= 50:
		style = func(s string) string { return WarningStyle.Render(s) }
	default:
		style = func(s string) string { return ErrorStyle.Render(s) }
	}

	bar := style(strings.Repeat("#", filled)) + MutedStyle.Render(strings.Repeat(".", width-filled))
	return fmt.Sprintf("[%s]", bar)
}

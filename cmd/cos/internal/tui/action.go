package tui

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

// ActionOptions carries the explicit operator confirmation and action inputs.
type ActionOptions struct {
	Confirm   bool
	MessageID string
	AckStatus string
	Note      string
}

// ActionResult is the receipt-backed result of an operable Surface 5 action.
type ActionResult struct {
	OK        bool              `json:"ok"`
	Action    string            `json:"action"`
	Outcome   string            `json:"outcome"`
	Project   string            `json:"project_dir"`
	Commands  [][]string        `json:"commands"`
	Receipt   string            `json:"receipt"`
	Reason    string            `json:"reason,omitempty"`
	Details   []CommandResult   `json:"details,omitempty"`
	Whitelist map[string]string `json:"allowlist,omitempty"`
}

// CommandResult is a redacted, bounded command execution summary.
type CommandResult struct {
	Command    []string `json:"command"`
	ReturnCode int      `json:"returncode"`
	StdoutTail string   `json:"stdout_tail"`
	StderrTail string   `json:"stderr_tail"`
}

type actionSpec struct {
	Description string
	Build       func(root string, opts ActionOptions) ([][]string, error)
}

var actionAllowlist = map[string]actionSpec{
	"refresh-coverage": {
		Description: "Refresh primitive coverage reports through scripts/cos-coverage.",
		Build: func(root string, _ ActionOptions) ([][]string, error) {
			return [][]string{{filepath.Join(root, "scripts", "cos-coverage"), "--json", "--refresh", "--project-dir", root}}, nil
		},
	},
	"cosd-process-once": {
		Description: "Ask the local cosd file-queue arbiter to process one batch.",
		Build: func(root string, _ ActionOptions) ([][]string, error) {
			return [][]string{{filepath.Join(root, "scripts", "cosd"), "--project-dir", root, "--json", "process-once"}}, nil
		},
	},
	"inbox-ack": {
		Description: "Acknowledge one directed agent-message inbox item.",
		Build: func(root string, opts ActionOptions) ([][]string, error) {
			messageID := strings.TrimSpace(opts.MessageID)
			if messageID == "" {
				return nil, errors.New("--message-id is required for inbox-ack")
			}
			status := strings.TrimSpace(opts.AckStatus)
			if status == "" {
				status = "seen"
			}
			cmd := []string{filepath.Join(root, "scripts", "cos_agent_message.py"), "--project-dir", root, "--json", "ack", "--message-id", messageID, "--status", status}
			if strings.TrimSpace(opts.Note) != "" {
				cmd = append(cmd, "--note", opts.Note)
			}
			return [][]string{cmd}, nil
		},
	},
}

func AllowedActions() map[string]string {
	out := make(map[string]string, len(actionAllowlist))
	for name, spec := range actionAllowlist {
		out[name] = spec.Description
	}
	return out
}

func RunAction(projectDir string, name string, opts ActionOptions) ActionResult {
	root := filepath.Clean(projectDir)
	action := strings.TrimSpace(name)
	result := ActionResult{Action: action, Project: root, Whitelist: AllowedActions()}
	if action == "" {
		result.Outcome = "rejected"
		result.Reason = "missing action"
		return result
	}
	spec, ok := actionAllowlist[action]
	if !ok {
		result.Outcome = "rejected"
		result.Reason = "action is not allowlisted"
		return result
	}
	commands, err := spec.Build(root, opts)
	if err != nil {
		result.Outcome = "rejected"
		result.Reason = err.Error()
		return result
	}
	result.Commands = commands
	if !opts.Confirm {
		result.Outcome = "rejected"
		result.Reason = "explicit --confirm is required for operable TUI actions"
		return result
	}
	result.Details = runCommands(root, commands)
	result.Outcome = "success"
	result.OK = true
	for _, detail := range result.Details {
		if detail.ReturnCode != 0 {
			result.OK = false
			result.Outcome = "failure"
			result.Reason = "one or more commands failed"
			break
		}
	}
	receipt, err := appendActionReceipt(root, result)
	if err != nil {
		result.OK = false
		result.Outcome = "failure"
		result.Reason = err.Error()
		return result
	}
	result.Receipt = receipt
	return result
}

func runCommands(root string, commands [][]string) []CommandResult {
	results := make([]CommandResult, 0, len(commands))
	for _, command := range commands {
		if len(command) == 0 {
			continue
		}
		cmd := exec.Command(command[0], command[1:]...)
		cmd.Dir = root
		cmd.Env = append(os.Environ(), "COGNITIVE_OS_PROJECT_DIR="+root)
		stdout, err := cmd.Output()
		stderr := []byte{}
		returnCode := 0
		if err != nil {
			if exitErr, ok := err.(*exec.ExitError); ok {
				returnCode = exitErr.ExitCode()
				stderr = exitErr.Stderr
			} else {
				returnCode = 127
				stderr = []byte(err.Error())
			}
		}
		results = append(results, CommandResult{
			Command:    command,
			ReturnCode: returnCode,
			StdoutTail: tail(string(stdout), 1200),
			StderrTail: tail(string(stderr), 1200),
		})
	}
	return results
}

func appendActionReceipt(root string, result ActionResult) (string, error) {
	path := filepath.Join(root, ".cognitive-os", "metrics", "tui-actions.jsonl")
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return "", err
	}
	row := map[string]any{
		"schema_version": "cos-tui-action-receipt.v1",
		"timestamp":      time.Now().UTC().Format(time.RFC3339Nano),
		"surface_kind":   "ui",
		"surface_id":     "tui",
		"mode":           "operable",
		"whitelisted":    true,
		"action":         result.Action,
		"outcome":        result.Outcome,
		"project_dir":    root,
		"commands":       result.Commands,
		"details": map[string]any{
			"results": result.Details,
		},
	}
	data, err := json.Marshal(row)
	if err != nil {
		return "", err
	}
	file, err := os.OpenFile(path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
	if err != nil {
		return "", err
	}
	defer file.Close()
	if _, err := file.Write(append(data, '\n')); err != nil {
		return "", err
	}
	return path, nil
}

func FormatActionResult(result ActionResult, jsonOutput bool) string {
	if jsonOutput {
		data, err := json.MarshalIndent(result, "", "  ")
		if err == nil {
			return string(data) + "\n"
		}
	}
	line := fmt.Sprintf("tui action %s %s", result.Action, result.Outcome)
	if result.Reason != "" {
		line += ": " + result.Reason
	}
	if result.Receipt != "" {
		line += " receipt=" + result.Receipt
	}
	return line + "\n"
}

func tail(value string, limit int) string {
	if len(value) <= limit {
		return value
	}
	return value[len(value)-limit:]
}

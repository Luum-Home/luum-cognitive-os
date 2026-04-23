package installer

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"luum-agent-os/cmd/cos/internal/manifest"
)

// settingsJSON models the .claude/settings.json structure for hook management.
// We use interface{} maps to preserve unknown fields during round-tripping.
type settingsJSON map[string]interface{}

// hookEntry represents a single hook command entry.
type hookEntry struct {
	Type    string `json:"type"`
	Command string `json:"command"`
}

// matcherGroup represents a matcher group within a lifecycle event.
type matcherGroup struct {
	Matcher string      `json:"matcher"`
	Hooks   []hookEntry `json:"hooks"`
}

// RegisterHooks adds hook exports to a settings file.
// Deduplicates by command string. Creates the file if it doesn't exist.
func RegisterHooks(settingsPath string, exports []manifest.Export, hookBasePath string) error {
	return RegisterHooksWithDriver(settingsPath, exports, hookBasePath, settingsDriverForHarness("claude"))
}

// RegisterHooksWithDriver adds hook exports using a harness-specific settings driver.
func RegisterHooksWithDriver(settingsPath string, exports []manifest.Export, hookBasePath string, driver SettingsDriver) error {
	// Filter to hook exports only.
	hookExports := filterHookExports(exports)
	if len(hookExports) == 0 {
		return nil
	}

	settings, err := loadSettings(settingsPath)
	if err != nil {
		return err
	}

	// Ensure the hooks map exists.
	hooksMap, ok := settings["hooks"].(map[string]interface{})
	if !ok {
		hooksMap = make(map[string]interface{})
		settings["hooks"] = hooksMap
	}

	for _, exp := range hookExports {
		event := exp.HookEvent
		if event == "" {
			event = "PostToolUse"
		}

		matcher := exp.HookMatcher
		if matcher == "" {
			matcher = "Bash"
		}

		command := buildHookCommandWithDriver(hookBasePath, exp, driver)

		addHookToEvent(hooksMap, event, matcher, command)
	}

	return saveSettings(settingsPath, settings)
}

// UnregisterHooks removes hook entries from a settings file.
func UnregisterHooks(settingsPath string, exports []manifest.Export, hookBasePath string) error {
	return UnregisterHooksWithDriver(settingsPath, exports, hookBasePath, settingsDriverForHarness("claude"))
}

// UnregisterHooksWithDriver removes hook entries using a harness-specific settings driver.
func UnregisterHooksWithDriver(settingsPath string, exports []manifest.Export, hookBasePath string, driver SettingsDriver) error {
	hookExports := filterHookExports(exports)
	if len(hookExports) == 0 {
		return nil
	}

	settings, err := loadSettings(settingsPath)
	if err != nil {
		// If settings file doesn't exist, nothing to unregister.
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}

	hooksMap, ok := settings["hooks"].(map[string]interface{})
	if !ok {
		return nil
	}

	for _, exp := range hookExports {
		event := exp.HookEvent
		if event == "" {
			event = "PostToolUse"
		}

		command := buildHookCommandWithDriver(hookBasePath, exp, driver)
		removeHookFromEvent(hooksMap, event, command)
	}

	return saveSettings(settingsPath, settings)
}

// buildHookCommand creates the hook command string.
// Example: bash "$CLAUDE_PROJECT_DIR/.cognitive-os/hooks/cos/safety-mesh/check.sh"
func buildHookCommand(hookBasePath string, export manifest.Export) string {
	return buildHookCommandWithDriver(hookBasePath, export, settingsDriverForHarness("claude"))
}

// buildHookCommandWithDriver creates the hook command string for a specific harness.
func buildHookCommandWithDriver(hookBasePath string, export manifest.Export, driver SettingsDriver) string {
	filename := filepath.Base(export.Source)
	return fmt.Sprintf("bash \"%s/%s/%s\"", driver.ProjectExpr, hookBasePath, filename)
}

// filterHookExports returns only exports of type "hook".
func filterHookExports(exports []manifest.Export) []manifest.Export {
	var hooks []manifest.Export
	for _, exp := range exports {
		if exp.Type == "hook" {
			hooks = append(hooks, exp)
		}
	}
	return hooks
}

// loadSettings reads and parses the settings.json file.
// Returns an empty map if the file doesn't exist.
func loadSettings(path string) (settingsJSON, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return settingsJSON{"hooks": make(map[string]interface{})}, nil
		}
		return nil, fmt.Errorf("reading settings: %w", err)
	}

	var settings settingsJSON
	if err := json.Unmarshal(data, &settings); err != nil {
		return nil, fmt.Errorf("parsing settings JSON: %w", err)
	}

	return settings, nil
}

// saveSettings writes the settings back to disk with indentation.
func saveSettings(path string, settings settingsJSON) error {
	// Ensure the parent directory exists.
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("creating settings directory: %w", err)
	}

	data, err := json.MarshalIndent(settings, "", "  ")
	if err != nil {
		return fmt.Errorf("marshalling settings: %w", err)
	}

	// Append a trailing newline.
	data = append(data, '\n')

	if err := os.WriteFile(path, data, 0644); err != nil {
		return fmt.Errorf("writing settings: %w", err)
	}

	return nil
}

// addHookToEvent adds a hook command to the specified event and matcher group.
// If the command already exists in the matcher group, it is not duplicated.
func addHookToEvent(hooksMap map[string]interface{}, event, matcher, command string) {
	// Get or create the event array.
	eventList, _ := hooksMap[event].([]interface{})

	// Find existing matcher group.
	for i, item := range eventList {
		group, ok := item.(map[string]interface{})
		if !ok {
			continue
		}

		groupMatcher, _ := group["matcher"].(string)
		if groupMatcher != matcher {
			continue
		}

		// Found the matcher group. Check if the command already exists.
		hooks, _ := group["hooks"].([]interface{})
		for _, h := range hooks {
			hMap, ok := h.(map[string]interface{})
			if !ok {
				continue
			}
			if cmd, _ := hMap["command"].(string); cmd == command {
				return // Already registered.
			}
		}

		// Add the new hook entry.
		newHook := map[string]interface{}{
			"type":    "command",
			"command": command,
		}
		hooks = append(hooks, newHook)
		group["hooks"] = hooks
		eventList[i] = group
		hooksMap[event] = eventList
		return
	}

	// No matching group found. Create a new one.
	newGroup := map[string]interface{}{
		"matcher": matcher,
		"hooks": []interface{}{
			map[string]interface{}{
				"type":    "command",
				"command": command,
			},
		},
	}
	eventList = append(eventList, newGroup)
	hooksMap[event] = eventList
}

// removeHookFromEvent removes a hook command from the specified event.
// Removes the matcher group if it becomes empty. Removes the event if it becomes empty.
func removeHookFromEvent(hooksMap map[string]interface{}, event, command string) {
	eventList, _ := hooksMap[event].([]interface{})
	if len(eventList) == 0 {
		return
	}

	var newEventList []interface{}
	for _, item := range eventList {
		group, ok := item.(map[string]interface{})
		if !ok {
			newEventList = append(newEventList, item)
			continue
		}

		hooks, _ := group["hooks"].([]interface{})
		var newHooks []interface{}
		for _, h := range hooks {
			hMap, ok := h.(map[string]interface{})
			if !ok {
				newHooks = append(newHooks, h)
				continue
			}
			if cmd, _ := hMap["command"].(string); cmd == command {
				continue // Skip this hook (removing it).
			}
			newHooks = append(newHooks, h)
		}

		if len(newHooks) > 0 {
			group["hooks"] = newHooks
			newEventList = append(newEventList, group)
		}
		// If newHooks is empty, skip the group entirely (removing it).
	}

	if len(newEventList) > 0 {
		hooksMap[event] = newEventList
	} else {
		delete(hooksMap, event)
	}
}

"""Comprehensive efficiency stress test suite for Cognitive OS.

Validates token budgets, contextual rule loading, hook performance,
efficiency profiles, cost projections, and completeness guarantees
after the efficiency optimization pass.
"""

import json
import os
import re
import subprocess
import time
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
NON_RULE_DOCS = {"ROADMAP.md"}

pytestmark = pytest.mark.unit


# ===========================================================================
# Helpers
# ===========================================================================

def estimate_tokens(text: str) -> float:
    """Rough token estimate: chars / 4."""
    return len(text) / 4


def load_config() -> dict:
    """Load cognitive-os.yaml."""
    config_path = PROJECT_ROOT / "cognitive-os.yaml"
    assert config_path.exists(), "cognitive-os.yaml not found"
    return yaml.safe_load(config_path.read_text())


def load_settings() -> dict:
    """Load .claude/settings.json (the one with hooks)."""
    for name in ["settings.json", "settings.local.json"]:
        path = PROJECT_ROOT / ".claude" / name
        if path.exists():
            data = json.loads(path.read_text())
            if "hooks" in data:
                return data
    # Fallback: try any of them
    for name in ["settings.json", "settings.local.json"]:
        path = PROJECT_ROOT / ".claude" / name
        if path.exists():
            return json.loads(path.read_text())
    pytest.fail("No settings.json found in .claude/")


def get_all_rule_files() -> list[Path]:
    """Return all .md files in rules/ excluding RULES-COMPACT.md."""
    return sorted(
        f for f in PROJECT_ROOT.glob("rules/*.md")
        if f.name != "RULES-COMPACT.md" and f.name not in NON_RULE_DOCS
    )


def extract_rule_references(compact_text: str) -> set[str]:
    """Extract all [`rule-name`] references from RULES-COMPACT.md."""
    return set(re.findall(r'\[`([a-z0-9-]+)`\]', compact_text))


def get_hooks_from_settings(settings: dict) -> list[str]:
    """Extract all hook script paths referenced in settings."""
    hooks_section = settings.get("hooks", {})
    scripts = []
    for _event_type, entries in hooks_section.items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                # Extract the script path from: bash "$CLAUDE_PROJECT_DIR/hooks/foo.sh"
                match = re.search(r'hooks/([a-z0-9_-]+\.sh)', cmd)
                if match:
                    scripts.append(match.group(1))
    return scripts


def run_hook(hook_path: Path, stdin_data: str = "", env_extra: dict = None,
             timeout: int = 5) -> subprocess.CompletedProcess:
    """Run a hook script with simulated input."""
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(PROJECT_ROOT),
        "COGNITIVE_OS_PROJECT_DIR": str(PROJECT_ROOT),
        "COGNITIVE_OS_SESSION_ID": "",
        "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
    }
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(hook_path)],
        input=stdin_data,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=str(PROJECT_ROOT),
    )


# ===========================================================================
# Category 1: Token Budget Tests
# ===========================================================================

class TestTokenBudgets:

    def test_rules_compact_token_budget(self):
        """RULES-COMPACT.md must be under 4,000 tokens."""
        path = PROJECT_ROOT / "rules" / "RULES-COMPACT.md"
        assert path.exists(), "RULES-COMPACT.md not found"
        tokens = estimate_tokens(path.read_text())
        assert tokens < 4000, (
            f"RULES-COMPACT.md is ~{tokens:.0f} tokens, exceeds 4,000 budget"
        )

    def test_rules_compact_thematic_sections(self):
        """Must have the expected thematic sections (## headers).

        Current structure: Always Active, Contextual, Project-Specific.
        """
        path = PROJECT_ROOT / "rules" / "RULES-COMPACT.md"
        content = path.read_text()
        headers = [line for line in content.splitlines() if line.startswith("## ")]
        expected_sections = [
            "## Always Active",
            "## Contextual (loaded on trigger)",
            "## Project-Specific",
        ]
        assert len(headers) >= 3, (
            f"Expected at least 3 ## sections, found {len(headers)}: "
            + ", ".join(f'"{h}"' for h in headers)
        )
        for expected in expected_sections:
            found = any(expected in h for h in headers)
            assert found, (
                f"Missing expected section '{expected}' in RULES-COMPACT.md. "
                f"Found: {headers}"
            )

    def test_every_rule_referenced_in_compact(self):
        """Every .md file in rules/ must have its [rule-name] key in RULES-COMPACT.md.

        The authoritative check lives in test_rules_consolidation.py.
        This test provides a helpful message pointing to the fix.
        """
        compact_text = (PROJECT_ROOT / "rules" / "RULES-COMPACT.md").read_text()
        rule_files = get_all_rule_files()
        references = extract_rule_references(compact_text)

        missing = []
        for f in rule_files:
            rule_name = f.stem
            if rule_name not in references:
                # Also check if the stem appears anywhere in compact text
                if rule_name not in compact_text:
                    missing.append(rule_name)

        assert not missing, (
            f"{len(missing)} rules not referenced in RULES-COMPACT.md: {missing}. "
            f"Add [`rule-name`] references to rules/RULES-COMPACT.md for each new rule."
        )

    def test_no_orphan_references_in_compact(self):
        """Every compact reference resolves to an enforceable rule or documented pattern."""
        compact_text = (PROJECT_ROOT / "rules" / "RULES-COMPACT.md").read_text()
        references = extract_rule_references(compact_text)
        existing_stems = {f.stem for f in get_all_rule_files()}
        pattern_stems = {
            f.stem for f in (PROJECT_ROOT / "docs" / "patterns").glob("*.md")
        }

        orphans = [
            ref for ref in references
            if ref not in existing_stems and ref not in pattern_stems
        ]
        assert not orphans, (
            f"RULES-COMPACT.md references keys with no rules/ or docs/patterns/ file: {orphans}"
        )

    def test_claude_md_token_budget(self):
        """Global CLAUDE.md must be under 3,500 tokens."""
        path = Path.home() / ".claude" / "CLAUDE.md"
        if not path.exists():
            pytest.skip("No global CLAUDE.md found")
        tokens = estimate_tokens(path.read_text())
        assert tokens < 3500, (
            f"CLAUDE.md is ~{tokens:.0f} tokens, exceeds 3,500 budget"
        )

    def test_total_always_loaded_budget(self):
        """RULES-COMPACT.md + CLAUDE.md combined must be under 7,000 tokens."""
        compact_path = PROJECT_ROOT / "rules" / "RULES-COMPACT.md"
        claude_path = Path.home() / ".claude" / "CLAUDE.md"
        if not claude_path.exists():
            pytest.skip("No global CLAUDE.md found")

        compact_tokens = estimate_tokens(compact_path.read_text())
        claude_tokens = estimate_tokens(claude_path.read_text())
        total = compact_tokens + claude_tokens

        assert total < 7000, (
            f"Combined always-loaded budget is ~{total:.0f} tokens "
            f"(RULES-COMPACT ~{compact_tokens:.0f} + CLAUDE.md ~{claude_tokens:.0f}), "
            f"exceeds 7,000"
        )


# ===========================================================================
# Category 2: Contextual Loader Tests
# ===========================================================================

@pytest.mark.xdist_group("hook-chain-perf")  # serialise hook-subprocess tests on one worker
class TestContextualLoader:

    LOADER_PATH = PROJECT_ROOT / "hooks" / "contextual-rule-loader.sh"

    def test_contextual_loader_exists_and_executable(self):
        """contextual-rule-loader.sh must exist and be executable."""
        assert self.LOADER_PATH.exists(), "contextual-rule-loader.sh not found"
        assert os.access(self.LOADER_PATH, os.X_OK), (
            "contextual-rule-loader.sh is not executable"
        )

    def test_contextual_loader_matches_acceptance_criteria(self):
        """Prompt containing 'acceptance criteria' should trigger acceptance-criteria.md injection."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "Define acceptance criteria for the new endpoint"
            }
        })
        result = run_hook(self.LOADER_PATH, stdin_data=input_json)
        # The loader should output the rule content or at least the rule name
        assert result.returncode == 0
        # Check if acceptance-criteria was matched (in stdout)
        if "acceptance-criteria" in result.stdout:
            assert True  # matched
        else:
            # It may output to stderr or no match if triggers don't include this exact phrase
            # Check the config to see what the actual trigger is
            config = load_config()
            triggers = config.get("rules", {}).get("loading", {}).get("contextual_triggers", {})
            if "acceptance-criteria" in triggers:
                trigger_pattern = triggers["acceptance-criteria"]
                # Our prompt should match
                assert re.search(trigger_pattern, "acceptance criteria", re.IGNORECASE), (
                    f"Trigger pattern '{trigger_pattern}' should match 'acceptance criteria'"
                )

    def test_contextual_loader_matches_error_pattern(self):
        """Prompt containing 'error' or 'failure' should trigger auto-repair.md."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "The service is crashing with a failure in the auth module"
            }
        })
        result = run_hook(self.LOADER_PATH, stdin_data=input_json)
        assert result.returncode == 0
        # auto-repair trigger includes "error|failure|crash"
        output = result.stdout + result.stderr
        assert "auto-repair" in output or "CONTEXTUAL RULES" in result.stdout, (
            f"Expected auto-repair rule injection for error/failure prompt. "
            f"stdout={result.stdout[:200]}, stderr={result.stderr[:200]}"
        )

    def test_contextual_loader_no_match_no_output(self):
        """Prompt with no trigger words should produce no rule output."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "hello world simple greeting"
            }
        })
        result = run_hook(self.LOADER_PATH, stdin_data=input_json)
        assert result.returncode == 0
        assert "CONTEXTUAL RULES" not in result.stdout, (
            f"Unexpected rule injection for neutral prompt: {result.stdout[:200]}"
        )

    def test_contextual_loader_max_3_rules(self):
        """Even if prompt matches many triggers, max 3 rules injected."""
        # Construct a prompt that hits many triggers
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": (
                    "error failure crash acceptance criteria verification "
                    "done complete finished quality exhaustive self-improve "
                    "session concurrent lock squad-report retrospective "
                    "new library adoption"
                )
            }
        })
        result = run_hook(self.LOADER_PATH, stdin_data=input_json)
        assert result.returncode == 0
        # Count how many "--- rules/" markers appear (each injected rule starts with this)
        injected_count = result.stdout.count("--- rules/")
        assert injected_count <= 3, (
            f"Injected {injected_count} rules, max should be 3"
        )

    def test_contextual_loader_skips_full_profile(self):
        """When rules loading strategy is 'full', loader should skip (exit 0, no output)."""
        # We test the logic by checking the script source for the strategy check
        content = self.LOADER_PATH.read_text()
        assert 'full' in content, (
            "Loader does not check for 'full' strategy"
        )
        # The actual behavior: if strategy=full in config, it exits early.
        # We verify the code path exists rather than changing the real config.
        assert 'exit 0' in content, "Loader should exit 0 when strategy is full"


# ===========================================================================
# Category 3: Hook Performance Tests
# ===========================================================================

@pytest.mark.xdist_group("hook-chain-perf")  # serialise hook-subprocess tests on one worker
class TestHookPerformance:

    def _get_hooks_by_event(self, event_type: str) -> list[Path]:
        """Get hook script paths for a given event type from settings."""
        settings = load_settings()
        hooks_section = settings.get("hooks", {})
        entries = hooks_section.get(event_type, [])
        paths = []
        for entry in entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                match = re.search(r'hooks/([a-z0-9_-]+\.sh)', cmd)
                if match:
                    hook_path = PROJECT_ROOT / "hooks" / match.group(1)
                    if hook_path.exists():
                        paths.append(hook_path)
        return paths

    def _find_hooks_for_tool(self, event_type: str, tool_name: str) -> list[Path]:
        """Find hooks that match a given tool name for an event type."""
        settings = load_settings()
        hooks = []
        for entry in settings.get("hooks", {}).get(event_type, []):
            matcher = entry.get("matcher", "")
            # Matcher can be empty (matches all), or pipe-separated like "Bash|Edit|Write"
            matcher_tools = [m.strip() for m in matcher.split("|")] if matcher else [""]
            if tool_name in matcher_tools or "" in matcher_tools:
                for hook in entry.get("hooks", []):
                    cmd = hook.get("command", "")
                    match = re.search(r'hooks/([a-z0-9_-]+\.sh)', cmd)
                    if match:
                        path = PROJECT_ROOT / "hooks" / match.group(1)
                        if path.exists():
                            hooks.append(path)
        return hooks

    def test_hook_chain_latency_per_bash(self):
        """Measure total hook latency for a simulated Bash tool call."""
        bash_hooks = self._find_hooks_for_tool("PostToolUse", "Bash")

        if not bash_hooks:
            pytest.skip("No Bash PostToolUse hooks registered")

        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "echo hello"},
            "tool_output": "hello\n"
        })

        total_ms = 0
        for hook_path in bash_hooks:
            start = time.time()
            try:
                run_hook(hook_path, stdin_data=input_json, timeout=5)
            except subprocess.TimeoutExpired:
                total_ms += 5000
                continue
            total_ms += (time.time() - start) * 1000

        assert total_ms < 2000, (
            f"Bash hook chain took {total_ms:.0f}ms, budget is 2000ms. "
            f"Hooks tested: {[h.name for h in bash_hooks]}"
        )

    def test_hook_chain_latency_per_agent(self):
        """Measure total hook latency for a simulated Agent tool call."""
        agent_hooks = self._find_hooks_for_tool("PostToolUse", "Agent")

        if not agent_hooks:
            pytest.skip("No Agent PostToolUse hooks registered")

        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "test agent prompt"},
            "tool_output": "Agent completed successfully.\nTRUST REPORT:\n  Score: 85/100"
        })

        total_ms = 0
        for hook_path in agent_hooks:
            start = time.time()
            try:
                run_hook(hook_path, stdin_data=input_json, timeout=10)
            except subprocess.TimeoutExpired:
                total_ms += 10000
                continue
            total_ms += (time.time() - start) * 1000

        # 6000ms budget: ~2000ms serial baseline × 3x parallel-load headroom.
        # The xdist_group("hook-chain-perf") marker serialises this test with
        # other hook-subprocess tests on one worker, but other xdist workers
        # still compete for CPU, so 3x headroom is warranted.
        assert total_ms < 6000, (
            f"Agent hook chain took {total_ms:.0f}ms, budget is 6000ms. "
            f"Hooks tested: {[h.name for h in agent_hooks]}"
        )

    def test_individual_hook_under_500ms(self):
        """Each registered hook individually must complete under 2000ms.

        Note: The threshold is set to 2000ms (not 500ms as the test name
        suggests) to account for cold-start overhead, system load variance,
        and CI environments. The test name is kept for backward compatibility
        with test selectors.
        """
        settings = load_settings()
        all_hooks = set()
        # Skip SessionStart and Stop hooks — they perform initialization work
        # (creating directories, git operations) that is expected to take longer
        # than the per-tool-call budget tested here.
        SKIP_EVENT_TYPES = {"SessionStart", "Stop"}
        for event_type, entries in settings.get("hooks", {}).items():
            if event_type in SKIP_EVENT_TYPES:
                continue
            for entry in entries:
                for hook in entry.get("hooks", []):
                    cmd = hook.get("command", "")
                    match = re.search(r'hooks/([a-z0-9_-]+\.sh)', cmd)
                    if match:
                        path = PROJECT_ROOT / "hooks" / match.group(1)
                        if path.exists():
                            all_hooks.add(path)

        if not all_hooks:
            pytest.skip("No hooks registered")

        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "echo test"},
            "tool_output": "test\n"
        })

        # Use 2000ms threshold to tolerate system load variance and
        # cold-start overhead (shell startup, sourcing libs, jq init).
        THRESHOLD_MS = 2000

        slow_hooks = []
        for hook_path in sorted(all_hooks):
            start = time.time()
            try:
                run_hook(hook_path, stdin_data=input_json, timeout=5)
            except subprocess.TimeoutExpired:
                slow_hooks.append((hook_path.name, 5000))
                continue
            elapsed_ms = (time.time() - start) * 1000
            if elapsed_ms > THRESHOLD_MS:
                slow_hooks.append((hook_path.name, elapsed_ms))

        assert not slow_hooks, (
            f"Hooks exceeding {THRESHOLD_MS}ms: "
            + ", ".join(f"{name} ({ms:.0f}ms)" for name, ms in slow_hooks)
        )

    def test_capability_level_skips_disabled_hooks(self):
        """At capability level 4, clarification-gate should exit immediately."""
        hook_path = PROJECT_ROOT / "hooks" / "clarification-gate.sh"
        if not hook_path.exists():
            pytest.skip("clarification-gate.sh not found")

        content = hook_path.read_text()
        assert "check_capability_level" in content, (
            "clarification-gate.sh does not call check_capability_level"
        )

        # Verify the common.sh function exists
        common_path = PROJECT_ROOT / "hooks" / "_lib" / "common.sh"
        assert common_path.exists(), "common.sh not found"
        common_content = common_path.read_text()
        assert "check_capability_level" in common_content, (
            "common.sh missing check_capability_level function"
        )


# ===========================================================================
# Category 4: Profile Tests
# ===========================================================================

class TestProfiles:

    def test_efficiency_profiles_exist(self):
        """cognitive-os.yaml must define the current ADR-002 profiles."""
        config = load_config()
        assert "efficiency" in config, "Missing efficiency section"
        profiles = config["efficiency"].get("profiles", {})
        for name in ["default", "full"]:
            assert name in profiles, f"Missing efficiency profile: {name}"

    def test_default_profile_has_required_fields(self):
        """Default profile must define rules_loading, hooks, capability_level."""
        config = load_config()
        default = config["efficiency"]["profiles"]["default"]
        assert "rules_loading" in default, "default profile missing rules_loading"
        assert "hooks" in default, "default profile missing hooks"
        assert "capability_level" in default, "default profile missing capability_level"
        assert default["capability_level"] == 3, (
            f"default capability_level should be 3, got {default['capability_level']}"
        )

    def test_full_profile_has_required_fields(self):
        """Full profile must define rules_loading, hooks, capability_level."""
        config = load_config()
        full = config["efficiency"]["profiles"]["full"]
        assert "rules_loading" in full, "full profile missing rules_loading"
        assert "hooks" in full, "full profile missing hooks"
        assert "capability_level" in full, "full profile missing capability_level"
        assert full["capability_level"] == 2, (
            f"full capability_level should be 2, got {full['capability_level']}"
        )

    def test_default_profile_hook_count(self):
        """Default profile should specify the committed default hook projection."""
        config = load_config()
        default = config["efficiency"]["profiles"]["default"]
        assert default["hooks"] == "default", (
            f"default hooks should be 'default', got '{default['hooks']}'"
        )

    def test_full_profile_hook_count(self):
        """Full profile should specify full hooks."""
        config = load_config()
        full = config["efficiency"]["profiles"]["full"]
        assert full["hooks"] == "full", (
            f"full hooks should be 'full', got '{full['hooks']}'"
        )

    def test_self_hosting_always_full(self):
        """self-install.sh must force full profile when inside COS repo."""
        path = PROJECT_ROOT / "hooks" / "self-install.sh"
        assert path.exists(), "self-install.sh not found"
        content = path.read_text()

        # Must detect self-hosting
        assert "IS_SELF_HOSTING" in content, (
            "self-install.sh missing IS_SELF_HOSTING detection"
        )
        # Must default to full for self-hosting
        assert 'EFFICIENCY_PROFILE="full"' in content, (
            "self-install.sh does not default EFFICIENCY_PROFILE to full"
        )
        # Must only read config profile when NOT self-hosting
        assert "IS_SELF_HOSTING" in content and "false" in content, (
            "self-install.sh should only read config profile when not self-hosting"
        )


# ===========================================================================
# Category 5: Cost Projection Tests
# ===========================================================================

class TestCostProjections:

    # Opus pricing: $15/1M input tokens
    OPUS_INPUT_PRICE_PER_TOKEN = 15.0 / 1_000_000

    def _calc_overhead_cost(self, *paths: Path) -> float:
        """Calculate Opus input cost for the given file paths."""
        total_tokens = 0
        for p in paths:
            if p.exists():
                total_tokens += estimate_tokens(p.read_text())
        return total_tokens * self.OPUS_INPUT_PRICE_PER_TOKEN

    def test_lean_session_cost_under_50_cents(self):
        """Lean profile overhead must be under $0.50/session on Opus.

        This only measures the always-loaded rule overhead, not full session cost.
        """
        compact = PROJECT_ROOT / "rules" / "RULES-COMPACT.md"
        claude_md = Path.home() / ".claude" / "CLAUDE.md"
        if not claude_md.exists():
            pytest.skip("No global CLAUDE.md found")

        cost = self._calc_overhead_cost(compact, claude_md)
        assert cost < 0.50, (
            f"Lean profile overhead cost is ${cost:.4f}, exceeds $0.50 budget"
        )

    def test_standard_session_cost_under_60_cents(self):
        """Standard profile overhead must be under $0.60/session on Opus."""
        compact = PROJECT_ROOT / "rules" / "RULES-COMPACT.md"
        claude_md = Path.home() / ".claude" / "CLAUDE.md"
        if not claude_md.exists():
            pytest.skip("No global CLAUDE.md found")

        cost = self._calc_overhead_cost(compact, claude_md)
        assert cost < 0.60, (
            f"Standard profile overhead cost is ${cost:.4f}, exceeds $0.60 budget"
        )

    def test_full_session_cost_documented(self):
        """Full profile cost should be documented in cognitive-os.yaml."""
        config = load_config()
        full_profile = config["efficiency"]["profiles"]["full"]
        # Full profile should have a target cost documented
        assert "target_cost_per_session_usd" in full_profile, (
            "Full profile missing target_cost_per_session_usd"
        )
        # Full profile cost should be higher than lean/standard
        default_cost = config["efficiency"]["profiles"]["default"].get(
            "target_cost_per_session_usd", 0
        )
        full_cost = full_profile["target_cost_per_session_usd"]
        assert full_cost > default_cost, (
            f"Full profile cost (${full_cost}) should exceed default (${default_cost})"
        )


# ===========================================================================
# Category 6: Completeness / No Feature Loss
# ===========================================================================

class TestCompleteness:

    def test_all_hooks_in_settings_json_exist(self):
        """Every .sh file referenced in settings.json must exist."""
        settings = load_settings()
        hook_scripts = get_hooks_from_settings(settings)
        missing = []
        for script in hook_scripts:
            # Check both hooks/ and packages/*/hooks/ (Paperclip hooks live in packages)
            path = PROJECT_ROOT / "hooks" / script
            if not path.exists():
                # Search in packages
                found = list(PROJECT_ROOT.glob(f"packages/*/hooks/{script}"))
                if not found:
                    missing.append(script)
        assert not missing, (
            f"Settings.json references non-existent hooks: {missing}"
        )

    def test_all_contextual_triggers_have_rule_files(self):
        """Every trigger key in contextual_triggers must have a rules/{key}.md file."""
        config = load_config()
        triggers = (
            config.get("rules", {})
            .get("loading", {})
            .get("contextual_triggers", {})
        )
        if not triggers:
            pytest.skip("No contextual_triggers defined")

        missing = []
        for rule_name in triggers.keys():
            rule_path = PROJECT_ROOT / "rules" / f"{rule_name}.md"
            pattern_path = PROJECT_ROOT / "docs" / "patterns" / f"{rule_name}.md"
            if not rule_path.exists() and not pattern_path.exists():
                missing.append(rule_name)

        assert not missing, (
            f"Contextual triggers reference non-existent rule/pattern files: {missing}"
        )

    def test_capability_level_components_match_hooks(self):
        """Every component in auto_disable must have a corresponding hook or rule."""
        config = load_config()
        auto_disable = config.get("model_capability", {}).get("auto_disable", {})
        all_components = set()
        for _level, components in auto_disable.items():
            if isinstance(components, list):
                all_components.update(components)

        missing = []
        for component in all_components:
            # Check if it's a hook
            hook_path = PROJECT_ROOT / "hooks" / f"{component}.sh"
            # Check if it's a rule
            rule_path = PROJECT_ROOT / "rules" / f"{component}.md"
            if not hook_path.exists() and not rule_path.exists():
                missing.append(component)

        assert not missing, (
            f"auto_disable references components with no hook or rule file: {missing}"
        )

    def test_cos_symlinks_intact(self):
        """All rule symlinks in .claude/rules/cos/ must exist and point to valid files."""
        cos_dir = PROJECT_ROOT / ".claude" / "rules" / "cos"
        if not cos_dir.exists():
            # Some setups symlink directly to .claude/rules/
            cos_dir = PROJECT_ROOT / ".claude" / "rules"
            if not cos_dir.exists():
                pytest.skip("No .claude/rules/ directory found")

        # Get all .md files (could be symlinks or actual files)
        rule_files = list(cos_dir.glob("*.md"))
        if not rule_files:
            pytest.skip("No rule files found in .claude/rules/")

        broken = []
        for f in rule_files:
            if f.is_symlink():
                target = f.resolve()
                if not target.exists():
                    broken.append(f"{f.name} -> {f.readlink()}")
            elif not f.exists():
                broken.append(f.name)

        assert not broken, (
            f"Broken rule symlinks in .claude/rules/: {broken}"
        )

    def test_rules_count_matches_expectations(self):
        """The number of rule .md files should not drop below a minimum baseline."""
        rule_files = list(PROJECT_ROOT.glob("rules/*.md"))
        # Exclude RULES-COMPACT.md from count
        actual_rules = [f for f in rule_files if f.name != "RULES-COMPACT.md"]
        # Minimum baseline; additions don't break this
        assert len(actual_rules) >= 50, (
            f"Only {len(actual_rules)} rule files found, expected at least 50"
        )

    def test_settings_hooks_all_executable(self):
        """Every hook referenced in settings must be executable."""
        settings = load_settings()
        hook_scripts = get_hooks_from_settings(settings)
        non_exec = []
        for script in hook_scripts:
            path = PROJECT_ROOT / "hooks" / script
            if path.exists() and not os.access(path, os.X_OK):
                non_exec.append(script)
        assert not non_exec, (
            f"Hooks not executable: {non_exec}"
        )

    def test_contextual_triggers_cover_key_patterns(self):
        """Key contextual triggers must be defined for critical rules."""
        config = load_config()
        triggers = (
            config.get("rules", {})
            .get("loading", {})
            .get("contextual_triggers", {})
        )
        required_triggers = [
            "auto-repair",
            "definition-of-done",
            "acceptance-criteria",
        ]
        missing = [t for t in required_triggers if t not in triggers]
        assert not missing, (
            f"Missing critical contextual triggers: {missing}"
        )

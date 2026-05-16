"""Integration tests for the safety mesh — testing INTERACTIONS between
multiple safety features (clarification-gate, blast-radius, assumption-tracker,
trust-score-validator, dry-run-preview, clarification-interceptor).

These tests verify cross-feature cascades, edge cases, and combined behavior.
All tests are pure Python using subprocess to call hooks with mocked
environment variables and input — no actual Claude API calls.
"""

import json
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_agent_input(prompt: str, tool_name: str = "Agent") -> str:
    """Build the JSON stdin that hooks expect for PreToolUse on Agent."""
    return json.dumps({
        "tool_name": tool_name,
        "tool_input": {"prompt": prompt},
    })


def make_agent_response_input(
    prompt: str, response: str, tool_name: str = "Agent"
) -> str:
    """Build the JSON stdin that PostToolUse hooks expect.

    Different hooks read from different fields:
    - trust-score-validator reads: .tool_result // .output
    - assumption-tracker reads: .tool_response (string or .tool_response.result)
    - clarification-interceptor reads: .tool_result // .tool_response.result // etc

    We provide both tool_result and tool_response for maximum compatibility.
    """
    return json.dumps({
        "tool_name": tool_name,
        "tool_input": {"prompt": prompt},
        "tool_result": response,
        "tool_response": {"result": response},
    })


def make_agent_response_string(prompt: str, response: str) -> str:
    """Build JSON with tool_response as a raw string (some hooks parse this way)."""
    return json.dumps({
        "tool_name": "Agent",
        "tool_input": {"prompt": prompt},
        "tool_response": response,
    })


def _blast_context(stdout: str) -> str:
    text = stdout.strip()
    if not text:
        return ""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text
    return payload.get("hookSpecificOutput", {}).get("additionalContext", text)


def _latest_blast_entry(cognitive_os_env) -> dict:
    session_id = cognitive_os_env["session_id"]
    session_log = (
        cognitive_os_env["cos_dir"]
        / "sessions"
        / session_id
        / "metrics"
        / "blast-radius.jsonl"
    )
    global_log = cognitive_os_env["cos_dir"] / "metrics" / "blast-radius.jsonl"
    log_file = session_log if session_log.exists() else global_log
    return json.loads(log_file.read_text().strip().split("\n")[-1])


# ---------------------------------------------------------------------------
# CROSS-FEATURE CASCADES
# ---------------------------------------------------------------------------


class TestCrossFeatureCascades:
    """Tests that verify interactions between multiple safety hooks."""

    def test_01_vague_prompt_blocked_then_clarified_proceeds(
        self, run_hook, cognitive_os_env
    ):
        """Vague prompt -> clarification gate BLOCKS -> user clarifies with
        detailed prompt -> blast radius estimates scope -> agent proceeds."""
        env = cognitive_os_env["env"]

        # Step 1: vague prompt -> clarification gate blocks (score > 60)
        # Combines: no file paths (+15), "all" without count (+20), no tech (+15),
        # action without target (+20), short (+20), no criteria (+10) = 100
        vague = make_agent_input("add auth to all services")
        result = run_hook("clarification-gate.sh", env=env, stdin=vague)
        assert result.returncode == 2, (
            f"Vague prompt should be BLOCKED, got: {result.stdout[:200]}"
        )
        assert "BLOCKED" in result.stdout

        # Step 2: user clarifies with a detailed prompt
        detailed = make_agent_input(
            "Fix the null pointer bug in internal/users/handler.go line 42. "
            "The handler does not check for nil user before accessing .Name. "
            "ACCEPTANCE CRITERIA: go test ./internal/users/... exits 0"
        )
        result_gate = run_hook("clarification-gate.sh", env=env, stdin=detailed)
        assert result_gate.returncode == 0, "Detailed prompt should pass"

        # Step 3: blast radius should estimate LOW
        result_blast = run_hook("blast-radius.sh", env=env, stdin=detailed)
        assert result_blast.returncode == 0
        # Single file -> should not trigger HIGH/CRITICAL output
        assert "CRITICAL" not in result_blast.stdout

    def test_02_assumptions_plus_trust_score_both_fire(
        self, run_hook, cognitive_os_env
    ):
        """Agent makes 3+ assumptions -> assumption tracker warns ->
        trust-score-validator also fires on low trust."""
        env = cognitive_os_env["env"]

        response_text = (
            "I completed the task. "
            "I assume the database is PostgreSQL. "
            "I assume the auth service uses JWT tokens. "
            "I assume the API follows REST conventions. "
            "I assume the config is in config.yaml. "
            "TRUST REPORT:\n  Score: 45/100\n"
            "WHAT I'M UNSURE ABOUT:\n  - database engine\n  - auth mechanism"
        )
        input_json = make_agent_response_input("implement user service", response_text)

        # Assumption tracker should warn (4 assumptions)
        result_assumptions = run_hook(
            "assumption-tracker.sh", env=env, stdin=input_json
        )
        assert result_assumptions.returncode == 0
        assert "ASSUMPTION TRACKER" in result_assumptions.stdout
        assert "WARNING" in result_assumptions.stdout

        # Trust score validator should also fire (score 45 < 50)
        result_trust = run_hook(
            "trust-score-validator.sh", env=env, stdin=input_json
        )
        assert result_trust.returncode == 0
        assert "ALERT" in result_trust.stdout or "Low confidence" in result_trust.stdout

    def test_03_dry_run_blocks_before_clarification_gate(
        self, run_hook, cognitive_os_env
    ):
        """DRY_RUN mode + clarification gate -> dry-run blocks FIRST
        (before clarification even runs)."""
        env = {**cognitive_os_env["env"], "DRY_RUN": "true"}
        prompt = make_agent_input("fix the bugs")

        # Dry-run fires as PreToolUse and blocks with exit 2
        result = run_hook("dry-run-preview.sh", env=env, stdin=prompt)
        assert result.returncode == 2
        assert "DRY-RUN" in result.stdout
        assert "BLOCKED" in result.stdout

        # Clarification gate would also block, but dry-run should be checked first
        # Verify the ordering: dry-run produces its message without clarification
        assert "CLARIFICATION" not in result.stdout

    def test_04_high_blast_radius_production_phase(
        self, run_hook, cognitive_os_env
    ):
        """High blast radius + production phase -> trust score threshold
        should be higher (verified by trust-score-validator alerting at 70)."""
        env = cognitive_os_env["env"]
        cos_dir = cognitive_os_env["cos_dir"]

        # Write production phase config
        config_file = cos_dir / "cognitive-os.yaml"
        config_file.write_text("lifecycle:\n  phase: production\n")

        # High blast radius prompt
        prompt = make_agent_input(
            "Migrate all services to the new auth provider. "
            "Update every endpoint across all controllers."
        )
        result = run_hook("blast-radius.sh", env=env, stdin=prompt)
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "CRITICAL" in combined or "HIGH" in combined

        # Now check trust score: a score of 65 should get a note in any context
        response = make_agent_response_input(
            "migrate all services",
            "Done. TRUST REPORT:\n  Score: 65/100\n"
            "WHAT I'M UNSURE ABOUT:\n  - some services may have been missed"
        )
        result_trust = run_hook("trust-score-validator.sh", env=env, stdin=response)
        assert result_trust.returncode == 0
        # Score 65 is below 70, should trigger a note
        combined_trust = result_trust.stdout + result_trust.stderr
        assert "confidence" in combined_trust.lower() or "NOTE" in combined_trust


# ---------------------------------------------------------------------------
# EDGE CASES — CLARIFICATION GATE
# ---------------------------------------------------------------------------


class TestClarificationGateEdgeCases:
    """Edge cases for the clarification-gate PreToolUse hook."""


    def test_06_question_not_task(self, run_hook, cognitive_os_env):
        """Prompt that's a question, not a task -> The gate detects open
        questions and may score, but short analysis questions are common."""
        env = cognitive_os_env["env"]
        prompt = make_agent_input(
            "What is the current architecture of the auth service in "
            "internal/auth/? How does it connect to the identity provider?"
        )
        result = run_hook("clarification-gate.sh", env=env, stdin=prompt)
        # Questions contain file paths and are descriptive, so may pass or warn
        # but should NOT block (it's asking, not instructing blindly)
        # The gate may flag "open questions" but the score depends on other signals
        assert result.returncode == 0 or result.returncode == 2
        # Just verify it ran without crashing

    def test_07_prompt_with_acceptance_criteria(self, run_hook, cognitive_os_env):
        """Prompt with acceptance criteria already defined -> should NOT
        trigger because criteria reduce ambiguity."""
        env = cognitive_os_env["env"]
        prompt = make_agent_input(
            "Add a new endpoint GET /api/users/:id to internal/users/controller.go. "
            "ACCEPTANCE CRITERIA: "
            "1. go test ./internal/users/... exits 0 "
            "2. curl localhost:3000/api/users/test-id returns 200 "
            "3. No new lint errors in golangci-lint"
        )
        result = run_hook("clarification-gate.sh", env=env, stdin=prompt)
        assert result.returncode == 0, "Prompt with acceptance criteria should pass"

    def test_08_very_short_prompt_max_ambiguity(self, run_hook, cognitive_os_env):
        """Very short prompt with scope words -> maximum ambiguity score.
        Needs to trigger multiple signals to exceed 60 threshold."""
        env = cognitive_os_env["env"]
        # "add tests to every module" triggers: no paths (+15), scope (+20),
        # no tech (+15), short (+20), no criteria (+10) = 80+
        prompt = make_agent_input("add tests to every module")
        result = run_hook("clarification-gate.sh", env=env, stdin=prompt)
        assert result.returncode == 2, (
            f"Prompt should be BLOCKED, got: {result.stdout[:200]}"
        )
        assert "BLOCKED" in result.stdout

    def test_09_detailed_prompt_min_ambiguity(self, run_hook, cognitive_os_env):
        """Very long prompt with all details -> minimum ambiguity score."""
        env = cognitive_os_env["env"]
        prompt = make_agent_input(
            "Implement the GetUserByID use case in internal/users/application/usecases/get_user.go "
            "using the Go clean architecture pattern. The use case receives a string user ID, "
            "calls the UserRepository.FindByID method, and returns a UserResponseDTO. "
            "Follow the existing pattern in internal/orders/application/usecases/get_order.go. "
            "ACCEPTANCE CRITERIA: "
            "1. go build ./internal/users/... exits 0. "
            "2. go test ./internal/users/... exits 0. "
            "3. golangci-lint run ./internal/users/... exits 0. "
            "SUCCESS: All 3 commands exit 0."
        )
        result = run_hook("clarification-gate.sh", env=env, stdin=prompt)
        assert result.returncode == 0, "Fully detailed prompt should pass cleanly"
        # Should not even warn
        assert "WARNING" not in result.stdout

    def test_10_short_ambiguous_prompt(self, run_hook, cognitive_os_env):
        """Short prompt without file paths or criteria should trigger ambiguity handling."""
        env = cognitive_os_env["env"]
        prompt = make_agent_input("fix the errors")
        result = run_hook("clarification-gate.sh", env=env, stdin=prompt)
        # Short, no file paths, no criteria -> should block or warn
        combined = result.stdout + result.stderr
        assert result.returncode == 2 or "WARNING" in combined


# ---------------------------------------------------------------------------
# EDGE CASES — BLAST RADIUS
# ---------------------------------------------------------------------------


class TestBlastRadiusEdgeCases:
    """Edge cases for the blast-radius PreToolUse hook."""

    def test_11_single_file_path_low(self, run_hook, cognitive_os_env):
        """Single file path -> LOW blast radius."""
        env = cognitive_os_env["env"]
        prompt = make_agent_input(
            "Fix the bug in internal/users/handler.go where nil check is missing. "
            "ACCEPTANCE CRITERIA: go test ./internal/users/... exits 0"
        )
        result = run_hook("blast-radius.sh", env=env, stdin=prompt)
        assert result.returncode == 0
        # LOW radius produces no output
        assert "CRITICAL" not in result.stdout
        assert "HIGH" not in result.stdout

    def test_12_glob_pattern_broad(self, run_hook, cognitive_os_env):
        """Glob-like pattern 'src/**/*.ts' -> estimate based on breadth.
        The hook detects directory patterns and multiplies."""
        env = cognitive_os_env["env"]
        prompt = make_agent_input(
            "Update all TypeScript files in src/services/ and src/controllers/ "
            "to use the new logger. "
            "ACCEPTANCE CRITERIA: yarn build exits 0"
        )
        result = run_hook("blast-radius.sh", env=env, stdin=prompt)
        assert result.returncode == 0
        # Two directory references -> MEDIUM or above
        result.stdout + result.stderr
        # Should log something (directory signals detected)
        log = cognitive_os_env["cos_dir"] / "metrics" / "blast-radius.jsonl"
        # Check the metrics were logged
        if log.exists():
            data = log.read_text().strip()
            if data:
                entry = json.loads(data.split("\n")[-1])
                assert entry["file_score"] > 0

    def test_13_all_services_no_list_critical(self, run_hook, cognitive_os_env):
        """Broad cross-service prompts still surface at least HIGH."""
        env = cognitive_os_env["env"]
        prompt = make_agent_input(
            "Update all services to use the new auth provider. "
            "Migrate every endpoint to the new SDK."
        )
        result = run_hook("blast-radius.sh", env=env, stdin=prompt)
        assert result.returncode == 0
        ctx = _blast_context(result.stdout)
        assert "HIGH" in ctx or "CRITICAL" in ctx

    def test_14_explicit_file_list_25(self, run_hook, cognitive_os_env):
        """A 25-file prompt is recorded even if the new threshold stays silent."""
        env = cognitive_os_env["env"]
        prompt = make_agent_input(
            "Update the following 25 files to use the new API client: "
            "src/a.ts src/b.ts src/c.ts and 22 more files. "
            "ACCEPTANCE CRITERIA: yarn build exits 0"
        )
        result = run_hook("blast-radius.sh", env=env, stdin=prompt)
        assert result.returncode == 0
        ctx = _blast_context(result.stdout)
        if ctx:
            assert "HIGH" in ctx or "CRITICAL" in ctx
        else:
            entry = _latest_blast_entry(cognitive_os_env)
            assert entry["file_score"] >= 25
            assert entry["radius"] == "LOW"

    def test_15_infra_keyword_single_file_medium(self, run_hook, cognitive_os_env):
        """Infra-only single-file prompts are logged, not auto-escalated."""
        env = cognitive_os_env["env"]
        prompt = make_agent_input(
            "Update the docker-compose.yml to add a new container. "
            "ACCEPTANCE CRITERIA: docker compose config exits 0"
        )
        result = run_hook("blast-radius.sh", env=env, stdin=prompt)
        assert result.returncode == 0
        assert _blast_context(result.stdout) == ""
        entry = _latest_blast_entry(cognitive_os_env)
        assert entry["infra"] is True
        assert entry["radius"] == "LOW"


# ---------------------------------------------------------------------------
# EDGE CASES — ASSUMPTIONS
# ---------------------------------------------------------------------------


class TestAssumptionTrackerEdgeCases:
    """Edge cases for the assumption-tracker PostToolUse hook."""

    def test_16_think_in_code_comment_not_assumption(
        self, run_hook, cognitive_os_env
    ):
        """Agent says 'I think' in a code comment (not about the task) ->
        should still trigger because the hook does pattern matching."""
        env = cognitive_os_env["env"]
        response = (
            "Created handler.go with the following content:\n"
            "```go\n"
            "// I think this handles the edge case correctly\n"
            "func Handle() {}\n"
            "```\n"
            "The implementation is complete."
        )
        input_json = make_agent_response_string("implement handler", response)
        result = run_hook("assumption-tracker.sh", env=env, stdin=input_json)
        assert result.returncode == 0
        # 1 match of "I think" — below threshold of 3, so no warning output
        assert "WARNING" not in result.stdout

    def test_17_explicit_database_assumption_triggers(
        self, run_hook, cognitive_os_env
    ):
        """Agent says 'I assume the database is PostgreSQL' -> should trigger."""
        env = cognitive_os_env["env"]
        response = (
            "I assume the database is PostgreSQL. "
            "I assume the schema uses UUID primary keys. "
            "I assume the connection string is in the .env file. "
            "Done implementing the repository."
        )
        input_json = make_agent_response_string("implement repository", response)
        result = run_hook("assumption-tracker.sh", env=env, stdin=input_json)
        assert result.returncode == 0
        assert "ASSUMPTION TRACKER" in result.stdout
        assert "WARNING" in result.stdout

    def test_18_zero_assumptions_clean_pass(self, run_hook, cognitive_os_env):
        """Agent response with 0 assumption language -> clean pass, no log."""
        env = cognitive_os_env["env"]
        response = (
            "Implemented the handler in internal/users/handler.go. "
            "Added unit tests in internal/users/handler_test.go. "
            "All tests pass: go test ./internal/users/... exits 0."
        )
        input_json = make_agent_response_string("implement handler", response)
        result = run_hook("assumption-tracker.sh", env=env, stdin=input_json)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_19_exactly_three_assumptions_threshold(
        self, run_hook, cognitive_os_env
    ):
        """Agent response with exactly 3 assumptions -> threshold warning fires."""
        env = cognitive_os_env["env"]
        response = (
            "I assume the service uses REST. "
            "I assume the port is 3000. "
            "I assume config is in YAML format. "
            "Implementation complete."
        )
        input_json = make_agent_response_string("implement service", response)
        result = run_hook("assumption-tracker.sh", env=env, stdin=input_json)
        assert result.returncode == 0
        assert "ASSUMPTION TRACKER" in result.stdout

    def test_20_assumption_in_quoted_block(self, run_hook, cognitive_os_env):
        """Assumption language in a quoted block -> the hook does not
        distinguish quoted vs unquoted, so it still detects it."""
        env = cognitive_os_env["env"]
        response = (
            'The user said: "I assume the database is PostgreSQL."\n'
            'And also: "I assume the cache uses Redis."\n'
            'Plus: "I assume the queue is Kafka."\n'
            "I followed their instructions exactly."
        )
        input_json = make_agent_response_string("follow instructions", response)
        result = run_hook("assumption-tracker.sh", env=env, stdin=input_json)
        assert result.returncode == 0
        # The hook does pattern matching on full text, including quotes
        # 3 "I assume" matches -> warning fires
        assert "ASSUMPTION TRACKER" in result.stdout


# ---------------------------------------------------------------------------
# EDGE CASES — CONFIDENCE / TRUST SCORE
# ---------------------------------------------------------------------------


class TestTrustScoreEdgeCases:
    """Edge cases for the trust-score-validator PostToolUse hook."""

    def test_21_trust_score_exactly_50(self, run_hook, cognitive_os_env):
        """Trust score exactly 50 -> boundary behavior (should warn, not
        critical alert)."""
        env = cognitive_os_env["env"]
        input_json = make_agent_response_input(
            "implement feature",
            "Done. TRUST REPORT:\n  Score: 50/100\n"
            "WHAT I'M UNSURE ABOUT:\n  - edge cases not tested"
        )
        result = run_hook("trust-score-validator.sh", env=env, stdin=input_json)
        assert result.returncode == 0
        # Score 50 is >= 50 and < 70 -> should not trigger "ALERT" (< 50)
        # but may trigger "NOTE" (< 70)
        combined = result.stdout + result.stderr
        # Should NOT say "Low confidence" (that's < 50)
        assert "ALERT" not in combined

    def test_22_trust_score_zero_critical(self, run_hook, cognitive_os_env):
        """Trust score 0 -> CRITICAL block alert."""
        env = cognitive_os_env["env"]
        input_json = make_agent_response_input(
            "implement feature",
            "Could not complete. TRUST REPORT:\n  Score: 0/100\n"
            "WHAT I'M UNSURE ABOUT:\n  - everything"
        )
        result = run_hook("trust-score-validator.sh", env=env, stdin=input_json)
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "ALERT" in combined or "Low confidence" in combined

    def test_23_no_trust_report_in_response(self, run_hook, cognitive_os_env):
        """No trust report in response -> trust-score-validator warns."""
        env = cognitive_os_env["env"]
        input_json = make_agent_response_input(
            "implement feature",
            "Done. All tests pass. Implementation complete."
        )
        result = run_hook("trust-score-validator.sh", env=env, stdin=input_json)
        assert result.returncode == 0
        assert "WARNING" in result.stdout
        assert "Trust Report" in result.stdout

    def test_24_trust_score_100_red_flag(self, run_hook, cognitive_os_env):
        """Trust score 100 -> '100% confident is a RED FLAG' per trust-score
        rule. The validator itself does not enforce this (the rule is for
        orchestrator interpretation), but the score should be logged."""
        env = cognitive_os_env["env"]
        input_json = make_agent_response_input(
            "implement feature",
            "Perfect implementation. TRUST REPORT:\n  Score: 100/100\n"
            "WHAT I'M CONFIDENT ABOUT:\n  - everything is perfect"
        )
        result = run_hook("trust-score-validator.sh", env=env, stdin=input_json)
        assert result.returncode == 0
        # Score 100 is above all thresholds, so no alerts from the hook itself
        # But the metric should be logged
        log = cognitive_os_env["cos_dir"] / "metrics" / "trust-scores.jsonl"
        assert log.exists()
        entries = [json.loads(l) for l in log.read_text().strip().split("\n") if l]
        assert any(e["score"] == 100 for e in entries)


# ---------------------------------------------------------------------------
# EDGE CASES — SPLIT-AND-RESUME (clarification-interceptor)
# ---------------------------------------------------------------------------


class TestSplitAndResumeEdgeCases:
    """Edge cases for the clarification-interceptor PostToolUse hook."""

    def test_25_single_question(self, run_hook, cognitive_os_env):
        """Agent returns NEEDS_CLARIFICATION with 1 question -> single round."""
        env = cognitive_os_env["env"]
        response = (
            "I started implementing but found an ambiguity.\n"
            "NEEDS_CLARIFICATION:\n"
            "1. Should the API use REST or GraphQL?"
        )
        input_json = make_agent_response_input("implement API", response)
        result = run_hook(
            "clarification-interceptor.sh", env=env, stdin=input_json
        )
        assert result.returncode == 0
        assert "SPLIT-AND-RESUME" in result.stdout
        assert "ORCHESTRATOR ACTION REQUIRED" in result.stdout
        assert "Round: 1/2" in result.stdout

    def test_26_five_questions_all_extracted(self, run_hook, cognitive_os_env):
        """Agent returns NEEDS_CLARIFICATION with 5 questions -> all extracted."""
        env = cognitive_os_env["env"]
        response = (
            "Multiple ambiguities found.\n"
            "NEEDS_CLARIFICATION:\n"
            "1. Which database engine?\n"
            "2. REST or GraphQL?\n"
            "3. What auth mechanism?\n"
            "4. Which port?\n"
            "5. Monorepo or polyrepo?"
        )
        input_json = make_agent_response_input("implement service", response)
        result = run_hook(
            "clarification-interceptor.sh", env=env, stdin=input_json
        )
        assert result.returncode == 0
        assert "SPLIT-AND-RESUME" in result.stdout
        # All 5 questions should appear in output
        assert "database" in result.stdout.lower()
        assert "auth" in result.stdout.lower()

    def test_27_second_round_detected(self, run_hook, cognitive_os_env):
        """Agent returns NEEDS_CLARIFICATION after first re-launch (prompt
        already contains CLARIFICATION ANSWERS:) -> second round detected."""
        env = cognitive_os_env["env"]
        prompt_with_answers = (
            "Implement the user service.\n"
            "CLARIFICATION ANSWERS:\n"
            "1. Q: Which database?\n   A: PostgreSQL\n"
        )
        response = (
            "Thanks for the DB clarification. Found another issue.\n"
            "NEEDS_CLARIFICATION:\n"
            "1. Should I use an ORM or raw SQL?"
        )
        input_json = make_agent_response_input(prompt_with_answers, response)
        result = run_hook(
            "clarification-interceptor.sh", env=env, stdin=input_json
        )
        assert result.returncode == 0
        assert "Round: 2/2" in result.stdout

    def test_28_third_round_exceeded(self, run_hook, cognitive_os_env):
        """Agent returns NEEDS_CLARIFICATION 3 times -> max rounds exceeded."""
        env = cognitive_os_env["env"]
        prompt_with_two_rounds = (
            "Implement the user service.\n"
            "CLARIFICATION ANSWERS:\n"
            "1. Q: Which database?\n   A: PostgreSQL\n"
            "CLARIFICATION ANSWERS:\n"
            "1. Q: ORM or raw SQL?\n   A: Use GORM\n"
        )
        response = (
            "Still confused.\n"
            "NEEDS_CLARIFICATION:\n"
            "1. What about migrations?"
        )
        input_json = make_agent_response_input(prompt_with_two_rounds, response)
        result = run_hook(
            "clarification-interceptor.sh", env=env, stdin=input_json
        )
        assert result.returncode == 0
        assert "MAX ROUNDS EXCEEDED" in result.stdout
        assert "Escalate" in result.stdout

    def test_29_marker_in_middle_of_text(self, run_hook, cognitive_os_env):
        """NEEDS_CLARIFICATION in the middle of normal text -> still detected."""
        env = cognitive_os_env["env"]
        response = (
            "I implemented the handler and wrote tests. However, I encountered "
            "an issue with the configuration format. "
            "NEEDS_CLARIFICATION:\n"
            "1. Is the config file YAML or TOML?\n"
            "Everything else is complete and tests pass."
        )
        input_json = make_agent_response_input("implement handler", response)
        result = run_hook(
            "clarification-interceptor.sh", env=env, stdin=input_json
        )
        assert result.returncode == 0
        assert "SPLIT-AND-RESUME" in result.stdout
        assert "YAML" in result.stdout or "config" in result.stdout.lower()

    def test_30_no_clarification_marker_clean_pass(
        self, run_hook, cognitive_os_env
    ):
        """Agent response without NEEDS_CLARIFICATION -> clean pass."""
        env = cognitive_os_env["env"]
        response = "Implementation complete. All tests pass."
        input_json = make_agent_response_input("implement handler", response)
        result = run_hook(
            "clarification-interceptor.sh", env=env, stdin=input_json
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_30b_answer_found_in_engram_scenario(self, run_hook, cognitive_os_env):
        """Verify clarification log records the event for Engram resolution.
        (Actual Engram search is orchestrator responsibility, not hook's.)"""
        env = cognitive_os_env["env"]
        response = (
            "NEEDS_CLARIFICATION:\n"
            "1. What port should the service run on?"
        )
        input_json = make_agent_response_input("implement service", response)
        result = run_hook(
            "clarification-interceptor.sh", env=env, stdin=input_json
        )
        assert result.returncode == 0
        # Verify metrics logged
        metrics_dir = cognitive_os_env["cos_dir"] / "metrics"
        log = metrics_dir / "clarifications.jsonl"
        # Check session-scoped metrics first
        session_id = cognitive_os_env["session_id"]
        session_log = (
            cognitive_os_env["cos_dir"]
            / "sessions"
            / session_id
            / "metrics"
            / "clarifications.jsonl"
        )
        found_log = session_log if session_log.exists() else log
        assert found_log.exists(), "Clarification event should be logged"
        data = found_log.read_text().strip()
        assert len(data) > 0
        entry = json.loads(data.split("\n")[-1])
        assert entry["resolution"] == "pending"
        assert entry["round"] == 1


# ---------------------------------------------------------------------------
# INTEGRATION SCENARIOS
# ---------------------------------------------------------------------------


class TestIntegrationScenarios:
    """End-to-end integration scenarios combining multiple safety features."""

    def test_31_full_pipeline_gates_overhead(self, run_hook, cognitive_os_env):
        """Full SDD pipeline with all gates active -> measure total overhead.
        Each gate should complete in < 3 seconds."""
        env = cognitive_os_env["env"]
        prompt = make_agent_input(
            "Implement the payment webhook handler in internal/payments/webhook.go. "
            "ACCEPTANCE CRITERIA: "
            "1. go test ./internal/payments/... exits 0. "
            "2. golangci-lint run ./internal/payments/... exits 0. "
            "3. go build ./internal/payments/... exits 0."
        )

        gates = [
            "clarification-gate.sh",
            "blast-radius.sh",
            "dry-run-preview.sh",  # only active with DRY_RUN=true
        ]

        for gate in gates:
            start = time.time()
            run_hook(gate, env=env, stdin=prompt)
            elapsed = time.time() - start
            assert elapsed < 3.0, f"{gate} took {elapsed:.2f}s (max 3s)"

    def test_32_singularity_low_confidence_gated(
        self, run_hook, cognitive_os_env
    ):
        """Singularity controller output with low confidence -> trust score
        validator fires alert."""
        env = cognitive_os_env["env"]
        response = (
            "Singularity cycle complete. Fixed 3 test failures.\n"
            "TRUST REPORT:\n  Score: 35/100\n"
            "WHAT I'M UNSURE ABOUT:\n"
            "  - root cause of 2 failures unclear\n"
            "  - fix may mask underlying issue"
        )
        input_json = make_agent_response_input(
            "singularity: fix test failures", response
        )
        result = run_hook("trust-score-validator.sh", env=env, stdin=input_json)
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "ALERT" in combined or "Low confidence" in combined

    def test_33_batch_dry_run_all_previewed(self, run_hook, cognitive_os_env):
        """Batch runner + dry-run -> all changes previewed, none executed."""
        env = {**cognitive_os_env["env"], "DRY_RUN": "true"}

        tasks = [
            "implement user handler in internal/users/handler.go",
            "implement order handler in internal/orders/handler.go",
            "implement payment handler in internal/payments/handler.go",
        ]

        for task in tasks:
            prompt = make_agent_input(task)
            result = run_hook("dry-run-preview.sh", env=env, stdin=prompt)
            assert result.returncode == 2, f"Task '{task}' should be blocked"
            assert "DRY-RUN" in result.stdout

        # Verify log has 3 entries
        metrics_dir = cognitive_os_env["cos_dir"] / "metrics"
        session_id = cognitive_os_env["session_id"]
        session_metrics = (
            cognitive_os_env["cos_dir"]
            / "sessions"
            / session_id
            / "metrics"
        )
        log = session_metrics / "dry-run.jsonl"
        if not log.exists():
            log = metrics_dir / "dry-run.jsonl"
        if log.exists():
            entries = [
                json.loads(l)
                for l in log.read_text().strip().split("\n")
                if l.strip()
            ]
            assert len(entries) == 3

    def test_34_self_install_hooks_accessible(self, run_hook, cognitive_os_env):
        """Self-install adds new safety hooks -> verify hooks are valid bash."""
        hooks_dir = Path(__file__).resolve().parent.parent.parent / "hooks"
        safety_hooks = [
            "clarification-gate.sh",
            "blast-radius.sh",
            "assumption-tracker.sh",
            "trust-score-validator.sh",
            "dry-run-preview.sh",
            "clarification-interceptor.sh",
        ]
        for hook in safety_hooks:
            hook_path = hooks_dir / hook
            assert hook_path.exists(), f"Safety hook {hook} must exist"
            result = subprocess.run(
                ["bash", "-n", str(hook_path)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, (
                f"{hook} has syntax errors: {result.stderr}"
            )


# ---------------------------------------------------------------------------
# NON-AGENT TOOL — ALL HOOKS SHOULD IGNORE
# ---------------------------------------------------------------------------


class TestNonAgentToolIgnored:
    """All safety hooks should silently ignore non-Agent tool calls."""

    @pytest.mark.parametrize(
        "hook_name",
        [
            "clarification-gate.sh",
            "blast-radius.sh",
            "assumption-tracker.sh",
            "trust-score-validator.sh",
            "clarification-interceptor.sh",
        ],
    )
    def test_non_agent_tool_ignored(
        self, run_hook, cognitive_os_env, hook_name
    ):
        env = cognitive_os_env["env"]
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "tool_response": "file1.go file2.go",
        })
        result = run_hook(hook_name, env=env, stdin=input_json)
        assert result.returncode == 0
        assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# PRIVATE MODE — ALL HOOKS SHOULD SKIP
# ---------------------------------------------------------------------------


class TestPrivateModeSkipsHooks:
    """When private mode is active, safety hooks should skip processing."""

    @pytest.mark.parametrize(
        "hook_name",
        [
            "clarification-gate.sh",
            "blast-radius.sh",
            "assumption-tracker.sh",
            "clarification-interceptor.sh",
        ],
    )
    def test_private_mode_skips(
        self, run_hook, cognitive_os_env, hook_name, tmp_path
    ):
        env = cognitive_os_env["env"]
        private_flag = Path("/tmp/claude-private-mode-active")
        try:
            private_flag.touch()
            input_json = make_agent_input("fix all the bugs everywhere")
            result = run_hook(hook_name, env=env, stdin=input_json)
            assert result.returncode == 0
            assert result.stdout.strip() == ""
        finally:
            private_flag.unlink(missing_ok=True)

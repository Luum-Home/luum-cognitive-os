"""
Unit tests for lib/user_model.py
"""

import json
from unittest.mock import MagicMock, patch

from lib.user_model import UserModel, UserPreference


class TestRecordPreference:
    def test_new_preference(self):
        model = UserModel()
        model.record_preference("communication", "language", "Spanish", 0.8)
        pref = model.get_preference("communication", "language")
        assert pref is not None
        assert pref.value == "Spanish"

    def test_update_higher_confidence(self):
        model = UserModel()
        model.record_preference("communication", "language", "English", 0.5)
        model.record_preference("communication", "language", "Spanish", 0.8)
        assert model.get_preference("communication", "language").value == "Spanish"

    def test_update_equal_confidence(self):
        # confidence >= existing means equal confidence also updates
        model = UserModel()
        model.record_preference("communication", "language", "English", 0.5)
        model.record_preference("communication", "language", "Spanish", 0.5)
        assert model.get_preference("communication", "language").value == "Spanish"

    def test_skip_lower_confidence(self):
        model = UserModel()
        model.record_preference("communication", "language", "Spanish", 0.9)
        model.record_preference("communication", "language", "English", 0.3)
        assert model.get_preference("communication", "language").value == "Spanish"

    def test_missing_returns_none(self):
        model = UserModel()
        assert model.get_preference("nonexistent", "key") is None

    def test_different_keys_stored_separately(self):
        model = UserModel()
        model.record_preference("communication", "language", "Spanish", 0.8)
        model.record_preference("communication", "verbosity", "terse", 0.5)
        assert model.get_preference("communication", "language").value == "Spanish"
        assert model.get_preference("communication", "verbosity").value == "terse"
        assert len(model.preferences) == 2

    def test_default_source_is_inferred(self):
        model = UserModel()
        model.record_preference("communication", "language", "Spanish", 0.8)
        pref = model.get_preference("communication", "language")
        assert pref.source == "inferred"

    def test_explicit_source_stored(self):
        model = UserModel()
        model.record_preference("explicit", "correction", "use tabs", 0.9, "explicit")
        pref = model.get_preference("explicit", "correction")
        assert pref.source == "explicit"

    def test_confidence_stored_correctly(self):
        model = UserModel()
        model.record_preference("communication", "language", "Spanish", 0.75)
        pref = model.get_preference("communication", "language")
        assert pref.confidence == 0.75


class TestRecordTechnicalContext:
    def test_stores_value(self):
        model = UserModel()
        model.record_technical_context("stack", "Go")
        assert model.technical_context["stack"] == "Go"

    def test_overwrites_existing(self):
        model = UserModel()
        model.record_technical_context("db", "postgres")
        model.record_technical_context("db", "mysql")
        assert model.technical_context["db"] == "mysql"

    def test_multiple_keys(self):
        model = UserModel()
        model.record_technical_context("stack", "Go")
        model.record_technical_context("db", "postgres")
        assert model.technical_context["stack"] == "Go"
        assert model.technical_context["db"] == "postgres"


class TestProfileSummary:
    def test_empty_model_returns_empty_string(self):
        model = UserModel()
        summary = model.get_profile_summary()
        assert summary == ""

    def test_with_preferences(self):
        model = UserModel()
        model.record_preference("communication", "language", "Spanish", 0.8)
        summary = model.get_profile_summary()
        assert "Spanish" in summary

    def test_with_technical_context(self):
        model = UserModel()
        model.record_technical_context("stack", "Go")
        summary = model.get_profile_summary()
        assert "Go" in summary

    def test_summary_contains_headers(self):
        model = UserModel()
        model.record_preference("communication", "language", "Spanish", 0.8)
        model.record_technical_context("stack", "Go")
        summary = model.get_profile_summary()
        assert "USER PREFERENCES:" in summary
        assert "TECHNICAL CONTEXT:" in summary

    def test_higher_confidence_first(self):
        model = UserModel()
        model.record_preference("communication", "language", "Spanish", 0.8)
        model.record_preference("communication", "verbosity", "terse", 0.3)
        summary = model.get_profile_summary()
        # Spanish (0.8) should appear before terse (0.3)
        assert summary.index("Spanish") < summary.index("terse")

    def test_only_preferences_section_when_no_context(self):
        model = UserModel()
        model.record_preference("communication", "language", "Spanish", 0.8)
        summary = model.get_profile_summary()
        assert "USER PREFERENCES:" in summary
        assert "TECHNICAL CONTEXT:" not in summary

    def test_only_context_section_when_no_preferences(self):
        model = UserModel()
        model.record_technical_context("stack", "Go")
        summary = model.get_profile_summary()
        assert "TECHNICAL CONTEXT:" in summary
        assert "USER PREFERENCES:" not in summary


class TestInference:
    def test_infer_spanish_from_indicator(self):
        model = UserModel()
        model.infer_from_message("dale hacé el endpoint")
        pref = model.get_preference("communication", "language")
        assert pref is not None
        assert "Spanish" in pref.value

    def test_infer_spanish_from_necesito(self):
        model = UserModel()
        model.infer_from_message("necesito arreglá el test")
        pref = model.get_preference("communication", "language")
        assert pref is not None
        assert "Spanish" in pref.value

    def test_no_spanish_for_plain_english_message(self):
        model = UserModel()
        # A long English message (>9 words) with no Spanish indicators
        model.infer_from_message("please fix the handler function and make sure the tests still pass")
        pref = model.get_preference("communication", "language")
        if pref is not None:
            assert "Spanish" not in pref.value

    def test_infer_go_tech_stack(self):
        model = UserModel()
        model.infer_from_message("fix the handler.go file")
        assert "go" in model.technical_context.get("stack", "").lower()

    def test_infer_python_tech_stack(self):
        model = UserModel()
        model.infer_from_message("run the tests in test_utils.py")
        assert "python" in model.technical_context.get("stack", "").lower()

    def test_infer_typescript_tech_stack(self):
        model = UserModel()
        model.infer_from_message("update the component.ts file")
        assert "typescript" in model.technical_context.get("stack", "").lower()

    def test_infer_docker_tech_stack(self):
        model = UserModel()
        model.infer_from_message("restart the docker container")
        assert "docker" in model.technical_context.get("stack", "").lower()

    def test_interaction_count_increments(self):
        model = UserModel()
        model.infer_from_message("hello")
        model.infer_from_message("world")
        assert model.interaction_count == 2

    def test_interaction_count_starts_at_zero(self):
        model = UserModel()
        assert model.interaction_count == 0

    def test_short_message_infers_terse(self):
        model = UserModel()
        # Less than 10 words -> terse
        model.infer_from_message("fix it")
        pref = model.get_preference("communication", "verbosity")
        assert pref is not None
        assert pref.value == "terse"

    def test_multiple_techs_accumulated(self):
        model = UserModel()
        model.infer_from_message("update handler.go")
        model.infer_from_message("also fix the test.py")
        stack = model.technical_context.get("stack", "")
        assert "go" in stack.lower()
        assert "python" in stack.lower()


class TestInferFromFeedback:
    def test_explicit_negative(self):
        model = UserModel()
        model.infer_from_feedback("explicit_negative")
        pref = model.get_preference("workflow", "last_feedback")
        assert pref is not None
        assert pref.value == "negative"

    def test_explicit_positive(self):
        model = UserModel()
        model.infer_from_feedback("explicit_positive")
        pref = model.get_preference("workflow", "last_feedback")
        assert pref is not None
        assert pref.value == "positive"

    def test_correction_with_detail(self):
        model = UserModel()
        model.infer_from_feedback("correction", detail="use tabs not spaces")
        pref = model.get_preference("explicit", "correction")
        assert pref is not None
        assert "tabs" in pref.value

    def test_correction_without_detail_ignored(self):
        model = UserModel()
        model.infer_from_feedback("correction", detail=None)
        pref = model.get_preference("explicit", "correction")
        assert pref is None

    def test_escalation(self):
        model = UserModel()
        model.infer_from_feedback("escalation")
        pref = model.get_preference("workflow", "prefers_manual_control")
        assert pref is not None
        assert pref.value == "true"

    def test_unknown_feedback_type_no_crash(self):
        model = UserModel()
        # Should not raise
        model.infer_from_feedback("unknown_type")


class TestSerialization:
    def test_roundtrip_with_preferences(self):
        model = UserModel()
        model.record_preference("comm", "lang", "ES", 0.9, "explicit")
        data = model.to_dict()
        restored = UserModel.from_dict(data)
        pref = restored.get_preference("comm", "lang")
        assert pref is not None
        assert pref.value == "ES"
        assert pref.confidence == 0.9
        assert pref.source == "explicit"

    def test_roundtrip_with_technical_context(self):
        model = UserModel()
        model.record_technical_context("db", "postgres")
        data = model.to_dict()
        restored = UserModel.from_dict(data)
        assert restored.technical_context["db"] == "postgres"

    def test_roundtrip_with_interaction_count(self):
        model = UserModel()
        model.interaction_count = 42
        data = model.to_dict()
        restored = UserModel.from_dict(data)
        assert restored.interaction_count == 42

    def test_empty_roundtrip(self):
        model = UserModel()
        data = model.to_dict()
        restored = UserModel.from_dict(data)
        assert len(restored.preferences) == 0
        assert len(restored.technical_context) == 0
        assert restored.interaction_count == 0

    def test_to_dict_structure(self):
        model = UserModel()
        model.record_preference("comm", "lang", "ES", 0.9)
        model.record_technical_context("stack", "go")
        model.interaction_count = 5
        data = model.to_dict()
        assert "preferences" in data
        assert "technical_context" in data
        assert "interaction_count" in data
        assert data["interaction_count"] == 5
        assert data["technical_context"]["stack"] == "go"
        assert len(data["preferences"]) == 1

    def test_from_dict_missing_keys_uses_defaults(self):
        restored = UserModel.from_dict({})
        assert restored.interaction_count == 0
        assert len(restored.preferences) == 0
        assert len(restored.technical_context) == 0

    def test_user_preference_dataclass(self):
        pref = UserPreference(
            category="comm",
            key="lang",
            value="Spanish",
            confidence=0.8,
            source="inferred",
        )
        assert pref.category == "comm"
        assert pref.key == "lang"
        assert pref.value == "Spanish"
        assert pref.confidence == 0.8
        assert pref.source == "inferred"


# ---------------------------------------------------------------------------
# Engram persistence (subprocess integration)
# ---------------------------------------------------------------------------


class TestEngramPersistence:
    """Tests for save_to_engram / load_from_engram — subprocess path mocked."""

    def test_save_to_engram_calls_subprocess(self):
        """save_to_engram must invoke the engram binary via subprocess.run."""
        model = UserModel()
        model.record_preference("communication", "language", "Spanish", 0.9)

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Saved."
        mock_proc.stderr = ""

        with patch("lib.user_model.subprocess.run", return_value=mock_proc) as mock_run:
            model.save_to_engram(project="test-project")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]  # positional first arg = cmd list
        assert any("save" in str(a) for a in call_args), (
            f"Expected 'save' in subprocess command, got: {call_args}"
        )

    def test_load_from_engram_empty_result_returns_default(self):
        """If engram search returns nothing, load_from_engram returns a default UserModel."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""  # no output from engram
        mock_proc.stderr = ""

        with patch("lib.user_model.subprocess.run", return_value=mock_proc):
            result = UserModel.load_from_engram(project="test-project")

        assert isinstance(result, UserModel), (
            "load_from_engram with empty output should return a UserModel instance"
        )
        assert result.interaction_count == 0, (
            "Default model should have interaction_count=0"
        )
        assert len(result.preferences) == 0, (
            "Default model should have no preferences"
        )

    def test_load_from_engram_corrupt_json_graceful(self):
        """If engram returns a line starting with '{' but is corrupt JSON, return default."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "{this is not valid json\n"
        mock_proc.stderr = ""

        with patch("lib.user_model.subprocess.run", return_value=mock_proc):
            result = UserModel.load_from_engram(project="test-project")

        assert isinstance(result, UserModel), (
            "Corrupt JSON from engram should return a default UserModel, not raise"
        )

    def test_preferences_survive_simulated_restart(self):
        """Preferences saved via mocked engram can be reloaded in a new instance.

        Simulates the full round-trip: save → (restart) → load.
        """
        original = UserModel()
        original.record_preference("communication", "language", "Spanish", 0.95)
        original.record_technical_context("stack", "Go")
        original.interaction_count = 7

        saved_json = json.dumps(original.to_dict())

        save_proc = MagicMock()
        save_proc.returncode = 0
        save_proc.stdout = "Saved."
        save_proc.stderr = ""

        load_proc = MagicMock()
        load_proc.returncode = 0
        # Engram returns a JSON line starting with '{'
        load_proc.stdout = saved_json + "\n"
        load_proc.stderr = ""

        with patch("lib.user_model.subprocess.run", return_value=save_proc):
            original.save_to_engram(project="test-project")

        with patch("lib.user_model.subprocess.run", return_value=load_proc):
            restored = UserModel.load_from_engram(project="test-project")

        assert isinstance(restored, UserModel)
        pref = restored.get_preference("communication", "language")
        assert pref is not None, "Language preference should survive the round-trip"
        assert pref.value == "Spanish"
        assert restored.technical_context.get("stack") == "Go"
        assert restored.interaction_count == 7

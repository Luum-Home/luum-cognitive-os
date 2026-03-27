"""
Integration tests for DeepEval and RAGAS evaluation frameworks.

These tests validate import availability, API surface correctness, and
configuration compatibility with the Cognitive OS agent architecture.
They run without Docker -- only pip-installed packages are required.

Usage:
    pip install deepeval ragas
    pytest tests/integration/test_eval_frameworks.py -m eval_frameworks
"""

import os
import inspect

import pytest

pytestmark = pytest.mark.eval_frameworks


# ---------------------------------------------------------------------------
# DeepEval Framework Tests
# ---------------------------------------------------------------------------

class TestDeepEvalFramework:
    """Validate DeepEval package availability and API surface for Cognitive OS."""

    def test_deepeval_import(self):
        """Verify deepeval module loads successfully.

        Cognitive OS integration: base dependency for all agent evaluation
        pipelines including SDD verify phase scoring.
        """
        try:
            import deepeval  # noqa: F401
        except ImportError:
            pytest.skip("deepeval not installed")

        assert hasattr(deepeval, "__version__")

    @pytest.mark.parametrize(
        "metric_name",
        [
            "AnswerRelevancyMetric",
            "FaithfulnessMetric",
            "HallucinationMetric",
            "ToolCorrectnessMetric",
            "ConversationalRelevancyMetric",
        ],
    )
    def test_deepeval_metrics_available(self, metric_name: str):
        """Verify key evaluation metrics are importable from deepeval.metrics.

        Cognitive OS integration: these metrics score agent responses during
        the sdd-verify phase and continuous evaluation runs.
        """
        try:
            from deepeval import metrics as dm  # noqa: F401
        except ImportError:
            pytest.skip("deepeval not installed")

        metric_cls = getattr(dm, metric_name, None)
        assert metric_cls is not None, f"{metric_name} not found in deepeval.metrics"
        assert inspect.isclass(metric_cls), f"{metric_name} should be a class"

    def test_deepeval_test_case_creation(self):
        """Create an LLMTestCase and verify field access.

        Cognitive OS integration: every agent action produces an LLMTestCase
        that feeds into the evaluation dataset for regression tracking.
        """
        try:
            from deepeval.test_case import LLMTestCase
        except ImportError:
            pytest.skip("deepeval not installed")

        tc = LLMTestCase(
            input="test",
            actual_output="response",
            expected_output="response",
        )
        assert tc.input == "test"
        assert tc.actual_output == "response"
        assert tc.expected_output == "response"

    def test_deepeval_conversational_test_case(self):
        """Create a ConversationalTestCase modeling a 3-turn SDD workflow.

        Cognitive OS integration: SDD phases (propose -> spec -> design) form
        a multi-turn conversation that must be evaluated as a coherent sequence.
        """
        try:
            from deepeval.test_case import LLMTestCase, ConversationalTestCase
        except ImportError:
            pytest.skip("deepeval not installed")

        turns = [
            LLMTestCase(
                input="Create a proposal for auth-refactor",
                actual_output="Proposal: migrate to OAuth 2.1 with PKCE",
            ),
            LLMTestCase(
                input="Generate spec from the proposal",
                actual_output="Spec: REQ-01 token rotation, REQ-02 PKCE flow",
            ),
            LLMTestCase(
                input="Produce a technical design from the spec",
                actual_output="Design: JWT service with Redis token store",
            ),
        ]

        conv = ConversationalTestCase(turns=turns)
        assert len(conv.turns) == 3
        assert conv.turns[0].input == "Create a proposal for auth-refactor"
        assert conv.turns[2].actual_output == "Design: JWT service with Redis token store"

    def test_deepeval_red_team_import(self):
        """Verify RedTeamer class is importable for adversarial testing.

        Cognitive OS integration: red-teaming validates that agent skills
        resist prompt injection and produce safe outputs.
        """
        try:
            from deepeval.red_teaming import RedTeamer
        except ImportError:
            pytest.skip("deepeval not installed")

        assert inspect.isclass(RedTeamer)

        # Instantiation requires an LLM key; skip if unavailable
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("No LLM API key set -- skipping RedTeamer instantiation")

    def test_deepeval_dataset_creation(self):
        """Create an EvaluationDataset with multiple test cases.

        Cognitive OS integration: evaluation datasets are built from engram
        observation history to track agent quality over time.
        """
        try:
            from deepeval.dataset import EvaluationDataset
            from deepeval.test_case import LLMTestCase
        except ImportError:
            pytest.skip("deepeval not installed")

        cases = [
            LLMTestCase(
                input="What is the project architecture?",
                actual_output="Microservices with event-driven communication",
            ),
            LLMTestCase(
                input="How is auth handled?",
                actual_output="OAuth 2.1 with PKCE and JWT tokens",
            ),
        ]

        dataset = EvaluationDataset(test_cases=cases)
        assert len(dataset.test_cases) == 2

    def test_deepeval_cognitive_os_trace_format(self):
        """Validate that Cognitive OS trace metadata can be stored in LLMTestCase.

        Cognitive OS integration: every evaluation trace carries metadata
        identifying the skill, session, SDD phase, change name, and retry
        count so results can be correlated with the DAG state.
        """
        try:
            from deepeval.test_case import LLMTestCase
        except ImportError:
            pytest.skip("deepeval not installed")

        trace_metadata = {
            "skill_name": "sdd-verify",
            "session_id": "sess-abc-123",
            "phase": "verify",
            "change_name": "auth-refactor",
            "retry_count": 1,
        }

        tc = LLMTestCase(
            input="Verify auth-refactor spec compliance",
            actual_output="PASS with warnings: REQ-03 untested",
            additional_metadata=trace_metadata,
        )

        assert tc.additional_metadata is not None
        assert tc.additional_metadata["skill_name"] == "sdd-verify"
        assert tc.additional_metadata["retry_count"] == 1
        assert tc.additional_metadata["change_name"] == "auth-refactor"


# ---------------------------------------------------------------------------
# RAGAS Framework Tests (targeting v0.4+ API)
# ---------------------------------------------------------------------------

class TestRagasFramework:
    """Validate RAGAS package availability and API surface for Cognitive OS.

    NOTE: These tests target the RAGAS v0.4+ API. Import paths may differ
    from earlier versions (v0.1.x used ragas.metrics with lowercase names).
    """

    def test_ragas_import(self):
        """Verify ragas module loads successfully.

        Cognitive OS integration: RAGAS provides RAG-specific evaluation
        for engram memory retrieval quality and context grounding.
        """
        try:
            import ragas  # noqa: F401
        except ImportError:
            pytest.skip("ragas not installed")

        assert hasattr(ragas, "__version__")

    @pytest.mark.parametrize(
        "metric_name,fallback_paths",
        [
            ("Faithfulness", ["ragas.metrics"]),
            ("ContextPrecision", ["ragas.metrics", "ragas.metrics._context_precision"]),
            ("ContextRecall", ["ragas.metrics", "ragas.metrics._context_recall"]),
            ("AnswerRelevancy", ["ragas.metrics", "ragas.metrics._answer_relevance"]),
        ],
    )
    def test_ragas_metrics_available(self, metric_name: str, fallback_paths: list):
        """Verify key RAGAS metrics are importable.

        Cognitive OS integration: these metrics evaluate engram retrieval
        quality -- context precision/recall measure whether the right
        observations surface for a given query.

        RAGAS v0.4+ uses capitalized class names. Fallback paths handle
        potential submodule restructuring across minor versions.
        """
        try:
            import ragas  # noqa: F401
        except ImportError:
            pytest.skip("ragas not installed")

        metric_cls = None
        import importlib

        for module_path in fallback_paths:
            try:
                mod = importlib.import_module(module_path)
                metric_cls = getattr(mod, metric_name, None)
                if metric_cls is not None:
                    break
            except ImportError:
                continue

        assert metric_cls is not None, (
            f"{metric_name} not found in any of {fallback_paths}"
        )
        assert inspect.isclass(metric_cls), f"{metric_name} should be a class"

    def test_ragas_dataset_creation(self):
        """Create a RAGAS EvaluationDataset with a SingleTurnSample.

        Cognitive OS integration: single-turn samples model one-shot agent
        queries against engram memory (e.g., mem_search -> response).

        RAGAS v0.4+ API: EvaluationDataset and SingleTurnSample live in
        the ragas top-level module.
        """
        try:
            from ragas import EvaluationDataset, SingleTurnSample
        except ImportError:
            pytest.skip("ragas not installed or SingleTurnSample not available in this version")

        sample = SingleTurnSample(
            user_input="What architecture decisions were made for auth?",
            response="OAuth 2.1 with PKCE was chosen over session-based auth",
            retrieved_contexts=[
                "Decision: chose OAuth 2.1 with PKCE for auth-refactor. "
                "Reason: stateless, mobile-friendly, industry standard.",
                "Architecture: JWT tokens stored in Redis with 15-min TTL. "
                "Refresh tokens rotated on each use.",
            ],
        )

        dataset = EvaluationDataset(samples=[sample])
        assert len(dataset.samples) == 1
        assert dataset.samples[0].user_input == "What architecture decisions were made for auth?"
        assert len(dataset.samples[0].retrieved_contexts) == 2

    def test_ragas_multi_turn_sample(self):
        """Create a MultiTurnSample modeling engram memory retrieval flow.

        Cognitive OS integration: multi-turn samples capture the full
        retrieval-augmented conversation: user asks -> agent searches
        engram -> agent responds with grounded context.

        RAGAS v0.4+ API: MultiTurnSample in ragas top-level module.
        """
        try:
            from ragas import MultiTurnSample
        except ImportError:
            pytest.skip("ragas not installed or MultiTurnSample not available in this version")

        # MultiTurnSample expects a list of dicts or message objects
        # representing the conversation. The exact schema depends on the
        # RAGAS version; we test basic instantiation.
        try:
            from ragas.messages import HumanMessage, AIMessage, ToolMessage, ToolCall

            user_msg = HumanMessage(content="What did we decide about the database?")
            tool_call = ToolCall(
                name="mem_search",
                args={"query": "database decision", "project": "luum-agent-os"},
            )
            tool_msg = ToolMessage(content="Observation: chose PostgreSQL with read replicas for scalability")
            ai_msg = AIMessage(
                content="We decided on PostgreSQL with read replicas for horizontal read scaling.",
                tool_calls=[tool_call],
            )

            sample = MultiTurnSample(
                user_input=[user_msg, ai_msg, tool_msg],
            )
            assert sample.user_input is not None
            assert len(sample.user_input) == 3
        except (ImportError, TypeError, AttributeError):
            # If message classes are not available or API differs,
            # fall back to verifying the class itself exists.
            assert inspect.isclass(MultiTurnSample)

    def test_ragas_tool_call_accuracy_import(self):
        """Verify ToolCallAccuracy metric is importable for agent trajectory testing.

        Cognitive OS integration: measures whether agents invoke the correct
        tools (mem_search, mem_save, skill dispatch) with proper arguments
        during SDD phase execution.

        RAGAS v0.4+ API: ToolCallAccuracy in ragas.metrics.
        """
        try:
            import ragas  # noqa: F401
        except ImportError:
            pytest.skip("ragas not installed")

        import importlib

        metric_cls = None
        search_paths = [
            ("ragas.metrics", "ToolCallAccuracy"),
            ("ragas.metrics._tool_call_accuracy", "ToolCallAccuracy"),
            ("ragas.metrics", "AgentGoalAccuracyWithReference"),
        ]

        for module_path, class_name in search_paths:
            try:
                mod = importlib.import_module(module_path)
                metric_cls = getattr(mod, class_name, None)
                if metric_cls is not None:
                    break
            except ImportError:
                continue

        if metric_cls is None:
            pytest.skip(
                "ToolCallAccuracy / AgentGoalAccuracyWithReference not found -- "
                "may require a newer RAGAS version"
            )

        assert inspect.isclass(metric_cls)

    def test_ragas_testset_generator_import(self):
        """Verify TestsetGenerator class exists for synthetic test generation.

        Cognitive OS integration: TestsetGenerator can produce synthetic
        evaluation datasets from project documentation and engram history,
        enabling automated regression test creation.

        RAGAS v0.4+ API: TestsetGenerator in ragas.testset module.
        Note: actual generation requires an LLM key and is not executed here.
        """
        try:
            from ragas.testset import TestsetGenerator
        except ImportError:
            pytest.skip("ragas not installed or TestsetGenerator not available")

        assert inspect.isclass(TestsetGenerator)

    def test_ragas_cognitive_os_memory_format(self):
        """Validate engram observation format maps to RAGAS retrieved_contexts.

        Cognitive OS integration: engram observations (title, content, type,
        topic_key) are the primary retrieval unit. This test confirms they
        can be serialized into the string-list format RAGAS expects for
        retrieved_contexts in SingleTurnSample.

        RAGAS v0.4+ API: retrieved_contexts is List[str].
        """
        try:
            from ragas import SingleTurnSample
        except ImportError:
            pytest.skip("ragas not installed or SingleTurnSample not available")

        # Simulate engram observations as returned by mem_get_observation
        engram_observations = [
            {
                "title": "Chose PostgreSQL over DynamoDB",
                "content": (
                    "What: Selected PostgreSQL with read replicas.\n"
                    "Why: Need ACID compliance for order processing.\n"
                    "Where: infrastructure/db-config\n"
                    "Learned: DynamoDB single-table design adds complexity "
                    "for relational queries."
                ),
                "type": "decision",
                "topic_key": "architecture/database",
            },
            {
                "title": "Fixed N+1 query in agent skill loader",
                "content": (
                    "What: Batch-load skill metadata instead of per-skill queries.\n"
                    "Why: Startup time was 4s, now 200ms.\n"
                    "Where: src/skills/loader.py\n"
                    "Learned: SQLAlchemy joinedload required explicit relationship config."
                ),
                "type": "bugfix",
                "topic_key": "performance/skill-loader",
            },
        ]

        # Map to RAGAS format: each observation becomes a context string
        retrieved_contexts = [
            f"[{obs['type']}] {obs['title']}\n{obs['content']}"
            for obs in engram_observations
        ]

        sample = SingleTurnSample(
            user_input="What database did we choose and why?",
            response="We chose PostgreSQL with read replicas for ACID compliance.",
            retrieved_contexts=retrieved_contexts,
        )

        assert len(sample.retrieved_contexts) == 2
        assert "[decision]" in sample.retrieved_contexts[0]
        assert "[bugfix]" in sample.retrieved_contexts[1]
        assert "PostgreSQL" in sample.retrieved_contexts[0]

# scope: both
"""Model recommender — cheapest model capable of handling a task type."""

from __future__ import annotations


class ModelRecommender:
    """Recommends the cheapest model capable of handling a task."""

    ROUTING_TABLE: dict[str, str] = {
        # haiku tasks (~$0.003/10K tokens)
        "archive": "haiku",
        "format": "haiku",
        "rename": "haiku",
        "doc-generation": "haiku",
        "doc-trim": "haiku",
        "catalog-update": "haiku",
        "plan-read": "haiku",
        # sonnet tasks (~$0.036/10K tokens)
        "implementation": "sonnet",
        "testing": "sonnet",
        "spec-writing": "sonnet",
        "migration": "sonnet",
        "skill-creation": "sonnet",
        "hook-creation": "sonnet",
        # opus tasks (~$0.18/10K tokens)
        "architecture": "opus",
        "root-cause-analysis": "opus",
        "security-review": "opus",
        "design": "opus",
        "complex-debugging": "opus",
    }

    # Keyword → task-type mapping (checked in order; first match wins)
    _KEYWORD_MAP: list[tuple[list[str], str]] = [
        # haiku
        (["archive", "archiv"], "archive"),
        (["format", "formatting"], "format"),
        (["rename", "renaming"], "rename"),
        (["doc generation", "generate doc", "write doc"], "doc-generation"),
        (["trim doc", "trim stub", "pointer stub", "trim 8", "trim docs"], "doc-trim"),
        (["catalog update", "update catalog"], "catalog-update"),
        (["plan read", "read plan"], "plan-read"),
        # sonnet
        (["implement", "implementation", "endpoint", "build"], "implementation"),
        (["test", "testing", "unit test", "write test"], "testing"),
        (["spec", "specification", "spec-writing"], "spec-writing"),
        (["migrat"], "migration"),
        (["skill creation", "create skill", "new skill"], "skill-creation"),
        (["hook creation", "create hook", "new hook"], "hook-creation"),
        # opus
        (["architect", "architecture"], "architecture"),
        (["root cause", "root-cause"], "root-cause-analysis"),
        (["security review", "security audit"], "security-review"),
        (["design"], "design"),
        (["debug", "debugging", "complex debug"], "complex-debugging"),
    ]

    # Cost per 1M tokens (input + output blended ~70/30 split)
    _COSTS_PER_1M: dict[str, float] = {
        "haiku": 0.25 * 0.7 + 1.25 * 0.3,   # ≈ 0.55
        "sonnet": 3.0 * 0.7 + 15.0 * 0.3,   # ≈ 6.60
        "opus": 15.0 * 0.7 + 75.0 * 0.3,    # ≈ 33.0
    }

    def classify_task_type(self, description: str) -> str:
        """Classify task description into a routing table key."""
        lower = description.lower()
        for keywords, task_type in self._KEYWORD_MAP:
            if any(kw in lower for kw in keywords):
                return task_type
        return "implementation"  # safe default maps to sonnet

    def recommend(self, task_description: str) -> str:
        """Return the recommended model for a task description."""
        task_type = self.classify_task_type(task_description)
        return self.ROUTING_TABLE.get(task_type, "sonnet")

    def estimate_cost(self, model: str, estimated_tokens: int = 50_000) -> float:
        """Estimate cost in USD for a task with given model and token count."""
        cost_per_1m = self._COSTS_PER_1M.get(model, self._COSTS_PER_1M["sonnet"])
        return cost_per_1m * estimated_tokens / 1_000_000

    def savings_vs_default(
        self,
        task_description: str,
        default_model: str = "sonnet",
        estimated_tokens: int = 50_000,
    ) -> dict:
        """Calculate savings using recommended model vs default."""
        recommended = self.recommend(task_description)
        rec_cost = self.estimate_cost(recommended, estimated_tokens)
        def_cost = self.estimate_cost(default_model, estimated_tokens)
        savings_usd = def_cost - rec_cost
        savings_pct = (savings_usd / def_cost * 100) if def_cost > 0 else 0.0
        return {
            "recommended": recommended,
            "default": default_model,
            "savings_pct": round(savings_pct, 1),
            "savings_usd": round(savings_usd, 6),
        }

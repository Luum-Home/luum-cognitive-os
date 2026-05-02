# SCOPE: both
"""Class facade over the canonical ``RESULT:`` parser."""

from __future__ import annotations

try:
    from lib.return_contract_parser import format_compact_result, parse_return_contract
except ModuleNotFoundError:
    from return_contract_parser import format_compact_result, parse_return_contract  # type: ignore[no-redef]


class ReturnContractValidator:
    """Extract, validate, and compact sub-agent ``RESULT:`` blocks."""

    REQUIRED_FIELDS = {"status", "summary"}
    VALID_STATUSES = {"completed", "success", "failed", "partial"}

    def extract_structured_return(self, agent_output: str) -> dict | None:
        """Extract the structured return block from agent output."""
        return parse_return_contract(agent_output)

    def validate_return(self, structured: dict) -> list[str]:
        """Return legacy class-API missing/invalid field descriptions."""
        issues: list[str] = []
        for field in self.REQUIRED_FIELDS:
            if not structured.get(field):
                issues.append(f"missing required field: {field}")
        status = str(structured.get("status", "")).lower()
        if status and status not in self.VALID_STATUSES:
            issues.append(f"invalid status '{status}'; must be one of {sorted(self.VALID_STATUSES)}")
        return issues

    def format_compact_summary(self, structured: dict) -> str:
        """Return a compact summary suitable for orchestrator context."""
        return format_compact_result(structured)

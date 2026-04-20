# SCOPE: both
"""ReturnContractValidator — parse and validate sub-agent RESULT blocks.

Sub-agents end their output with a RESULT: block (defined in agent-preamble.md).
The orchestrator uses this to extract a compact summary instead of reading the
full agent transcript.
"""

from __future__ import annotations

import re


class ReturnContractValidator:
    # Required fields in a structured return
    REQUIRED_FIELDS = {"status", "summary"}
    VALID_STATUSES = {"completed", "failed", "partial"}

    # ------------------------------------------------------------------ #
    # Extraction
    # ------------------------------------------------------------------ #

    def extract_structured_return(self, agent_output: str) -> dict | None:
        """Extract the structured RESULT block from agent output.

        Recognises two header variants:
          - ``RESULT:``  (preferred, machine-parseable)
          - ``## Result`` / ``## RESULT`` (markdown heading fallback)

        Parsed keys (all optional except status + summary):
          status, summary, files_created, files_modified, tests, discoveries,
          trust_score
        """
        block = self._find_result_block(agent_output)
        if block is None:
            return None
        return self._parse_block(block)

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def validate_return(self, structured: dict) -> list[str]:
        """Return a list of missing / invalid field descriptions."""
        issues: list[str] = []

        for field in self.REQUIRED_FIELDS:
            if not structured.get(field):
                issues.append(f"missing required field: {field}")

        status = structured.get("status", "")
        if status and status.lower() not in self.VALID_STATUSES:
            issues.append(
                f"invalid status '{status}'; must be one of {sorted(self.VALID_STATUSES)}"
            )

        return issues

    # ------------------------------------------------------------------ #
    # Formatting
    # ------------------------------------------------------------------ #

    def format_compact_summary(self, structured: dict) -> str:
        """Return a compact 3-5 line summary (≤500 chars) for the orchestrator."""
        parts: list[str] = []

        status = structured.get("status", "unknown").upper()
        summary = structured.get("summary", "")
        parts.append(f"[{status}] {summary}")

        created = structured.get("files_created", [])
        modified = structured.get("files_modified", [])
        file_parts: list[str] = []
        if created:
            file_parts.append(f"+{len(created)} created")
        if modified:
            file_parts.append(f"~{len(modified)} modified")
        if file_parts:
            parts.append("Files: " + ", ".join(file_parts))

        tests = structured.get("tests")
        if tests:
            parts.append(
                f"Tests: {tests.get('passed', 0)} passed, "
                f"{tests.get('failed', 0)} failed"
                + (f", {tests.get('xfail', 0)} xfail" if tests.get("xfail") else "")
            )

        discoveries = structured.get("discoveries", [])
        if discoveries:
            parts.append(f"Key findings: {discoveries[0]}"
                         + (f" (+{len(discoveries)-1} more)" if len(discoveries) > 1 else ""))

        trust = structured.get("trust_score")
        if trust is not None:
            parts.append(f"Trust: {trust}/100")

        result = "\n".join(parts)
        # Hard cap
        if len(result) > 500:
            result = result[:497] + "..."
        return result

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _find_result_block(self, text: str) -> str | None:
        """Return the raw text of the RESULT block or None."""
        # Try RESULT: header first
        m = re.search(r"^RESULT:\s*\n(.*?)(?:\n(?:TRUST_REPORT|##|\Z))", text,
                      re.MULTILINE | re.DOTALL)
        if m:
            return m.group(1)

        # Fallback: ## Result / ## RESULT markdown heading
        m = re.search(r"^##\s+RESULT\b.*?\n(.*?)(?:\n##|\Z)", text,
                      re.MULTILINE | re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1)

        return None

    def _parse_block(self, block: str) -> dict:
        result: dict = {}

        for line in block.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip().lower()
                value = value.strip()

                if key == "status":
                    result["status"] = value.lower()
                elif key == "summary":
                    result["summary"] = value
                elif key == "files_created":
                    result["files_created"] = self._parse_list(value)
                elif key == "files_modified":
                    result["files_modified"] = self._parse_list(value)
                elif key == "tests":
                    result["tests"] = self._parse_tests(value)
                elif key == "discoveries":
                    result.setdefault("discoveries", [])
                    if value:
                        result["discoveries"].append(value.lstrip("- "))
                elif key == "trust_score":
                    try:
                        result["trust_score"] = int(re.search(r"\d+", value).group())
                    except (AttributeError, ValueError):
                        pass
            elif line.startswith("- ") and "discoveries" in result:
                result["discoveries"].append(line.lstrip("- "))

        return result

    @staticmethod
    def _parse_list(value: str) -> list[str]:
        """Parse comma-separated or 'none'/empty list."""
        if not value or value.lower() in ("none", "[]", "-"):
            return []
        return [v.strip() for v in value.split(",") if v.strip()]

    @staticmethod
    def _parse_tests(value: str) -> dict:
        """Parse 'N passed, N failed, N xfail' into a dict."""
        tests: dict = {"passed": 0, "failed": 0, "xfail": 0}
        for m in re.finditer(r"(\d+)\s+(passed|failed|xfail)", value, re.IGNORECASE):
            tests[m.group(2).lower()] = int(m.group(1))
        return tests

"""Agent Runtime Web Service (ADR-291).

HTTP + SSE surface that exposes the Luum Cognitive OS agent runtime as a
standalone network service independent of any IDE harness.
"""

from agent_service.app import create_app

__all__ = ["create_app"]
__version__ = "0.1.0"

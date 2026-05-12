# SCOPE: both
# scope: both
"""STATUS: ORPHAN — Docker service configured, skill/hook exist, but zero production callers.
Wire when Jupyter MCP sandbox is activated (JUPYTER_SANDBOX=true).
See: docs/04-Concepts/root/gpu-sandbox.md for the design.

Jupyter REST API client for Cognitive OS agent code execution.

Provides sandboxed Python execution via a Jupyter kernel server.
Uses only stdlib (urllib) — no external dependencies.
Python 3.9+ compatible.
"""

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_BASE_URL = "http://localhost:8888"
_DEFAULT_TOKEN = "test-token"
_CONNECT_TIMEOUT = 3
_EXECUTE_TIMEOUT = 60


def _base_url() -> str:
    """Return the Jupyter server base URL."""
    return os.getenv("JUPYTER_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")


def _token() -> str:
    """Return the Jupyter authentication token."""
    return os.getenv("JUPYTER_TOKEN", _DEFAULT_TOKEN)


def _headers() -> Dict[str, str]:
    """Return default headers including auth token."""
    return {
        "Authorization": f"token {_token()}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Low-level HTTP helpers
# ---------------------------------------------------------------------------


def _http_get(path: str, timeout: int = _CONNECT_TIMEOUT) -> Optional[Dict[str, Any]]:
    """GET request to Jupyter API. Returns parsed JSON or None on failure."""
    url = f"{_base_url()}{path}"
    req = urllib.request.Request(url, headers=_headers(), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError) as exc:
        logger.debug("Jupyter GET %s failed: %s", path, exc)
        return None


def _http_post(
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    timeout: int = _CONNECT_TIMEOUT,
) -> Optional[Dict[str, Any]]:
    """POST request to Jupyter API. Returns parsed JSON or None on failure."""
    url = f"{_base_url()}{path}"
    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError) as exc:
        logger.debug("Jupyter POST %s failed: %s", path, exc)
        return None


def _http_delete(path: str, timeout: int = _CONNECT_TIMEOUT) -> bool:
    """DELETE request to Jupyter API. Returns True on success."""
    url = f"{_base_url()}{path}"
    req = urllib.request.Request(url, headers=_headers(), method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        logger.debug("Jupyter DELETE %s failed: %s", path, exc)
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def is_jupyter_available() -> bool:
    """Check if Jupyter server is reachable.

    Performs a GET to /api/status with the configured token.
    Returns True if the server responds with 200.
    """
    result = _http_get(f"/api/status?token={_token()}")
    return result is not None


def list_kernels() -> List[Dict[str, Any]]:
    """List all running Jupyter kernels.

    Returns:
        List of kernel info dicts with keys: id, name, execution_state, etc.
        Empty list if Jupyter is unavailable.
    """
    result = _http_get("/api/kernels")
    if result is None:
        return []
    if isinstance(result, list):
        return result
    return []


def create_kernel(name: str = "python3") -> Optional[str]:
    """Create a new Jupyter kernel.

    Args:
        name: Kernel spec name (default: python3).

    Returns:
        Kernel ID string, or None on failure.
    """
    result = _http_post("/api/kernels", {"name": name})
    if result is None:
        return None
    return result.get("id")


def delete_kernel(kernel_id: str) -> bool:
    """Shut down a running kernel.

    Args:
        kernel_id: The kernel ID to shut down.

    Returns:
        True if successfully deleted.
    """
    return _http_delete(f"/api/kernels/{kernel_id}")


def execute_code(
    code: str,
    kernel: str = "python3",
    timeout: int = _EXECUTE_TIMEOUT,
    kernel_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute code in a Jupyter kernel.

    Creates a kernel if none exists (or uses the provided kernel_id).
    Sends an execute_request via the Jupyter REST API.

    Args:
        code: Python code to execute.
        kernel: Kernel spec name for new kernels (default: python3).
        timeout: Maximum seconds to wait for execution.
        kernel_id: Optional existing kernel ID to reuse.

    Returns:
        Dict with keys:
            - stdout: str — captured standard output
            - stderr: str — captured standard error
            - result: str | None — execution result (repr of last expression)
            - success: bool — whether execution completed without error
            - error: str | None — error message if execution failed
    """
    empty_result = {
        "stdout": "",
        "stderr": "",
        "result": None,
        "success": False,
        "error": None,
    }

    # Check availability
    if not is_jupyter_available():
        empty_result["error"] = "Jupyter server is not available"
        return empty_result

    # Get or create a kernel
    kid = kernel_id
    created_kernel = False
    if kid is None:
        # Try to reuse an existing kernel
        kernels = list_kernels()
        for k in kernels:
            if k.get("name") == kernel:
                kid = k["id"]
                break
        if kid is None:
            kid = create_kernel(kernel)
            created_kernel = True
            if kid is None:
                empty_result["error"] = f"Failed to create kernel '{kernel}'"
                return empty_result
            # Give kernel time to start
            time.sleep(1)

    # Execute via the REST execute endpoint
    # Jupyter REST API: POST /api/kernels/{kernel_id}/execute
    payload = {
        "code": code,
    }
    result = _http_post(
        f"/api/kernels/{kid}/execute",
        payload,
        timeout=timeout,
    )

    if result is None:
        # Fallback: try the legacy /api/execute endpoint
        result = _http_post(
            "/api/execute",
            {"kernel_id": kid, "code": code},
            timeout=timeout,
        )

    if result is None:
        empty_result["error"] = "Failed to execute code via Jupyter API"
        return empty_result

    # Parse the execution result
    stdout = ""
    stderr = ""
    exec_result = None
    success = True
    error = None

    # Handle different response formats from Jupyter
    if "status" in result and result["status"] == "error":
        success = False
        error = result.get("traceback", result.get("evalue", "Unknown error"))
        if isinstance(error, list):
            error = "\n".join(error)
        stderr = error

    # Standard output parsing
    if "outputs" in result:
        for output in result.get("outputs", []):
            output_type = output.get("output_type", "")
            if output_type == "stream":
                name = output.get("name", "stdout")
                text = output.get("text", "")
                if name == "stderr":
                    stderr += text
                else:
                    stdout += text
            elif output_type == "execute_result":
                data = output.get("data", {})
                exec_result = data.get("text/plain", "")
            elif output_type == "error":
                success = False
                tb = output.get("traceback", [])
                error = "\n".join(tb) if isinstance(tb, list) else str(tb)
                stderr += output.get("evalue", "")
    else:
        # Simple response format
        stdout = result.get("stdout", result.get("output", ""))
        stderr = result.get("stderr", "")
        exec_result = result.get("result", result.get("data", None))
        if "error" in result:
            success = False
            error = result["error"]
        elif "status" in result:
            success = result["status"] in ("ok", "success", "complete")

    return {
        "stdout": stdout,
        "stderr": stderr,
        "result": exec_result,
        "success": success,
        "error": error,
    }


def is_sandbox_mode() -> bool:
    """Check if Jupyter sandbox mode is enabled.

    When JUPYTER_SANDBOX=true, Python execution should be routed
    to Jupyter instead of the local shell.
    """
    return os.getenv("JUPYTER_SANDBOX", "false").lower().strip() in ("true", "1", "yes")

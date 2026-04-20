# SCOPE: both
# scope: both
"""Multi-provider notification system for Cognitive OS.

Supports Telegram, Slack webhooks, and generic HTTP webhooks.
Provider configured via NOTIFY_PROVIDER env var.
Uses only stdlib (urllib) — no external dependencies.
Python 3.9+ compatible.
"""

import json
import logging
import os
import time
import urllib.request
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

_PROVIDERS = ("telegram", "slack", "webhook", "none")


def _get_provider() -> str:
    """Return the configured provider name, defaulting to 'none'."""
    provider = os.getenv("NOTIFY_PROVIDER", "none").lower().strip()
    if provider not in _PROVIDERS:
        logger.warning(
            "Unknown NOTIFY_PROVIDER=%r, falling back to 'none'", provider
        )
        return "none"
    return provider


# ---------------------------------------------------------------------------
# Low-level HTTP helper
# ---------------------------------------------------------------------------


def _http_post(
    url: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 10,
) -> bool:
    """POST JSON to *url*. Returns True on 2xx."""
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception as exc:
        logger.warning("Notification HTTP POST failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Telegram provider
# ---------------------------------------------------------------------------


def _telegram_config() -> Optional[Tuple[str, str]]:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return None
    return token, chat_id


def _telegram_send(text: str) -> bool:
    cfg = _telegram_config()
    if cfg is None:
        logger.debug("Telegram not configured, skipping")
        return False

    token, chat_id = cfg
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    return _http_post(url, {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    })


# ---------------------------------------------------------------------------
# Slack provider
# ---------------------------------------------------------------------------


def _slack_send(text: str, blocks: Optional[List[Dict[str, Any]]] = None) -> bool:
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        logger.debug("Slack webhook not configured, skipping")
        return False

    payload: Dict[str, Any] = {"text": text}
    if blocks:
        payload["blocks"] = blocks
    return _http_post(url, payload)


# ---------------------------------------------------------------------------
# Generic webhook provider
# ---------------------------------------------------------------------------


def _webhook_send(payload: Dict[str, Any]) -> bool:
    url = os.getenv("WEBHOOK_URL")
    if not url:
        logger.debug("Webhook URL not configured, skipping")
        return False
    return _http_post(url, payload)


# ---------------------------------------------------------------------------
# Message formatting helpers
# ---------------------------------------------------------------------------

_EVENT_EMOJI = {
    "phase_start": ">>",
    "phase_complete": "[OK]",
    "phase_fail": "[FAIL]",
    "pipeline_complete": "[DONE]",
    "batch_summary": "[BATCH]",
}


def _fmt_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return ""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = seconds / 60
    return f"{minutes:.1f}min"


def _telegram_format(
    event: str,
    title: str,
    details: Dict[str, Any],
) -> str:
    """Build a Telegram Markdown message."""
    tag = _EVENT_EMOJI.get(event, "[-]")
    lines = [f"*{tag} {title}*"]

    if details.get("change"):
        lines.append(f"Change: `{details['change']}`")
    if details.get("phase"):
        lines.append(f"Phase: *{details['phase'].upper()}*")
    if details.get("duration_s") is not None:
        lines.append(f"Duration: {_fmt_duration(details['duration_s'])}")
    if details.get("error"):
        err = str(details["error"])[:500]
        lines.append(f"Error: `{err}`")
    if details.get("resume_cmd"):
        lines.append(f"Resume: `{details['resume_cmd']}`")

    # Batch results
    if details.get("results"):
        results = details["results"]
        ok = sum(1 for r in results if r.get("success"))
        fail = len(results) - ok
        lines.append(f"Total: {len(results)} | OK: {ok} | FAIL: {fail}")
        for r in results:
            st = "OK" if r.get("success") else "FAIL"
            elapsed = _fmt_duration(r.get("elapsed_s"))
            suffix = f" ({elapsed})" if elapsed else ""
            lines.append(f"`[{st}]` {r.get('name', '?')}{suffix}")
        if fail > 0:
            lines.append("\n*Resume failed:*")
            for r in results:
                if not r.get("success") and r.get("resume_cmd"):
                    lines.append(f"`{r['resume_cmd']}`")

    if details.get("total_duration_s") is not None:
        lines.append(f"Total time: {_fmt_duration(details['total_duration_s'])}")

    return "\n".join(lines)


def _slack_format(
    event: str,
    title: str,
    details: Dict[str, Any],
) -> Tuple[str, List[Dict[str, Any]]]:
    """Build Slack blocks + fallback text."""
    tag = _EVENT_EMOJI.get(event, "[-]")
    fallback = f"{tag} {title}"
    blocks: List[Dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{tag} {title}"},
        }
    ]

    fields: List[Dict[str, str]] = []
    if details.get("change"):
        fields.append({"type": "mrkdwn", "text": f"*Change:* `{details['change']}`"})
    if details.get("phase"):
        fields.append({"type": "mrkdwn", "text": f"*Phase:* {details['phase'].upper()}"})
    if details.get("duration_s") is not None:
        fields.append({"type": "mrkdwn", "text": f"*Duration:* {_fmt_duration(details['duration_s'])}"})
    if details.get("error"):
        err = str(details["error"])[:500]
        fields.append({"type": "mrkdwn", "text": f"*Error:* `{err}`"})

    if fields:
        blocks.append({"type": "section", "fields": fields})

    if details.get("resume_cmd"):
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Resume:* `{details['resume_cmd']}`"},
        })

    # Batch results
    if details.get("results"):
        results = details["results"]
        ok = sum(1 for r in results if r.get("success"))
        fail = len(results) - ok
        summary = f"Total: {len(results)} | OK: {ok} | FAIL: {fail}"
        if details.get("total_duration_s") is not None:
            summary += f" | Time: {_fmt_duration(details['total_duration_s'])}"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": summary},
        })
        lines = []
        for r in results:
            st = ":white_check_mark:" if r.get("success") else ":x:"
            elapsed = _fmt_duration(r.get("elapsed_s"))
            suffix = f" ({elapsed})" if elapsed else ""
            lines.append(f"{st} `{r.get('name', '?')}`{suffix}")
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(lines)},
        })

    return fallback, blocks


def _webhook_format(
    event: str,
    title: str,
    details: Dict[str, Any],
) -> Dict[str, Any]:
    """Build plain JSON payload for generic webhooks."""
    payload: Dict[str, Any] = {
        "event": event,
        "title": title,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    payload.update(details)
    return payload


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def _dispatch(event: str, title: str, details: Dict[str, Any]) -> bool:
    """Format and send a notification via the configured provider."""
    provider = _get_provider()

    if provider == "none":
        logger.debug("Notifications disabled (NOTIFY_PROVIDER=none)")
        return False

    if provider == "telegram":
        text = _telegram_format(event, title, details)
        return _telegram_send(text)

    if provider == "slack":
        fallback, blocks = _slack_format(event, title, details)
        return _slack_send(fallback, blocks)

    if provider == "webhook":
        payload = _webhook_format(event, title, details)
        return _webhook_send(payload)

    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def notify_phase_start(
    change: str,
    phase: str,
) -> bool:
    """Notify that a phase is starting."""
    return _dispatch("phase_start", f"Phase starting: {phase}", {
        "change": change,
        "phase": phase,
    })


def notify_phase_complete(
    change: str,
    phase: str,
    duration_s: Optional[float] = None,
) -> bool:
    """Notify that a phase completed successfully."""
    return _dispatch("phase_complete", f"Phase complete: {phase}", {
        "change": change,
        "phase": phase,
        "duration_s": duration_s,
    })


def notify_phase_fail(
    change: str,
    phase: str,
    error: str = "",
    resume_cmd: str = "",
    duration_s: Optional[float] = None,
) -> bool:
    """Notify that a phase failed."""
    if not resume_cmd:
        resume_cmd = f"/sdd-continue {change}"
    return _dispatch("phase_fail", f"Phase FAILED: {phase}", {
        "change": change,
        "phase": phase,
        "error": error,
        "resume_cmd": resume_cmd,
        "duration_s": duration_s,
    })


def notify_pipeline_complete(
    change: str,
    phases_completed: Optional[List[str]] = None,
    total_duration_s: Optional[float] = None,
) -> bool:
    """Notify that a full SDD pipeline completed."""
    details: Dict[str, Any] = {"change": change}
    if phases_completed:
        details["phases_completed"] = phases_completed
    if total_duration_s is not None:
        details["total_duration_s"] = total_duration_s
    return _dispatch("pipeline_complete", f"Pipeline complete: {change}", details)


def notify_batch_summary(
    batch_id: str,
    results: List[Dict[str, Any]],
    total_duration_s: Optional[float] = None,
) -> bool:
    """Notify a batch execution summary.

    Each result dict should contain:
      - name: str
      - success: bool
      - elapsed_s: Optional[float]
      - resume_cmd: Optional[str]
    """
    return _dispatch("batch_summary", f"Batch complete: {batch_id}", {
        "results": results,
        "total_duration_s": total_duration_s,
    })


# ---------------------------------------------------------------------------
# Convenience: raw message (for backward compat / ad-hoc usage)
# ---------------------------------------------------------------------------


def send_raw(text: str) -> bool:
    """Send a raw text message via the configured provider.

    For Telegram/Slack this sends text directly.
    For webhook, wraps in ``{"event": "raw", "text": ...}``.
    """
    provider = _get_provider()
    if provider == "none":
        return False
    if provider == "telegram":
        return _telegram_send(text)
    if provider == "slack":
        return _slack_send(text)
    if provider == "webhook":
        return _webhook_send({"event": "raw", "text": text})
    return False

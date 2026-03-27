"""Telegram notifications for backend pipeline."""

import json
import logging
import os
import urllib.request

logger = logging.getLogger(__name__)


def _get_config() -> tuple[str, str] | None:
    """Get Telegram bot token and chat ID from env."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return None
    return token, chat_id


def send_message(text: str) -> bool:
    """Send a Telegram message. Returns True if sent."""
    config = _get_config()
    if not config:
        logger.debug("Telegram not configured, skipping notification")
        return False

    token, chat_id = config
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")
        return False


def notify_phase_success(
    workflow_type: str,
    workflow_id: str,
    phase: str,
    ticket_id: str = "",
    service: str = "",
) -> None:
    """Notify that a phase completed successfully."""
    service_line = f"\nService: `{service}`" if service else ""
    send_message(
        f"*BACKEND-WORKFLOW* `{workflow_id}`\n"
        f"Type: {workflow_type}{service_line}\n"
        f"Task: `{ticket_id}`\n"
        f"Phase *{phase.upper()}* completed"
    )


def notify_phase_failure(
    workflow_type: str,
    workflow_id: str,
    phase: str,
    ticket_id: str = "",
    service: str = "",
    error: str = "",
) -> None:
    """Notify that a phase failed."""
    error_detail = f"\nError: `{error[:500]}`" if error else ""
    service_line = f"\nService: `{service}`" if service else ""
    send_message(
        f"*BACKEND-WORKFLOW FAILED* `{workflow_id}`\n"
        f"Type: {workflow_type}{service_line}\n"
        f"Task: `{ticket_id}`\n"
        f"Phase *{phase.upper()}* failed{error_detail}\n"
        f"Resume: `uv run .cognitive-os/workflows/run.py resume "
        f"--workflow-id {workflow_id}`"
    )


def notify_pipeline_complete(
    workflow_type: str,
    workflow_id: str,
    pr_url: str = "",
    duration: str = "",
    ticket_id: str = "",
    service: str = "",
) -> None:
    """Notify pipeline completed all phases."""
    pr_line = f"\nPR: {pr_url}" if pr_url else ""
    duration_line = f"\nDuration: {duration}" if duration else ""
    service_line = f"\nService: `{service}`" if service else ""
    send_message(
        f"*BACKEND-WORKFLOW COMPLETE* `{workflow_id}`\n"
        f"Type: {workflow_type}{service_line}\n"
        f"Task: `{ticket_id}`{pr_line}{duration_line}"
    )

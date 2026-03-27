"""ClickUp API client for task management."""

import os
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .data_types import ClickUpTaskData

CLICKUP_BASE_URL = "https://api.clickup.com/api/v2"
CLICKUP_TEAM_ID = os.environ.get("CLICKUP_TEAM_ID", "9011665372")


def _get_headers() -> dict:
    token = os.environ.get("CLICKUP_API_TOKEN", "")
    return {
        "Authorization": token,
        "Content-Type": "application/json",
    }


def _is_custom_task_id(task_id: str) -> bool:
    """Check if task_id looks like a custom ID (e.g., DEV-1232) vs native."""
    return bool(re.match(r"^[A-Z]+-\d+$", task_id))


def _parse_task_response(data: dict) -> ClickUpTaskData:
    """Parse ClickUp API response into ClickUpTaskData."""
    tags = [t["name"] for t in data.get("tags", [])]
    assignees = [
        a["username"]
        for a in data.get("assignees", [])
        if a.get("username")
    ]
    custom_fields = {
        cf["name"]: cf.get("value")
        for cf in data.get("custom_fields", [])
        if cf.get("value") is not None
    }

    return ClickUpTaskData(
        task_id=data["id"],
        custom_id=data.get("custom_id", ""),
        name=data.get("name", ""),
        description=data.get("description", ""),
        status=data.get("status", {}).get("status", ""),
        tags=tags,
        assignees=assignees,
        url=data.get("url", ""),
        custom_fields=custom_fields,
        attachments=data.get("attachments", []),
    )


def fetch_task(task_id: str) -> Tuple[bool, Optional[ClickUpTaskData]]:
    """Fetch a task from ClickUp by ID (supports both native and custom IDs).

    Returns:
        (True, ClickUpTaskData) on success, (False, None) on failure.
    """
    try:
        with httpx.Client(timeout=15) as client:
            if _is_custom_task_id(task_id):
                resp = client.get(
                    f"{CLICKUP_BASE_URL}/task/{task_id}",
                    headers=_get_headers(),
                    params={
                        "custom_task_ids": "true",
                        "team_id": CLICKUP_TEAM_ID,
                    },
                )
            else:
                resp = client.get(
                    f"{CLICKUP_BASE_URL}/task/{task_id}",
                    headers=_get_headers(),
                )

            resp.raise_for_status()
            data = resp.json()

            # Custom ID endpoint returns a list
            if isinstance(data, dict) and "tasks" in data:
                tasks = data["tasks"]
                if not tasks:
                    print(f"  No task found with custom ID: {task_id}")
                    return False, None
                data = tasks[0]

        return True, _parse_task_response(data)

    except httpx.HTTPStatusError as e:
        print(
            f"  ClickUp API error: "
            f"{e.response.status_code} - {e.response.text[:200]}"
        )
        return False, None
    except Exception as e:
        print(f"  ClickUp fetch error: {e}")
        return False, None


def fetch_task_attachments(
    task_id: str,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Fetch attachments for a ClickUp task.

    Returns:
        (True, list of attachment dicts) on success, (False, []) on failure.
    """
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                f"{CLICKUP_BASE_URL}/task/{task_id}",
                headers=_get_headers(),
                params={"include_subtasks": "true"},
            )
            resp.raise_for_status()
            data = resp.json()
            attachments = data.get("attachments", [])
        return True, attachments
    except Exception as e:
        print(f"  ClickUp attachments error: {e}")
        return False, []


def update_task_status(
    task_id: str, status: str
) -> Tuple[bool, str]:
    """Update a task's status in ClickUp."""
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.put(
                f"{CLICKUP_BASE_URL}/task/{task_id}",
                headers=_get_headers(),
                json={"status": status},
            )
            resp.raise_for_status()
        return True, "ok"
    except httpx.HTTPStatusError as e:
        return False, f"ClickUp status update error: {e.response.status_code}"
    except Exception as e:
        return False, str(e)


def add_task_comment(
    task_id: str, comment_text: str
) -> Tuple[bool, str]:
    """Add a comment to a ClickUp task."""
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{CLICKUP_BASE_URL}/task/{task_id}/comment",
                headers=_get_headers(),
                json={"comment_text": comment_text},
            )
            resp.raise_for_status()
        return True, "ok"
    except httpx.HTTPStatusError as e:
        return False, f"ClickUp comment error: {e.response.status_code}"
    except Exception as e:
        return False, str(e)

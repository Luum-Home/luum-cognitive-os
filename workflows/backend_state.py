"""Persistent state for backend automation workflows."""

import json
import logging
import os
import sys
from typing import Optional

from lib.data_types import BackendWorkflowStateData
from lib.utils import get_project_root


def setup_logger(workflow_id: str) -> logging.Logger:
    """Logger that writes to console and file in state/{id}/."""
    project_root = get_project_root()
    log_dir = os.path.join(
        project_root, ".cognitive-os", "workflows", "state", workflow_id
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "execution.log")

    logger = logging.getLogger(f"backend_workflow_{workflow_id}")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fh = logging.FileHandler(log_file, mode="a")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(
        logging.Formatter(
            "\033[2m%(asctime)s\033[0m %(message)s",
            datefmt="%H:%M:%S",
        )
    )

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


class BackendWorkflowState:
    STATE_FILENAME = "workflow_state.json"

    def __init__(
        self,
        workflow_id: str,
        workflow_type: str,
        ticket_id: str = "",
        name: str = "",
        service_name: str = "",
        service_path: str = "",
        service_language: str = "",
    ):
        self.workflow_id = workflow_id
        self.data = BackendWorkflowStateData(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            ticket_id=ticket_id,
            name=name,
            service_name=service_name,
            service_path=service_path,
            service_language=service_language,
        )
        self.logger = logging.getLogger(__name__)

    def update(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self.data, key):
                setattr(self.data, key, value)
            else:
                self.logger.warning(
                    f"Unknown state key ignored: {key}"
                )

    def get(self, key: str, default=None):
        return getattr(self.data, key, default)

    def mark_phase_completed(self, phase: str) -> None:
        if phase not in self.data.phases_completed:
            self.data.phases_completed.append(phase)

    def get_state_dir(self) -> str:
        project_root = get_project_root()
        return os.path.join(
            project_root, ".cognitive-os", "workflows", "state", self.workflow_id
        )

    def save(self) -> None:
        state_dir = self.get_state_dir()
        os.makedirs(state_dir, exist_ok=True)
        state_path = os.path.join(state_dir, self.STATE_FILENAME)
        tmp_path = state_path + ".tmp"
        try:
            with open(tmp_path, "w") as f:
                json.dump(self.data.model_dump(), f, indent=2)
            os.replace(tmp_path, state_path)
        except OSError as exc:
            self.logger.error(f"Failed to save state: {exc}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @classmethod
    def load(cls, workflow_id: str) -> Optional["BackendWorkflowState"]:
        project_root = get_project_root()
        state_dir = os.path.join(
            project_root, ".cognitive-os", "workflows", "state", workflow_id
        )
        state_path = os.path.join(state_dir, cls.STATE_FILENAME)

        if not os.path.exists(state_path):
            return None

        with open(state_path, "r") as f:
            data = json.load(f)

        state = cls(
            workflow_id=workflow_id,
            workflow_type=data.get("workflow_type", "unknown"),
            ticket_id=data.get("ticket_id", ""),
            name=data.get("name", ""),
            service_name=data.get("service_name", ""),
            service_path=data.get("service_path", ""),
            service_language=data.get("service_language", ""),
        )
        state.data = BackendWorkflowStateData(**data)
        return state

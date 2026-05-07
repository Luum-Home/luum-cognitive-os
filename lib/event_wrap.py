# SCOPE: both
"""ADR-226 Slice C memoized step wrapper for replayable agent sessions."""
from __future__ import annotations

import functools
import hashlib
import inspect
import json
import os
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar, cast

from lib.session_bus import append_session_event, read_session_events

F = TypeVar("F", bound=Callable[..., Any])
_CALL_COUNTERS: dict[tuple[str, str], int] = defaultdict(int)
_REPLAY_COUNTERS: dict[tuple[str, str], int] = defaultdict(int)


class EventWrapError(RuntimeError):
    """Base error for ADR-226 event_wrap failures."""


class WrappedStepNotFound(EventWrapError):
    """Raised when replay requested a wrapped step that is not in the stream."""


class WrappedStepSignatureChanged(EventWrapError):
    """Raised when replay stream signature differs from current function."""


def _qualname(func: Callable[..., Any]) -> str:
    return f"{func.__module__}.{func.__qualname__}"


def _signature_sha(func: Callable[..., Any]) -> str:
    raw = f"{_qualname(func)}{inspect.signature(func)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value, sort_keys=True)
    except TypeError as exc:
        raise EventWrapError("event_wrap results must be JSON-serializable in Slice C") from exc
    return value


def _result_sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _replay_enabled() -> bool:
    return bool(os.environ.get("COS_REPLAY_FROM_SEQ"))


def _find_recorded_step(
    *,
    project_dir: str | Path,
    session_id: str,
    function_qualname: str,
    call_index: int,
) -> dict[str, Any]:
    for event in read_session_events(session_id, project_dir=project_dir, event_type="wrapped-step"):
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        if payload.get("function_qualname") == function_qualname and payload.get("call_index") == call_index:
            return payload
    raise WrappedStepNotFound(f"wrapped step not found: {function_qualname}#{call_index}")


def event_wrap(*, project_dir: str | Path, session_id: str) -> Callable[[F], F]:
    """Memoize a non-deterministic function into the ADR-226 session stream.

    Normal mode executes the function and appends a `wrapped-step` event with a
    JSON-serializable result. Replay mode (`COS_REPLAY_FROM_SEQ` set) returns the
    recorded result instead of executing the function, refusing if the function
    signature changed.
    """

    def decorate(func: F) -> F:
        function_qualname = _qualname(func)
        signature_sha = _signature_sha(func)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            counter_key = (session_id, function_qualname)
            if _replay_enabled():
                _REPLAY_COUNTERS[counter_key] += 1
                call_index = _REPLAY_COUNTERS[counter_key]
                recorded = _find_recorded_step(
                    project_dir=project_dir,
                    session_id=session_id,
                    function_qualname=function_qualname,
                    call_index=call_index,
                )
                if recorded.get("signature_sha") != signature_sha:
                    raise WrappedStepSignatureChanged(
                        f"signature changed for {function_qualname}: recorded={recorded.get('signature_sha')} current={signature_sha}"
                    )
                return recorded.get("result")

            _CALL_COUNTERS[counter_key] += 1
            call_index = _CALL_COUNTERS[counter_key]
            result = _jsonable(func(*args, **kwargs))
            append_session_event(
                "wrapped-step",
                {
                    "function_qualname": function_qualname,
                    "call_index": call_index,
                    "signature_sha": signature_sha,
                    "result": result,
                    "result_sha": _result_sha(result),
                },
                project_dir=project_dir,
                session_id=session_id,
            )
            return result

        return cast(F, wrapper)

    return decorate

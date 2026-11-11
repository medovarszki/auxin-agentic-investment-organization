"""Task state machine. States are the A2A 1.0 task states; no retries, only a timeout."""
from datetime import datetime, timedelta
from enum import StrEnum

# Every task, from WORKING (Mihály, 2026-11-11). The chains are synchronous: a scan or review task also waits for the
# tasks it starts downstream, so the whole chain has to fit.
TASK_TIMEOUT = timedelta(minutes=10)


class TaskState(StrEnum):
    SUBMITTED = "TASK_STATE_SUBMITTED"
    WORKING = "TASK_STATE_WORKING"
    COMPLETED = "TASK_STATE_COMPLETED"
    REJECTED = "TASK_STATE_REJECTED"
    FAILED = "TASK_STATE_FAILED"
    CANCELED = "TASK_STATE_CANCELED"


TERMINAL_STATES = frozenset(
    {TaskState.COMPLETED, TaskState.REJECTED, TaskState.FAILED, TaskState.CANCELED}
)

ALLOWED_TRANSITIONS: dict[TaskState, frozenset[TaskState]] = {
    TaskState.SUBMITTED: frozenset({TaskState.WORKING, TaskState.CANCELED}),
    TaskState.WORKING: frozenset(
        {TaskState.COMPLETED, TaskState.REJECTED, TaskState.FAILED, TaskState.CANCELED}
    ),
    **{state: frozenset() for state in TERMINAL_STATES},
}


class InvalidTransition(ValueError):
    pass


def transition(current: TaskState, new: TaskState) -> TaskState:
    if new not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransition(f"{current} -> {new} is not allowed")
    return new


def task_timeout(message_type: str) -> timedelta:
    return TASK_TIMEOUT


def is_timed_out(working_since: datetime, now: datetime) -> bool:
    return now - working_since >= TASK_TIMEOUT

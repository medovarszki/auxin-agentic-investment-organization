"""Task state machine. States are the A2A 1.0 task states; no retries, only a timeout."""
from datetime import datetime, timedelta
from enum import StrEnum

TASK_TIMEOUT = timedelta(minutes=60)  # the chain scan -> Research -> PM -> Execution is synchronous (6.3)
# The daily review runs one Research re-evaluation per open position, one after the other (6.4)
TASK_TIMEOUTS = {"review_trigger": timedelta(hours=4)}
MAX_REJECTION_ROUNDS = 2


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
    return TASK_TIMEOUTS.get(message_type, TASK_TIMEOUT)


def is_timed_out(working_since: datetime, now: datetime) -> bool:
    return now - working_since >= TASK_TIMEOUT


def can_resubmit(rejection_count: int) -> bool:
    """An item may come back after a rejection until it was rejected MAX_REJECTION_ROUNDS times."""
    return rejection_count < MAX_REJECTION_ROUNDS

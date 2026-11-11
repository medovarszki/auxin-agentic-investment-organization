from datetime import datetime, timedelta, timezone

import pytest

from auxin_schemas.task import (
    TERMINAL_STATES,
    InvalidTransition,
    TaskState,
    is_timed_out,
    task_timeout,
    transition,
)


def test_happy_path():
    state = transition(TaskState.SUBMITTED, TaskState.WORKING)
    assert transition(state, TaskState.COMPLETED) is TaskState.COMPLETED


@pytest.mark.parametrize("end", [TaskState.REJECTED, TaskState.FAILED, TaskState.CANCELED])
def test_working_can_end_in_any_terminal_state(end):
    assert transition(TaskState.WORKING, end) is end


def test_cannot_skip_working():
    with pytest.raises(InvalidTransition):
        transition(TaskState.SUBMITTED, TaskState.COMPLETED)


@pytest.mark.parametrize("terminal", sorted(TERMINAL_STATES))
def test_terminal_states_are_final(terminal):
    with pytest.raises(InvalidTransition):
        transition(terminal, TaskState.WORKING)


def test_states_match_a2a_names():
    assert {s.value for s in TaskState} == {
        "TASK_STATE_SUBMITTED",
        "TASK_STATE_WORKING",
        "TASK_STATE_COMPLETED",
        "TASK_STATE_REJECTED",
        "TASK_STATE_FAILED",
        "TASK_STATE_CANCELED",
    }


def test_timeout_is_ten_minutes_for_every_task():
    start = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
    assert not is_timed_out(start, start + timedelta(minutes=9, seconds=59))
    assert is_timed_out(start, start + timedelta(minutes=10))
    assert task_timeout("review_trigger") == task_timeout("idea") == timedelta(minutes=10)

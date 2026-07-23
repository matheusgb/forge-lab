from datetime import UTC, datetime

import pytest

from task_api.domain import Task, TaskAlreadyCompletedError, TaskStatus


def test_task_can_only_be_completed_once() -> None:
    now = datetime(2026, 7, 20, tzinfo=UTC)
    task = Task("1", "Learn", None, TaskStatus.PENDING, "u1", now, None, "r1")

    completed = task.complete(now)

    assert completed.status is TaskStatus.COMPLETED
    with pytest.raises(TaskAlreadyCompletedError):
        completed.complete(now)

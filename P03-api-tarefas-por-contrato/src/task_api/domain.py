from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum


class TaskStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"


@dataclass(frozen=True)
class Task:
    task_id: str
    title: str
    description: str | None
    status: TaskStatus
    created_by: str
    created_at: datetime
    completed_at: datetime | None
    request_id: str

    def complete(self, completed_at: datetime) -> Task:
        if self.status is TaskStatus.COMPLETED:
            raise TaskAlreadyCompletedError(self.task_id)
        return replace(
            self,
            status=TaskStatus.COMPLETED,
            completed_at=completed_at,
        )


class TaskError(Exception):
    code = "task_error"


class TaskNotFoundError(TaskError):
    code = "task_not_found"

    def __init__(self, task_id: str) -> None:
        super().__init__(f"task not found: {task_id}")
        self.task_id = task_id


class TaskAlreadyCompletedError(TaskError):
    code = "task_already_completed"

    def __init__(self, task_id: str) -> None:
        super().__init__(f"task already completed: {task_id}")
        self.task_id = task_id


class RepositoryUnavailableError(TaskError):
    code = "repository_unavailable"

    def __init__(self) -> None:
        super().__init__("task repository is unavailable")

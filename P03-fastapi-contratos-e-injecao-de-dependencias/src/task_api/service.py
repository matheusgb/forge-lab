from datetime import datetime
from uuid import uuid4

from task_api.domain import Task, TaskNotFoundError, TaskStatus
from task_api.repository import TaskRepository


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    def create(
        self,
        *,
        title: str,
        description: str | None,
        user_id: str,
        request_id: str,
        now: datetime,
    ) -> Task:
        task = Task(
            id=str(uuid4()),
            title=title,
            description=description,
            status=TaskStatus.PENDING,
            created_by=user_id,
            created_at=now,
            completed_at=None,
            request_id=request_id,
        )
        self.repository.add(task)
        return task

    def get(self, task_id: str) -> Task:
        task = self.repository.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return task

    def complete(self, task_id: str, *, now: datetime) -> Task:
        task = self.get(task_id)
        completed = task.complete(now)
        self.repository.update(completed)
        return completed

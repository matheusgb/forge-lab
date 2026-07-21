from typing import Protocol

from task_api.domain import Task


class TaskRepository(Protocol):
    def add(self, task: Task) -> None: ...

    def get(self, task_id: str) -> Task | None: ...

    def update(self, task: Task) -> None: ...

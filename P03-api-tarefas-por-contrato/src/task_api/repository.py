from typing import Protocol

from task_api.domain import Task


class TaskRepository(Protocol):
    def add(self, task: Task) -> None: ...

    def get(self, task_id: str) -> Task | None: ...

    def update(self, task: Task) -> None: ...


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def add(self, task: Task) -> None:
        self._tasks[task.id] = task

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def update(self, task: Task) -> None:
        self._tasks[task.id] = task

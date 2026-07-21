from task_api.domain import Task


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def add(self, task: Task) -> None:
        self._tasks[task.task_id] = task

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def update(self, task: Task) -> None:
        self._tasks[task.task_id] = task

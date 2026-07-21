from task_api.domain import RepositoryUnavailableError, Task


class FakeTaskRepository:
    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}

    def add(self, task: Task) -> None:
        self.tasks[task.task_id] = task

    def get(self, task_id: str) -> Task | None:
        return self.tasks.get(task_id)

    def update(self, task: Task) -> None:
        self.tasks[task.task_id] = task


class FailingTaskRepository(FakeTaskRepository):
    def get(self, task_id: str) -> Task | None:
        del task_id
        raise RepositoryUnavailableError

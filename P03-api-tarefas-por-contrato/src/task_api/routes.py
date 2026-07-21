from typing import Annotated

from fastapi import APIRouter, Path, status

from task_api.dependencies import (
    IdentityDependency,
    RepositoryDependency,
    RequestContextDependency,
)
from task_api.schemas import ErrorResponse, TaskCreate, TaskResponse
from task_api.service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])

TaskId = Annotated[str, Path(min_length=1, max_length=100)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={503: {"model": ErrorResponse, "description": "Repository unavailable"}},
)
def create_task(
    payload: TaskCreate,
    identity: IdentityDependency,
    context: RequestContextDependency,
    repository: RepositoryDependency,
) -> TaskResponse:
    task = TaskService(repository).create(
        title=payload.title,
        description=payload.description,
        user_id=identity.user_id,
        request_id=context.request_id,
        now=context.received_at,
    )
    return TaskResponse.from_task(task)


@router.get(
    "/{task_id}",
    responses={
        404: {"model": ErrorResponse, "description": "Task not found"},
        503: {"model": ErrorResponse, "description": "Repository unavailable"},
    },
)
def get_task(
    task_id: TaskId,
    identity: IdentityDependency,
    repository: RepositoryDependency,
) -> TaskResponse:
    del identity
    return TaskResponse.from_task(TaskService(repository).get(task_id))


@router.patch(
    "/{task_id}/complete",
    responses={
        404: {"model": ErrorResponse, "description": "Task not found"},
        409: {"model": ErrorResponse, "description": "Task already completed"},
        503: {"model": ErrorResponse, "description": "Repository unavailable"},
    },
)
def complete_task(
    task_id: TaskId,
    identity: IdentityDependency,
    context: RequestContextDependency,
    repository: RepositoryDependency,
) -> TaskResponse:
    del identity
    task = TaskService(repository).complete(task_id, now=context.received_at)
    return TaskResponse.from_task(task)

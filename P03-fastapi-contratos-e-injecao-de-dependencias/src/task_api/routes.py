from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, cast
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request, status

from task_api.repository import TaskRepository
from task_api.schemas import ErrorResponse, TaskCreate, TaskResponse
from task_api.service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])

TaskId = Annotated[str, Path(min_length=1, max_length=100)]


@dataclass(frozen=True)
class RequestContext:
    request_id: str
    received_at: datetime


def get_identity(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if x_user_id is None or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-ID header is required",
        )
    return x_user_id.strip()


def get_request_context(
    x_request_id: Annotated[str | None, Header()] = None,
) -> RequestContext:
    request_id = x_request_id.strip() if x_request_id and x_request_id.strip() else str(uuid4())
    return RequestContext(request_id=request_id, received_at=datetime.now(UTC))


def get_repository(request: Request) -> TaskRepository:
    return cast(TaskRepository, request.app.state.repository)


IdentityDependency = Annotated[str, Depends(get_identity)]
RequestContextDependency = Annotated[RequestContext, Depends(get_request_context)]
RepositoryDependency = Annotated[TaskRepository, Depends(get_repository)]


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
        user_id=identity,
        request_id=context.request_id,
        now=context.received_at,
    )
    return TaskResponse.model_validate(task)


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
    return TaskResponse.model_validate(TaskService(repository).get(task_id))


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
    return TaskResponse.model_validate(task)

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, cast
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Request, status

from task_api.contracts import TaskRepository


@dataclass(frozen=True)
class Identity:
    user_id: str


@dataclass(frozen=True)
class RequestContext:
    request_id: str
    received_at: datetime


def get_identity(x_user_id: Annotated[str | None, Header()] = None) -> Identity:
    if x_user_id is None or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-ID header is required",
        )
    return Identity(user_id=x_user_id.strip())


def get_request_context(
    x_request_id: Annotated[str | None, Header()] = None,
) -> RequestContext:
    request_id = x_request_id.strip() if x_request_id and x_request_id.strip() else str(uuid4())
    return RequestContext(request_id=request_id, received_at=datetime.now(UTC))


def get_repository(request: Request) -> TaskRepository:
    return cast(TaskRepository, request.app.state.repository)


IdentityDependency = Annotated[Identity, Depends(get_identity)]
RequestContextDependency = Annotated[RequestContext, Depends(get_request_context)]
RepositoryDependency = Annotated[TaskRepository, Depends(get_repository)]

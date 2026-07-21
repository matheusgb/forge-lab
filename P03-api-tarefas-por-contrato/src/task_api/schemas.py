from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from task_api.domain import Task, TaskStatus


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, Field(min_length=1, max_length=120)]
    description: Annotated[str | None, Field(max_length=500)] = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("title must not be blank")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str | None
    status: TaskStatus
    created_by: str
    created_at: datetime
    completed_at: datetime | None
    request_id: str

    @classmethod
    def from_task(cls, task: Task) -> TaskResponse:
        return cls(
            id=task.task_id,
            title=task.title,
            description=task.description,
            status=task.status,
            created_by=task.created_by,
            created_at=task.created_at,
            completed_at=task.completed_at,
            request_id=task.request_id,
        )


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail

from typing import Annotated

from pydantic import BaseModel, Field


class WorkResponse(BaseModel):
    boundary: str
    delay_seconds: float


class JobRequest(BaseModel):
    duration_seconds: Annotated[float, Field(gt=0, le=30)] = 1.0


class JobAccepted(BaseModel):
    job_id: str
    status: str


class HealthResponse(BaseModel):
    status: str
    correlation_id: str
    client_active: bool
    resource_active: bool

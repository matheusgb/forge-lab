from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from task_api.domain import RepositoryUnavailableError, TaskAlreadyCompletedError, TaskError
from task_api.repository import InMemoryTaskRepository, TaskRepository
from task_api.routes import router


def create_app(repository: TaskRepository | None = None) -> FastAPI:
    app = FastAPI(
        title="Task Contract API",
        version="1.0.0",
        description="Small API for creating, reading and completing tasks.",
    )
    app.state.repository = repository or InMemoryTaskRepository()
    app.include_router(router)

    app.add_exception_handler(TaskError, handle_task_error)

    return app


async def handle_task_error(request: Request, error: Exception) -> JSONResponse:
    del request
    if not isinstance(error, TaskError):
        raise error
    if isinstance(error, TaskAlreadyCompletedError):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(error, RepositoryUnavailableError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        status_code = status.HTTP_404_NOT_FOUND
    return _error_response(status_code, error.code, str(error))


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )

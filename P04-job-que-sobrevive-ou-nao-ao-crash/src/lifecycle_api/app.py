import time
from collections.abc import AsyncGenerator
from contextlib import ExitStack, asynccontextmanager
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, Query, Request, Response, status
from starlette.middleware.base import RequestResponseEndpoint

from lifecycle_api.components import ComponentFactory, EventJournal, ManagedComponent
from lifecycle_api.jobs import run_background_job
from lifecycle_api.schemas import HealthResponse, JobAccepted, JobRequest, WorkResponse

CORRELATION_HEADER = "X-Correlation-ID"
Delay = Annotated[float, Query(gt=0, le=2)]


def blocking_library_call(delay_seconds: float) -> None:
    time.sleep(delay_seconds)


def create_app(
    *,
    event_path: Path = Path("output/events.jsonl"),
    client_factory: ComponentFactory | None = None,
    resource_factory: ComponentFactory | None = None,
    fail_startup: bool = False,
    fail_shutdown: bool = False,
) -> FastAPI:
    journal = EventJournal(event_path)

    def default_client_factory() -> ManagedComponent:
        return ManagedComponent("client", journal)

    def default_resource_factory() -> ManagedComponent:
        return ManagedComponent(
            "resource",
            journal,
            fail_on_enter=fail_startup,
            fail_on_close=fail_shutdown,
        )

    selected_client_factory = (
        client_factory if client_factory is not None else default_client_factory
    )
    selected_resource_factory = (
        resource_factory if resource_factory is not None else default_resource_factory
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        with ExitStack() as stack:
            app.state.client = stack.enter_context(selected_client_factory())
            app.state.resource = stack.enter_context(selected_resource_factory())
            app.state.journal = journal
            journal.append("application_started")
            try:
                yield
            finally:
                journal.append("application_stopping")

    app = FastAPI(
        title="Lifecycle and Crash API",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def propagate_correlation_id(  # pyright: ignore[reportUnusedFunction]
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        received = request.headers.get(CORRELATION_HEADER, "").strip()
        correlation_id = received or str(uuid4())
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers[CORRELATION_HEADER] = correlation_id
        return response

    @app.get("/health", response_model=HealthResponse)
    async def health(  # pyright: ignore[reportUnusedFunction]
        request: Request,
    ) -> HealthResponse:
        return HealthResponse(
            status="ok",
            correlation_id=request.state.correlation_id,
            client_active=request.app.state.client.active,
            resource_active=request.app.state.resource.active,
        )

    @app.get("/work/sync", response_model=WorkResponse)
    def sync_work(  # pyright: ignore[reportUnusedFunction]
        delay_seconds: Delay = 0.1,
    ) -> WorkResponse:
        blocking_library_call(delay_seconds)
        return WorkResponse(boundary="def-threadpool", delay_seconds=delay_seconds)

    @app.get("/work/async-blocking", response_model=WorkResponse)
    async def async_blocking_work(  # pyright: ignore[reportUnusedFunction]
        delay_seconds: Delay = 0.1,
    ) -> WorkResponse:
        blocking_library_call(delay_seconds)
        return WorkResponse(boundary="async-event-loop", delay_seconds=delay_seconds)

    @app.post("/jobs", status_code=status.HTTP_202_ACCEPTED, response_model=JobAccepted)
    def schedule_job(  # pyright: ignore[reportUnusedFunction]
        payload: JobRequest,
        background_tasks: BackgroundTasks,
        request: Request,
    ) -> JobAccepted:
        job_id = str(uuid4())
        background_tasks.add_task(
            run_background_job,
            job_id,
            payload.duration_seconds,
            request.app.state.journal,
        )
        return JobAccepted(job_id=job_id, status="accepted")

    return app

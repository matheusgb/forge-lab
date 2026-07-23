import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import cast

from httpx2 import AsyncClient, Client, HTTPError
from pydantic import BaseModel


class Scenario(BaseModel):
    name: str
    concurrent_requests: int
    blocking_delay_seconds: float
    background_duration_seconds: float
    startup_timeout_seconds: float
    request_timeout_seconds: float


@dataclass
class Server:
    process: subprocess.Popen[bytes]
    base_url: str

    def stop(self, timeout: float, *, crash: bool = False) -> None:
        if self.process.poll() is not None:
            return
        if crash:
            self.process.kill()
        else:
            self.process.terminate()
        self.process.wait(timeout=timeout)


def load_scenario(path: Path) -> Scenario:
    return Scenario.model_validate_json(path.read_text(encoding="utf-8"))


def reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        return int(server.getsockname()[1])


@contextmanager
def running_server(
    event_path: Path,
    scenario: Scenario,
    *,
    fail_startup: bool = False,
    fail_shutdown: bool = False,
) -> Generator[Server]:
    port = reserve_port()
    environment = os.environ.copy()
    environment["P04_EVENT_PATH"] = str(event_path)
    environment.pop("P04_FAIL_STARTUP", None)
    environment.pop("P04_FAIL_SHUTDOWN", None)
    if fail_startup:
        environment["P04_FAIL_STARTUP"] = "1"
    if fail_shutdown:
        environment["P04_FAIL_SHUTDOWN"] = "1"

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "lifecycle_api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "critical",
        ],
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    server = Server(process, f"http://127.0.0.1:{port}")
    try:
        if not fail_startup:
            wait_until_ready(server, scenario)
        yield server
    finally:
        if process.poll() is None:
            try:
                server.stop(scenario.startup_timeout_seconds)
            except subprocess.TimeoutExpired:
                server.stop(scenario.startup_timeout_seconds, crash=True)


def wait_until_ready(server: Server, scenario: Scenario) -> None:
    deadline = time.monotonic() + scenario.startup_timeout_seconds
    with Client(base_url=server.base_url, timeout=scenario.request_timeout_seconds) as client:
        while time.monotonic() < deadline:
            if server.process.poll() is not None:
                raise RuntimeError("server exited before becoming ready")
            try:
                if client.get("/health").status_code == 200:
                    return
            except HTTPError, OSError:
                pass
            time.sleep(0.05)
    raise TimeoutError("server did not become ready")


async def measure_requests(server: Server, path: str, scenario: Scenario) -> float:
    async with AsyncClient(
        base_url=server.base_url,
        timeout=scenario.request_timeout_seconds,
    ) as client:
        started = perf_counter()
        responses = await asyncio.gather(
            *(
                client.get(
                    path,
                    params={"delay_seconds": scenario.blocking_delay_seconds},
                )
                for _ in range(scenario.concurrent_requests)
            )
        )
        elapsed = perf_counter() - started

    assert all(response.status_code == 200 for response in responses)
    return elapsed


def read_events(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [
        cast(dict[str, object], json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
    ]


def event_count(events: list[dict[str, object]], event_name: str) -> int:
    return sum(event.get("event") == event_name for event in events)


def require_event_count(
    events: list[dict[str, object]],
    event_name: str,
    expected: int,
) -> None:
    actual = event_count(events, event_name)
    if actual != expected:
        raise AssertionError(f"{event_name}: expected {expected}, observed {actual}")


def wait_for_event(path: Path, event_name: str, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if event_count(read_events(path), event_name):
            return
        time.sleep(0.02)
    raise TimeoutError(f"event not recorded: {event_name}")


def run() -> str:
    project = Path(__file__).resolve().parents[1]
    scenario = load_scenario(project / "scenario.yaml")
    evidence = project / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    paths = {
        name: evidence / f"events-{name}.jsonl"
        for name in ("graceful", "crash", "startup-failure", "shutdown-failure")
    }
    for path in paths.values():
        path.unlink(missing_ok=True)

    with running_server(paths["graceful"], scenario) as server:
        sync_seconds = asyncio.run(measure_requests(server, "/work/sync", scenario))
        async_blocking_seconds = asyncio.run(
            measure_requests(server, "/work/async-blocking", scenario)
        )
    graceful_events = read_events(paths["graceful"])

    with running_server(paths["crash"], scenario) as server:
        with Client(base_url=server.base_url, timeout=scenario.request_timeout_seconds) as client:
            response = client.post(
                "/jobs",
                json={"duration_seconds": scenario.background_duration_seconds},
            )
            response.raise_for_status()
            job_id = str(response.json()["job_id"])
        wait_for_event(paths["crash"], "job_started", scenario.request_timeout_seconds)
        server.stop(scenario.startup_timeout_seconds, crash=True)
    crash_events = read_events(paths["crash"])

    with running_server(paths["startup-failure"], scenario, fail_startup=True) as server:
        server.process.wait(timeout=scenario.startup_timeout_seconds)
    startup_events = read_events(paths["startup-failure"])

    with running_server(paths["shutdown-failure"], scenario, fail_shutdown=True) as server:
        server.stop(scenario.startup_timeout_seconds)
    shutdown_events = read_events(paths["shutdown-failure"])

    if async_blocking_seconds <= sync_seconds * 2:
        raise AssertionError("blocking async route did not serialize the concurrent requests")
    require_event_count(graceful_events, "client_closed", 1)
    require_event_count(graceful_events, "resource_closed", 1)
    require_event_count(crash_events, "job_started", 1)
    require_event_count(crash_events, "job_completed", 0)
    require_event_count(startup_events, "resource_start_failed", 1)
    require_event_count(startup_events, "client_closed", 1)
    require_event_count(shutdown_events, "resource_close_failed", 1)
    require_event_count(shutdown_events, "client_closed", 1)

    report = "\n".join(
        (
            f"Cenário: {scenario.name}",
            f"Requisições concorrentes: {scenario.concurrent_requests}",
            f"Espera bloqueante por requisição: {scenario.blocking_delay_seconds:.2f} s",
            f"Rota def em thread pool: {sync_seconds:.3f} s",
            f"Rota async def bloqueante: {async_blocking_seconds:.3f} s",
            f"Razão async bloqueante/def: {async_blocking_seconds / sync_seconds:.2f}x",
            "Fechamento gracioso: client=1, resource=1",
            f"Crash durante job {job_id}: started=1, completed=0",
            "Falha no startup: resource falhou e client adquirido foi fechado",
            "Falha no shutdown: resource falhou e client ainda foi fechado",
        )
    )
    (evidence / "result.txt").write_text(f"{report}\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(run())

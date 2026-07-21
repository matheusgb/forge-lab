import json
import os
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import cast

from httpx2 import Client, HTTPError


@dataclass(frozen=True)
class Scenario:
    name: str
    concurrent_requests: int
    blocking_delay_seconds: float
    background_duration_seconds: float
    startup_timeout_seconds: float
    request_timeout_seconds: float


def load_scenario(path: Path) -> Scenario:
    raw = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
    return Scenario(
        name=str(raw["name"]),
        concurrent_requests=int(cast(int, raw["concurrent_requests"])),
        blocking_delay_seconds=float(cast(float, raw["blocking_delay_seconds"])),
        background_duration_seconds=float(cast(float, raw["background_duration_seconds"])),
        startup_timeout_seconds=float(cast(float, raw["startup_timeout_seconds"])),
        request_timeout_seconds=float(cast(float, raw["request_timeout_seconds"])),
    )


def reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        return int(server.getsockname()[1])


def start_server(
    event_path: Path,
    scenario: Scenario,
    *,
    fail_startup: bool = False,
    fail_shutdown: bool = False,
) -> tuple[subprocess.Popen[bytes], str]:
    port = reserve_port()
    environment = os.environ.copy()
    environment["P04_EVENT_PATH"] = str(event_path)
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
    base_url = f"http://127.0.0.1:{port}"
    if not fail_startup:
        try:
            wait_until_ready(process, base_url, scenario)
        except BaseException:
            if process.poll() is None:
                process.kill()
                process.wait()
            raise
    return process, base_url


def wait_until_ready(
    process: subprocess.Popen[bytes],
    base_url: str,
    scenario: Scenario,
) -> None:
    deadline = time.monotonic() + scenario.startup_timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("server exited before becoming ready")
        try:
            with Client(timeout=scenario.request_timeout_seconds) as client:
                if client.get(f"{base_url}/health").status_code == 200:
                    return
        except (HTTPError, OSError):
            pass
        time.sleep(0.05)
    process.kill()
    process.wait()
    raise TimeoutError("server did not become ready")


def fetch(url: str, timeout_seconds: float) -> None:
    with Client(timeout=timeout_seconds) as client:
        response = client.get(url)
        response.raise_for_status()


def measure_requests(base_url: str, path: str, scenario: Scenario) -> float:
    url = f"{base_url}{path}?delay_seconds={scenario.blocking_delay_seconds}"
    started = perf_counter()
    with ThreadPoolExecutor(max_workers=scenario.concurrent_requests) as executor:
        futures = [
            executor.submit(fetch, url, scenario.request_timeout_seconds)
            for _ in range(scenario.concurrent_requests)
        ]
        for future in futures:
            future.result()
    return perf_counter() - started


def read_events(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [
        cast(dict[str, object], json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
    ]


def event_count(events: list[dict[str, object]], event_name: str) -> int:
    return sum(event.get("event") == event_name for event in events)


def wait_for_event(
    path: Path,
    event_name: str,
    timeout_seconds: float,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if event_count(read_events(path), event_name):
            return
        time.sleep(0.02)
    raise TimeoutError(f"event not recorded: {event_name}")


def reset(path: Path) -> None:
    path.unlink(missing_ok=True)


def run() -> str:
    project = Path(__file__).resolve().parents[1]
    scenario = load_scenario(project / "scenario.yaml")
    evidence = project / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)

    graceful_path = evidence / "events-graceful.jsonl"
    crash_path = evidence / "events-crash.jsonl"
    startup_failure_path = evidence / "events-startup-failure.jsonl"
    shutdown_failure_path = evidence / "events-shutdown-failure.jsonl"
    for path in (graceful_path, crash_path, startup_failure_path, shutdown_failure_path):
        reset(path)

    graceful, base_url = start_server(graceful_path, scenario)
    sync_seconds = measure_requests(base_url, "/work/sync", scenario)
    async_blocking_seconds = measure_requests(base_url, "/work/async-blocking", scenario)
    graceful.terminate()
    graceful.wait(timeout=scenario.startup_timeout_seconds)
    graceful_events = read_events(graceful_path)

    crash, crash_url = start_server(crash_path, scenario)
    with Client(timeout=scenario.request_timeout_seconds) as client:
        response = client.post(
            f"{crash_url}/jobs",
            json={"duration_seconds": scenario.background_duration_seconds},
        )
        response.raise_for_status()
        job_id = str(response.json()["job_id"])
    wait_for_event(crash_path, "job_started", scenario.request_timeout_seconds)
    crash.kill()
    crash.wait(timeout=scenario.startup_timeout_seconds)
    crash_events = read_events(crash_path)

    startup_failure, _ = start_server(
        startup_failure_path,
        scenario,
        fail_startup=True,
    )
    startup_failure.wait(timeout=scenario.startup_timeout_seconds)
    startup_events = read_events(startup_failure_path)

    shutdown_failure, _ = start_server(
        shutdown_failure_path,
        scenario,
        fail_shutdown=True,
    )
    shutdown_failure.terminate()
    shutdown_failure.wait(timeout=scenario.startup_timeout_seconds)
    shutdown_events = read_events(shutdown_failure_path)

    if async_blocking_seconds <= sync_seconds * 2:
        raise AssertionError("blocking async route did not serialize the concurrent requests")
    if event_count(graceful_events, "client_closed") != 1:
        raise AssertionError("client was not closed exactly once")
    if event_count(graceful_events, "resource_closed") != 1:
        raise AssertionError("resource was not closed exactly once")
    if event_count(crash_events, "job_started") != 1:
        raise AssertionError("background job did not start before the crash")
    if event_count(crash_events, "job_completed") != 0:
        raise AssertionError("background job unexpectedly completed before the crash")
    if event_count(startup_events, "client_closed") != 1:
        raise AssertionError("startup failure leaked the acquired client")
    if event_count(startup_events, "resource_start_failed") != 1:
        raise AssertionError("startup failure was not reproduced")
    if event_count(shutdown_events, "resource_close_failed") != 1:
        raise AssertionError("shutdown failure was not reproduced")
    if event_count(shutdown_events, "client_closed") != 1:
        raise AssertionError("shutdown failure skipped remaining cleanup")

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

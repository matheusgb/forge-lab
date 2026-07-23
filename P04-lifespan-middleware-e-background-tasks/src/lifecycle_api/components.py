import json
import os
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Self


class LifecycleFailure(RuntimeError):
    """Falha controlada ao abrir ou fechar um componente."""


class EventJournal:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()

    def append(self, event: str, **details: object) -> None:
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "pid": os.getpid(),
            "event": event,
            **details,
        }
        line = json.dumps(record, sort_keys=True)
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(f"{line}\n")
                stream.flush()
                os.fsync(stream.fileno())


@dataclass
class ManagedComponent:
    name: str
    journal: EventJournal
    fail_on_enter: bool = False
    fail_on_close: bool = False
    enter_calls: int = 0
    close_calls: int = 0
    active: bool = False

    @contextmanager
    def open(self) -> Generator[Self]:
        self.enter_calls += 1
        if self.fail_on_enter:
            self.journal.append(f"{self.name}_start_failed")
            raise LifecycleFailure(f"{self.name} failed during startup")
        self.active = True
        self.journal.append(f"{self.name}_started")
        try:
            yield self
        finally:
            self.close_calls += 1
            self.active = False
            if self.fail_on_close:
                self.journal.append(f"{self.name}_close_failed", close_calls=self.close_calls)
                raise LifecycleFailure(f"{self.name} failed during shutdown")
            self.journal.append(f"{self.name}_closed", close_calls=self.close_calls)


ComponentFactory = Callable[[], ManagedComponent]

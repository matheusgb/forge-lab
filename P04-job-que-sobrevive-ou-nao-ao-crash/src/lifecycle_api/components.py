import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from types import TracebackType


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


class ManagedComponent:
    def __init__(
        self,
        name: str,
        journal: EventJournal,
        *,
        fail_on_enter: bool = False,
        fail_on_close: bool = False,
    ) -> None:
        self.name = name
        self.journal = journal
        self.fail_on_enter = fail_on_enter
        self.fail_on_close = fail_on_close
        self.enter_calls = 0
        self.close_calls = 0
        self.active = False

    def __enter__(self) -> ManagedComponent:
        self.enter_calls += 1
        if self.fail_on_enter:
            self.journal.append(f"{self.name}_start_failed")
            raise LifecycleFailure(f"{self.name} failed during startup")
        self.active = True
        self.journal.append(f"{self.name}_started")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        del exc_type, exc_value, traceback
        self.close_calls += 1
        self.active = False
        if self.fail_on_close:
            self.journal.append(f"{self.name}_close_failed", close_calls=self.close_calls)
            raise LifecycleFailure(f"{self.name} failed during shutdown")
        self.journal.append(f"{self.name}_closed", close_calls=self.close_calls)
        return False


ComponentFactory = Callable[[], ManagedComponent]

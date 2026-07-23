import os
from pathlib import Path

from lifecycle_api.app import create_app


def enabled(name: str) -> bool:
    return os.environ.get(name) == "1"


app = create_app(
    event_path=Path(os.environ.get("P04_EVENT_PATH", "output/events.jsonl")),
    fail_startup=enabled("P04_FAIL_STARTUP"),
    fail_shutdown=enabled("P04_FAIL_SHUTDOWN"),
)

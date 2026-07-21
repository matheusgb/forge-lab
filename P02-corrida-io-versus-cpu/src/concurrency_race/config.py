import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast


@dataclass(frozen=True)
class IoConfig:
    operations: int
    delay_seconds: float


@dataclass(frozen=True)
class CpuConfig:
    inputs: tuple[int, ...]
    process_workers: int


@dataclass(frozen=True)
class Scenario:
    name: str
    repetitions: int
    heartbeat_interval_seconds: float
    io: IoConfig
    cpu: CpuConfig
    timeout_seconds: float


def _mapping(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return cast(dict[str, object], value)


def _integer(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _number(value: object, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field} must be a positive number")
    return float(value)


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _integer_tuple(value: object, field: str) -> tuple[int, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    items = cast(list[object], value)
    return tuple(_integer(item, field) for item in items)


def load_scenario(path: Path) -> Scenario:
    decoded = cast(object, json.loads(path.read_text(encoding="utf-8")))
    root = _mapping(decoded, "scenario")
    io = _mapping(root.get("io"), "io")
    cpu = _mapping(root.get("cpu"), "cpu")
    return Scenario(
        name=_text(root.get("name"), "name"),
        repetitions=_integer(root.get("repetitions"), "repetitions"),
        heartbeat_interval_seconds=_number(
            root.get("heartbeat_interval_seconds"), "heartbeat_interval_seconds"
        ),
        io=IoConfig(
            operations=_integer(io.get("operations"), "io.operations"),
            delay_seconds=_number(io.get("delay_seconds"), "io.delay_seconds"),
        ),
        cpu=CpuConfig(
            inputs=_integer_tuple(cpu.get("inputs"), "cpu.inputs"),
            process_workers=_integer(cpu.get("process_workers"), "cpu.process_workers"),
        ),
        timeout_seconds=_number(root.get("timeout_seconds"), "timeout_seconds"),
    )

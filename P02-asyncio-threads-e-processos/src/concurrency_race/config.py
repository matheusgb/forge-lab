from pathlib import Path
from typing import cast

import yaml
from pydantic import BaseModel, ConfigDict, PositiveFloat, PositiveInt


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class IoConfig(ConfigModel):
    operations: PositiveInt
    delay_seconds: PositiveFloat


class CpuConfig(ConfigModel):
    inputs: list[PositiveInt]
    process_workers: PositiveInt


class Scenario(ConfigModel):
    name: str
    repetitions: PositiveInt
    heartbeat_interval_seconds: PositiveFloat
    io: IoConfig
    cpu: CpuConfig
    timeout_seconds: PositiveFloat


def load_scenario(path: Path) -> Scenario:
    decoded = cast(object, yaml.safe_load(path.read_text(encoding="utf-8")))
    return Scenario.model_validate(decoded)

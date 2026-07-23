from pathlib import Path
from typing import Literal
from uuid import UUID

import yaml
from pydantic import BaseModel, ConfigDict, PositiveInt


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_a_id: UUID
    tenant_b_id: UUID
    orphan_tenant_id: UUID
    external_id: str
    valid_total_cents: PositiveInt
    valid_status: Literal["pending", "paid", "cancelled"]


def load_scenario(path: Path) -> Scenario:
    return Scenario.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))

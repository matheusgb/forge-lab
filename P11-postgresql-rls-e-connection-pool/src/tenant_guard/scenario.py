from pathlib import Path
from typing import Any
from uuid import UUID

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Tenant(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    name: str = Field(min_length=1)
    documents: tuple[str, ...] = Field(min_length=1)


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tenants: tuple[Tenant, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def tenant_ids_are_unique(self) -> Scenario:
        tenant_ids = [tenant.id for tenant in self.tenants]
        if len(tenant_ids) != len(set(tenant_ids)):
            raise ValueError("tenant ids must be unique")
        return self


def load_scenario(path: Path) -> Scenario:
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Scenario.model_validate(raw)

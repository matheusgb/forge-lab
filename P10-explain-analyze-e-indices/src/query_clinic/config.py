from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, Field, PostgresDsn, model_validator


class SeedConfig(BaseModel):
    row_count: int = Field(ge=10_000)
    customer_count: int = Field(ge=20)
    tenant_count: int = Field(ge=2)
    pending_every: int = Field(ge=2)


class TargetConfig(BaseModel):
    tenant_id: int = Field(ge=1)
    status: Literal["pending"]
    page_size: int = Field(ge=1, le=500)
    n_plus_one_rows: int = Field(ge=1, le=100)


class Scenario(BaseModel):
    database_url: PostgresDsn
    seed: SeedConfig
    target: TargetConfig

    @model_validator(mode="after")
    def validate_deterministic_distribution(self) -> Scenario:
        database = urlsplit(str(self.database_url))
        if (
            database.hostname not in {"127.0.0.1", "localhost"}
            or database.port != 55440
            or database.username != "clinic"
            or database.path != "/query_clinic"
        ):
            raise ValueError(
                "database_url precisa apontar para clinic@localhost:55440/query_clinic"
            )

        if self.target.tenant_id > self.seed.tenant_count:
            raise ValueError("target.tenant_id precisa existir no conjunto gerado")

        cycle = self.seed.tenant_count * self.seed.pending_every
        if self.seed.row_count % cycle != 0:
            raise ValueError("seed.row_count precisa fechar ciclos completos de tenant e status")

        rows_for_target = self.seed.row_count // cycle
        if self.target.page_size > rows_for_target:
            raise ValueError("target.page_size excede as linhas pendentes do tenant")
        if self.target.n_plus_one_rows > rows_for_target:
            raise ValueError("target.n_plus_one_rows excede as linhas pendentes do tenant")
        return self

    @property
    def dsn(self) -> str:
        return str(self.database_url)


def load_scenario(path: Path) -> Scenario:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Scenario.model_validate(raw)

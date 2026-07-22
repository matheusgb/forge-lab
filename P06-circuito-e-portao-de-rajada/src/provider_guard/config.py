import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from provider_guard.errors import MissingSecretError


@dataclass(frozen=True)
class ProviderConfig:
    endpoint: str
    api_key: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.endpoint:
            raise ValueError("provider endpoint must not be empty")
        if not self.api_key:
            raise MissingSecretError("provider secret must not be empty")

    @classmethod
    def from_env(
        cls,
        *,
        variable_name: str = "P06_PROVIDER_API_KEY",
        endpoint: str = "https://provider.test",
        environ: Mapping[str, str] | None = None,
    ) -> ProviderConfig:
        source = os.environ if environ is None else environ
        api_key = source.get(variable_name)
        if not api_key:
            raise MissingSecretError(f"required environment variable is missing: {variable_name}")
        return cls(endpoint=endpoint, api_key=api_key)

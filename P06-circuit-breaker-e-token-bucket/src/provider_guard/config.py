from pydantic import HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="P06_PROVIDER_", frozen=True)

    endpoint: HttpUrl = HttpUrl("https://provider.test")
    api_key: SecretStr

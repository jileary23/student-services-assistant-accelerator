from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_mode: Literal["mock", "azure"] = "mock"
    app_name: str = "Student Services Assistant"
    institution_name: str = "Contoso University"
    university_website: str | None = None
    support_destination: str = "Student Services Center"
    knowledge_path: Path = Field(default=Path("data/knowledge"))

    foundry_project_endpoint: str | None = None
    azure_ai_model_deployment_name: str = "gpt-4.1-mini"

    azure_search_endpoint: str | None = None
    azure_search_index_name: str = "student-services"
    azure_search_semantic_configuration: str = "student-services-semantic"
    azure_search_vector_enabled: bool = False

    applicationinsights_connection_string: str | None = None

    @property
    def azure_ready(self) -> bool:
        return bool(self.foundry_project_endpoint and self.azure_search_endpoint)


@lru_cache
def get_settings() -> Settings:
    return Settings()

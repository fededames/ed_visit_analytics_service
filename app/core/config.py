from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DEBUG_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:55432/ed_analytics"


class Settings(BaseSettings):
    app_name: str = "ED Visit Analytics Service"
    environment: str = "development"
    database_url: str = Field(default=LOCAL_DEBUG_DATABASE_URL, alias="DATABASE_URL")
    log_level: str = "INFO"
    patient_key_secret: str = Field(default="dev-secret-change-me", alias="PATIENT_KEY_SECRET")
    visit_reconstruction_window_hours: int = 24
    visit_inactive_gap_hours: int = 8
    stage_latency_heuristic_version: str = "v1"

    model_config = SettingsConfigDict(extra="ignore", populate_by_name=True)

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("visit_reconstruction_window_hours", "visit_inactive_gap_hours")
    @classmethod
    def validate_positive_hours(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("hour-based settings must be greater than zero.")
        return value

    @field_validator("patient_key_secret")
    @classmethod
    def validate_secret_not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("PATIENT_KEY_SECRET must not be blank.")
        return trimmed

    @model_validator(mode="after")
    def validate_sensitive_settings(self) -> "Settings":
        if self.environment != "development" and self.patient_key_secret == "dev-secret-change-me":
            raise ValueError("PATIENT_KEY_SECRET must be set to a non-default value outside development.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

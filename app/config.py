from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "SwiftCourier API"

    DEBUG: bool = False

    DATABASE_URL: str = "sqlite:///./swiftcourier.db"

    SECRET_KEY: str = Field(min_length=32)

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=15,
        gt=0,
        le=60
    )

    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        gt=0,
        le=30
    )

    ALLOWED_ORIGINS: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, value):
        if not value.startswith(
            ("sqlite:///", "postgresql+psycopg://")
        ):
            raise ValueError("Unsupported database URL")
        return value

    @property
    def allowed_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    # Inject variables in the process (Compose env_file or shell); never commit .env.
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    mysql_host: str = "localhost"
    mysql_port: int = Field(default=3306, ge=1, le=65535)
    mysql_database: str = "avatar"
    mysql_user: str = "avatar"
    mysql_password: SecretStr | None = None
    cors_origins: str = "http://localhost:5173"

    def database_url(self) -> URL:
        if not self.mysql_password or not self.mysql_password.get_secret_value():
            raise ValueError("MYSQL_PASSWORD must be supplied")
        return URL.create(
            "mysql+pymysql",
            username=self.mysql_user,
            password=self.mysql_password.get_secret_value(),
            host=self.mysql_host,
            port=self.mysql_port,
            database=self.mysql_database,
            query={"charset": "utf8mb4"},
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

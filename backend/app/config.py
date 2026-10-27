from decimal import Decimal
from typing import Literal
from uuid import UUID
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class AlertStockThreshold(BaseModel):
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    unit: Literal['kg', 'package', 'unit']
    origin: Literal['demo', 'operator_configured'] = 'operator_configured'

    @field_validator('quantity', mode='before')
    @classmethod
    def decimal_text(cls, value):
        if not isinstance(value, (str, Decimal)):
            raise ValueError('Threshold quantity must be a Decimal string')
        return value

    @field_validator('unit')
    @classmethod
    def counted_unit(cls, value, info):
        quantity = info.data.get('quantity')
        if value != 'kg' and quantity is not None and quantity != quantity.to_integral_value():
            raise ValueError('Counted-unit threshold must be an integer')
        return value


class Settings(BaseSettings):
    # Inject variables in the process (Compose env_file or shell); never commit .env.
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    mysql_host: str = "localhost"
    mysql_port: int = Field(default=3306, ge=1, le=65535)
    mysql_database: str = "avatar"
    mysql_user: str = "avatar"
    mysql_password: SecretStr | None = None
    avatar_api_key: SecretStr | None = None
    cors_origins: str = "http://localhost:5173"
    avatar_ml_model_dir: str = str(Path(__file__).resolve().parents[2] / 'ml' / 'models')

    avatar_alert_policy_version: str = Field(default='ek02-v1', pattern=r'^[a-zA-Z0-9._-]{1,40}$')
    avatar_alert_expiry_days: int = Field(default=7, ge=0, le=30)
    avatar_alert_cost_percent: Decimal = Field(default=Decimal('15'), gt=0, le=1000, max_digits=8, decimal_places=4)
    avatar_alert_yield_percent: Decimal = Field(default=Decimal('15'), gt=0, le=1000, max_digits=8, decimal_places=4)
    avatar_alert_deviation_origin: Literal['demo', 'operator_configured'] = 'demo'
    avatar_alert_stock_thresholds: dict[UUID, AlertStockThreshold] = Field(default_factory=dict, max_length=200)

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

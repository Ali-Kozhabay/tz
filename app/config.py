from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "tz-t"
    base_url: str = "http://localhost:8000"
    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/app"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "secret-key"
    jwt_alg: str = "HS256"
    access_token_ttl: int = 900  # 15m
    refresh_token_ttl: int = 60 * 60 * 24 * 7  # 7d
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str | None = None
    smtp_pass: str | None = None
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minio"
    s3_secret_key: str = "minio123"
    s3_bucket: str = "content"
    rate_limit_auth_per_minute: int = 10
    rate_limit_chat_per_minute: int = 30
    rate_limit_upload_per_minute: int = 5

    class Config:
        env_file = ".env"


settings = Settings()

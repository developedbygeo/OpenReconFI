from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Anthropic
    anthropic_api_key: str = ""

    # Google
    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""
    drive_invoices_folder_id: str = ""

    # Postgres
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "matchbook"
    postgres_user: str = "matchbook"
    postgres_password: str = ""

    # Embeddings (OpenAI)
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1024

    # App
    secret_key: str = ""
    frontend_url: str = "http://localhost:5173"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
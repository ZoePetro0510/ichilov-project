"""Settings loaded from environment variables / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str = "medai"
    postgres_password: str = "change-me"
    postgres_db: str = "medai"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    agent_db_user: str = "agent_readonly"
    agent_db_password: str = "change-me-too"

    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_dim: int = 384

    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = ""  # empty = sensible default per provider

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def agent_database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.agent_db_user}:{self.agent_db_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()

# Created by Ryan Polasky | 9/2/25
# Lode | All Rights Reserved

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized application settings. Default values are for the local Docker Compose setup.
    """
    OPENSEARCH_HOST: str = "opensearch-node1"
    OPENSEARCH_PORT: int = 9200
    OPENSEARCH_SSL: bool = False

    OLLAMA_HOST: str = "ollama"
    OLLAMA_PORT: int = 11434
    OLLAMA_MODEL: str = "phi3:mini"

    # REDIS_HOST: str = "redis"
    # POSTGRES_USER: str = "user"
    # POSTGRES_PASSWORD: str = "password"
    # POSTGRES_DB: str = "lode"
    # POSTGRES_HOST: str = "postgres"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')


settings = Settings()

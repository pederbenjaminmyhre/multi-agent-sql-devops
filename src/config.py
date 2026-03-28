from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"

    cosmos_endpoint: str = ""
    cosmos_key: str = ""
    cosmos_database: str = "sql-review-db"

    keyvault_url: str = ""
    appinsights_connection_string: str = ""
    max_critique_loops: int = 3


settings = Settings()

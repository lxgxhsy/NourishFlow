from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://nourish:nourish@localhost:5432/nourishflow"
    meili_url: str = "http://localhost:7700"
    meili_master_key: str = ""
    deepseek_api_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

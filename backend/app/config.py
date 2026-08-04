from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/open_hoops"
    redis_url: str = "redis://localhost:6379/0"
    upload_dir: str = "uploads"

    model_config = {"env_prefix": "OPEN_HOOPS_"}


settings = Settings()

import os

from pydantic_settings import BaseSettings

_LOCAL_UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads"
)


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/open_hoops"
    redis_url: str = "redis://localhost:6379/0"
    upload_dir: str = _LOCAL_UPLOAD_DIR

    model_config = {"env_prefix": "OPEN_HOOPS_"}


settings = Settings()

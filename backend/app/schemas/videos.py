from pydantic import BaseModel
from datetime import date


class VideoUpload(BaseModel):
    name: str
    date: date
    home_team_uid: str
    away_team_uid: str


class VideoResponse(BaseModel):
    uid: str
    name: str
    date: date
    home_team_uid: str
    away_team_uid: str
    status: str
    stats_json: dict | None

    model_config = {"from_attributes": True}

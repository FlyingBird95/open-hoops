from pydantic import BaseModel


class TeamCreate(BaseModel):
    name: str
    is_own: bool = False
    home_color: str = "#000000"
    away_color: str = "#ffffff"


class TeamUpdate(BaseModel):
    name: str | None = None
    home_color: str | None = None
    away_color: str | None = None


class TeamResponse(BaseModel):
    uid: str
    name: str
    is_own: bool
    home_color: str
    away_color: str

    model_config = {"from_attributes": True}

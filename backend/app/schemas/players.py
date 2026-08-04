from pydantic import BaseModel


class PlayerCreate(BaseModel):
    team_uid: str
    jersey_number: int
    name: str | None = None


class PlayerUpdate(BaseModel):
    jersey_number: int | None = None
    name: str | None = None


class PlayerResponse(BaseModel):
    uid: str
    team_uid: str
    jersey_number: int
    name: str | None

    model_config = {"from_attributes": True}

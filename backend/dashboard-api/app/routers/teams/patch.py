from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import database
from app.jsonapi import document

from .queries import fetch_team
from .router import router
from .serialize import serialize_team


class TeamPatchAttributes(BaseModel):
    name: str | None = None
    is_own: bool | None = None
    home_color: str | None = None
    away_color: str | None = None


class TeamPatchData(BaseModel):
    type: str = "teams"
    attributes: TeamPatchAttributes


class TeamPatchRequest(BaseModel):
    data: TeamPatchData


@router.patch("/{uid}")
def update_team(uid: str, body: TeamPatchRequest, db: Session = Depends(database.use_session)):
    team = fetch_team(db, uid)
    for key, value in body.data.attributes.model_dump(exclude_unset=True).items():
        setattr(team, key, value)
    db.commit()
    db.refresh(team)
    return document(data=serialize_team(team))

from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db, get_or_404
from app.jsonapi import document
from open_hoops.service.team.models import Team

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


def update_team(uid: str, body: TeamPatchRequest, db: Session = Depends(get_db)):
    team = get_or_404(db, Team, uid)
    for key, value in body.data.attributes.model_dump(exclude_unset=True).items():
        setattr(team, key, value)
    db.commit()
    db.refresh(team)
    return document(data=serialize_team(team))

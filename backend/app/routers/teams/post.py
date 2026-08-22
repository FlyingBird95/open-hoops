from fastapi import Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.jsonapi import document
from open_hoops.service.team.models import Team

from .serialize import serialize_team


class TeamCreateAttributes(BaseModel):
    name: str
    is_own: bool = False
    home_color: str = "#000000"
    away_color: str = "#ffffff"


class TeamCreateData(BaseModel):
    type: str = "teams"
    attributes: TeamCreateAttributes


class TeamCreateRequest(BaseModel):
    data: TeamCreateData


def create_team(body: TeamCreateRequest, db: Session = Depends(get_db)):
    attrs = body.data.attributes
    team = Team(
        name=attrs.name,
        is_own=attrs.is_own,
        home_color=attrs.home_color,
        away_color=attrs.away_color,
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    return JSONResponse(content=document(data=serialize_team(team)), status_code=201)

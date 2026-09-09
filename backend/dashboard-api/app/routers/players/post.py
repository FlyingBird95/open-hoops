from fastapi import Depends
from fastapi.responses import JSONResponse
from open_hoops.service.player.models import Player
from open_hoops.service.team.models import Team
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import exceptions
from app.database import database
from app.jsonapi import document

from .router import router
from .serialize import serialize_player


class PlayerCreateAttributes(BaseModel):
    jersey_number: int
    name: str | None = None


class RelLinkage(BaseModel):
    type: str
    uid: str


class TeamRelationship(BaseModel):
    data: RelLinkage


class PlayerCreateRelationships(BaseModel):
    team: TeamRelationship


class PlayerCreateData(BaseModel):
    type: str = "players"
    attributes: PlayerCreateAttributes
    relationships: PlayerCreateRelationships


class PlayerCreateRequest(BaseModel):
    data: PlayerCreateData


@router.post("")
def create_player(body: PlayerCreateRequest, db: Session = Depends(database.use_session)):
    team_uid = body.data.relationships.team.data.uid
    team = db.query(Team).filter(Team.uid == team_uid).first()
    if not team:
        raise exceptions.NotFound("Team not found")

    attrs = body.data.attributes
    player = Player(
        team_id=team.id,
        jersey_number=attrs.jersey_number,
        name=attrs.name,
    )
    db.add(player)
    db.commit()
    db.refresh(player)
    return JSONResponse(content=document(data=serialize_player(player)), status_code=201)

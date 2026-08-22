from fastapi import Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db, get_or_404
from app.jsonapi import document
from open_hoops.service.player.models import Player
from open_hoops.service.team.models import Team

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
def create_player(body: PlayerCreateRequest, db: Session = Depends(get_db)):
    team = get_or_404(db, Team, body.data.relationships.team.data.uid)
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

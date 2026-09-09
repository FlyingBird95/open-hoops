from fastapi import Depends
from open_hoops.service.event.models import GameEvent
from open_hoops.service.player.models import Player
from open_hoops.service.team.models import Team
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import exceptions
from app.database import database
from app.jsonapi import document

from . import dependencies
from .post import EVENT_TYPES
from .router import router
from .serialize import serialize_event


class EventPatchAttributes(BaseModel):
    type: str | None = None
    team_uid: str | None = None
    player_uid: str | None = None
    player2_uid: str | None = None


class EventPatchData(BaseModel):
    type: str = "game_events"
    attributes: EventPatchAttributes


class EventPatchRequest(BaseModel):
    data: EventPatchData


@router.patch("/{uid}")
def patch_event(
    body: EventPatchRequest,
    event: GameEvent = Depends(dependencies.get_event_by_uid),
    db: Session = Depends(database.use_session),
):
    attrs = body.data.attributes

    if attrs.type is not None:
        if attrs.type not in EVENT_TYPES:
            raise exceptions.UnprocessableEntity(f"Invalid event type: {attrs.type}")
        event.type = attrs.type

    if "team_uid" in body.data.attributes.model_fields_set:
        if attrs.team_uid:
            team = db.query(Team).filter(Team.uid == attrs.team_uid).first()
            if not team:
                raise exceptions.UnprocessableEntity("Team not found")
            event.team_id = team.id
        else:
            event.team_id = None

    if "player_uid" in body.data.attributes.model_fields_set:
        if attrs.player_uid:
            player = db.query(Player).filter(Player.uid == attrs.player_uid).first()
            if not player:
                raise exceptions.UnprocessableEntity("Player not found")
            event.player_id = player.id
        else:
            event.player_id = None

    if "player2_uid" in body.data.attributes.model_fields_set:
        if attrs.player2_uid:
            player2 = db.query(Player).filter(Player.uid == attrs.player2_uid).first()
            if not player2:
                raise exceptions.UnprocessableEntity("Player2 not found")
            event.player2_id = player2.id
        else:
            event.player2_id = None

    db.commit()
    db.refresh(event)

    return document(data=serialize_event(event))

from fastapi import Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.jsonapi import document
from app.models import Game, GameEvent, Player, Team

from .events_post import EVENT_TYPES
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


def patch_event(uid: str, event_id: str, body: EventPatchRequest, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.uid == uid).first()
    if not game:
        raise HTTPException(404, "Game not found")

    event = (
        db.query(GameEvent)
        .filter(GameEvent.id == int(event_id), GameEvent.game_id == game.id)
        .first()
    )
    if not event:
        raise HTTPException(404, "Event not found")

    attrs = body.data.attributes

    if attrs.type is not None:
        if attrs.type not in EVENT_TYPES:
            raise HTTPException(422, f"Invalid event type: {attrs.type}")
        event.type = attrs.type

    if "team_uid" in body.data.attributes.model_fields_set:
        if attrs.team_uid:
            team = db.query(Team).filter(Team.uid == attrs.team_uid).first()
            if not team:
                raise HTTPException(422, "Team not found")
            event.team_id = team.id
        else:
            event.team_id = None

    if "player_uid" in body.data.attributes.model_fields_set:
        if attrs.player_uid:
            player = db.query(Player).filter(Player.uid == attrs.player_uid).first()
            if not player:
                raise HTTPException(422, "Player not found")
            event.player_id = player.id
        else:
            event.player_id = None

    if "player2_uid" in body.data.attributes.model_fields_set:
        if attrs.player2_uid:
            player2 = db.query(Player).filter(Player.uid == attrs.player2_uid).first()
            if not player2:
                raise HTTPException(422, "Player2 not found")
            event.player2_id = player2.id
        else:
            event.player2_id = None

    db.commit()
    db.refresh(event)

    return document(data=serialize_event(event))
